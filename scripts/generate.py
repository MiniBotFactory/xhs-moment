#!/usr/bin/env python3
"""
xhs-moment image generator — minimalist color-block + typography cards.

Generates 3 images (1080x1440, 3:4) for social media posts:
  1. Cover  — large color block with quote text
  2. Quote  — decorative quotation marks with centered text
  3. Topics — hashtag badges in pill layout

6 color palettes: warm, cool, fresh, elegant, dreamy, bold.
Cross-platform: macOS / Windows / Linux with CJK font auto-detection.

Usage:
  python3 generate.py --text "your quote" --palette warm --output-dir ./out
  python3 generate.py --text "Quote" --palette bold --hashtags "AI,future"
"""
import argparse
import os
import platform
from PIL import Image, ImageDraw, ImageFont

# ── Canvas ──────────────────────────────────────────────────────────
W, H = 1080, 1440  # 3:4 social media standard

# ── Cross-platform font resolution ─────────────────────────────────
_FONT_CANDIDATES = {
    "Darwin": {
        "bold":  ["/System/Library/Fonts/STHeiti Medium.ttc",
                  "/System/Library/Fonts/PingFang.ttc",
                  "/Library/Fonts/Arial Unicode.ttf"],
        "light": ["/System/Library/Fonts/STHeiti Light.ttc",
                  "/System/Library/Fonts/PingFang.ttc",
                  "/Library/Fonts/Arial Unicode.ttf"],
    },
    "Windows": {
        "bold":  ["C:\\Windows\\Fonts\\msyhbd.ttc",
                  "C:\\Windows\\Fonts\\msyh.ttc",
                  "C:\\Windows\\Fonts\\simhei.ttf"],
        "light": ["C:\\Windows\\Fonts\\msyhl.ttc",
                  "C:\\Windows\\Fonts\\msyh.ttc",
                  "C:\\Windows\\Fonts\\simsun.ttc"],
    },
    "Linux": {
        "bold":  ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                  "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
                  "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"],
        "light": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                  "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
                  "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"],
    },
}

def _resolve_font(style, size):
    system = platform.system()
    candidates = _FONT_CANDIDATES.get(system, _FONT_CANDIDATES["Linux"])
    for path in candidates.get(style, candidates["light"]):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()

def font(size, bold=False):
    return _resolve_font("bold" if bold else "light", size)

# ── Color palettes ──────────────────────────────────────────────────
PALETTES = {
    "warm":    {"bg": (255,248,240), "block": ( 87,107, 76), "accent": (210,120, 50),
                "text_dark": ( 55, 45, 35), "text_light": (255,250,242)},
    "cool":    {"bg": (235,240,248), "block": ( 60, 80,120), "accent": (100,160,210),
                "text_dark": ( 40, 50, 70), "text_light": (230,238,250)},
    "fresh":   {"bg": (240,252,245), "block": ( 60,140, 90), "accent": (250,200, 60),
                "text_dark": ( 35, 60, 40), "text_light": (235,255,242)},
    "elegant": {"bg": (245,242,238), "block": ( 80, 50, 60), "accent": (180,140,100),
                "text_dark": ( 60, 40, 45), "text_light": (248,244,240)},
    "dreamy":  {"bg": (248,240,252), "block": (140,100,160), "accent": (220,150,180),
                "text_dark": ( 80, 55, 90), "text_light": (252,245,255)},
    "bold":    {"bg": ( 45, 45, 50), "block": ( 30, 30, 35), "accent": (240,220, 60),
                "text_dark": (240,240,235), "text_light": (255,255,250)},
}

# ── Drawing helpers ─────────────────────────────────────────────────
def draw_rounded_rect(d, xy, fill, radius=20):
    d.rounded_rectangle(xy, radius=radius, fill=fill)

