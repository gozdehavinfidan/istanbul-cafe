"""Resize the original dish images into web sizes.

Usage:  python tools/resize_images.py [--sheet OUT.png]
Reads   _src/istanbul-cafe/<category>/<slug>.webp
Writes  assets/img/menu/<category>/<slug>-200/-400/-800.webp (never upscaled)
With --sheet, also writes a labelled contact sheet built from data/menu.json so
every item/image pairing can be checked by eye.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_src" / "istanbul-cafe"
OUT = ROOT / "assets" / "img" / "menu"
SIZES = (200, 400, 800)


def resize_all():
    count = 0
    for src in sorted(SRC.glob("*/*.webp")):
        dest_dir = OUT / src.parent.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGB")
            for size in SIZES:
                w = min(size, im.width)
                h = round(im.height * w / im.width)
                im.resize((w, h), Image.LANCZOS).save(
                    dest_dir / f"{src.stem}-{size}.webp", "WEBP", quality=78, method=6
                )
        count += 1
    print(f"resized {count} images into {OUT}")


def contact_sheet(path):
    menu = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
    entries = []
    for cat in menu["categories"]:
        for it in cat["items"]:
            entries.append((f"{cat['title']}: {it['name']} ${it['price']:.2f}", OUT / cat["src"] / f"{it['img']}-400.webp"))
        if "addon" in cat:
            for im in cat["addon"]["imgs"]:
                entries.append((f"Add-on: {im['alt']}", OUT / cat["addon"]["src"] / f"{im['img']}-400.webp"))
    cell, cols = 220, 6
    rows = -(-len(entries) // cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 34)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    for i, (label, p) in enumerate(entries):
        x, y = (i % cols) * cell, (i // cols) * (cell + 34)
        with Image.open(p) as im:
            sheet.paste(im.convert("RGB").resize((cell - 10, cell - 10)), (x + 5, y + 5))
        draw.text((x + 5, y + cell - 2), label[:38], fill="black", font=font)
        draw.text((x + 5, y + cell + 13), label[38:76], fill="black", font=font)
    sheet.save(path)
    print(f"contact sheet: {path} ({len(entries)} entries)")


if __name__ == "__main__":
    resize_all()
    if "--sheet" in sys.argv:
        contact_sheet(sys.argv[sys.argv.index("--sheet") + 1])
