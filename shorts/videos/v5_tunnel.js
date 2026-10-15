// Video 5 — "What if you jumped into a tunnel through the Earth?"
'use strict';
const { clamp, lerp, E, prog, kf, rng, noise, hash, mixColor, n2, tr, G, O, P, C, EL, R, L, PL, PG, smoothPath } = require('../lib/core');
const { rusty, pose } = require('../lib/rusty');
const { BG, flat, space } = require('../lib/bg');
const { text, width } = require('../lib/text');
const fx = require('../lib/fx');
const pr = require('../lib/props');
const { timeline, camKeys } = require('../lib/scene');
const INK = '#2b2220', LW = 8;
const fit = (str, maxW, size) => Math.min(size, (size * maxW) / width(str, size));

// ---------------------------------------------------------------- local props
function earthSection(cx, cy, r, t, o = {}) {
  const { tunnel = true, glow = 1 } = o;
  let s = `<defs><radialGradient id="core${Math.round(cx)}"><stop offset="0" stop-color="#FFF6C2"/><stop offset="0.6" stop-color="#FFE27A"/><stop offset="1" stop-color="#FFC23A"/></radialGradient></defs>`;
  s += C(cx, cy, r + 40, { fill: '#7FC8FF', opacity: 0.25 });
  s += C(cx, cy, r, { fill: '#3B8FDB', stroke: INK, 'stroke-width': LW + 2 });
  // continents on the rim
  for (const [a, w] of [[-2.2, 0.5], [-0.9, 0.7], [0.5, 0.45], [1.7, 0.6], [2.8, 0.35]]) {
    s += P(`M${n2(cx + Math.cos(a) * r)},${n2(cy + Math.sin(a) * r)} A${r},${r} 0 0,1 ${n2(cx + Math.cos(a + w) * r)},${n2(cy + Math.sin(a + w) * r)}`, { fill: 'none', stroke: '#4FB35A', 'stroke-width': 26 });
  }
  s += C(cx, cy, r * 0.93, { fill: '#9A6A45', stroke: INK, 'stroke-width': 6 });
  s += C(cx, cy, r * 0.86, { fill: '#E8763A', stroke: INK, 'stroke-width': 6 });
  s += C(cx, cy, r * 0.55, { fill: '#F5A93A', stroke: INK, 'stroke-width': 6 });
  s += C(cx, cy, r * 0.28, { fill: `url(#core${Math.round(cx)})`, stroke: INK, 'stroke-width': 6 });
  // magma swirls
  let d = '';
  for (let i = 0; i < 8; i++) { const a = i * 0.8 + t * 0.2, rr = r * 0.7; d += `M${n2(cx + Math.cos(a) * rr)},${n2(cy + Math.sin(a) * rr)} q20,-20 40,0 q20,20 40,0 `; }
  s += P(d, { fill: 'none', stroke: '#C9551F', 'stroke-width': 7, 'stroke-linecap': 'round', opacity: 0.7 });
  if (tunnel) s += R(cx - 22, cy - r - 10, 44, 2 * r + 20, { fill: '#2A1A14', stroke: INK, 'stroke-width': 5 });
  return s;
}

