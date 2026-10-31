"""Data pipeline: fetch every source and write data/pescamare.db.

Run:  uv run python build.py          (--test: self-check, no network)
First run fetches waves for ~2,300 harbours (~1 h, cached per harbour in data/cache/waves/);
later runs only refetch the pilot harbours (PILOT_REGIONS), which also get the 3-day forecast.
"""
import re
import sqlite3
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

import community
import fronts
import habitat
import pressure
import scoring
import species
import waves

DATA = Path(__file__).parent.parent / "data"
DB = DATA / "pescamare.db"
GEONAMES = DATA / "cache" / "geonames"         # download.geonames.org/export/dump/<CC>.zip
NUTS = DATA / "cache" / "nuts2.geojson"
NUTS_URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2024_4326_LEVL_2.geojson"
PILOT_REGIONS = ["PT20", "EL42"]              # NUTS 2: Azores (ADR-0004), South Aegean (ADR-0008)
NAMES = {"PTLDP": "Lajes do Pico"}             # UN/LOCODE just says "Lajes"
ISO2 = dict(BEL="BE", BGR="BG", CYP="CY", DEU="DE", DNK="DK", ESP="ES", EST="EE", FIN="FI", FRA="FR",
            GRC="GR", HRV="HR", IRL="IE", ITA="IT", LTU="LT", LVA="LV", MLT="MT", NLD="NL", POL="PL",
            PRT="PT", ROU="RO", SVN="SI", SWE="SE")
# European waters, Canaries to the Arctic, Azores to the Black Sea; drops the odd overseas port
LETTERS = str.maketrans({"ł": "l", "ø": "o", "æ": "ae", "ß": "ss", "đ": "d", "þ": "th", "ı": "i"})  # no NFKD form
HARBOUR_WORDS = {"sadam", "paadisadam", "hamn", "havn", "hafen", "h", "i", "ii", "iii", "limhn", "limani"}
EUROPE_LAT, EUROPE_LON = (27, 72), (-32, 45)


def dms(s: str) -> tuple[float, float]:
    """UN/LOCODE '3744N 02540W' -> (37.733, -25.667)."""
    lat, lon = s.split()
    f = lambda v, n: (int(v[:n]) + int(v[n:n + 2]) / 60) * (-1 if v[-1] in "SW" else 1)
    return round(f(lat, 2), 4), round(f(lon, 3), 4)


def norm(name: str) -> str:
    """'St. -Peter-Ording' -> 'st peter ording': no accents, case or punctuation."""
    s = unicodedata.normalize("NFKD", name.lower().translate(LETTERS)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def variants(name: str) -> list[str]:
    """Names to try in order: whole, the part before '(', ',', '/' or ' - ', then both without
    harbour words or numbering ('Rannaaugu Sadam', 'Piaski I'), then Greek 'oy' read as 'ou'."""
    names = [norm(name), norm(re.split(r"[(,/]| - ", name)[0])]
    names += [" ".join(w for w in n.split() if w not in HARBOUR_WORDS) for n in names]
    names += [n.replace("oy", "ou") for n in names]
    return list(dict.fromkeys(n for n in names if n))


def geonames(cc: str) -> pd.DataFrame:
    """Populated places and harbours in one country: key (normalised name), lat, lon, tz, pop."""
    path = GEONAMES / f"{cc}.zip"
    if not path.exists():
        GEONAMES.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"https://download.geonames.org/export/dump/{cc}.zip", path)
    with zipfile.ZipFile(path) as z:
        g = pd.read_csv(z.open(f"{cc}.txt"), sep="\t", header=None, usecols=[1, 2, 3, 4, 5, 6, 7, 14, 17],
                        names=["name", "ascii", "alt", "lat", "lon", "cls", "fcode", "pop", "tz"],
                        dtype={"alt": str}, keep_default_na=False, quoting=3)
    g = g[(g.cls == "P") | g.fcode.isin(["HBR", "PRT"])]
    g["key"] = (g.name + "," + g.ascii + "," + g.alt).str.split(",")
    g = g.explode("key")
    g["key"] = g.key.map(norm)
    return g[g.key != ""].sort_values("pop", ascending=False)


