// Video 3 — "What if you drank too much water?"
'use strict';
const { clamp, lerp, E, prog, kf, rng, noise, hash, mixColor, n2, tr, G, O, P, C, EL, R, L, PL, PG, smoothPath } = require('../lib/core');
const { rusty, pose } = require('../lib/rusty');
const { BG, flat } = require('../lib/bg');
const { text } = require('../lib/text');
const fx = require('../lib/fx');
const pr = require('../lib/props');
const { timeline, camKeys } = require('../lib/scene');
const INK = '#2b2220', LW = 8;

// ---------------------------------------------------------------- local props
function bottle(x, y, rot = 0, s = 1, level = 0.8, labelOn = true) {
  const h = 300, w = 120;
  let o = '';
  o += R(-w / 2, -h / 2 + 50, w, h - 50, { rx: 34, fill: '#D9F1FF', 'fill-opacity': 0.9, stroke: INK, 'stroke-width': LW });
  const lh = (h - 70) * clamp(level);
  if (lh > 4) o += R(-w / 2 + 10, h / 2 - 10 - lh, w - 20, lh, { rx: 24, fill: '#4FB3F0' });
  o += P(`M${-w / 2 + 6},${-h / 2 + 70} Q${-w / 2 + 10},${-h / 2 + 30} -22,${-h / 2 + 10} L-22,${-h / 2 - 10} L22,${-h / 2 - 10} L22,${-h / 2 + 10} Q${w / 2 - 10},${-h / 2 + 30} ${w / 2 - 6},${-h / 2 + 70}`, { fill: '#D9F1FF', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  o += R(-28, -h / 2 - 44, 56, 40, { rx: 10, fill: '#2C7BE5', stroke: INK, 'stroke-width': LW });
  if (labelOn) o += R(-w / 2, -10, w, 80, { fill: '#FF6B6B', stroke: INK, 'stroke-width': 6 }) + text('1L', { x: 0, y: 30, size: 48, sw: 6, shadow: false, fill: '#ffffff' });
  o += R(-w / 2 + 16, -h / 2 + 80, 16, 150, { rx: 8, fill: '#ffffff', opacity: 0.7 });
  return G(tr(x, y, rot, s), o);
}

function glass(x, y, s = 1, level = 0.7) {
  let o = P('M-80,-120 L80,-120 L64,120 L-64,120Z', { fill: '#E6F6FF', 'fill-opacity': 0.85, stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  const top = 120 - 230 * level;
  o += P(`M${-64 - (top + 120) / 240 * -16 - 16 + 16},${top} L${64 + 0},${top} L60,112 L-60,112Z`, { fill: '#4FB3F0' });
  o += R(-60, -100, 14, 160, { rx: 7, fill: '#ffffff', opacity: 0.8 });
  return G(tr(x, y, 0, s), o);
}

function kidney(x, y, s = 1, o = {}) {
  const { flip = 1, mood = 'strain', t = 0 } = o;
  const d = 'M-60,-150 C40,-172 128,-90 116,12 C104,112 40,172 -40,162 C-122,152 -134,62 -84,22 C-56,0 -56,-30 -86,-62 C-126,-104 -112,-140 -60,-150Z';
  let g = P(d, { fill: '#D2565F', stroke: INK, 'stroke-width': LW + 2, 'stroke-linejoin': 'round' });
  g += P('M60,-110 C110,-60 112,40 70,110 C96,40 92,-40 60,-110Z', { fill: '#A83E48', opacity: 0.7 });
  g += EL(-40, -100, 30, 18, { fill: '#fff', opacity: 0.35, transform: 'rotate(-20 -40 -100)' });
  // face (always upright)
  const sq = mood === 'strain';
  let f = '';
  for (const ex of [-28, 32]) {
    if (sq) f += P(`M${ex - 16},-20 L${ex + 10},-8 L${ex - 16},4`, { fill: 'none', stroke: INK, 'stroke-width': 8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', transform: ex > 0 ? `translate(${ex * 2} 0) scale(-1 1)` : '' });
    else f += EL(ex, -10, 18, 22, { fill: '#fff', stroke: INK, 'stroke-width': 5 }) + C(ex, -8, 7, { fill: INK });
  }
  f += sq ? R(-26, 34, 52, 26, { rx: 10, fill: '#fff', stroke: INK, 'stroke-width': 5 }) + L(-26, 47, 26, 47, { stroke: INK, 'stroke-width': 3 })
    : P('M-20,44 Q0,60 20,44', { fill: 'none', stroke: INK, 'stroke-width': 7, 'stroke-linecap': 'round' });
  f += G(tr(70, -70 + Math.sin(t * 7) * 6, 0, 0.8), P('M0,-28 C10,-10 18,0 18,10 C18,22 -18,22 -18,10 C-18,0 -10,-10 0,-28Z', { fill: '#8FD3FF', stroke: INK, 'stroke-width': 5 }));
  return G(tr(x, y, 0, s), G(`scale(${flip} 1)`, g), G(tr(flip * -10, 0), f));
}

function rbc(x, y, s = 1, rot = 0) {
  return G(tr(x, y, rot, s), EL(0, 0, 46, 34, { fill: '#E2414E', stroke: INK, 'stroke-width': 6 }), EL(0, 0, 22, 14, { fill: '#B52D3B' }));
}
function salt(x, y, s = 1, rot = 0, a = 1) {
  return O(a, G(tr(x, y, rot, s), R(-22, -22, 44, 44, { rx: 6, fill: '#ffffff', stroke: INK, 'stroke-width': 5 }), P('M-22,-22 L-10,-34 L34,-34 L22,-22 M22,-22 L34,-34 L34,10 L22,22', { fill: '#DDE8F0', stroke: INK, 'stroke-width': 5, 'stroke-linejoin': 'round' })));
}
function drop(x, y, s = 1, rot = 0) {
  return G(tr(x, y, rot, s), P('M0,-34 C12,-12 22,0 22,12 C22,28 -22,28 -22,12 C-22,0 -12,-12 0,-34Z', { fill: '#4FB3F0', stroke: INK, 'stroke-width': 5 }), C(-8, 8, 5, { fill: '#fff', opacity: 0.7 }));
}

function cell(x, y, r, o = {}) {
  const { t = 0, mood = 'happy', seed = 1, shine = 0, color = '#F3B0D4' } = o;
  const pts = [];
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    const rr = r * (1 + 0.04 * noise(t * 1.5 + i * 0.7, seed) * (1 - shine));
    pts.push([Math.cos(a) * rr, Math.sin(a) * rr]);
  }
  let g = P(smoothPath(pts), { fill: color, stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  g += P(smoothPath(pts.map(([px, py]) => [px * 0.86 + r * 0.06, py * 0.86 + r * 0.06])), { fill: mixColor(color, '#ffffff', 0.25), opacity: 0.6 });
  g += C(r * 0.38, -r * 0.4, r * 0.2, { fill: '#9B5FC0', stroke: INK, 'stroke-width': 5 });
  g += EL(-r * 0.45, -r * 0.5, r * 0.2 * (1 + shine), r * 0.11 * (1 + shine), { fill: '#ffffff', opacity: 0.55 + shine * 0.3, transform: `rotate(-35 ${n2(-r * 0.45)} ${n2(-r * 0.5)})` });
  // face
  const k = Math.min(1, r / 160);
  const big = mood === 'scared';
  for (const ex of [-0.22, 0.12]) g += EL(ex * r, r * 0.05, 20 * k * (big ? 1.25 : 1), 24 * k * (big ? 1.25 : 1), { fill: '#fff', stroke: INK, 'stroke-width': 5 }) + C(ex * r, r * 0.07, (big ? 6 : 8) * k, { fill: INK });
  if (mood === 'happy') g += P(`M${-0.18 * r},${0.28 * r} Q${-0.05 * r},${0.38 * r} ${0.08 * r},${0.28 * r}`, { fill: 'none', stroke: INK, 'stroke-width': 6, 'stroke-linecap': 'round' });
  else if (mood === 'scared') g += EL(-0.05 * r, 0.32 * r, 14 * k, 18 * k, { fill: '#5a1a1e', stroke: INK, 'stroke-width': 5 });
  else g += P(`M${-0.18 * r},${0.32 * r} q${0.06 * r},${-0.06 * r} ${0.12 * r},0 q${0.06 * r},${0.06 * r} ${0.12 * r},0`, { fill: 'none', stroke: INK, 'stroke-width': 6, 'stroke-linecap': 'round' });
  return G(tr(x, y), g);
}

function brainSkull(x, y, s = 1, o = {}) {
  const { swell = 0, t = 0, mood = 'happy' } = o;
  let g = '';
  // hair tuft + skull
  g += P('M-60,-470 L-30,-540 L0,-480 L30,-560 L60,-475 L100,-520 L90,-450Z', { fill: '#D8612B', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  g += EL(0, 0, 400, 470, { fill: '#F3EAD6', stroke: INK, 'stroke-width': LW + 4 });
  g += EL(0, 0, 340, 410, { fill: '#5B2B3A', stroke: INK, 'stroke-width': LW });
  g += P('M-60,-468 Q-30,-440 0,-470 Q30,-440 60,-468', { fill: 'none', stroke: '#BBAE92', 'stroke-width': 6 });
  // brain: grows; once it touches the skull it squashes against it
  const want = 0.78 + swell * 0.32;
  const sx = Math.min(want, 1.0), sy = Math.min(want * 1.02, 1.0);
  const press = Math.max(0, want - 1);
  const pts = [];
  for (let i = 0; i < 20; i++) {
    const a = (i / 20) * Math.PI * 2;
    pts.push([Math.cos(a) * 320 * sx * (1 + 0.03 * Math.sin(i * 5.3)), Math.sin(a) * 380 * sy * (1 + 0.03 * Math.cos(i * 4.1))]);
  }
  g += P(smoothPath(pts), { fill: mixColor('#F49FB0', '#FF6B7A', press * 3), stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' });
  let folds = '';
  const r = rng(3);
  for (let i = 0; i < 12; i++) {
    const cx = (r() - 0.5) * 460 * sx, cy = (r() - 0.5) * 560 * sy;
    folds += `M${n2(cx - 60)},${n2(cy)} q30,-40 60,0 q30,40 60,0 `;
  }
  g += P(folds, { fill: 'none', stroke: '#D97389', 'stroke-width': 9, 'stroke-linecap': 'round' });
  g += L(0, -370 * sy, 0, 370 * sy, { stroke: '#D97389', 'stroke-width': 9 });
  // face
  const big = mood === 'scared';
  for (const ex of [-90, 90]) g += EL(ex, -20, big ? 52 : 44, big ? 62 : 52, { fill: '#fff', stroke: INK, 'stroke-width': 7 }) + C(ex, -14, big ? 12 : 16, { fill: INK });
  if (big) g += EL(0, 120, 46, 56, { fill: '#5a1a1e', stroke: INK, 'stroke-width': 7 });
  else g += P('M-60,110 Q0,160 60,110', { fill: 'none', stroke: INK, 'stroke-width': 10, 'stroke-linecap': 'round' });
  return G(tr(x, y, 0, s), g);
}

function qmark(x, y, s = 1, rot = 0) {
  return text('?', { x, y, size: 150 * s, rot, fill: '#FFE45C', sw: 12 });
}

module.exports = function (T) {
  const cues = [];
  const cue = (t, sfx, gain = 0.5, args) => cues.push({ t: +t.toFixed(3), sfx, gain, ...(args ? { args } : {}) });
  const duration = T.duration + 0.3;
  const shots = [];
  const cut = id => T.s(id) - 0.08;

  // ------------------------------------------------------------- S1 drinking six liters
  {
    const t1 = cut('l2'), t6 = T.w('l1', 'six'), t3 = T.w('l1', 'three');
    for (let i = 0; i < 6; i++) cue(0.3 + i * 0.5, 'gulp', 0.45);
    cue(t6, 'pop', 0.55); cue(t3, 'pop', 0.55); cue(t3 + 0.05, 'clock', 0.3, [0.8, 6]);
    shots.push({
      t0: 0, t1, push: 0.06, punch: 0,
      draw(lt, t) {
        let s = BG.blue();
        const x = 540, y = 1640, sc = 1.0;
        const gulp = Math.max(0, Math.sin(t * Math.PI * 2 / 0.5)) * 10;
        const st = pose({ x, y, s: sc, headRot: -8, handR: [128, -830], handPoseR: 'hold', bendR: -1, blush: 0.6 }, { mouth: 'O', mouthOpen: 0.35, eyes: 'closed', brow: 0.3 }, t, 2);
        st.headY = -gulp * 0.4;
        s += rusty(st);
        // bottle in Rusty's frame: neck at the mouth
        s += G(tr(x, y, 0, sc), bottle(128, -827, -127, 0.95, kf(t, [[0, 0.9], [t1, 0.15]])));
        // empty bottles piling up
        for (let i = 0; i < 5; i++) {
          const k = fx.popIn(t, 0.35 + i * 0.5, 0.3);
          if (k > 0) s += bottle(130 + i * 70 + (i % 2) * 10, 1760 - (i % 2) * 6, 90 + i * 12, 0.55 * k, 0, false);
        }
        const k1 = fx.popIn(t, t6, 0.35), k2 = fx.popIn(t, t3, 0.35);
        if (k1 > 0) s += text('6 LITERS', { x: 540, y: 300, size: 150, sx: k1, sy: k1, rot: -3, fill: '#8FE3FF' });
        if (k2 > 0) {
          s += pr.stopwatch(900, 600, 0.42 * k2, { frac: prog(t, t3, t1) * 0.25 });
          s += text('3 HOURS', { x: 900, y: 760, size: 76, sx: k2, sy: k2, fill: '#FFE45C' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S2 sounds healthy... it can kill him
  {
    const t0 = cut('l2'), t1 = cut('l4'), th = T.w('l2', 'healthy'), tk = T.w('l3', 'kill');
    cue(th, 'sparkle', 0.45); cue(tk, 'impact', 0.7); cue(tk, 'slide_down', 0.3, [0.6]);
    shots.push({
      t0, t1, push: 0.05,
      shakes: [[tk, 0.35, 20]],
      draw(lt, t) {
        const bad = t > tk - 0.05;
        let s = bad ? BG.pink() + R(-600, -600, 2280, 3120, { fill: '#5A0F1A', opacity: 0.55 * prog(t, tk - 0.05, tk + 0.15) }) : BG.mint();
        const st = pose({ x: 540, y: 1660, s: 1.0 }, bad ? 'shocked' : 'proud', t, 3);
        if (!bad) { st.handR = [200, -560]; st.handPoseR = 'thumb'; st.bendR = -1; st.handL = [-240, -760]; st.handPoseL = 'fist'; st.bendL = -1; }
        else { st.handL = [-120, -760]; st.handR = [120, -760]; st.bendL = -1; st.bendR = 1; st.handPoseL = 'spread'; st.handPoseR = 'spread'; }
        s += rusty(st);
        if (!bad) {
          s += fx.sparkles(t, th, 540, 900, { n: 8, radius: 380, size: 44, seed: 4 });
          s += text('HEALTHY?', { x: 540, y: 330, size: 150, fill: '#7CFF9E', sx: fx.popIn(t, th), sy: fx.popIn(t, th), rot: -3 });
        } else {
          const k = fx.popIn(t, tk, 0.4);
          // skull and crossbones
          s += G(tr(540, 420, 0, k),
            L(-130, -90, 130, 130, { stroke: INK, 'stroke-width': 56, 'stroke-linecap': 'round' }), L(130, -90, -130, 130, { stroke: INK, 'stroke-width': 56, 'stroke-linecap': 'round' }),
            L(-130, -90, 130, 130, { stroke: '#F3EAD6', 'stroke-width': 40, 'stroke-linecap': 'round' }), L(130, -90, -130, 130, { stroke: '#F3EAD6', 'stroke-width': 40, 'stroke-linecap': 'round' }),
            C(0, -20, 120, { fill: '#F3EAD6', stroke: INK, 'stroke-width': 10 }), R(-60, 70, 120, 70, { rx: 20, fill: '#F3EAD6', stroke: INK, 'stroke-width': 10 }),
            EL(-45, -20, 32, 38, { fill: INK }), EL(45, -20, 32, 38, { fill: INK }), P('M0,30 L-14,56 L14,56Z', { fill: INK }));
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S3 kidneys: 1 liter per hour
  {
    const t0 = cut('l4'), t1 = cut('l5'), tk = T.w('l4', 'kidneys'), to = T.w('l4', 'one');
    cue(t0 + 0.1, 'splash', 0.4, [1.5]); cue(to, 'pop', 0.55); cue(to + 0.3, 'ding', 0.35);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.warm();
        // pouring stream from top
        const wob = Math.sin(t * 20) * 6;
        for (const xx of [330, 750]) {
          s += P(`M${xx - 30},-100 Q${xx - 20 + wob},300 ${xx - 26},620 L${xx + 26},620 Q${xx + 20 - wob},300 ${xx + 30},-100Z`, { fill: '#4FB3F0', stroke: INK, 'stroke-width': 6 });
          for (let i = 0; i < 4; i++) s += drop(xx + (hash(i + xx) - 0.5) * 80, 560 + ((t * 300 + i * 40) % 120), 0.8);
        }
        s += kidney(330, 850, 1.55, { flip: 1, t });
        s += kidney(750, 850, 1.55, { flip: -1, t });
        // slow drip out to a measuring cup
        s += P('M520,1180 Q540,1240 540,1320', { fill: 'none', stroke: INK, 'stroke-width': 36, 'stroke-linecap': 'round' }) + P('M520,1180 Q540,1240 540,1320', { fill: 'none', stroke: '#F2C1A0', 'stroke-width': 22, 'stroke-linecap': 'round' });
        const dp = ((t * 1.2) % 1);
        s += drop(540, 1350 + dp * 160, 0.8);
        s += glass(540, 1640, 1.3, 0.2 + prog(t, t0, t1) * 0.2);
        const k = fx.popIn(t, to, 0.4);
        if (k > 0) s += text('1 LITER / HOUR', { x: 540, y: 300, size: 120, sx: k, sy: k, rot: -2 });
        else s += text('KIDNEYS', { x: 540, y: 300, size: 120, sx: fx.popIn(t, tk), sy: fx.popIn(t, tk), fill: '#FF8A8A' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S4 blood dilutes the salt
  {
    const t0 = cut('l5'), t1 = cut('l6'), tb = T.w('l5', 'blood'), td = T.w('l5', 'dilutes');
    cue(tb, 'splash', 0.35); cue(td, 'slide_down', 0.35, [0.6]); cue(td + 0.1, 'pop', 0.4);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = flat('#F7D4D8');
        // vessel walls
        s += R(-200, 560, 1480, 800, { fill: '#F9B8BE' });
        s += P('M-200,560 Q540,520 1280,560', { fill: 'none', stroke: INK, 'stroke-width': 12 }) + P('M-200,1360 Q540,1400 1280,1360', { fill: 'none', stroke: INK, 'stroke-width': 12 });
        s += R(-200, 480, 1480, 80, { fill: '#E67F8C' }) + R(-200, 1360, 1480, 80, { fill: '#E67F8C' });
        const r = rng(8), flow = t * 260;
        const dil = prog(t, td - 0.3, td + 0.6);
        for (let i = 0; i < 14; i++) {
          const px = ((r() * 1400 + flow * (0.8 + r() * 0.4)) % 1500) - 200, py = 640 + r() * 640;
          s += rbc(px, py, 0.9, t * 40 + i * 30);
        }
        for (let i = 0; i < 14; i++) {
          const px = ((r() * 1400 + flow * (0.8 + r() * 0.4)) % 1500) - 200, py = 640 + r() * 640;
          const fade = i % 3 === 0 ? 1 : 1 - dil;
          if (fade > 0.02) s += salt(px, py, 0.9 * fade, t * 60 + i * 20, fade);
        }
        const nW = Math.floor(prog(t, tb - 0.3, td + 0.5) * 30);
        for (let i = 0; i < nW; i++) {
          const px = ((r() * 1400 + flow * (0.9 + r() * 0.3)) % 1500) - 200, py = 640 + r() * 640;
          s += drop(px, py, 0.9, Math.sin(t * 3 + i) * 15);
        }
        s += text('BLOOD', { x: 540, y: 330, size: 130, fill: '#FF8A8A' });
        if (t > td) {
          const k = fx.popIn(t, td, 0.4);
          s += G(tr(540, 1650, 0, k), salt(-150, 0, 2.2, 0), text('SALT', { x: 60, y: 0, size: 110, shadow: true }), fx.arrow([250, -80], [250, 90], 1, { color: '#FF6B6B', w: 26, head: 56 }));
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S5 water rushes into the cells
  {
    const t0 = cut('l6'), t1 = cut('l7'), tc = T.w('l6', 'cells'), tr_ = T.w('l6', 'rushes');
    cue(tc, 'pop', 0.45); cue(tr_, 'suck', 0.5, [0.9]);
    for (let i = 0; i < 6; i++) cue(tr_ + 0.2 + i * 0.1, 'bubble', 0.2, [0.9 + i * 0.1]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.lilac();
        const grow = prog(t, tr_ + 0.2, t1 + 0.4) * 0.12;
        const cr = 300 * (1 + grow);
        s += cell(540, 1050, cr, { t, mood: t > tr_ ? 'worried' : 'happy' });
        // drops moving inward
        const r = rng(3);
        for (let i = 0; i < 18; i++) {
          const a = r() * Math.PI * 2, ph = r();
          const sp = t > tr_ ? 0.9 : 0.15;
          const p = ((t - t0) * sp * (0.8 + r() * 0.4) + ph) % 1;
          const d = lerp(720, cr * 0.75, E.inQuad(p));
          if (d < cr * 0.95) continue;
          s += drop(540 + Math.cos(a) * d, 1050 + Math.sin(a) * d, 1.1, (a * 180) / Math.PI - 90);
        }
        if (t > tr_) for (let i = 0; i < 6; i++) {
          const a = (i / 6) * Math.PI * 2 + 0.3;
          s += fx.arrow([540 + Math.cos(a) * 520, 1050 + Math.sin(a) * 520], [540 + Math.cos(a) * 380, 1050 + Math.sin(a) * 380], prog(t, tr_, tr_ + 0.25), { color: '#4FB3F0', w: 18, head: 40 });
        }
        s += text('CELL', { x: 540, y: 330, size: 130, fill: '#F3B0D4', sx: fx.popIn(t, tc), sy: fx.popIn(t, tc) });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S6 cells swell like balloons
  {
    const t0 = cut('l7'), t1 = cut('l8'), ts = T.w('l7', 'swell'), tb = T.w('l7', 'balloons');
    cue(ts, 'inflate', 0.5, [1.0]); cue(tb, 'boing', 0.4, [1.1]); cue(tb + 0.2, 'slide_up', 0.3);
    const spots = [[230, 900, 1], [540, 760, 2], [850, 900, 3], [300, 1300, 4], [780, 1300, 5], [540, 1160, 6]];
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = BG.mint();
        const g = prog(t, ts - 0.1, tb + 0.4, E.outBack);
        const lift = prog(t, tb, t1 + 0.5, E.inOutSine) * 160;
        for (const [x, y, sd] of spots) {
          const yy = y - lift * (0.6 + 0.4 * hash(sd));
          if (t > tb) s += P(`M${x},${yy + 120 * (1 + g * 0.5)} q30,80 -10,160 q-30,80 10,160`, { fill: 'none', stroke: INK, 'stroke-width': 5 });
          s += cell(x + Math.sin(t * 2 + sd) * 8, yy, 120 * (1 + g * 0.55), { t, seed: sd, mood: g > 0.4 ? 'scared' : 'happy', shine: g, color: ['#F3B0D4', '#F6C1A7', '#C8B6F2', '#B7E2C8', '#F3B0D4', '#FFD1A1'][sd - 1] });
        }
        const k = fx.popIn(t, tb, 0.4);
        if (k > 0) s += text('LIKE BALLOONS!', { x: 540, y: 330, size: 120, sx: k, sy: k, rot: -3 });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S7 body can stretch
  {
    const t0 = cut('l8'), t1 = cut('l9'), tst = T.w('l8', 'stretch');
    cue(tst, 'stretch', 0.4, [0.7]); cue(tst + 0.5, 'boing', 0.35);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.blue();
        const str = prog(t, tst - 0.1, tst + 0.35, E.outElastic);
        const st = pose({ x: 540, y: 1660, s: 1.0, fat: 0.35 + 0.05 * Math.sin(t * 8), armK: 1 + str * 0.6, handL: [lerp(-150, -520, str), lerp(-352, -760, str)], handR: [lerp(150, 520, str), lerp(-352, -760, str)], bendL: 1, bendR: -1, handPoseL: 'spread', handPoseR: 'spread' }, 'grin', t, 4);
        s += rusty(st);
        s += text('STRETCHY', { x: 540, y: 330, size: 130, sx: fx.popIn(t, tst), sy: fx.popIn(t, tst), fill: '#7CFF9E', rot: -2 });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S8 brain locked in the skull
  {
    const t0 = cut('l9'), t1 = cut('l10'), tb = T.w('l9', 'brain'), tl = T.w('l9', 'locked'), tn = T.w('l9', 'nowhere');
    cue(tb, 'pop', 0.4); cue(tl, 'inflate', 0.45, [1.4]); cue(tn, 'impact', 0.5); cue(tn + 0.1, 'alarm', 0.25, [2]);
    shots.push({
      t0, t1, push: 0.05,
      shakes: [[tn, 0.5, 14]],
      draw(lt, t) {
        let s = BG.purple();
        const sw = prog(t, tl - 0.2, tn + 0.3, E.inOutQuad);
        s += brainSkull(540, 1100, 1.05, { swell: sw, t, mood: sw > 0.5 ? 'scared' : 'happy' });
        if (sw > 0.6) {
          const a = prog(t, tn - 0.3, tn) * (0.7 + 0.3 * Math.sin(t * 20));
          for (let i = 0; i < 8; i++) {
            const ang = (i / 8) * Math.PI * 2;
            s += O(a, fx.arrow([540 + Math.cos(ang) * 470, 1100 + Math.sin(ang) * 540], [540 + Math.cos(ang) * 380, 1100 + Math.sin(ang) * 450], 1, { color: '#FF5A5A', w: 16, head: 38 }));
          }
        }
        const k = fx.popIn(t, tn, 0.4);
        if (k > 0) s += text('NOWHERE TO GO!', { x: 540, y: 330, size: 115, sx: k, sy: k, rot: -3, fill: '#FF8A8A' });
        else s += text('BRAIN', { x: 540, y: 330, size: 130, sx: fx.popIn(t, tb), sy: fx.popIn(t, tb), fill: '#F49FB0' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S9 headache, confusion, seizures
  {
    const t0 = cut('l10'), t1 = cut('l13'), th = T.s('l10'), tc = T.s('l11'), tz = T.s('l12');
    cue(th, 'zap', 0.4, [0.4]); cue(th, 'thud', 0.4); cue(tc, 'boing', 0.35, [0.6]); cue(tc + 0.15, 'slide_down', 0.25, [0.4]); cue(tz, 'zap', 0.4, [0.8]); cue(tz, 'impact', 0.35);
    shots.push({
      t0, t1, push: 0.03,
      cam: camKeys([[th, { x: 540, y: 1000, z: 1.12 }], [tc - 0.05, { x: 540, y: 960, z: 1.0 }], [tz - 0.05, { x: 540, y: 1050, z: 1.18 }]]),
      shakes: [[tz, 0.9, 26]],
      draw(lt, t) {
        let s = BG.lilac();
        const phase = t < tc - 0.05 ? 0 : t < tz - 0.05 ? 1 : 2;
        const jit = phase === 2 ? noise(t * 50, 2) * 22 : 0;
        const st = pose({ x: 540 + jit, y: 1660, s: 1.0, skinTint: '#9ACD5A', skinTintAmt: 0.25 + phase * 0.08 }, phase === 0 ? 'pain' : phase === 1 ? 'dizzy' : 'scared', t, 5);
        if (phase === 0) { st.handL = [-120, -1000]; st.handR = [120, -1000]; st.bendL = 1; st.bendR = -1; }
        if (phase === 2) { st.rot = noise(t * 40, 5) * 8; st.handL = [-260, -800 + noise(t * 30, 1) * 80]; st.handR = [260, -800 + noise(t * 30, 2) * 80]; st.bendL = -1; st.bendR = 1; st.handPoseL = 'spread'; st.handPoseR = 'spread'; }
        s += rusty(st);
        const hx = 540, hy = 1660 - 830;
        if (phase === 0) for (const [dx, dy, rt] of [[-260, -120, -20], [250, -150, 20], [0, -300, 0]]) s += pr.boltIcon(hx + dx, hy + dy + Math.sin(t * 20 + dx) * 6, 0.55, rt);
        if (phase === 1) for (let i = 0; i < 4; i++) { const a = t * 3 + (i * Math.PI) / 2; s += qmark(hx + Math.cos(a) * 280, hy - 120 + Math.sin(a) * 90, 0.8, Math.sin(t * 4 + i) * 15); }
        if (phase === 2) s += fx.emphasis(t, hx + 220, hy, { side: 1, scale: 1.5 }) + fx.emphasis(t, hx - 220, hy, { side: -1, scale: 1.5 });
        const lab = ['HEADACHE', 'CONFUSION', 'SEIZURES'][phase];
        const k = fx.popIn(t, [th, tc, tz][phase], 0.3);
        s += text(lab, { x: 540, y: 330, size: 140, sx: k, sy: k, rot: [-3, 3, -2][phase], fill: ['#FF8A8A', '#FFE45C', '#FF6B6B'][phase] });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S10 water intoxication
  {
    const t0 = cut('l13'), t1 = cut('l14'), tw = T.w('l13', 'water'), ti = T.w('l13', 'intoxication');
    cue(tw, 'pop', 0.5); cue(ti, 'impact', 0.5); cue(ti + 0.05, 'alarm', 0.2, [1]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.pink();
        s += fx.warning(540, 1100, 2.6 * fx.popIn(t, t0 + 0.05, 0.45));
        const k1 = fx.popIn(t, tw, 0.35), k2 = fx.popIn(t, ti, 0.4);
        if (k1 > 0) s += text('WATER', { x: 540, y: 380, size: 170, sx: k1, sy: k1, fill: '#8FE3FF', rot: -3 });
        if (k2 > 0) s += text('INTOXICATION', { x: 540, y: 580, size: 120, sx: k2, sy: k2, fill: '#FF6B6B', rot: 2 });
        s += bottle(240, 1650, -20, 1.0, 0.7);
        s += bottle(850, 1660, 18, 1.0, 0.5);
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S11 drink when thirsty, not to win a bet
  {
    const t0 = cut('l14'), t1 = duration, tth = T.w('l14', 'thirsty'), tbet = T.w('l14', 'bet');
    cue(tth - 0.2, 'gulp', 0.4); cue(tth + 0.3, 'chime', 0.35); cue(tbet, 'buzzer', 0.35);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.blue();
        const st = pose({ x: 540, y: 1700, s: 0.95, handR: [150, -540], handPoseR: 'hold', bendR: -1 }, t > tth ? 'happy' : 'curious', t, 6);
        s += rusty(st);
        s += glass(540 + 150 * 0.95, 1700 - 600 * 0.95, 0.75, 0.6);
        // banner
        const k = fx.popIn(t, tbet - 0.35, 0.35);
        if (k > 0) {
          s += G(tr(540, 380, -3, k), pr.signBoard(0, 0, 900, 220, { fill: '#FFE45C' }), text('DRINKING CONTEST', { x: 0, y: 0, size: 80, fill: '#FF6B6B', sw: 10 }));
          s += fx.crossOut(t, tbet, 540, 380, 300, { w: 34 });
        }
        if (t > tth) s += fx.checkMark(t, tth, 870, 950, 150);
        return s;
      },
    });
  }

  const tl = timeline(shots, duration);
  return { duration, frame: tl.frame, cues };
};
