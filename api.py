"""API over data/pescamare.db.

Run:  uv run uvicorn api:app --reload
"""
import sqlite3

from fastapi import FastAPI, HTTPException

from build import DB
from waves import LIMITS, status

app = FastAPI(title="PescaMare")


def rows(sql, *args):
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, args)]


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
    rank = rows("SELECT COUNT(*) + 1 AS r FROM harbours WHERE score > ?", found[0]["score"])[0]["r"]
    return found[0] | {
        "rank": rank, "of": rows("SELECT COUNT(*) AS n FROM harbours")[0]["n"],
        "weekly": rows("SELECT week, viability FROM viability_weekly WHERE code = ? AND limit_m = ? ORDER BY week",
                       code, limit),
        "trips": [r | {"status": status(r["worst_hs_m"], limit)}
                  for r in rows("SELECT date, worst_hs_m FROM forecast WHERE code = ? ORDER BY date", code)],
    }
