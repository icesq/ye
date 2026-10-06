"""Generates the store's branded media into assets/ (banners + looping MP4 animations).

    pip install Pillow          # only for this script, the bot itself doesn't need it
    python tools/make_assets.py [--name "NOVA"] [--only main,catalog]

Requires ffmpeg for the animations (static banners work without it).
Fonts: Inter Display (falls back to DejaVu Sans) and Noto Color Emoji for the emblems.
"""
import argparse
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
W, H = 1280, 720

FONT_DIRS = [os.path.join(ROOT, "tools", "fonts"), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
             "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"]
EMOJI_FONTS = [os.path.join(ROOT, "tools", "fonts", "NotoColorEmoji.ttf"),
               "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", "/usr/share/fonts/noto/NotoColorEmoji.ttf",
               "/System/Library/Fonts/Apple Color Emoji.ttc"]


def font(weight, size):
    names = {"black": ["InterDisplay-Black.otf", "Inter-Black.otf", "DejaVuSans-Bold.ttf"],
             "bold": ["InterDisplay-Bold.otf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf"],
             "semibold": ["InterDisplay-SemiBold.otf", "Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"],
             "medium": ["InterDisplay-Medium.otf", "Inter-Medium.otf", "DejaVuSans.ttf"]}[weight]
    for d in FONT_DIRS:
        for n in names:
            path = os.path.join(d, n)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


# ---------------------------------------------------------------- primitives
def gradient(size, c1, c2, horizontal=True):
    w, h = size
    base = Image.new("RGB", (256, 1))
    for x in range(256):
        base.putpixel((x, 0), lerp(c1, c2, x / 255))
    img = base.resize((w, h) if horizontal else (h, w), Image.BICUBIC)
    return img if horizontal else img.rotate(90, expand=True).resize((w, h))


def glow_layer(blobs, scale=4):
    """blobs: [(x, y, radius, rgb, alpha)] -> soft additive light layer (rendered small, upscaled)."""
    small = Image.new("RGB", (W // scale, H // scale), (0, 0, 0))
    for x, y, r, color, alpha in blobs:
        layer = Image.new("RGB", small.size, (0, 0, 0))
        d = ImageDraw.Draw(layer)
        rr = r / scale
        d.ellipse([x / scale - rr, y / scale - rr, x / scale + rr, y / scale + rr],
                  fill=tuple(int(c * alpha) for c in color))
        layer = layer.filter(ImageFilter.GaussianBlur(rr * 0.55))
        small = ImageChops.add(small, layer)
    return small.resize((W, H), Image.BICUBIC)


def base_background(colors, blobs=None, seed=1):
    rnd = random.Random(seed)
    img = gradient((W, H), (6, 9, 18), (12, 16, 34), horizontal=False).convert("RGB")
    c1, c2 = colors
    blobs = blobs or [(W * 0.82, H * 0.30, 360, c1, 0.85), (W * 0.62, H * 0.95, 330, c2, 0.7),
                      (W * 0.05, H * 0.05, 260, c2, 0.35)]
    img = ImageChops.add(img, glow_layer(blobs))
    # fine dot grid
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(20, W, 40):
        for y in range(20, H, 40):
            fade = max(0, 1 - math.hypot(x - W * 0.75, y - H * 0.45) / 900)
            if fade > 0.05:
                gd.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, int(28 * fade)))
    img = Image.alpha_composite(img.convert("RGBA"), grid)
    # subtle grain
    noise = Image.effect_noise((W // 2, H // 2), 18).resize((W, H)).convert("L")
    grain = Image.merge("RGBA", (noise, noise, noise, Image.new("L", (W, H), 7)))
    img = Image.alpha_composite(img, grain)
    # stars
    sd = ImageDraw.Draw(img)
    for _ in range(70):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        a = rnd.randint(40, 150)
        r = rnd.choice((0.6, 0.8, 1.2))
        sd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    return img


def sparkle_mask(size, power=3.2):
    """4-point star (astroid-like) as an L mask."""
    s = size
    m = Image.new("L", (s * 4, s * 4), 0)
    d = ImageDraw.Draw(m)
    cx = cy = s * 2
    pts = []
    for i in range(360):
        t = math.radians(i)
        c, sn = math.cos(t), math.sin(t)
        x = math.copysign(abs(c) ** power, c) * s * 2
        y = math.copysign(abs(sn) ** power, sn) * s * 2
        pts.append((cx + x, cy + y))
    d.polygon(pts, fill=255)
    return m.resize((s * 2, s * 2), Image.LANCZOS)


def paste_sparkle(img, center, size, c1, c2, glow=True, angle=0):
    mask = sparkle_mask(size)
    if angle:
        mask = mask.rotate(angle, resample=Image.BICUBIC)
    fill = gradient(mask.size, c1, c2).convert("RGBA")
    x, y = int(center[0] - mask.size[0] / 2), int(center[1] - mask.size[1] / 2)
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gm = mask.filter(ImageFilter.GaussianBlur(size / 5))
        g.paste(Image.new("RGBA", mask.size, c1 + (255,)), (x, y), gm)
        img.alpha_composite(g)
    img.paste(fill, (x, y), mask)


def emoji_image(char, size):
    for path in EMOJI_FONTS:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, 109)
                canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
                ImageDraw.Draw(canvas).text((80, 80), char, font=f, embedded_color=True, anchor="mm")
                bbox = canvas.getbbox()
                if bbox:
                    canvas = canvas.crop(bbox)
                return canvas.resize((size, int(size * canvas.size[1] / canvas.size[0])), Image.LANCZOS)
            except Exception:
                continue
    return None


def text_gradient(img, xy, text, fnt, c1, c2, anchor="la"):
    d = ImageDraw.Draw(img)
    bbox = d.textbbox(xy, text, font=fnt, anchor=anchor)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if w <= 0 or h <= 0:
        return bbox
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((xy[0] - bbox[0], xy[1] - bbox[1]), text, font=fnt, fill=255, anchor=anchor)
    img.paste(gradient((w, h), c1, c2).convert("RGBA"), (bbox[0], bbox[1]), mask)
    return bbox


def glass(img, box, radius=36, alpha=20):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius, fill=(255, 255, 255, alpha), outline=(255, 255, 255, 48), width=2)
    img.alpha_composite(layer)


