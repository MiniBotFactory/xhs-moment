#!/usr/bin/env python3
"""
xhs-moment — polished minimalist text cards for Xiaohongshu.

Three refined layout styles, each with cover / quote / topics variants.
Subtle film-grain texture and tight typographic composition.

Outputs 3 images (1080 × 1440):
  1. Cover card   — headline + date
  2. Quote card   — text with decorative treatment
  3. Topics card  — hashtag badges
"""

import argparse
import json
import os
import platform
import random
from typing import Callable, List, Tuple

from PIL import Image, ImageDraw, ImageFont

# ── canvas ───────────────────────────────────────────────────

W, H = 1080, 1440
PHI = 0.618

# ── font resolution ──────────────────────────────────────────

_FONT_CANDIDATES = {
    "Darwin": {
        "bold": [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ],
        "light": [
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ],
    },
    "Windows": {
        "bold": [
            "C:\\Windows\\Fonts\\msyhbd.ttc",
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
        ],
        "light": [
            "C:\\Windows\\Fonts\\msyhl.ttc",
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simsun.ttc",
        ],
    },
    "Linux": {
        "bold": [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ],
        "light": [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ],
    },
}


def _resolve_font(style: str, size: int):
    system = platform.system()
    candidates = _FONT_CANDIDATES.get(system, _FONT_CANDIDATES["Linux"])
    for path in candidates.get(style, candidates["light"]):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()


def font(size: int, bold: bool = False):
    return _resolve_font("bold" if bold else "light", size)


# ── text utilities ───────────────────────────────────────────

def text_width(fnt, text: str) -> int:
    bb = fnt.getbbox(text)
    return bb[2] - bb[0]


def wrap_text(text: str, fnt, max_w: int) -> List[str]:
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if cur and text_width(fnt, trial) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def fit_text(text: str, max_w: int, max_lines: int,
             start: int, min_sz: int, bold: bool = True):
    """Choose the largest font size that fits text in max_w x max_lines."""
    sz = start
    while sz >= min_sz:
        fnt = font(sz, bold=bold)
        lines = wrap_text(text, fnt, max_w)
        if len(lines) <= max_lines:
            return fnt, lines, sz
        sz -= 2
    fnt = font(min_sz, bold=bold)
    return fnt, wrap_text(text, fnt, max_w), min_sz


# ── visual effects ───────────────────────────────────────────

def add_grain(img, alpha=0.035):
    """Overlay subtle film-grain noise for warmth and depth."""
    w, h = img.size
    n = w * h
    try:
        raw = random.randbytes(n)
    except AttributeError:  # Python < 3.9
        raw = bytes(random.getrandbits(8) for _ in range(n))
    noise = Image.frombytes("L", (w, h), raw)
    return Image.blend(img, Image.merge("RGB", [noise] * 3), alpha)


def darken(c, amt=20):
    return tuple(max(0, v - amt) for v in c)


def lighten(c, amt=20):
    return tuple(min(255, v + amt) for v in c)


def fill_gradient(img, y0, y1, c_top, c_bot):
    """Full-width vertical gradient from y0 to y1."""
    d = ImageDraw.Draw(img)
    span = max(1, y1 - y0 - 1)
    for y in range(y0, y1):
        t = (y - y0) / span
        c = tuple(int(a + (b - a) * t) for a, b in zip(c_top, c_bot))
        d.line([(0, y), (W - 1, y)], fill=c)


# ── drawing primitives ───────────────────────────────────────

def rrect(d, xy, fill, r=24, outline=None, width=1):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def centered_text(d, lines, fnt, cx, y0, gap, fill):
    y = y0
    for ln in lines:
        d.text((cx, y), ln, font=fnt, fill=fill, anchor="mm")
        y += gap


