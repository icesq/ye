// Render a single SVG string (from a module exporting frame(t)) or test sheet to PNG.
const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');
function png(svg, out, w = 1080, h = 1920, scale = 0.5) {
  const doc = svg.startsWith('<svg') ? svg : `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${svg}</svg>`;
  const r = new Resvg(doc, { font: { loadSystemFonts: false }, fitTo: { mode: 'zoom', value: scale } });
  fs.writeFileSync(out, r.render().asPng());
}
module.exports = { png };
