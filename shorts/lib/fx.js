// Reusable cartoon FX: impact lines, puffs, sparkles, speed lines, arrows, marks.
'use strict';
const { clamp, lerp, E, prog, rng, noise, hash, n2, tr, G, O, P, C, EL, R, L, PL, PG, smoothPath } = require('./core');
const INK = '#2b2220';

// radial "shock" lines around a point (like the little |/ marks around a hit)
function burstLines(t, t0, x, y, o = {}) {
  const { n = 8, r0 = 60, r1 = 150, dur = 0.35, color = INK, w = 8, rot = 0, seed = 1 } = o;
  const p = (t - t0) / dur;
  if (p < 0 || p > 1) return '';
  let s = '';
  for (let i = 0; i < n; i++) {
    const a = rot + (i / n) * Math.PI * 2 + hash(i + seed) * 0.4;
    const a0 = lerp(r0, r1, E.outCubic(p) * 0.6), a1 = lerp(r0, r1, E.outCubic(p));
    s += L(x + Math.cos(a) * a0, y + Math.sin(a) * a0, x + Math.cos(a) * a1, y + Math.sin(a) * a1, { stroke: color, 'stroke-width': w * (1 - p * 0.6), 'stroke-linecap': 'round' });
  }
  return s;
}

// little "!" style emphasis lines next to a head (static wiggle)
function emphasis(t, x, y, o = {}) {
  const { side = 1, color = INK, scale = 1 } = o;
  const j = Math.sin(t * 30) * 3;
  return G(tr(x, y, 0, scale * side, scale),
    L(0, -40 + j, 34, -70, { stroke: color, 'stroke-width': 7, 'stroke-linecap': 'round' }),
    L(10, 0, 54, -4 + j, { stroke: color, 'stroke-width': 7, 'stroke-linecap': 'round' }),
    L(0, 40 - j, 34, 66, { stroke: color, 'stroke-width': 7, 'stroke-linecap': 'round' }));
}

// expanding smoke/steam puffs
function puffs(t, t0, x, y, o = {}) {
  const { n = 6, spread = 120, rise = 220, size = 50, dur = 1.2, color = '#ffffff', stroke = INK, seed = 3, opacity = 1 } = o;
  const r = rng(seed);
  let s = '';
  for (let i = 0; i < n; i++) {
    const delay = r() * 0.3, ang = (r() - 0.5) * 2;
    const p = (t - t0 - delay) / dur;
    if (p < 0 || p > 1) { r(); continue; }
    const ep = E.outCubic(p);
    const px = x + Math.sin(ang) * spread * ep + noise(t * 2 + i, i) * 10;
    const py = y - rise * ep * (0.6 + r() * 0.6);
    const rr = size * (0.4 + ep * 0.9);
    s += O((1 - p) * opacity, C(px, py, rr, { fill: color, stroke, 'stroke-width': stroke === 'none' ? 0 : 6 }));
  }
  return s;
}

// cloud-puff shape (cartoon smoke), static
function puffShape(x, y, r, o = {}) {
  const { fill = '#ffffff', stroke = INK, sw = 7, n = 7, seed = 1 } = o;
  const pts = [];
  const rr = rng(seed);
  let d = '';
  const bumps = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    bumps.push([x + Math.cos(a) * r * 0.7, y + Math.sin(a) * r * 0.55, r * (0.42 + rr() * 0.18)]);
  }
  let out = '';
  for (const [bx, by, br] of bumps) out += C(bx, by, br + sw / 2, { fill: stroke });
  for (const [bx, by, br] of bumps) out += C(bx, by, br - sw / 2, { fill });
  out += EL(x, y, r * 0.75, r * 0.55, { fill });
  return out;
}

function sparkle(x, y, s, color = '#FFE45C', rot = 0) {
  const d = `M0,-1 C0.12,-0.12 0.12,-0.12 1,0 C0.12,0.12 0.12,0.12 0,1 C-0.12,0.12 -0.12,0.12 -1,0 C-0.12,-0.12 -0.12,-0.12 0,-1Z`;
  return G(tr(x, y, rot, s), P(d, { fill: color, stroke: INK, 'stroke-width': 0.08, 'stroke-linejoin': 'round' }));
}

function sparkles(t, t0, x, y, o = {}) {
  const { n = 6, radius = 160, dur = 0.8, size = 34, color = '#FFE45C', seed = 5 } = o;
  const r = rng(seed);
  let s = '';
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2, d = radius * (0.5 + r() * 0.5), delay = r() * 0.25;
    const p = (t - t0 - delay) / dur;
    if (p < 0 || p > 1) continue;
    const sc = Math.sin(p * Math.PI) * size;
    s += sparkle(x + Math.cos(a) * d, y + Math.sin(a) * d, sc, color, p * 90);
  }
  return s;
}

// horizontal/vertical speed lines across a region
function speedLines(t, o = {}) {
  const { x0 = 0, x1 = 1080, y0 = 0, y1 = 1920, n = 14, dir = 'v', speed = 2400, len = 260, color = '#ffffff', w = 8, seed = 2, opacity = 0.7 } = o;
  const r = rng(seed);
  let s = '';
  for (let i = 0; i < n; i++) {
    const a = r(), b = r(), c = r();
    if (dir === 'v') {
      const x = lerp(x0, x1, a);
      const span = y1 - y0 + len;
      const y = y1 - (((t * speed * (0.7 + b * 0.6) + c * span) % span)) + len * 0.5;
      s += L(x, y, x, y + len * (0.5 + b), { stroke: color, 'stroke-width': w, 'stroke-linecap': 'round' });
    } else {
      const y = lerp(y0, y1, a);
      const span = x1 - x0 + len;
      const x = x0 + ((t * speed * (0.7 + b * 0.6) + c * span) % span) - len;
      s += L(x, y, x + len * (0.5 + b), y, { stroke: color, 'stroke-width': w, 'stroke-linecap': 'round' });
    }
  }
  return O(opacity, s);
}

