"""Protected areas: ProtectedSeas Navigator sites in the Europe box, with fishing protection level and rules (ADR-0010).

Run:  uv run python mpa.py --test  -> self-check, no network
Map overlay only, never scored. The API calls latest(); it asks Navigator for a newer version at most once a day.
A new version (quarterly) takes a few minutes to download, inside that one request.
"""
import gzip
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from build import EUROPE_LAT, EUROPE_LON
from community import CACHE
from shapely.geometry import mapping, shape

LAYER = ("https://services9.arcgis.com/lm7wE8a9YA9rKfzy/ArcGIS/rest/services/"
         "Navigator_AllSites_010925_attributes/FeatureServer/0")  # service name is old; the data is the quarterly version
# Ocean-wide treaty areas, EEZs, ship-reporting and water-quality areas would cover everything (chosen by the user).
WHERE = ("category_name NOT IN ('Jurisdictional Authority Area','Vessel Reporting Area','Water Quality/Human Health Area')"
         " AND (designation IS NULL OR designation NOT LIKE 'Convention Area%') AND total_area < 5000000")
SIMPLIFY_DEG = 0.001  # outline tolerance, ~100 m; 160 MB -> 39 MB, 9 MB gzipped. Done here: the service's maxAllowableOffset
                      # ignores small values and collapses shapes at large ones.
PAGE = 2000        # the service's maxRecordCount
# Navigator activity fields shown in the popup. Codes: 1 banned, 2 restricted, 3 allowed, 0 not known.
RULES = [("commercial_fishing", "Commercial fishing"), ("artisanal_fishing", "Small-scale fishing"),
         ("recreational_fishing", "Recreational fishing"), ("bottom_trawling", "Bottom trawl"),
         ("pelagic_trawling", "Midwater trawl"), ("dredges", "Dredge"), ("purse_seine_rndhaul_surrd_nets", "Purse seine"),
         ("gillnetting", "Gillnet"), ("nets", "Other nets"), ("longlining", "Longline"), ("hook_and_line", "Hook and line"),
         ("trolling", "Trolling"), ("traps_and_pots", "Traps and pots"), ("spear_fishing", "Spearfishing"),
         ("hand_capture", "Hand capture"), ("entry", "Entry"), ("anchoring", "Anchoring"), ("diving", "Diving")]
FIELDS = ["site_id", "site_name", "designation", "country", "lfp", "season", "navigator_link", "last_reviewed"]
DIR = CACHE / "mpa"
CHECKED = DIR / "checked"  # date of the last check with Navigator


def get(url: str, params: dict) -> dict:
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}",
                                 headers={"User-Agent": "PescaMare/0.1 (Copernicus Marine hackathon)"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def version() -> str:
    """Date of Navigator's last data edit, e.g. '2026-09-09'."""
    ms = get(LAYER, {"f": "json"})["editingInfo"]["dataLastEditDate"]
    return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()


def compact(p: dict) -> dict:
    """Navigator attributes -> the few the popup needs; rules as one digit per RULES entry."""
    return {"name": (p["site_name"] or "").strip(), "designation": p["designation"], "country": p["country"],
            "lfp": p["lfp"] or 0, "season": p["season"], "link": p["navigator_link"], "reviewed": p["last_reviewed"],
            "rules": "".join(str(p.get(k) or 0) for k, _ in RULES)}


def simplify(g: dict) -> dict:
    """Simplified outline, coordinates rounded to 4 decimals (~10 m)."""
    r = lambda c: [round(c[0], 4), round(c[1], 4)] if isinstance(c[0], float) else [r(x) for x in c]
    s = mapping(shape(g).simplify(SIMPLIFY_DEG))
    return {"type": s["type"], "coordinates": r(s["coordinates"])}


def fetch(ver: str) -> dict:
    (s, n), (w, e) = EUROPE_LAT, EUROPE_LON
    feats, offset = [], 0
    while True:
        page = get(f"{LAYER}/query", {
            "where": WHERE, "geometry": f"{w},{s},{e},{n}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
            "outSR": 4326, "geometryPrecision": 5, "orderByFields": "OBJECTID",
            "outFields": ",".join(FIELDS + [k for k, _ in RULES]), "resultOffset": offset, "resultRecordCount": PAGE,
            "f": "geojson"})
        feats += [{"type": "Feature", "geometry": simplify(f["geometry"]), "properties": compact(f["properties"])}
                  for f in page["features"] if f["geometry"]]
        if not page.get("properties", {}).get("exceededTransferLimit"):
            break
        offset += PAGE
    # Stricter areas last, so they draw on top where areas overlap.
    feats.sort(key=lambda f: f["properties"]["lfp"])
    return {"type": "FeatureCollection", "version": ver, "rules": [label for _, label in RULES], "features": feats}


def latest(today: date | None = None):
    """Path of the newest cached layer. Checks Navigator at most once a day; on failure keeps serving the last one."""
    today = today or date.today()
    DIR.mkdir(parents=True, exist_ok=True)
    if not CHECKED.exists() or CHECKED.read_text() != today.isoformat():
        try:
            ver = version()
            path = DIR / f"{ver}.geojson.gz"
            if not path.exists():  # stored gzipped: the API sends it as is
                path.write_bytes(gzip.compress(json.dumps(fetch(ver), separators=(",", ":")).encode()))
            CHECKED.write_text(today.isoformat())
        except Exception as e:  # Navigator down: the last version is still the latest we know
            print("protected areas: Navigator check failed:", e, flush=True)
    files = sorted(DIR.glob("*.geojson.gz"))
    if not files:
        raise FileNotFoundError("no protected-area layer yet and Navigator unreachable")
    return files[-1]


def test():
    global DIR, CHECKED, version, fetch
    import tempfile
    from pathlib import Path
    p = {"site_name": "Formigas\n", "designation": "Marine Nature Reserve", "country": "Portugal", "lfp": 5,
         "season": "Year-round", "navigator_link": "x", "last_reviewed": "2025-01-31", "commercial_fishing": 1,
         "recreational_fishing": 2, "diving": 3}
    c = compact(p)
    assert c["name"] == "Formigas" and c["rules"][:3] == "102" and c["rules"][-1] == "3" and len(c["rules"]) == len(RULES), c
    assert compact({**p, "lfp": None})["lfp"] == 0
    ring = [[0.0, 0.0], [0.5, 0.00001], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
    s = simplify({"type": "Polygon", "coordinates": [ring]})
    assert s["type"] == "Polygon" and len(s["coordinates"][0]) == 5 and s["coordinates"][0][0] == [0.0, 0.0], s
    DIR = Path(tempfile.mkdtemp()); CHECKED = DIR / "checked"
    calls = []
    version = lambda: calls.append(1) or "2026-09-09"
    fetch = lambda ver: {"type": "FeatureCollection", "version": ver, "rules": [], "features": []}
    assert latest(date(2026, 10, 30)).name == "2026-09-09.geojson.gz"
    latest(date(2026, 10, 30))
    assert len(calls) == 1, "checks Navigator once a day"
    version = lambda: 1 / 0  # Navigator down next day: keep serving the old layer
    assert latest(date(2026, 10, 31)).name == "2026-09-09.geojson.gz"
    assert json.loads(gzip.decompress(latest(date(2026, 10, 31)).read_bytes()))["version"] == "2026-09-09"
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        print(latest())
