// Video 1 — "What if lightning hit you?"
'use strict';
const { clamp, lerp, E, prog, kf, rng, noise, hash, mixColor, n2, tr, G, O, P, C, EL, R, L, PL, PG } = require('../lib/core');
const { rusty, pose } = require('../lib/rusty');
const { BG, space } = require('../lib/bg');
const { text, label, width } = require('../lib/text');
const fx = require('../lib/fx');
const pr = require('../lib/props');
const { timeline } = require('../lib/scene');
const INK = '#2b2220';

module.exports = function (T) {
  const cues = [];
  const cue = (t, sfx, gain = 0.5, args) => cues.push({ t: +t.toFixed(3), sfx, gain, ...(args ? { args } : {}) });
  const duration = T.duration + 0.6;
  const shots = [];
  const cut = id => T.s(id) - 0.08;

  // contour of Rusty's default pose, for the "current over the skin" effect (body coords)
  const contourL = [[0, -1080], [-90, -1060], [-160, -1000], [-175, -900], [-165, -800], [-120, -700], [-170, -610], [-200, -480], [-185, -350], [-130, -330], [-120, -200], [-115, -60], [-100, 0]];
  const contourR = contourL.map(([x, y]) => [-x, y]);
  const along = (pts, u) => {
    const seg = [];
    let tot = 0;
    for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); tot += d; }
    let k = clamp(u) * tot;
    for (let i = 0; i < seg.length; i++) {
      if (k <= seg[i]) { const f = k / seg[i]; return [lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)]; }
      k -= seg[i];
    }
    return pts[pts.length - 1];
  };
  // small random arcs around a body
  const arcs = (t, cx, cy, rx, ry, n, seed, w = 7) => {
    let s = '';
    const fr = Math.floor(t * 15);
    for (let i = 0; i < n; i++) {
      const r = rng(seed * 100 + i * 13 + fr * 7);
      if (r() < 0.35) continue;
      const a = r() * Math.PI * 2;
      const p0 = [cx + Math.cos(a) * rx * 0.75, cy + Math.sin(a) * ry * 0.75];
      const p1 = [cx + Math.cos(a + (r() - 0.5)) * rx * 1.15, cy + Math.sin(a + (r() - 0.5)) * ry * 1.15];
      s += pr.bolt(p0, p1, { seed: fr * 31 + i, width: w, branches: 1, glow: '#7FD8FF' });
    }
    return s;
  };

  // ---------------------------------------------------------------- S1 storm strike
  {
    const ts = T.w('l1', 'struck');
    const tEnd = cut('l2');
    cue(0, 'thunder', 0.25);
    cue(ts - 0.04, 'zap', 0.7);
    cue(ts, 'thunder', 0.95);
    cue(ts + 0.35, 'crackle', 0.5);
    cue(ts + 0.6, 'sizzle', 0.35);
    shots.push({
      t0: 0, t1: tEnd, push: 0.07, punch: 0,
      shakes: [[ts, 0.7, 34]],
      flashes: [[ts, 0.32, '#ffffff', 0.95]],
      draw(lt, t) {
        const hit = t >= ts;
        const strobe = hit && t < ts + 0.55 ? Math.floor((t - ts) * 16) % 2 === 0 : false;
        let s = pr.storm(t, { flashA: hit && t < ts + 0.6 ? (strobe ? 0.7 : 0.25) * (1 - (t - ts) / 0.6) : 0 });
        s += pr.hill(1700);
        const x = 540, y = 1660, sc = 1;
        const grip = [x + 150 * sc, y - 730 * sc];
        s += pr.umbrella(grip[0], grip[1], { len: 520, color: hit ? '#4a3a3a' : '#E8443A', color2: hit ? '#5a5050' : '#FFD23F' });
        const st = pose({
          x, y, s: sc,
          handR: [150, -730], handPoseR: 'fist', handL: [-150, -352],
          hair: hit ? Math.min(1, (t - ts) * 4) : 0,
          xray: strobe,
          skinTint: hit ? '#5a4a44' : null, skinTintAmt: hit ? 0.35 : 0,
          tint: hit ? '#3a3030' : null, tintAmt: hit ? 0.12 : 0,
        }, hit ? (t < ts + 0.6 ? 'shocked' : 'dizzy') : 'happy', t, 3);
        if (!hit) {
          st.look = [0.3, -0.6]; st.mouth = 'blow';
          for (let i = 0; i < 3; i++) {
            const p = ((t * 0.9 + i / 3) % 1);
            const nx = x - 70 - p * 160 + Math.sin(p * 8 + i) * 20, ny = y - 760 - p * 260;
            s += O(Math.sin(p * Math.PI), G(tr(nx, ny, -10, 1.1), P('M0,0 L0,-60 L34,-70 L34,-12', { fill: 'none', stroke: INK, 'stroke-width': 8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }), EL(-10, 0, 14, 10, { fill: INK }), EL(24, -10, 14, 10, { fill: INK })));
          }
        }
        if (hit) st.handL = [-260, -620];
        s += rusty(st);
        if (hit) {
          s += fx.puffs(t, ts + 0.15, x, y - 1000, { n: 7, spread: 140, rise: 300, size: 46, dur: 1.4, color: '#6d6a70', seed: 4 });
          s += arcs(t, x, y - 600, 260, 520, 4, 2);
        }
        // the bolt itself
        const tip = pr.umbrellaTip(grip[0], grip[1], 520);
        if (t >= ts - 0.06 && t < ts + 0.55) {
          const p = prog(t, ts - 0.06, ts, E.outQuad);
          const fl = Math.floor(t * 30) % 3;
          s += pr.bolt([tip[0] + 80, -200], tip, { seed: 40 + fl, p, width: 26, branches: 5, opacity: fl === 2 ? 0.6 : 1 });
        }
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S2 300 million volts
  {
    const t0 = cut('l2'), t1 = cut('l3');
    const tNum = T.w('l2', 'three'), tV = T.w('l2', 'volts');
    cue(t0 + 0.02, 'zap', 0.55); cue(t0 + 0.7, 'zap', 0.35); cue(tNum, 'pop', 0.6); cue(tV, 'impact', 0.6); cue(tV, 'zap', 0.5);
    shots.push({
      t0, t1, push: 0.06,
      shakes: [[tV, 0.4, 18]],
      flashes: [[tV, 0.15, '#BDEBFF', 0.6]],
      draw(lt, t) {
        let s = BG.purple();
        const jx = noise(t * 30, 3) * 10, jy = noise(t * 30, 5) * 6;
        const st = pose({ x: 540 + jx, y: 2240 + jy, s: 1.45, hair: 1, handL: [-280, -720], handR: [280, -720], handPoseL: 'spread', handPoseR: 'spread', bendL: -1, bendR: 1,
          xray: t > tV && t < tV + 0.3 && Math.floor((t - tV) * 20) % 2 === 0 }, 'pain', t, 5, 0.4);
        s += rusty(st);
        s += arcs(t, 540, 2240 - 800 * 1.45, 380, 420, 7, 9, 9);
        const k1 = fx.popIn(t, tNum, 0.4), k2 = fx.popIn(t, tV, 0.4);
        if (k1 > 0) s += text('300,000,000', { x: 540, y: 260, size: 132, sx: k1, sy: k1, rot: -3 + noise(t * 2, 1) * 1.5 });
        if (k2 > 0) s += text('VOLTS!', { x: 540, y: 425, size: 150, sx: k2, sy: k2, rot: 2, fill: '#7FE3FF' });
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S3 thermometer 30,000 degrees
  {
    const t0 = cut('l3'), t1 = cut('l4');
    const ta = T.w('l3', 'heats'), tb = T.w('l3', 'thirty'), tc = T.w('l3', 'degrees');
    cue(ta, 'riser', 0.45, [tc - ta + 0.1]); cue(tc + 0.05, 'pop', 0.7); cue(tc + 0.05, 'ding', 0.4); cue(t0 + 0.1, 'sizzle', 0.25);
    shots.push({
      t0, t1, push: 0.05,
      shakes: [[tc + 0.05, 0.3, 14]],
      draw(lt, t) {
        let s = BG.warm();
        // heat shimmer
        let d = '';
        for (let i = 0; i < 5; i++) {
          const yy = 900 - ((t * 160 + i * 140) % 700);
          d += `M${200 + i * 40},${yy} q20,-30 0,-60 q-20,-30 0,-60`;
        }
        s += P(d, { fill: 'none', stroke: '#E58A3A', 'stroke-width': 8, 'stroke-linecap': 'round', opacity: 0.6 });
        const lev = kf(t, [[t0, 0.1], [ta, 0.15], [tc, 1.0, E.inQuad]]);
        const pop = t > tc + 0.05;
        s += pr.thermometer(790, 1560, lev, { h: 1000, s: 0.95 });
        if (pop) {
          s += fx.burstLines(t, tc + 0.05, 790, 1560 - 960, { n: 10, r0: 70, r1: 220, dur: 0.45, w: 10 });
          s += fx.sparkles(t, tc + 0.05, 790, 1560 - 980, { n: 8, radius: 190, size: 40, seed: 3 });
        }
        const st = pose({ x: 330, y: 1720, s: 0.9, hair: 0.8, handL: [-120, -760], handR: [120, -760], handPoseL: 'open', handPoseR: 'open', bendL: -1, bendR: 1, sweat: 1 }, 'scared', t, 7);
        st.look = [0.7, -0.5];
        s += rusty(st);
        const val = Math.round(kf(t, [[tb - 0.2, 0], [tc + 0.05, 30000, E.outCubic]]) / 10) * 10;
        const k = fx.popIn(t, tb - 0.2, 0.35);
        if (k > 0) {
          const str = val.toLocaleString('en-US') + '°C';
          const kk = k * (pop ? 1 + 0.15 * (1 - prog(t, tc + 0.05, tc + 0.4, E.outCubic)) : 1);
          s += text(str, { x: 540, y: 330, size: 150, sx: kk, sy: kk, fill: pop ? '#FFF27A' : '#FFFFFF', rot: -2 });
        }
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S4 five times hotter than the sun
  {
    const t0 = cut('l4'), t1 = cut('l5');
    const tf = T.w('l4', 'five'), ts = T.w('l4', 'sun');
    cue(tf, 'pop', 0.7); cue(tf + 0.08, 'boing', 0.35, [1.3]); cue(ts, 'slide_down', 0.35);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = space({ t, top: '#151B4D', bottom: '#2B1D63' });
        const mood = t > ts ? 'jealous' : t > tf ? 'shocked' : 'happy';
        const sb = 1 + 0.03 * Math.sin(t * 5);
        const g = 0.5 + 0.5 * Math.sin(t * 20);
        s += '<defs><radialGradient id="glw"><stop offset="0" stop-color="#ffffff" stop-opacity="0.9"/><stop offset="0.35" stop-color="#9FDBFF" stop-opacity="0.45"/><stop offset="1" stop-color="#9FDBFF" stop-opacity="0"/></radialGradient>' +
          '<radialGradient id="glo"><stop offset="0" stop-color="#FFE27A" stop-opacity="0.7"/><stop offset="1" stop-color="#FF9A3C" stop-opacity="0"/></radialGradient></defs>';
        s += C(285, 760, 330, { fill: 'url(#glo)' });
        s += pr.sun(285, 760, 0.95 * sb, { t, mood, look: t > tf ? [1, 0] : [0, 0], sweat: t > ts ? 1 : 0 });
        s += text('SUN', { x: 285, y: 1090, size: 84, fill: '#FFD23F' });
        s += C(805, 760, 300 + 30 * g, { fill: 'url(#glw)' });
        s += pr.boltIcon(805 + noise(t * 20, 2) * 5, 760, 2.0, 8);
        s += text('LIGHTNING', { x: 805, y: 1090, size: 76, fill: '#9FDBFF' });
        const k = fx.popIn(t, tf, 0.45);
        if (k > 0) {
          s += text('5x', { x: 540, y: 1430, size: 300, sx: k, sy: k, rot: -6, fill: '#FF6B4A' });
          s += text('HOTTER', { x: 540, y: 1650, size: 130, sx: k, sy: k, rot: -2, fill: '#FFE45C' });
        }
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S5 current slides over skin
  {
    const t0 = cut('l5'), t1 = cut('l7');
    const tc = T.w('l5', 'current'), tn = T.w('l5', "doesn't"), tsl = T.w('l6', 'slides');
    cue(tc - 0.1, 'whoosh', 0.45); cue(tn, 'buzzer', 0.35); cue(tsl, 'zap', 0.45, [1.4]); cue(tsl + 0.2, 'crackle', 0.4, [1.2]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.lilac();
        const x = 540, y = 1700, sc = 1.05;
        const flowing = t > tsl;
        if (flowing) s += R(-200, -200, 1480, 2320, { fill: '#1b1440', opacity: n2(0.55 * prog(t, tsl, tsl + 0.2)) });
        const st = pose({ x, y, s: sc, hair: 0.45 }, flowing ? 'shocked' : t > tn ? 'smug' : 'curious', t, 9);
        st.look = flowing ? [0, 0.6] : [0.5, -0.5];
        s += rusty(st);
        // arrow trying to go inside
        const pa = prog(t, tc - 0.15, tc + 0.25, E.outCubic);
        if (pa > 0 && !flowing) {
          const bounce = t > tn ? E.outBack(prog(t, tn, tn + 0.3)) * 60 : 0;
          s += fx.arrow([980, 520], [lerp(980, 640 + bounce, pa), lerp(520, 1060 - bounce * 0.6, pa)], 1, { color: '#FFE04A', curve: 0.18 });
          s += fx.crossOut(t, tn, 640, 1080, 190);
        }
        if (flowing) {
          const a = prog(t, tsl, tsl + 0.25);
          // glowing skin outline
          const toW = p => [x + p[0] * sc, y + p[1] * sc];
          for (const cont of [contourL, contourR]) {
            const pts = cont.map(toW);
            s += PL(pts, { fill: 'none', stroke: '#4FC3FF', 'stroke-width': 60, opacity: n2(a * (0.18 + 0.1 * Math.sin(t * 30))), 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
            s += PL(pts, { fill: 'none', stroke: '#7FD8FF', 'stroke-width': 26, opacity: n2(a * (0.45 + 0.2 * Math.sin(t * 37))), 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
            s += PL(pts, { fill: 'none', stroke: '#F2FCFF', 'stroke-width': 9, opacity: n2(a), 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
            const fr = Math.floor(t * 15);
            for (let i = 0; i < 4; i++) {
              const u = hash(fr * 3 + i + (cont === contourL ? 0 : 50));
              const p0 = toW(along(cont, u)), p1 = toW(along(cont, Math.min(1, u + 0.12)));
              s += pr.bolt(p0, [p1[0] + (hash(fr + i) - 0.5) * 80, p1[1]], { seed: fr * 9 + i, width: 8, branches: 1, glow: '#7FD8FF' });
            }
            for (let i = 0; i < 12; i++) {
              const u = ((t - tsl) * 0.9 + i / 12) % 1;
              const p = toW(along(cont, u));
              s += fx.sparkle(p[0], p[1], 26 + 8 * Math.sin(t * 40 + i), '#E6F8FF', t * 300 + i * 40);
            }
          }
        }
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S6 steam blasts shoes off
  {
    const t0 = cut('l7'), t1 = cut('l8');
    const tst = T.w('l7', 'steam'), tb = T.w('l7', 'blasts');
    cue(tst, 'steam', 0.55, [1.3]); cue(tb, 'pop', 0.8, [0.7]); cue(tb + 0.03, 'pop', 0.7, [0.8]); cue(tb + 0.05, 'whoosh', 0.5); cue(tb + 0.2, 'slide_up', 0.35);
    shots.push({
      t0, t1, push: 0.05,
      shakes: [[tb, 0.35, 16]],
      draw(lt, t) {
        let s = BG.blue();
        const x = 540, y = 1650, sc = 1.0;
        const off = t > tb;
        const jump = off ? Math.sin(clamp((t - tb) / 0.5) * Math.PI) * 90 : 0;
        const [sqx, sqy] = fx.squash(t, tb + 0.5, 0.12);
        const st = pose({ x, y: y - jump, s: sc, sx: sqx, sy: sqy, hair: 0.5, socks: off, sweat: t < tst ? 1 : 0 }, off ? 'shocked' : t > tst ? 'worried' : 'puff', t, 11);
        if (off) { st.look = [0, 1]; st.handL = [-230, -560]; st.handR = [230, -560]; st.handPoseL = 'spread'; st.handPoseR = 'spread'; st.bendL = -1; st.bendR = 1; }
        // sweat drops on body before steam
        if (t < tst) {
          const r = rng(5);
          for (let i = 0; i < 9; i++) {
            const px = x + (r() - 0.5) * 300, py = y - 300 - r() * 600 + ((t * 80 + i * 50) % 60);
            s += '';
            st._drops = (st._drops || '') + G(tr(px, py, 0, 0.8), P('M0,-28 C10,-10 18,0 18,10 C18,22 -18,22 -18,10 C-18,0 -10,-10 0,-28Z', { fill: '#8FD3FF', stroke: INK, 'stroke-width': 5 }));
          }
        }
        s += rusty(st) + (st._drops || '');
        if (t > tst) s += fx.puffs(t, tst, x, y - 420, { n: 22, spread: 420, rise: 700, size: 95, dur: 1.9, seed: 8, opacity: 0.85, stroke: '#C9D9F0' });
        if (off) {
          const k = t - tb;
          for (const [side, vx, rot] of [[-1, -620, -900], [1, 700, 1000]]) {
            const sx = x + side * 66 + vx * k, sy = y - 18 - 2400 * k + 2600 * k * k;
            if (sy < 2300 && sx > -400 && sx < 1500) s += pr.shoe(sx, sy, rot * k, 1.1, side);
            s += fx.puffs(t, tb, x + side * 66, y, { n: 4, spread: 60, rise: 80, size: 30, dur: 0.6, seed: 12 + side });
          }
          s += fx.burstLines(t, tb, x, y - 20, { n: 10, r0: 120, r1: 260, dur: 0.4, w: 9 });
        }
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S7 Lichtenberg figures
  {
    const t0 = cut('l8'), t1 = cut('l10');
    const tg = T.w('l8', 'red'), tge = T.e('l8'), tl = T.w('l9', 'lichtenberg');
    cue(tg, 'sizzle', 0.45, [tge - tg + 0.3]); cue(tl, 'sparkle', 0.5); cue(tl, 'pop', 0.5);
    // fractal in arm-local coords: u along arm (0 = wrist), v across
    const A = [-160, 2160], B = [700, 760], AW = 250;
    const alen = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const ang = Math.atan2(A[1] - B[1], A[0] - B[0]); // from wrist toward shoulder
    const segs = [];
    const r = rng(21);
    const grow = (u, v, a, len, depth, d0) => {
      if (depth > 7 || len < 14) return;
      let u2 = u + Math.cos(a) * len, v2 = v + Math.sin(a) * len;
      if (Math.abs(v2) > AW / 2 - 18) { v2 = Math.sign(v2) * (AW / 2 - 18); }
      const dist = d0 + len;
      segs.push({ u, v, u2, v2, depth, d0, d1: dist });
      const kids = depth < 2 ? 3 : 2;
      for (let k = 0; k < kids; k++) {
        const na = a + (k - (kids - 1) / 2) * (0.5 + r() * 0.4) + (r() - 0.5) * 0.3;
        grow(u2, v2, na, len * (0.68 + r() * 0.2), depth + 1, dist);
      }
    };
    grow(120, 0, 0, 170, 0, 0);
    grow(330, 20, 0.15, 150, 1, 140);
    grow(560, -10, -0.1, 160, 1, 260);
    const maxD = Math.max(...segs.map(s => s.d1));
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = BG.mint();
        const toW = (u, v) => [B[0] + Math.cos(ang) * u - Math.sin(ang) * v, B[1] + Math.sin(ang) * u + Math.cos(ang) * v];
        // big arm
        const armPath = `M${n2(A[0])},${n2(A[1])} L${n2(B[0])},${n2(B[1])}`;
        s += P(armPath, { stroke: INK, 'stroke-width': AW + 18, 'stroke-linecap': 'round' }) + P(armPath, { stroke: '#F8C48B', 'stroke-width': AW, 'stroke-linecap': 'round' });
        // shading
        const sh0 = toW(0, AW * 0.32), sh1 = toW(alen, AW * 0.32);
        s += L(sh0[0], sh0[1], sh1[0], sh1[1], { stroke: '#E3A066', 'stroke-width': AW * 0.25, 'stroke-linecap': 'round', opacity: 0.6 });
        // fractal growth
        const gp = prog(t, tg, tge + 0.2, E.inOutSine) * maxD;
        let d = '', d2 = '';
        for (const sg of segs) {
          if (sg.d0 > gp) continue;
          const f = clamp((gp - sg.d0) / (sg.d1 - sg.d0));
          const p0 = toW(sg.u, sg.v), p1 = toW(lerp(sg.u, sg.u2, f), lerp(sg.v, sg.v2, f));
          const w = Math.max(3, 16 - sg.depth * 2.2);
          s += L(p0[0], p0[1], p1[0], p1[1], { stroke: '#E0525A', 'stroke-width': w + 5, 'stroke-linecap': 'round', opacity: 0.55 });
          s += L(p0[0], p0[1], p1[0], p1[1], { stroke: '#C93A45', 'stroke-width': w * 0.55, 'stroke-linecap': 'round' });
        }
        // hand
        const hd = (Math.atan2(B[1] - A[1], B[0] - A[0]) * 180) / Math.PI;
        const { rusty: _r } = require('../lib/rusty');
        s += G(tr(B[0], B[1], hd, 3.4), handBig(t));
        // Rusty peeking
        const st = pose({ x: 880, y: 2560, s: 1.05, hair: 0.3 }, t > tl ? 'starry' : 'curious', t, 13);
        st.look = [-0.8, -0.7];
        s += rusty(st);
        const k = fx.popIn(t, tl, 0.4);
        if (k > 0) s += text('LICHTENBERG\nFIGURES', { x: 540, y: 340, size: 112, sx: k, sy: k, rot: -3, fill: '#FF8A8A' });
        return s;
      },
    });
    function handBig(t) {
      // open hand in local coords pointing +x (copy of rig hand style, larger)
      const sk = { stroke: INK, 'stroke-width': 4.5, 'stroke-linejoin': 'round' };
      const f = (a, len) => [Math.cos((a * Math.PI) / 180) * len, Math.sin((a * Math.PI) / 180) * len];
      const fingers = [f(-40 + Math.sin(t * 3) * 3, 56), f(-12, 62), f(16, 58), f(40, 46), f(-95, 42)];
      let o = '';
      for (const [fx_, fy] of fingers) o += L(16, 0, 16 + fx_, fy, { stroke: INK, 'stroke-width': 21 + 9, 'stroke-linecap': 'round' });
      o += C(18, 0, 36, { fill: '#F8C48B', ...sk });
      for (const [fx_, fy] of fingers) o += L(16, 0, 16 + fx_, fy, { stroke: '#F8C48B', 'stroke-width': 21, 'stroke-linecap': 'round' });
      o += C(18, 0, 33, { fill: '#F8C48B' });
      return o;
    }
  }

  // ---------------------------------------------------------------- S8 heart stops
  {
    const t0 = cut('l10'), t1 = cut('l11');
    const td = T.w('l10', 'danger'), tsh = T.w('l10', 'shock'), tst = T.w('l10', 'stop');
    const bpm = 96, beat = 60 / bpm;
    for (let k = 0; t0 + k * beat + 0.3 * beat < tsh; k++) { cue(t0 + k * beat + 0.3 * beat, 'beep', 0.22); cue(t0 + k * beat + 0.3 * beat, 'heartbeat', 0.35, [bpm, 1]); }
    cue(tsh, 'zap', 0.7); cue(tsh, 'impact', 0.4); cue(tst, 'flatline', 0.3, [2.0]);
    shots.push({
      t0, t1, push: 0.06,
      shakes: [[tsh, 0.45, 26]],
      flashes: [[tsh, 0.22, '#ffffff', 0.8]],
      draw(lt, t) {
        let s = BG.pink();
        const alive = t < tst;
        const ph = ((t - t0) % beat) / beat;
        const pulse = alive && t < tsh ? 1 + 0.07 * Math.exp(-Math.pow((ph - 0.3) / 0.06, 2)) + 0.04 * Math.exp(-Math.pow((ph - 0.5) / 0.06, 2)) : 1;
        const jit = t > tsh && t < tst + 0.3 ? noise(t * 40, 2) * 12 : 0;
        const mood = t > tst ? 'dead' : t > tsh ? 'shocked' : t > td ? 'worried' : 'happy';
        const tint = prog(t, tst, tst + 0.6);
        s += pr.heart(540 + jit, 780, 1.45 * pulse, { mood, tint, t });
        if (t > tsh && t < tst + 0.4) s += pr.bolt([560, -100], [540 + jit, 640], { seed: Math.floor(t * 20), width: 22, branches: 3 });
        s += pr.monitor(540, 1480, t - t0, { flatT: tst - t0, bpm, color: tint > 0 ? '#FF5A5A' : '#4CFF8A' });
        if (t > tst) s += text('0 BPM', { x: 540, y: 1780, size: 100, fill: '#FF5A5A', sx: fx.popIn(t, tst, 0.3), sy: fx.popIn(t, tst, 0.3) });
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S9 nine out of ten survive
  {
    const t0 = cut('l11'), t1 = cut('l12');
    const tn = T.w('l11', 'nine'), tsv = T.w('l11', 'survive');
    for (let i = 0; i < 10; i++) cue(t0 + 0.05 + i * 0.07, 'bubble', 0.35, [1 + i * 0.05]);
    cue(tn, 'chime', 0.45); cue(tsv, 'sparkle', 0.5);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = BG.mint();
        for (let i = 0; i < 10; i++) {
          const row = Math.floor(i / 5), col = i % 5;
          const x = 140 + col * 200, y = 1180 + row * 400;
          const k = fx.popIn(t, t0 + 0.05 + i * 0.07, 0.35);
          if (k <= 0) continue;
          const unlucky = i === 7;
          const marked = t > tn + i * 0.03;
          if (marked) s += C(x, y - 140, 125 * E.outBack(prog(t, tn + i * 0.03, tn + i * 0.03 + 0.3)), { fill: unlucky ? '#B9B4BC' : '#7FE0A0', stroke: INK, 'stroke-width': 7 });
          const st = pose({ x, y, s: 0.27 * k, hair: 0.4, skinTint: unlucky && marked ? '#555' : null, skinTintAmt: 0.5, tint: unlucky && marked ? '#888' : null, tintAmt: 0.3 },
            marked ? (unlucky ? 'dead' : 'proud') : 'worried', t, 20 + i);
          s += rusty(st);
          if (unlucky && marked) s += fx.puffs(t, tn, x, y - 290, { n: 4, spread: 30, rise: 120, size: 20, dur: 1.2, color: '#6d6a70', seed: 2 });
        }
        const k1 = fx.popIn(t, tn, 0.4), k2 = fx.popIn(t, tsv, 0.4);
        if (k1 > 0) s += text('9 OUT OF 10', { x: 540, y: 380, size: 130, sx: k1, sy: k1, rot: -2 });
        if (k2 > 0) s += text('SURVIVE!', { x: 540, y: 560, size: 150, sx: k2, sy: k2, rot: 2, fill: '#7CFF9E' });
        return s;
      },
    });
  }

  // ---------------------------------------------------------------- S10 don't hide under a tree
  {
    const t0 = cut('l12'), t1 = duration;
    const th = T.w('l12', 'hide'), tu = T.w('l12', 'under'), tstr = T.e('l12') + 0.15;
    cue(t0 + 0.1, 'cartoon_run', 0.35, [tu - t0]); cue(tstr - 0.04, 'zap', 0.7); cue(tstr, 'thunder', 0.95); cue(tstr + 0.4, 'crackle', 0.4);
    shots.push({
      t0, t1, push: 0.05, punch: 0.02,
      shakes: [[tstr, 0.7, 30]],
      flashes: [[tstr, 0.35, '#ffffff', 0.95]],
      draw(lt, t) {
        const hit = t >= tstr;
        const strobe = hit && t < tstr + 0.55 ? Math.floor((t - tstr) * 16) % 2 === 0 : false;
        let s = pr.storm(t, { flashA: hit && t < tstr + 0.6 ? (strobe ? 0.7 : 0.2) * (1 - (t - tstr) / 0.6) : 0, id: 'st2' });
        s += pr.hill(1700);
        s += pr.tree(760, 1720, 1.3, { burnt: hit ? 1 : 0, t });
        const running = t < tu + 0.15;
        const rx = kf(t, [[t0, -180], [tu + 0.15, 600, E.outCubic]]);
        const ph = (t - t0) * 14;
        let st;
        if (running) {
          st = pose({ x: rx, y: 1700 + Math.abs(Math.sin(ph)) * -26, s: 0.95, lean: 8, footL: [-66 + Math.sin(ph) * 40, -18 - Math.max(0, Math.sin(ph)) * 70], footR: [66 - Math.sin(ph) * 40, -18 - Math.max(0, -Math.sin(ph)) * 70],
            handL: [-70, -1010], handR: [70, -1010], handPoseL: 'open', handPoseR: 'open', bendL: 1, bendR: -1 }, 'worried', t, 30);
        } else {
          st = pose({ x: 600, y: 1700, s: 0.95, hair: hit ? 1 : 0, xray: strobe,
            skinTint: hit ? '#4a3c38' : null, skinTintAmt: hit ? 0.45 : 0, tint: hit ? '#2d2626' : null, tintAmt: hit ? 0.18 : 0 }, hit ? (t < tstr + 0.5 ? 'shocked' : 'dizzy') : 'happy', t, 31);
          if (!hit) { st.handR = [190, -520]; st.handPoseR = 'thumb'; st.bendR = -1; }
        }
        s += rusty(st);
        if (hit) {
          s += fx.puffs(t, tstr + 0.1, 600, 1700 - 1010, { n: 7, spread: 140, rise: 300, size: 44, dur: 1.4, color: '#6d6a70', seed: 6 });
          s += fx.puffs(t, tstr + 0.1, 760, 1720 - 700, { n: 9, spread: 260, rise: 400, size: 70, dur: 1.8, color: '#5d5a60', seed: 7 });
        }
        if (t >= tstr - 0.06 && t < tstr + 0.5) {
          const p = prog(t, tstr - 0.06, tstr, E.outQuad);
          const fl = Math.floor(t * 30) % 3;
          s += pr.bolt([700, -200], [760, 1720 - 720], { seed: 60 + fl, p, width: 28, branches: 5, opacity: fl === 2 ? 0.6 : 1 });
        }
        return s;
      },
    });
  }

  const tl = timeline(shots, duration);
  return { duration, frame: tl.frame, cues };
};
