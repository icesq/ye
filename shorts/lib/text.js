// Text rendered as vector paths (opentype.js), so resvg needs no font loading.
'use strict';
const fs = require('fs');
const path = require('path');
const opentype = require('opentype.js');
const { n2, tr, G, P } = require('./core');

const FONT_DIR = path.join(__dirname, '..', 'assets', 'fonts');
const load = f => { const b = fs.readFileSync(path.join(FONT_DIR, f)); return opentype.parse(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)); };
const fonts = {
  lucky: load('LuckiestGuy-Regular.ttf'),
  lilita: load('LilitaOne-Regular.ttf'),
  bangers: load('Bangers-Regular.ttf'),
};

const r1 = v => Math.round(v * 10) / 10;
function cmdsToD(cmds) {
  let d = '';
  for (const c of cmds) {
    if (c.type === 'M' || c.type === 'L') d += `${c.type}${r1(c.x)} ${r1(c.y)} `;
    else if (c.type === 'Q') d += `Q${r1(c.x1)} ${r1(c.y1)} ${r1(c.x)} ${r1(c.y)} `;
    else if (c.type === 'C') d += `C${r1(c.x1)} ${r1(c.y1)} ${r1(c.x2)} ${r1(c.y2)} ${r1(c.x)} ${r1(c.y)} `;
    else if (c.type === 'Z') d += 'Z ';
  }
  return d;
}

const cache = new Map();
// returns {d, w, h} for text laid out at size 100 with baseline at y=0, centered horizontally
function shape(str, font = 'lucky', spacing = 0) {
  const key = font + '|' + spacing + '|' + str;
  if (cache.has(key)) return cache.get(key);
  const f = fonts[font];
  const size = 100;
  let x = 0;
  const glyphs = f.stringToGlyphs(str);
  const parts = [];
  for (let i = 0; i < glyphs.length; i++) {
    const g = glyphs[i];
    const p = g.getPath(x, 0, size);
    parts.push(cmdsToD(p.commands));
    let adv = (g.advanceWidth / f.unitsPerEm) * size;
    if (i < glyphs.length - 1) adv += (f.getKerningValue(g, glyphs[i + 1]) / f.unitsPerEm) * size;
    x += adv + spacing;
  }
  const w = x - spacing;
  const capH = ((f.tables.os2 && f.tables.os2.sCapHeight) || f.unitsPerEm * 0.7) / f.unitsPerEm * size;
  const res = { d: parts.join(''), w, capH };
  cache.set(key, res);
  return res;
}

// Big outlined cartoon text. (x, y) is the center of the text block.
function text(str, o = {}) {
  const {
    x = 0, y = 0, size = 120, font = 'lucky', fill = '#FFE45C', stroke = '#2b2220', sw = 14,
    rot = 0, sx = 1, sy = 1, spacing = 2, anchor = 'middle', shadow = true, lineGap = 1.05, opacity = 1,
  } = o;
  const lines = String(str).split('\n');
  const k = size / 100;
  let out = '';
  lines.forEach((ln, i) => {
    const s = shape(ln, font, spacing);
    const ox = anchor === 'middle' ? -s.w / 2 : anchor === 'end' ? -s.w : 0;
    const oy = s.capH / 2 + (i - (lines.length - 1) / 2) * 100 * lineGap;
    const t = `translate(${n2(ox)} ${n2(oy)})`;
    const body =
      (shadow ? P(s.d, { transform: `translate(${n2(ox + 4 / k)} ${n2(oy + 7 / k)})`, fill: stroke, stroke, 'stroke-width': n2(sw / k), 'stroke-linejoin': 'round', opacity: 0.35 }) : '') +
      P(s.d, { transform: t, fill: stroke, stroke, 'stroke-width': n2(sw / k), 'stroke-linejoin': 'round' }) +
      P(s.d, { transform: t, fill });
    out += body;
  });
  const g = G(tr(x, y, rot, k * sx, k * sy), out);
  return opacity < 1 ? `<g opacity="${n2(opacity)}">${g}</g>` : g;
}

// plain text (no outline), e.g. small labels drawn on props
function label(str, o = {}) {
  const { x = 0, y = 0, size = 40, font = 'lilita', fill = '#2b2220', rot = 0, anchor = 'middle', spacing = 0, opacity = 1 } = o;
  const s = shape(str, font, spacing);
  const k = size / 100;
  const ox = anchor === 'middle' ? -s.w / 2 : anchor === 'end' ? -s.w : 0;
  return G(tr(x, y, rot, k), P(s.d, { transform: `translate(${n2(ox)} ${n2(s.capH / 2)})`, fill, opacity: opacity < 1 ? opacity : undefined }));
}

const width = (str, size = 100, font = 'lucky', spacing = 2) => (shape(str, font, spacing).w * size) / 100;

module.exports = { text, label, width, shape };