def harbours() -> pd.DataFrame:
    """Harbours (ADR-0004): EU ports of registration with a licensed vessel under 12 m, outside
    the French outermost regions. code, name, cc, small_boats, lat, lon, coords, tz."""
    f = pd.read_csv(DATA / "fleet_EU_current.csv", low_memory=False, usecols=[
        "Country of Registration", "Place of Registration Code", "Place of Registration Name",
        "LOA (m)", "Licence Indicator", "Segment"])
    f = f[(f["LOA (m)"] < 12) & (f["Licence Indicator"] == "Y")
          & ~f.Segment.astype(str).str.startswith("4F")]
    f["cc"] = f["Country of Registration"].map(ISO2)
    raw = f["Place of Registration Code"].astype(str)
    # Not every country uses UN/LOCODE (Greece '007', Italy '00126'); those codes repeat across countries.
    f["code"] = raw.where(raw.str.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}"), f.cc + "-" + raw)
    h = f.groupby("code").agg(name=("Place of Registration Name", "first"), cc=("cc", "first"),
                              small_boats=("code", "size")).reset_index()

    loc = pd.read_csv(DATA / "unlocode.csv", dtype=str, keep_default_na=False)
    loc = loc[loc.Coordinates != ""].assign(code=loc.Country + loc.Location).drop_duplicates("code")
    h = h.merge(loc[["code", "Name", "Coordinates"]], on="code", how="left")
    h["name"] = h.code.map(NAMES).fillna(h.Name).fillna(h.name).fillna("")
    h[["lat", "lon"]] = [dms(c) if isinstance(c, str) else (np.nan, np.nan) for c in h.Coordinates]
    h["coords"] = np.where(h.lat.notna(), "UN/LOCODE", None)

    tz = []
    for cc, idx in h.groupby("cc").groups.items():
        g = geonames(cc)
        first = g.drop_duplicates("key").set_index("key")  # most populous place of each name
        for i in idx:
            if pd.isna(h.at[i, "lat"]):
                hit = next((first.loc[k] for k in variants(h.at[i, "name"]) if k in first.index), None)
                if hit is not None:
                    h.loc[i, ["lat", "lon", "coords"]] = hit.lat, hit.lon, "GeoNames"
        places = g[g.tz != ""].drop_duplicates(["lat", "lon"])
        for i in idx:  # time zone of the nearest place
            if pd.notna(h.at[i, "lat"]):
                tz.append((i, places.tz.iat[community.km(h.at[i, "lat"], h.at[i, "lon"],
                                                         places.lat.values, places.lon.values).argmin()]))
    h["tz"] = pd.Series(dict(tz))
    h["in_europe"] = h.lat.between(*EUROPE_LAT) & h.lon.between(*EUROPE_LON)
    return h.drop(columns=["Name", "Coordinates"]).sort_values("code").reset_index(drop=True)


def regions(h: pd.DataFrame) -> pd.DataFrame:
    """NUTS 2 region (Eurostat GISCO 2024, 1:1M) of each harbour: code, region, region_name.
    The region within the harbour's own country that contains it or, for a harbour just off the
    generalised coastline, lies nearest."""
    import json
    import shapely
    if not NUTS.exists():
        urllib.request.urlretrieve(NUTS_URL, NUTS)
    feats = json.loads(NUTS.read_text())["features"]
    shapes = np.array([shapely.geometry.shape(f["geometry"]) for f in feats])
    props = [f["properties"] for f in feats]
    out = []
    for cc, group in h.groupby("cc"):
        mine = [i for i, p in enumerate(props) if p["CNTR_CODE"] == {"GR": "EL"}.get(cc, cc)]  # Eurostat: Greece = EL
        pts = shapely.points(group.lon.values, group.lat.values)
        nearest = np.array([shapely.distance(shapes[mine], p).argmin() for p in pts])
        out += [dict(code=c, region=props[mine[i]]["NUTS_ID"], region_name=props[mine[i]]["NAME_LATN"])
                for c, i in zip(group.code, nearest)]
    return pd.DataFrame(out)


