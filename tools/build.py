"""Build step: inject generated markup into index.html.

Usage:  python tools/build.py

Replaces the content between these marker pairs in index.html:
  <!-- BUILD:hero -->   original Galata waterfront illustration (inline SVG)
  <!-- BUILD:chips -->  category tabs
  <!-- BUILD:menu -->   full menu, generated from data/menu.json

The illustration is drawn procedurally with a fixed random seed, so the output is
deterministic. Only the Python standard library is needed.
"""
import html
import json
import math
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
MENU = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
IMG_BASE = "assets/img/menu"

W, H = 1600, 900
WATER = 700          # waterline y
TOWER_X = 1130       # Galata Tower centre (right third: copy sits in the open sky on the left)
SUN = (1330, 440)


def f(n):
    """Compact number formatting for SVG output."""
    return f"{n:.1f}".rstrip("0").rstrip(".")


def ground(x):
    """Hill profile of Galata/Beyoğlu: peaks at the tower."""
    return WATER - 16 - 125 * math.exp(-(((x - TOWER_X) / 400) ** 2)) - 6 * math.exp(-(((x - 420) / 240) ** 2))


# --------------------------------------------------------------------------- hero
# "Sunset from Üsküdar": the classic Istanbul view looking west across the Bosphorus.
# The Maiden's Tower stands on its islet; behind it the historic peninsula (Blue Mosque,
# Hagia Sophia, Topkapı, Süleymaniye) is silhouetted against an orange-to-violet sky;
# Galata Tower rises across the Golden Horn and the Bosphorus Bridge glows in the distance.
# Everything is original vector art, drawn procedurally with a fixed seed (deterministic).

HZ = 600            # horizon / far shoreline
SUN = (1098, 550)   # low sun, half behind the peninsula
SUN_R = 64

C_LIGHT = "#FFD58A"     # warm window light
C_RIM = "#FFB27A"       # sunset rim light on domes


def dome(cx, base, r, color, rim=False, flat=1.0, finial=True):
    ry = r * flat
    out = f'<path d="M{f(cx - r)} {f(base)}A{f(r)} {f(ry)} 0 0 1 {f(cx + r)} {f(base)}Z" fill="{color}"/>'
    if finial:
        out += f'<path d="M{f(cx)} {f(base - ry)}v{f(-r * .32)}" stroke="{color}" stroke-width="{f(max(1.2, r * .06))}"/>'
        out += f'<circle cx="{f(cx)}" cy="{f(base - ry - r * .36)}" r="{f(max(1.2, r * .06))}" fill="{color}"/>'
    if rim:
        out += (f'<path d="M{f(cx - r * .92)} {f(base - ry * .35)}A{f(r)} {f(ry)} 0 0 1 {f(cx + r * .2)} {f(base - ry * .98)}" '
                f'fill="none" stroke="{C_RIM}" stroke-width="1.3" stroke-linecap="round" opacity=".75"/>')
    return out


def minaret(x, base, h, s, color, balconies=2):
    w = 4.6 * s
    top = base - h
    out = f'<rect x="{f(x - w / 2)}" y="{f(top)}" width="{f(w)}" height="{f(HZ + 4 - top)}" fill="{color}"/>'
    for i in range(balconies):
        by = top + h * (.16 + i * .2)
        out += f'<rect x="{f(x - w * .95)}" y="{f(by)}" width="{f(w * 1.9)}" height="{f(2.4 * s)}" fill="{color}"/>'
    out += f'<path d="M{f(x - w / 2)} {f(top)}L{f(x)} {f(top - 20 * s)}L{f(x + w / 2)} {f(top)}Z" fill="{color}"/>'
    return out


def arches(x0, x1, y, h, n, color=C_LIGHT, op=.8):
    if n <= 0:
        return ""
    step = (x1 - x0) / n
    w = step * .38
    out = "".join(f'<path d="M{f(x0 + step * (i + .5) - w / 2)} {f(y)}v{f(-h)}a{f(w / 2)} {f(w / 2)} 0 0 1 {f(w)} 0v{f(h)}Z"/>' for i in range(n))
    return f'<g fill="{color}" opacity="{op}">{out}</g>'


def blue_mosque(cx, base, s, c):
    """Sultan Ahmed Mosque: cascading domes, six minarets (three each side)."""
    o = f'<rect x="{f(cx - 78 * s)}" y="{f(base - 34 * s)}" width="{f(156 * s)}" height="{f(HZ + 4 - base + 34 * s)}" fill="{c}"/>'
    o += f'<rect x="{f(cx - 46 * s)}" y="{f(base - 52 * s)}" width="{f(92 * s)}" height="{f(20 * s)}" fill="{c}"/>'
    for dx in (-60, 60):
        o += dome(cx + dx * s, base - 34 * s, 12 * s, c)
    for dx in (-34, 34):
        o += dome(cx + dx * s, base - 52 * s, 20 * s, c)
    o += f'<rect x="{f(cx - 30 * s)}" y="{f(base - 66 * s)}" width="{f(60 * s)}" height="{f(14 * s)}" fill="{c}"/>'
    o += dome(cx, base - 66 * s, 31 * s, c)
    for dx, h in ((-70, 132), (70, 132), (-98, 116), (98, 116), (-122, 100), (122, 100)):
        o += minaret(cx + dx * s, base, h * s, s, c, 3 if h > 120 else 2)
    o += arches(cx - 70 * s, cx + 70 * s, base - 8 * s, 12 * s, 9)
    return o