def pill(img, xy, text, c1, c2, fnt):
    d = ImageDraw.Draw(img)
    tw = d.textlength(text, font=fnt)
    x, y = xy
    h = fnt.size + 22
    w = int(tw + 70)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x, y, x + w, y + h], h // 2, fill=(255, 255, 255, 18), outline=(255, 255, 255, 60), width=2)
    img.alpha_composite(layer)
    paste_sparkle(img, (x + 28, y + h / 2), 12, c1, c2, glow=False)
    d.text((x + 50, y + h / 2), text, font=fnt, fill=(232, 236, 255), anchor="lm")
    return w, h


# ------------------------------------------------------------------- banners
def emblem(img, char, center, size, c1, c2, angle=0, ring=True):
    cx, cy = center
    if ring:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = size * 0.95
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c1 + (90,), width=3)
        r2 = size * 1.22
        d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=(255, 255, 255, 30), width=2)
        # orbit dots
        for k in range(3):
            a = math.radians(angle + k * 120)
            ox, oy = cx + math.cos(a) * r2, cy + math.sin(a) * r2
            d.ellipse([ox - 7, oy - 7, ox + 7, oy + 7], fill=(c2 if k % 2 else c1) + (255,))
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))
        glass(img, [cx - size * 0.72, cy - size * 0.72, cx + size * 0.72, cy + size * 0.72], int(size * 0.32), 22)
    em = emoji_image(char, int(size * 0.92))
    if em is not None:
        halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        hr = size * 0.55
        hd.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=c2 + (90,))
        img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(size * 0.28)))
        pad = 60
        sm = Image.new("L", (em.size[0] + 2 * pad, em.size[1] + 2 * pad), 0)
        sm.paste(em.split()[3].point(lambda a: a * 0.35), (pad, pad))
        sm = sm.filter(ImageFilter.GaussianBlur(22))
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow.paste(Image.new("RGBA", sm.size, (4, 6, 20, 255)),
                     (int(cx - em.size[0] / 2 - pad), int(cy - em.size[1] / 2 + 22 - pad)), sm)
        img.alpha_composite(shadow)
        img.alpha_composite(em, (int(cx - em.size[0] / 2), int(cy - em.size[1] / 2)))
    else:
        paste_sparkle(img, center, int(size * 0.5), c1, c2)


