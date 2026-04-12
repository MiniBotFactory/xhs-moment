#!/usr/bin/env python3
"""
xhs-moment image generator — minimalist Xiaohongshu text cards.

Design goals:
- lots of whitespace
- restrained typography
- limited color usage
- golden-ratio-driven composition
- multiple layout schemes to avoid repetition

Outputs 3 images (1080x1440):
  1. Cover card
  2. Quote/detail card
  3. Topics card
"""
import argparse
import json
import os
import platform
import random
from typing import Callable, List, Tuple

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440
PHI = 0.618
GOLDEN_Y = int(H * PHI)
GOLDEN_X = int(W * PHI)

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
        "bg": (241, 251, 245),
        "block": (76, 134, 97),
        "accent": (219, 187, 87),
        "text_dark": (39, 62, 46),
        "text_light": (247, 253, 249),
        "muted": (175, 199, 183),
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

STYLE_CHOICES = [
    "golden-split",
    "floating-card",
    "quiet-corner",
    "centered-balance",
]


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


def text_width(fnt, text: str) -> int:
    box = fnt.getbbox(text)
    return box[2] - box[0]


def wrap_text(text: str, fnt, max_width: int) -> List[str]:
    lines, current = [], ""
    for ch in text:
        trial = current + ch
        if current and text_width(fnt, trial) > max_width:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def fit_text(text: str, max_width: int, max_lines: int, start: int, min_size: int, bold: bool = True):
    size = start
    while size >= min_size:
        fnt = font(size, bold=bold)
        lines = wrap_text(text, fnt, max_width)
        if len(lines) <= max_lines:
            return fnt, lines, size
        size -= 2
    fnt = font(min_size, bold=bold)
    return fnt, wrap_text(text, fnt, max_width), min_size


def draw_rounded_rect(d, xy, fill, radius=24, outline=None, width=1):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_lines_center(d, lines: List[str], fnt, cx: int, start_y: int, line_gap: int, fill):
    y = start_y
    for line in lines:
        d.text((cx, y), line, font=fnt, fill=fill, anchor="mm")
        y += line_gap


def draw_lines_left(d, lines: List[str], fnt, x: int, start_y: int, line_gap: int, fill):
    y = start_y
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill, anchor="lm")
        y += line_gap


