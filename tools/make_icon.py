"""Draw the Multi-Tofu app icon and every image the app and the site use.

The mark is one crowned tofu leading a flock: six birds fanned out behind a
bigger crowned one. The flock is drawn dimmer and thinner on purpose, so at 16
pixels the icon still reads as a single crowned bird instead of mush.
"""
import os
import subprocess

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "icon.iconset")
DOCS = os.path.join(ROOT, "docs", "assets")
APP_ASSETS = os.path.join(ROOT, "multitofu", "assets")

GRAPE = (74, 64, 118)
GRAPE_TOP = (88, 76, 138)
CREAM = (255, 246, 232)
FLOCK = (222, 210, 226)
SUNNY = (255, 201, 74)
GOLD_DEEP = (232, 158, 32)
MINT = (95, 224, 176)
INK = (46, 38, 80)
INK_SOFT = (78, 66, 126)
BLUSH = (255, 158, 168)

S = 1024

# head centre x, head centre y, size, all as a fraction of the canvas. The
# flock steps up and out, the way a V looks from the front.
FLOCK_POSITIONS = [
    (0.265, 0.445, 0.34),
    (0.160, 0.395, 0.32),
    (0.058, 0.360, 0.30),
    (0.735, 0.445, 0.34),
    (0.840, 0.395, 0.32),
    (0.942, 0.360, 0.30),
]
LEADER = (0.500, 0.505, 0.72)


def bird(d, hx, hy, u, *, fill, outline, width, tuft=None, crown=False,
         blush=False, feet=True, eyes=True):
    """One tofu. Geometry scales with u so the flock is the same drawing."""
    hr = 0.20 * u
    cx, cy = hx, hy + 0.22 * u
    rw, rh = 0.30 * u, 0.27 * u

    if feet:
        for dx in (-0.10 * u, 0.10 * u):
            d.line([(cx + dx, cy + rh - 0.02 * u), (cx + dx, cy + rh + 0.045 * u)],
                   fill=SUNNY, width=max(1, int(0.028 * u)))
    d.ellipse((cx - rw, cy - rh, cx + rw, cy + rh), fill=fill,
              outline=outline, width=width)
    if tuft is not None:
        d.ellipse((hx - 0.045 * u, hy - hr - 0.075 * u,
                   hx + 0.045 * u, hy - hr + 0.03 * u),
                  fill=tuft, outline=outline, width=max(1, int(width * 0.8)))
    d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=fill,
              outline=outline, width=width)
    if crown:
        _crown(d, hx, hy, hr, width)
    if eyes:
        er = 0.028 * u
        for dx in (-0.072 * u, 0.072 * u):
            d.ellipse((hx + dx - er, hy - er - 0.01 * u,
                       hx + dx + er, hy + er - 0.01 * u), fill=outline)
    if blush:
        br = 0.030 * u
        for dx in (-0.135 * u, 0.135 * u):
            d.ellipse((hx + dx - br, hy + 0.045 * u - br,
                       hx + dx + br, hy + 0.045 * u + br), fill=BLUSH)
    d.polygon([(hx - 0.042 * u, hy + 0.045 * u),
               (hx + 0.042 * u, hy + 0.045 * u),
               (hx, hy + 0.115 * u)], fill=SUNNY, outline=outline)


def _crown(d, hx, hy, hr, width):
    """Three points and a band, sitting on the head instead of the tuft."""
    base = hy - hr * 0.74
    half = hr * 0.72
    peak = base - hr * 0.86
    side = base - hr * 0.58
    valley = base - hr * 0.16
    d.polygon([(hx - half, base), (hx - half, side),
               (hx - half * 0.45, valley), (hx, peak),
               (hx + half * 0.45, valley), (hx + half, side),
               (hx + half, base)],
              fill=SUNNY, outline=INK, width=width)
    d.rounded_rectangle((hx - half * 1.06, base - hr * 0.05,
                         hx + half * 1.06, base + hr * 0.22),
                        radius=hr * 0.12, fill=GOLD_DEEP, outline=INK, width=width)
    tip = hr * 0.13
    for px, py in ((hx - half, side), (hx, peak), (hx + half, side)):
        d.ellipse((px - tip, py - tip, px + tip, py + tip),
                  fill=CREAM, outline=INK, width=max(1, int(width * 0.7)))


