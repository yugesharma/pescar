# PescaMare: design

Pilot: **Azores** (11 pilot harbours, full score). All European harbours shown with a partial score. Built for the Copernicus Marine Service Hackathon 2026; pitch materials are due **31 Oct 2026, 08:30**.
Vocabulary is defined in [GLOSSARY.md](GLOSSARY.md); the decisions behind this design are recorded in [docs/adr/](docs/adr/). Background and sources: [pescatourism_project.md](pescatourism_project.md).

## Problem Statement

Azorean regional government and fisheries bodies are asked to fund pescatourism (licences, training, boat refits, marketing) to keep small-scale fishers in business and to take pressure off fish stocks. They have no evidence on where it is viable or how much a harbour can sustain. They cannot tell:
- which harbours have the boats and the tourists to run trips;
- how many days a year the Atlantic swell actually lets a small boat take tourists out;
- where fishing pressure is already high;
- which of the species tourists would catch are overfished.

Once trips start, nobody can see whether they replace commercial fishing days or are added on top. The second case raises total pressure: the rebound risk.

## Solution

A web app with three screens, backed by Copernicus Marine and EU fisheries data for the 11 Azorean harbours.

1. **Explore:**
   - A map of every harbour coloured by harbour score, with layers you can toggle.
   - Clicking a harbour shows its four factors, its limiting factor, viable days per year, income potential, species list and 3-day trip status.
2. **Invest:**
   - Pick a harbour and write an investment proposal.
   - The app projects income and checks the proposal's target trips against the trip cap.
3. **Monitor:**
   - For Validated and Active harbours, see trips made, licensed boats, the share of viable days actually used, trips against the cap, and **replaced vs added fishing days**. That last figure is the rebound check.

## User Stories

### Explore: judging harbours
1. As a regional fisheries officer, I want a map of all Azorean harbours coloured by harbour score, so that I can see at a glance where pescatourism has most potential.
1b. As a regional fisheries officer, I want every European harbour on the map with its viability, viable days and Community, so that I can see how the Azores compare with the rest of Europe.
2. As a regional fisheries officer, I want a ranked list of harbours next to the map, so that I can compare them without clicking each one.
3. As a regional fisheries officer, I want to see each harbour's four factors (Community, Viability, Attractiveness, Headroom), so that I understand why a harbour ranks where it does.
4. As a regional fisheries officer, I want each harbour's limiting factor in plain words (e.g. "limited by winter swell"), so that I know what would have to change for it to rank higher.
5. As a regional fisheries officer, I want viable days per year and income potential (viable days × €500 per boat), so that I can weigh the economic case.
6. As a regional fisheries officer, I want a season curve of viability by week of the year, so that I can see which months trips can run.
7. As a regional fisheries officer, I want viable days in the shoulder season (Apr–Jun, Sep–Oct) shown separately, so that I can judge whether pescatourism extends the tourist season.
8. As a regional fisheries officer, I want to switch the wave limit between 1.0, 1.5 and 2.0 m, so that I can see how sensitive viability is to boat size and tourist comfort.
9. As a regional fisheries officer, I want the number of small boats (under 12 m, licensed) registered at each harbour, so that I know whether there are fishers to run trips.
10. As a regional fisheries officer, I want tourism access per harbour (beds nearby, distance to airport or ferry), so that I know whether tourists can reach it.
11. As a regional fisheries officer, I want a fishing pressure layer, so that I can see where adding activity is riskiest.
12. As a regional fisheries officer, I want a habitat suitability layer for the target species, so that I can see where tourists are likely to find fish.
13. As a regional fisheries officer, I want a list of species with their status (Overfished, Unknown, Healthy) and source, so that I know which fish pescatourism should avoid adding pressure on.
14. As a regional fisheries officer, I want chlorophyll, sea temperature and wave layers from Copernicus Marine, so that I can see current ocean conditions.
15. As a regional fisheries officer, I want protected areas shown on the map, so that I can see where fishing is restricted.
16. As a regional fisheries officer, I want the latest radar detections of vessels without AIS in European waters, labelled with their date, so that I can see current unidentified activity near protected areas.
17. As a regional fisheries officer, I want every layer to state its source, date and limitations, so that I do not over-read the data.
18. As a fisher, I want GO / MARGINAL / NO-GO for my harbour for the next 3 days, with the worst wave height in the trip window, so that I can decide whether to take tourists out.

