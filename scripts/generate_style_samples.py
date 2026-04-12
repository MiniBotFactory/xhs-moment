#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

BASE = Path('/Users/sky/.openclaw/workspace/xhs-moment/samples/20260412-2035')
STYLES = [
    'golden-split',
    'floating-card',
    'quiet-corner',
    'centered-balance',
    'ticket-stub',
    'margin-label',
]

BASE.mkdir(parents=True, exist_ok=True)
for style in STYLES:
    out = BASE / style
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'python3',
        '/Users/sky/.openclaw/workspace/xhs-moment/scripts/generate.py',
        '--text', '很多事不是对错，是选择',
        '--subtitle', '2026.04.12',
        '--palette', 'warm',
        '--style', style,
        '--hashtags', '人生思考,选择,感悟',
        '--output-dir', str(out),
    ], check=True, capture_output=True, text=True)
    print(f'{style} ok')

print(f'BASE={BASE}')
