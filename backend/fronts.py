"""Fronts step: where fish are likely today, after Tijani et al. 2015 (the method behind Map2Fish), without catch data.

Over the last 3 days of Copernicus sea temperature (SST) and chlorophyll (CHL):
- a front is where SST changes by at least FRONT_C_PER_KM;
- it is head-on (upwelling: cold, plankton-rich water) where P = ∇T·∇C / (|∇T| |∇C|) < HEAD_ON,
  i.e. the two gradients point in nearly opposite directions.
Writes data/fronts.png, a map image (EPSG:3857 rows) for the pilot area. Map layer only; not in the score.
Run:  uv run python fronts.py --test  -> self-check, no network
"""
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

SST = ("METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2", "analysed_sst")                       # 0.05°, daily, kelvin
CHL = ("cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D", "CHL")        # 4 km, daily, gap-free
DAYS = 3                  # composite length, as in the paper
FRONT_C_PER_KM = 0.02     # judgement (user, 30 Oct 2026): SST front; ~ the strongest 10% of Azores sea on 27-29 Oct 2026
HEAD_ON = -0.7            # judgement (user): angle between the gradients over ~135°
PNG = Path(__file__).parent.parent / "data" / "fronts.png"
COLOURS = {1: (214, 40, 40, 230), 2: (13, 148, 136, 240)}   # front, head-on front


def classify(t: np.ndarray, c: np.ndarray, lat: np.ndarray, step: float) -> np.ndarray:
    """SST (°C) and CHL on one regular grid (rows = lat ascending, step in degrees) -> 0 none, 1 front, 2 head-on front.
    CHL gradients are taken on log10 CHL, which spans orders of magnitude."""
    dy = 111.2 * step
    dx = dy * np.cos(np.radians(lat))[:, None]
    ty, tx = np.gradient(t)
    cy, cx = np.gradient(np.log10(c))
    ty, tx, cy, cx = ty / dy, tx / dx, cy / dy, cx / dx
    strength = np.hypot(tx, ty)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = (tx * cx + ty * cy) / (strength * np.hypot(cx, cy))
    front = strength >= FRONT_C_PER_KM
    return np.where(front & (p < HEAD_ON), 2, np.where(front, 1, 0))


def mercator_rows(lat: np.ndarray, step: float, n: int) -> np.ndarray:
    """Source row for each of n output rows evenly spaced in Web Mercator y, top (north) first."""
    y = lambda a: np.log(np.tan(np.pi / 4 + np.radians(a) / 2))
    lo, hi = lat[0] - step / 2, lat[-1] + step / 2
    rows = np.degrees(2 * np.arctan(np.exp(np.linspace(y(hi), y(lo), n))) - np.pi / 2)
    return np.clip(np.round((rows - lat[0]) / step).astype(int), 0, len(lat) - 1)


def png(path: Path, rgba: np.ndarray):
    """Minimal RGBA PNG writer (no imaging library installed)."""
    h, w, _ = rgba.shape
    raw = b"".join(b"\0" + rgba[i].tobytes() for i in range(h))
    chunk = lambda k, x: struct.pack(">I", len(x)) + k + x + struct.pack(">I", zlib.crc32(k + x))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def run(lat: tuple, lon: tuple) -> dict:
    """Fetch the last DAYS days both products have, write PNG; returns dates and image corners for the map."""
    import copernicusmarine as cm
    box = dict(minimum_latitude=lat[0], maximum_latitude=lat[1], minimum_longitude=lon[0], maximum_longitude=lon[1],
               start_datetime=str(np.datetime64("today") - 10))
    c = cm.open_dataset(dataset_id=CHL[0], variables=[CHL[1]], **box)[CHL[1]]
    t = cm.open_dataset(dataset_id=SST[0], variables=[SST[1]], **box)[SST[1]]
    days = np.intersect1d(c.time.values, t.time.values)[-DAYS:]
    c = c.sel(time=days).mean("time")
    t = t.sel(time=days).mean("time").sel(latitude=c.latitude, longitude=c.longitude, method="nearest") - 273.15
    la, lo = c.latitude.values, c.longitude.values
    step = float(la[1] - la[0])
    k = classify(t.values, c.values, la, step)[mercator_rows(la, step, 4 * len(la))]
    rgba = np.zeros((*k.shape, 4), np.uint8)
    for cls, colour in COLOURS.items():
        rgba[k == cls] = colour
    png(PNG, rgba)
    w, e, s, n = lo[0] - step / 2, lo[-1] + step / 2, la[0] - step / 2, la[-1] + step / 2
    return dict(fronts_dates=f"{str(days[0])[:10]} to {str(days[-1])[:10]}",
                fronts_corners=f"[[{w:.4f},{n:.4f}],[{e:.4f},{n:.4f}],[{e:.4f},{s:.4f}],[{w:.4f},{s:.4f}]]")


def test():
    # 5 x 5 grid at the equator, 0.1° (11.12 km) cells. SST rises 0.03 °C/km eastward.
    lat, step = np.arange(5) * 0.1, 0.1
    x_km = np.arange(5) * 11.12
    t = np.tile(0.03 * x_km, (5, 1))
    west = np.tile(10 ** (-0.001 * x_km), (5, 1))   # CHL rises westward: head-on
    east = np.tile(10 ** (0.001 * x_km), (5, 1))    # CHL rises eastward: same direction
    assert (classify(t, west, lat, step) == 2).all() and (classify(t, east, lat, step) == 1).all()
    assert (classify(t / 3, west, lat, step) == 0).all()   # 0.01 °C/km: no front
    # Mercator rows: north first, and the equator row sits mid-image for a box symmetric about it.
    r = mercator_rows(np.array([-1.0, 0, 1]), 1.0, 9)
    assert r[0] == 2 and r[-1] == 0 and r[4] == 1, r
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
