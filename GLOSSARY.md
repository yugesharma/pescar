# PescaMare

Planning for pescatourism: where it is viable, how much each site can sustain, and whether to go out on a given day.

## Sea state

**Harbour**:
An EU port of registration in European waters with at least one licensed vessel under 12 m, treated as the place trips depart from; its small boats are the boats registered there.
_Avoid_: site, marina, town

**Pilot harbour**:
One of the 11 Azorean harbours: the demo's focus, and the only harbours with a full harbour score.
_Avoid_: featured harbour, demo port

**Partial score**:
Community × Viability, shown for harbours outside the pilot until pressure and stock data exist for them.
_Avoid_: preliminary score, basic score

**Port of registration**:
The port a vessel is registered to in the EU Fleet Register; not necessarily where it works or where trips depart.
_Avoid_: home port, base

**Model cell**:
The nearest wave-model grid cell with sea data to a harbour; all wave figures for that harbour come from it.
_Avoid_: grid point, pixel, sea point

**Trip window**:
The hours of the local day during which a trip is at sea (default 08:00–14:59 in the harbour's own time zone).
_Avoid_: trip hours, working window

**Wave limit**:
The significant wave height (Hs) a trip window must stay below for a trip to run.
_Avoid_: threshold, cut-off, sea-state limit

**Viable day**:
A day on which the worst Hs in the trip window is below the wave limit.
_Avoid_: calm day, workable day, good day

**Viability**:
The share of days that are viable, for a harbour, wave limit and week of the year.
_Avoid_: workability, weather window, P(go)

**Trip status**:
GO, MARGINAL or NO-GO for a harbour on a forecast day: below the wave limit, up to 0.3 m above it, or worse.
_Avoid_: go/no-go flag, forecast status

## Harbour score

**Harbour score**:
Community × Viability × Attractiveness × Headroom, each divided by the best value across all European harbours so the best scores 1; a ranking, not an absolute measure.
_Avoid_: investment score, rating, index

**Community**:
How able a harbour is to run trips: its active small-scale vessels (under 12 m), local support, and tourist access.
_Avoid_: capacity, fleet score

**Viable days per year**:
Expected viable days in a year at the default wave limit (1.5 m); the input to the Viability factor and to income potential.
_Avoid_: season length, operating days

**Attractiveness**:
Habitat suitability for the target species near a harbour: where those fish are likely, never where they are seen.
_Avoid_: fish abundance, catch potential

**Headroom**:
How much extra activity the sea near a harbour can take: 1 / (1 + fishing hours × stock penalty / 100 h); never zero except inside no-take zones.
_Avoid_: capacity, sustainability score

**Local pressure**:
AIS fishing hours (Global Fishing Watch) recorded 2 km to 6 nm from a harbour in a year.
_Avoid_: fishing intensity, effort score

**Stock penalty**:
How fragile the fish near a harbour are: species status weights (Overfished 1.0, Unknown 0.7, Healthy 0.4), each counted by the share of the trip area that is that species' habitat.
_Avoid_: stock risk, regional penalty

**Limiting factor**:
The lowest of a harbour's four factors, named in plain words (e.g. "limited by winter swell").
_Avoid_: bottleneck, weakness

## Species

**Species status**:
Overfished, Unknown or Healthy, taken from the latest ICES or ICCAT assessment of the stock a species belongs to; it applies to the whole Azores, never to one harbour.
_Avoid_: stock health, sustainability rating

**Overfished**:
A stock assessed with fishing pressure above the sustainable level (F > FMSY) or stock size below its trigger.
_Avoid_: depleted, endangered, red-listed

**Target species**:
A species that is in local demand and not Overfished; habitat suitability is computed for these.
_Avoid_: focus species, catch species

## Harbour lifecycle

**Candidate**:
A harbour with a harbour score and nothing else; every harbour starts here.

**Investment proposal**:
A plan to fund pescatourism at one harbour: boats to license, training places, budget, target trips per week, notes.
_Avoid_: application, project, bid

**Proposed**:
A harbour that has at least one investment proposal.

**Validated**:
A harbour an authority has approved for pescatourism, with the approval date recorded.
_Avoid_: approved, certified, licensed harbour

**Active**:
A Validated harbour with at least one trip logged.

**Replaced day**:
A trip day on which the boat would otherwise have gone commercial fishing; trips that are not replaced days add to fishing pressure (rebound).
_Avoid_: substitution, swap day

**Trip cap**:
The most trips per week a harbour should run: licensed boats × viable days that week × Headroom, rounded down.
_Avoid_: quota, limit, carrying capacity

**Trip**:
One pescatourism outing logged against a harbour: date, boat, passengers, and whether it replaced a commercial fishing day.
_Avoid_: tour, excursion, booking
