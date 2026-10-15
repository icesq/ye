"""Procedural cartoon sound effects (numpy). Every effect returns float32 mono at SR."""
import numpy as np

SR = 44100
_rng = np.random.default_rng(1234)


def t_(d):
    return np.arange(int(d * SR)) / SR


def env_ad(n, a=0.005, d=None, curve=4.0):
    """attack-decay envelope over n samples"""
    t = np.arange(n) / SR
    dur = n / SR
    a = max(a, 1e-4)
    e = np.where(t < a, t / a, np.exp(-curve * (t - a) / max(dur - a, 1e-3)))
    return e.astype(np.float32)


def fade(x, fi=0.003, fo=0.02):
    n = len(x)
    i, o = int(fi * SR), int(fo * SR)
    if i: x[:i] *= np.linspace(0, 1, i)
    if o: x[-o:] *= np.linspace(1, 0, o)
    return x


def sweep(f0, f1, d, shape="exp"):
    n = int(d * SR)
    if shape == "exp":
        f = f0 * (f1 / f0) ** np.linspace(0, 1, n)
    else:
        f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR), f


def noise(d, color="white"):
    n = int(d * SR)
    w = _rng.standard_normal(n).astype(np.float32)
    if color == "white":
        return w
    W = np.fft.rfft(w)
    fr = np.fft.rfftfreq(n, 1 / SR)
    fr[0] = 1
    if color == "pink":
        W /= np.sqrt(fr)
    elif color == "brown":
        W /= fr
    x = np.fft.irfft(W, n)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def bandpass(x, lo, hi):
    n = len(x)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / SR)
    X[(fr < lo) | (fr > hi)] = 0
    return np.fft.irfft(X, n).astype(np.float32)


def lowpass(x, cut):
    return bandpass(x, 0, cut)


def highpass(x, cut):
    return bandpass(x, cut, SR / 2)


