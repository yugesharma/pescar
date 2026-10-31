"""Species step, per pilot region: stock status (ICES SAG; ICCAT and GFCM by hand) and habitat ranges
(GBIF occurrences x Copernicus temperature, FishBase depth).

Run:  uv run python species.py --test  -> status and range self-check, no network
Cached in data/cache/ices/, data/cache/gbif/ and data/cache/temp_05deg.npz; delete to refetch.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

import habitat
from community import CACHE

# Per pilot region (NUTS 2): name, scientific name, ICES stock (None: entered by hand below),
# depth range in m for bottom-living fish (FishBase "usually" range; None: surface fish, no depth check), target species
AZORES = [
    ("Blackspot seabream", "Pagellus bogaraveo", "sbr.27.10", (150, 300), False),
    ("Black scabbardfish", "Aphanopus carbo", "bsf.27.nea", (700, 1300), False),
    ("Alfonsinos", "Beryx splendens", "alf.27.nea", (400, 600), False),  # stock is Beryx spp.
    ("Greater forkbeard", "Phycis blennoides", "gfb.27.nea", (100, 450), False),
    ("Blue jack mackerel", "Trachurus picturatus", "jaa.27.10a2", None, True),
    ("Chub mackerel", "Scomber colias", None, None, False),
    ("Skipjack tuna", "Katsuwonus pelamis", None, None, True),
    ("Bigeye tuna", "Thunnus obesus", None, None, False),
]
# South Aegean: no ICES; status from GFCM (see GFCM below). Targets chosen by the user (30 Oct 2026).
AEGEAN = [
    ("Red mullet", "Mullus barbatus", None, (100, 300), False),
    ("Surmullet", "Mullus surmuletus", None, (5, 409), True),   # FishBase gives no "usually" range
    ("European hake", "Merluccius merluccius", None, (70, 400), False),
    ("Common pandora", "Pagellus erythrinus", None, (20, 100), True),
    ("Bogue", "Boops boops", None, (0, 100), False),
    ("Sardine", "Sardina pilchardus", None, None, False),
    ("European anchovy", "Engraulis encrasicolus", None, None, False),
    ("Dolphinfish", "Coryphaena hippurus", None, None, False),
]
SPECIES = {"PT20": AZORES, "EL42": AEGEAN}
SOMFI = "GFCM SoMFi 2025, GSA 22 (Aegean)"
# GFCM, The State of Mediterranean and Black Sea Fisheries 2025, Tables 5-6, reference year 2023: F/FMSY, B/BMSY.
GFCM = {"Red mullet": (0.78, 0.41), "Surmullet": (0.55, 0.61), "Sardine": (1.5, 0.66), "European anchovy": (0.39, 0.65)}
B_LOW = 0.5   # judgement (user, 30 Oct 2026): stock under half its MSY size counts as overfished, like ICES's trigger
HAND = {  # status, source, assessment year
    "Chub mackerel": ("Unknown", "No ICES or ICCAT assessment for the Azores", None),
    "Skipjack tuna": ("Healthy", "ICCAT, eastern Atlantic skipjack (SKJ-E)", 2022),
    "Bigeye tuna": ("Healthy", "ICCAT, Atlantic bigeye (BET)", 2025),
    "European hake": ("Unknown", f"{SOMFI}: advice in words only", 2023),
    "Common pandora": ("Unknown", "No GFCM assessment for the Aegean", None),
    "Bogue": ("Unknown", "No GFCM assessment for the Aegean", None),
    "Dolphinfish": ("Unknown", "No GFCM assessment for the Aegean", None),
}
SAG = "https://sag.ices.dk/SAG_API/api"
FIRST_YEAR = 2015   # oldest ICES assessment year searched for a stock's latest assessment
GBIF = "https://api.gbif.org/v1"
# Kept: observations and specimens; left out: fossils and aquarium (living) specimens.
BASIS = ["HUMAN_OBSERVATION", "MACHINE_OBSERVATION", "OBSERVATION", "PRESERVED_SPECIMEN", "MATERIAL_SAMPLE", "OCCURRENCE"]
CELL = 0.5          # degrees; one occurrence cell, as AquaMaps
RANGE_PCT = (2.5, 97.5)   # judgement (user, 31 Oct 2026): middle 95% of occurrence cells; 10-90 cut off warm seas
SEABED = "cmems_mod_glo_phy_anfc_0.083deg_P1M-m"   # tob: temperature at the seabed, monthly


def get(url: str, path=None) -> str:
    if path is None or not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PescaMare)"})
        for attempt in range(6):  # GBIF answers the odd request with a 5xx, or 429 when we go too fast
            try:
                body = urllib.request.urlopen(req, timeout=120).read()
                break
            except OSError as e:
                code = getattr(e, "code", None)
                if attempt == 5 or (code and 400 <= code < 500 and code != 429):
                    raise ValueError(f"{e} for {url}") from e
                time.sleep(2 ** attempt)
        if path is None:
            return body.decode("latin1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return path.read_text(encoding="latin1")


def cells(sci: str) -> np.ndarray:
    """GBIF occurrences of a species (with coordinates, no geospatial issue, present) -> unique CELL cells
    as (row, col) from (-90, -180). Read from facets (distinct coordinate values), not record pages:
    the occupied latitude bands first, then the longitudes within each band."""
    path = CACHE / "gbif" / f"{sci.replace(' ', '_')}.json"
    if not path.exists():
        key = json.loads(get(f"{GBIF}/species/match?" + urllib.parse.urlencode(dict(name=sci, strict="true"))))["usageKey"]
        base = dict(taxonKey=key, hasCoordinate="true", hasGeospatialIssue="false", occurrenceStatus="PRESENT",
                    limit=0, facetLimit=1_000_000)
        query = lambda **kw: f"{GBIF}/occurrence/search?" + urllib.parse.urlencode(base | kw) + "".join(
            f"&basisOfRecord={b}" for b in BASIS)
        facet = lambda url: [float(c["name"]) for c in json.loads(get(url))["facets"][0]["counts"]]
        bands = sorted({int((lat + 90) // CELL) for lat in facet(query(facet="decimalLatitude")) if abs(lat) < 90})  # ±90: bad records
        print(f"… GBIF {sci}: {len(bands)} latitude bands", flush=True)
        lo = lambda r: r * CELL - 90
        with ThreadPoolExecutor(3) as ex:  # 1e-6: a band's upper edge belongs to the next band
            lons = ex.map(lambda r: facet(query(facet="decimalLongitude",
                                                decimalLatitude=f"{lo(r):.6f},{lo(r) + CELL - 1e-6:.6f}")), bands)
            found = {(r, int((lon + 180) // CELL)) for r, ls in zip(bands, lons) for lon in ls}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(found)))
    return np.array(json.loads(path.read_text())).reshape(-1, 2)


def to_cells(v: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Model grid values (lat, lon), NaN on land -> mean per CELL cell (180/CELL, 360/CELL), NaN where all land."""
    rows, cols = int(180 / CELL), int(360 / CELL)
    r = np.clip(((lat + 90) // CELL).astype(int), 0, rows - 1)[:, None]
    c = np.clip(((lon + 180) // CELL).astype(int), 0, cols - 1)[None, :]
    idx, ok = (r * cols + c).ravel(), ~np.isnan(v.ravel())
    s = np.bincount(idx[ok], v.ravel()[ok], rows * cols)
    n = np.bincount(idx[ok], minlength=rows * cols)
    with np.errstate(invalid="ignore"):
        return (s / n).reshape(rows, cols)


def temperatures() -> tuple[np.ndarray, np.ndarray]:
    """Mean surface and seabed temperature over habitat.YEARS (the habitat step's years and model) per CELL cell."""
    path = CACHE / "temp_05deg.npz"
    if not path.exists():
        import copernicusmarine as cm
        out = {}
        for name, dataset, var in [("surface", habitat.TEMP, "thetao"), ("seabed", SEABED, "tob")]:
            print("… Copernicus global", name, "temperature", flush=True)
            a = cm.open_dataset(dataset_id=dataset, variables=[var], start_datetime=habitat.YEARS[0],
                                end_datetime=habitat.YEARS[1], **({"maximum_depth": 1} if var == "thetao" else {}))[var]
            a = a.isel(depth=0) if "depth" in a.dims else a
            months = [to_cells(a.isel(time=i).values, a.latitude.values, a.longitude.values) for i in range(a.sizes["time"])]
            with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
                __import__("warnings").simplefilter("ignore")
                out[name] = np.nanmean(months, 0)
        np.savez_compressed(path, **out)
    z = np.load(path)
    return z["surface"], z["seabed"]


def temp_range(found: np.ndarray, field: np.ndarray) -> tuple[float, float]:
    """RANGE_PCT percentiles of a temperature field over a species' occurrence cells (land cells skipped)."""
    v = field[found[:, 0], found[:, 1]]
    return tuple(np.percentile(v[~np.isnan(v)], RANGE_PCT).round(2))


def classify(f: str, b: str) -> str:
    """ICES MSY-line text status -> Overfished (F above FMSY or stock below trigger), Healthy, Unknown."""
    f, b = f.strip().lower(), b.strip().lower()
    if f.startswith(("above", "too high")) or b.startswith(("below", "too low")):
        return "Overfished"
    if f.startswith(("below", "appropriate", "at ")) and b.startswith(("above", "appropriate")):
        return "Healthy"
    return "Unknown"


def gfcm(f_ratio: float, b_ratio: float) -> str:
    """GFCM F/FMSY and B/BMSY -> Overfished (F above FMSY or B under B_LOW x BMSY), else Healthy."""
    return "Overfished" if f_ratio > 1 or b_ratio < B_LOW else "Healthy"


def ices(stock: str) -> tuple[str, str, int]:
    """Latest ICES advice assessment of a stock -> status, source, assessment year."""
    this_year = pd.Timestamp.now().year
    found = [s for y in range(FIRST_YEAR, this_year + 1)
             for s in json.loads(get(f"{SAG}/StockList?year={y}", CACHE / "ices" / f"stocks_{y}.json"))
             if s["StockKeyLabel"] == stock and s["Purpose"] == "Advice"]
    a = max(found, key=lambda s: s["AssessmentYear"])
    lines = json.loads(get(f"{SAG}/StockStatusValues?assessmentKey={a['AssessmentKey']}",
                           CACHE / "ices" / f"status_{a['AssessmentKey']}.json"))
    msy = next(l for l in lines if l["lineDescription"].strip() == "Maximum sustainable yield")
    return classify(msy["fishingPressureStatus"], msy["stockSizeStatus"]), f"ICES, {stock}", a["AssessmentYear"]


def run() -> pd.DataFrame:
    """One row per species: region, name, scientific, status, source, year, target, temp_min/max (°C), depth_min/max (m)."""
    out, (surface, seabed) = [], temperatures()
    for region, name, sci, stock, depth, target in [(r, *s) for r, sp in SPECIES.items() for s in sp]:
        status, source, year = (ices(stock) if stock else (gfcm(*GFCM[name]), f"{SOMFI}, F/FMSY {GFCM[name][0]}, "
                                f"B/BMSY {GFCM[name][1]}", 2023) if name in GFCM else HAND[name])
        t = temp_range(cells(sci), seabed if depth is not None else surface)
        out.append(dict(region=region, name=name, scientific=sci, status=status, source=source, year=year, target=target,
                        temp_min=t[0], temp_max=t[1], depth_min=depth and depth[0], depth_max=depth and depth[1]))
    return pd.DataFrame(out)


def test():
    assert classify("Above", "Above trigger") == "Overfished"      # blackspot seabream 2025
    assert classify("too high", "too low") == "Overfished"
    assert classify("Appropriate", "Above trigger") == "Healthy"
    assert classify("Below proxy", "Above proxy") == "Healthy"
    assert classify("Unknown", "Undefined") == "Unknown"            # greater forkbeard 2026
    assert classify("Below", "Undefined") == "Unknown"
    assert gfcm(0.78, 0.41) == "Overfished" and gfcm(0.55, 0.61) == "Healthy" and gfcm(1.5, 0.66) == "Overfished"
    names = [s[0] for sp in SPECIES.values() for s in sp]
    assert len(names) == len(set(names))                           # habitat rows join on the name
    assert all(n in GFCM or n in HAND for r, sp in SPECIES.items() if r != "PT20" for n, *_ in sp)
    # Model grid: 4 points in the cell (row 256, col 304) at 38.1-38.4 N, -27.9 to -27.6 E; one is land.
    lat, lon = np.array([38.1, 38.4]), np.array([-27.9, -27.6])
    g = to_cells(np.array([[10.0, 12.0], [14.0, np.nan]]), lat, lon)
    assert g[256, 304] == 12 and np.isnan(g[0, 0]), g[256, 304]
    field = np.full((360, 720), np.nan)
    field[0, :11] = np.arange(10, 21)                                      # 10..20 °C
    found = np.array([(0, i) for i in range(12)])                          # the 12th cell is land
    assert temp_range(found, field) == (10.25, 19.75)
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        print(run().to_string())
