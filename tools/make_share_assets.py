"""Render the share/app images with Playwright + Pillow.

Uses the installed Google Chrome when available, otherwise Playwright's own Chromium.

Usage:  python -m http.server 8765 --bind 127.0.0.1   (from the project root, in another terminal)
        python tools/make_share_assets.py

Writes:
  assets/icons/icon-512.png, icon-192.png, apple-touch-icon.png (180), favicon-32.png
  assets/og/share.jpg     1200x630 link-preview image (WhatsApp, iMessage, Facebook, X...)
"""
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def launch_chromium(pw):
    try:
        return pw.chromium.launch(channel="chrome")
    except Exception:
        return pw.chromium.launch()


BASE = "http://127.0.0.1:8765/"

ICONS = ROOT / "assets" / "icons"
OG = ROOT / "assets" / "og"
ICONS.mkdir(parents=True, exist_ok=True)
OG.mkdir(parents=True, exist_ok=True)

# The preview shows the finished hero scene with the name, without navigation or buttons.
OG_CSS = """
  .site-header, .hero__actions, .hero__scroll { display: none !important; }
  *, *::before, *::after { animation-delay: -10s !important; animation-play-state: paused !important; }
  .hero { min-height: 630px !important; height: 630px; }
  .hero__content { padding-top: 96px !important; }
"""

with sync_playwright() as pw:
    browser = launch_chromium(pw)

    # icons from the SVG
    page = browser.new_page(viewport={"width": 512, "height": 512})
    page.goto(BASE + "assets/svg/icon.svg")
    png = page.screenshot(clip={"x": 0, "y": 0, "width": 512, "height": 512})
    page.close()
    icon = Image.open(io.BytesIO(png)).convert("RGB")
    for name, size in (("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180), ("favicon-32.png", 32)):
        icon.resize((size, size), Image.LANCZOS).save(ICONS / name, optimize=True)

    # 1200x630 link preview
    page = browser.new_page(viewport={"width": 1200, "height": 630})
    page.goto(BASE, wait_until="networkidle")
    page.add_style_tag(content=OG_CSS)
    page.wait_for_timeout(800)
    shot = page.screenshot(clip={"x": 0, "y": 0, "width": 1200, "height": 630})
    page.close()
    browser.close()

img = Image.open(io.BytesIO(shot)).convert("RGB")
for q in (86, 80, 74, 68):  # keep it under ~300 KB, which WhatsApp handles most reliably
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    if buf.tell() < 290_000:
        break
(OG / "share.jpg").write_bytes(buf.getvalue())
print(f"icons -> {ICONS}\npreview -> {OG / 'share.jpg'} ({buf.tell() // 1024} KB, q={q})")
