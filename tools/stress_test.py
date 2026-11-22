"""Phone stress test for the Istanbul Café Quartzsite site.

Usage:
  python -m http.server 8765 --bind 127.0.0.1        (project root, another terminal)
  pip install playwright && python -m playwright install webkit
  python tools/stress_test.py [--shots DIR]

Runs iPhones in WebKit (Safari's engine) and Android phones in Chrome, with real device
profiles (viewport, pixel ratio, touch, mobile UA). Per device it checks:
  layout:       no sideways scroll, header fits, headline fits, buttons on screen and >= 44 px tall
  touch:        tap "Explore the Menu", tap a category tab, tap the list/photo toggle
  contact:      tap-to-call / mailto / map links present
  text 200%:    doubled base font size still has no sideways scroll
  scroll storm: 60 rapid random jumps + continuous touch-like scrolling, no errors
Chrome only:    frame rate while scrolling with 4x CPU throttling (reported, not gated); load on a slow 3G link.
Exits non-zero if any check fails.
"""
import argparse
import random
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8765/"

failures, notes = [], []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("    FAIL", msg)
    return cond


def settle(page, timeout=6000):
    """Wait until smooth scrolling has finished (scroll position unchanged for 300 ms)."""
    last, still, waited = None, 0, 0
    while waited < timeout:
        page.wait_for_timeout(150)
        waited += 150
        y = page.evaluate("scrollY")
        still = still + 1 if y == last else 0
        last = y
        if still >= 2 and waited > 400:
            break


def run_device(browser, label, profile, shots, engine):
    print(f"[{label}] {profile['viewport']['width']}x{profile['viewport']['height']} @{profile.get('device_scale_factor', 1)}x ({engine})")
    ctx = browser.new_context(**profile)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(3200)  # let the intro finish
    page.screenshot(path=str(shots / f"{label}-hero.png"))

    m = page.evaluate("""() => {
        const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, t: b.top, b: b.bottom, w: b.width, h: b.height}; };
        const btns = Array.from(document.querySelectorAll('.hero__actions .btn')).map(e => { const b = e.getBoundingClientRect(); return {l: b.left, r: b.right, t: b.top, b: b.bottom, h: b.height}; });
        const h1 = document.querySelector('.hero__title');
        return { vw: innerWidth, vh: innerHeight, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
                 header: r('.site-header'), brand: r('.brand'), nav: r('.site-nav ul'), h1: r('.hero__title'),
                 h1Overflow: h1.scrollWidth - h1.clientWidth, btns };
    }""")
    check(m["sw"] <= m["cw"], f"{label}: sideways scroll ({m['sw']} > {m['cw']})")
    br, nv = m["brand"], m["nav"]
    overlap = br["l"] < nv["r"] - 1 and nv["l"] < br["r"] - 1 and br["t"] < nv["b"] - 1 and nv["t"] < br["b"] - 1
    check(not overlap, f"{label}: brand overlaps navigation")
    check(m["header"]["h"] <= 66, f"{label}: header wrapped to two rows at normal text size ({m['header']['h']:.0f}px)")
    check(m["brand"]["b"] <= m["header"]["b"] + 1 and m["nav"]["b"] <= m["header"]["b"] + 1, f"{label}: header content spills out of the header")
    check(m["h1"]["r"] <= m["vw"] + 1 and m["h1Overflow"] <= 1, f"{label}: headline is wider than the screen")
    for i, b in enumerate(m["btns"]):
        check(b["l"] >= 0 and b["r"] <= m["vw"] + 1, f"{label}: hero button {i + 1} off screen")
        check(b["h"] >= 44, f"{label}: hero button {i + 1} only {b['h']:.0f}px tall")

    # touch: Explore the Menu
    page.tap(".hero__actions .btn--primary")
    settle(page)
    top = page.evaluate("document.getElementById('menu').getBoundingClientRect().top")
    check(-40 <= top <= 140, f"{label}: 'Explore the Menu' did not bring the menu into view (top={top:.0f})")
    page.screenshot(path=str(shots / f"{label}-menu.png"))

    # touch: a category tab far down the list
    tab = page.locator("a.tab[href='#desserts']")
    tab.scroll_into_view_if_needed()
    tab.tap()
    settle(page)
    head = page.evaluate("document.querySelector('#desserts .cat__head').getBoundingClientRect().top")
    bar = page.evaluate("document.getElementById('menu-bar').getBoundingClientRect().bottom")
    check(bar - 8 <= head <= m["vh"] - 60, f"{label}: Desserts heading not visible after tapping its tab (head={head:.0f}, bar={bar:.0f})")
    page.screenshot(path=str(shots / f"{label}-desserts.png"))

    # touch: list / photo toggle
    page.tap("[data-view-btn=list]")
    check(page.get_attribute("#menu", "data-view") == "list", f"{label}: list view tap failed")
    page.tap("[data-view-btn=photos]")
    check(page.get_attribute("#menu", "data-view") == "photos", f"{label}: photo view tap failed")

    # contact links
    hrefs = page.evaluate("Array.from(document.querySelectorAll('#visit a')).map(a => a.getAttribute('href'))")
    check("tel:+19289273070" in hrefs and "mailto:watnesbms@gmail.com" in hrefs, f"{label}: contact links missing")

    # small tap targets (block-level controls only; inline text links in sentences are exempt)
    small = page.evaluate("""Array.from(document.querySelectorAll('a, button')).filter(el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return r.width && s.visibility !== 'hidden' && !el.closest('.sr-only') && !el.classList.contains('skip-link')
               && !(s.display === 'inline' && el.closest('p')) && (r.height < 24 || r.width < 24);
    }).map(el => (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 30))""")
    check(not small, f"{label}: tap targets under 24px: {small}")

    # scroll storm
    page.evaluate("""async () => {
        const H = document.documentElement.scrollHeight;
        for (let i = 0; i < 60; i++) { window.scrollTo(0, Math.random() * H); await new Promise(r => requestAnimationFrame(r)); }
        for (let y = 0; y < H; y += 90) { window.scrollTo(0, y); await new Promise(r => requestAnimationFrame(r)); }
        for (let y = H; y > 0; y -= 140) { window.scrollTo(0, y); await new Promise(r => requestAnimationFrame(r)); }
    }""")
    page.wait_for_timeout(600)
    sw = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check(sw <= 0, f"{label}: sideways scroll appeared after the scroll storm ({sw}px)")

    # 200% text
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    page.wait_for_timeout(400)
    sw = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check(sw <= 0, f"{label}: sideways scroll at 200% text ({sw}px)")
    page.evaluate("window.scrollTo(0, document.getElementById('visit').offsetTop)")
    page.wait_for_timeout(800)
    page.screenshot(path=str(shots / f"{label}-text200.png"))
    page.evaluate("document.documentElement.style.fontSize = ''")

    check(not errors, f"{label}: script errors: {errors[:3]}")

    # Chrome only: frame rate under 4x CPU throttling while scrolling the hero and the menu
    if engine == "chromium":
        cdp = ctx.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        page.evaluate("window.scrollTo(0, 0)")
        fps = page.evaluate("""() => new Promise(res => {
            let frames = 0, y = 0; const H = document.documentElement.scrollHeight; const t0 = performance.now();
            function step() { frames++; y = (y + 24) % H; window.scrollTo(0, y);
                if (performance.now() - t0 < 4000) requestAnimationFrame(step); else res(Math.round(frames / ((performance.now() - t0) / 1000))); }
            requestAnimationFrame(step); })""")
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        notes.append(f"{label}: ~{fps} fps while scrolling with 4x CPU throttling")
        print(f"    scroll frame rate (4x CPU throttle): ~{fps} fps")
        # informational only: in headless software rendering this number is capped by the environment
        # (hiding the hero, all animations or all images does not change it), so it is not a pass/fail gate
    ctx.close()


