"""Scoring: raw factor values per harbour -> harbour score, limiting factor, income potential, trip cap.

Pure, no I/O. Every judgement call lives here.
Run:  uv run python scoring.py   -> self-check
"""
import math


def score(raw: list[dict]) -> list[dict]:
    """raw: one dict per harbour with code, small_boats, places (accommodation within 10 km),
    transport_km (nearest airport or ferry terminal), viable_days (per year at 1.5 m),
    nights_per_resident (guest nights a year per resident of the municipality) or None outside the pilot, and
    fishing_hours (AIS, 6 nm ring) or None where pressure data does not exist yet (partial score), and for
    pilot harbours habitat_share (target species' habitat share of the trip area, mean over months) and
    stock_shares ([(status, habitat share)] for every species in the table).
    Returns the same harbours with the factors, score, limiting factor and income added."""
    def by_best(key, f=lambda v: v):  # divide by the best harbour's value: best = 1, never min-max to zero
        best = f(max(h[key] for h in raw)) or 1
        return [f(h[key]) / best for h in raw]

    best_a = max(h.get("habitat_share") or 0 for h in raw) or 1
    out = []
    for h, b, v in zip(raw, by_best("small_boats", math.log1p), by_best("viable_days")):
        # Judgement: boats count on a log scale (1 to 991, Finnish registration districts); past a few
        # dozen, more adds little to filling a 6-10 seat boat.
        fit = tourism_fit(h["places"], h["transport_km"], h.get("nights_per_resident"))
        factors, extra = dict(community=b, viability=v, tourism_fit=math.prod(fit.values())), {}
        if h.get("fishing_hours") is not None:
            # Judgement: 100 fishing hours a year in the trip area halve Headroom; never zero, and
            # not relative to the busiest harbour (that would always zero its score).
            penalty = stock_penalty(h.get("stock_shares") or [])
            factors["headroom"] = 1 / (1 + h["fishing_hours"] * penalty / HEADROOM_HALF_H)
            extra["stock_penalty"] = round(penalty, 4)
        if h.get("habitat_share") is not None:
            factors["attractiveness"] = h["habitat_share"] / best_a
        # Geometric mean (ADR-0012): five factors below 1 multiply to tiny numbers, and harbours with
        # fewer factors (partial score) would otherwise beat pilot harbours.
        product = math.prod(factors.values()) ** (1 / len(factors))
        weakest = min(factors, key=factors.get)
        words = WORDS[min(fit, key=fit.get) if weakest == "tourism_fit" else weakest]
        out.append({k: x for k, x in h.items() if k != "stock_shares"} | extra | {k: round(x, 4) for k, x in factors.items()} | dict(
            {k: round(x, 4) for k, x in fit.items()}, band=band(h.get("nights_per_resident")), score=round(product, 4),
            limiting=words, income=round(h["viable_days"] * INCOME_PER_DAY)))
    return out


INCOME_PER_DAY = 500     # € per boat per trip-day (DG MARE, Greek FLAG programme)
TRANSPORT_HALF_KM = 10  # 10 km past REACH_KM halves Reachable
REACH_KM = 5            # full Reachable credit up to here
VISITOR_FLOOR = 10      # places to stay within 10 km for full Enough-visitors credit
CROWD_HALF = 20         # guest nights per resident a year that halve Not crowded
BANDS = [(10, "Under-visited"), (50, "Balanced"), (150, "Busy"), (math.inf, "Crowded")]
HEADROOM_HALF_H = 100    # AIS fishing hours / year within 6 nm
WORDS = {"community": "limited by few small boats", "viability": "limited by swell",
         "enough_visitors": "limited by few places to stay", "reachable": "limited by tourist access",
         "not_crowded": "limited by crowding", "headroom": "limited by fishing pressure",
         "attractiveness": "limited by fish habitat"}
STATUS_WEIGHT = {"Overfished": 1.0, "Unknown": 0.7, "Healthy": 0.4}


def tourism_fit(places: int, transport_km: float, nights_per_resident: float | None) -> dict:
    """Tourism fit parts (ADR-0011), fixed scales, never divided by the best harbour. Not crowded only
    where municipal nights exist (pilot harbours)."""
    parts = dict(enough_visitors=min(1, places / VISITOR_FLOOR),
                 reachable=1 / (1 + max(0, transport_km - REACH_KM) / TRANSPORT_HALF_KM))
    if nights_per_resident is not None:
        parts["not_crowded"] = 1 / (1 + nights_per_resident / CROWD_HALF)
    return parts


def band(nights_per_resident: float | None) -> str | None:
    return None if nights_per_resident is None else next(n for top, n in BANDS if nights_per_resident < top)


def stock_penalty(shares: list[tuple[str, float]]) -> float:
    """Status weights averaged by each species' habitat share of the trip area (ADR-0003): 0.4-1.
    Judgement: no habitat of any listed species -> 1 (precautionary)."""
    total = sum(s for _, s in shares)
    return sum(STATUS_WEIGHT[st] * s for st, s in shares) / total if total else 1.0


