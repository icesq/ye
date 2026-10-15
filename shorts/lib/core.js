// Core helpers: easing, keyframes, seeded randomness, SVG string builders.
'use strict';

const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a, b, t) => a + (b - a) * t;

const E = {
  linear: t => t,
  inQuad: t => t * t,
  outQuad: t => 1 - (1 - t) * (1 - t),
  inOutQuad: t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  inCubic: t => t * t * t,
  outCubic: t => 1 - Math.pow(1 - t, 3),
  inOutCubic: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  inOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
  outSine: t => Math.sin((t * Math.PI) / 2),
  inExpo: t => (t === 0 ? 0 : Math.pow(2, 10 * t - 10)),
  outExpo: t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  outBack: t => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  outBackSoft: t => { const c1 = 1.2, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  inBack: t => { const c1 = 1.70158, c3 = c1 + 1; return c3 * t * t * t - c1 * t * t; },
  outElastic: t => (t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1),
  outBounce: t => {
    const n1 = 7.5625, d1 = 2.75;
    if (t < 1 / d1) return n1 * t * t;
    if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + 0.75;
    if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + 0.9375;
    return n1 * (t -= 2.625 / d1) * t + 0.984375;
  },
};

// progress of t within [t0, t1], eased
const prog = (t, t0, t1, ease = E.linear) => ease(clamp((t - t0) / (t1 - t0)));

function hex2rgb(c) {
  const n = parseInt(c.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function rgb2hex([r, g, b]) {
  const h = v => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, '0');
  return '#' + h(r) + h(g) + h(b);
}
function mixColor(a, b, t) {
  if (t <= 0) return a;
  if (t >= 1) return b;
  const A = hex2rgb(a), B = hex2rgb(b);
  return rgb2hex([lerp(A[0], B[0], t), lerp(A[1], B[1], t), lerp(A[2], B[2], t)]);
}

function interp(a, b, t) {
  if (typeof a === 'number') return lerp(a, b, t);
  if (typeof a === 'string') return mixColor(a, b, t);
  if (Array.isArray(a)) return a.map((v, i) => interp(v, b[i], t));
  if (a && typeof a === 'object') {
    const o = {};
    for (const k of Object.keys(a)) o[k] = k in b ? interp(a[k], b[k], t) : a[k];
    return o;
  }
  return t < 0.5 ? a : b;
}

// keyframes: [[time, value, easeIntoThisKey?], ...]
function kf(t, keys, defEase = E.inOutCubic) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, ez] = keys[i];
    if (t <= t1) {
      const [t0, v0] = keys[i - 1];
      const p = t1 === t0 ? 1 : (t - t0) / (t1 - t0);
      return interp(v0, v1, (ez || defEase)(p));
    }
  }
  return keys[keys.length - 1][1];
}

// deterministic randomness
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hash(n) {
  let x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}
// smooth 1D value noise in [-1, 1]
function noise(x, seed = 0) {
  const i = Math.floor(x), f = x - i;
  const u = f * f * (3 - 2 * f);
  return lerp(hash(i + seed * 57.3), hash(i + 1 + seed * 57.3), u) * 2 - 1;
}