def hagia_sophia(cx, base, s, c):
    """Hagia Sophia: broad flattened dome on a windowed drum, heavy buttresses, four minarets."""
    o = f'<rect x="{f(cx - 82 * s)}" y="{f(base - 40 * s)}" width="{f(164 * s)}" height="{f(HZ + 4 - base + 40 * s)}" fill="{c}"/>'
    for dx in (-70, 54):  # stepped buttress towers
        o += f'<rect x="{f(cx + dx * s)}" y="{f(base - 64 * s)}" width="{f(16 * s)}" height="{f(30 * s)}" fill="{c}"/>'
        o += f'<path d="M{f(cx + dx * s)} {f(base - 64 * s)}l{f(8 * s)} {f(-8 * s)}l{f(8 * s)} {f(8 * s)}Z" fill="{c}"/>'
    for dx in (-30, 30):
        o += dome(cx + dx * s, base - 40 * s, 24 * s, c, flat=.75)
    o += f'<rect x="{f(cx - 36 * s)}" y="{f(base - 70 * s)}" width="{f(72 * s)}" height="{f(30 * s)}" fill="{c}"/>'
    o += f'<rect x="{f(cx - 40 * s)}" y="{f(base - 80 * s)}" width="{f(80 * s)}" height="{f(11 * s)}" fill="{c}"/>'
    o += arches(cx - 38 * s, cx + 38 * s, base - 70 * s, 7 * s, 10, op=.55)
    o += dome(cx, base - 80 * s, 40 * s, c, flat=.62)
    for dx, h, b in ((-96, 120, 2), (96, 126, 2), (-118, 104, 1), (118, 110, 1)):
        o += minaret(cx + dx * s, base, h * s, s * (1.15 if abs(dx) > 100 else 1), c, b)
    o += arches(cx - 60 * s, cx + 60 * s, base - 10 * s, 10 * s, 7)
    return o


def suleymaniye(cx, base, s, c):
    o = f'<rect x="{f(cx - 64 * s)}" y="{f(base - 32 * s)}" width="{f(128 * s)}" height="{f(HZ + 4 - base + 32 * s)}" fill="{c}"/>'
    for dx in (-28, 28):
        o += dome(cx + dx * s, base - 32 * s, 18 * s, c)
    o += f'<rect x="{f(cx - 28 * s)}" y="{f(base - 58 * s)}" width="{f(56 * s)}" height="{f(26 * s)}" fill="{c}"/>'
    o += dome(cx, base - 58 * s, 30 * s, c)
    for dx, h in ((-76, 132), (76, 132), (-98, 108), (98, 108)):
        o += minaret(cx + dx * s, base, h * s, s, c, 3 if h > 120 else 2)
    o += arches(cx - 54 * s, cx + 54 * s, base - 8 * s, 10 * s, 7)
    return o


def aqueduct(x0, x1, base, s, c):
    """Valens Aqueduct: a long two-tier Roman arcade. Openings are holes (even-odd fill)."""
    top = base - 62 * s
    mid = base - 30 * s
    d = f"M{f(x0)} {f(HZ + 4)}V{f(top)}H{f(x1)}V{f(HZ + 4)}Z"
    n_low = max(3, int((x1 - x0) / (19 * s)))
    step = (x1 - x0) / n_low
    for i in range(n_low):  # tall lower arches
        ax = x0 + i * step + step * .22
        aw = step * .56
        d += f" M{f(ax)} {f(HZ + 4)}V{f(mid + aw / 2 + 4 * s)}A{f(aw / 2)} {f(aw / 2)} 0 0 1 {f(ax + aw)} {f(mid + aw / 2 + 4 * s)}V{f(HZ + 4)}Z"
    n_up = n_low * 2
    step2 = (x1 - x0) / n_up
    for i in range(n_up):  # smaller upper arcade
        ax = x0 + i * step2 + step2 * .24
        aw = step2 * .52
        d += f" M{f(ax)} {f(mid - 3 * s)}V{f(top + 8 * s + aw / 2)}A{f(aw / 2)} {f(aw / 2)} 0 0 1 {f(ax + aw)} {f(top + 8 * s + aw / 2)}V{f(mid - 3 * s)}Z"
    return f'<path d="{d}" fill="{c}" fill-rule="evenodd"/>'


def cypress(x, base, h, c):
    w = h * .16
    return (f'<path d="M{f(x)} {f(base - h)}C{f(x + w)} {f(base - h * .7)} {f(x + w * .9)} {f(base - h * .2)} {f(x + w * .45)} {f(base)}'
            f'H{f(x - w * .45)}C{f(x - w * .9)} {f(base - h * .2)} {f(x - w)} {f(base - h * .7)} {f(x)} {f(base - h)}Z" fill="{c}"/>')


def topkapi(x0, x1, base, s, c, rng):
    o = f'<rect x="{f(x0)}" y="{f(base - 16 * s)}" width="{f(x1 - x0)}" height="{f(HZ + 4 - base + 16 * s)}" fill="{c}"/>'
    # crenellated walls
    o += "".join(f'<rect x="{f(x)}" y="{f(base - 20 * s)}" width="{f(4 * s)}" height="{f(4 * s)}" fill="{c}"/>' for x in [x0 + i * 9 * s for i in range(int((x1 - x0) / (9 * s)))])
    # Tower of Justice
    tx = x0 + (x1 - x0) * .45
    o += f'<rect x="{f(tx - 7 * s)}" y="{f(base - 70 * s)}" width="{f(14 * s)}" height="{f(56 * s)}" fill="{c}"/>'
    o += f'<rect x="{f(tx - 9 * s)}" y="{f(base - 74 * s)}" width="{f(18 * s)}" height="{f(5 * s)}" fill="{c}"/>'
    o += f'<path d="M{f(tx - 8 * s)} {f(base - 74 * s)}L{f(tx)} {f(base - 100 * s)}L{f(tx + 8 * s)} {f(base - 74 * s)}Z" fill="{c}"/>'
    o += arches(tx - 6 * s, tx + 6 * s, base - 56 * s, 7 * s, 2)
    # kitchen domes and chimneys
    for i in range(6):
        dx = x0 + (x1 - x0) * (.62 + i * .055)
        o += dome(dx, base - 16 * s, 5 * s, c, finial=False)
        o += f'<rect x="{f(dx - 1.4 * s)}" y="{f(base - 30 * s)}" width="{f(2.8 * s)}" height="{f(10 * s)}" fill="{c}"/>'
    # cypress groves
    for _ in range(14):
        x = rng.uniform(x0 - 10, x1 + 10)
        o += cypress(x, base - 6 * s, rng.uniform(26, 46) * s, c)
    return o


