"""Tourism step: guest nights per resident in each pilot harbour's municipality, with the raw numbers behind it.

Azores: INE monthly nights per municipality (indicator 0010735), hotels + rentals + rural tourism.
South Aegean (no open municipal nights):
  hotels and rooms = ELSTAT 2024 nights of the island group (regional unit), scaled to Eurostat NUTS 3 YEAR,
    split between the group's municipalities by their Inside Airbnb beds;
  rentals = Inside Airbnb reviews (last 12 months) x the NUTS 3 region's Eurostat platform nights per review.
Residents: GISCO LAU 2021; a municipality = the LAU codes sharing their first 4 digits (Greece, Portugal).
Gateway: nearest OSM airport that has Eurostat passengers.

Run:  uv run python tourism.py          -> fetch (cached in data/cache/tourism/) and print the pilot harbours
      uv run python tourism.py --test   -> self-check, no network
"""
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

import community

YEAR = 2025
CACHE = community.CACHE / "tourism"
UA = {"User-Agent": "PescaMare/0.1 (Copernicus Marine hackathon)"}
LAU_URL = "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2021_4326.geojson"
NUTS3_URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2024_4326_LEVL_3.geojson"
AIRBNB_URL = "https://data.insideairbnb.com/greece/south-aegean/south-aegean/2026-09-20/data/listings.csv.gz"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
INE = "https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0010735&Dim1=S3A{year}{month:02d}&lang=PT"
INE_RENTAL, INE_HOTEL = {"02"}, {"01", "03"}  # Alojamento local | Hotelaria, Turismo no espaço rural
# ELSTAT 2024 nights per South Aegean regional unit (key = first 2 digits of the municipality code):
# (hotels, rooms to let), foreign + domestic. From INSETE, "Ετήσια έκθεση ... Περιφέρεια Νοτίου Αιγαίου",
# Dec 2025, Tables 80-81 (pp. 226, 228) and 92-93 (pp. 248, 250). No machine-readable copy found.
ELSTAT_YEAR = 2024
ELSTAT_GROUPS = {
    "60": ("Thira", 2_347_427, 2_581_711), "66": ("Mykonos", 1_912_193, 587_493),
    "68": ("Paros", 665_592, 707_509), "67": ("Naxos", 618_942, 969_166),
    "58": ("Syros", 233_454, 221_148), "65": ("Milos", 217_011, 801_238),
    "70": ("Tinos", 134_900, 185_889), "59": ("Andros", 106_707, 72_812),
    "63": ("Kea-Kythnos", 53_155, 130_337), "69": ("Rhodes", 16_457_771, 1_337_568),
    "64": ("Kos", 8_731_235, 564_002), "62": ("Karpathos", 603_548, 175_203),
    "61": ("Kalymnos", 366_003, 502_515),
}


def fetch(url: str, name: str) -> bytes:
    """Download once into the cache; delete the file to refetch."""
    path = CACHE / name
    if not path.exists():
        print("…", name, flush=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900).read())
    return path.read_bytes()


def jsonstat(d: dict) -> pd.DataFrame:
    """Eurostat JSON-stat -> one row per value, one column per dimension."""
    codes = [sorted(d["dimension"][k]["category"]["index"], key=d["dimension"][k]["category"]["index"].get)
             for k in d["id"]]
    rows = [[codes[i][j] for i, j in enumerate(np.unravel_index(int(k), d["size"]))] + [v]
            for k, v in d["value"].items()]
    return pd.DataFrame(rows, columns=d["id"] + ["value"])


def eurostat(ds: str, **params) -> pd.DataFrame:
    q = urllib.parse.urlencode(params, doseq=True)
    return jsonstat(json.loads(fetch(EUROSTAT + ds + "?" + q, f"eurostat_{ds}_{hashlib.md5(q.encode()).hexdigest()[:8]}.json")))


