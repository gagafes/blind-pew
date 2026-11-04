#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Render an illustrative GIF using actual Composer output, not a desktop recording.

Development dependencies: Pillow and the distro fonts-dejavu-core package.
Run from the repository root: python3 .github/scripts/render-demo.py
"""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from blind_pew.core import Composer

FONT = Path('/usr/share/fonts/truetype/dejavu')

def font(size, bold=False):
    return ImageFont.truetype(str(FONT / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)


def frame(label, text, active=True):
    image = Image.new('RGB', (960, 360), '#06264c')
    draw = ImageDraw.Draw(image)
    draw.text((40, 24), 'Blind Pew', fill='#ffe6ac', font=font(30, True))
    draw.rounded_rectangle((750, 24, 920, 70), radius=12, fill='#ffe6ac')
    draw.text((773, 34), 'F12 toggle', fill='#06264c', font=font(20, True))
    draw.text((40, 92), label, fill='#c6d5e4', font=font(21))
    draw.rounded_rectangle((40, 132, 920, 244), radius=14, fill='#f7f9fc')
    draw.text((64, 160), text + '|', fill='#06264c', font=font(36))
    draw.text((40, 272), 'Transliteration ON' if active else 'Ordinary input', fill='#ffe6ac', font=font(23, True))
    draw.text((40, 315), 'Converter illustration · actual engine output · QWERTY / QWERTZ', fill='#c6d5e4', font=font(17))
    return image


def main():
    frames, durations = [], []
    for profile, label, text in [('be', 'Belarusian', 'Pryvitanne!'), ('ua', 'Ukrainian', "Ukrai'na je g'")]:
        composer = Composer(profile)
        committed = ''
        frames.append(frame(label, ''))
        durations.append(500)
        for char in text:
            committed += composer.feed(char)
            frames.append(frame(label, committed + composer.pending))
            durations.append(140)
        assert committed + composer.flush() == ('Прывітанне!' if profile == 'be' else 'Україна є ґ')
        durations[-1] = 1800
        frames.append(frame(label + ' · toggled off', 'Hello, Linux!', active=False))
        durations.append(1300)
    target = ROOT / 'docs/marketing/transliteration-demo.gif'
    target.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(target.relative_to(ROOT), target.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
