# Protected areas from ProtectedSeas Navigator, with per-gear rules

DESIGN story 15 asks for protected areas on the map so officers see where fishing is restricted. A protected area's name says little about its rules: in the Azores, "Costa Este" bans all fishing while "Baía do Cura" restricts none. We take sites from the ProtectedSeas Navigator all-sites layer (ArcGIS FeatureServer, CC BY 4.0, updated quarterly). Each site has a Level of Fishing Protection (1–5) and, read from its legal texts, a banned / restricted / allowed code per activity (commercial, small-scale, recreational fishing; trawl, nets, longline, hook and line, traps, spearfishing; entry, anchoring, diving). The API checks Navigator's version at most once a day and caches the Europe box as simplified GeoJSON (`backend/mpa.py`). It is a map layer only, not part of the score.

## Considered Options
- EU MPA dataset (Aminian-Biquet et al. 2024, Data in Brief, figshare): MPA Guide protection levels and per-activity regulations, but EU countries only (no UK, Norway, Iceland, Turkey) and 2022 data, not updated.
- WDPA / EEA Natura 2000 + CDDA: official boundaries, but only a coarse no-take flag (mostly "Not Reported") and no per-gear rules.
- Navigator's simplification on the server (`maxAllowableOffset`): ignores small tolerances and collapses shapes at large ones, so we simplify with shapely.

## Consequences
- 11,864 sites after dropping ocean-wide treaty areas, EEZs, ship-reporting and water-quality areas (user's choice).
- Navigator's numeric rule codes are inferred from the data, not documented (CAVEATS).
- A new quarterly version is downloaded inside the first map request of the day that sees it.
