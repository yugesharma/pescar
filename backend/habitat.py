"""Habitat step: share of each pilot harbour's trip area that suits each species, by month.

Suitable = monthly sea temperature inside the species' range (surface for surface fish, at the seabed for
bottom-living fish) and, for bottom-living fish, seabed depth inside their depth range.
Run:  uv run python habitat.py --test  -> self-check, no network
Cached: data/cache/thetao_monthly_<region>.nc (Copernicus Marine), data/cache/bathy/<code>.tif (EMODnet Bathymetry).
"""
import sys
import urllib.request

import numpy as np
import pandas as pd

from community import CACHE, km
from pressure import TRIP_KM

TEMP = "cmems_mod_glo_phy-thetao_anfc_0.083deg_P1M-m"   # monthly sea temperature by depth, 0.083°
YEARS = ("2023-01-01", "2025-12-01")                    # full years; each month's mean over them
MAX_DEPTH = 1500                                         # m; below every species' depth range
BATHY = ("https://ows.emodnet-bathymetry.eu/wcs?service=WCS&version=2.0.1&request=GetCoverage"
         "&coverageId=emodnet__mean&format=image/tiff&subset=Lat({},{})&subset=Long({},{})")


def temperature(region: str, lat: tuple, lon: tuple):
    """Monthly mean sea temperature (month 1-12, depth, latitude, longitude) over YEARS, for a pilot region's box."""
    import xarray as xr
    path = CACHE / f"thetao_monthly_{region}.nc"
    if not path.exists():
        import copernicusmarine as cm
        print("… Copernicus monthly sea temperature", flush=True)
        ds = cm.open_dataset(dataset_id=TEMP, variables=["thetao"], minimum_latitude=lat[0], maximum_latitude=lat[1],
                             minimum_longitude=lon[0], maximum_longitude=lon[1], maximum_depth=MAX_DEPTH,
                             start_datetime=YEARS[0], end_datetime=YEARS[1])
        ds.thetao.groupby("time.month").mean().to_netcdf(path)
    return xr.open_dataarray(path)


def seabed(code: str, lat: float, lon: float) -> pd.DataFrame:
    """EMODnet seabed depth (m, positive down) of the sea cells within TRIP_KM of a harbour: lat, lon, depth."""
    import rasterio
    path = CACHE / "bathy" / f"{code}.tif"
    d = TRIP_KM / 111.2 + 0.01
    k = np.cos(np.radians(lat))
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(BATHY.format(lat - d, lat + d, lon - d / k, lon + d / k), path)
    with rasterio.open(path) as r:
        z = r.read(1)
        rows, cols = np.indices(z.shape)
        xs, ys = rasterio.transform.xy(r.transform, rows.ravel(), cols.ravel())
    g = pd.DataFrame(dict(lat=np.asarray(ys), lon=np.asarray(xs), depth=-z.ravel().astype(float)))
    return g[(g.depth > 0) & (km(lat, lon, g.lat.values, g.lon.values) <= TRIP_KM)]


def cell_temps(g: pd.DataFrame, t) -> tuple[np.ndarray, np.ndarray]:
    """Monthly (12, cells) surface and seabed temperature for each fine cell, from its nearest model column
    with data; seabed = the deepest model level with data not below the cell's depth."""
    T = t.values                                              # month, depth, lat, lon
    lat, lon, depth = t.latitude.values, t.longitude.values, t.depth.values
    wet = ~np.isnan(T[0, 0])
    wj, wi = np.nonzero(wet)
    near = (abs(lat[wj] - g.lat.mean()) < 0.4) & (abs(lon[wi] - g.lon.mean()) < 0.5)  # keeps the distance matrix small
    wj, wi = wj[near], wi[near]
    k = np.cos(np.radians(lat.mean()))
    # nearest wet model column per fine cell
    d2 = (lat[wj][None] - g.lat.values[:, None]) ** 2 + ((lon[wi][None] - g.lon.values[:, None]) * k) ** 2
    n = d2.argmin(1)
    j, i = wj[n], wi[n]
    col = T[:, :, j, i]                                       # month, depth, cell
    deepest = (~np.isnan(col[0])).sum(0) - 1                  # last level with data in each column
    level = np.minimum(np.searchsorted(depth, g.depth.values, side="right") - 1, deepest).clip(0)
    return col[:, 0, :], col[:, level, np.arange(len(g))]


def shares(g: pd.DataFrame, surface: np.ndarray, bottom: np.ndarray, sp: pd.DataFrame) -> np.ndarray:
    """Share of the trip area's sea cells that suit each species, by month: (species, 12)."""
    out = []
    for s in sp.itertuples():
        bottom_fish = not pd.isna(s.depth_min)
        t = bottom if bottom_fish else surface
        ok = (t >= s.temp_min) & (t <= s.temp_max)
        if bottom_fish:
            ok &= ((g.depth.values >= s.depth_min) & (g.depth.values <= s.depth_max))[None]
        out.append(ok.mean(1))
    return np.array(out)


def run(harbours: pd.DataFrame, sp: pd.DataFrame) -> pd.DataFrame:
    """Pilot harbours x their region's species -> code, species, month, share.
    Delete a region's cached temperature if its harbours change."""
    rows = []
    for region, p in harbours[harbours.pilot.astype(bool)].groupby("region"):
        t = temperature(region, (p.lat.min() - 0.3, p.lat.max() + 0.3), (p.lon.min() - 0.3, p.lon.max() + 0.3))
        mine = sp[sp.region == region]
        for h in p.itertuples():
            g = seabed(h.code, h.lat, h.lon)
            s = shares(g, *cell_temps(g, t), mine)
            rows += [dict(code=h.code, species=name, month=m + 1, share=round(float(s[i, m]), 4))
                     for i, name in enumerate(mine.name) for m in range(12)]
    return pd.DataFrame(rows)


def test():
    import xarray as xr
    # Two model columns: west one 2 levels deep (0 m, 100 m), east one dry. Temperature 20 °C at 0 m, 10 °C at 100 m.
    T = np.full((12, 2, 1, 2), np.nan)
    T[:, 0, 0, 0], T[:, 1, 0, 0] = 20, 10
    t = xr.DataArray(T, dims=["month", "depth", "latitude", "longitude"],
                     coords=dict(month=range(1, 13), depth=[0, 100], latitude=[38], longitude=[-28, -27.9]))
    # Fine cells: 50 m and 500 m deep, both nearest the east (dry) column, so both use the west one.
    g = pd.DataFrame(dict(lat=38.0, lon=[-27.9, -27.91], depth=[50, 500]))
    surface, bottom = cell_temps(g, t)
    assert (surface == 20).all() and (bottom[:, 0] == 20).all() and (bottom[:, 1] == 10).all(), bottom
    sp = pd.DataFrame(dict(name=["surface fish", "bottom fish"], temp_min=[18, 8], temp_max=[22, 12],
                           depth_min=[np.nan, 400], depth_max=[np.nan, 600]))
    s = shares(g, surface, bottom, sp)
    assert (s[0] == 1).all() and (s[1] == 0.5).all(), s   # bottom fish: only the 500 m cell
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
