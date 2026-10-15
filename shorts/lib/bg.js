// Backgrounds: the signature light-blue "science doodle" wallpaper and scene skies.
'use strict';
const { rng, n2, tr, G, P, C, R, EL, mixColor } = require('./core');

const W = 1080, H = 1920;

// line-art icons in a ~100x100 box centered at 0,0
const ICONS = [
  // flask
  'M-14,-44 L14,-44 M-9,-44 L-9,-12 L-34,34 Q-38,44 -26,44 L26,44 Q38,44 34,34 L9,-12 L9,-44 M-22,14 L22,14',
  // atom
  'M0,0 m-6,0 a6,6 0 1,0 12,0 a6,6 0 1,0 -12,0 M-44,0 a44,16 0 1,0 88,0 a44,16 0 1,0 -88,0 M-22,-38 a44,16 60 1,0 44,76 M22,-38 a44,16 -60 1,0 -44,76',
  // star
  'M0,-40 L11,-13 L40,-12 L17,6 L25,36 L0,19 L-25,36 L-17,6 L-40,-12 L-11,-13Z',
  // rocket
  'M0,-46 C18,-30 20,0 14,24 L-14,24 C-20,0 -18,-30 0,-46Z M-14,10 L-30,30 L-14,26 M14,10 L30,30 L14,26 M0,-16 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0 M-7,30 L0,46 L7,30',
  // planet
  'M-26,0 a26,26 0 1,0 52,0 a26,26 0 1,0 -52,0 M-46,10 Q-60,26 -20,18 L24,6 Q62,-6 46,-14',
  // light bulb
  'M-22,-12 a22,24 0 1,1 44,0 C22,4 10,10 10,22 L-10,22 C-10,10 -22,4 -22,-12Z M-10,30 L10,30 M-7,38 L7,38 M-8,-14 L0,-4 L8,-14',
  // book
  'M-40,-28 Q-20,-38 0,-26 Q20,-38 40,-28 L40,30 Q20,20 0,32 Q-20,20 -40,30Z M0,-26 L0,32',
  // ruler
  'M-46,-12 L46,-12 L46,12 L-46,12Z M-34,-12 L-34,0 M-22,-12 L-22,4 M-10,-12 L-10,0 M2,-12 L2,4 M14,-12 L14,0 M26,-12 L26,4 M38,-12 L38,0',
  // magnifier
  'M-10,-10 m-24,0 a24,24 0 1,0 48,0 a24,24 0 1,0 -48,0 M8,8 L40,40',
  // DNA
  'M-14,-44 C30,-22 -30,22 14,44 M14,-44 C-30,-22 30,22 -14,44 M-8,-30 L8,-30 M-12,-10 L12,-10 M-12,10 L12,10 M-8,30 L8,30',
  // pencil
  'M-36,30 L-28,8 L22,-42 L38,-26 L-12,24Z M-36,30 L-12,24 M14,-34 L30,-18',
  // beaker
  'M-28,-38 L28,-38 M-24,-38 L-24,36 Q-24,42 -18,42 L18,42 Q24,42 24,36 L24,-38 M-24,0 L24,0 M-12,18 a4,4 0 1,0 1,0 M6,-14 a5,5 0 1,0 1,0',
  // triangle ruler
  'M-40,36 L40,36 L-40,-40Z M-26,22 L4,22 L-26,-8Z',
  // molecule
  'M-24,-18 a10,10 0 1,0 1,0 M24,-24 a12,12 0 1,0 1,0 M2,26 a10,10 0 1,0 1,0 M-16,-12 L14,-20 M-18,-8 L-2,20 M22,-14 L8,18',
  // cloud
  'M-36,16 Q-46,-6 -22,-10 Q-18,-34 4,-28 Q22,-40 30,-16 Q50,-12 40,16Z',
  // heart
  'M0,30 C-50,-6 -30,-46 0,-20 C30,-46 50,-6 0,30Z',
  // paper plane
  'M-40,0 L40,-30 L10,36 L0,8Z M0,8 L40,-30',
  // microscope
  'M-30,40 L30,40 M0,40 L0,26 M-16,26 L16,26 M-6,26 L-6,-10 L10,-40 L22,-34 L6,-4 M-10,8 Q-34,8 -26,30',
];

