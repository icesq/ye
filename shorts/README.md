# Rusty Shorts — генератор мультяшных YouTube Shorts

Главный герой — **Rusty (Расти)**: добродушный рыжий парень в бирюзовой футболке и красных штанах.
Закадровый голос отправляет его в абсурдные и смертельно опасные ситуации и по ходу объясняет,
как устроены физика, мир и человеческое тело.

Готовые ролики (1080×1920, 30 fps, H.264 + AAC, −14 LUFS) лежат в `out/`:

| Файл | Тема | Длина |
|---|---|---|
| `out/v1_lightning.mp4` | What if lightning hit you? | 32.6 s |
| `out/v2_space.mp4` | Space without a spacesuit | 32.6 s |
| `out/v3_water.mp4` | Drinking too much water | 31.8 s |
| `out/v4_blackhole.mp4` | Falling into a black hole | 27.5 s |
| `out/v5_tunnel.mp4` | A tunnel through the Earth | 32.5 s |

## Как это устроено

Всё генерируется кодом: внешних видео-ИИ, стоков или клипарта нет.

```
scripts/vN.json ──► audio/tts.py ──► build/vN/narration.wav + timing.json (тайминг каждого слова)
                                          │
videos/vN.js (сцены, анимация, SFX-метки) ◄┘
      │
      ├─► render.js ──► SVG на каждый кадр ──► resvg ──► ffmpeg (4 потока параллельно)
      └─► build/vN/cues.json ──► audio/mix.py (голос + музыка с даккингом + SFX, loudnorm)
                                          │
                               out/vN.mp4 ◄┘
```

- **Голос** — нейросетевой TTS Kokoro (голос `am_fenrir`). Из ONNX-графа модели достаются длительности
  фонем, поэтому анимация, надписи и звуки привязаны к конкретным словам.
- **Персонаж** — векторный риг (`lib/rusty.js`): IK для рук и ног в стиле «резиновых» конечностей, ~20 эмоций,
  моргание и дыхание, наэлектризованные волосы, рентген-скелет, раздувание, растяжение, тонировка (загар, сажа).
- **Анимация** — `lib/core.js` (easing, ключевые кадры), `lib/scene.js` (камера, зум-каты, тряска, вспышки),
  `lib/fx.js` (дым, искры, линии удара, стрелки), `lib/props.js` (молния, Солнце, сердце, ЭКГ, станция, Земля…).
- **Звук** — процедурные SFX (`audio/sfx.py`: гром, разряд, вжух, поп, буль, тиканье…) и процедурная музыка
  (`audio/music.py`: щипковые, маримба, бас, лёгкие ударные; 5 стилей).

## Пересборка

Нужны Node 18+, Python 3.10+, ffmpeg.

```bash
npm install
python3 -m venv .venv && . .venv/bin/activate
pip install kokoro-onnx onnx soundfile numpy

# модели TTS (GitHub Releases kokoro-onnx), ~350 МБ
mkdir -p models
curl -L -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o models/voices-v1.0.bin  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

PY=.venv/bin/python ./make.sh              # все пять роликов
PY=.venv/bin/python ./make.sh v1_lightning # только один
VOICE=af_heart ./make.sh v2_space          # другой голос
```

Предпросмотр без полного рендера:

```bash
node render.js v1_lightning --sheet 30         # контактный лист 30 кадров -> build/v1_lightning/sheet.png
node render.js v1_lightning --stills 0.9,3.4   # отдельные кадры -> build/v1_lightning/stills/
```

## Новый ролик

1. `scripts/v6_xxx.json` — текст по строкам (`id`, `text`, опционально `say` для произношения, `pause`) и стиль музыки.
2. `videos/v6_xxx.js` — список планов; время берётся из озвучки: `T.s('l3')` — начало строки,
   `T.w('l3', 'volts')` — начало слова. Звуки: `cue(t, 'zap', 0.5)`.
3. `./make.sh v6_xxx`.

Шрифты: Luckiest Guy (Apache 2.0), Lilita One и Bangers (SIL OFL) — `assets/fonts/`.