def slow_3g(browser, profile):
    ctx = browser.new_context(**profile)
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 400, "downloadThroughput": 400 * 1024 / 8, "uploadThroughput": 400 * 1024 / 8})
    t0 = time.time()
    page.goto(BASE, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector(".hero__title", state="visible")
    t_dom = time.time() - t0
    fcp = page.evaluate("new Promise(r => { const e = performance.getEntriesByName('first-contentful-paint')[0]; if (e) r(e.startTime); else new PerformanceObserver(l => r(l.getEntries()[0].startTime)).observe({type: 'paint', buffered: true}); })")
    page.wait_for_load_state("load", timeout=120000)
    t_load = time.time() - t0
    notes.append(f"slow 3G (400 kbps, 400 ms): first paint {fcp / 1000:.1f}s, page usable {t_dom:.1f}s, fully loaded {t_load:.1f}s")
    print(f"[slow 3G] first paint {fcp / 1000:.1f}s, usable {t_dom:.1f}s, fully loaded {t_load:.1f}s")
    check(fcp < 6000, f"slow 3G: first paint took {fcp / 1000:.1f}s")
    ctx.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=str(ROOT / "_shots" / "stress"))
    a = ap.parse_args()
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        d = pw.devices
        android = {
            "galaxy-fold-folded": {"viewport": {"width": 280, "height": 653}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True,
                                   "user_agent": d["Galaxy S9+"]["user_agent"]},
            "galaxy-s9": d["Galaxy S9+"],
            "pixel-7": d["Pixel 7"],
            "pixel-7-landscape": d["Pixel 7 landscape"],
        }
        iphones = {
            "iphone-se": d["iPhone SE"],
            "iphone-13": d["iPhone 13"],
            "iphone-14-pro-max": d["iPhone 14 Pro Max"],
            "iphone-13-landscape": d["iPhone 13 landscape"],
            "ipad-mini": d["iPad Mini"],
        }
        try:
            chromium = pw.chromium.launch(channel="chrome")  # installed Google Chrome
        except Exception:
            chromium = pw.chromium.launch()
        for label, prof in android.items():
            prof = {k: v for k, v in prof.items() if k != "default_browser_type"}
            run_device(chromium, label, prof, shots, "chromium")
        slow_3g(chromium, {k: v for k, v in d["Pixel 7"].items() if k != "default_browser_type"})
        chromium.close()
        try:
            webkit = pw.webkit.launch()
        except Exception as e:  # WebKit not installed
            webkit = None
            failures.append(f"WebKit not available ({str(e).splitlines()[0]}); run: python -m playwright install webkit")
        if webkit:
            for label, prof in iphones.items():
                prof = {k: v for k, v in prof.items() if k != "default_browser_type"}
                run_device(webkit, label, prof, shots, "webkit")
            webkit.close()
    print("\n" + "\n".join("note: " + n for n in notes))
    print(f"\n{'ALL STRESS CHECKS PASSED' if not failures else str(len(failures)) + ' FAILURE(S)'}")
    sys.exit(1 if failures else 0)