def galata_tower(x, base, s, c):
    body_top = base - 120 * s
    o = f'<path d="M{f(x - 19 * s)} {f(base)}L{f(x - 16 * s)} {f(body_top)}H{f(x + 16 * s)}L{f(x + 19 * s)} {f(base)}Z" fill="{c}"/>'
    # the tower continues down to the shore, so it rises from behind the houses instead of floating
    o += f'<rect x="{f(x - 19 * s)}" y="{f(base - 1)}" width="{f(38 * s)}" height="{f(HZ + 4 - base + 1)}" fill="{c}"/>'
    o += f'<rect x="{f(x - 24 * s)}" y="{f(base - 8 * s)}" width="{f(48 * s)}" height="{f(HZ + 4 - base + 8 * s)}" fill="{c}"/>'
    o += f'<rect x="{f(x - 23 * s)}" y="{f(body_top - 5 * s)}" width="{f(46 * s)}" height="{f(5 * s)}" fill="{c}"/>'
    o += "".join(f'<rect x="{f(x - 21 * s + i * 3.7 * s)}" y="{f(body_top - 12 * s)}" width="{f(1 * s)}" height="{f(7 * s)}" fill="{c}"/>' for i in range(12))
    o += f'<rect x="{f(x - 22 * s)}" y="{f(body_top - 13 * s)}" width="{f(44 * s)}" height="{f(1.6 * s)}" fill="{c}"/>'
    o += f'<rect x="{f(x - 14 * s)}" y="{f(body_top - 34 * s)}" width="{f(28 * s)}" height="{f(22 * s)}" fill="{c}"/>'
    o += f'<path d="M{f(x - 17 * s)} {f(body_top - 32 * s)}L{f(x)} {f(body_top - 82 * s)}L{f(x + 17 * s)} {f(body_top - 32 * s)}Z" fill="{c}"/>'
    o += f'<path d="M{f(x)} {f(body_top - 82 * s)}v{f(-8 * s)}" stroke="{c}" stroke-width="{f(1.6 * s)}"/>'
    o += arches(x - 13 * s, x + 13 * s, body_top - 16 * s, 12 * s, 4, op=.95)
    o += arches(x - 3 * s, x + 3 * s, base - 30 * s, 8 * s, 1, op=.9)
    o += arches(x - 3 * s, x + 3 * s, base - 70 * s, 8 * s, 1, op=.9)
    return o


