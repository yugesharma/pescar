import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'

type Trip = { date: string; worst_hs_m: number; status: 'GO' | 'MARGINAL' | 'NO-GO' }
type Harbour = {
  code: string; name: string; lat: number; lon: number; cell_km: number
  viable_days: number; shoulder_days: number
  weekly: { week: number; viability: number }[]; trips: Trip[]
}
type Data = { limit_m: number; meta: Record<string, string>; harbours: Harbour[] }

const LIMITS = [1.0, 1.5, 2.0]
const FAR_KM = 9  // ~one 0.083° grid cell; closer than this is normal for a coastal harbour
const BLUE = '#2a78d6'
// Sequential blue (light -> dark) for viable days per year. Fixed stops, so colours
// mean the same at every wave limit (and later across Europe).
const STOPS: [number, string][] = [[0, '#cde2fb'], [100, '#86b6ef'], [200, '#256abf'], [300, '#0d366b']]
const DOT_COLOR = ['interpolate', ['linear'], ['get', 'viable_days'], ...STOPS.flat()] as maplibregl.ExpressionSpecification

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

  const ranked = [...(data?.harbours ?? [])].sort((a, b) => b.viable_days - a.viable_days)
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
          <h2>Viable days per year</h2>
          <div className="legend" style={{ background: `linear-gradient(to right, ${STOPS.map(s => s[1]).join()})` }} />
          <div className="legend-labels muted">{STOPS.map(([v]) => <span key={v}>{v}{v === 300 ? '+' : ''}</span>)}</div>
          <ol>{ranked.map(x => (
            <li key={x.code}><button onClick={() => setCode(x.code)}>
              <span>{x.name}</span><span>{Math.round(x.viable_days)}</span>
            </button></li>))}
          </ol>
        </>}

        {data && <p className="muted">
          Waves: Copernicus Marine {data.meta.wave_product}, {data.meta.wave_history}.
          A viable day has every 3-hourly Hs in the trip window ({data.meta.trip_window}) below the wave limit.
          The 0.083° grid cannot resolve small coves. Built {data.meta.built_at}.
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
      properties: { code: h.code, viable_days: h.viable_days },
    })),
  })
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