def banner(name, title, subtitle, char, colors, brand="NOVA"):
    c1, c2 = hex2rgb(colors[0]), hex2rgb(colors[1])
    img = base_background((c1, c2), seed=hash(name) & 0xFFFF)
    emblem(img, char, (W * 0.77, H * 0.5), 205, c1, c2, angle=(hash(name) % 360))
    x = 92
    pill(img, (x, 120), f"{brand} · DIGITAL STORE", c1, c2, font("semibold", 24))
    size = 104 if len(title) <= 12 else 84 if len(title) <= 17 else 70
    fnt = font("black", size)
    lines = wrap(title, fnt, 640)
    y = 220
    for line in lines[:2]:
        text_gradient(img, (x, y), line, fnt, (255, 255, 255), lerp(c1, (255, 255, 255), 0.35))
        y += int(size * 1.08)
    d = ImageDraw.Draw(img)
    d.text((x + 2, y + 18), subtitle, font=font("medium", 34), fill=(176, 186, 220))
    # bottom accent line
    acc = gradient((240, 6), c1, c2).convert("RGBA")
    mask = Image.new("L", (240, 6), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 239, 5], 3, fill=255)
    img.paste(acc, (x, y + 90), mask)
    return img.convert("RGB")


def wrap(text, fnt, max_w):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=fnt) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


# --------------------------------------------------------------- animations
def encode(frames_dir, out, fps=30):
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found: skipping", out)
        return False
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(frames_dir, "%04d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-preset", "slow", "-movflags", "+faststart",
           "-an", out]
    subprocess.run(cmd, check=True)
    return True


def main_frames(brand, tmp, frames=120):
    c1, c2, c3 = hex2rgb("#7C5CFF"), hex2rgb("#22D3EE"), hex2rgb("#FF4FD8")
    rnd = random.Random(7)
    stars = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.5, 1.4), rnd.uniform(0, 6.28)) for _ in range(110)]
    orbit = ["🤖", "⭐", "🎮", "🎁"]
    emojis = {e: emoji_image(e, 118) for e in orbit}
    word_font = font("black", 196)
    for i in range(frames):
        t = i / frames
        ph = t * 2 * math.pi
        blobs = [(W * 0.70 + math.cos(ph) * 60, H * 0.35 + math.sin(ph) * 40, 380, c1, 0.9),
                 (W * 0.45 + math.cos(ph + 2) * 80, H * 0.95 + math.sin(ph) * 30, 340, c2, 0.75),
                 (W * 0.10 + math.sin(ph) * 50, H * 0.10, 260, c3, 0.45)]
        img = gradient((W, H), (6, 9, 18), (12, 16, 34), horizontal=False).convert("RGB")
        img = ImageChops.add(img, glow_layer(blobs, scale=6)).convert("RGBA")
        d = ImageDraw.Draw(img)
        for x, y, r, p in stars:
            a = int(70 + 80 * (0.5 + 0.5 * math.sin(ph * 2 + p)))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
        # orbiting emblems on the right
        cx, cy = W * 0.76, H * 0.5
        ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        for rr, al in ((250, 40), (175, 28)):
            rd.ellipse([cx - rr, cy - rr * 0.62, cx + rr, cy + rr * 0.62], outline=(255, 255, 255, al), width=2)
        img.alpha_composite(ring)
        paste_sparkle(img, (cx, cy), int(70 + 8 * math.sin(ph * 2)), c2, c1, angle=math.degrees(ph) / 2)
        placed = []
        for k, e in enumerate(orbit):
            a = ph + k * math.pi / 2
            ex, ey = cx + math.cos(a) * 250, cy + math.sin(a) * 250 * 0.62
            scale = 0.78 + 0.22 * (math.sin(a) + 1) / 2
            placed.append((math.sin(a), e, ex, ey, scale))
        for _, e, ex, ey, scale in sorted(placed):
            em = emojis[e]
            if em is None:
                continue
            sz = int(118 * scale)
            em2 = em.resize((sz, sz), Image.LANCZOS)
            img.alpha_composite(em2, (int(ex - sz / 2), int(ey - sz / 2)))
        # wordmark with a light sweep
        x = 90
        pill(img, (x, 150), "DIGITAL STORE · 24/7", c1, c2, font("semibold", 24))
        bbox = text_gradient(img, (x - 6, 215), brand, word_font, (255, 255, 255), (198, 186, 255))
        sweep_x = int(-300 + (W + 600) * ((t * 1.4) % 1.0))
        sweep = Image.new("L", (bbox[2] - bbox[0], bbox[3] - bbox[1]), 0)
        sd = ImageDraw.Draw(sweep)
        sd.polygon([(sweep_x - bbox[0], 0), (sweep_x - bbox[0] + 90, 0), (sweep_x - bbox[0] + 30, sweep.size[1]),
                    (sweep_x - bbox[0] - 60, sweep.size[1])], fill=150)
        sweep = sweep.filter(ImageFilter.GaussianBlur(18))
        tmask = Image.new("L", sweep.size, 0)
        ImageDraw.Draw(tmask).text((x - 6 - bbox[0], 215 - bbox[1]), brand, font=word_font, fill=255)
        light = ImageChops.multiply(sweep, tmask)
        img.paste(Image.new("RGBA", sweep.size, (255, 255, 255, 255)), (bbox[0], bbox[1]), light)
        d = ImageDraw.Draw(img)
        d.text((x, bbox[3] + 34), "AI · Stars · Games · Gift Cards", font=font("semibold", 40), fill=(214, 220, 245))
        d.text((x, bbox[3] + 92), "Instant delivery · Guarantee · Support", font=font("medium", 30),
               fill=(150, 162, 205))
        img.convert("RGB").save(os.path.join(tmp, f"{i:04d}.png"))