// cartoon arrow from a to b, drawn on with progress p
function arrow(a, b, p = 1, o = {}) {
  const { color = '#FF5A4E', w = 22, head = 46, curve = 0 } = o;
  if (p <= 0) return '';
  const mx = (a[0] + b[0]) / 2 - (b[1] - a[1]) * curve, my = (a[1] + b[1]) / 2 + (b[0] - a[0]) * curve;
  const q = (u) => [(1 - u) * (1 - u) * a[0] + 2 * (1 - u) * u * mx + u * u * b[0], (1 - u) * (1 - u) * a[1] + 2 * (1 - u) * u * my + u * u * b[1]];
  const N = 24, pts = [];
  for (let i = 0; i <= N; i++) pts.push(q((i / N) * p));
  const end = pts[pts.length - 1], prev = pts[pts.length - 2] || a;
  const ang = Math.atan2(end[1] - prev[1], end[0] - prev[0]);
  const hd = G(tr(end[0], end[1], (ang * 180) / Math.PI), PG([[head * 0.6, 0], [-head * 0.5, -head * 0.6], [-head * 0.5, head * 0.6]], { fill: color, stroke: INK, 'stroke-width': 7, 'stroke-linejoin': 'round' }));
  const body = PL(pts.slice(0, -1), { fill: 'none', stroke: INK, 'stroke-width': w + 14, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }) +
    PL(pts.slice(0, -1), { fill: 'none', stroke: color, 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
  return body + hd;
}

// red cross-out X, drawn on
function crossOut(t, t0, x, y, size = 160, o = {}) {
  const { color = '#E8343A', w = 30, dur = 0.3 } = o;
  const p1 = prog(t, t0, t0 + dur / 2, E.outCubic), p2 = prog(t, t0 + dur / 2, t0 + dur, E.outCubic);
  if (p1 <= 0) return '';
  const h = size / 2;
  let s = '';
  const seg = (ax, ay, bx, by, p) => p > 0 ? L(ax, ay, lerp(ax, bx, p), lerp(ay, by, p), { stroke: INK, 'stroke-width': w + 14, 'stroke-linecap': 'round' }) : '';
  const seg2 = (ax, ay, bx, by, p) => p > 0 ? L(ax, ay, lerp(ax, bx, p), lerp(ay, by, p), { stroke: color, 'stroke-width': w, 'stroke-linecap': 'round' }) : '';
  s += seg(x - h, y - h, x + h, y + h, p1) + seg(x + h, y - h, x - h, y + h, p2);
  s += seg2(x - h, y - h, x + h, y + h, p1) + seg2(x + h, y - h, x - h, y + h, p2);
  return s;
}

function checkMark(t, t0, x, y, size = 160, o = {}) {
  const { color = '#3CC86B', w = 30, dur = 0.3 } = o;
  const p = prog(t, t0, t0 + dur, E.outCubic);
  if (p <= 0) return '';
  const pts = [[x - size * 0.45, y], [x - size * 0.1, y + size * 0.35], [x + size * 0.5, y - size * 0.4]];
  const lenA = Math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]), lenB = Math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1]);
  const tot = lenA + lenB, cur = p * tot;
  const draw = cur <= lenA ? [pts[0], [lerp(pts[0][0], pts[1][0], cur / lenA), lerp(pts[0][1], pts[1][1], cur / lenA)]]
    : [pts[0], pts[1], [lerp(pts[1][0], pts[2][0], (cur - lenA) / lenB), lerp(pts[1][1], pts[2][1], (cur - lenA) / lenB)]];
  return PL(draw, { fill: 'none', stroke: INK, 'stroke-width': w + 14, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }) +
    PL(draw, { fill: 'none', stroke: color, 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
}

// pop-in scale with overshoot: returns scale factor for element appearing at t0
function popIn(t, t0, dur = 0.35, ease = E.outBack) {
  return ease(clamp((t - t0) / dur));
}
function popOut(t, t0, dur = 0.2) {
  return 1 - E.inBack(clamp((t - t0) / dur));
}
// combined appear/disappear scale
function life(t, tin, tout = 1e9, din = 0.35, dout = 0.2) {
  if (t < tin) return 0;
  if (t >= tout) return Math.max(0, 1 - E.inCubic(clamp((t - tout) / dout)));
  return E.outBack(clamp((t - tin) / din));
}

// squash & stretch bounce for an object landing: returns [sx, sy]
function squash(t, t0, amt = 0.25, dur = 0.45) {
  const p = clamp((t - t0) / dur);
  if (p <= 0 || p >= 1) return [1, 1];
  const k = Math.sin(p * Math.PI * 2.5) * Math.exp(-p * 4) * amt;
  return [1 + k, 1 - k];
}

// wobbly warning sign "DON'T TRY THIS AT HOME"
function warning(x, y, s = 1, textFn) {
  const tri = PG([[0, -95], [100, 80], [-100, 80]], { fill: '#FFD21F', stroke: INK, 'stroke-width': 12, 'stroke-linejoin': 'round' });
  const ex = R(-11, -40, 22, 70, { rx: 10, fill: INK }) + C(0, 52, 13, { fill: INK });
  return G(tr(x, y, 0, s), tri, ex);
}

module.exports = { burstLines, emphasis, puffs, puffShape, sparkle, sparkles, speedLines, arrow, crossOut, checkMark, popIn, popOut, life, squash, warning, INK };
