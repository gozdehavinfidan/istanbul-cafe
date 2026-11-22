"""End-to-end checks for the Istanbul Café site.

Usage:
  python -m http.server 8765 --bind 127.0.0.1      (from the project root, in another terminal)
  pip install playwright && python tools/test_site.py [--base URL] [--shots DIR] [--chrome PATH]

By default it uses the installed Google Chrome (no browser download needed), else Playwright's Chromium.
Checks, at 375 / 768 / 1024 / 1440 px:
  * rendered menu matches data/menu.json (names, image file + alt per item); no prices or Turkish UI phrases on the page
  * every image loads, every in-page link resolves, no console errors, no horizontal overflow
  * keyboard: skip link, category tabs, view toggle (Enter/Space), visible focus
  * reduced motion: animations disabled
Exits non-zero if anything fails.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MENU = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
WIDTHS = {"mobile": (375, 812), "tablet": (768, 1024), "laptop": (1024, 768), "desktop": (1440, 900)}

failures = []


def launch_default(pw):
    try:
        return pw.chromium.launch(channel="chrome")  # installed Google Chrome
    except Exception:
        return pw.chromium.launch()

AXE = None  # path to axe.min.js (optional, --axe)


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("  FAIL", msg)
    return cond


def expected_items():
    out = []
    for cat in MENU["categories"]:
        for it in cat["items"]:
            out.append({"id": f"dish-{it['id']}", "cat": cat["id"], "name": it["name"],
                        "img": f"{cat['src']}/{it['img']}-400.webp", "alt": it["alt"]})
    return out


def run(base, shots, chrome):
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome) if chrome else launch_default(pw)

        for label, (w, h) in WIDTHS.items():
            print(f"[{label} {w}x{h}]")
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.on("pageerror", lambda e: errors.append(str(e)))
            bad_responses = []
            page.on("response", lambda r: r.status >= 400 and bad_responses.append(f"{r.status} {r.url}"))
            page.goto(base, wait_until="networkidle")
            page.screenshot(path=str(shots / f"{label}-hero.png"))

            # bring every image into view (as a visitor would) and wait for it, bounded per image;
            # anything that never loads is reported by the broken-image check below
            page.evaluate("""async () => {
                for (const img of Array.from(document.images)) {
                    img.scrollIntoView({ block: 'center' });
                    if (!img.complete) await new Promise(r => { img.addEventListener('load', r); img.addEventListener('error', r); setTimeout(r, 4000); });
                }
            }""")
            page.wait_for_load_state("networkidle")
            page.evaluate("document.querySelectorAll('.reveal').forEach(e => e.classList.add('is-in'))")
            page.wait_for_timeout(900)

            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(overflow <= 0, f"{label}: horizontal overflow of {overflow}px")

            broken = page.evaluate("Array.from(document.images).filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.currentSrc || i.src)")
            check(not broken, f"{label}: images failed to load: {broken}")

            anchors = page.evaluate("Array.from(document.querySelectorAll('a[href^=\"#\"]')).map(a => a.getAttribute('href')).filter(h => h.length > 1 && !document.getElementById(h.slice(1)))")
            check(not anchors, f"{label}: in-page links with no target: {anchors}")

            check(not errors, f"{label}: console errors: {errors}")
            check(not bad_responses, f"{label}: failed requests: {bad_responses}")

            # small tap targets (interactive elements under 24px in either dimension)
            small = page.evaluate("""Array.from(document.querySelectorAll('a, button')).filter(el => {
                const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
                return r.width && s.visibility !== 'hidden' && !el.closest('.sr-only') && !el.classList.contains('skip-link') && !(s.display === 'inline' && el.closest('p')) && (r.width < 24 || r.height < 24);
              }).map(el => el.textContent.trim() || el.getAttribute('aria-label'))""")
            check(not small, f"{label}: tap targets under 24px: {small}")

            if AXE and AXE.exists():
                page.add_script_tag(path=str(AXE))
                res = page.evaluate("""async () => { const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] } });
                    return r.violations.map(v => v.id + ' (' + v.impact + '): ' + v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')); }""")
                check(not res, f"{label}: axe violations: {res}")
                print(f"  axe: {len(res)} violations")

            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(shots / f"{label}-full.png"), full_page=True)

            if label == "mobile":
                # menu data integrity
                rendered = page.evaluate("""Array.from(document.querySelectorAll('.dish')).map(d => ({
                    id: d.id, cat: d.closest('.cat').id,
                    name: d.querySelector('.dish__name').childNodes[0].textContent.trim(),
                    img: d.querySelector('img').getAttribute('src').replace('assets/img/menu/', ''),
                    alt: d.querySelector('img').alt }))""")
                exp = expected_items()
                check(len(rendered) == len(exp) == 35, f"dish count rendered={len(rendered)} expected={len(exp)}")
                for e, r in zip(exp, rendered):
                    for k in ("id", "cat", "name", "img", "alt"):
                        check(e[k] == r[k], f"menu mismatch {e['id']}.{k}: expected {e[k]!r}, got {r[k]!r}")
                addon = page.evaluate("[document.querySelector('.addon .dish__name').textContent, Array.from(document.querySelectorAll('.addon img')).map(i => i.getAttribute('src'))]")
                check(addon[0] == "Add Chicken or Beef" and len(addon[1]) == 2, f"add-on wrong: {addon}")
                text = page.evaluate("document.body.innerText")
                check("$" not in text and "dollar" not in text.lower(), "a price or currency still appears on the page")
                hrefs = page.evaluate("Array.from(document.querySelectorAll('#visit a, .site-footer a')).map(a => a.getAttribute('href'))")
                for need in ("tel:+19289273070", "mailto:watnesbms@gmail.com", "https://maps.app.goo.gl/6JqBSafxvdTHMwcP8"):
                    check(need in hrefs, f"contact link missing: {need}")
                check("1270 W Main St" in text and "Quartzsite, AZ 85346" in text, "address missing")
                check("[Add" not in text, "a placeholder is still visible")
                for phrase in ("Hoş geldiniz", "Sofraya", "buyurun", "Çay", "Mezeler", "Tatlılar", "Our Table"):
                    check(phrase not in text, f"removed phrase still on page: {phrase}")
                print(f"  menu: {len(rendered)} dishes + add-on verified against data/menu.json")

                # list view toggle via keyboard
                page.focus("[data-view-btn=list]")
                page.keyboard.press("Enter")
                check(page.get_attribute("#menu", "data-view") == "list", "Enter on List button did not switch view")
                check(page.get_attribute("[data-view-btn=list]", "aria-pressed") == "true", "aria-pressed not updated")
                hidden = page.evaluate("getComputedStyle(document.querySelector('.dish__img')).display")
                check(hidden == "none", "images still visible in list view")
                page.locator("#menu-bar").scroll_into_view_if_needed()
                page.evaluate("document.getElementById('plates').scrollIntoView()")
                page.wait_for_timeout(500)
                page.screenshot(path=str(shots / "mobile-listview.png"))
                page.focus("[data-view-btn=photos]")
                page.keyboard.press("Space")
                check(page.get_attribute("#menu", "data-view") == "photos", "Space on Photos button did not switch view")

                # chip jump + active state
                page.evaluate("window.scrollTo(0,0)")
                page.click("a.tab[href='#desserts']")
                page.wait_for_timeout(1200)
                top = page.evaluate("document.querySelector('#desserts .cat__head').getBoundingClientRect().top")
                bar_bottom = page.evaluate("document.getElementById('menu-bar').getBoundingClientRect().bottom")
                check(top >= bar_bottom - 8, f"category heading hidden under sticky bar after jump (top={top}, bar={bar_bottom})")
                page.screenshot(path=str(shots / "mobile-desserts.png"))
                # scroll a bit to trigger active chip on desserts (last section may not reach top)
                page.click("a.tab[href='#plates']")
                page.wait_for_timeout(1200)
                cur = page.evaluate("document.querySelector('.tab[aria-current=true]')?.hash")
                check(cur == "#plates", f"active tab after jump to plates is {cur}")
                page.screenshot(path=str(shots / "mobile-plates.png"))

                # keyboard: first Tab reaches the skip link, and it works
                page.evaluate("window.scrollTo(0,0)")
                page.goto(base, wait_until="networkidle")
                page.keyboard.press("Tab")
                check(page.evaluate("document.activeElement.className") == "skip-link", "first Tab does not reach skip link")
                page.screenshot(path=str(shots / "mobile-skiplink.png"))
                page.keyboard.press("Enter")
                check(page.evaluate("location.hash") == "#main", "skip link did not move to #main")
                # tab order sanity: walk 40 stops, each must show a visible outline
                page.goto(base, wait_until="networkidle")
                no_outline = []
                for _ in range(60):
                    page.keyboard.press("Tab")
                    if page.evaluate("document.activeElement === document.body"):
                        break  # wrapped past the last focusable element
                    info = page.evaluate("""(() => { const a = document.activeElement; const s = getComputedStyle(a);
                        return [a.tagName + ' ' + (a.textContent || '').trim().slice(0, 24), s.outlineStyle, s.outlineWidth]; })()""")
                    if info[1] == "none" or info[2] == "0px":
                        no_outline.append(info[0])
                check(not no_outline, f"focus without visible outline: {no_outline}")
            ctx.close()

        # reduced motion: no running animations, no parallax
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(base, wait_until="networkidle")
        anim = page.evaluate("document.getAnimations().filter(a => a.playState === 'running').length")
        check(anim == 0, f"reduced motion: {anim} animations still running")
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(300)
        p = page.evaluate("getComputedStyle(document.querySelector('.hero')).getPropertyValue('--p').trim()")
        check(p in ("0", ""), f"reduced motion: parallax still active (--p={p})")
        reveal = page.evaluate("document.querySelectorAll('.reveal').length")
        check(reveal == 0, "reduced motion: reveal-on-scroll still applied")
        print("[reduced motion] checked")
        ctx.close()

        # no-JS: menu is still fully present
        ctx = browser.new_context(viewport={"width": 375, "height": 812}, java_script_enabled=False)
        page = ctx.new_page()
        page.goto(base, wait_until="networkidle")
        n = page.evaluate("document.querySelectorAll('.dish').length") if False else page.locator(".dish").count()
        check(n == 35, f"no-JS: only {n} dishes visible")
        print("[no-js] checked")
        ctx.close()
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765/")
    ap.add_argument("--shots", default=str(ROOT / "_shots"))
    ap.add_argument("--chrome", default=None, help="path to a Chrome/Chromium binary (default: installed Chrome, else Playwright Chromium)")
    ap.add_argument("--axe", help="path to axe-core's axe.min.js to run an accessibility audit")
    a = ap.parse_args()
    AXE = Path(a.axe) if a.axe else None
    run(a.base, Path(a.shots), a.chrome)
    print(f"\n{'ALL CHECKS PASSED' if not failures else str(len(failures)) + ' FAILURE(S)'}")
    sys.exit(1 if failures else 0)
