"""Tiny procedural music sequencer for light, quirky background tracks."""
import numpy as np
from sfx import SR, noise, lowpass, highpass, norm

rng = np.random.default_rng(7)

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(f, d=0.6, bright=0.5, gain=1.0):
    """Karplus-Strong plucked string (pizzicato-ish)."""
    n = int(d * SR)
    p = max(2, int(SR / f))
    buf = (rng.random(p) * 2 - 1).astype(np.float32)
    # soften initial burst
    buf = np.convolve(buf, np.ones(3) / 3, mode="same").astype(np.float32)
    out = np.zeros(n, np.float32)
    decay = 0.996 - (1 - bright) * 0.006
    idx = 0
    for i in range(n):
        v = buf[idx]
        nxt = buf[(idx + 1) % p]
        buf[idx] = decay * 0.5 * (v + nxt)
        out[i] = v
        idx = (idx + 1) % p
    out *= np.minimum(1, (n - np.arange(n)) / (0.03 * SR))
    return out * gain


def marimba(f, d=0.5, gain=1.0):
    t = np.arange(int(d * SR)) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-6 * t) + 0.35 * np.sin(2 * np.pi * f * 3.9 * t) * np.exp(-18 * t) + 0.12 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-40 * t)
    x *= np.minimum(1, t / 0.002)
    return (x * gain).astype(np.float32)


def glock(f, d=1.0, gain=1.0):
    t = np.arange(int(d * SR)) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-3.5 * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-7 * t) + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-12 * t)
    x *= np.minimum(1, t / 0.001)
    return (x * gain).astype(np.float32)


def bass(f, d=0.35, gain=1.0):
    t = np.arange(int(d * SR)) / SR
    ph = 2 * np.pi * f * t
    x = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    x *= np.minimum(1, t / 0.005) * np.exp(-3.5 * t) * np.minimum(1, (d - t) / 0.03)
    return (x * gain).astype(np.float32)


def pad(freqs, d, gain=1.0):
    t = np.arange(int(d * SR)) / SR
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.25, 0.0, 0.25):
            ff = f * 2 ** (det / 12)
            x += np.sign(np.sin(2 * np.pi * ff * t + rng.random() * 6)) * 0.3
    x = lowpass(x.astype(np.float32), 1200)
    x *= np.minimum(1, t / 0.5) * np.minimum(1, (d - t) / 0.5)
    return (x / max(1, len(freqs)) * gain).astype(np.float32)


def kick(gain=1.0):
    d = 0.3
    t = np.arange(int(d * SR)) / SR
    f = 50 + 110 * np.exp(-30 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-9 * t)
    return (x * gain).astype(np.float32)


def snap(gain=1.0):
    d = 0.15
    t = np.arange(int(d * SR)) / SR
    x = highpass(noise(d), 1200) * np.exp(-30 * t)
    return (x * gain).astype(np.float32)


def shaker(gain=1.0):
    d = 0.06
    t = np.arange(int(d * SR)) / SR
    x = highpass(noise(d), 6000) * np.exp(-60 * t) * np.minimum(1, t / 0.004)
    return (x * gain).astype(np.float32)


def reverb(x, secs=1.3, mix=0.18):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = (rng.standard_normal(n) * np.exp(-4.5 * t / secs)).astype(np.float32)
    ir = lowpass(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    N = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]
    return ((1 - mix) * x + mix * y * 3).astype(np.float32)


def place(buf, x, t):
    o = int(t * SR)
    if o >= len(buf):
        return
    e = min(len(buf), o + len(x))
    buf[o:e] += x[: e - o]


CHORDS = {  # semitone offsets from key root
    "I": [0, 4, 7], "ii": [2, 5, 9], "iii": [4, 7, 11], "IV": [5, 9, 12], "V": [7, 11, 14], "vi": [9, 12, 16],
    "i": [0, 3, 7], "iv": [5, 8, 12], "v": [7, 10, 14], "VI": [8, 12, 15], "III": [3, 7, 10], "VII": [10, 14, 17], "bII": [1, 5, 8],
    "V7": [7, 11, 14, 17], "III7": [4, 8, 11, 14],
}

