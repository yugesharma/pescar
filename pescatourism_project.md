# PescaMare — Copernicus-powered planning for pescatourism

> Working name. Built for the Copernicus Marine Service Hackathon 2026 (29–31 Oct 2026), which is aligned with the European Ocean Pact.

## 1. One-line pitch

We took the "workability" analysis that offshore industries pay consultants for and made it free for small-scale fishers and their Fisheries Local Action Groups (FLAGs). Using Copernicus data, it shows which harbours can sustain pescatourism, on which days, and at what level of activity, without adding fishing pressure.

## 2. What is pescatourism

Pescatourism means professional fishers taking tourists on board their own fishing boats. Tourists watch or join low-intensity fishing, learn about the sea and local traditions, and often eat the catch. It differs from recreational fishing because it is run by licensed commercial fishers as a way to diversify their income.

Evidence from the Greek FLAG programme, as of Sept 2023 ([DG MARE, 2024](https://oceans-and-fisheries.ec.europa.eu/news/pescatourism-cooperation-opportunity-mediterranean-fisheries-2024-06-07_en)):
- 450+ fishers explored pescatourism, 100+ received training, 48 started licensing, and **157 were actively engaged**.
- **About €500 earned per trip-day.**
- A gillnet fisher sets **about 0.5 km of net on a pescatourism trip, against about 5 km on a commercial fishing day**, roughly 90% less gear in the water.
- Greece has had pescatourism rules since 2015, and Italy (Sardinia) has established operators, including inside the Asinara MPA.
- The main barriers are awareness among both fishers and tourists, licensing, business skills and seasonality.

## 3. Why this theme

### 3.1 It answers problems the EU named in 2026
| EU document | Problem it names | How pescatourism helps |
|---|---|---|
| **CFP evaluation** ([IP/26/938](https://ec.europa.eu/commission/presscorner/detail/en/ip_26_938)) | Fish stocks recovering too slowly; small-scale fishers facing rising costs, poor access to fishing opportunities and weak generational renewal | Income no longer tied to catch volume; less gear in the water; attractive to younger fishers |
| **EU Islands and Coastal Communities strategies** ([IP/26/1318](https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1318), 10 Jun 2026) | Seasonality, overdependence on tourism, unbalanced tourism, youth outmigration, diversified local economies needed | Extends the tourist season beyond the beach, and the money stays with local fishers |
| **European Ocean Pact** ([COM(2025) 281](https://oceans-and-fisheries.ec.europa.eu/european-ocean-pact_en)) | Small-scale fisheries named "a priority"; an EU Sustainable Tourism Strategy promised; coastal communities called "the driving force" of the blue economy | Combines sustainable tourism and small-scale fisheries in one activity |
| **EU fisheries control regulation 2023/2842** | All vessels, including those under 12 m, must carry tracking devices by 2028 | Future data source for small-scale fishing effort. The [EM4SSF project](https://www.irbim.cnr.it/en/progetto-dettagli/em4ssf/) (CNR-IRBIM, 2025–2028) is building the data framework for this |

### 3.2 Ocean Pact priorities covered
- **P1 Ocean health:** less fishing gear in the water, with activity steered away from overfished or protected areas.
- **P2 Sustainable blue economy:** a new income line for small-scale fishers.
- **P3 Coastal, island and outermost regions:** the main beneficiaries. The tool also works for the Azores, Madeira and the Canaries.
- **P4 Knowledge and skills:** the "sea story" builds ocean literacy, and trips could produce citizen-science data.
- **P6 Governance:** effort caps and harbour rankings give FLAGs and regions a basis for licensing and funding decisions.

### 3.3 Novelty check
- **Hackathon field:** none of the 47 submissions to this hackathon (checked 29 Oct 2026) addresses pescatourism. The closest are oyster-farmer alerts (#33) and a fishing-route AI (#18).
- **Existing tools:** the *calculation* is not new. Weather-window or workability analysis is a standard offshore-industry service (DHI Metocean Risk Ops, Noveltis Weather Downtime, consultancy climatologies), and surf-forecast.com publishes monthly wave statistics for surf spots. All of these are paid, aimed at large vessels or surfers, or too coarse to resolve sheltered bays.
- **What is new:** the user (small-scale fishers and FLAGs), the decision (where to invest in pescatourism, on which days, and how much), harbour-scale Copernicus data, and the tie-in to fishing-pressure limits.
- **Do not claim** to have invented weather-window analysis. Claim to have brought it to a sector that has never had it.

### 3.4 Problems to solve (aligned with the Ocean Pact)

**Core problem:** pescatourism is promoted as a way to take pressure off fish stocks while keeping small-scale fishers in business. But no one can tell where it is viable, how much a site can sustain, or whether it actually replaces fishing. Regions and FLAGs fund licences and training without that evidence.

| # | Problem | Evidence | Pact priority | Can Copernicus help? |
|---|---|---|---|---|
| 1 | **Small-scale fishing is declining:** rising costs, poor access to fishing opportunities, ageing boats, few young entrants | CFP evaluation (IP/26/938) | P2 Blue economy, P3 Coastal communities | Indirectly: pescatourism is the response, and the data shows where it can pay |
| 2 | **Seasonality and overdependence on tourism:** coastal and island economies depend on a short July–August beach season | Islands & Coastal Communities strategies (IP/26/1318) | P3 | **Yes:** wave history shows which harbours have viable shoulder-season weeks (F1) |
| 3 | **Fish stocks recover too slowly, and most Mediterranean stocks are overfished** | CFP evaluation: 63% of stocks fished sustainably, recovery slower than expected | P1 Ocean health | **Partly:** habitat and fishing-pressure layers steer activity away from stressed areas (F4, F5) |
| 4 | **Rebound risk:** pescatourism only helps stocks if it *replaces* fishing days. Tourist trips added on top of full fishing raise total pressure, and nothing tracks or limits this today | Implied by the ~0.5 km vs ~5 km net comparison (DG MARE); no cap mechanism found | P1, P6 Governance | **Yes, as a rule:** precautionary trip cap per site tied to stock status and pressure (F6) |
| 5 | **No evidence base for investment:** regions fund pescatourism without knowing which harbours can sustain it, given sea conditions, fish habitat and fishing pressure | Greek programme: 450 fishers interested, 157 active; no site-selection method reported | P6 Governance, P3 | **Yes, this is the core:** harbour investment score (F8) |
| 6 | **Safety and reliability:** small boats with paying tourists are exposed to sea state, and cancelled trips cost income and reputation | Pact: early warning for coastal resilience | P5 Resilience, P2 | **Yes:** go/no-go forecast for the trip day (F2) |
| 7 | **Small-scale fisheries are poorly monitored:** boats under 12 m mostly do not appear in vessel tracking, so their effort is barely recorded | EM4SSF project; tracking on all vessels by 2028 (Reg. 2023/2842) | P4 Knowledge, P6 | Not yet: trip logs could feed this data in future (roadmap) |
| 8 | **Low ocean literacy and low awareness of pescatourism among tourists** | DG MARE pescatourism article; Pact ocean-literacy aims | P4 Skills | **Partly:** the sea story turns each trip into data-backed learning (F3) |
| 9 | **Licensing and business-skill barriers** | DG MARE pescatourism article | P2 | No: policy and training, out of scope |

**Problem statement for the pitch:**

> Europe wants small-scale fishers to diversify into pescatourism to protect both livelihoods and fish stocks. But no one can say which harbours can sustain it, in which weeks, or at what level, so investment is guesswork. And nothing ensures tourist trips replace fishing days instead of adding to them.
> **We use Copernicus data to tell regions where pescatourism is viable and how much each site can sustain, and to tell fishers whether to go out tomorrow.**

**Focus:**
- **Core:** problems 4 and 5. Nobody addresses them, they need Copernicus data, and they hit the governance and ocean-health priorities.
- **Supporting features:** problems 2 and 6.
- **Context that motivates the project:** problems 1 and 3.
- **Out of scope:** problem 9.

## 4. Aims and goals

### Aim
Help coastal communities grow pescatourism where it is safe, viable and ecologically sustainable, so that it replaces fishing pressure instead of adding to it.

### Goals
1. **Viability:** for each harbour, quantify the probability that a small boat can take tourists out comfortably in each week of the year.
2. **Operations:** give fishers a simple go/no-go call for tomorrow's trip.
3. **Experience:** turn each trip into a short, data-backed "sea story" for tourists.
4. **Sustainability:** steer pescatourism away from overfished and protected areas and towards good habitat, and set a precautionary activity cap for each site.
5. **Investment:** rank harbours for public and FLAG investment in pescatourism (licences, training, boat refits, marketing).

### Users
| User | Decision supported |
|---|---|
| Small-scale fisher | Should I get a pescatourism licence? Do I go out tomorrow? Where do I take the tourists? |
| FLAG or regional authority | Which harbours should we fund? How many licences or trips can each area sustain? |
| Tourist | Is this trip likely to run, and what will I see and learn? |
| Fisheries managers / scientists | Is pescatourism replacing fishing effort, or adding to it? |

## 5. Features

### F0. Fishing community layer (which harbours have people to run pescatourism)
- **Question:** which harbours have a small-scale fishing community, support on the ground, and tourists within reach?
- **Three checks per harbour:**

| Check | Data | What to compute |
|---|---|---|
| **1. Small-scale fishing community** | **EU Fleet Register** ([fleet-europa](https://webgate.ec.europa.eu/fleet-europa/search_en)), free CSV export per country: port of registration, length, gear, engine power, status | Number of **active vessels under 12 m** per port of registration |
| **3. Support on the ground** | **FLAG map and directory** (FAMENET); national lists of licensed pescatourism operators | Is the port inside a FLAG area? Are there existing operators (proof of concept) or none (untapped potential)? |
| **4. Tourism access** | **OpenStreetMap** (hotels, guesthouses, campsites, marinas, ferry terminals, airports); Eurostat tourism nights per region | Beds within about 10 km; distance to the nearest airport or ferry |

- **Mapping ports:** Fleet Register ports use **UN/LOCODE** codes (e.g. `PTPDL` = Ponta Delgada). The UN/LOCODE list includes coordinates, so no geocoding is needed.
- **Score:**
  ```
  Community = small boats (<12 m, active, scaled 0–1) × (1 + FLAG bonus) × tourism access (scaled 0–1)
  ```
- **Sketch:**
  ```python
  import pandas as pd

  fleet = pd.read_csv("fleet_PRT.csv", sep=";")                     # fleet-europa export, Portugal
  fleet = fleet[(fleet["LOA"] < 12) & (fleet["Event"] != "DES")]    # <12 m, not withdrawn
  # ponytail: column names/event codes vary by export; check the header once
  ports = fleet.groupby("Port Code").size().rename("small_boats")
  ```
- **Azores specifics (to verify):**
  - Lotaçor and SREA landings by port and island, as a cross-check on where fishing actually happens.
  - The Portuguese "pesca-turismo" regulation and any list of licensed operators.
  - Which FLAG covers the Azores.
- **Limitation:** the port of registration is not always where a boat works or lands, especially across islands. Cross-check with landings by port where available.

### F1. Harbour viability atlas (core, novel)
- **Question:** in week N of the year, what is the probability that a trip day is viable at this harbour?
- **Method:**
  1. For each harbour, take one sea point about 1–3 km offshore, where boats actually operate. Cells right at the harbour are often land or blank in the model.
  2. Pull an hourly wave time series for 10+ years, at that point only, from the reanalysis.
  3. A day is **viable** if every hour in the trip window (for example 08:00–14:00 local) is below the thresholds: significant wave height (Hs) first; wind and wave period as stretch goals.
  4. Viability for week N = the share of days in week N, across all years, that were viable. That gives about 70 samples per week over 10 years.
  5. Expected viable days per month × about €500 per trip = income potential, especially outside July and August.
- **Why not a ready-made climatology:** monthly means hide the spread of conditions, and a calm average can still contain a dangerous mid-trip spike. We need the probability of a calm *trip window*, not an average.
- **Output:** a heatmap (harbours × weeks of the year), a season curve for each harbour, and the number of extra viable weeks outside peak season.

### F2. Day-of-trip go/no-go
- Applies the F1 thresholds to the Copernicus Marine wave forecast for the next few days.
- **Output:** a status for each harbour for the next 1–3 days (GO, MARGINAL or NO-GO), with the hour-by-hour wave height across the trip window.
- **Stretch:** a seasickness-comfort score from wave period; and a suggested calmer route given swell direction and currents.

### F3. Sea story
- A short, tourist-facing summary of today's sea:
  - sea temperature now against its 20-year normal for this date;
  - whether a marine heatwave is under way;
  - chlorophyll, and fronts where fish tend to gather;
  - the species likely to be seen or caught (from F5).
- **Purpose:** ocean literacy, and a better product the fisher can sell.

### F4. Fishing pressure and stock health (where *not* to add pressure)
Two parts: **local pressure**, which separates one harbour from another, and **regional stock health**, a multiplier for the whole region, because a stock area covers every pilot harbour.

**a) Local fishing pressure: source depends on the pilot area**

| Pilot area | Best source | Notes |
|---|---|---|
| **Azores** (and all ICES waters: Biscay/Iberia, Celtic, North Sea, Baltic…) | **EMODnet Human Activities fishing intensity** (from ICES VMS data) | Effort in mW fishing hours by gear type, plus **swept area ratio (SAR)**, surface and subsurface. VMS covers vessels of 12 m and over, more than AIS. **No Mediterranean coverage.** Years unconfirmed; the EDITO STAC copy ends at 2016, so check the portal for newer years |
| **Corsica / Gulf of Lions** | Ifremer swept-area-ratio layer (regional) | Mediterranean, but this area only |
| **Rest of the Mediterranean** (Sardinia, Greece…) | **Global Fishing Watch** apparent fishing effort (`public-global-fishing-effort:latest`, 4Wings API, non-commercial token), or **EMODnet vessel density, fishing ships** (1 km, monthly, no login, includes transits) | AIS only, so mostly vessels over about 15 m |

- **Per harbour:** take effort or SAR within the trip radius (about 6 nm, about 11 km; check the national licence limit). Sum effort; take the max or mean of SAR (it is already a rate).
- **Threshold:** an ICES-linked benchmark treats **SAR < 0.43** as low pressure from mobile bottom gears. This comes from a secondary source (ANEMONE/IOBAS), so **verify it with ICES**. Where SAR is unavailable, use the percentile rank of effort within the pilot area.

**b) Regional stock health**

| Region | Status source | Area polygons |
|---|---|---|
| ICES waters (Azores) | **ICES Stock Assessment Graphs (SAG) API**, tested 29 Oct 2026: `https://sag.ices.dk/SAG_API/api/StockList?year=2024` (198 stocks), `StockStatusValues?assessmentKey=`, `FishStockReferencePoints?assessmentKey=`, `SummaryTable?assessmentKey=` | `https://gis.ices.dk/shapefiles/ICES_areas.zip`, `https://gis.ices.dk/shapefiles/ICES_ecoregions.zip` (both tested). Azores = subarea 10, division 10.a.2 |
| Mediterranean | GFCM / STECF assessment reports, with no API, so enter 3–5 stocks into a CSV by hand | GFCM GSA shapefile (Sardinia = GSA 11; Greece = GSAs 20, 22, 23) |

- **Azores stocks in the 2024 SAG list:**
  - local: `jaa.27.10a2` (blue jack mackerel);
  - wide-ranging, North-East Atlantic: `alf.27.nea`, `bsf.27.nea`, `gfb.27.nea`, `dgs.27.nea`, `por.27.nea`, `mac.27.nea`.
  - Blackspot seabream was not in the 2024 list.
  - Many deep-water stocks are data-limited ("unknown").
  - Tunas are assessed by ICCAT, not ICES.
- **Penalty table (CSV):**
  - F > FMSY or SSB < MSY Btrigger → **1.0** (substitution only);
  - unknown / data-limited → **0.7**;
  - within limits → **0.4**.
  - **The numeric status codes are not yet mapped to colours.** The test stock returned `6`, probably grey/unknown. Check against one stock's ICES advice page.
- **Spatial join:** load the ICES areas shapefile with geopandas, `sjoin` the harbours to find their division, and keep the stocks covering that division. Check the shapefile's column names, e.g. `Area_Full`.
- **Combine:**
  ```
  Headroom = 1 − local pressure (scaled 0–1, or SAR vs 0.43) × regional stock penalty
             → 0 for trip areas inside no-take zones
  ```

**Limitations, stated in the tool:**
- AIS and VMS miss most boats under 12 m, so small-scale pressure is underestimated.
- Stock status applies to a whole region, not to a site.
- These are pressure indicators, not proof of overfishing at a site.

### F5. Habitat suitability (where fish are *likely*)
- For 1–3 target species typical of pescatourism in the pilot area, score each cell by:
  - temperature range (Copernicus sea temperature);
  - productivity (chlorophyll and fronts);
  - oxygen (Copernicus Marine biogeochemistry);
  - depth and seabed type (EMODnet bathymetry and EUSeaMap);
  - known occurrences (OBIS / GBIF).
- **Framing:** "habitat suitability", never "fish are here". Satellites cannot observe fish.
- **Use:** choose trip areas with a good tourist experience that do not overlap the hardest-fished cells from F4.

### F6. Precautionary effort cap ("healthy limit") per site
- A science-grade biological safe limit at site level needs a stock assessment, which is not possible in a hackathon. Instead we implement a **transparent, configurable precautionary rule**.
- **Principle:** pescatourism must reduce total gear in the water.
  - One pescatourism trip uses about 0.5 km of net, against about 5 km on a commercial day.
  - **Stock overfished** (most Mediterranean stocks, per GFCM): trips are allowed only as *substitutes* for commercial fishing days, never on top.
  - **High F4 pressure nearby:** a lower weekly trip cap.
  - **Inside a no-take zone:** fishing activity is zero; observation-only trips are allowed if the MPA rules permit.
- **Output:** recommended maximum trips per week per site.
- All thresholds live in a config file, and the pitch says scientists and FLAGs should calibrate them.

### F7. Suspicious-vessel overlay (layer only)
- Sentinel-1 radar vessel detections with no matching AIS signal, from the Global Fishing Watch `public-global-sar-presence` dataset (`matched=false`), overlaid on MPA boundaries.
- **This layer only flags. It is not an accusation, and we do not build a detector.**
  - Detecting dark vessels is mainstream; at least 3 hackathon submissions already work on vessel monitoring.
  - Radar misses small boats.

### F8. Harbour investment score (ties everything together)
```
Investment score = Community × Viability × Attractiveness × Headroom

Community      = small-scale fleet, FLAG support, tourism access  (F0)  → who will run trips
Viability      = expected viable trip days per year               (F1)  → when they can go
Attractiveness = habitat suitability near the harbour             (F5)  → what tourists see
Headroom       = 1 − local pressure × regional stock penalty      (F4)  → can the sea take it
                 → 0 for areas inside no-take zones
```
- **Output:** a ranked list of harbours, each with its income potential, recommended trip cap (F6) and main constraint ("limited by winter swell", "limited by fishing pressure", and so on).
- **This answers the infrastructure-investment question:** invest where the score is high, at the scale the cap allows.

## 6. Data sources

| Need | Source | ID / access | Notes |
|---|---|---|---|
| Wave history | Copernicus Marine | `MEDSEA_MULTIYEAR_WAV_006_012` (hourly dataset, probably `cmems_mod_med_wav_my_4.2km_PT1H-i`; **verify with `copernicusmarine describe`**) | About 4 km grid, variable `VHM0` = Hs |
| Wave forecast | Copernicus Marine | `MEDSEA_ANALYSISFORECAST_WAV_006_017` | For F2 |
| Currents, temperature | Copernicus Marine | `MEDSEA_ANALYSISFORECAST_PHY_006_013` | |
| Chlorophyll, oxygen | Copernicus Marine | `MEDSEA_ANALYSISFORECAST_BGC_006_014` / `MEDSEA_MULTIYEAR_BGC_006_008` | |
| Sea temperature now and its normal | Copernicus Marine | `SST_MED_SST_L4_NRT_OBSERVATIONS_010_004` / `SST_MED_SST_L4_REP_OBSERVATIONS_010_021` | |
| Wind | Copernicus Marine | `WIND_GLO_PHY_L4_NRT_012_004` / `WIND_GLO_PHY_L4_MY_012_006` | Stretch |
| Atlantic islands (if chosen) | Copernicus Marine | `IBI_MULTIYEAR_WAV_005_006`, `IBI_ANALYSISFORECAST_WAV_005_005`, `IBI_*` | Azores, Madeira, Canaries |
| Validation of wave statistics | C3S Climate Data Store | `sis-ocean-wave-indicators`, `sis-ocean-wave-timeseries` | Coastal points 30 km apart, for a cross-check |
| Alternative wave history | UIB European coastal hindcast 1940–2024 | 7,000 coastal points, hourly Hs/Tp/Dir | CC BY-NC licence |
| Small-scale fleet per port | EU Fleet Register (fleet-europa) | CSV export per country | Vessels under 12 m by port of registration (UN/LOCODE) |
| Port coordinates | UN/LOCODE list | Download | Maps Fleet Register port codes to coordinates |
| FLAG areas | FAMENET FLAG directory / map | Web | Support on the ground |
| Tourism access | OpenStreetMap (Overpass API); Eurostat tourism nights | API / download | Beds, marinas, ferries, airports |
| Fishing intensity (ICES waters) | EMODnet Human Activities | Fishing intensity: effort by gear + swept area ratio | ICES/VMS; no Mediterranean coverage |
| Stock status (ICES waters) | ICES SAG API | `https://sag.ices.dk/SAG_API/api/...` | Tested; status codes need mapping |
| Stock areas | ICES GIS | `ICES_areas.zip`, `ICES_ecoregions.zip` | Tested |
| Stock areas (Med) | GFCM | GSA shapefile | Status entered by hand from GFCM/STECF reports |
| Fishing effort | Global Fishing Watch API | `public-global-fishing-effort:latest` | Free non-commercial token needed |
| Dark vessels | Global Fishing Watch API | `public-global-sar-presence`, `matched=false` | Same token |
| Stock status | GFCM / STECF | Per GSA, from published reports | Entered by hand for the pilot GSA |
| Depth, seabed habitat, human activities | EMODnet | Bathymetry DTM, EUSeaMap, Human Activities (WMS/WFS, ERDDAP) | Free, no login |
| Protected areas | EMODnet Human Activities / Marine Regions / EEA Natura 2000 | Shapefile / WFS | |
| Species occurrences | OBIS / GBIF | APIs | For F5 |

## 7. Technical approach

- **Stack:**
  - Python with `copernicusmarine` (Toolbox v2, ARCO Zarr, `open_dataset` for point time series), `xarray`, `pandas`, and `requests` for the GFW and EMODnet APIs.
  - Front end: one simple web map (Streamlit + Folium, or a static Leaflet page).
- **Keep data small:** pull point time series only (one point per harbour), not full grids. 10+ years of hourly data at one point is about 90k values and downloads in seconds to minutes.
- **Thresholds in one config file:**
  - wave height limit (starting assumption: Hs < 1.0 m);
  - trip window (08:00–14:00 local);
  - effort-cap parameters;
  - €/trip (500).
- **Validation slide:** compare F1 results with the C3S wave indicators and, where available, the surf-forecast.com monthly statistics.

### Core F1 calculation (sketch)
```python
import copernicusmarine as cm
import pandas as pd

HARBOURS = {"Harbour A": (40.56, 8.29)}   # lat, lon ~1–3 km offshore
HS_MAX = 1.0                               # m; set from licence rules
WINDOW = range(8, 15)                      # trip hours; convert UTC→local

def hs_series(lat, lon):
    ds = cm.open_dataset(
        dataset_id="cmems_mod_med_wav_my_4.2km_PT1H-i",   # verify
        variables=["VHM0"],
        minimum_latitude=lat, maximum_latitude=lat,
        minimum_longitude=lon, maximum_longitude=lon,
        start_datetime="2014-01-01", end_datetime="2024-12-31",
    )
    return ds["VHM0"].squeeze().to_series()

cols = []
for name, (lat, lon) in HARBOURS.items():
    hs = hs_series(lat, lon)
    trip = hs[hs.index.hour.isin(WINDOW)]
    ok = trip.groupby(trip.index.date).max() < HS_MAX    # worst trip hour decides
    ok.index = pd.to_datetime(ok.index)
    cols.append(ok.groupby(ok.index.isocalendar().week).mean().rename(name))

atlas = pd.concat(cols, axis=1)   # weeks × harbours → P(viable day)
```

## 8. 48-hour scope

| Priority | Build | Notes |
|---|---|---|
| **Must** | F1 viability atlas, F2 go/no-go, F8 investment score with the F6 cap rule | The novel core; build properly |
| **Should** | F3 sea story, F5 habitat suitability (1–2 species), F4 fishing-effort map + stock-status table | Simple versions |
| **Could** | F7 dark-vessel overlay, MPA layer | One API call each; overlay only |
| **Won't (this weekend)** | Booking platform, tourist app, ML fish prediction, a custom illegal-fishing detector | Out of scope or mainstream |

### Suggested timeline
1. **First hours:**
   - Accounts: Copernicus Marine, GFW token, CDS (if used).
   - Pick the pilot area and 5–10 harbours.
   - Confirm the dataset IDs.
2. **Day 1:** F1 and F2 working end to end for all pilot harbours.
3. **Day 2 morning:** F4, F5, F6 and F8; F3 charts.
4. **Day 2 afternoon:** map front end, validation slide, pitch.

## 9. Pilot area options (to decide)

| Option | Pros | Cons |
|---|---|---|
| **Sardinia, Italy** | Established pescatourism operators (DG MARE article), Asinara MPA, good GFCM coverage | Italian licence limits need checking |
| **Greek islands** | 157 active fishers in the FLAG programme, rules in place since 2015 | Many small islands, so harbour selection takes care |
| **Azores / Madeira / Canaries** | Outermost-regions angle (Pact P3), strong storyline | Atlantic swell makes viability harder; switch to IBI products and different stock bodies |

## 10. Risks and limitations (state them in the pitch)

1. **Thresholds are assumptions.**
   - National pescatourism rules (distance from shore, sea-state limits, daylight) differ across Italy, Greece and Spain. **These have not been verified yet.**
   - There is no standard tourist-comfort threshold. Make both configurable for each boat.
2. **Model resolution:** about 4 km cannot fully resolve tiny coves. Use offshore points where boats operate, and say so.
3. **Fish availability is not observed.** F5 is habitat suitability only.
4. **Small-scale effort is invisible to AIS.**
   - F4 underestimates small-scale pressure.
   - Tracking data under Regulation 2023/2842 and EM4SSF will fill this gap from 2028. Present that as future integration.
5. **The effort cap is precautionary, not biological.** It must be calibrated by fisheries scientists and FLAGs.
6. **Dark-vessel flags are not evidence of illegality.**
7. **Unverified IDs / access:**
   - the hourly dataset ID inside `MEDSEA_MULTIYEAR_WAV_006_012`;
   - GFW token approval time;
   - whether the C3S wave indicators come per month or per year.

## 11. Future roadmap (pitch slide)
- Integrate vessel tracking under Regulation 2023/2842 / EM4SSF for real small-scale effort.
- Logbooks from pescatourism trips: tourists' catch and sightings → citizen-science data for data-poor small-scale fisheries.
- Calibrate caps with FLAGs and GFCM scientists.
- Extend to all EU coastlines (`IBI_*`, `NWSHELF_*`, `BAL_*`, `BLKSEA_*` products).
- A "nets not set" impact report for EMFAF-funded FLAG projects.

## 12. Pre-build checklist
- [ ] Copernicus Marine account, then `copernicusmarine login`
- [ ] Global Fishing Watch API token (non-commercial)
- [ ] CDS account + `~/.cdsapirc` (only for validation)
- [ ] Choose the pilot area and 5–10 harbours, with offshore points
- [ ] Confirm wave dataset ID and variables with `copernicusmarine describe`
- [ ] Look up national pescatourism licence limits for the pilot country
- [ ] Get stock status for 3–5 target species: ICES SAG (Azores) or GFCM/STECF (Med); map the SAG status codes to colours
- [ ] Download the Fleet Register CSV for the pilot country; check the column names
- [ ] Download the UN/LOCODE list for port coordinates
- [ ] Find the FLAG covering the pilot area (FAMENET)
- [ ] Check EMODnet fishing intensity years and the 0.43 SAR threshold source
- [ ] Check the hackathon challenge page for the matching theme and submission rules

## 13. Sources
- European Ocean Pact: https://oceans-and-fisheries.ec.europa.eu/european-ocean-pact_en
- CFP evaluation press release (IP/26/938): https://ec.europa.eu/commission/presscorner/detail/en/ip_26_938
- EU Islands and Coastal Communities strategies (IP/26/1318): https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1318
- Pescatourism in Mediterranean fisheries (DG MARE, 2024): https://oceans-and-fisheries.ec.europa.eu/news/pescatourism-cooperation-opportunity-mediterranean-fisheries-2024-06-07_en
- EM4SSF project (CNR-IRBIM): https://www.irbim.cnr.it/en/progetto-dettagli/em4ssf/
- C3S wave indicators: https://cds.climate.copernicus.eu/datasets/sis-ocean-wave-indicators
- C3S wave time series: https://cds.climate.copernicus.eu/datasets/sis-ocean-wave-timeseries
- UIB European coastal hindcast 1940–2024: https://portalinvestigacio.uib.cat/documentos/6a454fdd451e3576c05cf5da
- DHI offshore workability app: https://worldwide.dhigroup.com/global/news/2021/09/dhi-launches-new-cloud-based-offshore-workability-assessment-app
- Noveltis Weather Downtime: https://www.noveltis.fr/?p=4987
- Surf-forecast historical statistics: https://www.surf-forecast.com/greenroom/using-surf-forecasts-historical-surf-data-to-find-the-most-consistent-waves-on-earth/
- Global Fishing Watch: https://globalfishingwatch.org
- Background research report: reports/European Ocean Pact Copernicus hackathon.md