// SVG builders ---------------------------------------------------------------
const n2 = v => (Math.round(v * 100) / 100).toString();
function tr(x = 0, y = 0, r = 0, sx = 1, sy = sx) {
  let s = '';
  if (x || y) s += `translate(${n2(x)} ${n2(y)})`;
  if (r) s += ` rotate(${n2(r)})`;
  if (sx !== 1 || sy !== 1) s += ` scale(${n2(sx)} ${n2(sy)})`;
  return s;
}
const G = (transform, ...kids) => (transform ? `<g transform="${transform}">${kids.join('')}</g>` : `<g>${kids.join('')}</g>`);
const O = (opacity, ...kids) => (opacity <= 0 ? '' : opacity >= 1 ? kids.join('') : `<g opacity="${n2(opacity)}">${kids.join('')}</g>`);
// NOTE: element-level `opacity` is emitted as fill/stroke-opacity. resvg allocates a layer for
// `opacity`, and panics when that layer lies more than one canvas away from the frame.
const attrs = o => {
  if (o.opacity !== undefined && o.opacity !== null) {
    const a = +o.opacity;
    o = Object.assign({}, o);
    o['fill-opacity'] = (o['fill-opacity'] !== undefined ? +o['fill-opacity'] : 1) * a;
    o['stroke-opacity'] = (o['stroke-opacity'] !== undefined ? +o['stroke-opacity'] : 1) * a;
    delete o.opacity;
  }
  return Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== false)
    .map(([k, v]) => `${k}="${typeof v === 'number' ? n2(v) : v}"`).join(' ');
};
const P = (d, o = {}) => `<path d="${d}" ${attrs(o)}/>`;
const C = (cx, cy, r, o = {}) => `<circle cx="${n2(cx)}" cy="${n2(cy)}" r="${n2(r)}" ${attrs(o)}/>`;
const EL = (cx, cy, rx, ry, o = {}) => `<ellipse cx="${n2(cx)}" cy="${n2(cy)}" rx="${n2(Math.max(0, rx))}" ry="${n2(Math.max(0, ry))}" ${attrs(o)}/>`;
const R = (x, y, w, h, o = {}) => `<rect x="${n2(x)}" y="${n2(y)}" width="${n2(w)}" height="${n2(h)}" ${attrs(o)}/>`;
const L = (x1, y1, x2, y2, o = {}) => `<line x1="${n2(x1)}" y1="${n2(y1)}" x2="${n2(x2)}" y2="${n2(y2)}" ${attrs(o)}/>`;
const PL = (pts, o = {}) => `<polyline points="${pts.map(p => n2(p[0]) + ',' + n2(p[1])).join(' ')}" ${attrs(o)}/>`;
const PG = (pts, o = {}) => `<polygon points="${pts.map(p => n2(p[0]) + ',' + n2(p[1])).join(' ')}" ${attrs(o)}/>`;

// smooth closed path through points (Catmull-Rom -> cubic bezier)
function smoothPath(pts, closed = true, tension = 1) {
  const n = pts.length;
  if (n < 2) return '';
  const get = i => (closed ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]);
  let d = `M${n2(pts[0][0])},${n2(pts[0][1])}`;
  const last = closed ? n : n - 1;
  for (let i = 0; i < last; i++) {
    const p0 = get(i - 1), p1 = get(i), p2 = get(i + 1), p3 = get(i + 2);
    const c1 = [p1[0] + ((p2[0] - p0[0]) / 6) * tension, p1[1] + ((p2[1] - p0[1]) / 6) * tension];
    const c2 = [p2[0] - ((p3[0] - p1[0]) / 6) * tension, p2[1] - ((p3[1] - p1[1]) / 6) * tension];
    d += `C${n2(c1[0])},${n2(c1[1])} ${n2(c2[0])},${n2(c2[1])} ${n2(p2[0])},${n2(p2[1])}`;
  }
  return d + (closed ? 'Z' : '');
}
const polyPath = (pts, closed = true) => 'M' + pts.map(p => n2(p[0]) + ',' + n2(p[1])).join('L') + (closed ? 'Z' : '');

// 2-bone IK: returns joint position for a limb from a to b with segment lengths l1,l2; bend = +1/-1
function ik(a, b, l1, l2, bend = 1) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  let d = Math.hypot(dx, dy);
  const maxd = l1 + l2 - 0.01;
  const dd = Math.min(d, maxd);
  const ang = Math.atan2(dy, dx);
  const cosA = clamp((l1 * l1 + dd * dd - l2 * l2) / (2 * l1 * dd || 1), -1, 1);
  const A = Math.acos(cosA) * bend;
  return [a[0] + Math.cos(ang + A) * l1, a[1] + Math.sin(ang + A) * l1];
}

// quadratic curve from a to c that passes through b (at t=0.5)
function through(a, b, c) {
  const ctrl = [2 * b[0] - (a[0] + c[0]) / 2, 2 * b[1] - (a[1] + c[1]) / 2];
  return `M${n2(a[0])},${n2(a[1])} Q${n2(ctrl[0])},${n2(ctrl[1])} ${n2(c[0])},${n2(c[1])}`;
}

const deg = r => (r * 180) / Math.PI;
const rad = d => (d * Math.PI) / 180;

module.exports = {
  clamp, lerp, E, prog, kf, interp, mixColor, hex2rgb, rgb2hex, rng, hash, noise,
  n2, tr, G, O, P, C, EL, R, L, PL, PG, attrs, smoothPath, polyPath, ik, through, deg, rad,
};
