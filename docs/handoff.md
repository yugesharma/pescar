# Handoff: PescaMare, slices 1–3 done, slice 4 next

Repo: `/home/yugesh/Documents/TideVector/pescatourism/pescamare/`. This is the folder that goes to GitHub. It is a git repo with **no commits yet and no remote**; the user hasn't said to commit. Hackathon pitch materials are due **31 Oct 2026, 08:30**.

## Read first (don't re-derive)
- `DESIGN.md`: the spec and the 10-slice build plan. Updated this session:
  - Harbours section: key rule, GeoNames fallback, time zone, NUTS 2 region, placement counts.
  - Viability: missing model days (sea ice) are not viable.
  - Community: small boats and accommodation places both on a log scale, with reasons.
  - User story 2b (country + region filter); new known limitations.
- `GLOSSARY.md`: use its terms exactly (unchanged this session).
- `docs/adr/0001`–`0004` (unchanged).
- `README.md`: how to run, and what is in `data/` and `data/cache/`.
- The parent folder `pescatourism/archive/` is outside git and not needed by the code.

## State
**Slices 1–3 are built and checked in a browser.** Slice 3 = all of Europe with viability, Community and partial score, plus a country → NUTS 2 region filter the user asked for.

| File | Role |
|---|---|
| `build.py` | `build` command. `harbours()` builds the Europe harbour list from the fleet register (licensed, under 12 m, not `4F*`), UN/LOCODE then GeoNames coordinates, time zone from the nearest GeoNames place, Europe bounding box. `regions()` assigns NUTS 2. `main()` runs waves → drop rule → community → regions → scoring, writes `data/pescamare.db` atomically. Placement counts go into `meta` as `harbours_*`. |
| `waves.py` | `harbour(h, live)`: one harbour's rows. Pilot (`live=True`) is fetched fresh with the 3-day forecast; others are history only and cached in `data/cache/waves/<code>.json`. `run()` uses 16 threads; a failing harbour is left out and retried next run. `MAX_KM = 20` drop rule. `full_days()` makes missing days (sea ice) count as not viable. Per-harbour `tz` everywhere. |
| `community.py` | OSM accommodation within 10 km and nearest IATA airport / ferry terminal, one Overpass query per country (cached `data/cache/osm_<CC>.json`). Small-boat counting moved to `build.harbours()`. |
| `scoring.py` | Pure `score(raw)`. Boats and places use `math.log1p` before dividing by the best; closeness unchanged. Normalised across all of Europe. |
| `api.py` | `GET /api/harbours?limit=` → light list (code, name, cc, region, region_name, lat, lon, pilot, score, limiting, viable_days) + `meta`, ranked by score. `GET /api/harbours/{code}?limit=` → full detail + `rank`/`of` in Europe + weekly curve + trips. 422 on bad limit, 404 on unknown code. |
| `web/src/App.tsx` | Country picker (All Europe or a country) + Region picker (All of country or a NUTS 2 region); default Portugal → PT20 (Azores = the 11 pilot harbours). Map: non-pilot harbours clustered (MapLibre native, cluster colour = best score inside), pilot harbours a separate unclustered source with a dark ring. List ranked within selection + "#n in Europe"; All Europe shows top 100. Detail panel says "partial score" outside the pilot, notes GeoNames-placed locations, hides trip status for non-pilot. |

**Harbour keys:** UN/LOCODE where the register uses one; otherwise `ISO2-code` (`GR-007`, `IT-00126`, `FI-V`), because national codes repeat across countries.

**Self-checks** (all pass): `uv run python scoring.py`, and `--test` on `waves.py`, `build.py`, `community.py`. `cd web && npx tsc -b --noEmit` is clean; one oxlint warning (ref read during render) predates this session.

