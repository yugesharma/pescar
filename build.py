"""Data pipeline: fetch every source and write data/pescamare.db.

Run:  uv run python build.py          (--test: self-check, no network)
"""
import sqlite3
from pathlib import Path

import pandas as pd

import waves

DATA = Path(__file__).parent / "data"
DB = DATA / "pescamare.db"
PILOT_SEGMENTS = ["4K9", "4KA"]                # Azores (ADR-0004)
NAMES = {"PTLDP": "Lajes do Pico"}             # UN/LOCODE just says "Lajes"


def dms(s: str) -> tuple[float, float]:
    """UN/LOCODE '3744N 02540W' -> (37.733, -25.667)."""
    lat, lon = s.split()
    f = lambda v, n: (int(v[:n]) + int(v[n:n + 2]) / 60) * (-1 if v[-1] in "SW" else 1)
    return round(f(lat, 2), 4), round(f(lon, 3), 4)


def pilot_harbours() -> pd.DataFrame:
    """The 11 Azorean ports of registration, with UN/LOCODE coordinates."""
    fleet = pd.read_csv(DATA / "fleet_EU_current.csv", low_memory=False,
                        usecols=["Segment", "Place of Registration Code"])
    codes = fleet[fleet.Segment.isin(PILOT_SEGMENTS)]["Place of Registration Code"].unique()
    loc = pd.read_csv(DATA / "unlocode.csv", dtype=str, keep_default_na=False)
    loc["code"] = loc.Country + loc.Location
    h = loc[loc.code.isin(codes)][["code", "Name", "Coordinates"]].rename(columns={"Name": "name"})
    h["name"] = h.code.map(NAMES).fillna(h.name)
    h[["lat", "lon"]] = h.Coordinates.map(dms).tolist()
    assert len(h) == len(codes), f"missing coordinates: {set(codes) - set(h.code)}"
    return h.drop(columns="Coordinates").sort_values("code").reset_index(drop=True)


def main():
    harbours = pilot_harbours()
    w = waves.run(harbours)
    harbours = harbours.merge(w.pop("cells"), on="code")
    meta = pd.DataFrame([
        ("built_at", pd.Timestamp.now(tz="UTC").isoformat(timespec="minutes")),
        ("wave_product", waves.HIRES),
        ("wave_history", f"{waves.HISTORY_START} to {w['forecast'].date.min()}"),
        ("trip_window", "08:00-14:59 local"),
    ], columns=["key", "value"])
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    with sqlite3.connect(tmp) as con:
        for name, df in dict(harbours=harbours, meta=meta, **w).items():
            df.to_sql(name, con, index=False)
    tmp.replace(DB)  # swap in whole, so the API never reads a half-written db
    print(f"wrote {DB}: {len(harbours)} harbours")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        assert dms("3744N 02540W") == (37.7333, -25.6667)
        assert dms("5130N 00005E") == (51.5, 0.0833)
        print("ok")
    else:
        main()
