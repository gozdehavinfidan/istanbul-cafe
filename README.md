# Istanbul Café Quartzsite website

A static, single-page site for Istanbul Café Quartzsite (Quartzsite, Arizona). It needs no build step or framework, and it runs on any static web host.

## Run it locally

```bash
cd istanbul-cafe
python -m http.server 8000
```

Then open <http://localhost:8000>. (Opening `index.html` straight from disk also works.)

## Business details

These details appear in the Visit section, the footer and the search-engine data (JSON-LD in `<head>`):
- **Address:** 1270 W Main St, Quartzsite, AZ 85346, USA. The "Get directions" link opens Google Maps.
- **Phone:** (928) 927-3070, as a tap-to-call link.
- **Email:** watnesbms@gmail.com

**Opening hours are intentionally not listed.** The Contact card asks guests to call for the day's hours.

Once the site has a domain, make `og:image` an absolute URL and add `<meta property="og:url">`. Social networks ignore relative image paths.

## Editing the menu

`data/menu.json` is the single source of truth for dish names, descriptions, photos, alt text and short category intros. It also keeps the verified prices from the printed menu, but **prices are intentionally not shown on the site**. After editing it, regenerate the page:

```bash
python tools/build.py           # rewrites the menu, category links and hero art inside index.html
```

To add a new dish photo, put the original in `_src/istanbul-cafe/<category>/<slug>.webp` (the originals are kept out of the repository), then run `pip install pillow` and `python tools/resize_images.py`. This creates the 200/400/800 px web versions.

## Testing

```bash
pip install playwright
python -m http.server 8765 --bind 127.0.0.1   # in another terminal
python tools/test_site.py [--axe path/to/axe.min.js]
```

The test suite uses the installed Google Chrome. At 375, 768, 1024 and 1440 px it checks:
- every menu item, photo and alt text against `menu.json`, and that no prices or removed Turkish phrases appear
- that every image loads and every in-page link resolves
- for console errors and horizontal overflow
- tap target sizes
- keyboard use (skip link, category chips, Photos/List toggle, visible focus)
- that reduced motion turns all animation off
- that the full menu shows without JavaScript
- an axe-core WCAG 2.1 AA audit, when `--axe` is given

## Project layout

```
index.html              the page (menu + hero art injected by tools/build.py)
css/styles.css          all styles; motion is inside prefers-reduced-motion: no-preference
js/main.js              progressive enhancement: header, parallax, active category, view toggle
data/menu.json          menu data (verified against the two printed menu photos)
assets/img/menu/        dish photos, 200/400/800 px WebP
assets/svg/             tile.svg (İznik-inspired pattern), favicon.svg
assets/fonts/           self-hosted fonts + their licences
tools/                  build.py, resize_images.py, test_site.py
site.webmanifest        app name, colours and icons for home-screen installs
assets/icons/, assets/og/   app icons and the 1200x630 link-preview image (tools/make_share_assets.py)
```

## The opening illustration

The opening scene is "Sunset from Üsküdar", the classic Istanbul view looking west across the Bosphorus, drawn as original vector art by `tools/build.py`:
- the Maiden's Tower (Kız Kulesi) on its islet, with a glowing lantern
- the historic peninsula silhouetted against an orange-to-violet dusk sky, kept deliberately simple: the Valens Aqueduct, Hagia Sophia as the single domed monument, and Topkapı Palace with its cypresses
- Galata Tower across the Golden Horn with the Galata Bridge, and the Bosphorus Bridge, whose cable lights slowly shift colour like its real LED system
- city ferries, a fishing boat with a lantern, gliding gulls, stars, and layered sine-curve waves that loop seamlessly

## Motion

- **Intro (about 2.5 s):** the sky fades up and the shores rise from the sea in depth layers. The title is revealed line by line, then the ornament, tagline, buttons and header appear.
- **Ambient:** three wave bands drift at different speeds. Ferries cross, the sun path and ripples shimmer, clouds and gulls drift, the bridge lights change colour, and the tile bands drift slowly.
- **Interaction:** on desktop, the illustration layers move slightly with the pointer, and scrolling adds parallax. Section headings rise word by word, About photos reveal, and menu cards come in staggered. Category tabs have an animated underline, and a progress line runs along the header.
- **Performance:** the scene uses 15 GPU-composited layers. Static parts are merged, and the depth variables are non-inheriting `@property` values. Sections below the fold use `content-visibility`. Every animation stops for visitors who prefer reduced motion, and the page is fully usable without JavaScript.

## Hosting notes

Turn on gzip/brotli and long cache headers for `/assets/` on the host (Netlify, Cloudflare Pages and GitHub Pages do this by default). This is the main remaining Lighthouse suggestion. Measured locally with Lighthouse 12 (mobile, throttled, software rendering): Performance 82–94 across runs, Accessibility 100, Best Practices 100, SEO 100, with no layout shift. Most of the run-to-run variation comes from the hero intro animation; on devices with a GPU, its composited layers are cheaper. First load is about 440 KB.

## Credits and licences

- **Illustrations**: the Galata waterfront scene, ferries, tea glass, İznik-style tile, tulip and flourish ornaments, and favicon are original artwork made for this site.
- **Dish photography and menu content**: supplied by Istanbul Café.
- **Typefaces**: all under the [SIL Open Font License 1.1](https://openfontlicense.org), which permits commercial use. Licence files are in `assets/fonts/*/LICENSE`. They were obtained via [Fontsource](https://fontsource.org).
  - **Marcellus**: © 2012 Brian J. Bonislawsky (Astigmatic), Reserved Font Name "Marcellus"
  - **Jost**: © 2020 The Jost Project Authors
- No third-party code or libraries are bundled.
