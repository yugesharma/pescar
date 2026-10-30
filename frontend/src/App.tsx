import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import type { Feature, Point } from 'geojson'
import { fmtBearing, NM, rangeBearing, ring, type LngLat } from './geo.ts'

type Trip = { date: string; worst_hs_m: number; status: 'GO' | 'MARGINAL' | 'NO-GO' }
type Summary = {
  code: string; name: string; cc: string; region: string; region_name: string; lat: number; lon: number; pilot: number
  score: number; limiting: string; viable_days: number
}
type Harbour = Summary & {
  cell_km: number; shoulder_days: number; coords: string; rank: number; of: number
  small_boats: number; places: number; transport_km: number; transport: string
  community: number; boats_part: number; tourism_part: number; viability: number; income: number
  fishing_hours: number | null; headroom: number | null; stock_penalty: number | null
  attractiveness: number | null; habitat_share: number | null
  weekly: { week: number; viability: number; trip_cap: number | null }[]; trips: Trip[]
  state: 'Candidate' | 'Proposed' | 'Validated' | 'Active'; proposals: Proposal[]; validation: { date: string; boats: number } | null
  species: { name: string; scientific: string; status: 'Overfished' | 'Unknown' | 'Healthy'; source: string; year: number | null; target: number; share: number | null }[]
}
type Proposal = {
  id: number; boats: number; training: number; budget: number; target: number; notes: string; created: string
  income: number; caps: (number | null)[]; over_weeks: number[]
}
type Watched = {
  code: string; name: string; state: 'Validated' | 'Active'; validated: string; boats: number; demo: boolean
  trips: number; replaced: number; added: number; expected_days: number; used: number | null; over_weeks: number
  weekly: { start: string; trips: number; cap: number | null }[]
}
type Data = { limit_m: number; meta: Record<string, string>; harbours: Summary[] }

const LIMITS = [1.0, 1.5, 2.0]
const FAR_KM = 9  // ~one 0.083° grid cell; closer than this is normal for a coastal harbour
const BLUE = '#2a78d6'
// Sequential blue (light -> dark) for harbour score, 0-1 (best harbour in Europe = 1).
const STOPS: [number, string][] = [[0, '#cde2fb'], [0.33, '#86b6ef'], [0.66, '#256abf'], [1, '#0d366b']]
const color = (prop: string) => ['interpolate', ['linear'], ['get', prop], ...STOPS.flat()] as maplibregl.ExpressionSpecification
const VIEWS: Record<'azores' | 'europe', { center: [number, number]; zoom: number }> = {
  azores: { center: [-28, 38.4], zoom: 6.3 }, europe: { center: [12, 50], zoom: 3.4 },
}
const TOP = 100  // Europe list length; the map shows every harbour
// Range tool: centre, cursor or pinned target. Kept in a ref because map handlers are registered once.
type Range = { on: boolean; center?: LngLat; target?: LngLat; pinned: boolean }
type Label = { x: number; y: number; text: string }
const countryName = new Intl.DisplayNames(['en'], { type: 'region' })
// Scope: all of Europe, one country (ISO code), or one NUTS 2 region in it; filters the list and the map.
type Scope = { cc: string; region: string }  // cc 'europe' = everything; region '' = whole country
const PILOT: Scope = { cc: 'PT', region: 'PT20' }  // Região Autónoma dos Açores = the 11 pilot harbours
const inScope = ({ cc, region }: Scope) => (x: Summary) => cc === 'europe' || (x.cc === cc && (!region || x.region === region))
const counts = <K,>(xs: K[]) => { const m = new Map<K, number>(); for (const x of xs) m.set(x, (m.get(x) ?? 0) + 1); return m }
const fmt = (v: number) => v.toFixed(2)
const pct = (v: number) => `${Math.round(v * 100)}%`
// EMODnet static-gear fishing hours (ICES VMS, vessels of 12 m and over); latest ICES edition per ecoregion.
const EMODNET = 'https://ows.emodnet-humanactivities.eu/wms?service=WMS&version=1.1.1&layers=emodnet:fishingstaticgears'
const PRESSURE_TILES = `${EMODNET}&request=GetMap&styles=&format=image/png&transparent=true&srs=EPSG:3857&width=256&height=256`
  + `&bbox={bbox-epsg-3857}&CQL_FILTER=${encodeURIComponent("fo_year=2025 OR (ecoregn='Celtic Seas' AND fo_year=2024)")}`
const PRESSURE_LEGEND = `${EMODNET.replace('layers=', 'layer=')}&request=GetLegendGraphic&format=image/png`
// Copernicus Marine WMTS, live. Each layer shows its dataset's default time (the step nearest now), read from the
// dataset's own capabilities so the tiles and the label agree. Colour ranges chosen with the user.
const CMEMS = 'https://wmts.marine.copernicus.eu/teroWmts'
const OCEAN = [
  { id: 'chl', name: 'Chlorophyll', style: 'cmap:algae,logScale,range:0.05/2',
    layer: 'OCEANCOLOUR_GLO_BGC_L4_NRT_009_102/cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D_202311/CHL' },
  { id: 'thetao', name: 'Sea temperature', style: 'cmap:thermal',
    layer: 'GLOBAL_ANALYSISFORECAST_PHY_001_024/cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m_202406/thetao' },
  { id: 'waves', name: 'Wave height', style: 'cmap:amp,range:0/4', hourly: true,
    layer: 'GLOBAL_ANALYSISFORECAST_WAV_001_027/cmems_mod_glo_wav_anfc_0.083deg_PT3H-i_202411/VHM0' },
]
// Dark vessels: GFW radar detections without AIS, dot area ∝ detections per 0.1° cell. Amber passes the palette
// validator against the harbour blue and the fronts red.
const DARK = '#c98500'
const darkRadius = (n: maplibregl.ExpressionSpecification) =>  // the legend computes the same line
  ['interpolate', ['linear'], ['sqrt', n], 1, 3, 7, 10] as maplibregl.ExpressionSpecification
