import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'

type Trip = { date: string; worst_hs_m: number; status: 'GO' | 'MARGINAL' | 'NO-GO' }
type Summary = {
  code: string; name: string; cc: string; region: string; region_name: string; lat: number; lon: number; pilot: number
  score: number; limiting: string; viable_days: number
}
type Harbour = Summary & {
  cell_km: number; shoulder_days: number; coords: string; rank: number; of: number
  small_boats: number; places: number; transport_km: number; transport: string
  community: number; boats_part: number; tourism_part: number; viability: number; income: number
  fishing_hours: number | null; headroom: number | null
  weekly: { week: number; viability: number }[]; trips: Trip[]
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
const countryName = new Intl.DisplayNames(['en'], { type: 'region' })
// Scope: all of Europe, one country (ISO code), or one NUTS 2 region in it; filters the list and the map.
type Scope = { cc: string; region: string }  // cc 'europe' = everything; region '' = whole country
const PILOT: Scope = { cc: 'PT', region: 'PT20' }  // Região Autónoma dos Açores = the 11 pilot harbours
const inScope = ({ cc, region }: Scope) => (x: Summary) => cc === 'europe' || (x.cc === cc && (!region || x.region === region))
const counts = <K,>(xs: K[]) => { const m = new Map<K, number>(); for (const x of xs) m.set(x, (m.get(x) ?? 0) + 1); return m }
const fmt = (v: number) => v.toFixed(2)
// EMODnet static-gear fishing hours (ICES VMS, vessels of 12 m and over); latest ICES edition per ecoregion.
const EMODNET = 'https://ows.emodnet-humanactivities.eu/wms?service=WMS&version=1.1.1&layers=emodnet:fishingstaticgears'
const PRESSURE_TILES = `${EMODNET}&request=GetMap&styles=&format=image/png&transparent=true&srs=EPSG:3857&width=256&height=256`
  + `&bbox={bbox-epsg-3857}&CQL_FILTER=${encodeURIComponent("fo_year=2025 OR (ecoregn='Celtic Seas' AND fo_year=2024)")}`
const PRESSURE_LEGEND = `${EMODNET.replace('layers=', 'layer=')}&request=GetLegendGraphic&format=image/png`

export default function App() {
  const [limit, setLimit] = useState(1.5)
  const [data, setData] = useState<Data>()
  const [code, setCode] = useState<string>()
  const [loaded, setH] = useState<Harbour>()
  const h = loaded?.code === code ? loaded : undefined  // never show the previous harbour
  const [scope, setScope] = useState<Scope>(PILOT)
  const [pressure, setPressure] = useState(false)
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
  }, [code, limit])

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
      container: mapEl.current!, style: 'https://tiles.openfreemap.org/styles/positron', ...VIEWS.azores,
    })
    m.on('load', () => {
      m.addSource('pressure', { type: 'raster', tiles: [PRESSURE_TILES], tileSize: 256, attribution: 'EMODnet Human Activities, ICES' })
      m.addLayer({ id: 'pressure', type: 'raster', source: 'pressure', layout: { visibility: 'none' }, paint: { 'raster-opacity': 0.8 } })
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
      m.on('click', 'clusters', async e => {
        const f = e.features![0]
        const zoom = await (m.getSource('harbours') as maplibregl.GeoJSONSource).getClusterExpansionZoom(f.properties.cluster_id)
        m.easeTo({ center: (f.geometry as unknown as { coordinates: [number, number] }).coordinates, zoom })
      })
      for (const id of ['harbours', 'pilot']) m.on('click', id, e => setCode(e.features![0].properties.code))
      for (const id of ['harbours', 'pilot', 'clusters']) {
        m.on('mouseenter', id, () => (m.getCanvas().style.cursor = 'pointer'))
        m.on('mouseleave', id, () => (m.getCanvas().style.cursor = ''))
      }
      map.current = m
      showHarbours(m, inViewRef.current)
    })
    return () => { m.remove(); map.current = null }
  }, [])

  useEffect(() => { if (map.current) showHarbours(map.current, inViewRef.current) }, [data, scope])
  useEffect(() => { map.current?.setLayoutProperty('pressure', 'visibility', pressure ? 'visible' : 'none') }, [pressure])

  const europe = scope.cc === 'europe'
  const shown = europe ? inView.slice(0, TOP) : inView
  const rankOf = new Map(all.map((x, i) => [x.code, i + 1]))

  return (
    <div className="app">
      <div className="map" ref={mapEl} />
      <aside className="panel">
        <h1>PescaMare</h1>
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
        <label className="muted">Wave limit{' '}
          <select value={limit} onChange={e => setLimit(+e.target.value)}>
            {LIMITS.map(l => <option key={l} value={l}>{l.toFixed(1)} m</option>)}
          </select>
        </label>
        <label className="muted scope"><input type="checkbox" checked={pressure} onChange={e => setPressure(e.target.checked)} />{' '}
          Fishing intensity, static gears (EMODnet)</label>
        {pressure && <img height={150} src={PRESSURE_LEGEND} alt="Legend: average MW fishing hours per 0.05° cell" />}

        {code ? (h ? <Detail h={h} limit={limit} onBack={() => setCode(undefined)} /> : <p className="muted">Loading…</p>) : <>
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

        {data && <p className="muted">
          Sources: Copernicus Marine, EU Fleet Register, OpenStreetMap, Global Fishing Watch, EMODnet.
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

function Detail({ h, limit, onBack }: { h: Harbour; limit: number; onBack: () => void }) {
  return <>
    <h2>{h.name} <span className="muted">{h.code}</span></h2>
    <button onClick={onBack}>← All harbours</button>
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
    <Factor name="Attractiveness" note="habitat for target species: coming next" />
    <Factor name="Headroom" value={h.headroom ?? undefined} note={h.fishing_hours === null
      ? 'pilot harbours only'
      : `${Math.round(h.fishing_hours)} AIS fishing hours / year within 6 nm`} />
    <h2>Waves at {limit.toFixed(1)} m</h2>
    <div className="stats">
      <div><b>{Math.round(h.viable_days)}</b><span className="muted">viable days / year</span></div>
      <div><b>{Math.round(h.shoulder_days)}</b><span className="muted">in shoulder season (of 152)</span></div>
    </div>
    <h2>Season curve</h2>
    <p className="muted">Share of viable days by week of the year at {limit.toFixed(1)} m. Shaded: shoulder season.</p>
    <SeasonCurve key={`${h.code}-${limit}`} weekly={h.weekly} />
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
