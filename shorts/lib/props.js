// Shared props drawn in the same flat, outlined cartoon style as Rusty.
'use strict';
const { clamp, lerp, E, prog, rng, noise, hash, mixColor, n2, tr, G, O, P, C, EL, R, L, PL, PG, smoothPath, polyPath } = require('./core');
const { puffShape } = require('./fx');
const INK = '#2b2220';
const LW = 8;

// --- lightning ------------------------------------------------------------------
function boltPoints(a, b, seed, rough = 0.22, depth = 6) {
  const r = rng(seed);
  let pts = [a, b];
  let disp = Math.hypot(b[0] - a[0], b[1] - a[1]) * rough;
  for (let d = 0; d < depth; d++) {
    const np = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      const p0 = pts[i - 1], p1 = pts[i];
      const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2;
      const dx = p1[0] - p0[0], dy = p1[1] - p0[1], len = Math.hypot(dx, dy) || 1;
      const off = (r() - 0.5) * 2 * disp;
      np.push([mx - (dy / len) * off, my + (dx / len) * off], p1);
    }
    pts = np;
    disp *= 0.55;
  }
  return pts;
}

// glowing bolt with branches; p = how much of the bolt is drawn (0..1) from a to b
function bolt(a, b, o = {}) {
  const { seed = 1, p = 1, width = 18, glow = '#9FDBFF', core = '#ffffff', branches = 4, opacity = 1, rough = 0.22 } = o;
  const pts = boltPoints(a, b, seed, rough);
  const n = Math.max(2, Math.floor(pts.length * clamp(p)));
  const main = pts.slice(0, n);
  let s = '';
  const r = rng(seed + 99);
  const brs = [];
  for (let i = 0; i < branches; i++) {
    const k = Math.floor((0.15 + r() * 0.6) * pts.length);
    if (k >= n) continue;
    const st = pts[k];
    const ang = Math.atan2(b[1] - a[1], b[0] - a[0]) + (r() - 0.5) * 2.2;
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]) * (0.12 + r() * 0.2);
    brs.push(boltPoints(st, [st[0] + Math.cos(ang) * len, st[1] + Math.sin(ang) * len], seed + i * 7, 0.3, 4));
  }
  const draw = (pp, w) =>
    PL(pp, { fill: 'none', stroke: glow, 'stroke-width': w * 3.2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: 0.28 }) +
    PL(pp, { fill: 'none', stroke: glow, 'stroke-width': w * 1.7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: 0.6 }) +
    PL(pp, { fill: 'none', stroke: core, 'stroke-width': w * 0.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
  for (const bp of brs) s += draw(bp, width * 0.45);
  s += draw(main, width);
  return O(opacity, s);
}

// chunky cartoon bolt icon (yellow zigzag)
function boltIcon(x, y, s = 1, rot = 0, fill = '#FFE04A') {
  return G(tr(x, y, rot, s), P('M20,-120 L-50,10 L-6,10 L-30,120 L54,-20 L8,-20 L40,-120Z', { fill, stroke: INK, 'stroke-width': 10, 'stroke-linejoin': 'round' }),
    P('M18,-104 L-30,-4', { stroke: '#fff', 'stroke-width': 8, 'stroke-linecap': 'round', opacity: 0.6 }));
}

// --- weather -------------------------------------------------------------------
function cloud(x, y, s = 1, o = {}) {
  const { fill = '#ffffff', stroke = INK, shade = null, seed = 1 } = o;
  const bumps = [[-110, 10, 70], [-50, -30, 85], [30, -45, 95], [105, -5, 72], [150, 30, 50], [-150, 40, 45], [0, 30, 90]];
  let out = '';
  for (const [bx, by, br] of bumps) out += C(bx, by, br + LW / 2, { fill: stroke });
  for (const [bx, by, br] of bumps) out += C(bx, by, br - LW / 2, { fill });
  out += R(-150, 20, 300, 66, { fill });
  out += P('M-196,86 L196,86', { stroke: stroke, 'stroke-width': LW * 2, 'stroke-linecap': 'round' });
  if (shade) out += P('M-170,60 Q0,100 180,60 L180,82 L-170,82Z', { fill: shade, opacity: 0.6 });
  return G(tr(x, y, 0, s), out);
}

function storm(t, o = {}) {
  const { flashA = 0, rain = true, id = 'st' } = o;
  let s = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mixColor('#1E2647', '#E8F2FF', flashA)}"/><stop offset="1" stop-color="${mixColor('#4F5F8C', '#FFFFFF', flashA)}"/></linearGradient></defs>`;
  s += R(-600, -600, 2280, 3120, { fill: `url(#${id})` });
  // far clouds
  for (const [x, y, sc, sd] of [[150, 160, 1.6, 1], [560, 90, 1.9, 2], [960, 190, 1.5, 3], [330, 330, 1.2, 4], [800, 380, 1.1, 5]]) {
    s += cloud(x + noise(t * 0.2, sd) * 20, y, sc, { fill: mixColor('#3A4570', '#D7E6FF', flashA), stroke: '#151a33', shade: '#2a3358', seed: sd });
  }
  if (rain) {
    const r = rng(77);
    let d = '';
    for (let i = 0; i < 90; i++) {
      const x0 = r() * 1500 - 200, sp = 1900 + r() * 900, ph = r();
      const y = ((t * sp + ph * 2400) % 2400) - 300;
      const x = x0 - y * 0.18;
      d += `M${n2(x)},${n2(y)} l${n2(-12)},${n2(64)}`;
    }
    s += P(d, { stroke: '#BFD6FF', 'stroke-width': 5, 'stroke-linecap': 'round', opacity: 0.45 });
  }
  return s;
}