def success_frames(tmp, frames=90):
    c1, c2 = hex2rgb("#22C55E"), hex2rgb("#22D3EE")
    rnd = random.Random(3)
    confetti = [(rnd.uniform(-1, 1), rnd.uniform(-1.4, -0.3), rnd.choice([(255, 79, 216), (124, 92, 255),
                                                                         (34, 211, 238), (250, 204, 21),
                                                                         (34, 197, 94)]),
                 rnd.uniform(5, 11), rnd.uniform(0, 360)) for _ in range(140)]
    bg = base_background((c1, c2), seed=11)
    check_font = font("black", 96)
    for i in range(frames):
        t = i / frames
        img = bg.copy()
        cx, cy = W * 0.5, H * 0.42
        grow = min(1.0, t * 3.2)
        ease = 1 - (1 - grow) ** 3
        r = 120 * ease + 6 * math.sin(t * 2 * math.pi * 2) * (grow >= 1)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.ellipse([cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5], fill=c1 + (60,))
        layer = layer.filter(ImageFilter.GaussianBlur(40))
        img.alpha_composite(layer)
        circle = gradient((int(2 * r) + 1, int(2 * r) + 1), c1, c2).convert("RGBA")
        mask = Image.new("L", circle.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, circle.size[0] - 1, circle.size[1] - 1], fill=255)
        img.paste(circle, (int(cx - r), int(cy - r)), mask)
        if t > 0.18:
            d = ImageDraw.Draw(img)
            k = min(1.0, (t - 0.18) * 4)
            p1, p2, p3 = (cx - 52, cy + 2), (cx - 14, cy + 40), (cx + 58, cy - 40)
            mid = (p1[0] + (p2[0] - p1[0]) * min(1, k * 2), p1[1] + (p2[1] - p1[1]) * min(1, k * 2))
            d.line([p1, mid], fill=(255, 255, 255), width=22, joint="curve")
            if k > 0.5:
                kk = (k - 0.5) * 2
                end = (p2[0] + (p3[0] - p2[0]) * kk, p2[1] + (p3[1] - p2[1]) * kk)
                d.line([p2, end], fill=(255, 255, 255), width=22, joint="curve")
        # confetti burst
        d = ImageDraw.Draw(img)
        for vx, vy, color, size, rot in confetti:
            tt = max(0.0, t - 0.1) * 1.8
            x = cx + vx * 700 * tt
            y = cy + (vy * 600 * tt + 520 * tt * tt)
            if 0 <= x <= W and 0 <= y <= H and tt > 0:
                a = math.radians(rot + 400 * tt)
                dx, dy = math.cos(a) * size, math.sin(a) * size * 0.5
                d.polygon([(x - dx, y - dy), (x + dy, y - dx), (x + dx, y + dy), (x - dy, y + dx)], fill=color)
        if t > 0.3:
            alpha = int(255 * min(1.0, (t - 0.3) * 4))
            tl = Image.new("RGBA", img.size, (0, 0, 0, 0))
            td = ImageDraw.Draw(tl)
            td.text((cx, cy + 205), "Order complete", font=check_font, fill=(255, 255, 255, alpha), anchor="mm")
            td.text((cx, cy + 280), "Your item is below ↓", font=font("medium", 36), fill=(190, 200, 230, alpha),
                    anchor="mm")
            img.alpha_composite(tl)
        img.convert("RGB").save(os.path.join(tmp, f"{i:04d}.png"))


