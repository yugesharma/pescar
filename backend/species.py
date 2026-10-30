"""Species step: stock status (ICES SAG, ICCAT by hand) and habitat ranges (AquaMaps, FishBase).

Run:  uv run python species.py --test  -> status and envelope self-check, no network
Cached in data/cache/ices/ and data/cache/aquamaps/; delete to refetch.
"""
import http.cookiejar
import json
import re
import sys
import urllib.request

import numpy as np
import pandas as pd

from community import CACHE

# name, scientific name, AquaMaps SpecID, ICES stock (None: entered by hand below),
# depth range in m for bottom-living fish (FishBase "usually" range; None: surface fish, no depth check), target species
SPECIES = [
    ("Blackspot seabream", "Pagellus bogaraveo", "Fis-23207", "sbr.27.10", (150, 300), False),
    ("Black scabbardfish", "Aphanopus carbo", "Fis-29275", "bsf.27.nea", (700, 1300), False),
    ("Alfonsinos", "Beryx splendens", "Fis-29732", "alf.27.nea", (400, 600), False),  # stock is Beryx spp.
    ("Greater forkbeard", "Phycis blennoides", "Fis-23722", "gfb.27.nea", (100, 450), False),
    ("Blue jack mackerel", "Trachurus picturatus", "Fis-23872", "jaa.27.10a2", None, True),
    ("Chub mackerel", "Scomber colias", "Fis-133251", None, None, False),
    ("Skipjack tuna", "Katsuwonus pelamis", "Fis-22777", None, None, True),
    ("Bigeye tuna", "Thunnus obesus", "Fis-22836", None, None, False),
]
HAND = {  # status, source, assessment year
    "Chub mackerel": ("Unknown", "No ICES or ICCAT assessment for the Azores", None),
    "Skipjack tuna": ("Healthy", "ICCAT, eastern Atlantic skipjack (SKJ-E)", 2022),
    "Bigeye tuna": ("Healthy", "ICCAT, Atlantic bigeye (BET)", 2025),
}
SAG = "https://sag.ices.dk/SAG_API/api"
AQUAMAPS = "https://www.aquamaps.org"
FIRST_YEAR = 2015   # oldest ICES assessment year searched for a stock's latest assessment


def get(url: str, path=None, opener=urllib.request.build_opener()) -> str:
    if path is None or not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PescaMare)"})
        body = opener.open(req, timeout=120).read()
        if path is None:
            return body.decode("latin1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return path.read_text(encoding="latin1")


def aquamaps(spec_id: str) -> str:
    """The species' AquaMaps map-parameters page (envelope and the cells used for it). Needs a session:
    open the map page first, which names the session the parameters page belongs to."""
    path = CACHE / "aquamaps" / f"{spec_id}.html"
    if not path.exists():
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        page = get(f"{AQUAMAPS}/preMap.php?cache=1&SpecID={spec_id}&map=cached&type_of_map=regular", opener=opener)
        session = re.search(r"user_session=(\d+)", page).group(1)
        get(f"{AQUAMAPS}/ShowMapParam.php?SpecID={spec_id}&user_session={session}", path, opener)
    return get("", path)


def classify(f: str, b: str) -> str:
    """ICES MSY-line text status -> Overfished (F above FMSY or stock below trigger), Healthy, Unknown."""
    f, b = f.strip().lower(), b.strip().lower()
    if f.startswith(("above", "too high")) or b.startswith(("below", "too low")):
        return "Overfished"
    if f.startswith(("below", "appropriate", "at ")) and b.startswith(("above", "appropriate")):
        return "Healthy"
    return "Unknown"


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


def temp_range(page: str, bottom: bool) -> tuple[float, float]:
    """10th-90th percentile of the surface (or bottom) temperature of the cells AquaMaps used for the
    species' envelope. Rows are: #, lat, lon, depth, temp surface, temp bottom, ..."""
    rows = page[page.find("Cells used"):]
    temps = [float(c[5 if bottom else 4]) for r in re.findall(r"<tr bgcolor='(?:00ffcc|white)'>(.*?)</tr>", rows, re.S)
             if len(c := re.findall(r">\s*(-?[\d.]+)\s*<", r)) > 5]
    return tuple(np.percentile(temps, [10, 90]).round(2))


def run() -> pd.DataFrame:
    """One row per species: name, scientific, status, source, year, target, temp_min/max (°C), depth_min/max (m)."""
    out = []
    for name, sci, spec_id, stock, depth, target in SPECIES:
        status, source, year = ices(stock) if stock else HAND[name]
        t = temp_range(aquamaps(spec_id), bottom=depth is not None)
        out.append(dict(name=name, scientific=sci, status=status, source=source, year=year, target=target,
                        temp_min=t[0], temp_max=t[1], depth_min=depth and depth[0], depth_max=depth and depth[1]))
    return pd.DataFrame(out)


def test():
    assert classify("Above", "Above trigger") == "Overfished"      # blackspot seabream 2025
    assert classify("too high", "too low") == "Overfished"
    assert classify("Appropriate", "Above trigger") == "Healthy"
    assert classify("Below proxy", "Above proxy") == "Healthy"
    assert classify("Unknown", "Undefined") == "Unknown"            # greater forkbeard 2026
    assert classify("Below", "Undefined") == "Unknown"
    row = lambda *v: "<tr bgcolor='white'>" + "".join(f"<td>{x}</td>" for x in v) + "</tr>"
    page = "Cells used" + "".join(row(i, 38, -28, 500, 10 + i, 5) for i in range(11))  # surface 10..20
    assert temp_range(page, bottom=False) == (11, 19) and temp_range(page, bottom=True) == (5, 5)
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        print(run().to_string())