const DARK_KEY = [1, 5, 20]
const dayMonth = (d: string) => new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
const oceanQuery = (o: typeof OCEAN[number]) => `${CMEMS}?SERVICE=WMTS&LAYER=${o.layer}&STYLE=${o.style}`
async function latestTime(layer: string) {
  const dataset = layer.slice(0, layer.lastIndexOf('/'))
  const xml = new DOMParser().parseFromString(
    await (await fetch(`${CMEMS}/${dataset}?SERVICE=WMTS&REQUEST=GetCapabilities`)).text(), 'text/xml')
  const dim = [...xml.getElementsByTagNameNS('*', 'Dimension')]
    .find(d => d.getElementsByTagNameNS('*', 'Identifier')[0]?.textContent === 'time')
  return dim?.getElementsByTagNameNS('*', 'Default')[0]?.textContent ?? undefined
}

export default function App() {
  const [limit, setLimit] = useState(1.5)
  const [data, setData] = useState<Data>()
  const [code, setCode] = useState<string>()
  const [loaded, setH] = useState<Harbour>()
  const [rev, setRev] = useState(0)
  const [view, setView] = useState<'explore' | 'monitor'>('explore')  // bumped after a save, to refetch the harbour
  const h = loaded?.code === code ? loaded : undefined  // never show the previous harbour
  const [scope, setScope] = useState<Scope>(PILOT)
  const [pressure, setPressure] = useState(false)
  const [fronts, setFronts] = useState(false)
  const [ocean, setOcean] = useState<Record<string, boolean>>({})
  const [times, setTimes] = useState<Record<string, string>>({})
  const [dark, setDark] = useState(false)
  const [darkDates, setDarkDates] = useState<string>()
  const [ranging, setRanging] = useState(false)
  const [label, setLabel] = useState<Label>()
  const rng = useRef<Range>({ on: false, pinned: false })
  const mapEl = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map>(null)
  const all = data?.harbours ?? []  // ranked by score
  const inView = all.filter(inScope(scope))
  const inViewRef = useRef(inView)
  inViewRef.current = inView

  useEffect(() => {
    fetch(`/api/harbours?limit=${limit}`).then(r => r.json()).then(setData)
  }, [limit])

  useEffect(() => {
    if (code) fetch(`/api/harbours/${code}?limit=${limit}`).then(r => r.json()).then(setH)
  }, [code, limit, rev])

  const changeScope = (v: Scope) => {
    setScope(v); setCode(undefined)
    if (v.cc === 'europe') return map.current?.flyTo({ ...VIEWS.europe })
    const pts = all.filter(inScope(v))
    const lons = pts.map(x => x.lon), lats = pts.map(x => x.lat)
    map.current?.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 40, maxZoom: 9 })
  }
  const countries = [...counts(all.map(x => x.cc))].map(([cc, n]) => ({ cc, name: countryName.of(cc) ?? cc, n }))
    .sort((a, b) => a.name.localeCompare(b.name))
  const regionNames = new Map(all.map(x => [x.region, x.region_name]))
  const regions = [...counts(all.filter(x => x.cc === scope.cc).map(x => x.region))]
    .map(([id, n]) => ({ id, name: regionNames.get(id)!, n })).sort((a, b) => a.name.localeCompare(b.name))
  const select = (s: Summary) => { setCode(s.code); map.current?.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.current.getZoom(), 8) }) }

  useEffect(() => {
    const m = new maplibregl.Map({
      container: mapEl.current!, style: 'https://tiles.openfreemap.org/styles/positron', ...VIEWS.azores, attributionControl: { compact: true },
    })
    m.on('load', () => {
      m.addSource('pressure', { type: 'raster', tiles: [PRESSURE_TILES], tileSize: 256, attribution: 'EMODnet Human Activities, ICES' })
      m.addLayer({ id: 'pressure', type: 'raster', source: 'pressure', layout: { visibility: 'none' }, paint: { 'raster-opacity': 0.8 } })
      m.addSource('dark', { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, attribution: 'Global Fishing Watch' })
      m.addLayer({ id: 'dark', type: 'circle', source: 'dark', layout: { visibility: 'none' }, paint: {
        'circle-color': DARK, 'circle-opacity': 0.85, 'circle-radius': darkRadius(['get', 'detections']),
        'circle-stroke-width': 1, 'circle-stroke-color': '#fff' } })
      const tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
      m.on('mousemove', 'dark', e => { if (!rng.current.on) tip.setLngLat(e.lngLat)
        .setText(((n: number) => `${n} radar detection${n === 1 ? '' : 's'} without AIS`)(e.features![0].properties.detections)).addTo(m) })
      m.on('mouseleave', 'dark', () => tip.remove())
      // Clusters below zoom 8; each is coloured by the best harbour score inside it.
      m.addSource('harbours', {
        type: 'geojson', data: { type: 'FeatureCollection', features: [] },
        cluster: true, clusterMaxZoom: 7, clusterRadius: 30, clusterProperties: { best: ['max', ['get', 'score']] },
      })
      m.addLayer({
        id: 'clusters', type: 'circle', source: 'harbours', filter: ['has', 'point_count'],
        paint: {
          'circle-color': color('best'), 'circle-stroke-width': 2, 'circle-stroke-color': '#fff',
          'circle-radius': ['step', ['get', 'point_count'], 11, 10, 14, 50, 18],
        },
      })
      m.addLayer({
        id: 'cluster-count', type: 'symbol', source: 'harbours', filter: ['has', 'point_count'],
        layout: { 'text-field': '{point_count_abbreviated}', 'text-font': ['Noto Sans Regular'], 'text-size': 11 },
        paint: { 'text-color': '#1f1f1e', 'text-halo-color': '#fff', 'text-halo-width': 1.5 },
      })
      m.addLayer({
        id: 'harbours', type: 'circle', source: 'harbours', filter: ['!', ['has', 'point_count']],
        paint: { 'circle-radius': 6, 'circle-color': color('score'), 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' },
      })
      // Pilot harbours (full score): never clustered, larger, dark ring, drawn on top.
      m.addSource('pilot', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({
        id: 'pilot', type: 'circle', source: 'pilot',
        paint: { 'circle-radius': 9, 'circle-color': color('score'), 'circle-stroke-width': 2, 'circle-stroke-color': '#1f1f1e' },
      })
      // Range tool: drawn on top of everything.
      m.addSource('range', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'range-rings', type: 'line', source: 'range', filter: ['has', 'ring'],
        paint: { 'line-color': '#1f1f1e', 'line-opacity': 0.5, 'line-width': 1, 'line-dasharray': [4, 3] } })
      m.addLayer({ id: 'range-line', type: 'line', source: 'range', filter: ['==', ['geometry-type'], 'LineString'],
        paint: { 'line-color': '#1f1f1e', 'line-width': ['case', ['has', 'ring'], 0, 2] } })
      m.addLayer({ id: 'range-centre', type: 'circle', source: 'range', filter: ['==', ['geometry-type'], 'Point'],
        paint: { 'circle-radius': 4, 'circle-color': '#1f1f1e', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' } })
      // Click 1 sets the centre (snaps to a harbour), click 2 pins the target, click 3 starts again.
      m.on('click', e => {
        const r = rng.current
        if (!r.on) return
        const hit = m.queryRenderedFeatures(e.point, { layers: ['pilot', 'harbours'] })[0]
        const pt = hit ? (hit.geometry as Point).coordinates as LngLat : [e.lngLat.lng, e.lngLat.lat] as LngLat
        if (!r.center || r.pinned) Object.assign(r, { center: pt, target: undefined, pinned: false })
        else Object.assign(r, { target: pt, pinned: true })
        drawRange(m, r, setLabel)
      })
      m.on('mousemove', e => {
        const r = rng.current
        if (r.on && r.center && !r.pinned) { r.target = [e.lngLat.lng, e.lngLat.lat]; drawRange(m, r, setLabel) }
      })
      m.on('move', () => { if (rng.current.target) drawRange(m, rng.current, setLabel) })  // keep the label on its point
      m.on('click', 'clusters', async e => {
        if (rng.current.on) return
        const f = e.features![0]
        const zoom = await (m.getSource('harbours') as maplibregl.GeoJSONSource).getClusterExpansionZoom(f.properties.cluster_id)
        m.easeTo({ center: (f.geometry as unknown as { coordinates: [number, number] }).coordinates, zoom })
      })
      for (const id of ['harbours', 'pilot']) m.on('click', id, e => { if (!rng.current.on) setCode(e.features![0].properties.code) })
      for (const id of ['harbours', 'pilot', 'clusters']) {
        m.on('mouseenter', id, () => (m.getCanvas().style.cursor = 'pointer'))
        m.on('mouseleave', id, () => (m.getCanvas().style.cursor = rng.current.on ? 'crosshair' : ''))
      }
      map.current = m
      showHarbours(m, inViewRef.current)
    })
    return () => { m.remove(); map.current = null }
  }, [])

  useEffect(() => { if (map.current) showHarbours(map.current, inViewRef.current) }, [data, scope])
  useEffect(() => {  // range tool on/off; R toggles, Esc leaves
    const m = map.current
    rng.current = { on: ranging, pinned: false }
    if (m) { m.getCanvas().style.cursor = ranging ? 'crosshair' : ''; drawRange(m, rng.current, setLabel) }
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('select, textarea, input:not([type=checkbox])')) return  // typing, not a ticked box
      if (e.key === 'r' || e.key === 'R') setRanging(v => !v)
      if (e.key === 'Escape') setRanging(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [ranging])
  useEffect(() => { map.current?.setLayoutProperty('pressure', 'visibility', pressure ? 'visible' : 'none') }, [pressure])
  useEffect(() => {  // added once the build's corners are known; under the harbours
    const m = map.current, corners = data?.meta.fronts_corners
    if (!m || !corners) return
    if (!m.getSource('fronts')) {
      m.addSource('fronts', { type: 'image', url: '/api/layers/fronts.png', coordinates: JSON.parse(corners) })
      m.addLayer({ id: 'fronts', type: 'raster', source: 'fronts', paint: { 'raster-resampling': 'nearest' } }, 'dark')
    }
    m.setLayoutProperty('fronts', 'visibility', fronts ? 'visible' : 'none')
  }, [fronts, data])
  useEffect(() => {  // fetched on first use; the backend refreshes it once a day
    const m = map.current
    if (!m) return
    if (dark && !darkDates) fetch('/api/layers/dark.geojson').then(r => r.json()).then(g => {
      (m.getSource('dark') as maplibregl.GeoJSONSource).setData(g)
      setDarkDates(`${dayMonth(g.start).replace(g.start.slice(5, 7) === g.end.slice(5, 7) ? / .*/ : /$/, '')}–${dayMonth(g.end)}`)
    })
    m.setLayoutProperty('dark', 'visibility', dark ? 'visible' : 'none')
  }, [dark, darkDates])
  useEffect(() => {
    for (const o of OCEAN) latestTime(o.layer).then(t => t && setTimes(v => ({ ...v, [o.id]: t })))
  }, [])
  useEffect(() => {  // added once its time is known; under the fronts and the harbours
    const m = map.current
    if (!m) return
    for (const o of OCEAN) {
      if (!times[o.id]) continue
      if (!m.getSource(o.id)) {
        m.addSource(o.id, { type: 'raster', tileSize: 256, attribution: 'Copernicus Marine Service', tiles: [oceanQuery(o)
          + `&REQUEST=GetTile&TILEMATRIXSET=EPSG:3857&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/png&TIME=${times[o.id]}`] })
        m.addLayer({ id: o.id, type: 'raster', source: o.id, paint: { 'raster-opacity': 0.8 } }, m.getLayer('fronts') ? 'fronts' : 'dark')
      }
      m.setLayoutProperty(o.id, 'visibility', ocean[o.id] ? 'visible' : 'none')
    }
  }, [ocean, times])

  const europe = scope.cc === 'europe'
  const shown = europe ? inView.slice(0, TOP) : inView
  const rankOf = new Map(all.map((x, i) => [x.code, i + 1]))

  return (
    <div className="app">
      <div className="map-wrap">
        <div className="map" ref={mapEl} />
        <button className="range-btn" aria-pressed={ranging} onClick={() => setRanging(v => !v)}
          title="Range and bearing (R). Click a centre, then a target; Esc to leave.">
          ⌖ Range & bearing{ranging && (!rng.current.center || rng.current.pinned ? ' · click a centre' : ' · click to pin')}
        </button>
        {label && <div className="range-label" style={{ left: label.x, top: label.y }}>
          <b>{label.text}</b>
        </div>}
      </div>
      <aside className="panel">
        <h1>PescaMare</h1>
        <div className="tabs" role="tablist">{(['explore', 'monitor'] as const).map(v =>
          <button key={v} role="tab" aria-selected={view === v} onClick={() => setView(v)}>{v[0].toUpperCase() + v.slice(1)}</button>)}
        </div>
        {view === 'monitor' ? <Monitor limit={limit} onOpen={code => {
          const s = all.find(x => x.code === code); setView('explore'); if (s) select(s) }} /> : <>
        <div className="controls">
        <label className="muted scope">Country{' '}
          <select value={scope.cc} onChange={e => changeScope({ cc: e.target.value, region: '' })}>
            <option value="europe">All Europe ({all.length})</option>
            {countries.map(c => <option key={c.cc} value={c.cc}>{c.name} ({c.n})</option>)}
          </select>
        </label>
        {scope.cc !== 'europe' && <label className="muted scope">Region{' '}
          <select value={scope.region} onChange={e => changeScope({ ...scope, region: e.target.value })}>
            <option value="">All of {countryName.of(scope.cc)}</option>
            {regions.map(r => <option key={r.id} value={r.id}>{r.name} ({r.n}){r.id === PILOT.region ? ' · pilot' : ''}</option>)}
          </select>
        </label>}
        <label className="muted scope">Wave limit{' '}
          <select value={limit} onChange={e => setLimit(+e.target.value)}>
            {LIMITS.map(l => <option key={l} value={l}>{l.toFixed(1)} m</option>)}
          </select>
        </label>
        </div>
        <fieldset className="layers"><legend>Map layers</legend>
        <label className="muted scope"><input type="checkbox" checked={pressure} onChange={e => setPressure(e.target.checked)} />{' '}
          Fishing intensity, static gears (EMODnet)</label>
        {pressure && <img height={150} src={PRESSURE_LEGEND} alt="Legend: average MW fishing hours per 0.05° cell" />}
        <label className="muted scope"><input type="checkbox" checked={fronts} onChange={e => setFronts(e.target.checked)} />{' '}
          Fish fronts, sea temperature × chlorophyll{data && ` (${data.meta.fronts_dates})`}</label>
        {fronts && <p className="muted">
          <span className="swatch" style={{ background: 'rgb(214,40,40)' }} /> temperature front{' '}
          <span className="swatch" style={{ background: 'rgb(13,148,136)' }} /> front head-on with chlorophyll (upwelling)
        </p>}
        <label className="muted scope"><input type="checkbox" checked={dark} onChange={e => setDark(e.target.checked)} />{' '}
          Dark vessels, radar detections without AIS (Global Fishing Watch{darkDates && `, ${darkDates}`})</label>
        {dark && <p className="muted">
          {DARK_KEY.map(n => { const r = 3 + 7 * (Math.sqrt(n) - 1) / 6; return <span key={n}>
            <svg width={2 * r + 2} height={2 * r + 2} style={{ verticalAlign: 'middle' }}><circle cx={r + 1} cy={r + 1} r={r} fill={DARK} /></svg>
            {' '}{n}{' '}</span> })}
          detections per 0.1° cell · not evidence of illegal activity
        </p>}
        {OCEAN.map(o => <div key={o.id}>
          <label className="muted scope"><input type="checkbox" checked={!!ocean[o.id]}
            onChange={e => setOcean(v => ({ ...v, [o.id]: e.target.checked }))} />{' '}
            {o.name} (Copernicus Marine{times[o.id] && `, ${o.hourly ? `${times[o.id].slice(0, 16).replace('T', ' ')} UTC` : times[o.id].slice(0, 10)}`})</label>
          {ocean[o.id] && <img height={220} alt={`Legend: ${o.name}`}
            src={`${oceanQuery(o)}&REQUEST=GetLegend&FORMAT=${encodeURIComponent('image/svg+xml')}`} />}
        </div>)}
        </fieldset>

        {code ? (h ? <Detail h={h} limit={limit} onBack={() => setCode(undefined)} onSaved={() => setRev(r => r + 1)} /> : <p className="muted">Loading…</p>) : <>
          <h2>Harbour score</h2>
          <div className="legend" style={{ background: `linear-gradient(to right, ${STOPS.map(s => s[1]).join()})` }} />
          <div className="legend-labels muted">{STOPS.map(([v]) => <span key={v}>{fmt(v)}</span>)}</div>
          <p className="muted">Dark ring: pilot harbour (full score). Others: partial score.</p>
          {data && <p className="muted">{europe ? `Top ${TOP} of ${all.length}` : `${inView.length} harbours · # = rank in Europe`}</p>}
          <ol className="ranked">{shown.map((x, i) => (
            <li key={x.code}><button onClick={() => select(x)}>
              <span className="rank muted">{i + 1}</span>
              <span className="grow">{x.name}{(europe || !scope.region) && <span className="muted"> · {europe ? x.cc : x.region_name}</span>}<br />
                <span className="muted">{x.limiting}{!europe && ` · #${rankOf.get(x.code)} in Europe`}</span></span>
              <span>{fmt(x.score)}</span>
            </button></li>))}
          </ol>
        </>}
        </>}

        {data && <p className="muted">
          Sources: Copernicus Marine, EU Fleet Register, OpenStreetMap, Global Fishing Watch, EMODnet, ICES, ICCAT, AquaMaps, FishBase.
          Built {data.meta.built_at}.
        </p>}
      </aside>
    </div>
  )
}

function showHarbours(m: maplibregl.Map, harbours: Summary[]) {
  for (const [source, pilot] of [['harbours', 0], ['pilot', 1]] as const) {
    (m.getSource(source) as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: harbours.filter(h => h.pilot === pilot).map(h => ({
        type: 'Feature', geometry: { type: 'Point', coordinates: [h.lon, h.lat] },
        properties: { code: h.code, score: h.score },
      })),
    })
  }
}

function Factor({ name, value, note }: { name: string; value?: number; note: string }) {
  return <div className="factor">
    <div className="factor-head"><span>{name}</span><span>{value === undefined ? '–' : fmt(value)}</span></div>
    <div className="track">{value !== undefined && <div className="fill" style={{ width: `${value * 100}%` }} />}</div>
    <div className="muted">{note}</div>
  </div>
}

function Detail({ h, limit, onBack, onSaved }: { h: Harbour; limit: number; onBack: () => void; onSaved: () => void }) {
  return <>
    <h2>{h.name} <span className="muted">{h.code}</span></h2>
    <button className="btn" onClick={onBack}>← All harbours</button>
    {h.cell_km > FAR_KM && <p className="warning">⚠ Wave model cell {h.cell_km} km away</p>}
    {h.coords === 'GeoNames' && <p className="warning">⚠ Location from GeoNames name match</p>}
    <div className="stats">
      <div><b>{fmt(h.score)}</b><span className="muted">{h.pilot ? 'harbour score' : 'partial score'} · #{h.rank} of {h.of}</span></div>
      <div><b>€{h.income.toLocaleString('en-GB')}</b><span className="muted">income potential per boat / year</span></div>
    </div>
    <p><strong>{h.limiting[0].toUpperCase() + h.limiting.slice(1)}</strong></p>
    <h2>Factors</h2>
    <Factor name="Community" value={h.community}
      note={`${h.small_boats} small boats · ${h.places} places to stay within 10 km · ${h.transport || 'airport/ferry'} ${h.transport_km} km`} />
    <Factor name="Viability" value={h.viability} note="viable days per year at 1.5 m, vs the best harbour in Europe" />
    <Factor name="Attractiveness" value={h.attractiveness ?? undefined} note={h.habitat_share === null
      ? 'pilot harbours only'
      : `${pct(h.habitat_share)} of the trip area is target-species habitat, year average`} />
    <Factor name="Headroom" value={h.headroom ?? undefined} note={h.fishing_hours === null
      ? 'pilot harbours only'
      : `${Math.round(h.fishing_hours)} AIS fishing hours / year within 6 nm · stock penalty ${fmt(h.stock_penalty!)}`} />
    {h.headroom !== null && <p className="muted">Trip cap per licensed boat:{' '}
      {Math.min(...h.weekly.map(w => w.trip_cap!))}–{Math.max(...h.weekly.map(w => w.trip_cap!))} trips / week at {limit.toFixed(1)} m</p>}
    <h2>Waves at {limit.toFixed(1)} m</h2>
    <div className="stats">
      <div><b>{Math.round(h.viable_days)}</b><span className="muted">viable days / year</span></div>
      <div><b>{Math.round(h.shoulder_days)}</b><span className="muted">in shoulder season (of 152)</span></div>
    </div>
    <h2>Season curve</h2>
    <p className="muted">Share of viable days by week of the year at {limit.toFixed(1)} m. Shaded: shoulder season.</p>
    <SeasonCurve key={`${h.code}-${limit}`} weekly={h.weekly} />
    {h.species.some(s => s.share !== null) && <>
      <h2>Species</h2>
      <table><tbody>{h.species.map(s => (
        <tr key={s.name}>
          <td><span title={s.scientific}>{s.name}</span>{s.target ? <span className="muted"> · target</span> : ''}<br />
            <span className="muted">{s.source}{s.year ? `, ${s.year}` : ''}</span></td>
          <td className="muted" style={{ whiteSpace: 'nowrap', padding: '0 8px' }}>{s.share === null ? '' : `${pct(s.share)} habitat`}</td>
          <td><span className={`status ${s.status}`}>{s.status}</span></td>
        </tr>))}
      </tbody></table>
    </>}
    <Invest key={h.code} h={h} limit={limit} onSaved={onSaved} />
    {h.trips.length > 0 && <h2>Next 3 days</h2>}
    <table><tbody>{h.trips.map(t => (
      <tr key={t.date}>
        <td>{new Date(t.date).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })}</td>
        <td>worst Hs {t.worst_hs_m.toFixed(1)} m</td>
        <td><span className={`status ${t.status}`}>{t.status}</span></td>
      </tr>))}
    </tbody></table>
  </>
}

const eur = (v: number) => `€${Math.round(v).toLocaleString('en-GB')}`
const today = () => new Date().toISOString().slice(0, 10)
// Weeks as runs: [1,2,3,7,8] -> "1–3, 7–8"
const runs = (ws: number[]) => ws.reduce<number[][]>((a, w) => {
  const last = a.at(-1)
  if (last && w === last[1] + 1) last[1] = w; else a.push([w, w])
  return a
}, []).map(([a, b]) => a === b ? `${a}` : `${a}–${b}`).join(', ')
async function post(url: string, body: object) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (r.ok) return
  const d = (await r.json()).detail
  throw new Error(typeof d === 'string' ? d : d.map((e: { loc: string[]; msg: string }) => `${e.loc.at(-1)}: ${e.msg}`).join('; '))
}

