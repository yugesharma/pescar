// Range and bearing on a sphere (haversine); < 0.5% from the ellipsoid, far below what the map shows.
// Check: node geo.check.ts (from frontend/)
export type LngLat = [number, number]
const R = 6371008.8  // m, mean earth radius
export const NM = 1852
const rad = (d: number) => (d * Math.PI) / 180
const deg = (r: number) => (r * 180) / Math.PI

/** Distance (m) and initial true bearing (0-360°) from a to b. */
export function rangeBearing([lon1, lat1]: LngLat, [lon2, lat2]: LngLat) {
  const p1 = rad(lat1), p2 = rad(lat2), dl = rad(lon2 - lon1)
  const a = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2
  const y = Math.sin(dl) * Math.cos(p2)
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl)
  return { m: 2 * R * Math.asin(Math.min(1, Math.sqrt(a))), bearing: (deg(Math.atan2(y, x)) + 360) % 360 }
}

/** Point reached from a, going m metres on a true bearing. */
export function destination([lon, lat]: LngLat, bearing: number, m: number): LngLat {
  const p1 = rad(lat), d = m / R, b = rad(bearing)
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b))
  const l2 = rad(lon) + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2))
  return [((deg(l2) + 540) % 360) - 180, deg(p2)]
}

/** Closed circle of radius m around c, for range rings. */
export const ring = (c: LngLat, m: number) => Array.from({ length: 65 }, (_, i) => destination(c, (i * 360) / 64, m))

/** Navigator style: three digits, true. 359.6 -> '000°T'. */
export const fmtBearing = (b: number) => `${String(Math.round(b) % 360).padStart(3, '0')}°T`
