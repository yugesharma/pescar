"""Pressure step: AIS fishing hours near each pilot harbour (Global Fishing Watch, ADR-0005).

Run:  uv run python pressure.py --test  -> ring self-check, no network
Needs GFW_API_KEY in .env (free non-commercial token). Cached in data/cache/gfw_effort_<year>_<region>.json.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from community import CACHE, km

YEAR = 2025                  # last full calendar year; the API allows at most 366 days per report
DATASET = "public-global-fishing-effort:latest"
URL = ("https://gateway.api.globalfishingwatch.org/v3/4wings/report?spatial-resolution=HIGH"
       f"&temporal-resolution=ENTIRE&datasets[0]={DATASET}&date-range={YEAR}-01-01,{YEAR}-12-31&format=JSON")
TRIP_KM = 11.112             # 6 nm trip area
PORT_KM = 2                  # judgement: AIS "fishing" this close to port is mostly mooring or manoeuvring


def token() -> str:
    env = Path(__file__).parent.parent / ".env"
    lines = env.read_text().splitlines() if env.exists() else []
    return os.environ.get("GFW_API_KEY") or next(l.split("=", 1)[1] for l in lines if l.startswith("GFW_API_KEY="))


def effort(region: str, lat: tuple, lon: tuple) -> pd.DataFrame:
    """AIS fishing hours on 0.01° cells (one row per vessel and cell) in a pilot region's box: lat, lon, hours."""
    path = CACHE / f"gfw_effort_{YEAR}_{region}.json"
    if not path.exists():
        print("… GFW fishing effort", YEAR, region, flush=True)
        box = [[lon[0], lat[0]], [lon[1], lat[0]], [lon[1], lat[1]], [lon[0], lat[1]], [lon[0], lat[0]]]
        req = urllib.request.Request(URL, json.dumps({"geojson": {"type": "Polygon", "coordinates": [box]}}).encode(),
                                     headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
                                              "User-Agent": "PescaMare/0.1 (Copernicus Marine hackathon)"})
        path.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    rows = next(iter(json.loads(path.read_text())["entries"][0].values()))
    return pd.DataFrame(rows, columns=["lat", "lon", "hours"])


def hours(lat, lon, g: pd.DataFrame) -> float:
    """Fishing hours in the ring PORT_KM-TRIP_KM around a harbour."""
    d = km(lat, lon, g.lat.values, g.lon.values)
    return round(float(g.hours.values[(d > PORT_KM) & (d <= TRIP_KM)].sum()), 1)


def run(harbours: pd.DataFrame) -> pd.DataFrame:
    """Pilot harbours (code, lat, lon, region) -> code, fishing_hours. Each region's cached box is its harbours',
    padded by 0.2°; delete the cache file if a region's harbours change."""
    out = []
    for region, p in harbours[harbours.pilot.astype(bool)].groupby("region"):
        g = effort(region, (p.lat.min() - 0.2, p.lat.max() + 0.2), (p.lon.min() - 0.2, p.lon.max() + 0.2))
        out.append(pd.DataFrame(dict(code=p.code, fishing_hours=[hours(h.lat, h.lon, g) for h in p.itertuples()])))
    return pd.concat(out)


def test():
    # Points due north of (0, 0): 1 km (in port), 5 km and 11 km (in the ring), 12 km (outside 6 nm).
    g = pd.DataFrame(dict(lat=np.array([1, 5, 11, 12]) / 111.19, lon=0.0, hours=[100, 2, 3, 50]))
    assert hours(0, 0, g) == 5, hours(0, 0, g)
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
