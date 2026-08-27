"""Draw the Multi-Tofu app icon and build the .icns."""
import os
import subprocess

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "icon.iconset")

GRAPE = (74, 64, 118)
GRAPE_DEEP = (52, 44, 88)
CREAM = (255, 246, 232)
SUNNY = (255, 201, 74)
MINT = (95, 224, 176)
INK = (46, 38, 80)
BLUSH = (255, 158, 168)

S = 1024


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def render():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = S * 0.06
    rounded(d, (pad, pad, S - pad, S - pad), radius=S * 0.22, fill=GRAPE)
    rounded(d, (pad, pad, S - pad, S * 0.55), radius=S * 0.22, fill=(88, 76, 138))
    rounded(d, (pad, pad, S - pad, S - pad), radius=S * 0.22, fill=None)

    # body
    cx, cy = S / 2, S * 0.58
    rw, rh = S * 0.30, S * 0.27
    d.ellipse((cx - rw, cy - rh, cx + rw, cy + rh), fill=CREAM,
              outline=INK, width=int(S * 0.022))

    # head
    hx, hy = S / 2, S * 0.36
    hr = S * 0.20
    d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=CREAM,
              outline=INK, width=int(S * 0.022))

    # tuft
    d.ellipse((hx - S * 0.045, hy - hr - S * 0.075, hx + S * 0.045, hy - hr + S * 0.03),
              fill=MINT, outline=INK, width=int(S * 0.018))

    # eyes
    er = S * 0.028
    for dx in (-S * 0.072, S * 0.072):
        d.ellipse((hx + dx - er, hy - er - S * 0.01, hx + dx + er, hy + er - S * 0.01),
                  fill=INK)

    # blush
    br = S * 0.030
    for dx in (-S * 0.135, S * 0.135):
        d.ellipse((hx + dx - br, hy + S * 0.045 - br, hx + dx + br, hy + S * 0.045 + br),
                  fill=BLUSH)

    # beak
    d.polygon([(hx - S * 0.042, hy + S * 0.045),
               (hx + S * 0.042, hy + S * 0.045),
               (hx, hy + S * 0.115)], fill=SUNNY, outline=INK)

    # feet
    for dx in (-S * 0.10, S * 0.10):
        d.line([(cx + dx, cy + rh - S * 0.02), (cx + dx, cy + rh + S * 0.045)],
               fill=SUNNY, width=int(S * 0.028))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    base = render()
    for size in (16, 32, 64, 128, 256, 512):
        for scale, suffix in ((1, ""), (2, "@2x")):
            px = size * scale
            base.resize((px, px), Image.LANCZOS).save(
                os.path.join(OUT, f"icon_{size}x{size}{suffix}.png"))
    icns = os.path.join(ROOT, "build", "MultiTofu.icns")
    subprocess.run(["iconutil", "-c", "icns", OUT, "-o", icns], check=True)
    print("wrote", icns)


if __name__ == "__main__":
    main()
