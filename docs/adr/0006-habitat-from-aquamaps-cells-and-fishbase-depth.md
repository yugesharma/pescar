# Habitat from AquaMaps occurrence-cell temperatures and FishBase depth; chlorophyll not scored

*Temperature ranges now come from GBIF cells and Copernicus temperature: see ADR-0009.*

The design took each species' temperature and depth range from AquaMaps. Checked on 30 Oct 2026, the AquaMaps envelope fits surface fish poorly: for blue jack mackerel it gives a seabed depth of 305–370 m and a *bottom* temperature range of 2.2–15.1 °C. The same AquaMaps page lists the 0.5° cells used to build the envelope, with surface and bottom temperature. We take each species' temperature range as the 10th–90th percentile of those cells' temperatures: surface for surface fish (blue jack mackerel, chub mackerel, skipjack, bigeye), bottom for bottom-living fish (blackspot seabream, black scabbardfish, alfonsinos, greater forkbeard). Depth is checked for bottom-living fish only, against the FishBase "usually" depth range and EMODnet Bathymetry seabed depth. Chlorophyll is shown as a map layer and not scored: any rule needs an invented cut-off, and Azorean waters are low in chlorophyll almost everywhere.

The stock penalty is the habitat-weighted average of status weights, Σ weight × share ÷ Σ share, so it stays between 0.4 and 1 and local pressure always counts.

## Consequences
- Within 6 nm, the 0.083° sea temperature barely varies, so surface fish are in or out of range for a whole trip area in a given month; Attractiveness separates harbours little. The stock penalty, driven by bottom-living fish and depth, varies more.
- Blue jack mackerel's range comes from AquaMaps cells mostly off Africa and the Canaries, so the Azores are in range only in June and November.
- Chub mackerel is in range everywhere, which pulls every penalty toward 0.7 (0.57–0.67).