### Invest: proposing a harbour
19. As a regional fisheries officer, I want to select a harbour and create an investment proposal, so that I can record a funding plan.
20. As a regional fisheries officer, I want to enter boats to license, training places, budget, target trips per week and notes, so that the proposal captures the plan.
21. As a regional fisheries officer, I want to see projected yearly income for the proposal, so that I can compare it with the budget.
22. As a regional fisheries officer, I want a warning when target trips per week exceed the trip cap in any week, so that the plan does not push fishing pressure beyond what the harbour can take.
23. As a regional fisheries officer, I want proposals listed per harbour, so that I can revisit and compare them.
24. As a regional fisheries officer, I want to mark a Proposed harbour as Validated with a date, so that it moves to monitoring.

### Monitor: following a validated harbour
25. As a regional fisheries officer, I want a list of Validated and Active harbours, so that I can follow each one.
26. As a regional fisheries officer, I want each harbour's validation date, licensed boats and trips made, so that I can track uptake.
27. As a fisher or FLAG officer, I want to log a trip (date, boat, passengers, replaced a fishing day yes/no), so that activity is recorded.
28. As a regional fisheries officer, I want replaced vs added fishing days, so that I can see whether pescatourism is taking pressure off or adding to it.
29. As a regional fisheries officer, I want trips per week against the trip cap, so that I can see when a harbour runs over.
30. As a regional fisheries officer, I want the share of viable days actually used, so that I can see unused potential.
31. As a pitch audience member, I want demo data clearly labelled as demo data, so that I am not misled.

## Implementation Decisions

### Harbours
- **Harbours** are EU ports of registration in European waters with at least one licensed vessel under 12 m: 2,341 ports (ADR-0004).
  - French outermost regions (segments `4F*`) are excluded; the Azores, Madeira and the Canaries are kept.
  - Coordinates: UN/LOCODE first (613 ports), then the port name matched within its country in GeoNames.
  - Ports with no sea cell within 20 km are dropped (inland, lake or mismatched); the app reports how many were placed and dropped.
- The **pilot harbours** are the **11 Azorean ports of registration**, all with UN/LOCODE coordinates:
  - EU Fleet Register segments `4K9` and `4KA`;
  - current records, i.e. `Event End Date` = 2100-12-31;
  - keyed by `Place of Registration Code` (UN/LOCODE).
- Coordinates come from the UN/LOCODE list.
- Each harbour's **model cell** is the nearest sea cell of the 0.083° wave grid to a point just offshore.
- The fleet export covers the whole EU. It is read once and the current Portuguese records are kept as the pipeline's input.

### Viability (F1) and trip status (F2)
- **Wave data** (ADR-0001, ADR-0002):
  - Viability comes from `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i`, Nov 2022 onwards, variable VHM0.
  - The 0.2° reanalysis `cmems_mod_glo_wav_my_0.2deg_PT3H-i` is a check only.
- The same global 0.083° product is used for every harbour in Europe, so the method and numbers are comparable. Regional products (MED, IBI, NWS, BAL, BLKSEA) are on the roadmap.
- **Viable day:** every 3-hourly step within 08:00–14:59, in the harbour's own time zone (looked up from its coordinates), is below the wave limit.
  - Wave limits: 1.0, 1.5 and 2.0 m; 1.5 m is the default.
- **Outputs:**
  - viability per week of the year;
  - viable days per year (the input to the Viability factor);
  - shoulder-season viable days.
- **Trip status:** for the next 3 days.
  - GO if the worst Hs in the trip window is below the limit.
  - MARGINAL if it is up to 0.3 m above.
  - Otherwise NO-GO.

### Community (F0)
- Community is the average of two parts, each divided by the best harbour's value:
  - **Small boats:** under 12 m, `Licence Indicator` = Y.
  - **Tourism access:** the number of OpenStreetMap accommodation places within 10 km (hotels, guesthouses, campsites, apartments; OSM rarely records beds), and distance to the nearest airport or ferry terminal. One query per country, counted locally around each harbour; the same method everywhere.
- FLAG support is left out until the Azores FLAG is identified.

### Headroom (F4)
- **Headroom = 1 − local pressure × stock penalty.** This is one formula with two inputs; Headroom is 0 for trip areas inside no-take zones.
- **Local pressure** (input 1, from EMODnet):
  - EMODnet Human Activities fishing intensity, **static gears** layer: MW fishing hours on 0.05° cells, from VMS on vessels of 12 m and over.
  - 1,273 Azores cells, fishing-overview editions 2021–2025.
  - Per harbour: sum the fishing hours in cells within 6 nm (~11 km), divided by the highest harbour's total.
  - Swept area ratio is **not** used: it has no Azores data (bottom trawling is banned there).
  - Global Fishing Watch effort is the fallback only if EMODnet coverage proves too thin.
