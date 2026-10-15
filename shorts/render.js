#!/usr/bin/env node
// Frame renderer: video module -> SVG per frame -> resvg -> raw RGBA -> ffmpeg.
//   node render.js <name>                     full render (parallel workers) -> out/<name>.mp4
//   node render.js <name> --stills 1.2,3.4    preview PNGs in build/<name>/stills
//   node render.js <name> --sheet 24          contact sheet of 24 frames
'use strict';
const fs = require('fs');
const path = require('path');
const { spawn, fork } = require('child_process');
const { Resvg } = require('@resvg/resvg-js');
const { timingHelper } = require('./lib/scene');

const FPS = 30, W = 1080, H = 1920;
const args = process.argv.slice(2);
const name = args[0];
const opt = k => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : null; };
const bd = path.join(__dirname, 'build', name);
const outDir = path.join(__dirname, 'out');

function load() {
  const timing = JSON.parse(fs.readFileSync(path.join(bd, 'timing.json'), 'utf8'));
  const T = timingHelper(timing);
  const mod = require(path.join(__dirname, 'videos', name + '.js'));
  return mod(T);
}

function svgDoc(inner, scale = 1) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W * scale}" height="${H * scale}" viewBox="0 0 ${W} ${H}">${inner}</svg>`;
}
function raster(inner, scale = 1) {
  const r = new Resvg(svgDoc(inner), { font: { loadSystemFonts: false }, fitTo: { mode: 'width', value: Math.round(W * scale) } });
  return r.render();
}

async function renderSegment(v, f0, f1, file) {
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-g', String(FPS * 2), file], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = f0; f < f1; f++) {
    const img = raster(v.frame(f / FPS));
    if (!ff.stdin.write(Buffer.from(img.pixels))) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
}

async function main() {
  if (process.env.SEGMENT) {
    const [f0, f1, file] = process.env.SEGMENT.split(':');
    const v = load();
    await renderSegment(v, +f0, +f1, file);
    process.exit(0);
  }
  const v = load();
  const duration = v.duration;
  fs.mkdirSync(bd, { recursive: true });
  fs.writeFileSync(path.join(bd, 'cues.json'), JSON.stringify({ duration, cues: v.cues || [], musicStops: v.musicStops || [] }, null, 1));

  if (opt('stills')) {
    const dir = path.join(bd, 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const ts of opt('stills').split(',')) {
      const t = parseFloat(ts);
      fs.writeFileSync(path.join(dir, `t${t.toFixed(2)}.png`), raster(v.frame(t), 0.5).asPng());
    }
    console.log('stills ->', dir);
    return;
  }
  if (opt('sheet')) {
    const n = +opt('sheet'), cols = 6, sc = 0.2;
    const dir = path.join(bd, 'stills'); fs.mkdirSync(dir, { recursive: true });
    const t0 = opt('from') ? +opt('from') : 0, t1 = opt('to') ? +opt('to') : duration;
    const files = [];
    for (let i = 0; i < n; i++) {
      const t = t0 + ((i + 0.5) * (t1 - t0)) / n;
      const f = path.join(dir, `s${String(i).padStart(2, '0')}.png`);
      fs.writeFileSync(f, raster(v.frame(t), sc).asPng());
      files.push(f);
    }
    const rows = Math.ceil(n / cols);
    await new Promise((res, rej) => {
      const p = spawn('ffmpeg', ['-v', 'error', '-y', '-i', path.join(dir, 's%02d.png'), '-vf', `tile=${cols}x${rows}:padding=4:color=white`, '-frames:v', '1', path.join(bd, 'sheet.png')], { stdio: 'inherit' });
      p.on('close', c => (c ? rej(c) : res()));
    });
    console.log('sheet ->', path.join(bd, 'sheet.png'));
    return;
  }

  // full parallel render
  const total = Math.ceil(duration * FPS);
  const workers = +(opt('workers') || 4);
  const per = Math.ceil(total / workers);
  const segs = [];
  const t = Date.now();
  await Promise.all(Array.from({ length: workers }, (_, k) => {
    const f0 = k * per, f1 = Math.min(total, (k + 1) * per);
    const file = path.join(bd, `seg${k}.mp4`);
    segs.push(file);
    return new Promise((res, rej) => {
      const p = fork(__filename, [name], { env: { ...process.env, SEGMENT: `${f0}:${f1}:${file}` } });
      p.on('exit', c => (c === 0 ? res() : rej(new Error('worker ' + k + ' failed'))));
    });
  }));
  console.log(`rendered ${total} frames in ${((Date.now() - t) / 1000).toFixed(1)}s`);
  fs.writeFileSync(path.join(bd, 'segs.txt'), segs.map(s => `file '${s}'`).join('\n'));
  const video = path.join(bd, 'video.mp4');
  await run('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(bd, 'segs.txt'), '-c', 'copy', video]);
  const mix = path.join(bd, 'mix.wav');
  if (fs.existsSync(mix)) {
    fs.mkdirSync(outDir, { recursive: true });
    const out = path.join(outDir, name + '.mp4');
    await run('ffmpeg', ['-v', 'error', '-y', '-i', video, '-i', mix, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]);
    console.log('final ->', out);
  } else console.log('video only ->', video, '(no mix.wav yet)');
}

function run(cmd, a) {
  return new Promise((res, rej) => { const p = spawn(cmd, a, { stdio: 'inherit' }); p.on('close', c => (c ? rej(new Error(cmd + ' ' + c)) : res())); });
}

main().catch(e => { console.error(e); process.exit(1); });
