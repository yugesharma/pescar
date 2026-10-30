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


@app.get("/api/harbours")
def harbours(limit: float = 1.5):
    if limit not in LIMITS:
        raise HTTPException(422, f"limit must be one of {LIMITS}")
    out = {h["code"]: h | {"weekly": [], "trips": []} for h in rows(
        "SELECT h.*, d.per_year AS viable_days, d.shoulder AS shoulder_days "
        "FROM harbours h JOIN viable_days d USING (code) WHERE d.limit_m = ?", limit)}
    for r in rows("SELECT code, week, viability FROM viability_weekly WHERE limit_m = ? ORDER BY week", limit):
        out[r.pop("code")]["weekly"].append(r)
    for r in rows("SELECT * FROM forecast ORDER BY date"):
        out[r["code"]]["trips"].append(r | {"status": status(r["worst_hs_m"], limit)})
    meta = {r["key"]: r["value"] for r in rows("SELECT * FROM meta")}
    return {"limit_m": limit, "meta": meta, "harbours": list(out.values())}