# ----------------------------------------------------------------- catalog
P = {"violet": ("#7C5CFF", "#22D3EE"), "pink": ("#FF4FD8", "#7C5CFF"), "gold": ("#FBBF24", "#F97316"),
     "green": ("#22C55E", "#22D3EE"), "blue": ("#3B82F6", "#22D3EE"), "orange": ("#F97316", "#FF4FD8")}

BANNERS = {
    "catalog": ("Catalog", "AI · Stars · Games · Gift cards", "🛍️", P["violet"]),
    "payment": ("Secure payment", "Stars · Crypto · Cards · SBP", "💳", P["blue"]),
    "profile": ("Your profile", "Balance · Bonuses · Referrals", "👤", P["pink"]),
    "orders": ("My orders", "Everything you bought — in one place", "📦", ("#F59E0B", "#7C5CFF")),
    "topup": ("Top up balance", "One payment — many purchases", "💰", P["green"]),
    "support": ("Support 24/7", "We answer right in this chat", "💬", P["blue"]),
    "faq": ("How it works", "Choose · Pay · Get it instantly", "💡", ("#FBBF24", "#7C5CFF")),
    "subscribe": ("Join our channel", "News · Giveaways · Promo codes", "📢", P["pink"]),
    "admin": ("Control panel", "Products · Payments · Analytics", "⚙️", ("#94A3B8", "#7C5CFF")),
    "cat_ai": ("AI Subscriptions", "ChatGPT · Claude · Gemini · Grok", "🤖", P["violet"]),
    "cat_telegram": ("Telegram", "Stars · Premium · Gifts", "⭐", P["gold"]),
    "cat_steam": ("Steam", "Wallet top-up · Gift cards", "🎮", P["blue"]),
    "cat_games": ("Mobile Games", "UC · Crystals · Diamonds", "🕹️", P["orange"]),
    "cat_gifts": ("Gift Cards", "Apple · Google Play · PlayStation", "🎁", P["pink"]),
    "ai_chatgpt": ("ChatGPT", "Plus · Pro", "💬", ("#10A37F", "#22D3EE")),
    "ai_claude": ("Claude", "Pro · Max", "🧡", ("#D97757", "#F5C26B")),
    "ai_gemini": ("Gemini", "Google AI Pro", "✨", ("#4285F4", "#9B72CB")),
    "ai_perplexity": ("Perplexity", "Pro · AI search", "🔎", ("#20808D", "#22D3EE")),
    "ai_grok": ("Grok", "SuperGrok · Heavy", "⚡", ("#E5E7EB", "#7C5CFF")),
    "ai_midjourney": ("Midjourney", "Basic · Standard", "🎨", ("#F472B6", "#7C5CFF")),
    "ai_cursor": ("Cursor", "Pro · AI code editor", "💻", ("#A3A3A3", "#22D3EE")),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="NOVA")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))
    os.makedirs(OUT, exist_ok=True)
    for key, (title, sub, char, colors) in BANNERS.items():
        if only and key not in only:
            continue
        path = os.path.join(OUT, f"{key}.jpg")
        banner(key, title, sub, char, colors, args.name).save(path, quality=88, optimize=True, progressive=True)
        print("✓", path)
    for key, render in (("main", lambda tmp: main_frames(args.name, tmp)), ("success", success_frames)):
        if only and key not in only:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            render(tmp)
            out = os.path.join(OUT, f"{key}.mp4")
            if encode(tmp, out):
                print("✓", out)


if __name__ == "__main__":
    sys.exit(main())
