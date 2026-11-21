#!/usr/bin/env python3
"""MERIDIAN FALLS — a vintage travel poster for a place that isn't there.

Draws the poster 100% procedurally with only the Python standard library:
own raster primitives, own 5x7 bitmap display type, own PNG encoder
(zlib + struct). No network, no downloaded assets, no outside files.
Deterministic: two runs produce byte-identical output.

Usage: python3 main.py
Writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).
"""

import math
import os
import struct
import zlib

W, H = 768, 1024

# ---------------------------------------------------------------- palette
INK      = (18, 38, 58)     # deep navy silhouette / shadow
CREAM    = (247, 232, 200)  # poster cream (type, falls, frame)
PAPER    = (250, 240, 214)
GOLD     = (242, 180, 92)
ORANGE   = (232, 126, 60)
ROSE     = (198, 96, 110)
VIOLET   = (107, 74, 138)
INDIGO   = (35, 43, 82)
TEAL     = (14, 95, 107)
TEAL_DK  = (8, 59, 74)
SEA_DK   = (6, 42, 56)
WHITE    = (255, 250, 235)
FOAM     = (214, 240, 232)

# ---------------------------------------------------------------- buffer
buf = bytearray(W * H * 3)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def rect(x0, y0, x1, y1, c):
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(W, x1); y1 = min(H, y1)
    for y in range(y0, y1):
        i = (y * W + x0) * 3
        for x in range(x0, x1):
            buf[i], buf[i + 1], buf[i + 2] = c
            i += 3


def hline(x0, x1, y, c):
    for x in range(max(0, x0), min(W, x1)):
        px(x, y, c)


def circle(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        for x in range(cx - dx, cx + dx + 1):
            px(x, cy + dy, c)


def ellipse(cx, cy, rx, ry, c):
    for dy in range(-ry, ry + 1):
        t = 1.0 - (dy * dy) / float(ry * ry)
        dx = int(rx * (t ** 0.5)) if t > 0 else 0
        for x in range(cx - dx, cx + dx + 1):
            px(x, cy + dy, c)


def poly(points, c):
    """Scanline-filled polygon (points: list of (x, y))."""
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
        xs = []
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(int(xs[i]), int(xs[i + 1]) + 1):
                px(x, y, c)


def thick_line(x0, y0, x1, y1, r, c):
    """A line drawn as overlapping circles (radius r)."""
    steps = max(abs(x1 - x0), abs(y1 - y0), 1) * 2
    for i in range(steps + 1):
        t = i / steps
        circle(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, c)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(y0, y1, c_top, c_bot):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        c = lerp(c_top, c_bot, t)
        for x in range(W):
            i = (y * W + x) * 3
            buf[i], buf[i + 1], buf[i + 2] = c


# ---------------------------------------------------------------- 5x7 type
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00000", "00100"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
}


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(s, cx, y, scale, color, shadow=None):
    """Centre `s` on x=cx, top at y. Optional drop shadow offset (+3,+4)."""
    x0 = cx - text_w(s, scale) // 2
    if shadow is not None:
        _draw_text_at(s, x0 + 3, y + 4, scale, shadow)
    _draw_text_at(s, x0, y, scale, color)


def _draw_text_at(s, x0, y, scale, color):
    x = x0
    for ch in s:
        g = GLYPHS.get(ch, GLYPHS[" "])
        for r in range(7):
            row = g[r]
            for cix in range(5):
                if row[cix] == "1":
                    rect(x + cix * scale, y + r * scale,
                         x + (cix + 1) * scale, y + (r + 1) * scale, color)
        x += 6 * scale


