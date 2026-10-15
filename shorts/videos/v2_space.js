// Video 2 — "What if you went to space without a suit?"
'use strict';
const { clamp, lerp, E, prog, kf, rng, noise, hash, mixColor, n2, tr, G, O, P, C, EL, R, L, PL, PG } = require('../lib/core');
const { rusty, pose } = require('../lib/rusty');
const { BG, space } = require('../lib/bg');
const { text } = require('../lib/text');
const fx = require('../lib/fx');
const pr = require('../lib/props');
const { timeline, camKeys } = require('../lib/scene');
const INK = '#2b2220';

module.exports = function (T) {
  const cues = [];
  const cue = (t, sfx, gain = 0.5, args) => cues.push({ t: +t.toFixed(3), sfx, gain, ...(args ? { args } : {}) });
  const duration = T.duration + 0.3;
  const shots = [];
  const cut = id => T.s(id) - 0.08;

  // gentle zero-g float: limbs drift, body slowly rotates
  const floaty = (t, seed = 1, amt = 1) => ({
    rot: Math.sin(t * 0.7 + seed) * 7 * amt,
    handL: [-235 + Math.sin(t * 1.3 + seed) * 25, -560 + Math.sin(t * 1.1 + seed) * 40],
    handR: [235 + Math.sin(t * 1.2 + seed + 1) * 25, -590 + Math.sin(t * 1.0 + seed + 2) * 40],
    bendL: -1, bendR: 1, handPoseL: 'open', handPoseR: 'open',
    footL: [-110 + Math.sin(t * 0.9 + seed) * 20, -40 + Math.sin(t * 1.4 + seed) * 30],
    footR: [110 + Math.sin(t * 1.1 + seed) * 20, -70 + Math.sin(t * 1.2 + seed + 1) * 30],
  });
  const spaceBg = (t, k = '') => space({ t, top: '#0B1240', bottom: '#2A1660', id: k }) + pr.earthArc(t, { rot: t * 0.01 });

  // ------------------------------------------------------------- S1 steps out of the airlock
  {
    const t1 = cut('l2'), tw = T.w('l1', 'without');
    cue(0.05, 'whoosh', 0.35, [0.8]); cue(tw, 'pop', 0.6); cue(tw + 0.1, 'buzzer', 0.3);
    shots.push({
      t0: 0, t1, push: 0.06, punch: 0,
      draw(lt, t) {
        let s = spaceBg(t);
        s += pr.station(330, 1000, { s: 0.9, doorOpen: kf(t, [[0, 0.2], [0.5, 1, E.outBack]]) });
        const x = kf(t, [[0, 150], [1.6, 600, E.outCubic]]), y = kf(t, [[0, 1400], [1.6, 1500, E.outCubic]]);
        const st = pose(Object.assign({ x, y, s: 0.82 }, floaty(t, 1)), t > tw ? 'shocked' : 'happy', t, 2);
        if (t < tw) { st.handR = [200, -900 + Math.sin(t * 12) * 40]; st.bendR = 1; st.handPoseR = 'open'; }
        else st.look = [0.5, -0.6];
        s += rusty(st);
        const k = fx.popIn(t, tw, 0.4);
        if (k > 0) {
          s += G(tr(850, 360, 0, k * 0.9), pr.helmetIcon(0, 0, 1));
          s += fx.crossOut(t, tw + 0.15, 850, 380, 200);
          s += text('NO SUIT!', { x: 850, y: 580, size: 80, sx: k, sy: k, fill: '#FF6B6B' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S2 explode? nope
  {
    const t0 = cut('l2'), t1 = cut('l4'), te = T.w('l2', 'explode'), tn = T.w('l3', 'nope');
    cue(te - 0.1, 'inflate', 0.4, [0.5]); cue(te + 0.3, 'impact', 0.7); cue(tn, 'slide_down', 0.35, [0.3]); cue(tn + 0.05, 'pop', 0.5);
    shots.push({
      t0, t1, push: 0.05,
      shakes: [[te + 0.3, 0.4, 24]],
      draw(lt, t) {
        let s = spaceBg(t, 'b');
        const boom = t > te + 0.3 && t < tn;
        const fat = t < tn ? kf(t, [[te - 0.15, 0], [te + 0.3, 1.2, E.inQuad]]) : kf(t, [[tn, 1.0], [tn + 0.3, 0, E.outBack]]);
        if (!boom) {
          const st = pose(Object.assign({ x: 540, y: 1500, s: 0.9, fat }, floaty(t, 2, 0.5)), t > tn + 0.2 ? 'smug' : 'scared', t, 3);
          s += rusty(st);
        } else {
          s += pr.explosion(540, 1050, E.outBack(prog(t, te + 0.3, te + 0.55)) * 1.4, t);
          s += text('BOOM?', { x: 540, y: 1060, size: 170, rot: -5 });
        }
        if (t > tn) {
          const k = fx.popIn(t, tn, 0.35);
          s += text('NOPE!', { x: 540, y: 420, size: 190, sx: k, sy: k, rot: -4, fill: '#7CFF9E' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S3 freeze? no, vacuum, very slow
  {
    const t0 = cut('l4'), t1 = cut('l6');
    const tf = T.w('l4', 'freeze'), ta = T.w('l5', 'also'), tv = T.w('l5', 'vacuum'), tsl = T.w('l5', 'very');
    cue(tf, 'hiss', 0.35, [0.6]); cue(T.w('l4', 'instantly'), 'glass_tap', 0.5); cue(ta + 0.05, 'impact', 0.45); cue(ta + 0.05, 'glass_tap', 0.6); cue(tv, 'pop', 0.5); cue(tsl, 'boing', 0.3, [0.7]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = spaceBg(t, 'c');
        const broken = t > ta;
        const x = broken ? kf(t, [[ta, 540], [tv, 330, E.inOutCubic]]) : 540;
        const st = pose(Object.assign({ x, y: 1480, s: 0.85 }, floaty(t, 3, broken ? 1 : 0.1)), broken ? (t > tv ? 'curious' : 'happy') : 'shocked', t, 4, broken ? 1 : 0);
        if (!broken) { st.skinTint = '#9fd8ff'; st.skinTintAmt = prog(t, tf, tf + 0.4) * 0.5; }
        s += rusty(st);
        if (!broken) {
          s += pr.iceBlock(540, 1000, 640, 1100, { p: prog(t, tf, tf + 0.5, E.outCubic) });
          if (t > tf + 0.3) s += text('FREEZE?', { x: 540, y: 330, size: 150, fill: '#BFEFFF', sx: fx.popIn(t, tf + 0.3), sy: fx.popIn(t, tf + 0.3) });
        } else {
          // shards flying away
          const k = t - ta;
          const r = rng(4);
          for (let i = 0; i < 12; i++) {
            const a = r() * Math.PI * 2, sp = 900 + r() * 700;
            const px = 540 + Math.cos(a) * sp * k, py = 1000 + Math.sin(a) * sp * k;
            if (k < 1.2) s += G(tr(px, py, k * 400 * (r() - 0.5), 1), PG([[-40, -30], [50, -10], [10, 45]], { fill: '#BFEFFF', 'fill-opacity': 0.7, stroke: '#5AA9D6', 'stroke-width': 8 }));
            else r();
          }
          if (t > tv) {
            const k2 = fx.popIn(t, tv, 0.4);
            s += text('VACUUM', { x: 540, y: 330, size: 150, sx: k2, sy: k2, fill: '#FFE45C' });
            s += text('NO AIR = NO COLD AIR', { x: 540, y: 480, size: 60, sx: k2, sy: k2, fill: '#ffffff' });
            s += pr.thermometer(820, 1350, kf(t, [[tv, 0.62], [t1, 0.58]]), { s: 0.6, h: 900 });
          }
          if (t > tsl) s += pr.snail(kf(t, [[tsl, 1200], [t1, 720, E.outCubic]]), 1740, 1.4, t);
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S4 breathe out
  {
    const t0 = cut('l6'), t1 = cut('l7'), tb = T.w('l6', 'breathe');
    cue(tb, 'whoosh', 0.5, [0.9, false]);
    shots.push({
      t0, t1, push: 0.07,
      draw(lt, t) {
        let s = space({ t, id: 'd' });
        const ex = t > tb;
        const st = pose(Object.assign({ x: 540, y: 2350, s: 1.6 }, floaty(t, 4, 0.3)), ex ? 'blow' : 'puff', t, 5);
        st.rot = 0; st.eyeOpen = ex ? 0.7 : 1;
        if (!ex) st.blush = 1;
        s += rusty(st);
        if (ex) {
          const mx = 540, my = 2350 - 731 * 1.6;
          for (let i = 0; i < 7; i++) {
            const p = ((t - tb) * 1.2 + i / 7) % 1;
            if (t - tb < i * 0.06) continue;
            s += O(1 - p, fx.puffShape(mx + 60 + p * 480, my + 30 - p * 120 + Math.sin(i) * 60, 40 + p * 60, { fill: '#E8F4FF', stroke: '#9CC4EE', seed: i }));
          }
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S5 lungs would rip
  {
    const t0 = cut('l7'), t1 = cut('l8'), th = T.w('l7', 'holding'), tr_ = T.w('l7', 'rip'), tap = T.w('l7', 'apart');
    cue(th, 'inflate', 0.45, [tap - th]); cue(tr_, 'zap', 0.25, [0.3]); cue(tap, 'impact', 0.6); cue(tap, 'alarm', 0.25, [2]);
    shots.push({
      t0, t1, push: 0.05,
      shakes: [[tap, 0.45, 22]],
      flashes: [[tap, 0.25, '#FF5A5A', 0.4]],
      draw(lt, t) {
        let s = BG.pink();
        const inf = prog(t, th, tap, E.inQuad);
        const wob = t > tap ? noise(t * 30, 3) * 8 : 0;
        s += pr.lungs(540 + wob, 1080, 1.55, { inflate: inf, crack: prog(t, tr_, tap + 0.2), t });
        if (t > tap) {
          s += fx.burstLines(t, tap, 540, 1080, { n: 14, r0: 420, r1: 620, dur: 0.5, w: 12, color: '#E8343A' });
          const k = fx.popIn(t, tap, 0.35);
          s += text('DANGER!', { x: 540, y: 360, size: 170, sx: k, sy: k, rot: -4, fill: '#FF6B6B' });
        } else s += text('HOLDING BREATH', { x: 540, y: 360, size: 96, sx: fx.popIn(t, th), sy: fx.popIn(t, th), fill: '#ffffff' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S6 saliva boils
  {
    const t0 = cut('l8'), t1 = cut('l9'), tt = T.w('l8', 'tongue'), tb = T.w('l8', 'boil');
    cue(tb - 0.2, 'sizzle', 0.4, [1.6]);
    for (let i = 0; i < 10; i++) cue(tb - 0.1 + i * 0.12, 'bubble', 0.18, [1.4 + (i % 3) * 0.3]);
    shots.push({
      t0, t1, push: 0.08,
      cam: camKeys([[T.w('l8', 'tongue'), { x: 540, y: 1000, z: 1.45 }, 0.35]]),
      draw(lt, t) {
        let s = space({ t, id: 'e' });
        const sc = 2.8, x = 540, y = 2950;
        const st = pose({ x, y, s: sc, handL: [-200, -300], handR: [200, -300] }, { mouth: 'tongue', brow: 0.9, browTilt: 0.8, eyeSize: 1.1, pupil: 0.7 }, t, 6);
        st.look = [0, 0.9];
        s += rusty(st);
        // tongue tip in world coords
        const tx = x, ty = y + (-666 - 165 + 140) * sc;
        if (t > tb - 0.25) {
          const r = rng(9);
          for (let i = 0; i < 16; i++) {
            const bx = tx + (r() - 0.5) * 120, ph = r(), sp = 0.8 + r() * 0.8, sz = 14 + r() * 18;
            const p = ((t - tb) * sp + ph) % 1;
            if ((t - tb + 0.25) * sp < ph * 0.5) continue;
            s += C(bx + Math.sin(p * 6 + i) * 10, ty - 20 - p * 160, sz * (0.5 + p), { fill: '#ffffff', 'fill-opacity': 0.5, stroke: '#8FD3FF', 'stroke-width': 4, opacity: n2(1 - p) });
          }
          s += fx.puffs(t, tb, tx, ty - 160, { n: 6, spread: 100, rise: 300, size: 40, dur: 1.4, color: '#ffffff', stroke: 'none', opacity: 0.6, seed: 4 });
        }
        const ts = T.w('l8', 'saliva');
        if (t > ts) {
          const k = fx.popIn(t, ts, 0.4);
          s += text(t > tb ? 'BOILS AT 37°C!' : 'SALIVA', { x: 540, y: 1330, size: 80, sx: k, sy: k, rot: -3, fill: '#8FE3FF' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S7 swells to twice his size
  {
    const t0 = cut('l9'), t1 = cut('l10'), tv = T.w('l9', 'vapor'), tsw = T.w('l9', 'swells'), ttw = T.w('l9', 'twice');
    cue(tv - 0.1, 'hiss', 0.3, [0.9]); cue(tsw, 'inflate', 0.55, [1.3]); cue(ttw, 'boing', 0.4, [0.8]); cue(ttw, 'pop', 0.4);
    shots.push({
      t0, t1, push: 0.04,
      draw(lt, t) {
        let s = spaceBg(t, 'f');
        const fat = kf(t, [[tsw - 0.1, 0], [ttw + 0.4, 1.0, E.outBack]]);
        const st = pose(Object.assign({ x: 540, y: 1520, s: 0.85, fat, blush: fat }, floaty(t, 5, 0.6)), fat > 0.3 ? 'scared' : 'worried', t, 7);
        s += rusty(st);
        if (t > tv - 0.1 && t < tsw + 0.6) s += fx.puffs(t, tv - 0.1, 540, 1000, { n: 10, spread: 300, rise: 420, size: 50, dur: 1.4, color: '#CFEAFF', stroke: 'none', opacity: 0.8, seed: 5 });
        const k = fx.popIn(t, ttw, 0.4);
        if (k > 0) s += text('2X BIGGER', { x: 540, y: 380, size: 140, sx: k, sy: k, rot: -3 });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S8 skin holds him together
  {
    const t0 = cut('l10'), t1 = cut('l11'), tsk = T.w('l10', 'skin');
    cue(tsk, 'stretch', 0.35, [0.8]); cue(tsk + 0.05, 'pop', 0.45);
    shots.push({
      t0, t1, push: 0.08,
      cam: camKeys([[t0, { x: 540, y: 1000, z: 1.15 }]]),
      draw(lt, t) {
        let s = spaceBg(t, 'g');
        const wob = 1 + 0.025 * Math.sin(t * 9);
        const st = pose(Object.assign({ x: 540, y: 1520, s: 0.85, fat: 1.0 * wob, blush: 1 }, floaty(t, 5, 0.4)), 'worried', t, 7);
        s += rusty(st);
        // tension marks around the bloated body
        for (const [px, py, a] of [[300, 980, 200], [790, 980, -20], [330, 1300, 160], [760, 1300, 20]]) {
          s += G(tr(px, py, a), L(0, -20, 40, -30, { stroke: INK, 'stroke-width': 7, 'stroke-linecap': 'round' }), L(6, 10, 50, 10, { stroke: INK, 'stroke-width': 7, 'stroke-linecap': 'round' }));
        }
        const pa = prog(t, tsk - 0.1, tsk + 0.25, E.outCubic);
        s += fx.arrow([820, 560], [lerp(820, 740, pa), lerp(560, 850, pa)], pa > 0 ? 1 : 0, { color: '#FFE04A', curve: -0.2 });
        if (t > tsk) {
          const k = fx.popIn(t, tsk, 0.35);
          s += text('SKIN', { x: 780, y: 470, size: 120, sx: k, sy: k, rot: 6, fill: '#F8C48B' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S9 15 seconds, passes out
  {
    const t0 = cut('l11'), t1 = cut('l12'), tfi = T.w('l11', 'fifteen'), tpo = T.w('l11', 'passes');
    cue(t0 + 0.1, 'clock', 0.4, [tfi - t0 + 0.5, 4]); cue(tfi + 0.4, 'ding', 0.4); cue(tpo, 'slide_down', 0.35, [0.7]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = spaceBg(t, 'h');
        const out = t > tpo;
        const fat = 0.85;
        const st = pose(Object.assign({ x: 470, y: 1560, s: 0.8, fat }, floaty(t, 6, out ? 0.4 : 1)), out ? { mouth: 'O', mouthOpen: 0.3, eyes: 'closed', brow: 0.2 } : 'sleepy', t, 8);
        if (!out) { st.eyes = 'normal'; st.eyeOpen = kf(t, [[t0, 1], [tpo, 0.35]]); st.mouth = 'wavy'; }
        if (out) st.rot = kf(t, [[tpo, 0], [t1, -25]]);
        s += rusty(st);
        if (out) {
          // stars orbiting the head
          for (let i = 0; i < 3; i++) {
            const a = t * 4 + (i * Math.PI * 2) / 3;
            s += fx.sparkle(470 + Math.cos(a) * 170, 1560 - 1080 * 0.8 + Math.sin(a) * 50, 30, '#FFE45C', t * 200);
          }
        }
        const secs = Math.min(15, kf(t, [[t0, 0], [tfi + 0.4, 15, E.inOutSine]]));
        s += pr.stopwatch(820, 520, 0.85, { frac: secs / 60 });
        s += text(Math.round(secs) + ' SEC', { x: 820, y: 820, size: 90, fill: '#FFE45C' });
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S10 friend reels him in within 90 seconds
  {
    const t0 = cut('l12'), t1 = cut('l13'), tf = T.w('l12', 'friend'), tp = T.w('l12', 'pulls'), tn = T.w('l12', 'ninety');
    cue(tf, 'pop', 0.45); cue(tp, 'whoosh', 0.45, [1.2]); cue(tn, 'ding', 0.4, [0.8]);
    shots.push({
      t0, t1, push: 0.05,
      draw(lt, t) {
        let s = spaceBg(t, 'i');
        s += pr.station(330, 1000, { s: 0.9, doorOpen: 1 });
        // friend in the hatch
        const fpull = Math.sin(Math.max(0, t - tp) * 7) * 30;
        const fx_ = 300, fy = 1260;
        const fs = pose(Object.assign({ x: fx_, y: fy, s: 0.55, handR: [260 - fpull, -640], handL: [200 + fpull, -600], handPoseR: 'fist', handPoseL: 'fist', bendR: 1, bendL: 1 }, pr.friendBase), t > tp ? 'angry' : 'shocked', t, 40);
        s += rusty(fs);
        // Rusty being reeled in
        const rx = kf(t, [[t0, 820], [tp, 820], [t1, 560, E.inOutCubic]]), ry = kf(t, [[t0, 1500], [t1, 1350]]);
        const st = pose(Object.assign({ x: rx, y: ry, s: 0.72, fat: 0.8 }, floaty(t, 7, 0.4)), { mouth: 'O', mouthOpen: 0.3, eyes: 'closed' }, t, 9);
        st.rot = -25 + Math.sin(t) * 5;
        s += rusty(st);
        // rope from friend's hand to Rusty's waist
        const hand = [fx_ + 260 * 0.55, fy - 640 * 0.55], waist = [rx, ry - 420 * 0.72];
        s += P(`M${n2(hand[0])},${n2(hand[1])} Q${n2((hand[0] + waist[0]) / 2)},${n2(Math.max(hand[1], waist[1]) + 80 - (t > tp ? 70 : 0))} ${n2(waist[0])},${n2(waist[1])}`, { fill: 'none', stroke: INK, 'stroke-width': 16, 'stroke-linecap': 'round' }) +
          P(`M${n2(hand[0])},${n2(hand[1])} Q${n2((hand[0] + waist[0]) / 2)},${n2(Math.max(hand[1], waist[1]) + 80 - (t > tp ? 70 : 0))} ${n2(waist[0])},${n2(waist[1])}`, { fill: 'none', stroke: '#F2C14E', 'stroke-width': 8, 'stroke-linecap': 'round' });
        const k = fx.popIn(t, tn, 0.4);
        if (k > 0) {
          s += pr.stopwatch(820, 470, 0.6 * k, { frac: 0.25, ring: '#3CC86B' });
          s += text('< 90 SEC', { x: 820, y: 690, size: 92, sx: k, sy: k, fill: '#7CFF9E' });
        }
        return s;
      },
    });
  }

  // ------------------------------------------------------------- S11 survives, sunburned
  {
    const t0 = cut('l13'), t1 = duration, tsv = T.w('l13', 'survive'), tsb = T.w('l14', 'sunburn');
    cue(tsv, 'chime', 0.45); cue(tsb, 'sizzle', 0.45, [0.8]); cue(tsb, 'boing', 0.35, [1.2]);
    shots.push({
      t0, t1, push: 0.06,
      draw(lt, t) {
        let s = pr.shipInterior(t);
        const burnt = prog(t, tsb, tsb + 0.3);
        const st = pose({ x: 540, y: 1720, s: 1.0, skinTint: '#FF3A2A', skinTintAmt: 0.7 * burnt, blush: burnt }, t > tsb ? 'pain' : t > tsv ? 'proud' : 'dizzy', t, 10);
        if (t > tsv && t < tsb) { st.handR = [190, -560]; st.handPoseR = 'thumb'; st.bendR = -1; }
        if (t > tsb) { st.handL = [-120, -980]; st.handR = [120, -980]; st.bendL = 1; st.bendR = -1; }
        s += rusty(st);
        if (t > tsb) s += fx.puffs(t, tsb, 540, 1720 - 900, { n: 6, spread: 200, rise: 260, size: 36, dur: 1.2, color: '#ffffff', stroke: '#C9D9F0', seed: 3 });
        const k = fx.popIn(t, tsv, 0.4), k2 = fx.popIn(t, tsb, 0.4);
        if (k > 0) s += text('SURVIVED!', { x: 540, y: 330, size: 150, sx: k, sy: k, rot: -3, fill: '#7CFF9E' });
        if (k2 > 0) s += text('+ SUNBURN', { x: 540, y: 500, size: 110, sx: k2, sy: k2, rot: 3, fill: '#FF7B5C' });
        return s;
      },
    });
  }

  const tl = timeline(shots, duration);
  return { duration, frame: tl.frame, cues };
};
