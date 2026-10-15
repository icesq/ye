// Shot timeline, camera, and timing helpers shared by every video.
'use strict';
const { clamp, lerp, E, prog, noise, n2, R, interp } = require('./core');

const W = 1080, H = 1920;

// timing helper built from tts timing.json
function timingHelper(timing) {
  const byId = {};
  for (const l of timing.lines) byId[l.id] = l;
  const line = id => {
    if (!byId[id]) throw new Error('no line ' + id);
    return byId[id];
  };
  const T = {
    duration: timing.duration,
    s: id => line(id).s,
    e: id => line(id).e,
    // start of the word inside a line: by index or by (case-insensitive) prefix match
    w: (id, which, end = false) => {
      const l = line(id);
      let wd;
      if (typeof which === 'number') wd = l.words[Math.min(which, l.words.length - 1)];
      else {
        const k = which.toLowerCase();
        wd = l.words.find(x => x.w.toLowerCase().replace(/[^a-z0-9']/g, '').startsWith(k));
        if (!wd) throw new Error(`word "${which}" not in ${id}: ${l.text}`);
      }
      return end ? wd.e : wd.s;
    },
    lines: timing.lines,
  };
  return T;
}

// camera shake offset
function shake(t, t0, dur = 0.4, amp = 20, seed = 1) {
  const p = (t - t0) / dur;
  if (p < 0 || p > 1) return [0, 0];
  const k = amp * Math.pow(1 - p, 2);
  return [noise(t * 40, seed) * k, noise(t * 40, seed + 9) * k];
}

// white (or any) flash overlay
function flash(t, t0, dur = 0.25, color = '#ffffff', peak = 1) {
  const p = (t - t0) / dur;
  if (p < 0 || p > 1) return '';
  const a = peak * Math.pow(1 - p, 2);
  return R(-100, -100, W + 200, H + 200, { fill: color, opacity: n2(a) });
}

function camWrap(content, cam) {
  const { x = 0, y = 0, z = 1, r = 0 } = cam;
  return `<g transform="translate(${n2(W / 2)} ${n2(H / 2)}) rotate(${n2(r)}) scale(${n2(z)}) translate(${n2(-W / 2 - x)} ${n2(-H / 2 - y)})">${content}</g>`;
}

/*
 shots: [{ t0, t1?, draw(lt, t, shot) -> svg, cam?(lt, dur) -> {x,y,z,r}, push?: number, punch?: number, shakes?: [[t, dur, amp]], flashes?: [[t, dur, color]] }]
 t1 defaults to next shot t0. Times are absolute seconds.
*/
function timeline(shots, duration) {
  shots.sort((a, b) => a.t0 - b.t0);
  for (let i = 0; i < shots.length; i++) if (shots[i].t1 == null) shots[i].t1 = i + 1 < shots.length ? shots[i + 1].t0 : duration;
  const overlays = [];
  const frame = t => {
    let idx = shots.findIndex(s => t >= s.t0 && t < s.t1);
    if (idx < 0) idx = t < shots[0].t0 ? 0 : shots.length - 1;
    const s = shots[idx];
    const lt = t - s.t0, dur = s.t1 - s.t0;
    let content = s.draw(lt, t, s, dur);
    let cam = s.cam ? s.cam(lt, dur, t) : {};
    const push = s.push ?? 0.05;
    const punch = s.punch ?? 0.035;
    const z0 = (cam.z ?? 1) * (1 + push * clamp(lt / dur)) * (1 + punch * (1 - E.outCubic(clamp(lt / 0.35))));
    let sx = 0, sy = 0;
    for (const [st, sd, sa] of s.shakes || []) {
      const [a, b] = shake(t, st, sd, sa, Math.round(st * 10));
      sx += a; sy += b;
    }
    content = camWrap(content, { x: (cam.x || 0) + sx, y: (cam.y || 0) + sy, z: z0, r: cam.r || 0 });
    for (const [ft, fd, fc, fp] of s.flashes || []) content += flash(t, ft, fd, fc, fp);
    for (const o of overlays) content += o(t);
    return content;
  };
  return { frame, shots, overlay: fn => overlays.push(fn) };
}

// camera keys: [[tAbs, {x, y, z}, tweenDur = 0 (hard cut), ease]]; x/y = point to center on (frame coords)
function camKeys(keys) {
  return (lt, dur, t) => {
    let c = { x: 540, y: 960, z: 1 };
    for (const [kt, v, d = 0, ease = E.inOutCubic] of keys) {
      if (t < kt) break;
      const p = d ? ease(clamp((t - kt) / d)) : 1;
      c = interp(c, Object.assign({ x: 540, y: 960, z: 1 }, v), p);
    }
    return { x: c.x - 540, y: c.y - 960, z: c.z };
  };
}

module.exports = { W, H, timingHelper, timeline, shake, flash, camWrap, camKeys };