def _tile(size):
    """Grape tile with a soft top-to-bottom gradient. Two stacked rounded
    rectangles left a visible seam, so the gradient is painted per row."""
    band = Image.new("RGBA", (1, size))
    px = band.load()
    for y in range(size):
        f = y / max(1, size - 1)
        px[0, y] = tuple(int(a + (b - a) * f) + 0 for a, b in
                         zip(GRAPE_TOP, GRAPE)) + (255,)
    band = band.resize((size, size))
    pad = size * 0.06
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (pad, pad, size - pad, size - pad), radius=size * 0.22, fill=255)
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile.paste(band, (0, 0), mask)
    return tile, mask


def scene(size, background=True, flock=True):
    """flock=False is the small-size cut. Six birds at 32 pixels is grey soup,
    so the icon below 64 keeps the crowned leader and drops the rest."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = None
    if background:
        tile, mask = _tile(size)
        img.alpha_composite(tile)

    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    if flock:
        for fx, fy, fu in FLOCK_POSITIONS:
            bird(ld, fx * size, fy * size, fu * size, fill=FLOCK,
                 outline=INK_SOFT, width=max(1, int(0.016 * fu * size)),
                 tuft=MINT, eyes=True)
        lx, ly, lu = LEADER
    else:
        lx, ly, lu = 0.500, 0.520, 0.88
    bird(ld, lx * size, ly * size, lu * size, fill=CREAM, outline=INK,
         width=max(2, int(0.022 * lu * size)), crown=True, blush=True)

    if mask is not None:
        img.paste(layer, (0, 0), Image.composite(
            layer.split()[3], Image.new("L", (size, size), 0), mask))
    else:
        img.alpha_composite(layer)
    return img


def render():
    return scene(S)


def og_card(base):
    """1200x630 social card: the mark on the same grape, room for nothing else
    because the crop is unpredictable."""
    card = Image.new("RGBA", (1200, 630), GRAPE)
    mark = scene(560, background=False)
    card.alpha_composite(mark, (320, 35))
    return card.convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    base = render()
    small = scene(S, flock=False)
    for size in (16, 32, 64, 128, 256, 512):
        for scale, suffix in ((1, ""), (2, "@2x")):
            px = size * scale
            source = base if px >= 128 else small
            source.resize((px, px), Image.LANCZOS).save(
                os.path.join(OUT, f"icon_{size}x{size}{suffix}.png"))
    icns = os.path.join(ROOT, "build", "MultiTofu.icns")
    subprocess.run(["iconutil", "-c", "icns", OUT, "-o", icns], check=True)

    base.resize((512, 512), Image.LANCZOS).save(os.path.join(DOCS, "logo.png"))
    base.resize((128, 128), Image.LANCZOS).save(os.path.join(DOCS, "logo-128.png"))
    small.resize((32, 32), Image.LANCZOS).save(os.path.join(DOCS, "favicon-32.png"))
    base.resize((180, 180), Image.LANCZOS).save(
        os.path.join(DOCS, "apple-touch-icon.png"))
    og_card(base).save(os.path.join(DOCS, "og-card.png"))
    import shutil
    shutil.copy(icns, os.path.join(DOCS, "MultiTofu.icns"))

    # the wheel hub draws this one, so it has to be the transparent mark
    scene(512, background=False).save(os.path.join(APP_ASSETS, "logo.png"))
    print("wrote", icns, "and", DOCS)


if __name__ == "__main__":
    main()