# ---------------------------------------------------------------- scene
def draw():
    # Sky: indigo -> violet -> orange -> gold, horizon at ~y 640.
    vgrad(0, 340, INDIGO, VIOLET)
    vgrad(340, 520, VIOLET, ORANGE)
    vgrad(520, 660, ORANGE, GOLD)

    # Sun: low, big, cream disc with glow rings over the horizon.
    for r, c in ((150, (238, 150, 80)), (120, (244, 178, 96)),
                 (95, (248, 205, 130))):
        circle(384, 600, r, c)
    circle(384, 600, 72, CREAM)

    # High clouds: flat cream ellipses, upper sky (kept clear of the title).
    for cx, cy, rx, ry in ((150, 300, 120, 26), (210, 282, 90, 22),
                           (640, 330, 100, 20), (560, 352, 70, 18),
                           (700, 400, 80, 18)):
        ellipse(cx, cy, rx, ry, (250, 232, 205))

    # Distant headland, hazy rose, across the horizon.
    poly([(0, 660), (180, 600), (330, 640), (470, 596), (620, 636),
          (768, 606), (768, 660), (0, 660)], ROSE)

    # Sea: teal gradient below the horizon.
    vgrad(660, H, TEAL, SEA_DK)
    # Gold reflection path under the sun, leading the eye to the falls.
    for y in range(664, 936, 16):
        wdt = 26 + (y - 664) // 12
        hline(384 - wdt, 384 + wdt, y, (216, 150, 74))
        hline(384 - wdt, 384 + wdt, y + 2, (232, 178, 96))
    # Wave strokes: pale arcs catching the sunset.
    for y, x0, x1 in ((700, 60, 300), (740, 420, 720), (790, 120, 380),
                      (850, 480, 740), (920, 40, 260), (970, 380, 700)):
        for dx in range(x0, x1, 14):
            hline(dx, dx + 8, y, FOAM)
        hline(x0, x1, y + 3, (10, 74, 88))

    # Main cliff (left): dark silhouette the falls climb from.
    poly([(0, 1024), (0, 780), (90, 700), (210, 640), (300, 560),
          (360, 520), (400, 560), (380, 660), (330, 760), (300, 880),
          (260, 1024)], INK)
    # Right headland, lower.
    poly([(768, 1024), (768, 800), (700, 740), (620, 700), (560, 720),
          (600, 820), (640, 1024)], INK)
    # Cliff-top pines (tiny triangles).
    for tx, ty, s in ((150, 690, 26), (205, 650, 32), (255, 610, 24),
                      (320, 545, 28), (660, 725, 24), (700, 760, 30)):
        poly([(tx, ty - s), (tx - s // 2, ty), (tx + s // 2, ty)], INK)
        rect(tx - 2, ty, tx + 3, ty + 12, INK)

    # --- The impossible landmark: the river climbs to the sky. ---
    # A bright ribbon rises from the sea in a great arc and dissolves
    # into cloud at the top. Quadratic Bezier from the sea (430, 780)
    # through (300, 560) to the cloud (330, 380).
    p0, p1, p2 = (430, 790), (250, 600), (330, 370)
    n = 90
    prev = None
    for i in range(n + 1):
        t = i / n
        x = int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0])
        y = int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
        r = int(26 - 20 * t)  # tapers as it climbs
        circle(x, y, r, CREAM)
        if prev is not None:
            thick_line(prev[0], prev[1], x, y, r, CREAM)
        prev = (x, y)
    # Bright core thread inside the ribbon.
    prev = None
    for i in range(n + 1):
        t = i / n
        x = int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0])
        y = int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
        r = max(2, int(9 - 7 * t))
        circle(x, y, r, WHITE)
        if prev is not None:
            thick_line(prev[0], prev[1], x, y, r, WHITE)
        prev = (x, y)
    # Spray where the falls leave the sea, and mist where they meet cloud.
    # A foam ring marks the exact spot the river lifts off the water.
    for cx, cy, r in ((400, 800, 14), (452, 812, 10), (372, 818, 9),
                      (470, 792, 8), (330, 372, 26), (306, 386, 16),
                      (356, 384, 18), (330, 352, 14)):
        circle(cx, cy, r, CREAM)
    for ang in range(0, 360, 30):
        circle(int(430 + 52 * math.cos(math.radians(ang))),
               int(792 + 16 * math.sin(math.radians(ang))), 5, FOAM)
    for cx, cy, r in ((330, 368, 12), (312, 380, 8), (348, 378, 9)):
        circle(cx, cy, r, WHITE)
    # Rising droplets along the arc.
    for t in (0.15, 0.3, 0.45, 0.6, 0.75, 0.88):
        x = int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0])
        y = int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
        circle(x - 34, y - 6, 3, CREAM)
        circle(x + 32, y + 4, 2, CREAM)

    # Birds.
    for bx, by, s in ((520, 300, 14), (560, 330, 10), (480, 350, 9),
                      (600, 290, 12)):
        thick_line(bx - s, by, bx, by - s // 2, 2, INK)
        thick_line(bx, by - s // 2, bx + s, by, 2, INK)

    # --- Type: the place name carries the poster. ---
    draw_text("MERIDIAN", 384, 78, 13, CREAM, shadow=INK)
    draw_text("FALLS", 384, 190, 11, GOLD, shadow=INK)
    # Thin rules flanking the tagline, bottom band.
    hline(120, 300, 948, CREAM)
    hline(468, 648, 948, CREAM)
    draw_text("WHERE THE RIVER CLIMBS TO THE SKY", 384, 962, 3,
              CREAM, shadow=INK)

    # Vintage double frame.
    for x0, y0, x1, y1, c in ((14, 14, W - 14, H - 14, CREAM),
                              (26, 26, W - 26, H - 26, CREAM)):
        for x in range(x0, x1):
            px(x, y0, c); px(x, y1 - 1, c)
        for y in range(y0, y1):
            px(x0, y, c); px(x1 - 1, y, c)


# ---------------------------------------------------------------- PNG out
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    draw()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(encode_png())
    print("wrote", path)


if __name__ == "__main__":
    main()
