"""API over data/pescamare.db (read-only, rebuilt by build.py) and data/user.db (proposals, validations).

Run:   uv run uvicorn api:app
Test:  uv run python api.py --test   -> in-process requests against a temporary user.db
Demo:  uv run python api.py --demo   -> seed two harbours with generated trips, flagged demo
"""
import datetime
import random
import re
import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import dark
import mpa
from build import DB
from fronts import PNG
from scoring import trip_cap
from waves import LIMITS, status

app = FastAPI(title="PescaMare")


def rows(sql, *args):
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, args)]


# User writes live apart from the build output: build.py replaces pescamare.db whole.
USER_DB = DB.parent / "user.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, code TEXT NOT NULL, boats INTEGER NOT NULL,
  training INTEGER NOT NULL, budget REAL NOT NULL, target INTEGER NOT NULL, notes TEXT NOT NULL, created TEXT NOT NULL,
  demo INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS validations (code TEXT PRIMARY KEY, date TEXT NOT NULL, boats INTEGER NOT NULL,
  demo INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, code TEXT NOT NULL, date TEXT NOT NULL, boat TEXT NOT NULL,
  passengers INTEGER NOT NULL, replaced INTEGER NOT NULL, demo INTEGER NOT NULL DEFAULT 0);
"""


def user(sql, *args):
    con = sqlite3.connect(USER_DB)
    try:
        with con:
            con.executescript(SCHEMA)
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


class Proposal(BaseModel):
    boats: int = Field(ge=1, le=1000)          # boats to license
    training: int = Field(ge=0, le=10_000)     # training places
    budget: float = Field(ge=0, le=1e9)        # €
    target: int = Field(ge=0, le=10_000)       # trips per week
    notes: str = Field("", max_length=2000)


class Validation(BaseModel):
    date: datetime.date
    boats: int = Field(ge=1, le=1000)          # licensed boats; feeds the Monitor cap


class Trip(BaseModel):
    date: datetime.date
    boat: str = Field(min_length=1, max_length=100)
    passengers: int = Field(ge=1, le=50)
    replaced: bool                             # the boat would otherwise have gone commercial fishing that day


def check(limit):
    if limit not in LIMITS:
        raise HTTPException(422, f"limit must be one of {LIMITS}")


@app.get("/api/harbours")
def harbours(limit: float = 1.5):
    """Every placed harbour, without per-week or forecast rows (see /api/harbours/{code})."""
    check(limit)
    meta = {r["key"]: r["value"] for r in rows("SELECT * FROM meta")}
    return {"limit_m": limit, "meta": meta, "harbours": rows(
        "SELECT h.code, h.name, h.cc, h.region, h.region_name, h.lat, h.lon, h.pilot, h.score, h.limiting, d.per_year AS viable_days "
        "FROM harbours h JOIN viable_days d USING (code) WHERE d.limit_m = ? ORDER BY h.score DESC", limit)}


@app.get("/api/harbours/{code}")
def harbour(code: str, limit: float = 1.5):
    check(limit)
    found = rows("SELECT h.*, d.per_year AS viable_days, d.shoulder AS shoulder_days "
                 "FROM harbours h JOIN viable_days d USING (code) WHERE code = ? AND d.limit_m = ?", code, limit)
    if not found:
        raise HTTPException(404, f"no harbour {code}")
    h = found[0]
    rank = rows("SELECT COUNT(*) + 1 AS r FROM harbours WHERE score > ?", h["score"])[0]["r"]
    weekly = rows("SELECT week, viability FROM viability_weekly WHERE code = ? AND limit_m = ? ORDER BY week", code, limit)
    caps = lambda boats: [None if h["headroom"] is None else trip_cap(boats, 7 * w["viability"], h["headroom"]) for w in weekly]
    proposals = [p | {"income": h["income"] * p["boats"], "caps": c,
                      "over_weeks": [w["week"] for w, cap in zip(weekly, c) if cap is not None and p["target"] > cap]}
                 for p in user("SELECT * FROM proposals WHERE code = ? ORDER BY id DESC", code) for c in [caps(p["boats"])]]
    validation = (user("SELECT date, boats FROM validations WHERE code = ?", code) or [None])[0]
    active = bool(user("SELECT 1 FROM trips WHERE code = ? LIMIT 1", code))
    return h | {
        "rank": rank, "of": rows("SELECT COUNT(*) AS n FROM harbours")[0]["n"],
        "state": "Active" if active else "Validated" if validation else "Proposed" if proposals else "Candidate",
        "proposals": proposals, "validation": validation,
        "weekly": [w | {"trip_cap": c} for w, c in zip(weekly, caps(1))],  # trip cap for one licensed boat
        "species": rows("SELECT s.name, s.scientific, s.status, s.source, s.year, s.target, AVG(x.share) AS share "
                        "FROM species s LEFT JOIN habitat x ON x.species = s.name AND x.code = ? WHERE s.region = ? GROUP BY s.name "
                        "ORDER BY s.target DESC, CASE s.status WHEN 'Overfished' THEN 0 WHEN 'Unknown' THEN 1 ELSE 2 END, s.name",
                        code, h["region"]),
        "trips": [r | {"status": status(r["worst_hs_m"], limit)}
                  for r in rows("SELECT date, worst_hs_m FROM forecast WHERE code = ? ORDER BY date", code)],
    }


def exists(code):
    if not rows("SELECT 1 FROM harbours WHERE code = ?", code):
        raise HTTPException(404, f"no harbour {code}")


@app.post("/api/harbours/{code}/proposals", status_code=201)
def propose(code: str, p: Proposal):
    exists(code)
    user("INSERT INTO proposals (code, boats, training, budget, target, notes, created) VALUES (?, ?, ?, ?, ?, ?, ?)",
         code, p.boats, p.training, p.budget, p.target, p.notes.strip(), datetime.date.today().isoformat())
    return {"ok": True}


@app.post("/api/harbours/{code}/validation", status_code=201)
def validate(code: str, v: Validation):
    """Proposed -> Validated. Only once per harbour."""
    exists(code)
    if not user("SELECT 1 FROM proposals WHERE code = ?", code):
        raise HTTPException(409, "only a Proposed harbour (one with a proposal) can be Validated")
    if user("SELECT 1 FROM validations WHERE code = ?", code):
        raise HTTPException(409, "already Validated")
    user("INSERT INTO validations (code, date, boats) VALUES (?, ?, ?)", code, v.date.isoformat(), v.boats)
    return {"ok": True}


@app.post("/api/harbours/{code}/trips", status_code=201)
def log_trip(code: str, t: Trip):
    exists(code)
    v = user("SELECT date FROM validations WHERE code = ?", code)
    if not v:
        raise HTTPException(409, "only a Validated harbour can log trips")
    if not v[0]["date"] <= t.date.isoformat() <= datetime.date.today().isoformat():
        raise HTTPException(422, "trip date must be between the validation date and today")
    user("INSERT INTO trips (code, date, boat, passengers, replaced) VALUES (?, ?, ?, ?, ?)",
         code, t.date.isoformat(), t.boat.strip(), t.passengers, int(t.replaced))
    return {"ok": True}


def weekly_viability(code, limit):
    """ISO week -> share of viable days; week 53 (missing in some years' data) falls back to the last week."""
    via = {r["week"]: r["viability"] for r in rows(
        "SELECT week, viability FROM viability_weekly WHERE code = ? AND limit_m = ?", code, limit)}
    return lambda d: via.get(d.isocalendar().week, via[max(via)])


@app.get("/api/monitor")
def monitor(limit: float = 1.5):
    """Validated and Active harbours: uptake, replaced vs added days, trips per week vs the trip cap."""
    check(limit)
    out, today = [], datetime.date.today()
    for v in user("SELECT * FROM validations ORDER BY date"):
        h = rows("SELECT code, name, headroom FROM harbours WHERE code = ?", v["code"])[0]
        via = weekly_viability(v["code"], limit)
        trips = user("SELECT date, replaced, demo FROM trips WHERE code = ?", v["code"])
        start = datetime.date.fromisoformat(v["date"])
        days = [start + datetime.timedelta(i) for i in range((today - start).days + 1)]
        # Typical calm boat-days since validation, from the weekly averages (not the actual days).
        expected = v["boats"] * sum(via(d) for d in days)
        monday = lambda d: d - datetime.timedelta(d.weekday())
        weeks = dict.fromkeys(sorted({monday(d) for d in days}), 0)
        for t in trips:
            weeks[monday(datetime.date.fromisoformat(t["date"]))] += 1
        weekly = [dict(start=m.isoformat(), trips=n,
                       cap=None if h["headroom"] is None else trip_cap(v["boats"], 7 * via(m), h["headroom"]))
                  for m, n in weeks.items()]
        replaced = sum(t["replaced"] for t in trips)
        out.append(h | dict(state="Active" if trips else "Validated", validated=v["date"], boats=v["boats"],
                            demo=bool(v["demo"] or any(t["demo"] for t in trips)), trips=len(trips),
                            replaced=replaced, added=len(trips) - replaced, expected_days=round(expected, 1),
                            used=round(len(trips) / expected, 4) if expected else None, weekly=weekly,
                            over_weeks=sum(w["cap"] is not None and w["trips"] > w["cap"] for w in weekly)))
    return {"limit_m": limit, "harbours": out}


# Demo data: one harbour where trips mostly replace fishing days, one where they mostly add to them (rebound).
# Judgement (demo only): validated 1 Apr 2026 with 2 boats; each boat sails on a day with probability
# typical viability x uptake; replaced with the given probability; 2-6 passengers.
DEMO = [dict(code="PTPDL", uptake=0.45, replaced=0.8), dict(code="PTVFC", uptake=0.9, replaced=0.25)]
DEMO_START, DEMO_BOATS = datetime.date(2026, 4, 1), 2


def seed_demo(today=None):
    today = today or datetime.date.today()
    rng = random.Random(1)
    for d in DEMO:
        code = d["code"]
        if user("SELECT 1 FROM validations WHERE code = ? AND demo = 0", code):
            print(f"{code}: has a real validation, left alone"); continue
        for table in ("proposals", "validations", "trips"):
            user(f"DELETE FROM {table} WHERE code = ? AND demo = 1", code)
        user("INSERT INTO proposals (code, boats, training, budget, target, notes, created, demo) VALUES (?, ?, 4, 40000, 6, 'demo data', ?, 1)",
             code, DEMO_BOATS, (DEMO_START - datetime.timedelta(30)).isoformat())
        user("INSERT INTO validations (code, date, boats, demo) VALUES (?, ?, ?, 1)", code, DEMO_START.isoformat(), DEMO_BOATS)
        via = weekly_viability(code, 1.5)
        n, day = 0, DEMO_START
        while day < today:
            for boat in range(1, DEMO_BOATS + 1):
                if rng.random() < via(day) * d["uptake"]:
                    user("INSERT INTO trips (code, date, boat, passengers, replaced, demo) VALUES (?, ?, ?, ?, ?, 1)",
                         code, day.isoformat(), f"Boat {boat}", rng.randint(2, 6), int(rng.random() < d["replaced"]))
                    n += 1
            day += datetime.timedelta(1)
        print(f"{code}: {n} demo trips")


@app.get("/api/layers/fronts/{region}.png")
def fronts(region: str):
    """SST/chlorophyll fronts image for one pilot region; corners and dates are in /api/harbours meta."""
    path = Path(PNG.format(region))
    if not re.fullmatch(r"[A-Z]{2}[0-9A-Z]{2}", region) or not path.exists():
        raise HTTPException(404, f"no fronts image for {region}")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})