function speedometer(x, y, s, frac, label) {
  let o = P('M-260,0 A260,260 0 0,1 260,0 Z', { fill: '#ffffff', stroke: INK, 'stroke-width': LW + 2 });
  const arc = (a0, a1, col) => P(`M${n2(-Math.cos(a0) * 220)},${n2(-Math.sin(a0) * 220)} A220,220 0 0,1 ${n2(-Math.cos(a1) * 220)},${n2(-Math.sin(a1) * 220)}`, { fill: 'none', stroke: col, 'stroke-width': 34 });
  o += arc(0.05, 1.1, '#3CC86B') + arc(1.1, 2.1, '#FFD23F') + arc(2.1, Math.PI - 0.05, '#FF5A4E');
  for (let i = 0; i <= 10; i++) { const a = (i / 10) * Math.PI; o += L(-Math.cos(a) * 190, -Math.sin(a) * 190, -Math.cos(a) * 160, -Math.sin(a) * 160, { stroke: INK, 'stroke-width': 6, 'stroke-linecap': 'round' }); }
  const a = clamp(frac) * Math.PI + noise(frac * 50, 2) * 0.03;
  o += L(0, 0, -Math.cos(a) * 200, -Math.sin(a) * 200, { stroke: INK, 'stroke-width': 18, 'stroke-linecap': 'round' }) + L(0, 0, -Math.cos(a) * 200, -Math.sin(a) * 200, { stroke: '#FF5A4E', 'stroke-width': 8, 'stroke-linecap': 'round' });
  o += C(0, 0, 26, { fill: INK });
  return G(tr(x, y, 0, s), o);
}

function shovel(x, y, rot, s = 1) {
  return G(tr(x, y, rot, s), L(0, -260, 0, 120, { stroke: INK, 'stroke-width': 26, 'stroke-linecap': 'round' }), L(0, -260, 0, 120, { stroke: '#B07A4A', 'stroke-width': 14, 'stroke-linecap': 'round' }),
    R(-40, -290, 80, 30, { rx: 12, fill: '#B07A4A', stroke: INK, 'stroke-width': 7 }),
    P('M-60,120 L60,120 L52,230 Q0,270 -52,230Z', { fill: '#AEB8C7', stroke: INK, 'stroke-width': LW, 'stroke-linejoin': 'round' }));
}

function sheep(x, y, s = 1, t = 0, look = 0) {
  let o = '';
  for (const lx of [-60, -20, 30, 70]) o += R(lx - 9, 40, 18, 80, { rx: 8, fill: '#3a2c2a' });
  const pts = [];
  for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; pts.push([Math.cos(a) * 130, Math.sin(a) * 85]); }
  for (const [px, py] of pts) o += C(px, py, 44, { fill: INK });
  for (const [px, py] of pts) o += C(px, py, 36, { fill: '#ffffff' });
  o += EL(0, 0, 130, 85, { fill: '#ffffff' });
  o += G(tr(150, -40, look * 10), EL(0, 0, 52, 62, { fill: '#3a2c2a', stroke: INK, 'stroke-width': 6 }), EL(-46, -30, 26, 12, { fill: '#3a2c2a', stroke: INK, 'stroke-width': 5 }), EL(46, -30, 26, 12, { fill: '#3a2c2a', stroke: INK, 'stroke-width': 5 }),
    EL(-16, -8, 13, 16, { fill: '#fff' }), EL(16, -8, 13, 16, { fill: '#fff' }), C(-16 + look * 6, -6, 6, { fill: INK }), C(16 + look * 6, -6, 6, { fill: INK }));
  return G(tr(x, y, 0, s), o);
}

function ground(y, o = {}) {
  const { grass = '#5DB35A', dirt = '#9A6A45', sand = false } = o;
  let s = R(-600, y, 2280, 2000, { fill: dirt, stroke: INK, 'stroke-width': LW });
  s += R(-600, y + 140, 2280, 2000, { fill: mixColor(dirt, '#5a3a25', 0.35) });
  s += R(-600, y + 330, 2280, 2000, { fill: mixColor(dirt, '#3a2418', 0.55) });
  s += R(-600, y - 10, 2280, 50, { fill: sand ? '#F2D58A' : grass, stroke: INK, 'stroke-width': LW });
  const r = rng(5);
  for (let i = 0; i < 24; i++) s += EL(r() * 1500 - 200, y + 80 + r() * 500, 16 + r() * 18, 10 + r() * 10, { fill: '#6b4a32', opacity: 0.6 });
  return s;
}