- **Stock penalty** (input 2, from species status + habitat):
  - Status weights: Overfished 1.0, Unknown 0.7, Healthy 0.4.
  - Each weight counts in proportion to the share of the trip area that is that species' habitat (same depth and temperature calculation as Attractiveness).
  - So the penalty differs by harbour even though stock status is regional (ADR-0003).
- Until slice 5 builds the habitat calculation, the stock penalty is 1 and Headroom uses local pressure alone.

### Species and Attractiveness (F5)
- **Species table:** a few species of each status (Overfished, Unknown, Healthy).
  - ICES SAG stocks are read automatically, using the latest assessment across years and the text status fields.
  - A few ICCAT tuna stocks are entered by hand.
  - Each row cites its source and assessment year.
  - Current picture:
    - Overfished: blackspot seabream, greater forkbeard, black scabbardfish.
    - Unknown: blue jack mackerel, chub mackerel, alfonsinos.
    - Healthy: skipjack tuna; bigeye to be verified.
- **Demand** is a one-off cited snapshot of the most-landed Azorean species: the SREA 2025 summary. Nothing more is taken from SREA.
- **Target species** are the top two by demand that are not Overfished: **blue jack mackerel** and **skipjack tuna**.
- The same habitat calculation also runs for the Overfished species, to give each harbour's stock penalty (see Headroom).
- **Attractiveness** = the share of each harbour's trip area (6 nm) where the target species' habitat is suitable, by month. Suitable means:
  - monthly Copernicus sea temperature is inside the species' AquaMaps range;
  - depth is inside its range (EMODnet bathymetry, or GEBCO where EMODnet does not reach);
  - chlorophyll-a from Copernicus biogeochemistry is included.
- The method is adapted from Map2Fish's inputs and probability framing. We have no catch data to calibrate with, so we use species ranges instead.

### Harbour score (F8) and trip cap (F6)
- **Harbour score** = Community × Viability × Attractiveness × Headroom, for the 11 pilot harbours.
  - Each factor is divided by the best value across all European harbours, so it is never min–max scaled to zero. Dividing by a constant never changes the order, so the pilot ranking is the same whichever set is used.
- **Partial score** = Community × Viability, for every other harbour, clearly labelled. Local pressure and stock penalty need data sources outside the Azores (EMODnet covers ICES waters only; the Mediterranean would need Global Fishing Watch), so they come later.
  - It is a ranking, not an absolute measure.
- **Limiting factor** = the lowest factor, named in plain words.
- **Weekly trip cap** = licensed boats × viable days that week × Headroom, rounded down.
  - Licensed boats come from the proposal; for a Validated harbour, from what was recorded at validation.
- **Income potential** = viable days per year × €500 per boat.
- No "replace fishing days only" wording appears in the UI.

### Dark vessels (F7)
- Data: Global Fishing Watch radar detections of vessels without AIS (`public-global-sar-presence`, `matched=false`).
  - Coverage: all European waters, as 0.1° gridded counts.
  - Only the most recent date GFW has published is shown, labelled with that date.
- The backend checks once a day and swaps in newer data when it appears. GFW lags about 72 hours, so checking more often gains nothing.
- The token lives in `.env`.
- The layer is an overlay only. It is not part of the score and is labelled "not evidence of illegal activity".

### Map layers
- **Copernicus Marine WMTS tiles:** chlorophyll, sea temperature, waves. These are live, with no processing on our side.
- **EMODnet WMS tiles:** fishing intensity.
- **One generated image each:** viability and habitat suitability. These are small grids, so no tile server is needed.
- **GeoJSON:** harbours, protected areas, dark vessels.
- **Basemap:** OpenFreeMap, which needs no key. Map library: MapLibre GL.

### Modules
1. **Data pipeline (Python).**
   - One `build` command fetches every source and writes the harbour table, species table and derived layer images into SQLite.
   - Internally there is one step per factor: waves, community, pressure, species, habitat.
2. **Scoring (pure Python, no I/O).**
   - Input: four raw factor values per harbour.
   - Output: harbour score, limiting factor, trip cap, income potential.
   - Every judgement call lives here.