CAP_SHARE = 5        # 1 in 5 registered small boats may switch to pescatourism (user, 31 Oct 2026)
CAP_MAX_BOATS = 10   # and never more than 10 per harbour


def cap_boats(small_boats: int) -> int:
    """Boats the harbour's trip cap is sized for: fixed per harbour, never from a proposal."""
    return max(1, min(CAP_MAX_BOATS, math.ceil(small_boats / CAP_SHARE)))


def trip_cap(boats: int, viable_days_week: float, headroom: float) -> int:
    """Most trips per week: licensed boats x viable days that week x Headroom, rounded down."""
    return math.floor(boats * viable_days_week * headroom + 1e-9)  # 1e-9: 0.1 * 3 * 10 is 2.9999...


def test():
    a = dict(code="A", small_boats=10, places=100, transport_km=0, viable_days=200)
    b = dict(code="B", small_boats=5, places=50, transport_km=0, viable_days=100)
    A, B = score([a, b])

    # The best harbour scores 1; the weakest is scaled by the best, never to zero.
    assert (A["community"], A["viability"], A["score"]) == (1, 1, 1), A
    # B: boats log(6)/log(11) = 0.7472 (Community = boats only); viability 0.5.
    assert (B["community"], B["viability"], B["tourism_fit"]) == (0.7472, 0.5, 1), B
    assert B["limiting"] == "limited by swell", B
    assert B["income"] == 50_000, B  # 100 viable days x €500 per boat

    # Tourism fit: full credit from 10 places and within 5 km; 17 km -> 1 / 2.2; 20 nights per resident halve it.
    assert tourism_fit(5, 17, None) == dict(enough_visitors=0.5, reachable=1 / 2.2)
    assert tourism_fit(10, 5, 20)["not_crowded"] == 0.5 and tourism_fit(500, 0, 0) == dict(enough_visitors=1, reachable=1, not_crowded=1)
    assert [band(x) for x in (3.6, 10, 29, 58, 150, 315, None)] == [
        "Under-visited", "Balanced", "Balanced", "Busy", "Crowded", "Crowded", None]
    crowded = a | dict(code="K", nights_per_resident=180)  # Not crowded 0.1, a fixed scale
    _, K = score([a, crowded])
    assert (K["tourism_fit"], K["band"], K["limiting"]) == (0.1, "Crowded", "limited by crowding"), K
    few = dict(code="F", small_boats=1, places=100, transport_km=0, viable_days=200)
    far = dict(code="T", small_boats=10, places=100, transport_km=45, viable_days=200)
    _, F, T = score([a, few, far])
    assert F["limiting"] == "limited by few small boats", F
    assert T["limiting"] == "limited by tourist access" and T["reachable"] == 0.2, T

    # A factor nobody has (all zero) does not divide by zero.
    z = dict(code="Z", small_boats=0, places=0, transport_km=0, viable_days=0)
    assert score([z])[0]["score"] == 0

    # Headroom: only where fishing hours exist; 100 h halves it and joins the geometric mean (0.25 ** (1/4)).
    calm, busy = a | dict(code="Q", fishing_hours=0), a | dict(code="P", fishing_hours=300)
    A, Q, P = score([a, calm, busy])
    assert "headroom" not in A and Q["headroom"] == 1 and P["headroom"] == 0.25, P
    assert P["score"] == 0.7071 and P["limiting"] == "limited by fishing pressure", P

    # Stock penalty: weighted by habitat share; overfished-fish habitat nearby raises it, none -> 1.
    assert stock_penalty([("Overfished", 0.5), ("Healthy", 0.5)]) == 0.7
    assert stock_penalty([("Overfished", 0.1), ("Healthy", 0.9)]) < stock_penalty([("Overfished", 0.9), ("Healthy", 0.1)])
    assert stock_penalty([]) == stock_penalty([("Healthy", 0)]) == 1
    # Headroom falls as the penalty rises: 100 h at penalty 0.4 -> 1 / 1.4.
    mild = a | dict(code="M", fishing_hours=100, stock_shares=[("Healthy", 1)])
    harsh = a | dict(code="H", fishing_hours=100, stock_shares=[("Overfished", 1)])
    _, M, H = score([a, mild, harsh])
    assert (M["headroom"], H["headroom"], M["stock_penalty"]) == (0.7143, 0.5, 0.4) and "stock_shares" not in M, M

    # Attractiveness: divided by the best harbour's habitat share; joins the geometric mean.
    good, poor = a | dict(code="G", habitat_share=0.4), a | dict(code="W", habitat_share=0.1)
    _, G, W = score([a, good, poor])
    assert (G["attractiveness"], W["attractiveness"], W["score"]) == (1, 0.25, 0.7071), W
    assert W["limiting"] == "limited by fish habitat" and "attractiveness" not in _, W

    # Trip cap: rounded down.
    assert [cap_boats(n) for n in (0, 1, 9, 10, 11, 262)] == [1, 1, 2, 2, 3, 10]
    assert trip_cap(3, 7 * 0.5, 0.5) == 5 and trip_cap(10, 3, 0.1) == 3 and trip_cap(1, 0, 1) == 0
    print("ok")


if __name__ == "__main__":
    test()