def houses(rng, x0, x1, base_fn, hmin, hmax, wmin, wmax, color, lights, light_op=.85):
    out, win = [], []
    x = x0
    while x < x1:
        w = rng.uniform(wmin, wmax)
        b = base_fn(x + w / 2)
        h = rng.uniform(hmin, hmax)
        top = b - h
        out.append(f'<rect x="{f(x)}" y="{f(top)}" width="{f(w + .6)}" height="{f(HZ + 4 - top)}"/>')
        r = rng.random()
        if r < .45:
            out.append(f'<path d="M{f(x - 1.5)} {f(top)}L{f(x + w / 2)} {f(top - rng.uniform(6, 13))}L{f(x + w + 1.5)} {f(top)}Z"/>')
        elif r < .6:
            out.append(f'<rect x="{f(x - 1)}" y="{f(top - 3)}" width="{f(w + 2)}" height="3"/>')
        # a few lit windows per house, not a uniform grid
        cols = max(1, int(w // 8))
        rows = max(1, int(h // 11))
        for cx in range(cols):
            for ry in range(rows):
                if rng.random() < .32:
                    wx = x + 3 + cx * (w - 6) / cols
                    wy = top + 5 + ry * 11
                    if wy < HZ - 6:
                        win.append(f'<rect x="{f(wx)}" y="{f(wy)}" width="3" height="4.2"/>')
        x += w + rng.uniform(-1.5, 1)
    lights.append(f'<g fill="{C_LIGHT}" opacity="{light_op}">{"".join(win)}</g>')
    return f'<g fill="{color}">{"".join(out)}</g>'


def ferry(hull="#14284B", deck="#FBF7EE", s=1.0):
    """City ferry (vapur), facing right, origin at the bow-waterline left end."""
    return f'''<g>
<path d="M-6 44 Q120 36 252 40 L240 64 Q120 70 14 64 Z" fill="{hull}"/>
<path d="M-4 44 Q120 37 250 41 L248 46 Q120 42 -2 49 Z" fill="#F2C77B"/>
<rect x="14" y="20" width="214" height="22" rx="3" fill="{deck}"/>
<rect x="18" y="26" width="206" height="7" fill="#2B2A4A"/>
<g fill="{C_LIGHT}">{"".join(f'<rect x="{22 + i * 13}" y="27" width="8" height="5" rx="1"/>' for i in range(16))}</g>
<rect x="50" y="4" width="140" height="17" rx="3" fill="{deck}"/>
<rect x="54" y="9" width="132" height="6" fill="#2B2A4A"/>
<g fill="{C_LIGHT}" opacity=".9">{"".join(f'<rect x="{58 + i * 13}" y="10" width="7" height="4" rx="1"/>' for i in range(10))}</g>
<rect x="44" y="2" width="152" height="3" rx="1.5" fill="{hull}"/>
<rect x="104" y="-26" width="20" height="30" fill="#F2C77B"/>
<rect x="104" y="-26" width="20" height="9" fill="#1A1A2E"/>
<path d="M70 2 V-18 M176 2 V-14" stroke="{hull}" stroke-width="2"/>
<circle cx="70" cy="-19" r="2.4" fill="#FFF3C4"/>
<path d="M14 20 L4 4 M14 20 V6" stroke="{hull}" stroke-width="1.6"/>
<path d="M4 4 h11 v8 h-11 z" fill="#E03A3E"/>
<circle cx="9" cy="8" r="2.2" fill="#fff"/><circle cx="9.8" cy="8" r="1.8" fill="#E03A3E"/>
</g>'''


def wave_band(y0, amp, period, fill_top, fill_bot, fill_op, crest, crest_op, crest_w, gid, phase=0.0):
    """One seamless band of sea: a sampled sine crest (two harmonics, both periodic in `period`)
    filled down to the bottom. Drawn from -period to W+period so a translate of exactly one
    period loops without a seam."""
    pts = []
    x = -period
    while x <= W + period + .1:
        t = 2 * math.pi * x / period + phase
        y = y0 + amp * math.sin(t) + amp * .35 * math.sin(2 * t + 1.3)
        pts.append((x, y))
        x += period / 24
    crest_d = "M" + " L".join(f"{f(px)} {f(py)}" for px, py in pts)
    per = pts[:25]
    arc = sum(math.dist(per[i], per[i + 1]) for i in range(len(per) - 1))
    dash = f"{f(arc * .34)} {f(arc * .1)} {f(arc * .22)} {f(arc * .34)}"
    fill_d = crest_d + f" L{f(W + period)} {H + 20} L{f(-period)} {H + 20}Z"
    grad = (f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{fill_top}"/><stop offset="1" stop-color="{fill_bot}"/></linearGradient>')
    # foam: short bright arcs riding the crests
    foam = []
    for i in range(int((W + 2 * period) / period) + 1):
        px = -period + i * period + period * .2
        t = 2 * math.pi * px / period + phase
        py = y0 + amp * math.sin(t) + amp * .35 * math.sin(2 * t + 1.3)
        foam.append(f'<path d="M{f(px)} {f(py - 1)}q{f(period * .08)} {f(-amp * .6)} {f(period * .16)} 0"/>')
    body = (f'<path d="{fill_d}" fill="url(#{gid})" opacity="{fill_op}"/>'
            f'<path d="{crest_d}" fill="none" stroke="{crest}" stroke-width="{crest_w}" stroke-linecap="round" stroke-dasharray="{dash}" opacity="{crest_op}"/>'
)
    return grad, body


def catenary(x0, y0, x1, y1, sag, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        pts.append((x, y))
    return pts


def hero_svg():
    rng = random.Random(1453)

    def layer(name, body, defs=""):
        d = f"<defs>{defs}</defs>" if defs else ""
        return (f'<svg class="layer layer--{name}" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" focusable="false">'
                f"{d}{body}</svg>\n")

    # ---------------- sky ----------------
    sky_defs = ('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0" stop-color="#101838"/><stop offset=".26" stop-color="#232B62"/>'
                '<stop offset=".44" stop-color="#4C3B7A"/><stop offset=".56" stop-color="#8E4C7E"/>'
                '<stop offset=".63" stop-color="#D2646E"/><stop offset=".68" stop-color="#F28F5E"/>'
                '<stop offset=".72" stop-color="#FBC277"/></linearGradient>'
                '<radialGradient id="haze" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFE3A3" stop-opacity=".9"/>'
                '<stop offset=".35" stop-color="#FFB07A" stop-opacity=".45"/><stop offset="1" stop-color="#F28F5E" stop-opacity="0"/></radialGradient>')
    sky = f'<rect width="{W}" height="{HZ + 4}" fill="url(#sky)"/>'
    sky += f'<ellipse cx="{SUN[0]}" cy="{SUN[1] + 10}" rx="760" ry="230" fill="url(#haze)"/>'

    stars = "".join(f'<circle cx="{f(rng.uniform(0, W))}" cy="{f(rng.uniform(8, 300) ** 1.0)}" r="{f(rng.uniform(.6, 1.7))}" opacity="{f(rng.uniform(.3, .9))}"/>' for _ in range(70))

    sun_defs = ('<radialGradient id="sun-disc" cx=".5" cy=".45" r=".55"><stop offset="0" stop-color="#FFF8DC"/>'
                '<stop offset=".7" stop-color="#FFE0A0"/><stop offset="1" stop-color="#FFB86E"/></radialGradient>'
                '<radialGradient id="sun-glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFE9B0" stop-opacity=".85"/>'
                '<stop offset=".4" stop-color="#FFC27A" stop-opacity=".35"/><stop offset="1" stop-color="#FFB07A" stop-opacity="0"/></radialGradient>')
    sun = (f'<circle cx="{SUN[0]}" cy="{SUN[1]}" r="230" fill="url(#sun-glow)"/>'
           f'<circle cx="{SUN[0]}" cy="{SUN[1]}" r="{SUN_R}" fill="url(#sun-disc)"/>')

    # sunset clouds: long streaks lit from below
    cloud_defs = ('<linearGradient id="cloud-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5A4580"/>'
                  '<stop offset=".6" stop-color="#C2647E"/><stop offset="1" stop-color="#FFB27A"/></linearGradient>'
                  '<linearGradient id="cloud-b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3D3570"/>'
                  '<stop offset="1" stop-color="#E07A78"/></linearGradient>')

    def cloud(cx, cy, wdt, hgt, grad, op, seed):
        """A long sunset streak: billowing top, softly curved base, tapered ends, lit from below."""
        r = random.Random(seed)
        n = 18
        top = []
        for i in range(n + 1):
            t = i / n
            x = cx - wdt / 2 + wdt * t
            taper = math.sin(math.pi * t) ** .8
            y = cy - hgt * taper * (.55 + .45 * abs(math.sin(t * math.pi * r.uniform(2.5, 4.5) + r.random())))
            top.append((x, y))
        d = f"M{f(top[0][0])} {f(cy)}"
        for (x0, y0), (x1, y1) in zip(top, top[1:]):
            d += f" Q{f(x0)} {f(y0)} {f((x0 + x1) / 2)} {f((y0 + y1) / 2)}"
        d += f" L{f(top[-1][0])} {f(cy)} Q{f(cx)} {f(cy + hgt * .35)} {f(top[0][0])} {f(cy)}Z"
        rim = f"M{f(cx - wdt * .42)} {f(cy + hgt * .12)} Q{f(cx)} {f(cy + hgt * .42)} {f(cx + wdt * .42)} {f(cy + hgt * .12)}"
        return (f'<g opacity="{op}"><path d="{d}" fill="url(#{grad})"/>'
                f'<path d="{rim}" fill="none" stroke="#FFC99C" stroke-width="1.6" stroke-linecap="round" opacity=".7"/></g>')
    clouds = (cloud(800, 300, 420, 30, "cloud-a", .85, 1) + cloud(1250, 255, 480, 26, "cloud-b", .75, 2)
              + cloud(1500, 380, 320, 20, "cloud-a", .7, 3) + cloud(560, 400, 300, 16, "cloud-a", .55, 4)
              + cloud(1090, 425, 600, 14, "cloud-a", .55, 5) + cloud(300, 250, 260, 14, "cloud-b", .35, 6))

    gull_pos = [(860, 330, 1.0, "#2A1F45"), (905, 352, .75, "#2A1F45"), (1180, 300, 1.1, "#2A1F45"),
                (1250, 335, .8, "#2A1F45"), (980, 460, .7, "#FFE2B8"), (1010, 474, .55, "#FFE2B8"), (1400, 420, .8, "#2A1F45")]
    gulls = "".join(f'<g transform="translate({gx} {gy}) scale({gs})"><g class="gull gull--{i % 3}"><path class="gull__w" stroke="{gc}" d="M-14 0 Q-7 -9 0 0 Q7 -9 14 0"/></g></g>'
                    for i, (gx, gy, gs, gc) in enumerate(gull_pos))

    # ---------------- the far shore ----------------
    lights_far, lights_mid = [], []
    islands = (f'<path d="M60 {HZ} Q130 {HZ - 16} 210 {HZ - 6} Q260 {HZ - 12} 300 {HZ}Z" fill="#7A5A8E" opacity=".55"/>'
               f'<path d="M330 {HZ} Q390 {HZ - 10} 450 {HZ - 3} Q490 {HZ - 8} 520 {HZ}Z" fill="#7A5A8E" opacity=".45"/>')

    PEN = "#4A2E60"   # historic peninsula, backlit
    def ground_p(x):
        return HZ - 4 - 24 * math.exp(-(((x - 1010) / 210) ** 2)) - 16 * math.exp(-(((x - 1225) / 70) ** 2))
    land = " ".join(f"L{f(x)} {f(ground_p(x))}" for x in range(730, 1292, 12))
    peninsula = f'<path d="M712 {HZ + 4} {land} L1292 {HZ + 4}Z" fill="{PEN}"/>'
    peninsula += houses(rng, 908, 1285, ground_p, 8, 20, 10, 22, PEN, lights_far, .6)  # none behind the aqueduct, so its arches stay open
    peninsula += aqueduct(752, 902, ground_p(827) + 4, .9, PEN)
    peninsula += topkapi(1100, 1262, ground_p(1180) + 2, .86, PEN, rng)
    peninsula += hagia_sophia(1000, ground_p(1000) + 2, .98, PEN)
    for x in (736, 912, 930, 1072, 1086):  # a few cypresses between the monuments
        peninsula += cypress(x, ground_p(x) + 2, rng.uniform(28, 40), PEN)

    # the Golden Horn: its far shore (Fatih/Eyüp hills, small domes) shows in the gap, lighter with distance
    HORN = "#5E4378"
    horn = f'<path d="M1180 {HZ + 4} L1180 {HZ - 20} Q1230 {HZ - 34} 1280 {HZ - 26} Q1320 {HZ - 32} 1360 {HZ - 22} L1360 {HZ + 4}Z" fill="{HORN}"/>'
    horn += houses(rng, 1240, 1330, lambda x: HZ - 22, 6, 14, 8, 16, HORN, lights_far, .5)
    peninsula = horn + peninsula

    # Bosphorus Bridge (behind Galata, far right)
    BR = "#3A2A5C"
    deck_y = HZ - 30
    t1, t2 = 1520, 1780
    bridge = f'<rect x="1420" y="{deck_y}" width="460" height="5" fill="{BR}"/>'
    for tx in (t1, t2):
        bridge += f'<path d="M{tx - 6} {HZ + 2}L{tx - 4} {deck_y - 110}H{tx + 4}L{tx + 6} {HZ + 2}Z" fill="{BR}"/>'
        bridge += f'<rect x="{tx - 7}" y="{deck_y - 70}" width="14" height="3" fill="{BR}"/><rect x="{tx - 7}" y="{deck_y - 20}" width="14" height="3" fill="{BR}"/>'
    main = catenary(t1, deck_y - 108, t2, deck_y - 108, 96)
    side = catenary(1420, deck_y, t1, deck_y - 108, -22)
    cable_d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in side + main)
    bridge += f'<path d="{cable_d}" fill="none" stroke="{BR}" stroke-width="2"/>'
    hangers = "".join(f'<path d="M{f(x)} {f(y)}V{deck_y}"/>' for x, y in main[2:-2:2])
    bridge += f'<g stroke="{BR}" stroke-width=".8" opacity=".8">{hangers}</g>'
    bulbs = [(x, y) for x, y in side[::2] + main[::2]]

    def bridge_lights(color):
        return f'<g fill="{color}">' + "".join(f'<circle cx="{f(x)}" cy="{f(y)}" r="1.8"/>' for x, y in bulbs) + \
               f'</g><path d="{cable_d}" fill="none" stroke="{color}" stroke-width="1" opacity=".55"/>'

    # Galata: the hill across the Golden Horn
    GAL = "#2B2148"
    def ground_g(x):
        if x < 1305:
            return HZ + 4
        return HZ - 6 - 62 * math.exp(-(((x - 1420) / 150) ** 2))
    gland = " ".join(f"L{f(x)} {f(ground_g(x))}" for x in range(1306, 1680, 10))
    galata = f'<path d="M1306 {HZ + 4} {gland} L1680 {HZ + 4}Z" fill="#3A2C5E"/>'
    # back row: higher on the hill, lighter (aerial perspective)
    galata += houses(rng, 1310, 1670, lambda x: ground_g(x) - 10, 16, 36, 12, 26, "#3A2C5E", lights_mid, .7)
    galata += galata_tower(1420, ground_g(1420) + 4, 1.0, GAL)
    # Galata Bridge across the mouth of the Golden Horn, with its lamps
    gb_y = HZ - 9
    galata += f'<rect x="1214" y="{gb_y}" width="112" height="5" fill="{GAL}"/>'
    galata += "".join(f'<rect x="{x}" y="{gb_y + 5}" width="4" height="{HZ + 4 - gb_y - 5}" fill="{GAL}"/>' for x in range(1222, 1326, 16))
    galata += "".join(f'<path d="M{x} {gb_y}v-9" stroke="{GAL}" stroke-width="1.2"/>' for x in range(1220, 1326, 13))
    lights_mid.append(f'<g fill="{C_LIGHT}">' + "".join(f'<circle cx="{x}" cy="{gb_y - 10}" r="1.6"/>' for x in range(1220, 1326, 13)) + '</g>')
    # front row along the shore, darker
    galata += houses(rng, 1305, 1680, lambda x: HZ - 2 - 14 * math.exp(-(((x - 1420) / 120) ** 2)), 12, 30, 14, 30, GAL, lights_mid, .9)

    # ---------------- Maiden's Tower on its islet ----------------
    MT = "#221A3A"
    mx, my = 1196, 694
    maiden = (f'<path d="M{mx - 62} {my + 4} Q{mx - 40} {my - 10} {mx - 6} {my - 8} Q{mx + 30} {my - 12} {mx + 64} {my + 4}Z" fill="{MT}"/>'
              f'<rect x="{mx - 44}" y="{my - 26}" width="66" height="22" fill="{MT}"/>'
              f'<path d="M{mx - 46} {my - 26}L{mx - 11} {my - 36}L{mx + 24} {my - 26}Z" fill="{MT}"/>'
              f'<rect x="{mx + 6}" y="{my - 66}" width="20" height="44" fill="{MT}"/>'
              f'<rect x="{mx + 3}" y="{my - 70}" width="26" height="4" fill="{MT}"/>'
              f'<rect x="{mx + 9}" y="{my - 86}" width="14" height="16" fill="{MT}"/>'
              f'<path d="M{mx + 7} {my - 86}Q{mx + 16} {my - 104} {mx + 25} {my - 86}Z" fill="{MT}"/>'
              f'<path d="M{mx + 16} {my - 99}v-8" stroke="{MT}" stroke-width="1.6"/>'
              f'<path d="M{mx - 30} {my - 26}a10 9 0 0 1 20 0Z" fill="{MT}"/>')
    maiden_lights = (arches(mx - 40, mx + 20, my - 9, 8, 5, op=.95) + arches(mx + 8, mx + 24, my - 42, 9, 2, op=.95)
                     + arches(mx + 11, mx + 21, my - 74, 7, 1, op=1))
    lantern = (f'<circle cx="{mx + 16}" cy="{my - 79}" r="16" fill="url(#lamp-glow)"/>'
               f'<circle cx="{mx + 16}" cy="{my - 79}" r="2.6" fill="#FFF3C4"/>')
    lamp_defs = ('<radialGradient id="lamp-glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFE7A8" stop-opacity=".9"/>'
                 '<stop offset="1" stop-color="#FFB86E" stop-opacity="0"/></radialGradient>')

    # ---------------- sea ----------------
    water_defs = ('<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">'
                  '<stop offset="0" stop-color="#F6B271"/><stop offset=".07" stop-color="#E0806E"/>'
                  '<stop offset=".2" stop-color="#8A5A84"/><stop offset=".4" stop-color="#3C5B86"/>'
                  '<stop offset=".7" stop-color="#1D4E70"/><stop offset="1" stop-color="#0C2340"/></linearGradient>'
                  '<linearGradient id="refl-fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".55"/>'
                  '<stop offset=".35" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                  f'<mask id="refl-mask"><rect x="0" y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#refl-fade)"/></mask>')
    reflection = (f'<g mask="url(#refl-mask)" opacity=".45"><g transform="translate(0 {2 * HZ + 6}) scale(1 -1)">'
                  f'<use href="#far-shore"/><use href="#mid-shore"/></g></g>')
    sea = f'<rect y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#sea)"/>' + reflection
    # Maiden's Tower reflection
    sea += f'<g opacity=".35" transform="translate(0 {2 * my + 6}) scale(1 -1)"><use href="#maiden"/></g>'

    # sun path on the water: rippled golden strokes, wider toward the viewer
    glint = []
    for i in range(34):
        y = HZ + 6 + i * (i * .14 + 3.2)
        if y > H - 4:
            break
        spread = 10 + i * 5.2
        for _ in range(1 + i // 9):
            x = SUN[0] + rng.uniform(-spread, spread)
            wl = rng.uniform(12, 26) + i * 1.4
            glint.append(f'<path d="M{f(x - wl / 2)} {f(y)}q{f(wl / 4)} {f(-1.6 - i * .05)} {f(wl / 2)} 0t{f(wl / 2)} 0" '
                         f'stroke-width="{f(1.4 + i * .05)}" opacity="{f(max(.18, .9 - i * .02))}"/>')
    # ripple flecks across the sea (perspective: small and dense far away, larger near)
    flecks = []
    crest_rows = (688, 752, 838)
    while len(flecks) < 130:
        t = rng.random() ** 1.6
        y = HZ + 8 + t * (H - HZ - 12)
        if any(abs(y - c) < 9 + (c - HZ) * .06 for c in crest_rows):
            continue
        x = rng.uniform(-30, W + 30)
        wl = 6 + t * 34
        col = "#FFC79A" if y < 700 else "#9FD3D6"
        flecks.append(f'<path d="M{f(x)} {f(y)}q{f(wl / 4)} {f(-1 - t * 3)} {f(wl / 2)} 0t{f(wl / 2)} 0" stroke="{col}" stroke-width="{f(.8 + t * 1.6)}" opacity="{f(.25 + t * .3)}"/>')

    g1, b1 = wave_band(688, 2.2, 100, "#5E5B8C", "#2A4C74", .32, "#FFC79A", .55, 1.2, "wb1")
    g2, b2 = wave_band(752, 4.5, 170, "#2F5A82", "#173E62", .45, "#A8D8DA", .5, 1.6, "wb2", 1.1)
    g3, b3 = wave_band(838, 8.5, 260, "#1B4568", "#0A1F3A", .75, "#7CC4CB", .6, 2.0, "wb3", 2.3)

    # fishing boat with a lantern, bobbing near the left shore
    boat = ('<g transform="translate(420 708)">'
            '<path d="M-26 0 Q0 10 30 0 L24 8 Q0 14 -20 8Z" fill="#2A1F45"/>'
            '<path d="M-2 0 V-26" stroke="#2A1F45" stroke-width="1.6"/>'
            '<path d="M-2 -24 L14 -4 H-2Z" fill="#E9C9A0" opacity=".9"/>'
            '<circle cx="22" cy="-6" r="7" fill="url(#lamp-glow)"/><circle cx="22" cy="-6" r="1.8" fill="#FFF3C4"/></g>')

    # ---------------- assemble the layers (back to front) ----------------
    # Static parts are merged into as few layers as possible: every full-frame layer costs
    # raster time on first paint, so only parts that move independently get their own layer.
    out = '<div class="frame">\n'
    out += layer("sky", sky + f'<g fill="#FFF6DC">{stars}</g>' + sun, sky_defs + sun_defs)
    out += layer("clouds", clouds, cloud_defs)
    out += layer("gulls", f'<g fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{gulls}</g>')
    out += layer("far", f'<g id="far-shore">{islands}{peninsula}</g>' + "".join(lights_far))
    out += layer("bridge", bridge + bridge_lights("#FFD58A"))
    out += layer("bridge-glow", bridge_lights("#7FE3E0"))
    out += layer("mid", f'<g id="mid-shore">{galata}</g>' + "".join(lights_mid))
    out += layer("water", sea, water_defs)
    out += layer("surface", f'<g fill="none" stroke-linecap="round">{"".join(flecks)}</g>'
                 f'<g fill="none" stroke="#FFE7B0" stroke-linecap="round">{"".join(glint)}</g>' + boat, lamp_defs)
    out += layer("maiden", f'<g transform="translate({mx} {my}) scale(1.18) translate({-mx} {-my})"><g id="maiden">{maiden}</g>{maiden_lights}{lantern}</g>')
    out += layer("ferry-far", f'<g transform="translate({W + 100} {HZ + 34}) scale(-.4 .4)">{ferry("#2B2A4A")}</g>')
    out += layer("wave-1", b1, g1)
    out += layer("wave-2", b2, g2)
    out += layer("ferry-near",
                 f'<g transform="translate(0 {HZ + 168})">'
                 '<g stroke="#FFE7C2" stroke-linecap="round" fill="none" opacity=".7"><path d="M-10 64 Q-70 70 -150 64" stroke-width="3"/>'
                 '<path d="M-6 70 Q-90 80 -220 74" stroke-width="2" opacity=".6"/><path d="M0 60 Q-40 62 -90 58" stroke-width="2"/></g>'
                 f'{ferry()}<g transform="translate(0 132) scale(1 -1)" opacity=".16">{ferry()}</g></g>')
    out += layer("wave-3", b3, g3)
    return out + "</div>"


WAVE_PERIODS = {"wave-1": 100, "wave-2": 170, "wave-3": 260}  # used by CSS loop distances (period / W)


# --------------------------------------------------------------------------- menu
# Prices stay in data/menu.json (verified against the printed menu) but are not shown on the site.

def img_tag(src_dir, slug, alt, sizes):
    base = f"{IMG_BASE}/{src_dir}/{slug}"
    return (f'<img src="{base}-400.webp" srcset="{base}-200.webp 200w, {base}-400.webp 400w, {base}-800.webp 623w" '
            f'sizes="{sizes}" width="400" height="400" loading="lazy" decoding="async" alt="{html.escape(alt)}">')


def dish(cat, it, index, compact=False):
    featured = it.get("featured")
    if featured:
        sizes = "(min-width: 900px) 300px, (min-width: 600px) 220px, 104px"
    elif compact:
        sizes = "(min-width: 900px) 220px, 45vw"
    else:
        sizes = "(min-width: 900px) 140px, 104px"
    name = html.escape(it["name"])
    note = f' <span class="dish__note">{html.escape(it["note"])}</span>' if it.get("note") else ""
    desc = f'<p class="dish__desc">{html.escape(it["desc"])}</p>' if it.get("desc") else ""
    badge = '<p class="dish__badge">For sharing</p>' if featured else ""
    cls = "dish dish--featured" if featured else "dish"
    return f'''<article class="{cls}" id="dish-{it["id"]}" style="--i:{min(index, 8)}">
  <div class="dish__img">{img_tag(cat["src"], it["img"], it["alt"], sizes)}</div>
  <div class="dish__body">
    {badge}<h4 class="dish__name">{name}{note}</h4>
    {desc}
  </div>
</article>'''


def addon_block(cat):
    a = cat["addon"]
    imgs = "".join(f'<span class="addon__img">{img_tag(a["src"], im["img"], im["alt"], "64px")}</span>' for im in a["imgs"])
    return f'''<aside class="addon" id="dish-{a["id"]}" aria-label="Salad add-on">
  <div class="addon__imgs">{imgs}</div>
  <div class="addon__body">
    <h4 class="dish__name">{html.escape(a["name"])}</h4>
    <p class="dish__desc">{html.escape(a["desc"])}</p>
  </div>
</aside>'''


def menu_html():
    out = []
    for cat in MENU["categories"]:
        compact = all(not it.get("desc") or it["id"] == "soft-drinks" for it in cat["items"])
        grid_cls = "dish-grid dish-grid--tiles" if compact else "dish-grid"
        items = "\n".join(dish(cat, it, i, compact) for i, it in enumerate(cat["items"]))
        addon = addon_block(cat) if "addon" in cat else ""
        intro = f'<p class="cat__intro">{html.escape(cat["intro"])}</p>' if cat.get("intro") else ""
        out.append(f'''<section class="cat" id="{cat["id"]}" aria-labelledby="{cat["id"]}-title">
<header class="cat__head">
  <h3 class="cat__title" id="{cat["id"]}-title">{html.escape(cat["title"])}</h3>
  {intro}
</header>
<div class="{grid_cls}">
{items}
</div>
{addon}
</section>''')
    return "\n".join(out)


def chips_html():
    return "\n".join(f'<li><a class="tab" href="#{c["id"]}">{html.escape(c["title"].replace(" & Appetizers", ""))}</a></li>' for c in MENU["categories"])


# ---------------------------------------------------------------------------- share
# Set this to the live address (e.g. "https://istanbulcafequartzsite.com") and rebuild.
# Link previews (WhatsApp, iMessage, Facebook, X) only load an image from an absolute URL.
SITE_URL = "https://gozdehavinfidan.github.io/istanbul-cafe"

SHARE_TITLE = "Istanbul Café Quartzsite | Authentic Turkish Cuisine"
SHARE_DESC = "Meze, grilled kebabs, gyro and baklava in Quartzsite, Arizona, inspired by the everyday cooking of Istanbul."


def share_html():
    base = SITE_URL.rstrip("/")
    img = f"{base}/assets/og/share.jpg" if base else "assets/og/share.jpg"
    lines = [
        f'<meta property="og:site_name" content="Istanbul Café Quartzsite">',
        f'<meta property="og:title" content="{html.escape(SHARE_TITLE)}">',
        f'<meta property="og:description" content="{html.escape(SHARE_DESC)}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:locale" content="en_US">',
        f'<meta property="og:image" content="{img}">',
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Istanbul Café Quartzsite: an illustrated Istanbul skyline at sunset over the Bosphorus">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{html.escape(SHARE_TITLE)}">',
        f'<meta name="twitter:description" content="{html.escape(SHARE_DESC)}">',
        f'<meta name="twitter:image" content="{img}">',
    ]
    if base:
        lines += [f'<meta property="og:url" content="{base}/">', f'<link rel="canonical" href="{base}/">']
    return chr(10).join("  " + l for l in lines)


def inject(text, name, content):
    pat = re.compile(rf"(<!-- BUILD:{name} -->)(.*?)(<!-- /BUILD:{name} -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"marker BUILD:{name} not found")
    return pat.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(3), text)


if __name__ == "__main__":
    text = INDEX.read_text(encoding="utf-8")
    text = inject(text, "hero", hero_svg())
    text = inject(text, "chips", chips_html())
    text = inject(text, "menu", menu_html())
    text = inject(text, "share", share_html())
    if not SITE_URL:
        print("note: SITE_URL is empty, so link previews need it set to the live address (see tools/build.py)")
    INDEX.write_text(text, encoding="utf-8", newline="\n")
    n = sum(len(c["items"]) for c in MENU["categories"])
    print(f"built index.html: {n} dishes + add-ons, {len(MENU['categories'])} categories, {INDEX.stat().st_size // 1024} KB")