def badges(d, tags, bg, fg, x, y, max_w,
           align="center", fsz=30, bh=58, px=28, gap=18, rgap=18):
    """Draw hashtag pill badges, wrapping into rows."""
    if not tags:
        tags = ["\u968f\u624b\u8bb0"]
    bf = font(fsz, bold=True)
    items = [(f"# {t}", text_width(bf, f"# {t}") + px * 2) for t in tags]

    rows, row, rw = [], [], 0
    for label, bw in items:
        need = bw + (gap if row else 0)
        if row and rw + need > max_w:
            rows.append((row, rw))
            row, rw = [(label, bw)], bw
        else:
            row.append((label, bw))
            rw += need
    if row:
        rows.append((row, rw))

    cy = y
    for row_items, row_w in rows:
        cx = x + max(0, (max_w - row_w) // 2) if align == "center" else x
        for label, bw in row_items:
            rrect(d, [cx, cy, cx + bw, cy + bh], bg, r=bh // 2)
            d.text((cx + bw // 2, cy + bh // 2),
                   label, font=bf, fill=fg, anchor="mm")
            cx += bw + gap
        cy += bh + rgap
    return cy


# ── palettes ─────────────────────────────────────────────────

PALETTES = {
    "warm": {
        "bg": (255, 248, 240),
        "block": (91, 105, 84),
        "accent": (205, 132, 72),
        "text_dark": (55, 45, 35),
        "text_light": (255, 251, 245),
        "muted": (188, 176, 164),
    },
    "cool": {
        "bg": (238, 242, 248),
        "block": (67, 86, 118),
        "accent": (131, 162, 206),
        "text_dark": (44, 54, 72),
        "text_light": (245, 248, 253),
        "muted": (170, 181, 200),
    },
    "fresh": {
        "bg": (243, 250, 245),
        "block": (58, 120, 88),
        "accent": (230, 195, 80),
        "text_dark": (36, 58, 44),
        "text_light": (247, 253, 249),
        "muted": (168, 196, 178),
    },
    "elegant": {
        "bg": (246, 242, 238),
        "block": (101, 74, 81),
        "accent": (182, 149, 114),
        "text_dark": (70, 50, 54),
        "text_light": (252, 248, 245),
        "muted": (198, 183, 172),
    },
    "dreamy": {
        "bg": (248, 242, 252),
        "block": (137, 112, 157),
        "accent": (217, 163, 189),
        "text_dark": (86, 66, 96),
        "text_light": (252, 247, 255),
        "muted": (205, 188, 218),
    },
    "bold": {
        "bg": (242, 241, 236),
        "block": (48, 51, 58),
        "accent": (215, 192, 73),
        "text_dark": (37, 39, 44),
        "text_light": (250, 248, 242),
        "muted": (170, 171, 165),
    },
}


# ══════════════════════════════════════════════════════════════
# Style: POSTER — full-bleed block, text as cinematic hero
# ══════════════════════════════════════════════════════════════

def cover_poster(text, subtitle, p, path):
    img = Image.new("RGB", (W, H), p["block"])
    fill_gradient(img, 0, H, darken(p["block"], 12), lighten(p["block"], 6))
    d = ImageDraw.Draw(img)

    # hero text — big, bold, centered
    fnt, lines, sz = fit_text(text, W - 200, 3, 72, 36)
    gap = int(sz * 1.65)
    th = gap * (len(lines) - 1)
    ty = int(H * 0.38) - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_light"])

    # accent underline
    uy = ty + th + int(sz * 0.9)
    d.line([W // 2 - 40, uy, W // 2 + 40, uy], fill=p["accent"], width=3)

    # subtitle near bottom
    d.text((W // 2, H - 180), subtitle,
           font=font(26), fill=p["muted"], anchor="mm")
    d.ellipse([W // 2 - 4, H - 120, W // 2 + 4, H - 112], fill=p["accent"])

    img = add_grain(img, alpha=0.04)
    img.save(path, quality=95)


def quote_poster(text, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    # large decorative opening quote mark
    qc = lighten(p["accent"], 50)
    d.text((120, 260), "\u201c", font=font(160, bold=True), fill=qc)

    # quote text
    fnt, lines, sz = fit_text(text, W - 260, 4, 56, 30)
    gap = int(sz * 1.7)
    th = gap * (len(lines) - 1)
    ty = int(H * 0.42) - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_dark"])

    # closing quote mark — lower-right, diagonal composition
    d.text((W - 100, int(H * 0.62)), "\u201d",
           font=font(120, bold=True), fill=qc, anchor="rm")

    img = add_grain(img, alpha=0.025)
    img.save(path, quality=95)


def topics_poster(tags, p, path):
    img = Image.new("RGB", (W, H), p["block"])
    fill_gradient(img, 0, H, p["block"], darken(p["block"], 10))
    d = ImageDraw.Draw(img)

    # header
    d.text((W // 2, 320), "TOPICS",
           font=font(24, bold=True), fill=p["accent"], anchor="mm")
    d.line([W // 2 - 50, 348, W // 2 + 50, 348],
           fill=p["accent"], width=2)

    # badges — centered, vertically balanced
    badges(d, tags, lighten(p["block"], 22), p["text_light"],
           120, 500, W - 240, align="center")

    img = add_grain(img, alpha=0.04)
    img.save(path, quality=95)


# ══════════════════════════════════════════════════════════════
# Style: SPLIT — golden-ratio horizontal division
# ══════════════════════════════════════════════════════════════

def cover_split(text, subtitle, p, path):
    split_y = int(H * 0.58)
    img = Image.new("RGB", (W, H), p["bg"])
    fill_gradient(img, 0, split_y, darken(p["block"], 8), p["block"])
    d = ImageDraw.Draw(img)

    # accent bar at split
    d.rectangle([0, split_y, W, split_y + 4], fill=p["accent"])

    # text centered in top block
    fnt, lines, sz = fit_text(text, W - 220, 3, 64, 34)
    gap = int(sz * 1.6)
    th = gap * (len(lines) - 1)
    ty = split_y // 2 - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_light"])

    # thin line below text (only if room)
    uy = ty + th + int(sz * 0.8)
    if uy < split_y - 30:
        d.line([W // 2 - 36, uy, W // 2 + 36, uy],
               fill=p["accent"], width=2)

    # subtitle in bottom area
    d.text((120, split_y + 80), subtitle,
           font=font(26), fill=p["text_dark"], anchor="lm")

    img = add_grain(img, alpha=0.035)
    img.save(path, quality=95)


def quote_split(text, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    # elegant frame
    m = 100
    box = [m, m + 40, W - m, H - m - 40]
    rrect(d, box, None, r=28, outline=p["muted"], width=2)

    # decorative quote marks
    qc = lighten(p["accent"], 40)
    d.text((m + 56, m + 80), "\u201c",
           font=font(120, bold=True), fill=qc)

    # text
    fnt, lines, sz = fit_text(text, W - m * 2 - 140, 4, 50, 28)
    gap = int(sz * 1.65)
    th = gap * (len(lines) - 1)
    cy = (box[1] + box[3]) // 2
    ty = cy - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_dark"])

    d.text((W - m - 56, box[3] - 60), "\u201d",
           font=font(90, bold=True), fill=qc, anchor="rm")

    img = add_grain(img, alpha=0.025)
    img.save(path, quality=95)


def topics_split(tags, p, path):
    strip_h = int(H * 0.30)
    img = Image.new("RGB", (W, H), p["bg"])
    fill_gradient(img, 0, strip_h, darken(p["block"], 6), p["block"])
    d = ImageDraw.Draw(img)

    # accent bar
    d.rectangle([0, strip_h, W, strip_h + 3], fill=p["accent"])

    # label in dark strip
    d.text((W // 2, strip_h // 2), "TOPICS",
           font=font(26, bold=True), fill=p["text_light"], anchor="mm")

    # badges in light area
    badges(d, tags, darken(p["bg"], 20), p["text_dark"],
           120, strip_h + 100, W - 240, align="left")

    img = add_grain(img, alpha=0.03)
    img.save(path, quality=95)


# ══════════════════════════════════════════════════════════════
# Style: CARD — floating rounded card on light background
# ══════════════════════════════════════════════════════════════

_CARD_MX = 72       # horizontal margin
_CARD_MT = 100      # top margin
_CARD_MB = 140      # bottom margin (heavier for visual gravity)


def _card_rect():
    return [_CARD_MX, _CARD_MT, W - _CARD_MX, H - _CARD_MB]


def cover_card(text, subtitle, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    card = _card_rect()
    rrect(d, card, p["block"], r=28)
    cw = card[2] - card[0]
    ch = card[3] - card[1]

    # text centered in card
    fnt, lines, sz = fit_text(text, cw - 160, 3, 64, 34)
    gap = int(sz * 1.6)
    th = gap * (len(lines) - 1)
    ty = card[1] + int(ch * 0.38) - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_light"])

    # accent line
    uy = ty + th + int(sz * 0.8)
    d.line([W // 2 - 36, uy, W // 2 + 36, uy], fill=p["accent"], width=2)

    # subtitle inside card
    d.text((W // 2, card[3] - 80), subtitle,
           font=font(24), fill=p["muted"], anchor="mm")

    # accent dot in the bg frame area
    d.ellipse([W // 2 - 4, H - _CARD_MB // 2 - 4,
               W // 2 + 4, H - _CARD_MB // 2 + 4], fill=p["accent"])

    img = add_grain(img, alpha=0.035)
    img.save(path, quality=95)


def quote_card(text, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    card = _card_rect()
    rrect(d, card, p["block"], r=28)
    cw = card[2] - card[0]
    ch = card[3] - card[1]

    # decorative quote marks
    qc = lighten(p["accent"], 30)
    d.text((card[0] + 60, card[1] + 80), "\u201c",
           font=font(120, bold=True), fill=qc)

    # text
    fnt, lines, sz = fit_text(text, cw - 180, 4, 50, 28)
    gap = int(sz * 1.65)
    th = gap * (len(lines) - 1)
    cy = card[1] + ch // 2
    ty = cy - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_light"])

    d.text((card[2] - 60, ty + th + 50), "\u201d",
           font=font(90, bold=True), fill=qc, anchor="rm")

    img = add_grain(img, alpha=0.035)
    img.save(path, quality=95)


def topics_card(tags, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    card = _card_rect()
    rrect(d, card, p["block"], r=28)
    cw = card[2] - card[0]

    # header
    d.text((W // 2, card[1] + 120), "TOPICS",
           font=font(24, bold=True), fill=p["accent"], anchor="mm")
    d.line([W // 2 - 50, card[1] + 148, W // 2 + 50, card[1] + 148],
           fill=p["accent"], width=2)

    # badges
    badges(d, tags, lighten(p["block"], 22), p["text_light"],
           card[0] + 60, card[1] + 230, cw - 120, align="center")

    img = add_grain(img, alpha=0.035)
    img.save(path, quality=95)


# ══════════════════════════════════════════════════════════════
# Style: MEMO — iOS Notes screenshot aesthetic
# ══════════════════════════════════════════════════════════════

_MEMO_H = 88
_MEMO_BLUE = (0, 122, 255)
_MEMO_HDR = (246, 246, 246)
_MEMO_RULE = (228, 228, 228)


def _memo_header(d):
    """Draw iOS Notes header bar."""
    d.rectangle([0, 0, W, _MEMO_H], fill=_MEMO_HDR)
    d.line([0, _MEMO_H, W, _MEMO_H], fill=(215, 215, 215), width=1)
    cy = _MEMO_H // 2
    d.text((28, cy), "〈", font=font(28), fill=_MEMO_BLUE, anchor="lm")
    d.text((56, cy), "备忘录", font=font(32), fill=_MEMO_BLUE, anchor="lm")
    # share icon — square + upward arrow
    ix = W - 130
    s = 12
    d.rectangle([ix - s, cy - s + 6, ix + s, cy + s + 6],
                outline=_MEMO_BLUE, width=2)
    d.line([ix, cy + 3, ix, cy - s - 5], fill=_MEMO_BLUE, width=2)
    d.polygon([(ix - 5, cy - s), (ix, cy - s - 7), (ix + 5, cy - s)],
              fill=_MEMO_BLUE)
    # more button — encircled dots
    mx = W - 55
    d.ellipse([mx - 17, cy - 17, mx + 17, cy + 17],
              outline=_MEMO_BLUE, width=2)
    for dx in [-7, 0, 7]:
        d.ellipse([mx + dx - 2, cy - 2, mx + dx + 2, cy + 2],
                  fill=_MEMO_BLUE)


def _hl_text(d, lines, fnt, x0, y0, gap, fg, hl_bg, hl_s, hl_e):
    """Left-aligned text with highlight rectangles on chars [hl_s, hl_e)."""
    bb = fnt.getbbox("测")
    ch_h = bb[3] - bb[1]
    y_off = bb[1]
    idx, y = 0, y0
    for ln in lines:
        cells = []
        x = x0
        for ch in ln:
            cw = int(fnt.getlength(ch))
            cells.append((ch, x, cw, hl_s <= idx < hl_e))
            x += cw
            idx += 1
        for _, cx, cw, hl in cells:
            if hl:
                d.rectangle([cx - 2, y + y_off - 4,
                             cx + cw + 2, y + y_off + ch_h + 4],
                            fill=hl_bg)
        for ch, cx, _, _ in cells:
            d.text((cx, y), ch, font=fnt, fill=fg)
        y += gap
    return y


def cover_memo(text, subtitle, p, path):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    _memo_header(d)

    mx = 72
    fnt, lines, sz = fit_text(text, W - mx * 2, 4, 78, 38)
    gap = int(sz * 1.85)
    y0 = _MEMO_H + 140

    n = len(text)
    hl_len = max(2, n * 2 // 5)
    _hl_text(d, lines, fnt, mx, y0, gap,
             (30, 30, 30), lighten(p["accent"], 80),
             n - hl_len, n)

    d.text((mx, H - 150), subtitle, font=font(26), fill=(170, 170, 170))

    img = add_grain(img, alpha=0.015)
    img.save(path, quality=95)


def quote_memo(text, p, path):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    _memo_header(d)

    mx = 80
    fnt, lines, sz = fit_text(text, W - mx * 2, 6, 52, 28, bold=False)
    gap = int(sz * 2.4)
    th = gap * (len(lines) - 1)
    y0 = int(H * 0.36) - th // 2

    # ruled lines aligned with text spacing
    rule_y = y0 + sz + 8
    ry = rule_y
    while ry - gap > _MEMO_H + 10:
        ry -= gap
    while ry < H - 30:
        if ry > _MEMO_H + 5:
            d.line([55, ry, W - 55, ry], fill=_MEMO_RULE, width=1)
        ry += gap

    for i, ln in enumerate(lines):
        d.text((mx, y0 + i * gap), ln, font=fnt, fill=(45, 45, 45))

    img = add_grain(img, alpha=0.015)
    img.save(path, quality=95)


def topics_memo(tags, p, path):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    _memo_header(d)

    d.text((W // 2, 280), "TOPICS",
           font=font(24, bold=True), fill=(160, 160, 160), anchor="mm")
    d.line([W // 2 - 40, 306, W // 2 + 40, 306],
           fill=(200, 200, 200), width=2)

    badges(d, tags, (238, 238, 238), (80, 80, 80),
           120, 430, W - 240)

    img = add_grain(img, alpha=0.015)
    img.save(path, quality=95)


# ══════════════════════════════════════════════════════════════
# Style: HIGHLIGHT — bold accent-color quote with sparkles
# ══════════════════════════════════════════════════════════════

def _star4(d, cx, cy, r, fill):
    """Draw a 4-pointed sparkle star."""
    ir = r * 0.28
    d.polygon([
        (cx, cy - r), (cx + ir, cy - ir),
        (cx + r, cy), (cx + ir, cy + ir),
        (cx, cy + r), (cx - ir, cy + ir),
        (cx - r, cy), (cx - ir, cy - ir),
    ], fill=fill)


def _sparkles(d, seed, color, zones=None):
    """Place sparkle stars with slight jitter."""
    rng = random.Random(seed)
    if zones is None:
        zones = [
            (90, 220, 28), (920, 310, 22), (150, 920, 16),
            (870, 1060, 24), (960, 190, 12), (110, 1170, 18),
        ]
    for bx, by, br in zones:
        _star4(d, bx + rng.randint(-15, 15), by + rng.randint(-15, 15),
               br + rng.randint(-3, 3), color)


def cover_highlight(text, subtitle, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    # large decorative quote marks
    qc = lighten(p["accent"], 60)
    d.text((60, 160), "\u201c", font=font(200, bold=True), fill=qc)
    d.text((W - 60, H - 380), "\u201d",
           font=font(200, bold=True), fill=qc, anchor="rm")

    _sparkles(d, text, lighten(p["accent"], 40))

    # hero text in darkened accent color
    tc = darken(p["accent"], 40)
    fnt, lines, sz = fit_text(text, W - 200, 3, 72, 36)
    gap = int(sz * 1.7)
    th = gap * (len(lines) - 1)
    ty = int(H * 0.40) - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, tc)

    # CTA at bottom
    d.text((W // 2, H - 180), "右划查看全文  →",
           font=font(26), fill=p["muted"], anchor="mm")

    img = add_grain(img, alpha=0.02)
    img.save(path, quality=95)


def quote_highlight(text, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    # accent border frame
    m = 90
    rrect(d, [m, m + 30, W - m, H - m - 30], None, r=20,
          outline=lighten(p["accent"], 30), width=3)

    # corner sparkles
    sc = lighten(p["accent"], 50)
    _star4(d, m + 40, m + 70, 16, sc)
    _star4(d, W - m - 40, H - m - 60, 14, sc)

    qc = lighten(p["accent"], 50)
    d.text((m + 60, m + 100), "\u201c",
           font=font(120, bold=True), fill=qc)

    fnt, lines, sz = fit_text(text, W - m * 2 - 140, 4, 50, 28)
    gap = int(sz * 1.65)
    th = gap * (len(lines) - 1)
    ty = H // 2 - th // 2
    centered_text(d, lines, fnt, W // 2, ty, gap, p["text_dark"])

    d.text((W - m - 60, ty + th + 50), "\u201d",
           font=font(90, bold=True), fill=qc, anchor="rm")

    img = add_grain(img, alpha=0.02)
    img.save(path, quality=95)


def topics_highlight(tags, p, path):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    _sparkles(d, "topics", lighten(p["accent"], 50),
              zones=[(140, 350, 20), (880, 400, 16),
                     (200, 1050, 14), (850, 980, 18)])

    d.text((W // 2, 360), "TOPICS",
           font=font(24, bold=True), fill=darken(p["accent"], 20),
           anchor="mm")
    d.line([W // 2 - 50, 388, W // 2 + 50, 388],
           fill=p["accent"], width=2)

    badges(d, tags, lighten(p["accent"], 60), p["text_dark"],
           120, 500, W - 240)

    img = add_grain(img, alpha=0.02)
    img.save(path, quality=95)


# ══════════════════════════════════════════════════════════════
# Style registry & mood system
# ══════════════════════════════════════════════════════════════

STYLE_CHOICES = ["poster", "split", "card", "memo", "highlight"]

STYLE_RENDERERS = {
    "poster":    (cover_poster,    quote_poster,    topics_poster),
    "split":     (cover_split,     quote_split,     topics_split),
    "card":      (cover_card,      quote_card,      topics_card),
    "memo":      (cover_memo,      quote_memo,      topics_memo),
    "highlight": (cover_highlight, quote_highlight,  topics_highlight),
}

PALETTE_CHOICES = list(PALETTES.keys())

MOOD_CHOICES = ["auto", "thinking", "healing", "attitude",
                "romantic", "fresh", "neutral"]

MOOD_KEYWORDS = {
    "thinking": ["思考", "判断", "选择", "认知", "复盘", "问题",
                 "逻辑", "决定", "为什么", "how", "why", "think"],
    "healing":  ["治愈", "温柔", "舒服", "安静", "晚安", "松弛",
                 "放松", "日常", "平静", "夕阳", "咖啡"],
    "attitude": ["不", "别", "必须", "狠狠", "清醒", "边界",
                 "态度", "自信", "表达", "野心", "酷", "行动"],
    "romantic": ["浪漫", "喜欢", "想念", "花", "月亮", "心动",
                 "温柔", "少女", "梦", "春天"],
    "fresh":    ["元气", "开心", "出发", "早安", "活力", "新鲜",
                 "轻盈", "清晨", "晴天", "夏天"],
}

STYLE_WEIGHTS = {"poster": 2, "split": 3, "card": 2, "memo": 2, "highlight": 2}

STYLE_BOOSTS = {
    "thinking": {"poster": 2, "split": 3, "card": 2, "memo": 2, "highlight": 1},
    "healing":  {"poster": 1, "split": 2, "card": 3, "memo": 3, "highlight": 2},
    "attitude": {"poster": 3, "split": 2, "card": 1, "memo": 1, "highlight": 3},
    "romantic": {"poster": 1, "split": 2, "card": 3, "memo": 1, "highlight": 2},
    "fresh":    {"poster": 2, "split": 3, "card": 2, "memo": 2, "highlight": 1},
    "neutral":  {"poster": 1, "split": 1, "card": 1, "memo": 1, "highlight": 1},
}

PALETTE_BOOSTS = {
    "thinking": {"cool": 3, "elegant": 2, "bold": 2,
                 "warm": 1, "fresh": 1, "dreamy": 1},
    "healing":  {"warm": 3, "elegant": 2, "fresh": 2,
                 "cool": 1, "dreamy": 1, "bold": 1},
    "attitude": {"bold": 3, "cool": 2, "elegant": 1,
                 "warm": 1, "fresh": 1, "dreamy": 1},
    "romantic": {"dreamy": 3, "elegant": 2, "warm": 2,
                 "cool": 1, "fresh": 1, "bold": 1},
    "fresh":    {"fresh": 3, "warm": 2, "dreamy": 1,
                 "cool": 1, "elegant": 1, "bold": 1},
    "neutral":  {n: 1 for n in PALETTE_CHOICES},
}


def infer_mood(text: str, tags: list) -> str:
    corpus = f"{text} {' '.join(tags)}".lower()
    scores = {m: sum(1 for kw in kws if kw.lower() in corpus)
              for m, kws in MOOD_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


def choose_style(style: str, mood: str, seed: str) -> str:
    if style != "auto":
        return style
    rng = random.Random(seed if seed else None)
    boosts = STYLE_BOOSTS.get(mood, STYLE_BOOSTS["neutral"])
    weights = [STYLE_WEIGHTS[s] * boosts.get(s, 1) for s in STYLE_CHOICES]
    return rng.choices(STYLE_CHOICES, weights=weights, k=1)[0]


def choose_palette(palette: str, style: str, mood: str, seed: str) -> str:
    if palette != "auto":
        return palette
    rng = random.Random(f"{seed}::pal::{style}::{mood}" if seed else None)
    boosts = PALETTE_BOOSTS.get(mood, PALETTE_BOOSTS["neutral"])
    weights = [boosts.get(n, 1) for n in PALETTE_CHOICES]
    return rng.choices(PALETTE_CHOICES, weights=weights, k=1)[0]


def add_meta(out_dir, palette, style, mood, text, subtitle, tags):
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"palette": palette, "style": style, "mood": mood,
                   "text": text, "subtitle": subtitle, "hashtags": tags},
                  f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description="Generate minimalist Xiaohongshu text cards")
    ap.add_argument("--text", required=True, help="Quote / key phrase")
    ap.add_argument("--subtitle", default="", help="Date or signature")
    ap.add_argument("--palette", default="auto",
                    choices=["auto"] + PALETTE_CHOICES)
    ap.add_argument("--style", default="auto",
                    choices=["auto"] + STYLE_CHOICES)
    ap.add_argument("--mood", default="auto", choices=MOOD_CHOICES)
    ap.add_argument("--seed", default="",
                    help="Random seed for reproducibility")
    ap.add_argument("--hashtags", default="",
                    help="Comma-separated tags")
    ap.add_argument("--output-dir", default="/tmp/xhs-moment")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    tags = ([t.strip() for t in args.hashtags.split(",") if t.strip()]
            if args.hashtags else ["\u968f\u624b\u8bb0"])
    subtitle = args.subtitle or "\u968f\u624b\u8bb0"

    seed_basis = args.seed or args.text
    mood = (infer_mood(args.text, tags)
            if args.mood == "auto" else args.mood)
    style = choose_style(args.style, mood, seed_basis)
    pal_name = choose_palette(args.palette, style, mood, seed_basis)
    pal = PALETTES[pal_name]

    cover_fn, quote_fn, topics_fn = STYLE_RENDERERS[style]
    paths = [os.path.join(args.output_dir, f"moment-{i}.jpg")
             for i in range(1, 4)]

    cover_fn(args.text, subtitle, pal, paths[0])
    quote_fn(args.text, pal, paths[1])
    topics_fn(tags, pal, paths[2])
    add_meta(args.output_dir, pal_name, style, mood,
             args.text, subtitle, tags)

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