const FIELDS = [['boats', 'Boats to license'], ['training', 'Training places'], ['budget', 'Budget (€)'], ['target', 'Target trips / week']] as const

function Invest({ h, limit, onSaved }: { h: Harbour; limit: number; onSaved: () => void }) {
  const [form, setForm] = useState({ boats: 2, training: 4, budget: 50000, target: 6, notes: '' })
  const [error, setError] = useState<string>()
  const [picked, setPicked] = useState<number>()
  const [vDate, setVDate] = useState(today())
  const shown = h.proposals.find(p => p.id === picked) ?? h.proposals[0]
  const [vBoats, setVBoats] = useState<number>()
  const save = (url: string, body: object) => post(url, body).then(() => { setError(undefined); onSaved() }, e => setError(e.message))
  return <>
    <h2>Invest <span className={`status ${h.state}`}>{h.state}</span></h2>
    <form className="invest" onSubmit={e => { e.preventDefault(); save(`/api/harbours/${h.code}/proposals`, form) }}>
      {FIELDS.map(([k, name]) => <label key={k} className="muted">{name}
        <input type="number" min={k === 'boats' ? 1 : 0} required value={form[k]} onChange={e => setForm({ ...form, [k]: +e.target.value })} />
      </label>)}
      <label className="muted wide">Notes<textarea rows={2} maxLength={2000} value={form.notes}
        onChange={e => setForm({ ...form, notes: e.target.value })} /></label>
      <p className="muted wide">Projected income {eur(h.income * form.boats)} / year vs budget {eur(form.budget)}</p>
      <button className="wide btn primary">Save proposal</button>
    </form>
    {error && <p className="warning">⚠ {error}</p>}
    {h.proposals.length > 0 && <>
      <h2>Proposals</h2>
      <table className="proposals"><tbody>{h.proposals.map(p => (
        <tr key={p.id} className={p === shown ? 'picked' : ''} tabIndex={0}
          onClick={() => setPicked(p.id)} onKeyDown={e => e.key === 'Enter' && setPicked(p.id)}>
          <td>{dayMonth(p.created)}<br /><span className="muted">{p.boats} boats · {p.training} training · {p.target} trips/wk</span>
            {p.notes && <><br /><span className="muted">{p.notes}</span></>}</td>
          <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{eur(p.budget)}<br /><span className="muted">{eur(p.income)} / yr</span></td>
          <td>{p.caps[0] === null ? <span className="muted">no cap</span>
            : p.over_weeks.length ? <span className="status over">⚠ {p.over_weeks.length} wk</span>
            : <span className="status Healthy">✓ cap</span>}</td>
        </tr>))}
      </tbody></table>
      {shown.caps[0] === null ? <p className="muted">Trip cap: pilot harbours only</p> : <>
        <p className={shown.over_weeks.length ? 'warning' : 'muted'}>{shown.over_weeks.length
          ? `⚠ ${shown.target} trips / week is over the cap in ${shown.over_weeks.length} weeks: ${runs(shown.over_weeks)}`
          : `${shown.target} trips / week is within the cap every week`} ({shown.boats} boats, {limit.toFixed(1)} m)</p>
        <CapChart key={shown.id} weekly={h.weekly} p={shown} />
      </>}
      {h.validation ? <p>Validated {dayMonth(h.validation.date)} {h.validation.date.slice(0, 4)} · {h.validation.boats} licensed boats</p>
        : <form className="invest" onSubmit={e => { e.preventDefault()
          save(`/api/harbours/${h.code}/validation`, { date: vDate, boats: vBoats ?? shown.boats }) }}>
          <label className="muted">Validation date<input type="date" required value={vDate} onChange={e => setVDate(e.target.value)} /></label>
          <label className="muted">Licensed boats<input type="number" min={1} required value={vBoats ?? shown.boats}
            onChange={e => setVBoats(+e.target.value)} /></label>
          <button className="wide btn primary">Mark Validated</button>
        </form>}
    </>}
  </>
}

