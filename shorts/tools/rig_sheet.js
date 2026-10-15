const { png } = require('./still');
const { rusty, pose } = require('../lib/rusty');
const { BG } = require('../lib/bg');
const out = require('path').join(__dirname, '..', 'build', '');
require('fs').mkdirSync(out, { recursive: true });
let s = BG.blue();
s += rusty(pose({ x: 540, y: 1700, s: 1.25 }, 'happy', 0.5));
png(s, require('path').join(out, 'rig_full.png'));
let sh = BG.blue();
const poses = [
  [{}, 'happy'],
  [{ handL: [-230, -820], handR: [230, -820], handPoseL: 'spread', handPoseR: 'spread' }, 'scared'],
  [{ handL: [-250, -560], handR: [250, -560], bendL: -1, bendR: 1 }, 'worried'],
  [{ fat: 1, handL: [-300, -420], handR: [300, -420] }, 'shocked'],
  [{ hair: 1 }, 'pain'],
  [{ xray: true }, 'shocked'],
  [{ socks: true, footL: [-80, -40], footR: [70, -10] }, 'curious'],
  [{ handR: [60, -800], handPoseR: 'point', handL: [-120, -420], handPoseL: 'fist' }, 'smug'],
  [{ sx: 0.7, sy: 1.6 }, 'scared'],
];
poses.forEach(([b, e], i) => {
  const x = 180 + (i % 3) * 360, y = 600 + Math.floor(i / 3) * 620;
  sh += rusty(pose(Object.assign({ x, y, s: 0.42 }, b), e, 0.5));
});
png(sh, require('path').join(out, 'rig_poses.png'));
