// "Rusty" — the ginger-haired hero. Front-facing cartoon rig drawn as SVG.
// Origin is between the feet; up is -y. Default height is ~1000 units.
'use strict';
const { clamp, lerp, E, mixColor, n2, tr, G, P, C, EL, R, L, smoothPath, polyPath, ik, through, deg, noise, hash } = require('./core');

const PAL = {
  ink: '#2b2220', skin: '#F8C48B', skinSh: '#E3A066', blush: '#F29A86', freckle: '#C9733F',
  hair: '#D8612B', hairSh: '#A9431D', hairHi: '#F08A45',
  shirt: '#22A79A', shirtSh: '#178478', pants: '#D5353D', pantsSh: '#A8242E',
  shoe: '#3a2c2a', sock: '#ffffff', white: '#ffffff', mouth: '#5a1a1e', tongue: '#EE6B6E', teeth: '#ffffff',
};
const LW = 8;

// default state ---------------------------------------------------------------
function defaults() {
  return {
    x: 0, y: 0, s: 1, rot: 0, flip: 1, opacity: 1,
    sx: 1, sy: 1,               // whole-body squash/stretch
    lean: 0,                    // torso rotation (deg)
    bob: 0,                     // vertical torso offset
    headRot: 0, headX: 0, headY: 0,
    fat: 0,                     // swelling 0..1+
    // hands/feet in body coordinates
    handL: [-150, -352], handR: [150, -352], bendL: 1, bendR: -1,
    handPoseL: 'open', handPoseR: 'open', handRotL: null, handRotR: null,
    footL: [-66, -18], footR: [66, -18],
    // face
    eyeOpen: 1, eyeOpenL: null, eyeOpenR: null, eyeSize: 1, pupil: 1, look: [0, 0],
    brow: 0, browTilt: 0, browL: null, browR: null,  // brow raise / tilt (+ = worried, - = angry)
    mouth: 'smile', mouthOpen: 1, mouthW: 1,
    blush: 0, sweat: 0, freckles: true,
    eyes: 'normal', // normal | x | spiral | closed | happy | star
    hair: 0,        // 0 normal -> 1 electrified
    tint: null, tintAmt: 0,     // recolor everything toward tint
    skinTint: null, skinTintAmt: 0,
    xray: false,
    socks: false,   // shoes blown off
    noHead: false,
    hideLegs: false,
    armsBehind: false,
    shirtless: false,
    t: 0,           // time, for internal wiggles
  };
}

// colors with optional tint
function palette(st) {
  const p = {};
  const base = Object.assign({}, PAL, { hand: (st.pal && st.pal.hand) || (st.pal && st.pal.skin) || PAL.skin }, st.pal || {});
  for (const k of Object.keys(base)) {
    let c = base[k];
    if (st.skinTint && (k === 'skin' || k === 'skinSh' || k === 'blush' || (k === 'hand' && !(st.pal && st.pal.hand)))) c = mixColor(c, st.skinTint, st.skinTintAmt);
    if (st.tint) c = mixColor(c, st.tint, st.tintAmt);
    p[k] = c;
  }
  return p;
}