const INK = '#1f1f1e', OVER = '#fff4dc'
const TRIPS = BLUE, OVER_BAR = '#eb6834', ADDED = '#eb6834'  // palette slots 1 and 2

function Monitor({ limit, onOpen }: { limit: number; onOpen: (code: string) => void }) {
  const [list, setList] = useState<Watched[]>()
  const [rev, setRev] = useState(0)
  useEffect(() => { fetch(`/api/monitor?limit=${limit}`).then(r => r.json()).then(d => setList(d.harbours)) }, [limit, rev])
  if (!list) return <p className="muted">Loading…</p>
  if (!list.length) return <p className="muted">No Validated harbours yet. Validate one from its Invest section.</p>
  return <>{list.map(w => <section key={w.code} className="watched">
    <h2><button className="link" onClick={() => onOpen(w.code)}>{w.name}</button>{' '}
      <span className={`status ${w.state}`}>{w.state}</span>{w.demo && <span className="demo">demo data</span>}</h2>
    <p className="muted">Validated {dayMonth(w.validated)} {w.validated.slice(0, 4)} · {w.boats} licensed boats</p>
    <div className="stats">
      <div><b>{w.trips}</b><span className="muted">trips made</span></div>
      <div><b>{w.used === null ? '–' : pct(w.used)}</b><span className="muted">of typical viable boat-days used ({Math.round(w.expected_days)})</span></div>
    </div>
    {w.trips > 0 && <>
      <div className="split" role="img" aria-label={`${w.replaced} replaced, ${w.added} added fishing days`}>
        <div style={{ flex: w.replaced, background: BLUE }} /><div style={{ flex: w.added, background: ADDED }} />
      </div>
      <p className="muted"><span className="swatch" style={{ background: BLUE }} /> {w.replaced} replaced a fishing day{' '}
        <span className="swatch" style={{ background: ADDED }} /> {w.added} added ({pct(w.added / w.trips)})</p>
    </>}
    {w.weekly[0]?.cap === null ? <p className="muted">Trip cap: pilot harbours only</p> : <>
      <p className={w.over_weeks ? 'warning' : 'muted'}>{w.over_weeks
        ? `⚠ Over the trip cap in ${w.over_weeks} of ${w.weekly.length} weeks` : `Within the trip cap every week`} ({limit.toFixed(1)} m)</p>
      <WeekBars weekly={w.weekly} />
    </>}
    <TripForm code={w.code} since={w.validated} onSaved={() => setRev(r => r + 1)} />
  </section>)}</>
}