def ine_month(month: int) -> list[dict]:
    """INE rows for one month. INE answers bursts with 429 (an HTML page), so wait and retry."""
    path = CACHE / f"ine_0010735_{YEAR}{month:02d}.json"
    for wait in [0, 30, 60, 120, 240]:
        if not path.exists():
            time.sleep(wait)
            print("… INE", YEAR, month, flush=True)
            CACHE.mkdir(parents=True, exist_ok=True)
            body = urllib.request.urlopen(urllib.request.Request(INE.format(year=YEAR, month=month), headers=UA),
                                          timeout=300).read()
            if not body.lstrip().startswith(b"["):
                continue
            path.write_bytes(body)
        return next(iter(json.loads(path.read_text())[0]["Dados"].values()))
    raise RuntimeError(f"INE {YEAR}-{month:02d} kept refusing")


def fill_confidential(known: dict, total: float) -> dict:
    """INE hides small cells ('…'). Judgement: split the region's remainder equally between the hidden ones."""
    hidden = [k for k, v in known.items() if v is None]
    rest = max(total - sum(v for v in known.values() if v is not None), 0)
    return {k: (rest / len(hidden) if v is None else v) for k, v in known.items()}


def azores() -> pd.DataFrame:
    """muni (PT + 4 digits), month, rental, hotel, hidden (cells filled from the remainder)."""
    out = []
    for m in range(1, 13):
        rows = ine_month(m)
        for seg in INE_RENTAL | INE_HOTEL:
            mine = [r for r in rows if r["dim_3"] == seg]
            total = next(float(r["valor"]) for r in mine if r["geocod"] == "200")
            known = {"PT" + r["geocod"][3:]: (float(r["valor"]) if "valor" in r else 0.0 if r.get("sinal_conv") == "-" else None)
                     for r in mine if r["geocod"].startswith("200") and len(r["geocod"]) == 7}
            hid = {k for k, v in known.items() if v is None}
            for k, v in fill_confidential(known, total).items():
                out.append(dict(muni=k, month=m, kind="rental" if seg in INE_RENTAL else "hotel", nights=v, hidden=k in hid))
    df = pd.DataFrame(out)
    names = {"PT" + r["geocod"][3:]: r["geodsg"] for r in ine_month(1) if len(r["geocod"]) == 7}
    return df.assign(name=df.muni.map(names))


def municipalities():
    """Pilot municipalities: code -> shape, residents, NUTS 3. Greece EL42; Azores = Portuguese LAU codes 4xxxxx."""
    import shapely
    lau = json.loads(fetch(LAU_URL, "lau2021.geojson"))["features"]
    nuts = [f for f in json.loads(fetch(NUTS3_URL, "nuts3.geojson"))["features"] if f["properties"]["NUTS_ID"][:4] in ("EL42", "PT20")]
    parts = {}
    for f in lau:
        p = f["properties"]
        if p["CNTR_CODE"] in ("EL", "PT") and not (p["CNTR_CODE"] == "PT" and p["LAU_ID"][0] != "4"):
            parts.setdefault(p["CNTR_CODE"] + p["LAU_ID"][:4], []).append((shapely.geometry.shape(f["geometry"]), p["POP_2021"] or 0))
    n3 = [(f["properties"]["NUTS_ID"], shapely.geometry.shape(f["geometry"])) for f in nuts]
    out = {}
    for code, ps in parts.items():
        shape = shapely.union_all([s for s, _ in ps])
        inside = [nid for nid, s in n3 if s.contains(shape.representative_point())]
        if inside:
            out[code] = dict(shape=shape, residents=int(sum(p for _, p in ps)), nuts3=inside[0])
    return out


def assign(munis: dict, lon, lat) -> np.ndarray:
    """Municipality containing each point, or None."""
    import shapely
    hit = np.full(len(lon), None, dtype=object)
    for code, m in munis.items():
        hit[shapely.contains_xy(m["shape"], lon, lat) & (hit == None)] = code  # noqa: E711
    return hit


def nearest(munis: dict, lon: float, lat: float, cc: str) -> str:
    """Municipality containing the harbour or, just off the generalised coastline, nearest to it."""
    import shapely
    p = shapely.Point(lon, lat)
    return min((c for c in munis if c.startswith(cc)), key=lambda c: munis[c]["shape"].distance(p))


