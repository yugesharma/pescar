"""Waves step: Viability (F1) and trip status (F2) from Copernicus Marine Hs.

Run:  uv run python waves.py --test   -> logic self-check, no network
      uv run python waves.py --check  -> 0.083° vs 0.2° reanalysis check (ADR-0002)
"""
import math
import sys

import pandas as pd

LIMITS = [1.0, 1.5, 2.0]      # wave limits, m; viable if worst trip-window Hs is below
MARGIN = 0.3                  # m above the limit = MARGINAL
TRIP_HOURS = range(8, 15)     # trip window, local time, 08:00-14:59
SHOULDER = [4, 5, 6, 9, 10]   # Apr-Jun, Sep-Oct
SHOULDER_DAYS = 152           # days in those months
# ponytail: one time zone, fine for the 11 pilot harbours; look up by coordinates in slice 3
TZ = "Atlantic/Azores"
HIRES = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"   # Nov 2022 -> +10 days
LONG = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"        # 1980 -> ~2 months ago
HISTORY_START = "2022-11-01"


# --- core logic -------------------------------------------------------------
def daily_worst(hs: pd.Series) -> pd.Series:
    """Max Hs over the local trip window, per local day. hs index is UTC."""
    hs = hs.tz_localize("UTC").tz_convert(TZ) if hs.index.tz is None else hs.tz_convert(TZ)
    trip = hs[hs.index.hour.isin(TRIP_HOURS)]
    return trip.groupby(trip.index.date).max()


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
    """Hs time series at the model cell: nearest sea cell to (lat, lon)."""
    import copernicusmarine as cm
    d = 0.25
    ds = cm.open_dataset(dataset_id=dataset_id, variables=["VHM0"],
                         minimum_latitude=lat - d, maximum_latitude=lat + d,
                         minimum_longitude=lon - d, maximum_longitude=lon + d,
                         start_datetime=start, end_datetime=end)
    first = ds["VHM0"].isel(time=0).to_dataframe().dropna().reset_index()
    k = math.cos(math.radians(lat))
    d2 = (first.latitude - lat) ** 2 + ((first.longitude - lon) * k) ** 2
    cell = first.loc[d2.idxmin()]
    km = round(math.sqrt(d2.min()) * 111.2, 1)  # equirectangular; fine at these distances
    s = ds["VHM0"].sel(latitude=cell.latitude, longitude=cell.longitude).to_series()
    return s.dropna(), (round(float(cell.latitude), 3), round(float(cell.longitude), 3), km)


def run(harbours: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """harbours: code, lat, lon -> tables for the database."""
    today = pd.Timestamp.now(tz=TZ).normalize()
    today_utc = today.tz_convert("UTC").tz_localize(None)
    cells, weekly, days, forecast = [], [], [], []
    for h in harbours.itertuples():
        print("…", h.code, h.name, flush=True)
        hs, (clat, clon, km) = hs_series(HIRES, h.lat, h.lon, HISTORY_START,
                                     str((today + pd.Timedelta(days=4)).date()))
        cells.append(dict(code=h.code, cell_lat=clat, cell_lon=clon, cell_km=km))
        worst = daily_worst(hs[hs.index < today_utc])
        for lim in LIMITS:
            weekly += [dict(code=h.code, limit_m=lim, week=int(w), viability=round(v, 3))
                       for w, v in weekly_viability(worst, lim).items()]
            per_year, shoulder = viable_days(worst, lim)
            days.append(dict(code=h.code, limit_m=lim, per_year=per_year, shoulder=shoulder))
        forecast += [dict(code=h.code, date=str(d), worst_hs_m=round(float(w), 2))
                     for d, w in daily_worst(hs[hs.index >= today_utc]).head(3).items()]
    return dict(cells=pd.DataFrame(cells), viability_weekly=pd.DataFrame(weekly),
                viable_days=pd.DataFrame(days), forecast=pd.DataFrame(forecast))


def check(harbours: pd.DataFrame, limit=1.5):
    """Were the ~4 hi-res years typical? Compare on the 0.2° grid (ADR-0002)."""
    rows = []
    for h in harbours.itertuples():
        lw = daily_worst(hs_series(LONG, h.lat, h.lon, "1993-01-01", "2026-08-31")[0])
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
    w = daily_worst(hs)
    assert list(w.round(2)) == [0.8, 1.7], w
    v = weekly_viability(w, 1.0)
    assert v.loc[2] == 0.5, v
    assert [status(x, 1.0) for x in (0.9, 1.2, 1.5)] == ["GO", "MARGINAL", "NO-GO"]
    # One year: May viable, everything else not -> all viable days are shoulder days.
    days = pd.Series(2.0, index=pd.date_range("2025-01-01", "2025-12-31").date)
    days[[d.month == 5 for d in days.index]] = 0.5
    assert viable_days(days, 1.0) == (31.0, 31.0), viable_days(days, 1.0)
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    elif "--check" in sys.argv:
        from build import pilot_harbours
        check(pilot_harbours())