def tv_filter(x, fc, q=4.0):
    """time-varying resonant bandpass (state variable filter), fc array or float"""
    fc = np.broadcast_to(np.asarray(fc, dtype=np.float64), x.shape)
    y = np.zeros_like(x)
    low = band = 0.0
    damp = 1.0 / q
    for i in range(len(x)):
        f = 2 * np.sin(np.pi * min(fc[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        y[i] = band
    return y


def norm(x, peak=0.9):
    m = np.abs(x).max()
    return (x / m * peak).astype(np.float32) if m > 0 else x.astype(np.float32)


# --- effects --------------------------------------------------------------------

def pop(pitch=1.0):
    d = 0.11
    s, _ = sweep(1100 * pitch, 260 * pitch, d)
    x = s * env_ad(len(s), 0.002, curve=6)
    x += 0.3 * noise(d) * env_ad(len(s), 0.0005, curve=40)
    return norm(fade(x), 0.8)


def bubble(pitch=1.0):
    d = 0.09
    s, _ = sweep(300 * pitch, 1400 * pitch, d)
    return norm(fade(s * env_ad(len(s), 0.004, curve=5)), 0.6)


def whoosh(d=0.45, up=True):
    n = noise(d, "pink")
    t = np.linspace(0, 1, len(n))
    fc = (300 + 2600 * (t if up else 1 - t) ** 1.5)
    x = tv_filter(n, fc, q=1.6)
    e = np.sin(np.pi * t) ** 1.6
    return norm(fade(x * e), 0.7)


def swish():
    return whoosh(0.22)


def boing(pitch=1.0, d=0.7):
    t = t_(d)
    f = 220 * pitch * (1 + 0.35 * np.sin(2 * np.pi * 9 * t) * np.exp(-3 * t)) * (1 + 0.6 * np.exp(-8 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * env_ad(len(t), 0.003, curve=4)
    return norm(fade(x), 0.7)


def thud(pitch=1.0):
    d = 0.35
    s, _ = sweep(140 * pitch, 45 * pitch, d)
    x = s * env_ad(len(s), 0.002, curve=7)
    x += 0.5 * lowpass(noise(d), 1200) * env_ad(len(s), 0.001, curve=25)
    return norm(fade(x), 0.95)


def impact():
    d = 0.6
    x = thud(0.8)[: int(0.35 * SR)]
    n = lowpass(noise(d, "pink"), 4000) * env_ad(int(d * SR), 0.001, curve=9)
    out = np.zeros(int(d * SR), np.float32)
    out[: len(x)] += x
    out += 0.6 * n
    return norm(fade(out), 0.95)


def thunder(d=2.8):
    n = noise(d, "brown")
    t = np.linspace(0, 1, len(n))
    rumble = lowpass(n, 220) * (np.exp(-2.2 * t) * (1 + 0.5 * np.sin(2 * np.pi * 3.3 * t * d)))
    crack = highpass(noise(d), 800) * np.exp(-30 * t * d / 2.8)
    x = 1.0 * norm(rumble) + 0.7 * crack
    x[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return norm(fade(x, 0.002, 0.3), 0.98)


def zap(d=0.7):
    t = t_(d)
    buzz = np.sign(np.sin(2 * np.pi * 95 * t + 3 * np.sin(2 * np.pi * 13 * t)))
    crackle = noise(d) * (_rng.random(len(t)) > 0.985) * 6
    am = 0.55 + 0.45 * (_rng.random(len(t) // 400 + 1).repeat(400)[: len(t)])
    x = (0.5 * highpass(buzz.astype(np.float32), 300) + 0.6 * crackle + 0.4 * highpass(noise(d), 3000)) * am
    x *= np.minimum(1, t / 0.01) * np.exp(-1.8 * t)
    return norm(fade(x), 0.85)


def crackle(d=1.0):
    t = t_(d)
    x = noise(d) * (_rng.random(len(t)) > 0.993) * 5
    x = highpass(x.astype(np.float32), 1500) * np.exp(-1.2 * t)
    return norm(fade(x), 0.6)


def hiss(d=0.9):
    n = highpass(noise(d), 3500)
    t = np.linspace(0, 1, len(n))
    e = np.minimum(1, t * 12) * np.exp(-2.2 * t)
    return norm(fade(n * e), 0.6)


def steam(d=1.2):
    return hiss(d)


def ding(pitch=1.0, d=1.4):
    t = t_(d)
    f = 1320 * pitch
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-k * t) for a, m, k in [(1, 1, 3), (0.5, 2.76, 5), (0.25, 5.4, 8), (0.15, 8.9, 12)])
    x *= np.minimum(1, t / 0.002)
    return norm(fade(x), 0.55)


def chime():
    a = ding(1.0, 0.9)
    b = ding(1.5, 1.1)
    out = np.zeros(int(1.25 * SR), np.float32)
    out[: len(a)] += a
    o = int(0.12 * SR)
    out[o: o + len(b)] += b[: len(out) - o]
    return norm(out, 0.6)


def sparkle():
    out = np.zeros(int(1.0 * SR), np.float32)
    for i, p in enumerate([2.0, 2.5, 3.0, 4.0]):
        b = ding(p, 0.6) * 0.7
        o = int(i * 0.06 * SR)
        out[o: o + len(b)] += b[: len(out) - o]
    return norm(out, 0.45)


def tick():
    d = 0.03
    x = highpass(noise(d), 2000) * env_ad(int(d * SR), 0.0005, curve=30)
    return norm(x, 0.5)


def clock(d=2.0, rate=2.0):
    out = np.zeros(int(d * SR), np.float32)
    k = tick()
    for i in range(int(d * rate)):
        o = int(i / rate * SR)
        out[o: o + len(k)] += k * (1.0 if i % 2 == 0 else 0.7)
    return out


def heartbeat(bpm=80, beats=2):
    per = 60 / bpm
    out = np.zeros(int(per * beats * SR + 0.4 * SR), np.float32)
    for b in range(beats):
        for off, g in [(0, 1.0), (0.22, 0.7)]:
            th = thud(0.7) * g
            o = int((b * per + off) * SR)
            out[o: o + len(th)] += th[: len(out) - o]
    return norm(out, 0.9)


def beep(f=1000, d=0.14):
    t = t_(d)
    x = np.sin(2 * np.pi * f * t) * 0.6
    return fade(x.astype(np.float32), 0.004, 0.02)


def flatline(d=1.8):
    t = t_(d)
    x = 0.5 * np.sin(2 * np.pi * 1000 * t)
    return fade(x.astype(np.float32), 0.005, 0.2)


def buzzer():
    t = t_(0.45)
    x = np.sign(np.sin(2 * np.pi * 140 * t)) * 0.4 + np.sign(np.sin(2 * np.pi * 147 * t)) * 0.4
    return norm(fade(lowpass(x.astype(np.float32), 2500)), 0.5)


def alarm(n=3):
    out = []
    for i in range(n):
        out.append(beep(880, 0.16)); out.append(np.zeros(int(0.04 * SR), np.float32))
        out.append(beep(660, 0.16)); out.append(np.zeros(int(0.06 * SR), np.float32))
    return norm(np.concatenate(out), 0.5)


def slide_up(d=0.5):
    s, _ = sweep(300, 1400, d)
    return norm(fade(s * np.sin(np.linspace(0, np.pi, len(s))) ** 0.5), 0.5)


def slide_down(d=0.5):
    s, _ = sweep(1400, 250, d)
    return norm(fade(s * np.sin(np.linspace(0, np.pi, len(s))) ** 0.5), 0.5)


def fall_whistle(d=1.6):
    t = t_(d)
    f = 1900 * (0.22) ** (t / d)
    x = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))) / SR)
    x *= np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.1)
    return norm(x.astype(np.float32), 0.45)


def stretch(d=1.0):
    t = t_(d)
    f = 400 * (0.35) ** (t / d) * (1 + 0.04 * np.sin(2 * np.pi * 25 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sign(np.sin(ph)) * 0.3 + np.sin(ph * 2) * 0.3
    x = lowpass(x.astype(np.float32), 2500)
    x *= np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.15)
    return norm(x, 0.55)


def inflate(d=1.4):
    n = noise(d, "pink")
    t = np.linspace(0, 1, len(n))
    x = tv_filter(n, 250 + 1700 * t ** 1.2, q=6)
    s, _ = sweep(120, 420, d)
    x = norm(x) + 0.25 * s
    x *= np.minimum(1, t * 8) * np.minimum(1, (1 - t) * 10)
    return norm(fade(x.astype(np.float32)), 0.55)


def gulp():
    out = np.zeros(int(0.5 * SR), np.float32)
    for i, p in enumerate([0.55, 0.7]):
        b = bubble(p)
        o = int(i * 0.18 * SR)
        out[o: o + len(b)] += b
    return norm(lowpass(out, 3000), 0.75)


def splash(d=0.9):
    n = noise(d, "pink")
    t = np.linspace(0, 1, len(n))
    x = bandpass(n, 400, 7000) * np.exp(-5 * t) * np.minimum(1, t * 200)
    out = norm(x) * 0.8
    for i in range(6):
        b = bubble(0.8 + _rng.random()) * 0.3
        o = int((0.05 + _rng.random() * 0.5) * SR)
        out[o: o + len(b)] += b[: len(out) - o]
    return norm(out, 0.8)


def rumble(d=3.0):
    n = noise(d, "brown")
    t = np.linspace(0, 1, len(n))
    x = lowpass(n, 120) * np.minimum(1, t * 4) * np.minimum(1, (1 - t) * 4)
    return norm(x.astype(np.float32), 0.8)


def drone(d=3.0, f=55):
    t = t_(d)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t + np.sin(2 * np.pi * 0.3 * t)) + 0.3 * lowpass(noise(d, "brown"), 200)
    x *= np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6)
    return norm(x.astype(np.float32), 0.6)


