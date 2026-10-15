#!/usr/bin/env bash
# Full pipeline for one or more videos: narration -> cues -> audio mix -> frames -> mp4.
#   ./make.sh v1_lightning v2_space ...      (no args = all five)
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python3}
VOICE=${VOICE:-am_fenrir}
SPEED=${SPEED:-1.1}
vids=("$@")
[ ${#vids[@]} -eq 0 ] && vids=(v1_lightning v2_space v3_water v4_blackhole v5_tunnel)
for v in "${vids[@]}"; do
  echo "== $v"
  $PY audio/tts.py "scripts/$v.json" "build/$v" "$VOICE" "$SPEED"
  node render.js "$v" --stills 0 > /dev/null          # writes build/$v/cues.json
  style=$($PY -c "import json,sys;print(json.load(open('scripts/$v.json'))['music']['style'])")
  seed=$($PY -c "import json,sys;print(json.load(open('scripts/$v.json'))['music']['seed'])")
  gain=$($PY -c "import json,sys;print(json.load(open('scripts/$v.json'))['music'].get('gain',0.24))")
  (cd audio && $PY mix.py "../build/$v" "$style" "$seed" "$gain")
  node render.js "$v"
done