3. **API (FastAPI + SQLite, no login).**
   - Reads: harbours with factors, species, layer metadata, the dark-vessel feed.
   - Writes: investment proposals, validation, trips.
   - Runs locally for the pitch; deployment only if time allows.
4. **Frontend (React + TypeScript + Vite + MapLibre).**
   - Three screens: Explore, Invest, Monitor.
   - Visual design is done with the `ui-ux-pro-max` skill during the UI slice.

### Harbour lifecycle
- Candidate → Proposed (has an investment proposal) → Validated (an authority approves it; date recorded) → Active (first trip logged).
- **Trip log fields:** date, harbour, boat, passengers, replaced day (yes/no).
- **Demo data:** two harbours are seeded with generated trips, flagged as demo data in the database and the UI.

## Testing Decisions

- Test external behaviour through each module's interface, never its internals.
- **Scoring** is the main test point. Plain assert-based checks cover:
  - the product of factors;
  - dividing by the best harbour's value (no zero for the weakest);
  - the limiting factor;
  - Headroom 0 inside a no-take zone;
  - Headroom falls as local pressure or stock penalty rises, and a harbour with no overfished-species habitat nearby is penalised less;
  - trip cap rounding;
  - income potential.
- **Wave logic:** there is an existing self-check for daily worst Hs in the local trip window, weekly viability and trip status.
- **API:** in-process requests for the flow Candidate → proposal → Validated → trip logged → Monitor figures, including replaced vs added days and trips against the cap.
- **Pipeline data pulls** are not unit-tested. They are checked by eye against known values, e.g. Vila Franca do Campo ≈ 0.62 viability at 1.5 m, and the 0.2° check within ±0.03.
- Each vertical slice is checked in the browser before the next starts.

## Out of Scope

- F3 sea story (later).
- Booking, payments, a tourist app, user accounts and login.
- Machine-learning fish prediction, and a custom dark-vessel detector.
- Stock status per island or harbour, which is not possible because stocks are assessed as whole populations.
- National or Azorean licence limits and FLAG support, which are parked as open questions.
- Any use of SREA data beyond the one-off species snapshot.
- Production deployment.

## Further Notes

### Build plan: vertical slices
Each slice goes pipeline → database → API → screen and is verified in the browser before the next starts. If time runs short, cut in this order:
- habitat with one species;
- Monitor with demo data only, without the entry form;
- dark vessels as a static snapshot.

| # | Slice | Shows |
|---|---|---|
| 1 | Harbours + viability | 11 harbours on the map coloured by viability; detail panel with season curve and 3-day trip status |
| 2 | Community + harbour score | boats, tourism access, score, limiting factor, income potential |
| 3 | Europe: viability + Community | all 2,341 harbours placed; viability and viable days (global 0.083° waves, ~1 h in the background); Community; partial score; clustered on the map, details on zoom |
| 4 | Fishing pressure | EMODnet static-gear tiles; Headroom from local pressure (stock penalty = 1 for now) |
| 5 | Species + habitat | species table; habitat for target and Overfished species; stock penalty; full Headroom and score; trip cap |
| 6 | Ocean layers | Copernicus WMTS chlorophyll, sea temperature, waves |
| 7 | Dark vessels | latest GFW European layer |
| 8 | Invest screen | investment proposals; cap check; Validate action |
| 9 | Monitor screen | trip log; replaced vs added; trips against cap; demo data |
| 10 | UI pass + pitch | `ui-ux-pro-max` design pass; pitch materials |

### Open questions
- Local pressure and stock penalty for harbours outside the Azores (EMODnet for ICES waters; Global Fishing Watch effort and GFCM/STECF status for the Mediterranean).
- Azorean pescatourism licence limits (DLR 36/2008/A; RAMTA DLR 23/2007/A): distance, sea state, passengers, hours.
- Which FLAG covers which islands.
- Why some EMODnet cells near harbours are empty (no vessels of 12 m and over, or withheld by ICES for confidentiality).
- ICCAT status for bigeye and North Atlantic albacore.
- Access to AquaMaps species ranges.
- Daylight-dependent or per-harbour trip windows.

### Known limitations (state them in the pitch)
- About 4 years of high-resolution wave history. It matches the 40-year record on the coarse grid.
- The 0.083° grid cannot resolve small coves.
- Wave limits are assumptions.
- Ports of registration are not always where boats work.
- VMS and AIS miss most boats under 12 m, so fishing pressure is underestimated.
- Habitat suitability is not observed fish.
- Radar detections are not evidence of illegality.
- "Replaced a fishing day" is self-reported.