def scribble():
    d = 0.35
    n = bandpass(noise(d), 1500, 6000)
    t = np.linspace(0, 1, len(n))
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 22 * t * d)
    return norm(fade(n * am * np.sin(np.pi * t)), 0.4)


def dig():
    d = 0.3
    n = lowpass(noise(d), 2500)
    e = env_ad(len(n), 0.003, curve=10)
    return norm(fade(n * e + 0.4 * thud(1.4)[: len(n)]), 0.7)


def jump():
    s, _ = sweep(250, 900, 0.18)
    return norm(fade(s * env_ad(len(s), 0.004, curve=3)), 0.5)


def splat():
    d = 0.4
    n = lowpass(noise(d), 1800) * env_ad(int(d * SR), 0.001, curve=12)
    return norm(fade(n + 0.6 * thud(0.9)[: len(n)]), 0.8)


def sizzle(d=1.4):
    n = highpass(noise(d), 2500)
    t = np.linspace(0, 1, len(n))
    am = 0.6 + 0.4 * (_rng.random(len(n) // 300 + 1).repeat(300)[: len(n)])
    return norm(fade(n * am * np.minimum(1, t * 10) * np.exp(-1.2 * t)), 0.45)


def warp(d=1.5):
    """sci-fi pitch-bend down with flanger, for time slowing"""
    t = t_(d)
    f = 600 * (0.15) ** (t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(ph * 1.01 + 1) + 0.3 * np.sin(ph * 2.02)
    x *= np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.3)
    return norm(x.astype(np.float32), 0.45)


def riser(d=1.5):
    n = noise(d, "pink")
    t = np.linspace(0, 1, len(n))
    x = tv_filter(n, 300 + 5000 * t ** 2, q=3) * t ** 1.5
    return norm(fade(x.astype(np.float32), 0.01, 0.02), 0.5)


def suck(d=0.8):
    """reverse whoosh: things sucked in"""
    return whoosh(d, up=True)[::-1].copy() * 0.9


def cartoon_run(d=1.2):
    out = np.zeros(int(d * SR), np.float32)
    k = 0
    while k * 0.09 < d - 0.1:
        b = pop(0.5 + 0.1 * (k % 2)) * 0.4
        o = int(k * 0.09 * SR)
        out[o: o + len(b)] += b[: len(out) - o]
        k += 1
    return out


def glass_tap():
    return ding(2.2, 0.4)


LIB = {k: v for k, v in globals().items() if callable(v) and not k.startswith("_") and k not in (
    "t_", "env_ad", "fade", "sweep", "noise", "bandpass", "lowpass", "highpass", "tv_filter", "norm")}
