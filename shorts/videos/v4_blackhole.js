// Video 4 — "What if you fell into a black hole?"
'use strict';
const { clamp, lerp, E, prog, kf, rng, noise, hash, mixColor, n2, tr, G, O, P, C, EL, R, L, PL, PG, smoothPath } = require('../lib/core');
const { rusty, pose, PAL } = require('../lib/rusty');
const { space, flat } = require('../lib/bg');
const { text, width } = require('../lib/text');
const fx = require('../lib/fx');
const pr = require('../lib/props');
const { timeline, camKeys } = require('../lib/scene');
const INK = '#2b2220';

const fit = (str, maxW, size) => Math.min(size, (size * maxW) / width(str, size));

// black hole with accretion disk; disk swirl animated by dash offset
function blackHole(cx, cy, Rr, t, o = {}) {
  const { tiltK = 0.42, id = 'bh' } = o;
  const rx = Rr * 2.25, ry = Rr * 2.25 * tiltK;
  let s = `<defs><radialGradient id="${id}g"><stop offset="0.3" stop-color="#FF9A3C" stop-opacity="0.55"/><stop offset="0.6" stop-color="#C2410C" stop-opacity="0.18"/><stop offset="1" stop-color="#7C2D12" stop-opacity="0"/></radialGradient>
  <linearGradient id="${id}d" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FF7A1A"/><stop offset="0.5" stop-color="#FFF1A8"/><stop offset="1" stop-color="#FF7A1A"/></linearGradient></defs>`;
  s += C(cx, cy, Rr * 3.0, { fill: `url(#${id}g)` });
  const ring = (w, col, op, dash) => EL(cx, cy, rx, ry, { fill: 'none', stroke: col, 'stroke-width': w, opacity: op, ...(dash ? { 'stroke-dasharray': dash, 'stroke-dashoffset': n2(-t * 260) } : {}) });
  // back part of disk
  s += ring(Rr * 0.55, '#C2410C', 0.55) + ring(Rr * 0.32, `url(#${id}d)`, 1) + ring(Rr * 0.1, '#FFF8D6', 0.8, `${n2(Rr * 0.5)} ${n2(Rr * 0.3)}`);
  // lensed light arching over the top
  s += P(`M${n2(cx - Rr * 1.22)},${n2(cy)} A${n2(Rr * 1.22)},${n2(Rr * 1.16)} 0 0,1 ${n2(cx + Rr * 1.22)},${n2(cy)}`, { fill: 'none', stroke: '#FFB54A', 'stroke-width': Rr * 0.22, opacity: 0.8 });
  s += P(`M${n2(cx - Rr * 1.22)},${n2(cy)} A${n2(Rr * 1.22)},${n2(Rr * 1.16)} 0 0,1 ${n2(cx + Rr * 1.22)},${n2(cy)}`, { fill: 'none', stroke: '#FFF1A8', 'stroke-width': Rr * 0.07 });
  // shadow + photon ring
  s += C(cx, cy, Rr * 1.04, { fill: 'none', stroke: '#FFE7A0', 'stroke-width': Rr * 0.05, opacity: 0.9 });
  s += C(cx, cy, Rr, { fill: '#000000' });
  // front part of the disk (lower arc, over the shadow)
  const arc = `M${n2(cx - rx)},${n2(cy)} A${n2(rx)},${n2(ry)} 0 0,0 ${n2(cx + rx)},${n2(cy)}`;
  s += P(arc, { fill: 'none', stroke: '#C2410C', 'stroke-width': Rr * 0.55, opacity: 0.55 }) + P(arc, { fill: 'none', stroke: `url(#${id}d)`, 'stroke-width': Rr * 0.32 }) +
    P(arc, { fill: 'none', stroke: '#FFF8D6', 'stroke-width': Rr * 0.1, opacity: 0.85, 'stroke-dasharray': `${n2(Rr * 0.5)} ${n2(Rr * 0.3)}`, 'stroke-dashoffset': n2(t * 260) });
  return s;
}

