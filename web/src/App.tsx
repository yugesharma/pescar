import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'

type Trip = { date: string; worst_hs_m: number; status: 'GO' | 'MARGINAL' | 'NO-GO' }
type Harbour = {
  code: string; name: string; lat: number; lon: number; cell_km: number
  viable_days: number; shoulder_days: number
  small_boats: number; places: number; transport_km: number; transport: string
  community: number; boats_part: number; tourism_part: number; viability: number
  score: number; limiting: string; income: number
  weekly: { week: number; viability: number }[]; trips: Trip[]
}
type Data = { limit_m: number; meta: Record<string, string>; harbours: Harbour[] }

const LIMITS = [1.0, 1.5, 2.0]
const FAR_KM = 9  // ~one 0.083° grid cell; closer than this is normal for a coastal harbour
const BLUE = '#2a78d6'
// Sequential blue (light -> dark) for harbour score, 0-1 (best harbour in Europe = 1).
const STOPS: [number, string][] = [[0, '#cde2fb'], [0.33, '#86b6ef'], [0.66, '#256abf'], [1, '#0d366b']]
const DOT_COLOR = ['interpolate', ['linear'], ['get', 'score'], ...STOPS.flat()] as maplibregl.ExpressionSpecification
const fmt = (v: number) => v.toFixed(2)

export default function App() {
  const [limit, setLimit] = useState(1.5)
  const [data, setData] = useState<Data>()
  const [code, setCode] = useState<string>()
  const mapEl = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map>(null)
  const dataRef = useRef(data)
  dataRef.current = data

  useEffect(() => {
    fetch(`/api/harbours?limit=${limit}`).then(r => r.json()).then(setData)
  }, [limit])

  useEffect(() => {
    const m = new maplibregl.Map({
      container: mapEl.current!, style: 'https://tiles.openfreemap.org/styles/positron',
      center: [-28, 38.4], zoom: 6.3,
    })
    m.on('load', () => {
      m.addSource('harbours', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({
        id: 'harbours', type: 'circle', source: 'harbours',
        paint: { 'circle-radius': 9, 'circle-color': DOT_COLOR, 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' },
      })
      m.on('click', 'harbours', e => setCode(e.features![0].properties.code))
      m.on('mouseenter', 'harbours', () => (m.getCanvas().style.cursor = 'pointer'))
      m.on('mouseleave', 'harbours', () => (m.getCanvas().style.cursor = ''))
      map.current = m
      if (dataRef.current) showHarbours(m, dataRef.current)
    })
    return () => { m.remove(); map.current = null }
  }, [])

  useEffect(() => { if (map.current && data) showHarbours(map.current, data) }, [data])

  const ranked = [...(data?.harbours ?? [])].sort((a, b) => b.score - a.score)
  const h = data?.harbours.find(x => x.code === code)

  return (
    <div className="app">
      <div className="map" ref={mapEl} />
      <aside className="panel">
        <h1>PescaMare · Azores</h1>
        <label className="muted">Wave limit{' '}
          <select value={limit} onChange={e => setLimit(+e.target.value)}>
            {LIMITS.map(l => <option key={l} value={l}>{l.toFixed(1)} m</option>)}
          </select>
        </label>

        {h ? <Detail h={h} limit={limit} onBack={() => setCode(undefined)} /> : <>
          <h2>Harbour score</h2>
          <div className="legend" style={{ background: `linear-gradient(to right, ${STOPS.map(s => s[1]).join()})` }} />
          <div className="legend-labels muted">{STOPS.map(([v]) => <span key={v}>{fmt(v)}</span>)}</div>
          <p className="muted">Community × Viability so far, each divided by the best harbour. A ranking, not an absolute measure.</p>
          <ol>{ranked.map(x => (
            <li key={x.code}><button onClick={() => setCode(x.code)}>
              <span>{x.name}<br /><span className="muted">{x.limiting}</span></span><span>{fmt(x.score)}</span>
            </button></li>))}
          </ol>
        </>}

        {data && <p className="muted">
          Waves: Copernicus Marine {data.meta.wave_product}, {data.meta.wave_history}.
          A viable day has every 3-hourly Hs in the trip window ({data.meta.trip_window}) below the wave limit.
          The 0.083° grid cannot resolve small coves.
          Boats: {data.meta.fleet} (licensed, under 12 m, by port of registration; not always where boats work).
          Tourism: {data.meta.osm}; OSM counts places, rarely beds. Built {data.meta.built_at}.
        </p>}
      </aside>
    </div>
  )
}

function showHarbours(m: maplibregl.Map, data: Data) {
  (m.getSource('harbours') as maplibregl.GeoJSONSource).setData({
    type: 'FeatureCollection',
    features: data.harbours.map(h => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: [h.lon, h.lat] },
      properties: { code: h.code, score: h.score },
    })),
  })
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
    {h.cell_km > FAR_KM && <p className="warning">
      ⚠ Wave figures come from the nearest model sea cell, {h.cell_km} km from the harbour.
      Sea state there may differ from the harbour's own waters.
    </p>}
    <div className="stats">
      <div><b>{fmt(h.score)}</b><span className="muted">harbour score</span></div>
      <div><b>€{h.income.toLocaleString('en-GB')}</b><span className="muted">income potential per boat / year</span></div>
    </div>
    <p><strong>{h.limiting[0].toUpperCase() + h.limiting.slice(1)}</strong></p>
    <h2>Factors</h2>
    <Factor name="Community" value={h.community}
      note={`${h.small_boats} small boats · ${h.places} places to stay within 10 km · ${h.transport || 'airport/ferry'} ${h.transport_km} km`} />
    <Factor name="Viability" value={h.viability} note="viable days per year at 1.5 m, vs the best harbour" />
    <Factor name="Attractiveness" note="habitat for target species: coming next" />
    <Factor name="Headroom" note="fishing pressure and stock status: coming next" />
    <p className="muted">Score and income use the default 1.5 m wave limit. Income potential = viable days × €500 per trip-day.</p>
    <h2>Waves at {limit.toFixed(1)} m</h2>
    <div className="stats">
      <div><b>{Math.round(h.viable_days)}</b><span className="muted">viable days / year</span></div>
      <div><b>{Math.round(h.shoulder_days)}</b><span className="muted">in shoulder season (of 152)</span></div>
    </div>
    <h2>Season curve</h2>
    <p className="muted">Share of viable days by week of the year at {limit.toFixed(1)} m. ~4 years per week, so single weeks are noisy. Shaded: shoulder season.</p>
    <SeasonCurve key={`${h.code}-${limit}`} weekly={h.weekly} />
    <h2>Next 3 days</h2>
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
