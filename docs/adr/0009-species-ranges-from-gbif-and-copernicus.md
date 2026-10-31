# Species temperature ranges from GBIF occurrences and Copernicus temperature

ADR-0006 took each species' temperature range from the cells AquaMaps used for its envelope. On 30–31 Oct 2026 AquaMaps refused connections for hours, and the eight South Aegean species (ADR-0008) had no cached pages. We now build the same kind of range ourselves for every species, in both regions: GBIF occurrences (with coordinates, no geospatial issue, present; fossils and aquarium specimens left out) are reduced to unique 0.5° cells, as AquaMaps does, and each cell gets the mean 2023–2025 Copernicus temperature at the surface (`cmems_mod_glo_phy-thetao_anfc_0.083deg_P1M-m`, top level) or at the seabed (`cmems_mod_glo_phy_anfc_0.083deg_P1M-m`, `tob`). The range is now the 2.5th–97.5th percentile (the 10th–90th cut off the warm Aegean, where pandora and surmullet are caught all year): surface for surface fish, seabed for bottom-living fish. Depth still comes from FishBase.

## Considered Options
- Wait for AquaMaps: no schedule, and the pitch is due.
- AquaMaps for the Azores, GBIF for the Aegean: faster, but the two regions' habitat would come from different sources.
- OBIS: attaches a surface temperature to each record but none at the seabed, and has fewer records than GBIF (which includes most of OBIS).

## Consequences
- Species ranges and trip-area temperatures now come from the same ocean model, years and grid source.
- Azores habitat shares changed from the AquaMaps-based values (see CAVEATS for the new results).
- GBIF records follow where people sample, not where fish are: well-surveyed seas weigh more. AquaMaps shares this bias.
- GBIF pages stop at 100,000 records, so large searches are split by latitude band; a cold fetch takes several minutes.
