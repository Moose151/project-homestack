#!/usr/bin/env python3
"""Turn the brand source PNGs into the web assets the frontend actually loads.

The sources in `brand/` are 1536×1024 renders: the artwork sits inside a lot of empty canvas
with a soft glow around it, and each file is over a megabyte. Shipping those directly would
download ~3 MB to draw a 36px logo, and the canvas padding would make the mark impossible to
align. This crops each one to its real artwork, resizes it, and writes the results to
`frontend/public/brand/`.

Re-run after replacing a source file:

    python3 scripts/build_brand_assets.py

Requires Pillow (`pip install Pillow`). The generated files are committed, so this is a
one-off tool rather than part of the build.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "brand"
OUTPUT_DIR = ROOT / "frontend" / "public" / "brand"

# The glow fades to nothing over a wide margin, so an alpha>0 crop keeps most of the empty
# canvas. This threshold finds the artwork itself; the margin below then gives it room to
# breathe without leaving the crop dependent on how far the glow happens to spread.
SOLID_ALPHA = 40
MARGIN = 0.02

# iOS fills a transparent home-screen icon with black, so that one gets the app's paper colour.
PAPER = (255, 250, 242, 255)


def artwork(path: Path) -> Image.Image:
    """The source cropped to its artwork, with a small even margin."""
    image = Image.open(path).convert("RGBA")
    mask = image.getchannel("A").point(lambda value: 255 if value > SOLID_ALPHA else 0)
    box = mask.getbbox()
    if box is None:
        raise SystemExit(f"{path.name} looks empty")
    pad = round(max(box[2] - box[0], box[3] - box[1]) * MARGIN)
    return image.crop((
        max(box[0] - pad, 0), max(box[1] - pad, 0),
        min(box[2] + pad, image.width), min(box[3] + pad, image.height),
    ))


def scaled_to_height(image: Image.Image, height: int) -> Image.Image:
    width = round(image.width * height / image.height)
    return image.resize((width, height), Image.LANCZOS)


def squared(image: Image.Image, size: int, background: tuple | None = None) -> Image.Image:
    """Centre the artwork on a square canvas so every icon size lines up identically."""
    fitted = image.copy()
    fitted.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), background or (0, 0, 0, 0))
    canvas.alpha_composite(
        fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2)
    )
    return canvas


def save(image: Image.Image, name: str) -> None:
    target = OUTPUT_DIR / name
    image.save(target, optimize=True)
    print(f"  {name:<24} {image.width}×{image.height}  {target.stat().st_size / 1024:.0f} kB")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mark = artwork(SOURCE_DIR / "homestack-mark-source.png")
    wordmark = artwork(SOURCE_DIR / "homestack-wordmark-source.png")
    lockup = artwork(SOURCE_DIR / "homestack-lockup-source.png")

    print(f"Writing {OUTPUT_DIR.relative_to(ROOT)}/")
    save(squared(mark, 512), "mark.png")
    save(squared(mark, 192), "mark-192.png")
    save(scaled_to_height(wordmark, 160), "wordmark.png")
    save(scaled_to_height(lockup, 512), "lockup.png")
    save(squared(mark, 180, PAPER), "apple-touch-icon.png")
    save(squared(mark, 32), "favicon-32.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
