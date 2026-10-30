"""Waves step: Viability (F1) and trip status (F2) from Copernicus Marine Hs.

Run:  uv run python waves.py --test   -> logic self-check, no network
      uv run python waves.py --check  -> 0.083° vs 0.2° reanalysis check (ADR-0002)
"""
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

LIMITS = [1.0, 1.5, 2.0]      # wave limits, m; viable if worst trip-window Hs is below
MARGIN = 0.3                  # m above the limit = MARGINAL
TRIP_HOURS = range(8, 15)     # trip window, local time, 08:00-14:59
SHOULDER = [4, 5, 6, 9, 10]   # Apr-Jun, Sep-Oct
SHOULDER_DAYS = 152           # days in those months
MAX_KM = 20                   # no sea cell this close -> harbour dropped (inland, lake, mismatched)
CACHE = Path(__file__).parent.parent / "data" / "cache" / "waves"   # non-pilot results; delete to refetch
HIRES = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"   # Nov 2022 -> +10 days
LONG = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"        # 1980 -> ~2 months ago
HISTORY_START = "2022-11-01"


# --- core logic -------------------------------------------------------------
def daily_worst(hs: pd.Series, tz: str) -> pd.Series:
    """Max Hs over the local trip window, per local day. hs index is UTC."""
    hs = hs.tz_localize("UTC").tz_convert(tz) if hs.index.tz is None else hs.tz_convert(tz)
    trip = hs[hs.index.hour.isin(TRIP_HOURS)]
    return trip.groupby(trip.index.date).max()


def full_days(worst: pd.Series, today) -> pd.Series:
    """Every day from HISTORY_START to yesterday; a day with no model data (sea ice: the model
    has no waves there) is NaN, which is never below a limit, so it counts as not viable."""
    return worst.reindex(pd.date_range(HISTORY_START, today.tz_localize(None) - pd.Timedelta(days=1)).date)


def weekly_viability(worst: pd.Series, limit: float) -> pd.Series:
    """Share of viable days per ISO week of year, across all years."""
    ok = worst < limit
    weeks = pd.to_datetime(ok.index).isocalendar().week.values
    return ok.groupby(weeks).mean()


def viable_days(worst: pd.Series, limit: float) -> tuple[float, float]:
    """Expected viable days per year, and within the shoulder season."""
    ok = worst < limit
    shoulder = ok[pd.to_datetime(ok.index).month.isin(SHOULDER)]
    return round(ok.mean() * 365, 1), round(shoulder.mean() * SHOULDER_DAYS, 1)


def status(worst: float, limit: float) -> str:
    return "GO" if worst < limit else "MARGINAL" if worst < limit + MARGIN else "NO-GO"


# --- data access ------------------------------------------------------------
def hs_series(dataset_id, lat, lon, start, end):
    """Hs time series at the model cell: nearest sea cell to (lat, lon); (None, None) if none in the box."""
    import copernicusmarine as cm
    k = math.cos(math.radians(lat))
    d = 0.2  # ° latitude, > MAX_KM; widened in longitude so the box covers MAX_KM at any latitude
    ds = cm.open_dataset(dataset_id=dataset_id, variables=["VHM0"],
                         minimum_latitude=lat - d, maximum_latitude=lat + d,
                         minimum_longitude=lon - d / k, maximum_longitude=lon + d / k,
                         start_datetime=start, end_datetime=end)
    first = ds["VHM0"].isel(time=0).to_dataframe().dropna().reset_index()
    if first.empty:
        return None, None
    d2 = (first.latitude - lat) ** 2 + ((first.longitude - lon) * k) ** 2
    cell = first.loc[d2.idxmin()]
    km = round(math.sqrt(d2.min()) * 111.2, 1)  # equirectangular; fine at these distances
    s = ds["VHM0"].sel(latitude=cell.latitude, longitude=cell.longitude).to_series()
    return s.dropna(), (round(float(cell.latitude), 3), round(float(cell.longitude), 3), km)


