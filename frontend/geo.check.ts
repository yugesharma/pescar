// Self-check for geo.ts: node geo.check.ts
import assert from 'node:assert/strict'
import { destination, fmtBearing, NM, rangeBearing, type LngLat } from './src/geo.ts'

const near = (a: number, b: number, tol: number) => assert.ok(Math.abs(a - b) <= tol, `${a} vs ${b}`)

// 1° of longitude along the equator = 111.195 km = 60.04 nm, due east; back is due west.
let r = rangeBearing([0, 0], [1, 0])
near(r.m / NM, 60.04, 0.01); near(r.bearing, 90, 1e-9)
near(rangeBearing([1, 0], [0, 0]).bearing, 270, 1e-9)
near(rangeBearing([0, 0], [0, 1]).bearing, 0, 1e-9)
near(rangeBearing([0, 1], [0, 0]).bearing, 180, 1e-9)

// Round trip in the Azores: 6 nm on 137° from Ponta Delgada and back.
const pdl: LngLat = [-25.67, 37.74]
r = rangeBearing(pdl, destination(pdl, 137, 6 * NM))
near(r.m / NM, 6, 1e-9); near(r.bearing, 137, 1e-9)
// Across north: bearing 355° stays near 355°, not negative.
near(rangeBearing(pdl, destination(pdl, 355, 2 * NM)).bearing, 355, 1e-9)

assert.equal(fmtBearing(7.2), '007°T')
assert.equal(fmtBearing(359.6), '000°T')
assert.equal(fmtBearing(137.4), '137°T')
console.log('ok')