STYLES = {
    "quirky": dict(bpm=116, key="F", prog=["I", "vi", "IV", "V"], scale=[0, 2, 4, 5, 7, 9, 11], lead="pluck", drums=True),
    "bouncy": dict(bpm=124, key="G", prog=["I", "III7", "IV", "iv"], scale=[0, 2, 4, 5, 7, 9, 11], lead="marimba", drums=True),
    "curious": dict(bpm=108, key="D", prog=["I", "IV", "vi", "V"], scale=[0, 2, 4, 7, 9], lead="marimba", drums=True),
    "mystery": dict(bpm=92, key="A", prog=["i", "VI", "III", "VII"], scale=[0, 2, 3, 5, 7, 8, 10], lead="glock", drums=False),
    "tense": dict(bpm=120, key="E", prog=["i", "iv", "VI", "V"], scale=[0, 2, 3, 5, 7, 8, 11], lead="pluck", drums=True),
}


def compose(duration, style="quirky", seed=1, stops=()):
    """Return a stereo-ready mono music bed. `stops` = list of (t0, t1) to drop out (for comedic pauses)."""
    global rng
    rng = np.random.default_rng(seed)
    S = STYLES[style]
    bpm = S["bpm"]
    beat = 60 / bpm
    root = 48 + NOTE[S["key"]]
    n = int((duration + 2) * SR)
    mel, harm, low, drm = (np.zeros(n, np.float32) for _ in range(4))
    bars = int(duration / (4 * beat)) + 2
    # a 1-bar rhythmic motif, reused with pitch variation
    motif = [0, 0.75, 1.5, 2, 2.5, 3.25] if style != "mystery" else [0, 1.5, 2, 3]
    contour = rng.integers(0, 5, size=len(motif))
    scale = S["scale"]
    lead = {"pluck": pluck, "marimba": marimba, "glock": glock}[S["lead"]]
    for b in range(bars):
        ch = CHORDS[S["prog"][b % len(S["prog"])]]
        t0 = b * 4 * beat
        # bass
        if style == "mystery":
            place(low, bass(midi_hz(root - 12 + ch[0]), 4 * beat, 0.9), t0)
            place(harm, pad([midi_hz(root + c) for c in ch], 4 * beat + 0.4, 0.5), t0)
        else:
            for k, (bt, off) in enumerate([(0, 0), (1.5, 12), (2, 7), (3, 0)]):
                place(low, bass(midi_hz(root - 12 + ch[0] + off), 0.32, 0.9 if k == 0 else 0.7), t0 + bt * beat)
            # off-beat chord stabs
            for bt in (0.5, 1.5, 2.5, 3.5):
                for c in ch[:3]:
                    place(harm, pluck(midi_hz(root + 12 + c), 0.25, 0.3, 0.18), t0 + bt * beat)
        # melody: phrase A A' B A''
        phrase = b % 4
        for i, mt in enumerate(motif):
            if phrase == 3 and i > 3:
                continue
            deg = (contour[i] + (phrase == 2) * 2 + (b // 4) % 2) % len(scale)
            # snap to chord tone on strong beats
            if mt in (0, 2):
                pitch = root + 12 + ch[i % len(ch)]
            else:
                pitch = root + 12 + scale[deg]
            g = 0.5 if S["lead"] != "glock" else 0.35
            dur = 0.5 if S["lead"] != "glock" else 1.2
            place(mel, lead(midi_hz(pitch + 12), dur, gain=g), t0 + mt * beat)
        # drums
        if S["drums"]:
            for bt in (0, 2):
                place(drm, kick(0.75), t0 + bt * beat)
            for bt in (1, 3):
                place(drm, snap(0.22), t0 + bt * beat)
            for k in range(8):
                place(drm, shaker(0.12 if k % 2 else 0.07), t0 + k * 0.5 * beat)
    mix = 0.9 * mel + 0.6 * harm + 0.8 * low + 0.7 * drm
    mix = reverb(mix, 1.2, 0.16)[: int(duration * SR)]
    # drop-outs
    t = np.arange(len(mix)) / SR
    g = np.ones_like(mix)
    for a, b in stops:
        g *= 1 - np.clip(np.minimum((t - a) / 0.05, (b - t) / 0.2), 0, 1)
    mix *= g
    # fade in/out
    fi, fo = int(0.05 * SR), int(1.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    return norm(mix, 0.8)
