"""Narration generator: Kokoro TTS with per-word timings.

Usage: python tts.py <script.json> <out_dir> [voice] [speed]

script.json: {"lines": [{"id": "l1", "text": "...", "pause": 0.25}, ...]}
Writes <out_dir>/narration.wav (24 kHz mono) and <out_dir>/timing.json with
absolute start/end per line and per word, so the animation can sync to speech.
"""
import json, os, re, sys
import numpy as np
import onnx
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro

MODELS = os.environ.get("KOKORO_DIR", os.path.join(os.path.dirname(__file__), "..", "models"))
SR = 24000
HOP = 600  # samples per duration unit


def duration_model(path_in, path_out):
    """Expose the encoder's per-token durations as an extra output of the graph."""
    if not os.path.exists(path_out):
        m = onnx.load(path_in)
        m.graph.output.append(onnx.helper.make_tensor_value_info(
            "/encoder/Gather_output_0", onnx.TensorProto.INT64, None))
        onnx.save(m, path_out)
    return ort.InferenceSession(path_out, providers=["CPUExecutionProvider"])


def words_of(text):
    return re.findall(r"[A-Za-z0-9'’,.\-%°]+", text)


def synth(k, sess, text, voice, speed):
    ph = k.tokenizer.phonemize(text, "en-us")
    vocab = k.tokenizer.vocab
    chars = [c for c in ph if c in vocab]
    toks = [vocab[c] for c in chars]
    style = k.get_voice_style(voice)[len(toks)]
    audio, dur = sess.run(["audio", "/encoder/Gather_output_0"], {
        "tokens": np.array([[0, *toks, 0]], dtype=np.int64),
        "style": style,
        "speed": np.array([speed], dtype=np.float32)})
    dur = dur.astype(np.int64)
    # dur[0] is the start pad, dur[1:-1] map to chars
    t = dur[0] * HOP / SR
    spans, cur = [], None
    for c, d in zip(chars, dur[1:-1]):
        d = d * HOP / SR
        if c == " ":
            if cur: spans.append(cur); cur = None
        elif c in ".,!?;:—…\"":
            if cur: cur[1] = t  # punctuation pause belongs to gap
        else:
            if cur is None: cur = [t, t + d]
            else: cur[1] = t + d
        t += d
    if cur: spans.append(cur)
    return audio, spans, ph


def main():
    script, out = sys.argv[1], sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "am_michael"
    speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.1
    os.makedirs(out, exist_ok=True)
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    sess = duration_model(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "kokoro-dur.onnx"))
    spec = json.load(open(script))
    lead = spec.get("lead", 0.15)
    chunks, timing, t = [np.zeros(int(lead * SR), np.float32)], [], lead
    for line in spec["lines"]:
        audio, spans, ph = synth(k, sess, line.get("say", line["text"]), line.get("voice", voice), line.get("speed", speed))
        # trim leading/trailing silence so pauses are under our control
        env = np.abs(audio) > 0.01
        idx = np.nonzero(env)[0]
        a0, a1 = (max(0, idx[0] - 240), min(len(audio), idx[-1] + 1200)) if len(idx) else (0, len(audio))
        audio = audio[a0:a1]
        off = a0 / SR
        ws = words_of(line["text"])
        if len(ws) != len(spans):
            print(f"[warn] {line['id']}: {len(ws)} words vs {len(spans)} spans -> proportional map", file=sys.stderr)
            n = max(1, len(spans))
            spans = [spans[min(n - 1, int(i * n / len(ws)))] for i in range(len(ws))]
        words = [{"w": w, "s": round(t + s - off, 3), "e": round(t + e - off, 3)} for w, (s, e) in zip(ws, spans)]
        d = len(audio) / SR
        timing.append({"id": line["id"], "text": line["text"], "s": round(t, 3), "e": round(t + d, 3), "words": words})
        chunks.append(audio.astype(np.float32))
        gap = line.get("pause", 0.22)
        chunks.append(np.zeros(int(gap * SR), np.float32))
        t += d + gap
        print(f"{line['id']}: {d:.2f}s  {ph}")
    tail = spec.get("tail", 1.2)
    chunks.append(np.zeros(int(tail * SR), np.float32))
    full = np.concatenate(chunks)
    sf.write(os.path.join(out, "narration.wav"), full, SR)
    json.dump({"duration": round(len(full) / SR, 3), "lines": timing}, open(os.path.join(out, "timing.json"), "w"), indent=1)
    print("total", round(len(full) / SR, 2), "s")


if __name__ == "__main__":
    main()
