# Fish fronts layer after Tijani et al. 2015, without catch data

Habitat from temperature ranges (ADR-0006) barely varies within a 6 nm trip area. Map2Fish, the Copernicus Marine use case for fishing tourism, locates pelagic fish at fronts using the method of Tijani et al. (IGARSS 2015): on 3-day SST and chlorophyll composites, upwelling areas are strong fronts where the SST and chlorophyll gradients point in opposite directions, P = ∇T·∇C / (‖∇T‖‖∇C‖) near −1. We add this as a daily map layer for the pilot area: SST fronts (gradient ≥ 0.02 °C/km) and, on them, head-on stretches (P < −0.7). It is not part of the harbour score.

## Considered Options
- Front frequency per trip area as Attractiveness: would separate harbours better, but changes scores, needs a 3-year daily download, and the 4 km chlorophyll grid is only 2–3 cells across a trip area.
- Canny edge detection, as in the paper: thin front lines, but needs an image library or more code; a gradient threshold gives bands instead.

## Consequences
- The paper calibrated against Adriatic catch data; we have none, so the layer shows where fish are more likely, not a probability.
- Its thresholds are not published; ours are judgement calls (CAVEATS).
- On 27–29 Oct 2026, 62% of Azores front cells were head-on against 39% of all sea cells, consistent with the paper's physics.
