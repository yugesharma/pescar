# Local pressure from Global Fishing Watch AIS effort; Headroom never zero

The design took local pressure from EMODnet static-gear fishing hours (ICES VMS). Checked on 30 Oct 2026, its latest Azores edition (2025, average 2021–24) has no cell within 6 nm of 9 of the 11 pilot harbours; Horta holds almost all of what there is. ICES withholds cells with few vessels, so EMODnet cannot tell the pilot harbours apart. Global Fishing Watch apparent fishing effort (AIS, 2025, 0.01°) has hours near 9 of 11 harbours, from 0 (Angra do Heroísmo) to ~490 h (Vila Franca do Campo). We score local pressure from GFW and keep EMODnet as a map layer.

Headroom was 1 − hours ÷ the highest harbour's hours, which always gives the busiest harbour Headroom 0 and a harbour score of 0. We use Headroom = 1 / (1 + hours / 100 h) instead, the same shape as transport closeness: 100 fishing hours a year in the trip area halve Headroom, and no harbour reaches zero.

## Consequences
- Hours within 2 km of the harbour point are dropped: AIS "fishing" next to port is mostly mooring or manoeuvring (125 of 616 h at Vila Franca).
- AIS misses most boats under ~15 m, so pressure is underestimated; at some harbours one vessel holds most of the hours (61% at Vila Franca).
- GFW covers the Mediterranean too, which opens a path to Headroom outside the pilot.
- The stock penalty (slice 5) still multiplies local pressure: Headroom = 1 / (1 + hours × stock penalty / 100 h).