function TripForm({ code, since, onSaved }: { code: string; since: string; onSaved: () => void }) {
  const [t, setT] = useState({ date: today(), boat: 'Boat 1', passengers: 4, replaced: true })
  const [error, setError] = useState<string>()
  return <details><summary>Log a trip</summary>
    <form className="invest" onSubmit={e => { e.preventDefault()
      post(`/api/harbours/${code}/trips`, t).then(() => { setError(undefined); onSaved() }, e => setError(e.message)) }}>
      <label className="muted">Date<input type="date" required min={since} max={today()} value={t.date}
        onChange={e => setT({ ...t, date: e.target.value })} /></label>
      <label className="muted">Boat<input required maxLength={100} value={t.boat} onChange={e => setT({ ...t, boat: e.target.value })} /></label>
      <label className="muted">Passengers<input type="number" min={1} max={50} required value={t.passengers}
        onChange={e => setT({ ...t, passengers: +e.target.value })} /></label>
      <label className="muted check"><input type="checkbox" checked={t.replaced} onChange={e => setT({ ...t, replaced: e.target.checked })} />
        Replaced a fishing day</label>
      <button className="wide btn primary">Save trip</button>
    </form>
    {error && <p className="warning">⚠ {error}</p>}
  </details>
}

function WeekBars({ weekly }: { weekly: Watched['weekly'] }) {
  const [hover, setHover] = useState<number>()
  const top = Math.max(1, ...weekly.flatMap(w => [w.trips, w.cap!])) * 1.1
  const yc = (v: number) => T + (1 - v / top) * (H - T - B)
  const step = (W - L - 4) / weekly.length
  const ticks = [0, Math.round(top / 2.2), Math.round(top / 1.1)]
  const capPath = weekly.map((w, i) => `${i ? 'L' : 'M'}${L + i * step},${yc(w.cap!)}H${L + (i + 1) * step}`).join('')
  const hw = hover === undefined ? undefined : weekly[hover]
  return <>
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Trips per week and trip cap"
      onMouseLeave={() => setHover(undefined)} onMouseMove={e => {
        const r = e.currentTarget.getBoundingClientRect()
        const i = Math.floor((((e.clientX - r.left) / r.width) * W - L) / step)
        setHover(i >= 0 && i < weekly.length ? i : undefined) }}>
      {ticks.map(v => <g key={v}>
        <line x1={L} x2={W - 4} y1={yc(v)} y2={yc(v)} stroke="#e4e3df" />
        <text x={L - 4} y={yc(v) + 4} fontSize="10" textAnchor="end" fill="#6b6a66">{v}</text>
      </g>)}
      {weekly.map((w, i) => <g key={w.start}>
        {w.trips > 0 && <rect x={L + i * step + 1} y={yc(w.trips)} width={Math.max(1, step - 2)} height={yc(0) - yc(w.trips)}
          rx="2" fill={w.trips > w.cap! ? OVER_BAR : TRIPS} opacity={hover === undefined || hover === i ? 1 : 0.6} />}
        {(i ? w.start.slice(5, 7) !== weekly[i - 1].start.slice(5, 7) : w.start.slice(5, 7) === weekly[2]?.start.slice(5, 7)) &&
          <text x={L + i * step} y={H - 4} fontSize="10" fill="#6b6a66">{MONTHS[+w.start.slice(5, 7) - 1]}</text>}
      </g>)}
      <path d={capPath} fill="none" stroke={INK} strokeWidth="2" />
    </svg>
    <p className="muted">
      <span className="swatch" style={{ background: TRIPS }} /> trips{' '}
      <span className="swatch" style={{ background: OVER_BAR }} /> ⚠ over cap{' '}
      <span className="swatch" style={{ background: INK }} /> trip cap
    </p>
    <p className="muted">{hw ? `Week of ${dayMonth(hw.start)}: ${hw.trips} trips, cap ${hw.cap}${hw.trips > hw.cap! ? ' · ⚠ over cap' : ''}`
      : 'Hover the chart for weekly values.'}</p>
  </>
}

