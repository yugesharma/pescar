"""Scoring: raw factor values per harbour -> harbour score, limiting factor, income potential.

Pure, no I/O. Every judgement call lives here.
Run:  uv run python scoring.py   -> self-check
"""
import math


def score(raw: list[dict]) -> list[dict]:
    """raw: one dict per harbour with code, small_boats, places (accommodation within 10 km),
    transport_km (nearest airport or ferry terminal), viable_days (per year at 1.5 m).
    Returns the same harbours with the factors, score, limiting factor and income added."""
    def by_best(key, f=lambda v: v):  # divide by the best harbour's value: best = 1, never min-max to zero
        best = f(max(h[key] for h in raw)) or 1
        return [f(h[key]) / best for h in raw]

    # Judgement: a ferry or airport 10 km away is worth half one next door.
    closeness = [1 / (1 + h["transport_km"] / TRANSPORT_HALF_KM) for h in raw]
    best_c = max(closeness)
    out = []
    for h, b, p, c, v in zip(raw, by_best("small_boats", math.log1p), by_best("places", math.log1p), closeness, by_best("viable_days")):
        tourism = (p + c / best_c) / 2
        # Judgement: boats and places to stay count on a log scale. Boats range from 1 to 991
        # (Finnish registration districts), places from 0 to 941 (Riccione); past a few dozen,
        # more of either adds little to filling a 6-10 seat boat.
        factors = dict(community=(b + tourism) / 2, viability=v)
        # ponytail: Attractiveness and Headroom join the product in slices 4-5
        product = factors["community"] * factors["viability"]
        weakest = min(factors, key=factors.get)
        words = WORDS[weakest] if weakest != "community" else (
            "limited by few small boats" if b < tourism else "limited by tourist access")
        out.append(h | {k: round(x, 4) for k, x in factors.items()} | dict(
            boats_part=round(b, 4), tourism_part=round(tourism, 4), score=round(product, 4),
            limiting=words, income=round(h["viable_days"] * INCOME_PER_DAY)))
    return out


INCOME_PER_DAY = 500     # € per boat per trip-day (DG MARE, Greek FLAG programme)
TRANSPORT_HALF_KM = 10
WORDS = {"viability": "limited by swell"}


def test():
    a = dict(code="A", small_boats=10, places=100, transport_km=0, viable_days=200)
    b = dict(code="B", small_boats=5, places=50, transport_km=0, viable_days=100)
    A, B = score([a, b])

    # The best harbour scores 1; the weakest is scaled by the best, never to zero.
    assert (A["community"], A["viability"], A["score"]) == (1, 1, 1), A
    # B: boats log(6)/log(11) = 0.7472; places log(51)/log(101) = 0.8519, tourism (0.8519 + 1) / 2
    # = 0.926 -> community 0.8366; viability 0.5.
    assert (B["boats_part"], B["tourism_part"], B["community"], B["viability"]) == (0.7472, 0.926, 0.8366, 0.5), B
    assert B["limiting"] == "limited by swell", B
    assert B["income"] == 50_000, B  # 100 viable days x €500 per boat

    # Transport: 10 km away counts half as much as next door.
    c = dict(code="C", small_boats=10, places=100, transport_km=10, viable_days=200)
    _, C = score([a, c])
    assert C["community"] == 0.875, C  # (1 + (1 + 0.5) / 2) / 2

    # Community is limiting: name its weaker part.
    few = dict(code="F", small_boats=1, places=100, transport_km=0, viable_days=200)
    far = dict(code="T", small_boats=10, places=5, transport_km=50, viable_days=200)
    _, F, T = score([a, few, far])
    assert F["limiting"] == "limited by few small boats", F
    assert T["limiting"] == "limited by tourist access", T

    # A factor nobody has (all zero) does not divide by zero.
    z = dict(code="Z", small_boats=0, places=0, transport_km=0, viable_days=0)
    assert score([z])[0]["score"] == 0
    print("ok")


if __name__ == "__main__":
    test()
