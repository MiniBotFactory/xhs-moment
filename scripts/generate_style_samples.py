#!/usr/bin/env python3
"""Generate sample images for all 3 layout styles."""
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parent / "generate.py"
EXAMPLES = Path(__file__).parent.parent / "examples"
STYLES = ["poster", "split", "card", "memo", "highlight"]

for style in STYLES:
    out = EXAMPLES / style
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "python3", str(SCRIPT),
        "--text", "\u5f88\u591a\u4e8b\u4e0d\u662f\u5bf9\u9519\uff0c\u662f\u9009\u62e9",
        "--subtitle", "style demo",
        "--palette", "warm",
        "--style", style,
        "--hashtags", "\u4eba\u751f\u601d\u8003,\u9009\u62e9,\u611f\u609f",
        "--output-dir", str(out),
    ], check=True, capture_output=True, text=True)
    print(f"{style} ok")

print(f"examples dir: {EXAMPLES}")
