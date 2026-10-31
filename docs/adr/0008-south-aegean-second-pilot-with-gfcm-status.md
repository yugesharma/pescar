# South Aegean as a second pilot region, with stock status from GFCM

To show the method compares across Europe, a second region gets the full harbour score: the South Aegean (NUTS 2 EL42, Cyclades and Dodecanese, 24 harbours, 1,105 small boats). Pilot harbours are now the harbours of a list of NUTS 2 regions (`build.PILOT_REGIONS`), not the Azores fleet segments; the Azores pilot (PT20) holds the same 11 harbours. Everything else runs per region on the same sources as the Azores: GFW fishing hours, Copernicus monthly temperature, EMODnet Bathymetry, AquaMaps and FishBase ranges, live waves and a fish-fronts image.

ICES does not assess Mediterranean stocks. The newest public status for the Aegean (GSA 22) is GFCM's *The State of Mediterranean and Black Sea Fisheries 2025* (SoMFi), Tables 5–6, reference year 2023, which give F/FMSY and B/BMSY. A stock is Overfished when F/FMSY > 1 or B/BMSY < 0.5 (half its MSY size, standing in for ICES's MSY Btrigger), otherwise Healthy; stocks with only qualitative advice or no assessment are Unknown. Values are entered by hand with their source, as ICCAT's are for the Azores.

## Considered Options
- Galicia: every source including ICES works unchanged, but a mainland coast against islands, and less of a contrast in sea and tourism.
- GFCM Stock Assessment Forms and STAR spreadsheets (public blob store): machine-readable, but the newest Aegean files are for 2019–2020.
- STECF Mediterranean assessments: the Aegean ones are older or qualitative (hake, deep-water rose shrimp).
- Fishing mortality only (GFCM's own "sustainable" colouring): red mullet would be Healthy at 41% of its MSY biomass.

## Consequences
- Attractiveness is divided by the best pilot harbour across both regions, although the two regions' species differ (chosen by the user).
- AIS misses most small Greek boats, so Aegean fishing pressure is underestimated more than in the Azores.
- Aegean waters are low in chlorophyll, so head-on fronts are rarer there.