def wrap_text(text, fnt, max_width):
    """Wrap CJK/mixed text character-by-character based on measured width."""
    lines, current = [], ""
    for ch in text:
        test = current + ch
        if fnt.getbbox(test)[2] - fnt.getbbox(test)[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines

def draw_multiline_center(d, lines, fnt, x_center, y_start, line_height, fill):
    for i, line in enumerate(lines):
        d.text((x_center, y_start + i * line_height), line,
               font=fnt, fill=fill, anchor="mm")

# ── Card generators ─────────────────────────────────────────────────
def gen_cover(text, subtitle, p, path):
    """Image 1: Large color block with quote text + subtitle."""
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=p["accent"])
    block_h = int(H * 0.58)
    draw_rounded_rect(d, [0, 0, W, block_h], p["block"], radius=0)
    d.rectangle([0, 0, W, 10], fill=p["accent"])
    fnt = font(52, bold=True)
    lines = wrap_text(text, fnt, W - 160)
    line_h, total_h = 80, len(wrap_text(text, fnt, W - 160)) * 80
    y0 = block_h // 2 - total_h // 2 + line_h // 2 + 20
    draw_multiline_center(d, lines, fnt, W // 2, y0, line_h, p["text_light"])
    d.line([W//2-60, y0+total_h+30, W//2+60, y0+total_h+30], fill=p["accent"], width=3)
    d.text((W//2, block_h + (H-block_h)//2), subtitle,
           font=font(28), fill=p["text_dark"], anchor="mm")
    d.ellipse([W//2-8, H-80, W//2+8, H-64], fill=p["accent"])
    img.save(path, quality=95)

def gen_quote(text, p, path):
    """Image 2: Decorative quotation marks with centered quote."""
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    d.text((100, 200), "\u201c", font=font(200, bold=True), fill=p["accent"])
    fnt = font(44, bold=True)
    lines = wrap_text(text, fnt, W - 200)
    line_h = 72
    total_h = len(lines) * line_h
    y0 = H // 2 - total_h // 2 + line_h // 2 - 40
    draw_multiline_center(d, lines, fnt, W // 2, y0, line_h, p["text_dark"])
    line_y = y0 + total_h + 50
    d.line([W//2-100, line_y, W//2+100, line_y], fill=p["accent"], width=3)
    d.text((W-180, line_y+20), "\u201d", font=font(120, bold=True), fill=p["accent"])
    d.ellipse([W-120, H-120, W-60, H-60], fill=p["accent"])
    img.save(path, quality=95)

def gen_closing(hashtags, p, path):
    """Image 3: Hashtag badges in flowing pill layout."""
    img = Image.new("RGB", (W, H), p["block"])
    d = ImageDraw.Draw(img)
    d.text((W//2, 250), "TOPICS", font=font(36), fill=p["text_light"], anchor="mm")
    d.line([W//2-50, 285, W//2+50, 285], fill=p["accent"], width=2)
    tag_fnt = font(34, bold=True)
    badge_h, pad_x, gap, row_gap = 65, 36, 20, 24
    badges = [(f"# {t}", tag_fnt.getbbox(f"# {t}")[2] - tag_fnt.getbbox(f"# {t}")[0] + pad_x*2)
              for t in hashtags]
    max_row_w = W - 140
    rows, row, rw = [], [], 0
    for label, bw in badges:
        needed = bw + (gap if row else 0)
        if rw + needed > max_row_w and row:
            rows.append(row); row, rw = [(label, bw)], bw
        else:
            row.append((label, bw)); rw += needed
    if row: rows.append(row)
    total_h = len(rows) * (badge_h + row_gap) - row_gap
    y_base = H // 2 - total_h // 2
    for i, r in enumerate(rows):
        row_w = sum(bw for _, bw in r) + gap * (len(r) - 1)
        x = (W - row_w) // 2
        y = y_base + i * (badge_h + row_gap)
        for label, bw in r:
            draw_rounded_rect(d, [x, y, x+bw, y+badge_h], p["bg"], radius=badge_h//2)
            d.text((x+bw//2, y+badge_h//2), label, font=tag_fnt, fill=p["text_dark"], anchor="mm")
            x += bw + gap
    d.text((W//2, H-160), "\u2014 \u968f\u624b\u8bb0 \u2014", font=font(26), fill=p["text_light"], anchor="mm")
    d.polygon([(0, H), (80, H), (0, H-80)], fill=p["accent"])
    img.save(path, quality=95)

# ── CLI ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Generate minimalist social media cards (1080x1440)")
    ap.add_argument("--text", required=True, help="Quote / key phrase")
    ap.add_argument("--subtitle", default="", help="Subtitle (date, author)")
    ap.add_argument("--palette", default="warm", choices=list(PALETTES.keys()))
    ap.add_argument("--hashtags", default="", help="Comma-separated hashtags")
    ap.add_argument("--output-dir", default="/tmp/xhs-moment")
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    p = PALETTES[args.palette]
    tags = [t.strip() for t in args.hashtags.split(",") if t.strip()] if args.hashtags else ["\u968f\u624b\u8bb0"]
    for i, fn, a in [(1, gen_cover, (args.text, args.subtitle or "\u968f\u624b\u8bb0", p)),
                      (2, gen_quote, (args.text, p)),
                      (3, gen_closing, (tags, p))]:
        out = os.path.join(args.output_dir, f"moment-{i}.jpg")
        fn(*a, out)
        print(os.path.abspath(out))

if __name__ == "__main__":
    main()