let cachedDoodle = new Map();
// big doodle layer larger than frame (so camera moves never reveal edges)
function doodleLayer(color = '#6E95D6', opacity = 0.42, seed = 7, density = 1) {
  const key = color + opacity + seed + density;
  if (cachedDoodle.has(key)) return cachedDoodle.get(key);
  const r = rng(seed);
  let s = '';
  const step = 150 / Math.sqrt(density);
  for (let y = -500; y < H + 500; y += step) {
    for (let x = -500; x < W + 500; x += step) {
      const ix = Math.floor(r() * ICONS.length);
      const jx = (r() - 0.5) * step * 0.6, jy = (r() - 0.5) * step * 0.6;
      const rot = (r() - 0.5) * 70;
      const sc = 0.5 + r() * 0.3;
      s += P(ICONS[ix], { transform: tr(x + jx + ((Math.round(y / step) % 2) * step) / 2, y + jy, rot, sc) });
    }
  }
  const out = `<g fill="none" stroke="${color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="${opacity}">${s}</g>`;
  cachedDoodle.set(key, out);
  return out;
}

// light blue paper with radial glow and doodles
function doodle(o = {}) {
  const { base = '#A8C6EF', center = '#C3DAF8', edge = '#8AAEE4', icon = '#6E95D6', iconOpacity = 0.38, seed = 7, density = 1 } = o;
  const id = 'bgr' + (o.id || '');
  return `<defs><radialGradient id="${id}" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="${center}"/><stop offset="0.6" stop-color="${base}"/><stop offset="1" stop-color="${edge}"/></radialGradient></defs>` +
    R(-600, -600, W + 1200, H + 1200, { fill: `url(#${id})` }) + doodleLayer(icon, iconOpacity, seed, density);
}

// variants used by specific stories
const BG = {
  blue: () => doodle({ id: 'b' }),
  lilac: () => doodle({ id: 'l', base: '#BBC2EE', center: '#D6DBFA', edge: '#9AA3DD', icon: '#8C93CF' }),
  warm: () => doodle({ id: 'w', base: '#F6D9A8', center: '#FBE9C9', edge: '#EDC383', icon: '#D9A863', iconOpacity: 0.35 }),
  mint: () => doodle({ id: 'm', base: '#B5E3D3', center: '#D3F2E7', edge: '#8FD0BB', icon: '#6FB7A0' }),
  pink: () => doodle({ id: 'p', base: '#F4C2C6', center: '#FADADD', edge: '#E9A1A8', icon: '#D88A92', iconOpacity: 0.32 }),
  purple: () => doodle({ id: 'u', base: '#6F5BC2', center: '#8572D6', edge: '#4C3C9E', icon: '#5A48AE', iconOpacity: 0.55 }),
};

// starfield for space scenes
const starCache = new Map();
function space(o = {}) {
  const { top = '#0B1240', bottom = '#24125A', seed = 3, t = 0, twinkle = true, id = 's' } = o;
  const key = seed;
  if (!starCache.has(key)) {
    const r = rng(seed);
    const stars = [];
    for (let i = 0; i < 260; i++) stars.push([r() * (W + 1000) - 500, r() * (H + 1000) - 500, 1.2 + r() * r() * 5, r() * 6.28, r()]);
    starCache.set(key, stars);
  }
  let s = `<defs><linearGradient id="sp${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${bottom}"/></linearGradient></defs>`;
  s += R(-600, -600, W + 1200, H + 1200, { fill: `url(#sp${id})` });
  let st = '';
  for (const [x, y, sz, ph, k] of starCache.get(key)) {
    const a = twinkle ? 0.55 + 0.45 * Math.sin(t * (1.5 + k * 3) + ph) : 1;
    if (sz > 4.5) st += P(`M${n2(x)},${n2(y - sz * 2)} L${n2(x + sz * 0.5)},${n2(y - sz * 0.5)} L${n2(x + sz * 2)},${n2(y)} L${n2(x + sz * 0.5)},${n2(y + sz * 0.5)} L${n2(x)},${n2(y + sz * 2)} L${n2(x - sz * 0.5)},${n2(y + sz * 0.5)} L${n2(x - sz * 2)},${n2(y)} L${n2(x - sz * 0.5)},${n2(y - sz * 0.5)}Z`, { fill: '#FFF6C8', opacity: n2(a) });
    else st += C(x, y, sz * 0.6, { fill: '#ffffff', opacity: n2(a * 0.85) });
  }
  return s + st;
}

function flat(color) {
  return R(-600, -600, W + 1200, H + 1200, { fill: color });
}

module.exports = { doodle, doodleLayer, BG, space, flat, ICONS, W, H };