def run(harbours: pd.DataFrame) -> pd.DataFrame:
    """harbours: code, cc, lat, lon of the pilot harbours -> one row of tourism numbers per harbour."""
    munis = municipalities()
    m = pd.DataFrame([dict(muni=k, residents=v["residents"], nuts3=v["nuts3"]) for k, v in munis.items()]).set_index("muni")

    # Region numbers (Eurostat, YEAR): nights in establishments, platform nights, residents.
    n3 = list(m.nuts3.unique())
    est = eurostat("tour_occ_nin3", geo=n3, c_resid="TOTAL", unit="NR", nace_r2="I551-I553", time=YEAR).set_index("geo").value
    plat = eurostat("tour_ce_oan3", geo=n3, c_resid="TOTAL", time=YEAR).set_index("geo").value
    res3 = eurostat("demo_r_pjanaggr3", geo=n3, sex="T", age="TOTAL", time=YEAR).set_index("geo").value
    months = eurostat("tour_occ_nin2m", geo=["EL42", "PT20"], c_resid="TOTAL", unit="NR", nace_r2="I551-I553", time=YEAR)
    months = months[months.month != "TOTAL"].pivot(index="geo", columns="month", values="value")

    # Greece: Inside Airbnb listings; each listing's municipality name -> code by where most of them sit.
    air = pd.read_csv(io.BytesIO(fetch(AIRBNB_URL, "airbnb_south_aegean.csv.gz")), compression="gzip",
                      usecols=["neighbourhood_cleansed", "latitude", "longitude", "number_of_reviews_ltm", "accommodates"])
    air["muni"] = assign(munis, air.longitude.values, air.latitude.values)
    code_of = air.dropna(subset="muni").groupby("neighbourhood_cleansed").muni.agg(lambda s: s.mode()[0])
    air["muni"] = air.neighbourhood_cleansed.map(code_of)
    g = air.groupby("muni").agg(listings=("muni", "size"), reviews=("number_of_reviews_ltm", "sum"), beds=("accommodates", "sum"))
    m = m.join(g)
    m["muni_name"] = pd.Series({c: n.split("(")[-1].rstrip(")").strip() for n, c in code_of.items()})
    per_review = plat / m.groupby("nuts3").reviews.sum().replace(0, np.nan)  # no Airbnb data (Azores) -> none, not inf
    m["nights_per_review"] = m.nuts3.map(per_review)

    # Azores: INE truth.
    az = azores()
    a = az.groupby(["muni", "kind"]).nights.sum().unstack()
    m.loc[a.index, "ine_rental"], m.loc[a.index, "ine_hotel"] = a.rental, a.hotel
    m.loc[a.index, "hidden_cells"] = az.groupby("muni").hidden.sum()
    m["muni_name"] = m.muni_name.fillna(az.groupby("muni").name.first())
    peak_az = az.groupby(["muni", "month"]).nights.sum().unstack()

    # Greece hotels and rooms: island group (ELSTAT) scaled to Eurostat YEAR, split by Airbnb beds.
    gr = m.index.str.startswith("EL")
    m.loc[gr, "group"] = m.index[gr].str[2:4]
    m["group_name"] = m.group.map({k: v[0] for k, v in ELSTAT_GROUPS.items()})
    elstat = pd.Series({k: v[1] + v[2] for k, v in ELSTAT_GROUPS.items()})
    scale = {n: est[n] / elstat[m[m.nuts3 == n].group.dropna().unique()].sum() for n in ("EL421", "EL422")}
    m["group_nights"] = m.group.map(elstat) * m.nuts3.map(scale)
    m["group_share"] = m.beds.fillna(0) / m.groupby("group").beds.transform("sum")
    m["rental_nights"] = np.where(gr, m.reviews.fillna(0) * m.nights_per_review, m.ine_rental)
    m["hotel_nights"] = np.where(gr, m.group_nights * m.group_share, m.ine_hotel)
    assert np.allclose(m[gr].groupby("nuts3").hotel_nights.sum(), est[["EL421", "EL422"]]), "groups must add up to Eurostat"
    m["nights"] = m.rental_nights + m.hotel_nights
    m["nights_per_resident"] = m.nights / m.residents
    m["level"] = np.where(gr, "municipality (estimate)", "municipality (INE)")
    # Peak month: the Azores per municipality (INE); Greece only per NUTS 2 (Eurostat monthly profile).
    share_gr = months.loc["EL42"] / months.loc["EL42"].sum()
    for code in m.index:
        s = share_gr if code.startswith("EL") else peak_az.loc[code] / peak_az.loc[code].sum()
        k = s.idxmax()
        m.loc[code, "peak_month"] = int(str(k).lstrip("M"))
        m.loc[code, "peak_nights_per_resident"] = m.at[code, "nights"] * s.max() / m.at[code, "residents"]
    m["region_nights_per_resident"] = m.nuts3.map(est / res3)

    # Gateway: nearest airport with Eurostat passengers.
    tags = [e["tags"] | e.get("center", e) for cc in ("GR", "PT")
            for e in json.loads((community.CACHE / f"osm_{cc}.json").read_text())["elements"]
            if e.get("tags", {}).get("aeroway") == "aerodrome" and "icao" in e["tags"]]
    ap = pd.DataFrame([dict(icao=t["icao"], name=t.get("name:en", t.get("name", "")), lat=t["lat"], lon=t["lon"],
                            rep=("EL_" if t["icao"].startswith("LG") else "PT_") + t["icao"]) for t in tags])
    pax = eurostat("avia_paoa", rep_airp=list(ap.rep), unit="PAS", tra_meas="PAS_CRD", schedule="TOTAL", tra_cov="TOTAL",
                   freq="A", time=YEAR).set_index("rep_airp").value
    ap = ap[ap.rep.map(pax).fillna(0) > 0].reset_index(drop=True)
    ap["pax"] = ap.rep.map(pax).astype(int)

    out = []
    for h in harbours.itertuples():
        code = nearest(munis, h.lon, h.lat, "EL" if h.cc == "GR" else "PT")
        d = community.km(h.lat, h.lon, ap.lat.values, ap.lon.values)
        i = int(d.argmin())
        out.append(dict(code=h.code, muni=code, airport=ap.name[i], airport_km=round(float(d[i]), 1), airport_pax=int(ap.pax[i])))
    cols = ["muni_name", "nuts3", "level", "residents", "rental_nights", "hotel_nights", "nights", "nights_per_resident",
            "peak_month", "peak_nights_per_resident", "region_nights_per_resident", "group_name", "group_nights",
            "group_share", "listings", "reviews", "beds", "nights_per_review", "hidden_cells"]
    return pd.DataFrame(out).join(m[cols], on="muni")