## Results (built 30 Oct 2026, 1.5 m)
- 2,356 ports → 298 without coordinates (13%), 1 outside Europe (Guadeloupe), 210 no sea cell within 20 km → **1,847 placed**. 611 are > 9 km from their model cell.
- Top of Europe: Thessaloniki, Turku, Kerkyra, Peiraias, Mytilini (~0.81–0.86).
- Azores: Ponta Delgada 0.37 (#1,050) … Praia da Vitória 0.15 (#1,806); 9 of 11 "limited by swell". Within the Azores the order is stable: Ponta Delgada, Horta, Vila Franca.
- Europe-wide limiting: few small boats 1,524, tourist access 270, swell 53.
- Oulu: 214 viable days after the sea-ice fix (was 365).
- Suggest the pitch uses the Europe rank as context, not the headline: Atlantic swell vs calm Med/Baltic dominates it.

## Run
```sh
cd pescamare
uv run python build.py                 # ~36 s when caches exist; ~40 min cold (waves) + ~25 min OSM
uv run uvicorn api:app --port 8000     # no --reload: restart after api.py or db schema changes
cd web && npx vite --port 5173 --strictPort    # proxies /api to :8000
```
The API and Vite may still be running from this session (ports 8000 / 5173).

## Caches (`data/cache/`, git-ignored; delete a file to refetch)
- `waves/<code>.json`: ~2,046 files, Europe history up to 30 Oct 2026. Delete all if wave logic changes (a full refetch is ~40 min, run it in the background). Dropped harbours (no sea cell) are cached too.
- `osm_<CC>.json`: all 22 countries.
- `geonames/<CC>.zip`, `nuts2.geojson`: auto-downloaded by `build.py` when missing.

## Gotchas found this session
- **Overpass returns 502 often.** 5 of 22 countries failed first time and succeeded on retry a minute later. DE/FR take ~3 min each.
- **Sea ice:** the global wave model has NaN under ice (Oulu Dec–Apr). Handled. But Turku/Vaasa have data all winter and come out at ~364 viable days, so the model may report small waves under ice; listed as a limitation, not fixed (would need a Copernicus sea-ice product).
- **Eurostat codes Greece as `EL`**, not `GR` (handled in `regions()`).
- **`pkill`/`pgrep -f` with the pattern in the same command kills your own shell** (exit 144). Find PIDs in one call, `ps -o pid,cmd -p` to confirm, then `kill` in another.
- **TypeScript lib** doesn't include `Object.groupBy`; a small `counts()` helper in `App.tsx` does it.
- Copernicus `open_dataset` is thread-safe enough: 16 threads ≈ 50 harbours/min.
- Carried over: Chrome extension not connected, so use Playwright with system Chrome (`uv run --with playwright python script.py`, `executable_path="/usr/bin/google-chrome"`, `--use-angle=swiftshader --enable-unsafe-swiftshader`, wait ~5 s for tiles). Keep `optimizeDeps.exclude: ['maplibre-gl']`. Quote URLs with `?` in zsh. Ignore the `VIRTUAL_ENV` warning from uv.

## Small open items
- Denmark lists "Karrebæksminde" twice (two registration codes, same name). Could show the code in the row.
- Some GeoNames placements are wrong but within 20 km of sea (e.g. one inland dot near Spili, Crete). The detail panel already warns.
- **Unplaced ports (509, 16% of small boats): deferred by the user.** Plan is in DESIGN.md "Later: unplaced ports" (override CSV for ~30 big ports, Greek transliteration, keep the 20 km rule, regional wave products need an ADR).

## Next: slice 4 (fishing pressure)
DESIGN.md "Headroom (F4)" + build plan row 4:
- EMODnet Human Activities fishing intensity, **static gears**, 0.05° cells; WMS tiles on the map.
- Local pressure per pilot harbour = fishing hours within 6 nm ÷ highest harbour's; Headroom = 1 − local pressure (stock penalty = 1 until slice 5).
- `scoring.score` needs Headroom in the product for pilot harbours only; non-pilot stay **Partial score** (Community × Viability).
- Detail panel: replace the Headroom "coming next" bar.

## User preferences
- Vertical slices, each verified in a browser before the next starts.
- Ponytail mode: minimal code, one runnable check per non-trivial piece of logic.
- Ask before judgement calls that change scoring (they chose log scale for boats and places this session).
- Be honest about novelty and limitations.
- Use `dataviz` for any chart/colour scale; `ui-ux-pro-max`, `ui-styling`, `design-system` in slice 10.
- Don't commit or push without being asked.