def main():
    sp = species.run()  # first: the slowest network step on a cold cache (GBIF)
    all_h = harbours()
    h = all_h[all_h.in_europe].drop(columns="in_europe")  # no coordinates -> not in Europe either
    h = h.merge(regions(h), on="code")
    h["pilot"] = h.region.isin(PILOT_REGIONS)
    w = waves.run(h)
    cells = w.pop("cells")
    placed = cells[cells.cell_km <= waves.MAX_KM]
    counts = dict(ports=len(all_h), no_coords=int(all_h.lat.isna().sum()),
                  outside_europe=int((all_h.lat.notna() & ~all_h.in_europe).sum()),
                  no_sea_cell=len(cells) - len(placed), fetch_failed=len(h) - len(cells), placed=len(placed))
    print(counts)
    h = h.merge(placed, on="code")
    h = h.merge(community.run(h), on="code")
    h = h.merge(pressure.run(h), on="code", how="left")
    hab = habitat.run(h, sp)
    year = hab.groupby(["code", "species"]).share.mean().reset_index()  # mean over the 12 months
    status = dict(zip(sp.name, sp.status))
    h["stock_shares"] = h.code.map({c: [(status[s], x) for s, x in zip(g.species, g.share)] for c, g in year.groupby("code")})
    # Judgement: Attractiveness = target species' habitat share, mean over the target species and months.
    h["habitat_share"] = h.code.map(year[year.species.isin(sp.name[sp.target])].groupby("code").share.mean())
    for c in ["fishing_hours", "habitat_share", "stock_shares"]:  # None = partial score
        h[c] = h[c].astype(object).where(h[c].notna(), None)
    default = w["viable_days"].query("limit_m == 1.5")[["code", "per_year"]]
    h = pd.DataFrame(scoring.score(
        h.merge(default.rename(columns={"per_year": "viable_days"})).to_dict("records"))
    ).drop(columns="viable_days")  # per-limit values live in the viable_days table
    w = {k: v[v.code.isin(h.code)] for k, v in w.items()}
    layers = {"fronts_regions": ",".join(PILOT_REGIONS)}
    for region, p in h[h.pilot.astype(bool)].groupby("region"):
        layers |= fronts.run(region, (p.lat.min() - 0.7, p.lat.max() + 0.7), (p.lon.min() - 0.7, p.lon.max() + 0.7))
    meta = pd.DataFrame([
        *[(f"harbours_{k}", str(v)) for k, v in counts.items()],
        ("built_at", pd.Timestamp.now(tz="UTC").isoformat(timespec="minutes")),
        ("wave_product", waves.HIRES),
        ("wave_history", f"{waves.HISTORY_START} to {h.history_end.min()}–{h.history_end.max()}"),
        ("trip_window", "08:00-14:59 local"),
        ("osm", "OpenStreetMap via Overpass, cached " + ", ".join(
            pd.Timestamp((community.CACHE / f"osm_{cc}.json").stat().st_mtime, unit="s").strftime(f"{cc} %Y-%m-%d")
            for cc in sorted(h.cc.unique()))),
        ("fleet", "EU Fleet Register, current records"),
        ("species", "ICES Stock Assessment Graphs, ICCAT, GFCM SoMFi 2025, GBIF x Copernicus temperature, FishBase"),
        ("habitat", f"Copernicus Marine {habitat.TEMP}, {habitat.YEARS[0][:4]}-{habitat.YEARS[1][:4]}; EMODnet Bathymetry"),
        *layers.items(),
        ("pressure", f"Global Fishing Watch apparent fishing effort (AIS), {pressure.YEAR}, "
                     f"{pressure.PORT_KM}-{pressure.TRIP_KM:.0f} km from the harbour"),
    ], columns=["key", "value"])
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    with sqlite3.connect(tmp) as con:
        for name, df in dict(harbours=h, meta=meta, species=sp, habitat=hab, **w).items():
            df.to_sql(name, con, index=False)
    tmp.replace(DB)  # swap in whole, so the API never reads a half-written db
    print(f"wrote {DB}: {len(h)} harbours")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        assert dms("3744N 02540W") == (37.7333, -25.6667)
        assert dms("5130N 00005E") == (51.5, 0.0833)
        assert variants("St. -Peter-Ording") == ["st peter ording"]
        assert variants("Szczecin-Stołczyn") == ["szczecin stolczyn"]
        assert variants("Porto (Leixões)") == ["porto leixoes", "porto"]
        assert variants("Rannaaugu Sadam")[1] == "rannaaugu"
        assert "fournoi" in variants("Foyrnoi")
        print("ok")
    else:
        main()