function CapChart({ weekly, p }: { weekly: Harbour['weekly']; p: Proposal }) {
  const [hover, setHover] = useState<number>()  // index into weekly
  const top = Math.max(1, p.target, ...p.caps.map(c => c!)) * 1.1
  const yc = (v: number) => T + (1 - v / top) * (H - T - B)
  const step = (W - L - 4) / 52
  const over = new Set(p.over_weeks)
  const path = weekly.map((w, i) => `${i ? 'L' : 'M'}${x(w.week)},${yc(p.caps[i]!)}H${x(w.week) + step}`).join('')
  const ticks = [0, Math.round(top / 2.2), Math.round(top / 1.1)]
  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const i = Math.floor((((e.clientX - r.left) / r.width) * W - L) / step)
    setHover(i >= 0 && i < weekly.length ? i : undefined)
  }
  const hw = hover === undefined ? undefined : weekly[hover]
  return (<>
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" onMouseMove={onMove} onMouseLeave={() => setHover(undefined)}
      role="img" aria-label={`Trip cap and target trips per week; over the cap in ${p.over_weeks.length} weeks`}>
      {weekly.filter(w => over.has(w.week)).map(w =>
        <rect key={w.week} x={x(w.week)} y={T} width={step} height={H - T - B} fill={OVER} />)}
      {ticks.map(v => <g key={v}>
        <line x1={L} x2={W - 4} y1={yc(v)} y2={yc(v)} stroke="#e4e3df" />
        <text x={L - 4} y={yc(v) + 4} fontSize="10" textAnchor="end" fill="#6b6a66">{v}</text>
      </g>)}
      {[...MONTHS].map((m, i) => <text key={i} x={x(weekOf(i + 0.5))} y={H - 4} fontSize="10" textAnchor="middle" fill="#6b6a66">{m}</text>)}
      <path d={path} fill="none" stroke={BLUE} strokeWidth="2" />
      <line x1={L} x2={W - 4} y1={yc(p.target)} y2={yc(p.target)} stroke={INK} strokeWidth="2" strokeDasharray="5 3" />
      {hw && <line x1={x(hw.week) + step / 2} x2={x(hw.week) + step / 2} y1={T} y2={H - B} stroke="#9a9993" />}
    </svg>
    <p className="muted">
      <span className="swatch" style={{ background: BLUE }} /> trip cap{' '}
      <span className="swatch" style={{ background: INK }} /> target{' '}
      <span className="swatch" style={{ background: OVER, outline: '1px solid #fab219' }} /> ⚠ over cap
    </p>
    <p className="muted">{hw ? `Week ${hw.week}: cap ${p.caps[hover!]} trips, target ${p.target}${over.has(hw.week) ? ' · ⚠ over cap' : ''}`
      : 'Hover the chart for weekly values.'}</p>
  </>)
}