module.exports = function (T) {
  const cues = [];
  const cue = (t, sfx, gain = 0.5, args) => cues.push({ t: +t.toFixed(3), sfx, gain, ...(args ? { args } : {}) });
  const duration = T.duration + 0.3;
  const shots = [];
  const cut = id => T.s(id) - 0.08;
  const fallSt = (t, x, y, s, expr, extra = {}) => pose(Object.assign({ x, y, s, hair: 0.8, handL: [-230, -900 + Math.sin(t * 14) * 30], handR: [230, -900 + Math.cos(t * 14) * 30], bendL: -1, bendR: 1, handPoseL: 'spread', handPoseR: 'spread', footL: [-90, -40], footR: [90, -60] }, extra), expr, t, 3);

  // ------------------------------------------------------------- S1 dig & jump
  {
    const t1 = cut('l2'), tj = T.w('l1', 'jumped');
    for (let k = 0; 0.25 + k * 0.45 < tj - 0.1; k++) cue(0.25 + k * 0.45, 'dig', 0.45);
    cue(tj, 'jump', 0.5); cue(tj + 0.35, 'fall_whistle', 0.35, [1.2]);
    shots.push({
      t0: 0, t1, push: 0.05, punch: 0,
      draw(lt, t) {
        let s = BG.blue();
        const gy = 1500, hx = 700;
        const hole = kf(t, [[0, 0.5], [tj, 1]]);
        s += ground(gy);
        s += EL(hx, gy + 15, 150 * hole, 44 * hole, { fill: '#1d120d', stroke: INK, 'stroke-width': LW });
        const jumping = t > tj;
        let st;
        if (!jumping) {
          const ph = (t % 0.45) / 0.45;
          const dip = Math.sin(ph * Math.PI);
          st = pose({ x: 440, y: gy + 40, s: 0.85, lean: 6 + dip * 8, handL: [150, -560 + dip * 120], handR: [230, -420 + dip * 120], bendL: -1, bendR: -1, handPoseL: 'fist', handPoseR: 'fist' }, 'happy', t, 4);
          s += rusty(st);
          s += shovel(440 + 200 * 0.85, gy + 40 - (520 - dip * 120) * 0.85 + 60, 25 + dip * 10, 0.85);
          // flying dirt
          const r = rng(Math.floor(t / 0.45) + 3);
          for (let i = 0; i < 6; i++) {
            const k = ph;
            s += EL(hx - 80 + r() * 160 - k * 300 * (0.5 + r()), gy - 40 - Math.sin(k * Math.PI) * (160 + r() * 140), 18, 12, { fill: '#7a5236', stroke: INK, 'stroke-width': 5 });
          }
        } else {
          const k = clamp((t - tj) / 0.55);
          const x = lerp(440, hx, k), y = gy + 40 - Math.sin(k * Math.PI) * 300 + Math.max(0, (t - tj - 0.55)) * 2200;
          st = pose({ x, y, s: 0.85, rot: k * 180, handL: [-80, -1080], handR: [80, -1080], bendL: 1, bendR: -1, handPoseL: 'open', handPoseR: 'open' }, 'grin', t, 4);
          // clip Rusty to above-ground + the hole opening
          s += `<defs><clipPath id="hc"><rect x="-600" y="-600" width="2280" height="${gy + 615}"/><ellipse cx="${hx}" cy="${gy + 15}" rx="${150 * hole}" ry="${44 * hole}"/></clipPath></defs>`;
          s += `<g clip-path="url(#hc)">${rusty(st)}</g>`;
          s += shovel(330, gy - 120, -60, 0.85);
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S2 cross-section, no air, faster and faster
  {
    const t0 = cut('l2'), t1 = cut('l3'), ta = T.w('l2', 'air'), tf = T.w('l2', 'faster');
    cue(t0 + 0.1, 'whoosh', 0.35, [1.4]); cue(ta, 'pop', 0.4); cue(tf, 'riser', 0.4, [1.0]);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = space({ t, id: 'a' });
        const cx = 540, cy = 1120, r = 600;
        s += earthSection(cx, cy, r, t);
        const p = prog(t, t0, t1 + 0.4, E.inQuad);
        const y = lerp(cy - r + 40, cy - 60, p);
        s += C(cx, y + 150, 90, { fill: '#FFE45C', opacity: 0.3 }) + rusty(pose({ x: cx, y: y + 20, s: 0.21, rot: 180, hair: 1 }, 'scared', t, 5));
        if (t > tf) s += fx.arrow([cx + 110, y - 60], [cx + 110, y + 60 + 120 * prog(t, tf, tf + 0.5)], 1, { color: '#FFE45C', w: 16, head: 34 });
        if (t > ta) {
          const k = fx.popIn(t, ta, 0.35);
          s += text('NO AIR', { x: 540, y: 330, size: 140, sx: k, sy: k, fill: '#9FDBFF', rot: -3 });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S3 28,000 km/h
  {
    const t0 = cut('l3'), t1 = cut('l4'), tc = T.w('l3', 'center'), tn = T.w('l3', 'twenty'), th = T.w('l3', 'hour');
    cue(t0 + 0.05, 'whoosh', 0.5, [1.5]); cue(tn, 'riser', 0.35, [th - tn + 0.2]); cue(th + 0.2, 'impact', 0.45); cue(th + 0.2, 'ding', 0.35);
    shots.push({
      t0, t1, push: 0.04,
      shakes: [[t0, t1 - t0, 6]],
      draw(lt, t) {
        let s = flat('#3A2418');
        // tunnel walls rushing past
        s += R(-600, -600, 820, 3120, { fill: '#7a4a2a' }) + R(860, -600, 820, 3120, { fill: '#7a4a2a' });
        s += L(220, -600, 220, 2600, { stroke: INK, 'stroke-width': 10 }) + L(860, -600, 860, 2600, { stroke: INK, 'stroke-width': 10 });
        const r = rng(2);
        for (let i = 0; i < 20; i++) { const x = r() < 0.5 ? r() * 200 : 880 + r() * 200; const yy = ((r() * 2400 - t * 3400) % 2400 + 2400) % 2400 - 300; s += EL(x, yy, 30, 60, { fill: '#5e3820' }); }
        s += fx.speedLines(t, { x0: 240, x1: 840, dir: 'v', speed: -3200, n: 12, color: '#ffffff', opacity: 0.4, w: 6, len: 300 });
        s += rusty(fallSt(t, 540, 1720, 0.8, 'scared', { rot: 180 + Math.sin(t * 3) * 5, y: 380 }));
        const spd = Math.round(kf(t, [[tn - 0.2, 6000], [th + 0.2, 28000, E.outCubic]]) / 100) * 100;
        s += speedometer(540, 1600, 0.9, spd / 30000);
        s += text(spd.toLocaleString('en-US') + ' KM/H', { x: 540, y: 1720, size: 92, fill: spd >= 28000 ? '#FFE45C' : '#ffffff' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S4 5,000 degrees
  {
    const t0 = cut('l4'), t1 = cut('l5'), tf = T.w('l4', 'five'), ts = T.w('l4', 'sun'), tal = T.w('l4', 'almost');
    cue(t0 + 0.1, 'sizzle', 0.4, [1.6]); cue(tf, 'riser', 0.3, [0.7]); cue(tf + 0.7, 'pop', 0.5); cue(tal, 'pop', 0.45); cue(ts, 'boing', 0.35);
    shots.push({
      t0, t1, push: 0.05,
      cam: camKeys([[tal - 0.05, { x: 540, y: 1250, z: 1.18 }]]),
      draw(lt, t) {
        const heat = prog(t, t0, tf + 0.5);
        let s = flat(mixColor('#5a2a14', '#A8320F', heat));
        s += R(-600, -600, 820, 3120, { fill: mixColor('#7a4a2a', '#FF7A1A', heat) }) + R(860, -600, 820, 3120, { fill: mixColor('#7a4a2a', '#FF7A1A', heat) });
        s += L(220, -600, 220, 2600, { stroke: INK, 'stroke-width': 10 }) + L(860, -600, 860, 2600, { stroke: INK, 'stroke-width': 10 });
        const r = rng(4);
        for (let i = 0; i < 16; i++) { const x = r() < 0.5 ? r() * 200 : 880 + r() * 200; const yy = ((r() * 2400 - t * 2400) % 2400 + 2400) % 2400 - 300; s += C(x, yy, 26 + r() * 30, { fill: '#FFD23F', opacity: 0.6 * heat }); }
        s += fx.speedLines(t, { x0: 240, x1: 840, dir: 'v', speed: -2600, n: 10, color: '#FFE27A', opacity: 0.35, w: 6, len: 300 });
        const st = fallSt(t, 470, 820, 0.75, 'scared', { rot: 180, skinTint: '#FF5A3A', skinTintAmt: 0.3 * heat, sweat: 1 });
        st.y = 820 - 1000 * 0.75 + 1000 * 0.75; // feet up: rotated 180
        s += rusty(Object.assign(st, { y: 300 }));
        s += pr.thermometer(820, 1300, kf(t, [[t0, 0.4], [tf + 0.7, 1.0, E.inQuad]]), { s: 0.62, h: 900 });
        if (t > tf + 0.7) s += fx.burstLines(t, tf + 0.7, 820, 1300 - 900 * 0.62, { n: 10, r0: 50, r1: 150, dur: 0.4, w: 8 });
        const val = Math.round(kf(t, [[tf - 0.1, 0], [tf + 0.7, 5000, E.outCubic]]) / 10) * 10;
        if (t > tf - 0.1) s += text(val.toLocaleString('en-US') + '°C', { x: 470, y: 1520, size: 150, fill: '#FFE45C', sx: fx.popIn(t, tf - 0.1), sy: fx.popIn(t, tf - 0.1) });
        if (t > tal) {
          const k = fx.popIn(t, tal, 0.4);
          s += pr.sun(330, 1700, 0.55 * k, { t, mood: t > ts ? 'shocked' : 'happy', look: [1, 0] });
          s += text('≈ SUN', { x: 700, y: 1710, size: 100, sx: k, sy: k, fill: '#FFD23F' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S5 center: zero gravity
  {
    const t0 = cut('l5'), t1 = cut('l6'), tz = T.w('l5', 'zero');
    cue(t0 + 0.05, 'sparkle', 0.35); cue(tz, 'boing', 0.4, [0.6]); cue(tz + 0.05, 'pop', 0.4);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = `<defs><radialGradient id="cz"><stop offset="0" stop-color="#FFF9D6"/><stop offset="0.6" stop-color="#FFE27A"/><stop offset="1" stop-color="#FFB627"/></radialGradient></defs>` + R(-600, -600, 2280, 3120, { fill: 'url(#cz)' });
        const r = rng(7);
        for (let i = 0; i < 14; i++) s += C(r() * 1080, (r() * 1920 + t * 40) % 1920, 10 + r() * 20, { fill: '#ffffff', opacity: 0.5 });
        const st = pose({ x: 540, y: 1500 + Math.sin(t * 1.8) * 30, s: 0.95, rot: Math.sin(t) * 12, handL: [-250, -620], handR: [250, -650], bendL: -1, bendR: 1, footL: [-110, -40], footR: [110, -60], skinTint: '#FF8A5A', skinTintAmt: 0.15 }, 'happy', t, 6);
        st.eyes = 'happy';
        s += rusty(st);
        const k = fx.popIn(t, tz, 0.4);
        if (k > 0) s += text('0 G', { x: 540, y: 380, size: 260, sx: k, sy: k, rot: -4, fill: '#7CFF9E' });
        else s += text('CENTER', { x: 540, y: 380, size: 140, fill: '#FF8A3C' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S6 equal pull from every side
  {
    const t0 = cut('l6'), t1 = cut('l7'), te = T.w('l6', 'equally'), tev = T.w('l6', 'every');
    cue(te, 'whoosh', 0.35, [0.5]); for (let i = 0; i < 8; i++) cue(te + i * 0.05, 'bubble', 0.15, [1 + i * 0.08]);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = space({ t, id: 'b' });
        const cx = 540, cy = 1050, r = 600;
        s += earthSection(cx, cy, r, t);
        s += C(cx, cy, 100, { fill: '#FFF6C2', opacity: 0.45 }) + rusty(pose({ x: cx, y: cy + 110, s: 0.22, rot: Math.sin(t) * 20, handL: [-240, -640], handR: [240, -640], bendL: -1, bendR: 1 }, 'happy', t, 7));
        const p = prog(t, te - 0.1, te + 0.35, E.outBack);
        for (let i = 0; i < 8; i++) {
          const a = (i / 8) * Math.PI * 2 + Math.PI / 8;
          s += fx.arrow([cx + Math.cos(a) * 130, cy + Math.sin(a) * 130], [cx + Math.cos(a) * (130 + 300 * p), cy + Math.sin(a) * (130 + 300 * p)], p > 0 ? 1 : 0, { color: '#FFE45C', w: 18, head: 40 });
        }
        if (t > tev) s += text('EQUAL PULL', { x: 540, y: 300, size: 130, sx: fx.popIn(t, tev), sy: fx.popIn(t, tev), fill: '#FFE45C', rot: -2 });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S7 slowing down
  {
    const t0 = cut('l7'), t1 = cut('l8'), ts = T.w('l7', 'slowing');
    cue(ts, 'slide_down', 0.35, [0.9]);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = space({ t, id: 'c' });
        const cx = 540, cy = 1050, r = 600;
        s += earthSection(cx, cy, r, t);
        const p = prog(t, t0, t1 + 0.4, E.outQuad);
        const y = lerp(cy - 60, cy + r - 280, p);
        s += C(cx, y + 110, 90, { fill: '#FFE45C', opacity: 0.3 }) + rusty(pose({ x: cx, y: y - 60, s: 0.21, rot: 180, hair: 0.5 }, 'curious', t, 8));
        const sl = 1 - p;
        s += fx.arrow([cx + 110, y - 40], [cx + 110, y - 40 + 40 + 160 * sl], 1, { color: '#7FD8FF', w: 16, head: 34 });
        s += speedometer(540, 1880, 0.55, sl * 0.95);
        s += text('SLOWING DOWN', { x: 540, y: 300, size: fit('SLOWING DOWN', 960, 120), sx: fx.popIn(t, ts), sy: fx.popIn(t, ts), fill: '#9FDBFF' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S8 pops out on the other side after 42 minutes
  {
    const t0 = cut('l8'), t1 = cut('l9'), tf = T.w('l8', 'forty'), tp = T.w('l8', 'pops'), to = T.w('l8', 'other');
    cue(tf, 'pop', 0.45); cue(tf + 0.1, 'clock', 0.35, [tp - tf - 0.1, 10]); cue(tp, 'jump', 0.5); cue(tp + 0.05, 'pop', 0.6, [0.7]); cue(to, 'boing', 0.3, [1.2]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = `<defs><linearGradient id="sky2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFB8A0"/><stop offset="1" stop-color="#FFE3B5"/></linearGradient></defs>` + R(-600, -600, 2280, 3120, { fill: 'url(#sky2)' });
        s += C(820, 380, 110, { fill: '#FFE27A', stroke: INK, 'stroke-width': 8 });
        const gy = 1500, hx = 540;
        s += ground(gy, { grass: '#7CC15A' });
        s += EL(hx, gy + 15, 150, 44, { fill: '#1d120d', stroke: INK, 'stroke-width': LW });
        s += sheep(880, 1450, 0.8, t, t > tp ? -1 : 0);
        if (t > tp) {
          const k = clamp((t - tp) / 0.9);
          const y = gy + 900 - Math.sin(Math.min(1, k * 1.6) * Math.PI / 2) * (900 + 330) + Math.max(0, k - 0.62) * 0;
          const st = pose({ x: hx, y: Math.min(gy + 900, y), s: 0.8, handL: [-240, -980], handR: [240, -980], bendL: -1, bendR: 1, handPoseL: 'spread', handPoseR: 'spread', hair: 0.6 }, 'grin', t, 9);
          s += `<defs><clipPath id="hc2"><rect x="-600" y="-600" width="2280" height="${gy + 615}"/><ellipse cx="${hx}" cy="${gy + 15}" rx="150" ry="44"/></clipPath></defs>`;
          s += `<g clip-path="url(#hc2)">${rusty(st)}</g>`;
          s += fx.burstLines(t, tp, hx, gy, { n: 10, r0: 160, r1: 300, dur: 0.4, w: 9 });
        }
        if (t > tf) {
          const k = fx.popIn(t, tf, 0.4);
          s += pr.stopwatch(220, 420, 0.45 * k, { frac: kf(t, [[tf, 0], [tp, 42 / 60, E.inOutSine]]) });
          s += text('42 MIN', { x: 220, y: 600, size: 90, sx: k, sy: k, fill: '#FF6B4A' });
        }
        if (t > to) s += text('OTHER SIDE!', { x: 540, y: 1720, size: 120, sx: fx.popIn(t, to), sy: fx.popIn(t, to), rot: -3 });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S9 swings back and forth forever
  {
    const t0 = cut('l9'), t1 = duration, tfb = T.w('l9', 'falls'), tsw = T.w('l9', 'swings'), tfe = T.w('l9', 'forever');
    cue(tfb, 'slide_down', 0.35, [0.7]); cue(tsw, 'whoosh', 0.35, [0.6]); cue(tsw + 0.9, 'whoosh', 0.35, [0.6]); cue(tfe, 'chime', 0.4);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = space({ t, id: 'd' });
        const cx = 540, cy = 1080, r = 600;
        s += earthSection(cx, cy, r, t);
        // simple harmonic motion through the tunnel
        const w = 3.4;
        const y = cy - Math.cos((t - t0) * w) * (r - 70);
        for (let i = 1; i <= 5; i++) {
          const yy = cy - Math.cos((t - t0 - i * 0.03) * w) * (r - 70);
          s += C(cx, yy, 24 - i * 3, { fill: '#FFE45C', opacity: 0.5 - i * 0.08 });
        }
        const up = Math.sin((t - t0) * w) > 0;
        s += C(cx, y, 90, { fill: '#FFE45C', opacity: 0.3 }) + rusty(pose({ x: cx, y: up ? y - 100 : y + 100, s: 0.2, rot: up ? 180 : 0, hair: 0.7 }, 'grin', t, 10));
        // arrows on both sides of the tunnel
        s += fx.arrow([cx - 180, cy - 300], [cx - 180, cy + 300], 1, { color: '#7FD8FF', w: 14, head: 32 }) + fx.arrow([cx + 180, cy + 300], [cx + 180, cy - 300], 1, { color: '#7FD8FF', w: 14, head: 32 });
        if (t > tfe) s += text('FOREVER!', { x: 540, y: 300, size: 170, sx: fx.popIn(t, tfe), sy: fx.popIn(t, tfe), rot: -3, fill: '#FFE45C' });
        else if (t > tsw) s += text('BACK & FORTH', { x: 540, y: 300, size: fit('BACK & FORTH', 960, 130), sx: fx.popIn(t, tsw), sy: fx.popIn(t, tsw), fill: '#ffffff' });
        return s;
      },
    });
  }

  const tl = timeline(shots, duration);
  return { duration, frame: tl.frame, cues };
};