def test():
    # Hidden cells share what the listed municipalities leave of the region's total.
    assert fill_confidential({"a": 10.0, "b": None, "c": None}, 30) == {"a": 10.0, "b": 10.0, "c": 10.0}
    assert fill_confidential({"a": 40.0, "b": None}, 30) == {"a": 40.0, "b": 0}  # never negative
    # JSON-stat: value key = row-major position over the dimension sizes.
    d = {"id": ["geo", "time"], "size": [2, 2], "value": {"1": 5, "2": 7},
         "dimension": {"geo": {"category": {"index": {"B": 1, "A": 0}}}, "time": {"category": {"index": {"2024": 0, "2025": 1}}}}}
    assert jsonstat(d).values.tolist() == [["A", "2025", 5], ["B", "2024", 7]]
    # Hand-entered ELSTAT groups add up to the tables' own totals (Cyclades, Dodecanese; hotels, rooms).
    dod = {"61", "62", "64", "69"}
    for keys, hotels, rooms in [(ELSTAT_GROUPS.keys() - dod, 6_289_381, 6_257_303), (dod, 26_158_557, 2_579_288)]:
        assert sum(ELSTAT_GROUPS[k][1] for k in keys) == hotels and sum(ELSTAT_GROUPS[k][2] for k in keys) == rooms
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        import sqlite3
        con = sqlite3.connect(community.DATA / "pescamare.db")
        h = pd.read_sql("select code, name, cc, lat, lon from harbours where pilot = 1", con)
        t = h[["code", "name"]].merge(run(h), on="code")
        pd.set_option("display.width", 250)
        print(t.drop(columns=["code"]).round(2).sort_values(["nuts3", "nights_per_resident"]).to_string(index=False))
