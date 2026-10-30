"""Dark vessels: GFW radar (Sentinel-1) detections not matched to AIS, Europe, last DAYS published days (DESIGN F7).

Run:  uv run python dark.py --test  -> self-check, no network
Map overlay only, never scored. The API calls latest(); it asks GFW for a newer date at most once a day.
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

from build import EUROPE_LAT, EUROPE_LON
from community import CACHE
from pressure import token

DAYS = 7                     # one day covers only the satellite's passes; 7 days cover most coasts (chosen by the user)
DATASET = "public-global-sar-presence:latest"
GFW = "https://gateway.api.globalfishingwatch.org/v3"
DIR = CACHE / "dark"
CHECKED = DIR / "checked"    # date of the last check with GFW


def gfw(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(f"{GFW}/{path}", json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
                                          "User-Agent": "PescaMare/0.1 (Copernicus Marine hackathon)"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def last_day() -> date:
    """Last day GFW has published (the dataset's endDate is exclusive)."""
    return date.fromisoformat(gfw(f"datasets/{DATASET}")["endDate"][:10]) - timedelta(days=1)


def to_geojson(rows: list, start: date, end: date) -> dict:
    """GFW 0.1° rows (lat, lon, detections) -> point features, with the window as foreign members."""
    return {"type": "FeatureCollection", "start": start.isoformat(), "end": end.isoformat(), "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r["lon"], 2), round(r["lat"], 2)]},
         "properties": {"detections": r["detections"]}} for r in rows]}


def fetch(end: date) -> dict:
    start = end - timedelta(days=DAYS - 1)
    (s, n), (w, e) = EUROPE_LAT, EUROPE_LON
    q = urllib.parse.urlencode({"spatial-resolution": "LOW", "temporal-resolution": "ENTIRE", "format": "JSON",
                                "datasets[0]": DATASET, "filters[0]": "matched='false'",
                                "date-range": f"{start},{end + timedelta(days=1)}"})  # end exclusive
    box = [[w, s], [e, s], [e, n], [w, n], [w, s]]
    rows = next(iter(gfw(f"4wings/report?{q}", {"geojson": {"type": "Polygon", "coordinates": [box]}})["entries"][0].values()))
    return to_geojson(rows, start, end)


def latest(today: date | None = None):
    """Path of the newest cached layer. Checks GFW at most once a day; on failure keeps serving the last one."""
    today = today or date.today()
    DIR.mkdir(parents=True, exist_ok=True)
    if not CHECKED.exists() or CHECKED.read_text() != today.isoformat():
        try:
            end = last_day()
            path = DIR / f"{end}.geojson"
            if not path.exists():
                path.write_text(json.dumps(fetch(end)))
            CHECKED.write_text(today.isoformat())
        except Exception as e:  # GFW down: the last layer is still correct for its own dates
            print("dark vessels: GFW check failed:", e, flush=True)
    files = sorted(DIR.glob("*.geojson"))
    if not files:
        raise FileNotFoundError("no dark-vessel layer yet and GFW unreachable")
    return files[-1]


def test():
    global DIR, CHECKED, last_day, fetch
    import tempfile
    from pathlib import Path
    g = to_geojson([{"lat": 38.7, "lon": -27.2, "detections": 3}], date(2026, 10, 21), date(2026, 10, 27))
    assert g["features"][0]["geometry"]["coordinates"] == [-27.2, 38.7] and g["start"] == "2026-10-21", g
    DIR = Path(tempfile.mkdtemp()); CHECKED = DIR / "checked"
    calls = []
    last_day = lambda: calls.append(1) or date(2026, 10, 27)
    fetch = lambda end: to_geojson([], end - timedelta(days=DAYS - 1), end)
    assert latest(date(2026, 10, 30)).name == "2026-10-27.geojson"
    latest(date(2026, 10, 30))
    assert len(calls) == 1, "checks GFW once a day"
    last_day = lambda: 1 / 0  # GFW down next day: keep serving the old layer
    assert latest(date(2026, 10, 31)).name == "2026-10-27.geojson"
    assert json.loads((DIR / "2026-10-27.geojson").read_text())["start"] == "2026-10-21"
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