// HANDS (local: +x points from wrist outwards) ----------------------------------
function hand(pose, p, scale, mirror) {
  const sk = { stroke: p.ink, 'stroke-width': LW, 'stroke-linejoin': 'round' };
  const my = mirror ? -1 : 1;
  let out = '';
  const finger = (ang, len, w) => {
    const a = (ang * Math.PI) / 180;
    return [Math.cos(a) * len, Math.sin(a) * len * my, w];
  };
  let fingers = [];
  let palmR = 33;
  if (pose === 'open') fingers = [finger(-48, 52, 21), finger(-16, 58, 21), finger(16, 55, 21), finger(-100, 40, 22)];
  else if (pose === 'spread') fingers = [finger(-60, 56, 20), finger(-22, 62, 20), finger(16, 58, 20), finger(-115, 44, 22)];
  else if (pose === 'point') fingers = [finger(0, 70, 21), finger(-95, 34, 22)];
  else if (pose === 'thumb') fingers = [finger(-90, 50, 23)];
  else if (pose === 'fist' || pose === 'hold') fingers = [];
  const base = [16, 0];
  // outlines
  for (const [fx, fy, w] of fingers) out += L(base[0], base[1], base[0] + fx, base[1] + fy, { stroke: p.ink, 'stroke-width': w + LW * 2, 'stroke-linecap': 'round' });
  out += C(18, 0, palmR, { fill: p.hand, ...sk });
  for (const [fx, fy, w] of fingers) out += L(base[0], base[1], base[0] + fx, base[1] + fy, { stroke: p.hand, 'stroke-width': w, 'stroke-linecap': 'round' });
  out += C(18, 0, palmR - LW / 2, { fill: p.hand });
  if (pose === 'fist' || pose === 'point' || pose === 'thumb' || pose === 'hold') {
    // knuckle lines
    out += P(`M${30},${-20 * my} Q${44},${-6 * my} ${34},${8 * my}`, { fill: 'none', stroke: p.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
    out += P(`M${24},${10 * my} Q${36},${22 * my} ${26},${30 * my}`, { fill: 'none', stroke: p.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
  }
  return G(tr(0, 0, 0, scale), out);
}

// LIMB: noodle stroke a->j->b with outline ----------------------------------------
function limb(a, j, b, w, fill, ink, phase) {
  const d = through(a, j, b);
  if (phase === 'outline') return P(d, { fill: 'none', stroke: ink, 'stroke-width': w + LW * 2, 'stroke-linecap': 'round' });
  return P(d, { fill: 'none', stroke: fill, 'stroke-width': w, 'stroke-linecap': 'round' });
}

// HAIR ---------------------------------------------------------------------------
// [x, y, tip?] around the head (head-local, head center at 0,0)
const HAIR_OUT = [
  [-140, -28, 0], [-170, -82, 1], [-150, -116, 0], [-182, -158, 1], [-134, -172, 0], [-150, -226, 1],
  [-92, -204, 0], [-80, -262, 1], [-34, -224, 0], [4, -270, 1], [36, -224, 0], [88, -256, 1], [98, -204, 0],
  [158, -218, 1], [140, -170, 0], [184, -146, 1], [152, -112, 0], [172, -76, 1], [140, -28, 0],
];
const HAIR_FRINGE = [
  [128, -58, 1], [110, -96, 0], [90, -56, 1], [64, -100, 0], [38, -62, 1], [16, -104, 0], [-12, -64, 1],
  [-38, -104, 0], [-64, -60, 1], [-90, -100, 0], [-112, -60, 1], [-130, -92, 0],
];

function hairShape(amt, t) {
  // amt: 0 normal, 1 electrified (spikes stretched outwards + jitter)
  const cx = 0, cy = -60;
  const map = ([x, y, tip], i) => {
    if (!tip || amt <= 0) return [x, y];
    const dx = x - cx, dy = y - cy;
    const len = Math.hypot(dx, dy);
    const k = 1 + amt * (0.55 + 0.25 * hash(i * 3.1));
    const jit = amt * 10 * noise(t * 18 + i * 1.7, i);
    // bias spikes upwards when electrified
    const ux = dx / len, uy = dy / len;
    const bx = lerp(ux, ux * 0.6, amt), by = lerp(uy, uy - 0.6, amt);
    const bl = Math.hypot(bx, by);
    return [cx + (bx / bl) * len * k + jit, cy + (by / bl) * len * k + jit * 0.5];
  };
  const out = HAIR_OUT.map(map);
  const fr = HAIR_FRINGE.map(([x, y, tip], i) => (tip && amt > 0 ? [x + amt * 6 * noise(t * 20 + i, 9), y + amt * 18] : [x, y]));
  const pts = out.concat(fr);
  // rounded-ish spikes: quadratic segments using midpoints, tips stay sharp
  let d = '';
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    d += (i === 0 ? 'M' : 'L') + n2(p[0]) + ',' + n2(p[1]);
  }
  return d + 'Z';
}

// HEAD (local: neck joint at 0,0; head center at 0,-165) -------------------------
function head(st, p) {
  const sk = { stroke: p.ink, 'stroke-width': LW, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
  const fatK = 1 + st.fat * 0.22;
  let o = '';
  // ears
  o += EL(-140 * fatK, 8, 25, 33, { fill: p.skin, ...sk });
  o += EL(140 * fatK, 8, 25, 33, { fill: p.skin, ...sk });
  o += P(`M${-146 * fatK},${-6} q-10,14 2,28`, { fill: 'none', stroke: p.skinSh, 'stroke-width': 6, 'stroke-linecap': 'round' });
  o += P(`M${146 * fatK},${-6} q10,14 -2,28`, { fill: 'none', stroke: p.skinSh, 'stroke-width': 6, 'stroke-linecap': 'round' });
  // head shape
  const hw = 140 * fatK, jaw = 112 * (1 + st.fat * 0.35);
  const headD = `M${-hw},-40 C${-hw - 4},-132 -84,-174 0,-174 C84,-174 ${hw + 4},-132 ${hw},-40 C${hw - 2},62 ${jaw},150 0,152 C${-jaw},150 ${-hw + 2},62 ${-hw},-40Z`;
  o += P(headD, { fill: p.skin, ...sk });
  // jaw shade
  o += P(`M${-hw + 18},40 C${-hw + 30},110 ${-jaw * 0.6},140 0,142 C${jaw * 0.6},140 ${hw - 30},110 ${hw - 18},40 C${hw - 40},118 ${jaw * 0.5},128 0,130 C${-jaw * 0.5},128 ${-hw + 40},118 ${-hw + 18},40Z`, { fill: p.skinSh, opacity: 0.55 });
  // hair
  if (st.hairStyle === 'short') {
    o += P('M-146,-30 C-158,-150 -86,-206 0,-206 C86,-206 158,-150 146,-30 Q128,-104 64,-112 Q20,-86 -30,-116 Q-100,-120 -146,-30Z', { fill: p.hair, ...sk });
    o += P('M-96,-170 Q-56,-192 -14,-186', { fill: 'none', stroke: p.hairHi, 'stroke-width': 9, 'stroke-linecap': 'round' });
  } else if (!st.bald) {
    const hd = hairShape(st.hair, st.t);
    const tw = st.hair * 30 * noise(st.t * 15, 4);
    o += P(`M-22,-226 C-30,-286 ${-4 + tw},-322 ${30 + tw},-330 C${14 + tw},-306 14,-276 24,-226Z`, { fill: p.hair, ...sk });
    o += P(hd, { fill: p.hair, ...sk });
    // hair strands / shading
    o += P('M-120,-150 Q-96,-120 -100,-104 M-60,-196 Q-50,-150 -58,-112 M10,-206 Q16,-160 6,-116 M70,-196 Q76,-150 72,-112 M124,-150 Q118,-118 118,-100', { fill: 'none', stroke: p.hairSh, 'stroke-width': 7, 'stroke-linecap': 'round', opacity: 0.9 });
    o += P('M-92,-176 Q-60,-198 -26,-190', { fill: 'none', stroke: p.hairHi, 'stroke-width': 10, 'stroke-linecap': 'round' });
  }
  // face
  o += face(st, p);
  if (st.helmet) {
    o += C(0, -40, 250, { fill: '#BFE6FF', 'fill-opacity': 0.28, stroke: '#ffffff', 'stroke-width': 14 });
    o += C(0, -40, 250, { fill: 'none', stroke: p.ink, 'stroke-width': 6 });
    o += P('M-170,-150 A210,210 0 0,1 -40,-262', { fill: 'none', stroke: '#ffffff', 'stroke-width': 18, 'stroke-linecap': 'round', opacity: 0.8 });
    o += P('M-196,-60 A200,200 0 0,1 -186,-110', { fill: 'none', stroke: '#ffffff', 'stroke-width': 14, 'stroke-linecap': 'round', opacity: 0.6 });
  }
  return G(tr(0, -165), o);
}

function eye(cx, cy, st, p, side) {
  const sk = { stroke: p.ink, 'stroke-width': LW * 0.85, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
  const open = side < 0 ? (st.eyeOpenL ?? st.eyeOpen) : (st.eyeOpenR ?? st.eyeOpen);
  const rx = 46 * st.eyeSize, ry = 54 * st.eyeSize;
  const type = st.eyes;
  if (type === 'x') {
    return P(`M${cx - 26},${cy - 26} L${cx + 26},${cy + 26} M${cx + 26},${cy - 26} L${cx - 26},${cy + 26}`, { fill: 'none', ...sk, 'stroke-width': 12 });
  }
  if (type === 'closed' || open < 0.08) {
    return P(`M${cx - 36},${cy + 4} Q${cx},${cy + 24} ${cx + 36},${cy + 4}`, { fill: 'none', ...sk, 'stroke-width': 9 });
  }
  if (type === 'happy') {
    return P(`M${cx - 34},${cy + 10} Q${cx},${cy - 30} ${cx + 34},${cy + 10}`, { fill: 'none', ...sk, 'stroke-width': 10 });
  }
  if (type === 'squeeze') { // > <
    const s = side < 0 ? 1 : -1;
    return P(`M${cx - 30 * s},${cy - 24} L${cx + 26 * s},${cy} L${cx - 30 * s},${cy + 22}`, { fill: 'none', ...sk, 'stroke-width': 11 });
  }
  let o = EL(cx, cy, rx, ry * open, { fill: p.white, ...sk });
  if (type === 'spiral') {
    let d = '';
    for (let i = 0; i <= 40; i++) {
      const a = i * 0.45 + st.t * 9 * side, r = i * 0.95;
      d += (i ? 'L' : 'M') + n2(cx + Math.cos(a) * r) + ',' + n2(cy + Math.sin(a) * r * open);
    }
    return o + P(d, { fill: 'none', stroke: p.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
  }
  const pr = 12 * st.pupil * Math.max(0.6, st.eyeSize * 0.9);
  const lx = clamp(st.look[0], -1, 1) * (rx - pr - 10), ly = clamp(st.look[1], -1, 1) * (ry * open - pr - 10);
  if (type === 'star') {
    let d = '';
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + (i * Math.PI) / 5, r = i % 2 ? 9 : 22;
      d += (i ? 'L' : 'M') + n2(cx + lx + Math.cos(a) * r) + ',' + n2(cy + ly + Math.sin(a) * r);
    }
    o += P(d + 'Z', { fill: '#FFD23F', stroke: p.ink, 'stroke-width': 3 });
  } else {
    o += C(cx + lx, cy + ly, pr, { fill: p.ink });
    if (st.pupil > 1.2) o += C(cx + lx - pr * 0.35, cy + ly - pr * 0.35, pr * 0.28, { fill: '#fff' });
  }
  if (open < 0.97 && open >= 0.08) {
    // eyelid line for half-closed eyes
    o += P(`M${cx - rx},${cy - ry * open * 0.15} Q${cx},${cy - ry * open * 0.5} ${cx + rx},${cy - ry * open * 0.15}`, { fill: 'none', stroke: 'none' });
  }
  return o;
}

function face(st, p) {
  const sk = { stroke: p.ink, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
  let o = '';
  const fatK = 1 + st.fat * 0.22;
  // cheeks
  if (st.blush > 0) {
    o += EL(-86 * fatK, 50, 26, 15, { fill: p.blush, opacity: n2(0.7 * st.blush) });
    o += EL(86 * fatK, 50, 26, 15, { fill: p.blush, opacity: n2(0.7 * st.blush) });
  }
  if (st.freckles) {
    for (const s of [-1, 1]) {
      o += C(s * 82 * fatK, 40, 4.5, { fill: p.freckle }) + C(s * 98 * fatK, 52, 4, { fill: p.freckle }) + C(s * 72 * fatK, 56, 4, { fill: p.freckle });
    }
  }
  // eyes
  const ey = -14;
  o += eye(-49, ey, st, p, -1) + eye(49, ey, st, p, 1);
  // brows
  if (st.eyes !== 'x') {
    for (const s of [-1, 1]) {
      const raise = (s < 0 ? st.browL : st.browR) ?? st.brow;
      const tilt = st.browTilt; // + worried (inner up), - angry (inner down)
      const by = -86 - raise * 22 - (st.eyeSize - 1) * 40;
      const inner = [s * 18, by - tilt * 16], outer = [s * 82, by + tilt * 10];
      const mid = [s * 50, by - 8 - Math.abs(tilt) * 2];
      o += P(through(inner, mid, outer), { fill: 'none', ...sk, 'stroke-width': 14 });
    }
  }
  // nose
  o += P('M-4,26 C-24,40 -18,62 2,62 C14,62 20,54 16,46', { fill: 'none', ...sk, 'stroke-width': 7 });
  // mouth
  o += mouth(st, p);
  // sweat
  if (st.sweat > 0) {
    const sy = 10 * Math.sin(st.t * 6);
    o += G(tr(120 * fatK, -110 + sy * st.sweat, 0, st.sweat), P('M0,-28 C10,-10 18,0 18,10 C18,22 -18,22 -18,10 C-18,0 -10,-10 0,-28Z', { fill: '#8FD3FF', stroke: p.ink, 'stroke-width': 5 }));
  }
  return o;
}

function mouth(st, p) {
  const sk = { stroke: p.ink, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
  const w = st.mouthW, op = st.mouthOpen, my = 100;
  switch (st.mouth) {
    case 'line': return P(`M${-30 * w},${my} Q0,${my + 4} ${30 * w},${my}`, { fill: 'none', ...sk, 'stroke-width': 8 });
    case 'smile': return P(`M${-44 * w},${my - 12} Q0,${my + 26} ${44 * w},${my - 12}`, { fill: 'none', ...sk, 'stroke-width': 8 });
    case 'smirk': return P(`M${-36 * w},${my} Q${10 * w},${my + 14} ${40 * w},${my - 14}`, { fill: 'none', ...sk, 'stroke-width': 8 });
    case 'frown': return P(`M${-38 * w},${my + 12} Q0,${my - 16} ${38 * w},${my + 12}`, { fill: 'none', ...sk, 'stroke-width': 8 });
    case 'wavy': {
      let d = `M${-44 * w},${my}`;
      for (let i = 1; i <= 6; i++) d += ` Q${(-44 + (i - 0.5) * 14.67) * w},${my + (i % 2 ? -10 : 10)} ${(-44 + i * 14.67) * w},${my}`;
      return P(d, { fill: 'none', ...sk, 'stroke-width': 7 });
    }
    case 'grin': {
      const d = `M${-58 * w},${my - 16} Q0,${my - 4} ${58 * w},${my - 16} Q${50 * w},${my + 46 * op} 0,${my + 48 * op} Q${-50 * w},${my + 46 * op} ${-58 * w},${my - 16}Z`;
      return P(d, { fill: p.mouth, ...sk, 'stroke-width': 7 }) +
        P(`M${-52 * w},${my - 13} Q0,${my - 2} ${52 * w},${my - 13} L${48 * w},${my + 6} Q0,${my + 14} ${-48 * w},${my + 6}Z`, { fill: p.teeth }) +
        P(d, { fill: 'none', ...sk, 'stroke-width': 7 });
    }
    case 'grit': {
      const hw = 52 * w, hh = 24 * op;
      let o = R(-hw, my - hh, hw * 2, hh * 2, { rx: 16, fill: p.teeth, ...sk, 'stroke-width': 7 });
      o += L(-hw, my, hw, my, { stroke: p.ink, 'stroke-width': 5 });
      for (let i = -2; i <= 2; i++) o += L(i * hw * 0.38, my - hh, i * hw * 0.38, my + hh, { stroke: p.ink, 'stroke-width': 4 });
      return o;
    }
    case 'O': {
      const rx = 24 * w * (0.6 + 0.4 * op), ry = 32 * op;
      return EL(0, my + 4, rx, ry, { fill: p.mouth, ...sk, 'stroke-width': 7 }) + EL(0, my + 4 + ry * 0.5, rx * 0.6, ry * 0.32, { fill: p.tongue });
    }
    case 'scream': {
      const hw = 50 * w, top = my - 18, bot = my + 52 * op;
      const d = `M${-hw},${top} Q0,${top - 10} ${hw},${top} Q${hw + 6},${bot} 0,${bot} Q${-hw - 6},${bot} ${-hw},${top}Z`;
      return P(d, { fill: p.mouth, ...sk, 'stroke-width': 7 }) +
        P(`M${-hw * 0.8},${top + 2} Q0,${top - 6} ${hw * 0.8},${top + 2} L${hw * 0.72},${top + 14} Q0,${top + 8} ${-hw * 0.72},${top + 14}Z`, { fill: p.teeth }) +
        EL(0, bot - 14 * op, hw * 0.5, 13 * op, { fill: p.tongue }) +
        P(d, { fill: 'none', ...sk, 'stroke-width': 7 });
    }
    case 'tongue': { // tongue out, saliva bubbles handled by scene
      const d = `M${-40 * w},${my - 6} Q0,${my + 30} ${40 * w},${my - 6}Z`;
      return P(d, { fill: p.mouth, ...sk, 'stroke-width': 7 }) +
        P(`M-22,${my + 4} C-26,${my + 60} 26,${my + 60} 22,${my + 4}Z`, { fill: p.tongue, ...sk, 'stroke-width': 6 }) +
        L(0, my + 12, 0, my + 34, { stroke: '#c94a52', 'stroke-width': 4, 'stroke-linecap': 'round' });
    }
    case 'puff': // cheeks puffed, holding breath
      return P(`M${-20 * w},${my} Q0,${my + 8} ${20 * w},${my}`, { fill: 'none', ...sk, 'stroke-width': 8 });
    case 'blow': // exhaling
      return EL(0, my + 4, 14, 12, { fill: p.mouth, ...sk, 'stroke-width': 6 });
    default: return '';
  }
}

// TORSO --------------------------------------------------------------------------
function torso(st, p) {
  const sk = { stroke: p.ink, 'stroke-width': LW, 'stroke-linejoin': 'round' };
  const f = 1 + st.fat * 1.1;
  const wB = 104 * f, wT = 118 * (1 + st.fat * 0.6), yB = -400, yT = -640 + st.bob, belly = st.fat * 60;
  const shirt = st.shirtless ? p.skin : p.shirt, shirtSh = st.shirtless ? p.skinSh : p.shirtSh;
  const d = `M${-wB},${yB} C${-wB - belly},${yB - 90} ${-wT - belly * 0.6},${yT + 90} ${-wT},${yT + 26} Q${-wT + 4},${yT} ${-wT + 40},${yT - 6} L${wT - 40},${yT - 6} Q${wT - 4},${yT} ${wT},${yT + 26} C${wT + belly * 0.6},${yT + 90} ${wB + belly},${yB - 90} ${wB},${yB}Z`;
  let o = P(d, { fill: shirt, ...sk });
  // side shade
  o += P(`M${wB - 8},${yB - 4} C${wB + belly - 10},${yB - 90} ${wT + belly * 0.6 - 12},${yT + 90} ${wT - 8},${yT + 30} C${wT - 40},${yT + 120} ${wB - 40},${yB - 80} ${wB - 30},${yB - 4}Z`, { fill: shirtSh, opacity: 0.8 });
  // collar
  if (!st.shirtless) o += P(`M-46,${yT - 6} Q0,${yT + 44} 46,${yT - 6}Z`, { fill: p.skin, ...sk }) + P(`M-30,${yT - 4} Q0,${yT + 26} 30,${yT - 4}Z`, { fill: p.skinSh, opacity: 0.6 });
  else o += P(`M-30,${yT + 70} Q-14,${yT + 84} -4,${yT + 72} M30,${yT + 70} Q14,${yT + 84} 4,${yT + 72} M-6,${yT + 170} q6,8 12,0`, { fill: 'none', stroke: p.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
  return o;
}

function pelvis(st, p, phase) {
  const f = 1 + st.fat * 1.1;
  const w = 104 * f;
  const d = `M${-w},-412 L${w},-412 L${w - 4},-360 Q0,-338 ${-w + 4},-360Z`;
  if (phase === 'outline') return P(d, { fill: p.ink, stroke: p.ink, 'stroke-width': LW * 2, 'stroke-linejoin': 'round' });
  return P(d, { fill: p.pants });
}

// SKELETON (x-ray flash) --------------------------------------------------------
function skeleton(st, joints) {
  const bone = '#ffffff', glow = '#9FE7FF';
  const { sL, sR, eL, eR, hL, hR, hipL, hipR, kL, kR, fL, fR } = joints;
  let o = '';
  const b = (a, c, w = 18) => L(a[0], a[1], c[0], c[1], { stroke: bone, 'stroke-width': w, 'stroke-linecap': 'round' });
  // spine + ribs
  o += b([0, -640], [0, -400], 16);
  for (let i = 0; i < 5; i++) {
    const y = -610 + i * 38, w = 90 - i * 6;
    o += P(`M0,${y} Q${-w},${y - 6} ${-w + 12},${y + 26} M0,${y} Q${w},${y - 6} ${w - 12},${y + 26}`, { fill: 'none', stroke: bone, 'stroke-width': 11, 'stroke-linecap': 'round' });
  }
  o += P('M-95,-400 Q0,-350 95,-400 L70,-360 Q0,-330 -70,-360Z', { fill: bone });
  o += b([-110, -628], [110, -628], 14);
  o += b(sL, eL) + b(eL, hL) + b(sR, eR) + b(eR, hR);
  o += C(hL[0], hL[1], 22, { fill: bone }) + C(hR[0], hR[1], 22, { fill: bone });
  o += b(hipL, kL, 22) + b(kL, fL, 20) + b(hipR, kR, 22) + b(kR, fR, 20);
  // skull
  const sk = G(tr(st.headX, -670 + st.headY, st.headRot),
    G(tr(0, -165),
      P('M-120,-30 C-125,-130 -70,-165 0,-165 C70,-165 125,-130 120,-30 C118,40 80,80 50,90 L50,135 L-50,135 L-50,90 C-80,80 -118,40 -120,-30Z', { fill: bone }),
      EL(-48, -10, 34, 40, { fill: '#1d3f73' }), EL(48, -10, 34, 40, { fill: '#1d3f73' }),
      P('M0,30 L-14,60 L14,60Z', { fill: '#1d3f73' }),
      ...[-36, -12, 12, 36].map(x => L(x, 98, x, 132, { stroke: '#1d3f73', 'stroke-width': 5 }))));
  return G('', o, sk);
}

// MAIN ---------------------------------------------------------------------------
function rusty(input = {}) {
  const st = Object.assign(defaults(), input);
  const p = palette(st);
  if (st.xray) { p.skin = '#3d7fd6'; p.skinSh = '#2f6bc0'; p.shirt = '#4b93e6'; p.shirtSh = '#3d7fd6'; p.pants = '#3a78cf'; p.pantsSh = '#3a78cf'; p.hair = '#5aa0f0'; p.hairSh = '#4b93e6'; p.hairHi = '#7ab8ff'; p.ink = '#173a6e'; p.shoe = '#173a6e'; p.freckle = p.skin; }

  const f = 1 + st.fat;
  const armW = 40 * (1 + st.fat * 0.9), legW = 80 * (1 + st.fat * 0.55);
  const lean = st.lean;
  // shoulder & hip joints (body coords)
  const shY = -616 + st.bob;
  const shX = 112 * (1 + st.fat * 0.6);
  const sL = [-shX, shY], sR = [shX, shY];
  const hipL = [-56 * (1 + st.fat * 0.9), -405], hipR = [56 * (1 + st.fat * 0.9), -405];
  const armLen = 140 * (st.armK || 1);
  const hL = st.handL, hR = st.handR;
  const eL = ik(sL, hL, armLen, armLen, st.bendL), eR = ik(sR, hR, armLen, armLen, st.bendR);
  const legLen = 183;
  const fL = [st.footL[0] - st.fat * 60, st.footL[1]], fR = [st.footR[0] + st.fat * 60, st.footR[1]];
  const ankL = [fL[0], fL[1] - 30], ankR = [fR[0], fR[1] - 30];
  const kL = ik(hipL, ankL, legLen, legLen, -1), kR = ik(hipR, ankR, legLen, legLen, 1);

  let body = '';
  if (st.headOnly) {
    const g = `<g transform="${tr(st.x, st.y, st.rot, st.s * st.sx, st.s * st.sy)}">${head(st, p)}</g>`;
    return st.opacity < 1 ? `<g opacity="${n2(st.opacity)}">${g}</g>` : g;
  }
  // LEGS (outline pass then fill pass so they merge with the pelvis)
  if (!st.hideLegs) {
    let legs = '';
    legs += limb(hipL, kL, ankL, legW, p.pants, p.ink, 'outline') + limb(hipR, kR, ankR, legW, p.pants, p.ink, 'outline') + pelvis(st, p, 'outline');
    legs += limb(hipL, kL, ankL, legW, p.pants, p.ink, 'fill') + limb(hipR, kR, ankR, legW, p.pants, p.ink, 'fill') + pelvis(st, p, 'fill');
    // pants shade on right leg
    legs += P(through([hipR[0] + legW * 0.28, hipR[1] + 10], [kR[0] + legW * 0.3, kR[1]], [ankR[0] + legW * 0.28, ankR[1] - 10]), { fill: 'none', stroke: p.pantsSh, 'stroke-width': legW * 0.3, 'stroke-linecap': 'round', opacity: 0.7 });
    // feet
    for (const [ft, s] of [[fL, -1], [fR, 1]]) {
      const foot = st.socks
        ? P('M-26,-36 L22,-36 L22,-8 Q48,-8 52,8 Q50,18 0,18 Q-30,18 -28,4Z', { fill: p.sock, stroke: p.ink, 'stroke-width': LW, 'stroke-linejoin': 'round' })
        : P('M-34,-30 Q-4,-42 26,-30 Q62,-18 64,6 Q64,20 40,20 L-30,20 Q-46,18 -44,0 Q-44,-22 -34,-30Z', { fill: p.shoe, stroke: p.ink, 'stroke-width': LW, 'stroke-linejoin': 'round' }) +
          P('M-30,12 L54,12', { stroke: '#ffffff', 'stroke-width': 5, opacity: 0.22, 'stroke-linecap': 'round' }) +
          P('M-14,-30 Q4,-38 22,-30', { fill: 'none', stroke: '#ffffff', 'stroke-width': 6, opacity: 0.25, 'stroke-linecap': 'round' });
      legs += G(tr(ft[0], ft[1] - 4, st.footRot ? st.footRot * s : 0, s, 1), foot);
    }
    body += legs;
  }

  const armPass = () => {
    let a = '';
    for (const [s, e, h, pose, rotOv, mirror] of [[sL, eL, hL, st.handPoseL, st.handRotL, false], [sR, eR, hR, st.handPoseR, st.handRotR, true]]) {
      const armC = st.longSleeves ? p.shirt : p.skin;
      a += limb(s, e, h, armW, armC, p.ink, 'outline') + limb(s, e, h, armW, armC, p.ink, 'fill');
      // sleeve
      if (!st.shirtless) {
        const ang = Math.atan2(e[1] - s[1], e[0] - s[0]);
        a += G(tr(s[0], s[1], deg(ang)), P(`M-30,${-armW * 0.95} L56,${-armW * 0.9} Q66,0 56,${armW * 0.9} L-30,${armW * 0.95} Q-46,0 -30,${-armW * 0.95}Z`, { fill: p.shirt, stroke: p.ink, 'stroke-width': LW, 'stroke-linejoin': 'round' }));
      }
      const ha = rotOv != null ? rotOv : deg(Math.atan2(h[1] - e[1], h[0] - e[0]));
      a += G(tr(h[0], h[1], ha), hand(pose, p, 1 + st.fat * 0.5, mirror ^ (st.flip < 0)));
    }
    return a;
  };

  // TORSO + ARMS
  let upper = '';
  if (st.backpack) upper += R(-150, -700 + st.bob, 300, 320, { rx: 40, fill: '#C9D2DF', stroke: p.ink, 'stroke-width': LW }) + R(-120, -740 + st.bob, 60, 60, { rx: 14, fill: '#9AA6B8', stroke: p.ink, 'stroke-width': LW });
  if (st.armsBehind) upper += armPass();
  // neck (behind the shirt collar)
  upper += R(-28, -700 + st.bob, 56, 80, { fill: p.skin, stroke: p.ink, 'stroke-width': LW });
  upper += R(-24, -668 + st.bob, 48, 22, { fill: p.skinSh, opacity: 0.7 });
  upper += torso(st, p);
  if (st.helmet) upper += R(-120, -690 + st.bob, 240, 60, { rx: 28, fill: '#C9D2DF', stroke: p.ink, 'stroke-width': LW });
  if (!st.armsBehind) upper += armPass();
  // head
  if (!st.noHead) upper += G(tr(st.headX, -666 + st.bob + st.headY, st.headRot, 1 + st.fat * 0.12), head(st, p));

  body += G(lean ? `rotate(${n2(lean)} 0 -420)` : '', upper);
  if (st.xray) body += skeleton(st, { sL, sR, eL, eR, hL, hR, hipL, hipR, kL, kR, fL: ankL, fR: ankR });

  const flipT = st.flip < 0 ? ' scale(-1 1)' : '';
  const g = `<g transform="${tr(st.x, st.y, st.rot, st.s * st.sx, st.s * st.sy)}${flipT}">${body}</g>`;
  return st.opacity < 1 ? `<g opacity="${n2(st.opacity)}">${g}</g>` : g;
}

// EXPRESSIONS --------------------------------------------------------------------
const EXPR = {
  neutral: { mouth: 'line', brow: 0, browTilt: 0, eyeSize: 1, pupil: 1 },
  happy: { mouth: 'smile', brow: 0.4, browTilt: 0, eyeSize: 1, pupil: 1 },
  grin: { mouth: 'grin', mouthOpen: 1, brow: 0.5, browTilt: 0, pupil: 1 },
  proud: { mouth: 'grin', mouthOpen: 0.8, eyes: 'happy', brow: 0.6 },
  smug: { mouth: 'smirk', brow: 0.2, browTilt: -0.3, eyeOpen: 0.75 },
  curious: { mouth: 'O', mouthOpen: 0.45, brow: 0.6, browL: 0.9, browTilt: 0.2, pupil: 1 },
  worried: { mouth: 'wavy', brow: 0.4, browTilt: 1, pupil: 0.9 },
  scared: { mouth: 'scream', mouthOpen: 0.8, brow: 1, browTilt: 1, eyeSize: 1.12, pupil: 0.6, sweat: 1 },
  shocked: { mouth: 'O', mouthOpen: 1, brow: 1.3, browTilt: 0.4, eyeSize: 1.2, pupil: 0.55 },
  pain: { mouth: 'grit', mouthOpen: 1, eyes: 'squeeze', brow: -0.2, browTilt: -0.8 },
  angry: { mouth: 'grit', mouthOpen: 0.8, brow: -0.3, browTilt: -1, pupil: 0.9 },
  sad: { mouth: 'frown', brow: 0.3, browTilt: 1, pupil: 1 },
  dizzy: { mouth: 'wavy', eyes: 'spiral', brow: 0.5, browTilt: 0.6 },
  dead: { mouth: 'O', mouthOpen: 0.35, eyes: 'x', brow: 0 },
  sick: { mouth: 'wavy', brow: 0.3, browTilt: 1, eyeOpen: 0.7, skinTint: '#9ACD5A', skinTintAmt: 0.45 },
  puff: { mouth: 'puff', brow: 0.6, browTilt: 0.5, eyeSize: 1.05, pupil: 0.8, blush: 1 },
  blow: { mouth: 'blow', brow: 0.4, browTilt: 0.3, eyeOpen: 0.8 },
  starry: { mouth: 'grin', eyes: 'star', brow: 0.8 },
  sleepy: { mouth: 'line', eyes: 'closed', brow: -0.1 },
};

// idle life: breathing, blinking, tiny sway. Returns partial state.
function idle(t, seed = 1, amt = 1) {
  const breath = Math.sin(t * 2.4 + seed) * 4 * amt;
  // blink every ~2.8s with jitter
  const period = 2.6 + hash(seed) * 1.2;
  const ph = ((t + hash(seed * 7) * period) % period) / period;
  const blinkDur = 0.14 / period;
  const blink = ph < blinkDur ? Math.abs(Math.cos((ph / blinkDur) * Math.PI)) : 1;
  return {
    bob: breath,
    headRot: noise(t * 0.7, seed) * 3 * amt,
    headY: Math.sin(t * 2.4 + seed + 0.6) * 2 * amt,
    eyeBlink: blink,
    t,
  };
}

// compose: state = rusty-ready object with expression + idle merged
function pose(base, expr, t, seed = 1, idleAmt = 1) {
  const e = typeof expr === 'string' ? EXPR[expr] : expr || {};
  const i = idle(t, seed, idleAmt);
  const s = Object.assign({}, e, base);
  s.bob = (base.bob || 0) + i.bob;
  s.headRot = (base.headRot || 0) + i.headRot;
  s.headY = (base.headY || 0) + i.headY;
  s.t = t;
  const eo = s.eyeOpen ?? 1;
  if (!base.noBlink) s.eyeOpen = eo * i.eyeBlink;
  return s;
}

module.exports = { rusty, EXPR, idle, pose, PAL, defaults };