def sparse_badges(d, tags: List[str], p: dict, x: int, y: int, max_width: int, align: str = "left"):
    if not tags:
        tags = ["随手记"]
    badge_font = font(28, bold=True)
    badge_h, pad_x, gap, row_gap = 54, 26, 18, 18
    badges = [(f"# {t}", text_width(badge_font, f"# {t}") + pad_x * 2) for t in tags]

    rows, row, row_w = [], [], 0
    for label, bw in badges:
        need = bw + (gap if row else 0)
        if row and row_w + need > max_width:
            rows.append((row, row_w))
            row, row_w = [(label, bw)], bw
        else:
            row.append((label, bw))
            row_w += need
    if row:
        rows.append((row, row_w))

    current_y = y
    for row, row_w in rows:
        current_x = x if align == "left" else x + max(0, (max_width - row_w) // 2)
        for label, bw in row:
            draw_rounded_rect(d, [current_x, current_y, current_x + bw, current_y + badge_h], p["bg"], radius=badge_h // 2)
            d.text((current_x + bw // 2, current_y + badge_h // 2), label, font=badge_font, fill=p["text_dark"], anchor="mm")
            current_x += bw + gap
        current_y += badge_h + row_gap


def add_meta(output_dir: str, palette: str, style: str, text: str, subtitle: str, tags: List[str]):
    meta = {
        "palette": palette,
        "style": style,
        "text": text,
        "subtitle": subtitle,
        "hashtags": tags,
    }
    with open(os.path.join(output_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ----- cover layouts -----
def cover_golden_split(text: str, subtitle: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    split_y = int(H * PHI)
    d.rectangle([0, 0, W, split_y], fill=p["block"])
    d.rectangle([0, split_y - 6, W, split_y], fill=p["accent"])

    fnt, lines, size = fit_text(text, W - 240, 3, 46, 30)
    gap = int(size * 1.55)
    total_h = gap * (len(lines) - 1)
    start_y = split_y // 2 - total_h // 2
    draw_lines_center(d, lines, fnt, W // 2, start_y, gap, p["text_light"])

    d.line([W // 2 - 64, int(split_y * 0.78), W // 2 + 64, int(split_y * 0.78)], fill=p["accent"], width=3)
    d.text((120, split_y + 92), subtitle, font=font(24), fill=p["text_dark"], anchor="lm")
    d.text((W - 120, H - 96), "xhs moment", font=font(20), fill=p["muted"], anchor="rm")
    img.save(path, quality=95)


def cover_floating_card(text: str, subtitle: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    card = [96, 120, int(W * 0.72), int(H * 0.56)]
    draw_rounded_rect(d, card, p["block"], radius=34)
    d.rectangle([card[0], card[1], card[0] + 10, card[3]], fill=p["accent"])
    d.rectangle([W - 170, 94, W - 108, 156], fill=p["accent"])

    inner_w = card[2] - card[0] - 130
    fnt, lines, size = fit_text(text, inner_w, 4, 42, 28)
    gap = int(size * 1.5)
    draw_lines_left(d, lines, fnt, card[0] + 60, card[1] + 80, gap, p["text_light"])

    d.text((card[0] + 60, card[3] - 72), subtitle, font=font(24), fill=p["text_light"], anchor="lm")
    d.line([96, GOLDEN_Y, W - 96, GOLDEN_Y], fill=p["muted"], width=1)
    img.save(path, quality=95)


def cover_quiet_corner(text: str, subtitle: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    d.line([140, 110, 140, H - 150], fill=p["accent"], width=4)
    draw_rounded_rect(d, [W - 212, 106, W - 122, 196], None, radius=18, outline=p["block"], width=2)

    fnt, lines, size = fit_text(text, W - 320, 4, 40, 28)
    gap = int(size * 1.55)
    start_y = GOLDEN_Y - gap
    draw_lines_left(d, lines, fnt, 190, start_y, gap, p["text_dark"])

    d.text((190, H - 136), subtitle, font=font(24), fill=p["muted"], anchor="lm")
    d.text((W - 110, H - 120), "01", font=font(22, bold=True), fill=p["muted"], anchor="rm")
    img.save(path, quality=95)


def cover_centered_balance(text: str, subtitle: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    panel_w, panel_h = int(W * 0.6), int(H * 0.23)
    x0 = (W - panel_w) // 2
    y0 = int(H * 0.24)
    draw_rounded_rect(d, [x0, y0, x0 + panel_w, y0 + panel_h], None, radius=28, outline=p["block"], width=2)
    d.line([x0 + 44, y0 + 42, x0 + panel_w - 44, y0 + 42], fill=p["accent"], width=2)

    fnt, lines, size = fit_text(text, panel_w - 140, 3, 40, 28)
    gap = int(size * 1.5)
    total_h = gap * (len(lines) - 1)
    start_y = y0 + panel_h // 2 - total_h // 2 + 12
    draw_lines_center(d, lines, fnt, W // 2, start_y, gap, p["text_dark"])

    d.text((W // 2, y0 + panel_h + 110), subtitle, font=font(24), fill=p["text_dark"], anchor="mm")
    d.ellipse([W // 2 - 8, GOLDEN_Y - 8, W // 2 + 8, GOLDEN_Y + 8], fill=p["accent"])
    img.save(path, quality=95)


# ----- quote card layouts -----
def quote_golden_split(text: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    box = [120, 150, W - 120, int(H * 0.72)]
    draw_rounded_rect(d, box, None, radius=30, outline=p["muted"], width=2)
    d.text((170, 210), "“", font=font(120, bold=True), fill=p["accent"])

    fnt, lines, size = fit_text(text, W - 320, 4, 40, 28)
    gap = int(size * 1.6)
    total_h = gap * (len(lines) - 1)
    start_y = (box[1] + box[3]) // 2 - total_h // 2
    draw_lines_center(d, lines, fnt, W // 2, start_y, gap, p["text_dark"])
    d.text((W - 170, box[3] - 50), "”", font=font(90, bold=True), fill=p["accent"], anchor="rm")
    img.save(path, quality=95)


def quote_floating_card(text: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([92, 108, 116, 300], fill=p["accent"])
    d.rectangle([W - 210, H - 220, W - 120, H - 130], fill=p["block"])

    fnt, lines, size = fit_text(text, int(W * 0.55), 5, 38, 26)
    gap = int(size * 1.58)
    draw_lines_left(d, lines, fnt, 160, 240, gap, p["text_dark"])
    d.text((160, H - 150), "keep it simple", font=font(20), fill=p["muted"], anchor="lm")
    img.save(path, quality=95)


def quote_quiet_corner(text: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["block"])
    d = ImageDraw.Draw(img)
    d.rectangle([90, 90, W - 90, H - 90], outline=p["accent"], width=2)

    fnt, lines, size = fit_text(text, W - 320, 4, 38, 26)
    gap = int(size * 1.62)
    total_h = gap * (len(lines) - 1)
    start_y = GOLDEN_Y - total_h // 2 - 20
    draw_lines_left(d, lines, fnt, 160, start_y, gap, p["text_light"])
    d.text((160, 138), "NOTE", font=font(22, bold=True), fill=p["accent"], anchor="lm")
    img.save(path, quality=95)


def quote_centered_balance(text: str, p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    d.line([140, GOLDEN_Y, W - 140, GOLDEN_Y], fill=p["muted"], width=1)
    d.line([W // 2, 170, W // 2, H - 170], fill=p["muted"], width=1)

    fnt, lines, size = fit_text(text, W - 340, 4, 38, 26)
    gap = int(size * 1.6)
    total_h = gap * (len(lines) - 1)
    start_y = GOLDEN_Y - total_h // 2
    draw_lines_center(d, lines, fnt, W // 2, start_y, gap, p["text_dark"])
    d.ellipse([W // 2 - 10, GOLDEN_Y - 10, W // 2 + 10, GOLDEN_Y + 10], fill=p["accent"])
    img.save(path, quality=95)


# ----- topics card layouts -----
def topics_golden_split(tags: List[str], p: dict, path: str):
    img = Image.new("RGB", (W, H), p["block"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(H * 0.74), W, H], fill=p["bg"])
    d.text((W // 2, 182), "TOPICS", font=font(28, bold=True), fill=p["text_light"], anchor="mm")
    sparse_badges(d, tags, p, 120, 300, W - 240, align="center")
    d.text((120, H - 120), "minimal / whitespace / calm", font=font(20), fill=p["text_dark"], anchor="lm")
    img.save(path, quality=95)


def topics_floating_card(tags: List[str], p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    card = [120, 180, W - 120, int(H * 0.66)]
    draw_rounded_rect(d, card, p["block"], radius=32)
    d.text((card[0] + 56, card[1] + 56), "话题", font=font(26, bold=True), fill=p["text_light"], anchor="lm")
    sparse_badges(d, tags, {**p, "bg": p["bg"], "text_dark": p["text_dark"]}, card[0] + 56, card[1] + 120, card[2] - card[0] - 112, align="left")
    img.save(path, quality=95)


def topics_quiet_corner(tags: List[str], p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    d.line([150, 120, 150, H - 120], fill=p["accent"], width=4)
    d.text((210, 150), "Tags", font=font(24, bold=True), fill=p["text_dark"], anchor="lm")
    sparse_badges(d, tags, p, 210, 250, W - 320, align="left")
    img.save(path, quality=95)


def topics_centered_balance(tags: List[str], p: dict, path: str):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    panel = [170, 260, W - 170, int(H * 0.78)]
    draw_rounded_rect(d, panel, None, radius=28, outline=p["block"], width=2)
    d.text((W // 2, 210), "topic set", font=font(22), fill=p["muted"], anchor="mm")
    sparse_badges(d, tags, p, panel[0] + 40, panel[1] + 60, panel[2] - panel[0] - 80, align="center")
    img.save(path, quality=95)


STYLE_RENDERERS: dict[str, Tuple[Callable, Callable, Callable]] = {
    "golden-split": (cover_golden_split, quote_golden_split, topics_golden_split),
    "floating-card": (cover_floating_card, quote_floating_card, topics_floating_card),
    "quiet-corner": (cover_quiet_corner, quote_quiet_corner, topics_quiet_corner),
    "centered-balance": (cover_centered_balance, quote_centered_balance, topics_centered_balance),
}


def choose_style(style: str, seed: str) -> str:
    if style != "auto":
        return style
    rng = random.Random()
    if seed:
        rng.seed(seed)
    return rng.choice(STYLE_CHOICES)


def main():
    ap = argparse.ArgumentParser(description="Generate minimalist Xiaohongshu text cards")
    ap.add_argument("--text", required=True, help="Quote / key phrase")
    ap.add_argument("--subtitle", default="", help="Subtitle (date / signature)")
    ap.add_argument("--palette", default="warm", choices=list(PALETTES.keys()))
    ap.add_argument("--style", default="auto", choices=["auto"] + STYLE_CHOICES, help="Layout style. auto = random pick")
    ap.add_argument("--seed", default="", help="Optional random seed for reproducible auto style")
    ap.add_argument("--hashtags", default="", help="Comma-separated hashtags")
    ap.add_argument("--output-dir", default="/tmp/xhs-moment")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    palette = PALETTES[args.palette]
    tags = [t.strip() for t in args.hashtags.split(",") if t.strip()] if args.hashtags else ["随手记"]
    subtitle = args.subtitle or "随手记"
    style = choose_style(args.style, args.seed or args.text)
    cover_fn, quote_fn, topics_fn = STYLE_RENDERERS[style]

    outputs = [
        os.path.join(args.output_dir, "moment-1.jpg"),
        os.path.join(args.output_dir, "moment-2.jpg"),
        os.path.join(args.output_dir, "moment-3.jpg"),
    ]

    cover_fn(args.text, subtitle, palette, outputs[0])
    quote_fn(args.text, palette, outputs[1])
    topics_fn(tags, palette, outputs[2])
    add_meta(args.output_dir, args.palette, style, args.text, subtitle, tags)

    print(outputs[0])
    print(outputs[1])
    print(outputs[2])


if __name__ == "__main__":
    main()