@app.get("/api/layers/dark.geojson")
def dark_vessels():
    """GFW radar detections without AIS, last 7 published days; window in the top-level start/end."""
    return FileResponse(dark.latest(), media_type="application/geo+json", headers={"Cache-Control": "no-cache"})


@app.get("/api/layers/mpa.geojson")
def protected_areas():
    """ProtectedSeas Navigator sites, Europe; version date and rule labels in the top-level version/rules. Stored gzipped."""
    return FileResponse(mpa.latest(), media_type="application/geo+json",
                        headers={"Cache-Control": "no-cache", "Content-Encoding": "gzip"})


def test():
    import tempfile
    from pathlib import Path

    from fastapi.testclient import TestClient
    global USER_DB
    USER_DB = Path(tempfile.mkdtemp()) / "user.db"
    c = TestClient(app)
    pilot = rows("SELECT code FROM harbours WHERE pilot = 1 LIMIT 1")[0]["code"]
    other = rows("SELECT code FROM harbours WHERE pilot = 0 LIMIT 1")[0]["code"]
    get = lambda code: c.get(f"/api/harbours/{code}").json()

    h = get(pilot)
    assert h["state"] == "Candidate" and h["proposals"] == [] and h["validation"] is None, h["state"]
    assert c.post(f"/api/harbours/{pilot}/validation", json=dict(date="2026-10-30", boats=2)).status_code == 409
    assert c.post(f"/api/harbours/{pilot}/proposals", json=dict(boats=0, training=0, budget=0, target=1)).status_code == 422
    assert c.post("/api/harbours/NOPE/proposals", json=dict(boats=1, training=0, budget=0, target=1)).status_code == 404

    # A target nobody can reach is over the cap every week; zero never is.
    for target in (10_000, 0):
        r = c.post(f"/api/harbours/{pilot}/proposals", json=dict(boats=2, training=4, budget=50_000, target=target, notes=" x "))
        assert r.status_code == 201, r.text
    h = get(pilot)
    zero, high = h["proposals"]  # newest first
    assert h["state"] == "Proposed" and len(high["over_weeks"]) == len(h["weekly"]) and zero["over_weeks"] == [], h
    assert high["income"] == 2 * h["income"] and high["notes"] == "x", high
    w = h["weekly"][0]
    assert high["caps"][0] == trip_cap(2, 7 * w["viability"], h["headroom"]), high["caps"][0]

    assert c.post(f"/api/harbours/{pilot}/validation", json=dict(date="2026-10-30", boats=2)).status_code == 201
    assert c.post(f"/api/harbours/{pilot}/validation", json=dict(date="2026-10-31", boats=3)).status_code == 409
    h = get(pilot)
    assert h["state"] == "Validated" and h["validation"] == dict(date="2026-10-30", boats=2), h["validation"]

    # Trips: only once Validated, dated between validation and today; the first makes the harbour Active.
    trip = dict(date=datetime.date.today().isoformat(), boat="Boat 1", passengers=4, replaced=True)
    assert c.post(f"/api/harbours/{other}/trips", json=trip).status_code == 409  # Candidate
    assert c.post(f"/api/harbours/{pilot}/trips", json=trip | dict(date="2026-10-29")).status_code == 422
    assert c.post(f"/api/harbours/{pilot}/trips", json=trip | dict(passengers=0)).status_code == 422
    for replaced in (True, True, False):
        assert c.post(f"/api/harbours/{pilot}/trips", json=trip | dict(replaced=replaced)).status_code == 201
    assert get(pilot)["state"] == "Active"
    m = c.get("/api/monitor").json()["harbours"]
    assert len(m) == 1 and m[0]["code"] == pilot, m
    m = m[0]
    assert (m["state"], m["trips"], m["replaced"], m["added"], m["boats"], m["demo"]) == ("Active", 3, 2, 1, 2, False), m
    # 3 trips in under a day of typical calm boat-days: more than 100% used.
    assert 0 < m["expected_days"] < 3 and m["used"] > 1, m
    week = m["weekly"][-1]
    assert week["trips"] == 3 and m["over_weeks"] == int(week["trips"] > week["cap"]), m["weekly"]

    # Demo seed: both harbours with trips, flagged demo; reseeding replaces rather than doubles.
    seed_demo(datetime.date(2026, 10, 30)); first = c.get("/api/monitor").json()["harbours"]
    seed_demo(datetime.date(2026, 10, 30)); again = c.get("/api/monitor").json()["harbours"]
    demo = {x["code"]: x for x in again if x["demo"]}
    assert set(demo) == {"PTPDL", "PTVFC"} and [x["trips"] for x in first] == [x["trips"] for x in again], again
    good, rebound = demo["PTPDL"], demo["PTVFC"]
    assert good["replaced"] > good["added"] and rebound["added"] > rebound["replaced"], (good, rebound)
    assert rebound["over_weeks"] > good["over_weeks"], (good["over_weeks"], rebound["over_weeks"])

    # No Headroom outside the pilot: no cap, so no weeks over it.
    c.post(f"/api/harbours/{other}/proposals", json=dict(boats=1, training=0, budget=0, target=10_000))
    p = get(other)["proposals"][0]
    assert p["caps"][0] is None and p["over_weeks"] == [], p
    print("ok")


if __name__ == "__main__" and "--test" in sys.argv:
    test()
if __name__ == "__main__" and "--demo" in sys.argv:
    seed_demo()
