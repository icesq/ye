"""Final audio mix: narration + ducked music bed + timed SFX, loudness-normalized.

Usage: python mix.py <build_dir> <style> <seed> [music_gain]
Reads build_dir/narration.wav, build_dir/cues.json, build_dir/timing.json; writes build_dir/mix.wav
"""
import json, os, subprocess, sys, tempfile
import numpy as np
import soundfile as sf
import sfx
import music

SR = sfx.SR


def ffmpeg_filter(inp, out, af):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", inp, "-af", af, "-ar", str(SR), "-ac", "1", out], check=True)


def envelope(x, win=0.05):
    n = int(win * SR)
    e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))
    return e


def smooth_gate(active, att=0.04, rel=0.35):
    g = np.zeros_like(active)
    a = 1 - np.exp(-1 / (att * SR))
    r = 1 - np.exp(-1 / (rel * SR))
    v = 0.0
    # vectorize by downsampling to 1 ms blocks
    blk = SR // 1000
    act = active[::blk]
    out = np.zeros_like(act)
    a = 1 - np.exp(-1 / (att * 1000))
    r = 1 - np.exp(-1 / (rel * 1000))
    for i, x in enumerate(act):
        v += (x - v) * (a if x > v else r)
        out[i] = v
    return np.repeat(out, blk)[: len(active)]


def main():
    bd, style, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    mgain = float(sys.argv[4]) if len(sys.argv) > 4 else 0.22
    timing = json.load(open(os.path.join(bd, "timing.json")))
    cues = json.load(open(os.path.join(bd, "cues.json")))
    dur = cues.get("duration", timing["duration"])
    n = int(dur * SR)

    # narration: resample + gentle voice chain
    with tempfile.TemporaryDirectory() as td:
        vpath = os.path.join(td, "v.wav")
        ffmpeg_filter(os.path.join(bd, "narration.wav"), vpath,
                      "aresample=44100:resampler=soxr,highpass=f=75,equalizer=f=200:t=q:w=1:g=1.5,equalizer=f=3800:t=q:w=1.2:g=2.5,"
                      "acompressor=threshold=-22dB:ratio=3:attack=4:release=90:makeup=3dB,alimiter=limit=0.9")
        voice, _ = sf.read(vpath, dtype="float32")
    v = np.zeros(n, np.float32)
    v[: min(n, len(voice))] = voice[:n]

    # music, with ducking under voice
    stops = [tuple(s) for s in cues.get("musicStops", [])]
    m = music.compose(dur, style=style, seed=seed, stops=stops)
    m = np.pad(m, (0, max(0, n - len(m))))[:n]
    env = envelope(v)
    active = (env > 0.02).astype(np.float32)
    duck = smooth_gate(active)
    m_gain = mgain * (1 - 0.5 * duck)

    # sfx
    fx = np.zeros(n + SR * 4, np.float32)
    cache = {}
    for c in cues["cues"]:
        name = c["sfx"]
        args = tuple(c.get("args", []))
        key = (name, args)
        if key not in cache:
            cache[key] = sfx.LIB[name](*args)
        x = cache[key] * c.get("gain", 0.5)
        o = int(c["t"] * SR)
        if o < 0 or o >= n:
            continue
        fx[o: o + len(x)] += x
    fx = fx[:n]

    L = v * 1.0 + fx * 0.9 + m * m_gain
    R = L.copy()
    # widen music slightly with a Haas delay on the right channel
    d = int(0.012 * SR)
    R[d:] = (v * 1.0 + fx * 0.9)[d:] + (m * m_gain)[:-d]
    st = np.stack([L, R], axis=1)
    pre = os.path.join(bd, "premix.wav")
    sf.write(pre, st, SR)
    # loudness normalize for YouTube (-14 LUFS, -1 dBTP)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.2:LRA=9", "-ar", str(SR), os.path.join(bd, "mix.wav")], check=True)
    print("mix ok", round(dur, 2), "s")


if __name__ == "__main__":
    main()
