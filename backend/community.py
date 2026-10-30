"""Community step: tourism access (OpenStreetMap). Small boats are counted with the harbour list (build.py).

Run:  uv run python community.py --test  -> distance self-check, no network
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent.parent / "data"
CACHE = DATA / "cache"            # raw OSM per country; delete a file to refetch
RADIUS_KM = 10
STAY = {"hotel", "guest_house", "camp_site", "apartment"}
OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = """[out:json][timeout:600];area["ISO3166-1"="{cc}"][admin_level=2]->.a;(
nwr["tourism"~"^(hotel|guest_house|camp_site|apartment)$"](area.a);
nwr["aeroway"="aerodrome"]["iata"](area.a);
nwr["amenity"="ferry_terminal"](area.a););out center tags;"""


def km(lat, lon, lats, lons):
    """Great-circle distance (km) from one point to arrays of points."""
    p1, p2 = np.radians(lat), np.radians(lats)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lons - lon) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def osm(cc: str) -> pd.DataFrame:
    """Accommodation and transport points for one country: kind, name, lat, lon."""
    path = CACHE / f"osm_{cc}.json"
    if not path.exists():
        print("… OSM", cc, flush=True)
        req = urllib.request.Request(OVERPASS, urllib.parse.urlencode({"data": QUERY.format(cc=cc)}).encode(),
                                     headers={"User-Agent": "PescaMare/0.1 (Copernicus Marine hackathon)"})
        CACHE.mkdir(exist_ok=True)
        path.write_bytes(urllib.request.urlopen(req, timeout=900).read())
    rows = []
    for e in json.loads(path.read_text())["elements"]:
        t, pos = e.get("tags", {}), e.get("center", e)
        kind = ("airport" if t.get("aeroway") == "aerodrome" else
                "ferry" if t.get("amenity") == "ferry_terminal" else
                "stay" if t.get("tourism") in STAY else None)
        if kind and "lat" in pos:
            rows.append((kind, t.get("name", ""), pos["lat"], pos["lon"]))
    return pd.DataFrame(rows, columns=["kind", "name", "lat", "lon"])


def run(harbours: pd.DataFrame) -> pd.DataFrame:
    """harbours: code, cc, lat, lon -> code, places, transport_km, transport."""
    out = []
    for cc, group in harbours.groupby("cc"):
        pts = osm(cc)
        stay, move = pts[pts.kind == "stay"], pts[pts.kind != "stay"].reset_index(drop=True)
        for h in group.itertuples():
            d = km(h.lat, h.lon, move.lat.values, move.lon.values)
            i = int(d.argmin())
            out.append(dict(code=h.code, places=int((km(h.lat, h.lon, stay.lat.values, stay.lon.values) <= RADIUS_KM).sum()),
                            transport_km=round(float(d[i]), 1),
                            transport=f"{move.kind[i]}: {move.name[i]}".strip(": ")))
    return pd.DataFrame(out)


def test():
    # One degree along a great circle is 6371·π/180 = 111.19 km; at 60°N a degree of
    # longitude is half that along the parallel, slightly less than half as a great circle.
    assert abs(km(0, 0, np.array([1.0]), np.array([0.0]))[0] - 111.19) < 0.01
    assert abs(km(0, 0, np.array([0.0]), np.array([1.0]))[0] - 111.19) < 0.01
    assert 55.5 < km(60, 0, np.array([60.0]), np.array([1.0]))[0] < 55.6
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