function hill(y = 1720, color = '#4E9F53', o = {}) {
  const { shade = '#3E8443' } = o;
  return P(`M-300,${y + 60} Q540,${y - 140} 1380,${y + 60} L1380,2600 L-300,2600Z`, { fill: color, stroke: INK, 'stroke-width': LW }) +
    P(`M-300,${y + 150} Q540,${y - 20} 1380,${y + 150} L1380,2600 L-300,2600Z`, { fill: shade, opacity: 0.5 });
}

// umbrella; (x,y) = handle grip point; canopy above
function umbrella(x, y, o = {}) {
  const { len = 520, rot = 0, open = 1, color = '#E8443A', color2 = '#FFD23F' } = o;
  const top = -len;
  const w = 290 * open, h = 150;
  let s = '';
  s += L(0, 0, 0, top, { stroke: INK, 'stroke-width': 18, 'stroke-linecap': 'round' }) + L(0, 0, 0, top, { stroke: '#8a8f99', 'stroke-width': 8 });
  s += P(`M0,0 q0,40 -34,40 q-26,0 -26,-26`, { fill: 'none', stroke: INK, 'stroke-width': 16, 'stroke-linecap': 'round' });
  // canopy segments
  const segs = 4;
  let can = '';
  for (let i = 0; i < segs; i++) {
    const x0 = -w + (i * 2 * w) / segs, x1 = -w + ((i + 1) * 2 * w) / segs;
    can += P(`M0,${top - h} Q${(x0 + x1) / 2 * 0.6},${top - h * 0.9} ${x0},${top} Q${(x0 + x1) / 2},${top - 34} ${x1},${top} Q${(x0 + x1) / 2 * 0.6},${top - h * 0.9} 0,${top - h}Z`, { fill: i % 2 ? color2 : color, stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  }
  s += can;
  s += L(0, top - h, 0, top - h - 70, { stroke: INK, 'stroke-width': 16, 'stroke-linecap': 'round' }) + L(0, top - h, 0, top - h - 70, { stroke: '#c9ced6', 'stroke-width': 7, 'stroke-linecap': 'round' });
  return G(tr(x, y, rot), s);
}
const umbrellaTip = (x, y, len = 520, rot = 0) => {
  const a = (rot * Math.PI) / 180, d = len + 150 + 70;
  return [x + Math.sin(a) * d, y - Math.cos(a) * d];
};

function tree(x, y, s = 1, o = {}) {
  const { burnt = 0, t = 0 } = o;
  const trunk = mixColor('#8A5A35', '#2a2422', burnt), leaf = mixColor('#4FAF52', '#3a3430', burnt), leaf2 = mixColor('#3D9444', '#2a2422', burnt);
  let out = P('M-40,0 L-28,-330 Q-80,-400 -120,-420 M-28,-330 L28,-330 L40,0Z', { fill: trunk, stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  out += P('M-40,0 L-28,-330 L28,-330 L40,0Z', { fill: trunk, stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  out += P('M8,-40 Q14,-140 4,-240', { fill: 'none', stroke: '#6b4428', 'stroke-width': 6, 'stroke-linecap': 'round' });
  const bl = [[-150, -440, 120], [0, -560, 150], [150, -450, 120], [-80, -340, 110], [90, -340, 110], [0, -420, 130]];
  for (const [bx, by, br] of bl) out += C(bx + noise(t * 0.8, bx) * 4, by, br + LW / 2, { fill: INK });
  for (const [bx, by, br] of bl) out += C(bx + noise(t * 0.8, bx) * 4, by, br - LW / 2, { fill: leaf });
  out += C(-60, -520, 46, { fill: leaf2, opacity: 0.6 }) + C(80, -420, 40, { fill: leaf2, opacity: 0.6 });
  return G(tr(x, y, 0, s), out);
}

// --- thermometer ---------------------------------------------------------------
function thermometer(x, y, level, o = {}) {
  const { s = 1, h = 900, color = '#F04438', bulbR = 95 } = o;
  const tw = 70;
  let out = '';
  out += R(-tw, -h, tw * 2, h, { rx: tw, fill: '#ffffff', stroke: INK, 'stroke-width': LW + 2 });
  out += C(0, 40, bulbR, { fill: color, stroke: INK, 'stroke-width': LW + 2 });
  const lh = (h - 50) * clamp(level);
  out += R(-tw + 22, -lh - 20, (tw - 22) * 2, lh + 80, { rx: tw - 22, fill: color });
  out += C(0, 40, bulbR - LW, { fill: color });
  out += C(-30, 10, 22, { fill: '#ffffff', opacity: 0.5 });
  for (let i = 1; i < 9; i++) out += L(tw - 4, -i * h / 9, tw - 34, -i * h / 9, { stroke: INK, 'stroke-width': 6, 'stroke-linecap': 'round' });
  out += R(-tw + 14, -h + 30, 18, h - 120, { rx: 9, fill: '#ffffff', opacity: 0.6 });
  return G(tr(x, y, 0, s), out);
}

// --- cute sun -------------------------------------------------------------------
function sun(x, y, s = 1, o = {}) {
  const { t = 0, mood = 'happy', look = [0, 0], sweat = 0 } = o;
  let out = '';
  const rays = 12;
  for (let i = 0; i < rays; i++) {
    const a = (i / rays) * Math.PI * 2 + t * 0.4;
    const r0 = 175, r1 = 245 + 14 * Math.sin(t * 4 + i);
    out += PG([[Math.cos(a - 0.12) * r0, Math.sin(a - 0.12) * r0], [Math.cos(a) * r1, Math.sin(a) * r1], [Math.cos(a + 0.12) * r0, Math.sin(a + 0.12) * r0]], { fill: '#FFB627', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  }
  out += C(0, 0, 180, { fill: '#FFD23F', stroke: INK, 'stroke-width': LW + 2 });
  out += C(0, 0, 150, { fill: '#FFE27A', opacity: 0.6 });
  // face
  const ex = 55, ey = -25;
  const big = mood === 'shocked' || mood === 'jealous';
  for (const sx of [-1, 1]) {
    out += EL(sx * ex, ey, 30, big ? 42 : 36, { fill: '#fff', stroke: INK, 'stroke-width': 6 });
    out += C(sx * ex + look[0] * 12, ey + look[1] * 14, big ? 8 : 11, { fill: INK });
    if (mood === 'jealous') out += P(`M${sx * 28},-78 L${sx * 86},-64`, { stroke: INK, 'stroke-width': 10, 'stroke-linecap': 'round' });
    else out += P(`M${sx * 28},-${big ? 92 : 78} Q${sx * 55},-${big ? 104 : 90} ${sx * 84},-${big ? 88 : 76}`, { fill: 'none', stroke: INK, 'stroke-width': 9, 'stroke-linecap': 'round' });
  }
  if (mood === 'happy') out += P('M-55,50 Q0,105 55,50', { fill: 'none', stroke: INK, 'stroke-width': 9, 'stroke-linecap': 'round' });
  else if (mood === 'shocked') out += EL(0, 68, 26, 32, { fill: '#7a1f1f', stroke: INK, 'stroke-width': 7 });
  else out += P('M-50,78 Q0,48 50,78', { fill: 'none', stroke: INK, 'stroke-width': 9, 'stroke-linecap': 'round' });
  out += EL(-105, 40, 22, 13, { fill: '#FF8C5A', opacity: 0.6 }) + EL(105, 40, 22, 13, { fill: '#FF8C5A', opacity: 0.6 });
  if (sweat > 0) out += G(tr(150, -110, 0, sweat), P('M0,-28 C10,-10 18,0 18,10 C18,22 -18,22 -18,10 C-18,0 -10,-10 0,-28Z', { fill: '#8FD3FF', stroke: INK, 'stroke-width': 5 }));
  return G(tr(x, y, 0, s), out);
}

// --- heart character -----------------------------------------------------------
function heart(x, y, s = 1, o = {}) {
  const { mood = 'happy', t = 0, tint = 0, look = [0, 0] } = o;
  const red = mixColor('#E8424D', '#8d8a91', tint), dark = mixColor('#B92E3A', '#6d6a71', tint);
  let out = P('M0,170 C-120,90 -230,10 -230,-80 C-230,-170 -150,-220 -80,-210 C-40,-205 -12,-180 0,-150 C12,-180 40,-205 80,-210 C150,-220 230,-170 230,-80 C230,10 120,90 0,170Z', { fill: red, stroke: INK, 'stroke-width': LW + 3, 'stroke-linejoin': 'round' });
  out += P('M120,-150 C180,-140 205,-90 195,-40 C170,20 120,70 40,130 C110,60 160,0 170,-60 C175,-100 155,-135 120,-150Z', { fill: dark, opacity: 0.6 });
  out += EL(-120, -120, 40, 26, { fill: '#fff', opacity: 0.35, transform: 'rotate(-30 -120 -120)' });
  // vessels on top
  out = G('', R(-70, -300, 50, 120, { rx: 20, fill: '#5B8DE8', stroke: INK, 'stroke-width': LW }), R(20, -310, 56, 130, { rx: 22, fill: red, stroke: INK, 'stroke-width': LW }), out);
  // face
  if (mood === 'dead') {
    for (const sx of [-1, 1]) out += P(`M${sx * 70 - 24},-60 l48,48 m0,-48 l-48,48`, { stroke: INK, 'stroke-width': 11, 'stroke-linecap': 'round' });
    out += EL(0, 50, 20, 14, { fill: '#5a1a1e', stroke: INK, 'stroke-width': 6 });
  } else {
    const big = mood === 'shocked';
    for (const sx of [-1, 1]) {
      out += EL(sx * 70, -40, big ? 42 : 36, big ? 50 : 42, { fill: '#fff', stroke: INK, 'stroke-width': 6 });
      out += C(sx * 70 + look[0] * 12, -40 + look[1] * 14, big ? 9 : 13, { fill: INK });
    }
    if (mood === 'happy') out += P('M-45,40 Q0,85 45,40', { fill: 'none', stroke: INK, 'stroke-width': 9, 'stroke-linecap': 'round' });
    else if (mood === 'shocked') out += EL(0, 60, 28, 34, { fill: '#5a1a1e', stroke: INK, 'stroke-width': 7 });
    else out += P('M-40,60 Q0,30 40,60', { fill: 'none', stroke: INK, 'stroke-width': 9, 'stroke-linecap': 'round' });
  }
  return G(tr(x, y, 0, s), out);
}

// ECG monitor, trace scrolls with time; flat after flatT
function monitor(x, y, t, o = {}) {
  const { w = 760, h = 300, flatT = 1e9, bpm = 90, color = '#4CFF8A' } = o;
  let out = R(-w / 2 - 24, -h / 2 - 24, w + 48, h + 48, { rx: 34, fill: '#D9DEE6', stroke: INK, 'stroke-width': LW + 2 });
  out += R(-w / 2, -h / 2, w, h, { rx: 16, fill: '#13262A', stroke: INK, 'stroke-width': 6 });
  let grid = '';
  for (let gx = -w / 2 + 40; gx < w / 2; gx += 60) grid += `M${gx},${-h / 2}V${h / 2}`;
  for (let gy = -h / 2 + 30; gy < h / 2; gy += 60) grid += `M${-w / 2},${gy}H${w / 2}`;
  out += P(grid, { stroke: '#2A4A45', 'stroke-width': 2 });
  // trace: sample function over the visible window (last 2.2 s)
  const win = 2.2, N = 220, beat = 60 / bpm;
  const ecg = tt => {
    if (tt > flatT) return 0;
    const ph = ((tt % beat) + beat) % beat / beat;
    const g = (c, wd, a) => a * Math.exp(-Math.pow((ph - c) / wd, 2));
    return g(0.12, 0.03, 0.15) - g(0.27, 0.012, 0.25) + g(0.3, 0.014, 1.0) - g(0.33, 0.014, 0.35) + g(0.55, 0.05, 0.3);
  };
  const pts = [];
  for (let i = 0; i <= N; i++) {
    const tt = t - win + (i / N) * win;
    pts.push([-w / 2 + (i / N) * w, -ecg(tt) * h * 0.38 + h * 0.08]);
  }
  out += PL(pts, { fill: 'none', stroke: color, 'stroke-width': 14, opacity: 0.25, 'stroke-linejoin': 'round' });
  out += PL(pts, { fill: 'none', stroke: color, 'stroke-width': 6, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
  const last = pts[pts.length - 1];
  out += C(last[0], last[1], 10, { fill: '#ffffff' });
  return G(tr(x, y), out);
}

// --- misc ----------------------------------------------------------------------
function signBoard(x, y, w, h, o = {}) {
  const { fill = '#ffffff', rot = 0, s = 1, rx = 26 } = o;
  return G(tr(x, y, rot, s), R(-w / 2 + 8, -h / 2 + 12, w, h, { rx, fill: INK, opacity: 0.25 }), R(-w / 2, -h / 2, w, h, { rx, fill, stroke: INK, 'stroke-width': LW + 2 }));
}

function shoe(x, y, rot = 0, s = 1, flip = 1) {
  return G(tr(x, y, rot, s * flip, s),
    P('M-34,-30 Q-4,-42 26,-30 Q62,-18 64,6 Q64,20 40,20 L-30,20 Q-46,18 -44,0 Q-44,-22 -34,-30Z', { fill: '#3a2c2a', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' }),
    P('M-14,-30 Q4,-38 22,-30', { fill: 'none', stroke: '#ffffff', 'stroke-width': 6, opacity: 0.25, 'stroke-linecap': 'round' }));
}

// stopwatch / clock with hand angle
function stopwatch(x, y, s = 1, o = {}) {
  const { frac = 0, color = '#ffffff', ring = '#FF5A4E' } = o;
  let out = R(-30, -250, 60, 60, { rx: 12, fill: '#c9ced6', stroke: INK, 'stroke-width': LW });
  out += C(0, 0, 210, { fill: ring, stroke: INK, 'stroke-width': LW + 2 });
  out += C(0, 0, 175, { fill: color, stroke: INK, 'stroke-width': LW });
  if (frac > 0) {
    const a = frac * Math.PI * 2;
    const large = frac > 0.5 ? 1 : 0;
    out += P(`M0,0 L0,-160 A160,160 0 ${large},1 ${n2(Math.sin(a) * 160)},${n2(-Math.cos(a) * 160)}Z`, { fill: ring, opacity: 0.25 });
  }
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    out += L(Math.sin(a) * 150, -Math.cos(a) * 150, Math.sin(a) * 132, -Math.cos(a) * 132, { stroke: INK, 'stroke-width': 7, 'stroke-linecap': 'round' });
  }
  const a = frac * Math.PI * 2;
  out += L(0, 0, Math.sin(a) * 130, -Math.cos(a) * 130, { stroke: INK, 'stroke-width': 12, 'stroke-linecap': 'round' });
  out += C(0, 0, 16, { fill: INK });
  return G(tr(x, y, 0, s), out);
}

module.exports = { bolt, boltPoints, boltIcon, cloud, storm, hill, umbrella, umbrellaTip, tree, thermometer, sun, heart, monitor, signBoard, shoe, stopwatch, INK, LW };

// ============================================================ space props
const SUIT = { shirt: '#EEF2F7', shirtSh: '#C8D1DE', pants: '#E3E8EF', pantsSh: '#BCC6D4', shoe: '#8D98A8', hand: '#F4F6FA', hair: '#4A3428', hairSh: '#33231b', hairHi: '#6b4c3b', skin: '#E8B48A', skinSh: '#CF9670' };
const friendBase = { pal: SUIT, hairStyle: 'short', helmet: true, backpack: true, freckles: false, longSleeves: true };

// big planet arc at the bottom of the frame
function earthArc(t, o = {}) {
  const { cy = 3350, r = 1750, rot = 0 } = o;
  let s = `<defs><radialGradient id="atm" cx="50%" cy="50%" r="50%"><stop offset="0.9" stop-color="#7FC8FF" stop-opacity="0.55"/><stop offset="1" stop-color="#7FC8FF" stop-opacity="0"/></radialGradient></defs>`;
  s += C(540, cy, r + 160, { fill: 'url(#atm)' });
  s += C(540, cy, r, { fill: '#2F7FD6', stroke: INK, 'stroke-width': LW + 2 });
  const land = [[-0.3, 0.94, 150, 70], [0.0, 0.9, 210, 90], [0.33, 0.95, 130, 60], [-0.55, 0.88, 120, 60], [0.55, 0.9, 160, 70], [0.15, 0.97, 70, 34]];
  let g = '';
  for (const [a, k, w, h] of land) {
    const ang = a - Math.PI / 2 + rot;
    const x = 540 + Math.cos(ang) * r * k, y = cy + Math.sin(ang) * r * k;
    g += EL(x, y, w, h, { fill: '#4FB35A', stroke: INK, 'stroke-width': 7, transform: `rotate(${n2((ang + Math.PI / 2) * 57.3)} ${n2(x)} ${n2(y)})` });
  }
  for (let i = 0; i < 6; i++) {
    const ang = -Math.PI / 2 + (i - 2.5) * 0.22 + rot * 1.3 + 0.05 * Math.sin(t * 0.3 + i);
    const x = 540 + Math.cos(ang) * r * 0.985, y = cy + Math.sin(ang) * r * 0.985;
    g += EL(x, y, 130, 30, { fill: '#ffffff', opacity: 0.85, transform: `rotate(${n2((ang + Math.PI / 2) * 57.3)} ${n2(x)} ${n2(y)})` });
  }
  s += `<g>${g}</g>`;
  s += C(540, cy, r, { fill: 'none', stroke: INK, 'stroke-width': LW + 2 });
  return s;
}

// space station hull with an open airlock on its right side; (x,y) = airlock center
function station(x, y, o = {}) {
  const { s = 1, doorOpen = 1, inside = '#1c2348' } = o;
  let out = '';
  // solar panel
  out += R(-700, -720, 520, 200, { fill: '#2C4E9E', stroke: INK, 'stroke-width': LW });
  for (let i = 1; i < 5; i++) out += L(-700 + i * 104, -720, -700 + i * 104, -520, { stroke: '#7FA6F0', 'stroke-width': 4 });
  out += L(-700, -620, -180, -620, { stroke: '#7FA6F0', 'stroke-width': 4 });
  out += R(-200, -640, 120, 40, { fill: '#AAB4C3', stroke: INK, 'stroke-width': LW });
  // hull
  out += R(-760, -480, 760, 960, { rx: 80, fill: '#E3E8EF', stroke: INK, 'stroke-width': LW + 2 });
  out += R(-760, -480, 760, 120, { rx: 40, fill: '#C8D1DE', stroke: INK, 'stroke-width': LW });
  out += R(-760, 360, 760, 120, { rx: 40, fill: '#C8D1DE', stroke: INK, 'stroke-width': LW });
  for (const [px, py] of [[-560, -200], [-560, 120]]) out += C(px, py, 70, { fill: '#9FD3FF', stroke: INK, 'stroke-width': LW }) + P(`M${px - 36},${py - 20} Q${px - 20},${py - 46} ${px + 8},${py - 50}`, { fill: 'none', stroke: '#fff', 'stroke-width': 10, 'stroke-linecap': 'round' });
  for (let i = 0; i < 8; i++) out += C(-700 + i * 90, -330, 7, { fill: '#9AA6B8' });
  // airlock opening
  out += R(-260, -230, 260, 460, { rx: 60, fill: inside, stroke: INK, 'stroke-width': LW + 2 });
  out += R(-232, -200, 210, 400, { rx: 46, fill: '#2a3466' });
  // door (swings outward, hinged on the right edge)
  const dw = 250 * Math.cos(doorOpen * 1.25);
  out += P(`M0,-230 L${n2(dw)},${n2(-230 - doorOpen * 60)} L${n2(dw)},${n2(230 + doorOpen * 60)} L0,230Z`, { fill: '#C8D1DE', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  out += C(dw * 0.5, 0, 26 * Math.max(0.2, Math.cos(doorOpen * 1.25)), { fill: '#FFB627', stroke: INK, 'stroke-width': 6 });
  return G(tr(x, y, 0, s), out);
}

function iceBlock(x, y, w, h, o = {}) {
  const { p = 1, s = 1 } = o;
  const hh = h * clamp(p);
  let out = R(-w / 2, h / 2 - hh, w, hh, { rx: 40, fill: '#BFEFFF', 'fill-opacity': 0.55, stroke: '#5AA9D6', 'stroke-width': 12 });
  out += P(`M${-w / 2 + 40},${h / 2 - hh + 60} L${-w / 2 + 40},${h / 2 - 80}`, { stroke: '#ffffff', 'stroke-width': 18, 'stroke-linecap': 'round', opacity: 0.7 });
  out += P(`M${-w / 2 + 80},${h / 2 - hh + 50} L${-w / 2 + 160},${h / 2 - hh + 50}`, { stroke: '#ffffff', 'stroke-width': 14, 'stroke-linecap': 'round', opacity: 0.7 });
  return G(tr(x, y, 0, s), out);
}

function explosion(x, y, s = 1, t = 0) {
  const star = (r0, r1, n, rot) => {
    const pts = [];
    for (let i = 0; i < n * 2; i++) { const a = rot + (i * Math.PI) / n; const r = i % 2 ? r0 : r1 * (0.85 + 0.15 * Math.sin(i * 3.1 + t * 10)); pts.push([Math.cos(a) * r, Math.sin(a) * r]); }
    return pts;
  };
  return G(tr(x, y, 0, s), PG(star(200, 380, 12, 0.1), { fill: '#FF5A3C', stroke: INK, 'stroke-width': 12, 'stroke-linejoin': 'round' }),
    PG(star(150, 270, 12, 0.35), { fill: '#FFB627', stroke: INK, 'stroke-width': 9, 'stroke-linejoin': 'round' }),
    PG(star(90, 160, 10, 0.2), { fill: '#FFF27A' }));
}

function lungs(x, y, s = 1, o = {}) {
  const { inflate = 0, crack = 0, t = 0 } = o;
  const k = 1 + inflate * 0.35;
  let out = '';
  out += R(-22, -330, 44, 200, { rx: 18, fill: '#F2B8C0', stroke: INK, 'stroke-width': LW });
  for (let i = 0; i < 6; i++) out += L(-22, -310 + i * 30, 22, -310 + i * 30, { stroke: '#D88E9A', 'stroke-width': 5 });
  for (const sd of [-1, 1]) {
    const lobe = `M${sd * 30},-170 C${sd * 60},-230 ${sd * 200},-220 ${sd * 230},-80 C${sd * 260},60 ${sd * 250},200 ${sd * 160},230 C${sd * 80},250 ${sd * 40},200 ${sd * 36},120 C${sd * 30},40 ${sd * 30},-60 ${sd * 30},-170Z`;
    out += G(tr(sd * 10, 0, 0, k, k), P(lobe, { fill: mixColor('#F49AA8', '#FF6B6B', inflate), stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' }),
      P(`M${sd * 30},-130 Q${sd * 90},-60 ${sd * 120},20 M${sd * 70},-80 Q${sd * 140},-40 ${sd * 190},-50 M${sd * 80},30 Q${sd * 130},80 ${sd * 150},150`, { fill: 'none', stroke: '#D9707F', 'stroke-width': 7, 'stroke-linecap': 'round' }),
      EL(sd * 140, -110, 40, 24, { fill: '#fff', opacity: 0.35 }));
    if (crack > 0) out += G(tr(sd * 10, 0, 0, k, k), PL([[sd * 230, -60], [sd * 190, -30], [sd * 215, 0], [sd * 170, 40], [sd * 200, 70]].slice(0, 2 + Math.floor(crack * 3)), { fill: 'none', stroke: INK, 'stroke-width': 9, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
  }
  out += P('M-22,-150 Q-30,-130 -50,-120 M22,-150 Q30,-130 50,-120', { fill: 'none', stroke: INK, 'stroke-width': LW, 'stroke-linecap': 'round' });
  return G(tr(x, y, 0, s), out);
}

function snail(x, y, s = 1, t = 0) {
  const sq = 1 + 0.06 * Math.sin(t * 4);
  let out = P(`M-120,0 Q-130,-40 -90,-46 L90,-30 Q130,-50 140,-110 L150,-112 Q150,-40 120,0Z`, { fill: '#9FD07A', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round', transform: `scale(${n2(sq)} 1)` });
  out += L(130, -100, 120, -170, { stroke: INK, 'stroke-width': 7, 'stroke-linecap': 'round' }) + L(146, -104, 160, -168, { stroke: INK, 'stroke-width': 7, 'stroke-linecap': 'round' });
  out += C(120, -176, 12, { fill: '#fff', stroke: INK, 'stroke-width': 5 }) + C(160, -174, 12, { fill: '#fff', stroke: INK, 'stroke-width': 5 }) + C(122, -176, 5, { fill: INK }) + C(162, -174, 5, { fill: INK });
  out += C(0, -90, 90, { fill: '#E8A14A', stroke: INK, 'stroke-width': LW });
  let sp = '';
  for (let i = 0; i <= 30; i++) { const a = i * 0.42, r = 80 - i * 2.5; sp += (i ? 'L' : 'M') + n2(Math.cos(a) * r) + ',' + n2(-90 + Math.sin(a) * r); }
  out += P(sp, { fill: 'none', stroke: '#B8722E', 'stroke-width': 9, 'stroke-linecap': 'round' });
  return G(tr(x, y, 0, s), out);
}

function helmetIcon(x, y, s = 1) {
  return G(tr(x, y, 0, s), C(0, 0, 120, { fill: '#BFE6FF', 'fill-opacity': 0.6, stroke: INK, 'stroke-width': 10 }),
    R(-110, 90, 220, 60, { rx: 26, fill: '#C9D2DF', stroke: INK, 'stroke-width': 10 }),
    P('M-80,-50 A100,100 0 0,1 -20,-100', { fill: 'none', stroke: '#fff', 'stroke-width': 16, 'stroke-linecap': 'round' }));
}

// interior wall of a ship
function shipInterior(t) {
  let s = R(-600, -600, 2280, 3120, { fill: '#D7DEE8' });
  for (let x = -600; x < 1700; x += 270) s += L(x, -600, x, 2520, { stroke: '#BBC5D3', 'stroke-width': 10 });
  for (let y = -600; y < 2600; y += 330) s += L(-600, y, 1700, y, { stroke: '#BBC5D3', 'stroke-width': 6 });
  for (const [px, py] of [[230, 420], [850, 420]]) {
    s += C(px, py, 130, { fill: '#18204A', stroke: INK, 'stroke-width': 14 }) + C(px, py, 130, { fill: 'none', stroke: '#AAB4C3', 'stroke-width': 26 });
    for (let i = 0; i < 6; i++) s += C(px - 70 + ((i * 53 + t * 15) % 140), py - 60 + ((i * 37) % 120), 4, { fill: '#fff' });
  }
  s += R(-600, 1640, 2280, 900, { fill: '#AEB8C7', stroke: INK, 'stroke-width': LW });
  return s;
}

Object.assign(module.exports, { SUIT, friendBase, earthArc, station, iceBlock, explosion, lungs, snail, helmetIcon, shipInterior });