// Rusty drawn as a long noodle path (for the spaghetti plate)
function rustyNoodle(pts, w, t) {
  const n = pts.length;
  const segs = [[0, 0.12, PAL.hair], [0.12, 0.25, PAL.skin], [0.25, 0.55, PAL.shirt], [0.55, 0.93, PAL.pants], [0.93, 1, PAL.shoe]];
  let s = PL(pts, { fill: 'none', stroke: INK, 'stroke-width': w + 14, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
  for (const [a, b, c] of segs) {
    const sub = pts.slice(Math.floor(a * (n - 1)), Math.ceil(b * (n - 1)) + 1);
    s += PL(sub, { fill: 'none', stroke: c, 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
  }
  return s;
}

module.exports = function (T) {
  const cues = [];
  const cue = (t, sfx, gain = 0.5, args) => cues.push({ t: +t.toFixed(3), sfx, gain, ...(args ? { args } : {}) });
  const duration = T.duration + 0.3;
  const shots = [];
  const cut = id => T.s(id) - 0.08;
  const bg = (t, id) => space({ t, top: '#05061A', bottom: '#160B33', id, seed: 9 });

  // ------------------------------------------------------------- S1 falling in
  {
    const t1 = cut('l2');
    cue(0.02, 'fall_whistle', 0.4, [1.7]); cue(0.0, 'drone', 0.45, [3.0, 49]);
    shots.push({
      t0: 0, t1, push: 0.08, punch: 0,
      draw(lt, t) {
        let s = bg(t, 'a');
        s += blackHole(540, 1300, 230, t, { id: 'b1' });
        const p = prog(t, 0, t1 + 0.6, E.inQuad);
        const ang = p * 3.4, rad = lerp(560, 330, p);
        const x = 540 + Math.cos(ang - 1.2) * rad, y = 1300 + Math.sin(ang - 1.2) * rad * 0.7 - 120;
        const st = pose({ x, y, s: lerp(0.62, 0.38, p), rot: t * 220, handL: [-260, -760], handR: [260, -760], bendL: -1, bendR: 1, handPoseL: 'spread', handPoseR: 'spread', footL: [-120, -40], footR: [120, -40], hair: 0.4 }, 'scared', t, 1);
        s += rusty(st);
        s += fx.speedLines(t, { dir: 'v', speed: 1800, n: 10, color: '#ffffff', opacity: 0.25, w: 5, len: 200 });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S2 feet pulled harder than head
  {
    const t0 = cut('l2'), t1 = cut('l3'), tf = T.w('l2', 'feet'), th = T.w('l2', 'harder'), thd = T.w('l2', 'than');
    cue(tf, 'whoosh', 0.35, [0.4]); cue(th, 'boing', 0.3, [0.6]); cue(thd, 'pop', 0.4);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = bg(t, 'b');
        s += blackHole(540, 2280, 520, t, { id: 'b2' });
        const pull = prog(t, th, th + 0.5) * 30;
        const st = pose({ x: 540, y: 1500 + pull, s: 0.8, sy: 1 + pull / 600, handL: [-200, -800], handR: [200, -800], bendL: -1, bendR: 1, handPoseL: 'spread', handPoseR: 'spread' }, 'worried', t, 2);
        st.look = [0, 1];
        s += rusty(st);
        const pa = prog(t, tf - 0.1, tf + 0.25, E.outBack), big = 1 + prog(t, th, th + 0.3, E.outBack) * 0.5;
        if (pa > 0) {
          s += fx.arrow([700, 1350], [700, 1350 + 260 * pa * big], 1, { color: '#FF5A4E', w: 30 * big, head: 64 * big });
          s += text('STRONG', { x: 870, y: 1480, size: 70, sx: pa, sy: pa, fill: '#FF8A7A', rot: 8 });
        }
        const pb = prog(t, thd - 0.1, thd + 0.25, E.outBack);
        if (pb > 0) {
          s += fx.arrow([700, 640], [700, 640 + 90 * pb], 1, { color: '#7FD8FF', w: 16, head: 36 });
          s += text('WEAK', { x: 860, y: 700, size: 64, sx: pb, sy: pb, fill: '#9FDBFF', rot: 8 });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S3 stretched like a noodle
  {
    const t0 = cut('l3'), t1 = cut('l4'), ts = T.w('l3', 'stretched'), tn = T.w('l3', 'noodle');
    cue(ts - 0.1, 'stretch', 0.55, [1.1]); cue(tn, 'boing', 0.4, [0.5]);
    shots.push({
      t0, t1, push: 0.05,
      cam: camKeys([[t0, { x: 540, y: 1000, z: 1 }], [ts, { x: 540, y: 900, z: 0.96 }, 0.8]]),
      draw(lt, t) {
        let s = bg(t, 'c');
        s += blackHole(540, 2280, 520, t, { id: 'b3' });
        const k = prog(t, ts - 0.15, tn + 0.2, E.inOutCubic);
        const wob = Math.sin(t * 14) * 0.04 * k;
        const st = pose({ x: 540, y: 1720, s: 0.8, sx: lerp(1, 0.42, k) + wob, sy: lerp(1, 2.0, k) - wob, handL: [-130, -820], handR: [130, -820], bendL: -1, bendR: 1, handPoseL: 'spread', handPoseR: 'spread' }, k > 0.3 ? 'scared' : 'worried', t, 3);
        s += rusty(st);
        const kk = fx.popIn(t, tn, 0.4);
        if (kk > 0) s += text('NOODLE!', { x: 540, y: 300, size: 170, sx: kk, sy: kk, rot: -4, fill: '#FFE45C' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S4 spaghettification plate
  {
    const t0 = cut('l4'), t1 = cut('l5'), tsc = T.w('l4', 'scientists'), tsp = T.w('l4', 'spaghettification');
    cue(tsc, 'pop', 0.4); cue(tsp, 'chime', 0.4); cue(tsp, 'boing', 0.35, [1.1]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = flat('#F6D9A8') + require('../lib/bg').BG.warm();
        // plate
        s += EL(540, 1250, 470, 240, { fill: '#D9D2C5', stroke: INK, 'stroke-width': 10 }) + EL(540, 1235, 470, 240, { fill: '#ffffff', stroke: INK, 'stroke-width': 10 }) + EL(540, 1235, 330, 160, { fill: '#F3EFE8', stroke: '#D9D2C5', 'stroke-width': 6 });
        // noodle swirl
        const pts = [];
        for (let i = 0; i <= 120; i++) {
          const u = i / 120, a = u * Math.PI * 7.5 + 0.4 * Math.sin(t * 2);
          const r = lerp(30, 280, Math.pow(u, 0.8));
          pts.push([540 + Math.cos(a) * r, 1215 + Math.sin(a) * r * 0.42 - 20 * Math.sin(u * 30 + t * 3)]);
        }
        pts.reverse();
        s += rustyNoodle(pts, 34, t);
        // little head at the noodle's end
        const hp = pts[0];
        // head-local origin is the neck joint; head center sits 165 units above it
        s += rusty(pose({ x: hp[0], y: hp[1] + 165 * 0.62 - 40, s: 0.62, headOnly: true }, 'dizzy', t, 4));
        // fork
        s += G(tr(820, 900, 28), R(-16, -60, 32, 420, { rx: 14, fill: '#B9C1CC', stroke: INK, 'stroke-width': 8 }), P('M-52,-60 L-52,-200 M-18,-60 L-18,-210 M18,-60 L18,-210 M52,-60 L52,-200', { stroke: INK, 'stroke-width': 22, 'stroke-linecap': 'round' }), P('M-52,-60 L-52,-200 M-18,-60 L-18,-210 M18,-60 L18,-210 M52,-60 L52,-200', { stroke: '#B9C1CC', 'stroke-width': 10, 'stroke-linecap': 'round' }), P('M-60,-60 Q0,10 60,-60', { fill: '#B9C1CC', stroke: INK, 'stroke-width': 8 }));
        const k = fx.popIn(t, tsp, 0.45);
        if (k > 0) { const sz = fit('SPAGHETTIFICATION', 980, 110); s += text('SPAGHETTIFICATION', { x: 540, y: 380, size: sz, sx: k, sy: k, rot: -3, fill: '#FFE45C' }); }
        else s += text('SCIENTISTS CALL IT...', { x: 540, y: 380, size: fit('SCIENTISTS CALL IT...', 960, 80), sx: fx.popIn(t, tsc), sy: fx.popIn(t, tsc), fill: '#ffffff' });
        return s;
      },
    });
  }
  // ------------------------------------------------------------- S5 friend watching from far away
  {
    const t0 = cut('l5'), t1 = cut('l6'), tw = T.w('l5', 'watching'), tst = T.w('l5', 'strange');
    cue(tw, 'whoosh', 0.3, [0.6]); cue(tst, 'slide_up', 0.35, [0.4]); cue(tst + 0.1, 'pop', 0.4);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = bg(t, 'd');
        s += blackHole(820, 560, 120, t, { id: 'b5' });
        // tiny Rusty near the black hole
        s += rusty(pose({ x: 760, y: 470, s: 0.1, sy: 2.2, sx: 0.5 }, 'scared', t, 5));
        const st = pose(Object.assign({ x: 330, y: 1680, s: 0.95, handR: [200, -500], handPoseR: 'fist', bendR: -1 }, pr.friendBase), t > tst ? 'shocked' : 'curious', t, 6);
        st.look = [0.9, -0.6];
        s += rusty(st);
        // telescope on a tripod
        const tx = 720, ty = 1060;
        s += P(`M${tx},${ty} L${tx - 120},1690 M${tx},${ty} L${tx + 130},1690 M${tx},${ty} L${tx + 10},1700`, { stroke: INK, 'stroke-width': 22, 'stroke-linecap': 'round' }) + P(`M${tx},${ty} L${tx - 120},1690 M${tx},${ty} L${tx + 130},1690 M${tx},${ty} L${tx + 10},1700`, { stroke: '#8A4A24', 'stroke-width': 10, 'stroke-linecap': 'round' });
        s += G(tr(tx, ty, -38), R(-170, -40, 380, 80, { rx: 18, fill: '#C9733F', stroke: INK, 'stroke-width': 8 }), R(180, -56, 90, 112, { rx: 18, fill: '#8A4A24', stroke: INK, 'stroke-width': 8 }), R(-200, -28, 40, 56, { rx: 10, fill: '#8A4A24', stroke: INK, 'stroke-width': 8 }), C(0, 0, 18, { fill: '#555', stroke: INK, 'stroke-width': 6 }));
        if (t > tst) s += text('?!', { x: 250, y: 620, size: 180, fill: '#FFE45C', sx: fx.popIn(t, tst), sy: fx.popIn(t, tst), rot: -8 });
        s += text('FAR AWAY', { x: 300, y: 330, size: 90, fill: '#9FDBFF', sx: fx.popIn(t, T.w('l5', 'far')), sy: fx.popIn(t, T.w('l5', 'far')) });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S6 slower, red, fades, frozen
  {
    const t0 = cut('l6'), t1 = cut('l8');
    const ts1 = T.w('l6', 'slower'), ts2 = T.s('l6') + 1.1, tred = T.w('l7', 'red'), tfd = T.w('l7', 'fades'), tfr = T.w('l7', 'frozen');
    cue(t0 + 0.1, 'warp', 0.4, [2.4]); cue(tred, 'hiss', 0.25, [0.8]); cue(tfr, 'glass_tap', 0.5); cue(tfr, 'drone', 0.4, [1.6, 41]);
    shots.push({
      t0, t1, push: 0.07,
      draw(lt, t) {
        let s = bg(t, 'e');
        s += blackHole(540, 1500, 400, t * 0.4, { id: 'b6' });
        // position approaches the rim ever more slowly
        const u = 1 - Math.exp(-(t - t0) * 0.9);
        const y = lerp(760, 1000, u), x = 540;
        const red = prog(t, tred - 0.1, tred + 0.6), fade = prog(t, tfd, tfr + 0.3);
        const st = pose({ x, y: y + 200, s: 0.32, sx: 0.8, sy: 1.25, tint: '#D0102B', tintAmt: red * 0.75, opacity: 1 - fade * 0.82, handL: [-200, -780], handR: [200, -780], bendL: -1, bendR: 1 }, 'scared', t * (1 - u * 0.95), 7, 1 - u);
        s += rusty(st);
        // his clock as seen from outside: slowing down
        const frac = (1 - Math.exp(-(t - t0) * 0.7)) * 0.6;
        s += O(1 - fade * 0.7, pr.stopwatch(820, 560, 0.5, { frac, ring: mixColor('#FF5A4E', '#9b1020', red) }));
        const lab = t > tfr ? 'FROZEN' : t > tred ? 'RED...' : t > ts2 ? 'SLOWER...' : t > ts1 ? 'SLOWER' : '';
        if (lab) s += text(lab, { x: 540, y: 330, size: lab === 'FROZEN' ? 170 : 140, fill: t > tred ? '#FF6B6B' : '#9FDBFF', rot: -3, sx: fx.popIn(t, t > tfr ? tfr : t > tred ? tred : t > ts2 ? ts2 : ts1, 0.3), sy: fx.popIn(t, t > tfr ? tfr : t > tred ? tred : t > ts2 ? ts2 : ts1, 0.3) });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S7 for Rusty, time runs normally
  {
    const t0 = cut('l8'), t1 = cut('l9'), tw = T.w('l8', 'what'), tn = T.w('l8', 'normally');
    cue(tw, 'boing', 0.3, [0.9]); cue(T.w('l8', 'time'), 'clock', 0.45, [1.2, 4]); cue(tn + 0.3, 'ding', 0.3);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = bg(t, 'f');
        s += blackHole(540, 2300, 560, t, { id: 'b7' });
        const st = pose({ x: 470, y: 1760, s: 0.7, sx: 0.55, sy: 1.6, handL: [-170, -520], handR: [190, -600], handPoseL: 'open', handPoseR: 'fist', bendL: 1, bendR: -1 }, t > tw ? 'smug' : 'neutral', t, 8);
        st.look = [0.9, 0.2];
        s += rusty(st);
        s += pr.stopwatch(820, 820, 0.62, { frac: ((t - t0) * 0.5) % 1, ring: '#3CC86B' });
        if (t > tn) s += text('NORMAL TIME', { x: 540, y: 330, size: 120, sx: fx.popIn(t, tn), sy: fx.popIn(t, tn), fill: '#7CFF9E', rot: -2 });
        else if (t > tw) s += text("WHAT'S LEFT OF HIM", { x: 540, y: 330, size: fit("WHAT'S LEFT OF HIM", 960, 90), sx: fx.popIn(t, tw), sy: fx.popIn(t, tw), fill: '#ffffff' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S8 crossing the event horizon
  {
    const t0 = cut('l9'), t1 = cut('l10'), tc = T.w('l9', 'crosses'), te = T.w('l9', 'event'), tl = T.w('l9', 'light');
    cue(tc, 'suck', 0.5, [1.2]); cue(te, 'pop', 0.4); cue(tl, 'sparkle', 0.35);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = bg(t, 'g');
        const cx = 540, cy = 2700, Rr = 1500;
        const y = kf(t, [[t0, 1120], [tc, 1170], [te + 1.0, 2060, E.inCubic]]);
        const st = pose({ x: 540, y, s: 0.46, sx: 0.5, sy: 1.6, handL: [-160, -820], handR: [160, -820], bendL: -1, bendR: 1, handPoseL: 'open', handPoseR: 'open' }, 'shocked', t, 9);
        s += rusty(st);
        // horizon: glowing rim + opaque inside, drawn over Rusty so he vanishes into it
        s += C(cx, cy, Rr + 60, { fill: 'none', stroke: '#FF9A3C', 'stroke-width': 80, opacity: 0.25 });
        s += C(cx, cy, Rr + 14, { fill: 'none', stroke: '#FFE7A0', 'stroke-width': 18, opacity: 0.9 });
        s += C(cx, cy, Rr, { fill: '#000000' });
        // light trying to escape but falling back
        if (t > tl - 0.4) {
          for (let i = 0; i < 7; i++) {
            const ph = ((t - tl + 0.4) * 0.7 + i / 7) % 1;
            const x = 140 + i * 133, h = Math.sin(ph * Math.PI) * 260;
            const yy = 1520 - h;
            s += C(x, yy, 14, { fill: '#FFE45C' }) + C(x, yy, 30, { fill: '#FFE45C', opacity: 0.25 });
          }
        }
        if (t > te) {
          const k = fx.popIn(t, te, 0.4);
          s += text('EVENT HORIZON', { x: 540, y: 330, size: fit('EVENT HORIZON', 960, 130), sx: k, sy: k, rot: -2, fill: '#FFB54A' });
          s += fx.arrow([860, 560], [lerp(860, 800, k), lerp(560, 1170, k)], 1, { color: '#FFB54A', curve: -0.15 });
        }
        if (t > tl) s += text('NOT EVEN LIGHT ESCAPES', { x: 540, y: 1780, size: fit('NOT EVEN LIGHT ESCAPES', 940, 70), fill: '#FFE45C', sx: fx.popIn(t, tl), sy: fx.popIn(t, tl) });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S9 no way back
  {
    const t0 = cut('l10'), t1 = duration, tn = T.w('l10', 'no');
    cue(tn, 'impact', 0.5); cue(tn, 'drone', 0.45, [2.0, 37]);
    shots.push({
      t0, t1, push: 0.06,
      draw(lt, t) {
        let s = flat('#000000') + O(0.5, space({ t, top: '#000000', bottom: '#0B0618', id: 'h', seed: 21 }));
        // a tiny hand waving goodbye, sinking
        const y = kf(t, [[t0, 1200], [t1, 1420]]);
        const a = Math.sin(t * 8) * 25;
        s += O(1 - prog(t, t1 - 0.8, t1), G(tr(540, y, a, 2.2), L(0, 120, 0, 30, { stroke: INK, 'stroke-width': 56, 'stroke-linecap': 'round' }), L(0, 120, 0, 30, { stroke: '#F8C48B', 'stroke-width': 40, 'stroke-linecap': 'round' }),
          ...[-50, -20, 10, 40].map((ang, i) => L(0, 0, Math.sin((ang * Math.PI) / 180) * 60, -Math.cos((ang * Math.PI) / 180) * 60, { stroke: INK, 'stroke-width': 30, 'stroke-linecap': 'round' })),
          C(0, 0, 38, { fill: '#F8C48B', stroke: INK, 'stroke-width': 8 }),
          ...[-50, -20, 10, 40].map((ang, i) => L(0, 0, Math.sin((ang * Math.PI) / 180) * 60, -Math.cos((ang * Math.PI) / 180) * 60, { stroke: '#F8C48B', 'stroke-width': 18, 'stroke-linecap': 'round' })),
          C(0, 0, 34, { fill: '#F8C48B' })));
        const k = fx.popIn(t, tn, 0.45);
        if (k > 0) s += text('NO WAY BACK', { x: 540, y: 620, size: 150, sx: k, sy: k, fill: '#FF6B6B', rot: -2 });
        return s;
      },
    });
  }

  const tl = timeline(shots, duration);
  return { duration, frame: tl.frame, cues };
};