const W = 300, H = 130, L = 28, B = 18, T = 8
const MONTHS = 'JFMAMJJASOND'
const x = (week: number) => L + ((week - 1) / 52) * (W - L - 4)
const y = (v: number) => T + (1 - v) * (H - T - B)
const weekOf = (month: number) => 1 + (month * 52) / 12  // start of month (0-based), approx.

function SeasonCurve({ weekly }: { weekly: Harbour['weekly'] }) {
  const [hover, setHover] = useState<Harbour['weekly'][number]>()
  const path = weekly.map((p, i) => `${i ? 'L' : 'M'}${x(p.week)},${y(p.viability)}`).join('')
  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    setHover(weekly.reduce((a, b) => Math.abs(x(b.week) - px) < Math.abs(x(a.week) - px) ? b : a))
  }
  return (<>
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" onMouseMove={onMove} onMouseLeave={() => setHover(undefined)}
      role="img" aria-label="Viability by week of the year">
      {[[3, 6], [8, 10]].map(([a, b]) => (
        <rect key={a} x={x(weekOf(a))} y={T} width={x(weekOf(b)) - x(weekOf(a))} height={H - T - B} fill="#f0efec" />))}
      {[0, 0.5, 1].map(v => <g key={v}>
        <line x1={L} x2={W - 4} y1={y(v)} y2={y(v)} stroke="#e4e3df" />
        <text x={L - 4} y={y(v) + 4} fontSize="10" textAnchor="end" fill="#6b6a66">{v * 100}%</text>
      </g>)}
      {[...MONTHS].map((m, i) => <text key={i} x={x(weekOf(i + 0.5))} y={H - 4} fontSize="10" textAnchor="middle" fill="#6b6a66">{m}</text>)}
      <path d={path} fill="none" stroke={BLUE} strokeWidth="2" strokeLinejoin="round" />
      {hover && <g>
        <line x1={x(hover.week)} x2={x(hover.week)} y1={T} y2={H - B} stroke="#9a9993" />
        <circle cx={x(hover.week)} cy={y(hover.viability)} r="4" fill={BLUE} stroke="#fff" strokeWidth="2" />
      </g>}
    </svg>
    <p className="muted">{hover ? `Week ${hover.week}: ${Math.round(hover.viability * 100)}% of days viable` : 'Hover the curve for weekly values.'}</p>
  </>)
}

function drawRange(m: maplibregl.Map, r: Range, setLabel: (l?: Label) => void) {
  const line = (coordinates: LngLat[], properties = {}) =>
    ({ type: 'Feature' as const, properties, geometry: { type: 'LineString' as const, coordinates } })
  const features: Feature[] = []
  const rb = r.on && r.center && r.target ? rangeBearing(r.center, r.target) : undefined
  if (r.on && r.center) {
    features.push({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: r.center } })
    // ring through the target: follows the cursor
    if (rb) features.push(line(ring(r.center, rb.m), { ring: 1 }), line([r.center, r.target!]))
  }
  (m.getSource('range') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features })
  if (!rb) return setLabel(undefined)
  const p = m.project(r.target!)
  setLabel({ x: p.x, y: p.y, text: `${(rb.m / NM).toFixed(1)} nm · ${fmtBearing(rb.bearing)}` })
}