def harbour(h, live: bool) -> dict[str, list[dict]]:
    """One harbour's rows for each table. live: fetch now and add the 3-day forecast (pilot);
    otherwise history only, cached in CACHE so a rerun skips harbours already done."""
    path = CACHE / f"{h.code}.json"
    if not live and path.exists():
        return json.loads(path.read_text())
    today = pd.Timestamp.now(tz=h.tz).normalize()
    today_utc = today.tz_convert("UTC").tz_localize(None)
    hs, cell = hs_series(HIRES, h.lat, h.lon, HISTORY_START, str((today + pd.Timedelta(days=4 if live else 0)).date()))
    clat, clon, km = cell or (None, None, None)
    out = dict(cells=[dict(code=h.code, cell_lat=clat, cell_lon=clon, cell_km=km, history_end=str(today.date()))],
               viability_weekly=[], viable_days=[], forecast=[])
    if km is not None and km <= MAX_KM:
        worst = full_days(daily_worst(hs[hs.index < today_utc], h.tz), today)
        for lim in LIMITS:
            out["viability_weekly"] += [dict(code=h.code, limit_m=lim, week=int(w), viability=round(v, 3))
                                        for w, v in weekly_viability(worst, lim).items()]
            per_year, shoulder = viable_days(worst, lim)
            out["viable_days"].append(dict(code=h.code, limit_m=lim, per_year=per_year, shoulder=shoulder))
        if live:
            out["forecast"] = [dict(code=h.code, date=str(d), worst_hs_m=round(float(w), 2))
                               for d, w in daily_worst(hs[hs.index >= today_utc], h.tz).head(3).items()]
    if not live:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".tmp").write_text(json.dumps(out))
        path.with_suffix(".tmp").replace(path)  # whole file or nothing, if the run is killed
    return out


def run(harbours: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """harbours: code, lat, lon, tz, pilot -> tables for the database. A harbour whose fetch
    fails is left out (no cells row) and retried on the next run."""
    def one(h):
        try:
            return harbour(h, live=h.pilot)
        except Exception as e:
            print("!", h.code, h.name, repr(e)[:200], flush=True)
            return {}
    tables = dict(cells=[], viability_weekly=[], viable_days=[], forecast=[])
    with ThreadPoolExecutor(16) as ex:  # I/O bound: ~1.6 s per harbour with 8 threads vs 7 s alone
        for i, rows in enumerate(ex.map(one, harbours.itertuples()), 1):
            for k, v in rows.items():
                tables[k] += v
            if i % 100 == 0 or i == len(harbours):
                print(f"… waves {i}/{len(harbours)}", flush=True)
    return {k: pd.DataFrame(v, columns=None if v else ["code"]) for k, v in tables.items()}


def check(harbours: pd.DataFrame, limit=1.5):
    """Were the ~4 hi-res years typical? Compare on the 0.2° grid (ADR-0002)."""
    rows = []
    for h in harbours.itertuples():
        lw = daily_worst(hs_series(LONG, h.lat, h.lon, "1993-01-01", "2026-08-31")[0], h.tz)
        recent = lw[pd.to_datetime(lw.index) >= HISTORY_START]
        rows.append(dict(harbour=h.name, p_1993=round((lw < limit).mean(), 3),
                         p_2022=round((recent < limit).mean(), 3)))
    df = pd.DataFrame(rows).assign(diff=lambda d: (d.p_2022 - d.p_1993).round(3))
    print(df.to_string(index=False))


def test():
    # 2 winter days (UTC-1), 3-hourly. Day 1 calm except a 2.5 m spike at 21 UTC
    # (20 local, outside window); day 2 spikes at 12 UTC (11 local, inside window).
    idx = pd.date_range("2025-01-06", periods=16, freq="3h")
    hs = pd.Series(0.8, index=idx)
    hs[pd.Timestamp("2025-01-06 21:00")] = 2.5
    hs[pd.Timestamp("2025-01-07 12:00")] = 1.7
    w = daily_worst(hs, "Atlantic/Azores")
    assert list(w.round(2)) == [0.8, 1.7], w
    v = weekly_viability(w, 1.0)
    assert v.loc[2] == 0.5, v
    assert [status(x, 1.0) for x in (0.9, 1.2, 1.5)] == ["GO", "MARGINAL", "NO-GO"]
    # One year: May viable, everything else not -> all viable days are shoulder days.
    days = pd.Series(2.0, index=pd.date_range("2025-01-01", "2025-12-31").date)
    days[[d.month == 5 for d in days.index]] = 0.5
    assert viable_days(days, 1.0) == (31.0, 31.0), viable_days(days, 1.0)
    # Ice: no data for a day must count as not viable, not be skipped.
    gap = full_days(pd.Series(0.5, index=pd.date_range(HISTORY_START, "2022-11-02").date), pd.Timestamp("2022-11-05"))
    assert len(gap) == 4 and (gap < 1.0).mean() == 0.5, gap
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    elif "--check" in sys.argv:
        from build import harbours
        check(harbours().query("pilot"))
