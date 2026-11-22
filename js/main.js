/* Istanbul Café: progressive enhancement only. Every section is readable and navigable without JS. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  const motionOK = () => !reduceMotion.matches;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  };

  const header = $("#top-bar");
  const hero = $(".hero");
  const menu = $("#menu");
  const bar = $("#menu-bar");
  const root = document.documentElement;
  // elements that read the hero depth variables; set them directly (they are registered as
  // non-inheriting in CSS, so updates never restyle the thousand SVG nodes inside the layers)
  const depthEls = hero ? $$(".layer, .hero__content", hero) : [];
  const setDepth = (name, value) => depthEls.forEach((el) => el.style.setProperty(name, value));
  let lastP = -1;

  /* ---------- Scroll-driven state: header, parallax, progress line, sticky bar ---------- */
  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      // all reads first, then all writes: no forced synchronous layout
      const y = window.scrollY;
      const max = Math.max(1, root.scrollHeight - window.innerHeight);
      const heroH = hero ? hero.offsetHeight || 1 : 1;
      const headerH = header.offsetHeight;
      // the menu is far below the hero: skip measuring it (and forcing its layout) until we get close
      const nearMenu = y > heroH * 0.6;
      const stuck = nearMenu && bar ? bar.getBoundingClientRect().top <= headerH + 1 : false;
      const current = nearMenu ? currentCategory(headerH) : null;

      header.classList.toggle("is-solid", y > 40);
      header.style.setProperty("--progress", (y / max).toFixed(4)); // scoped to the header, not :root
      const p = Math.min(1, y / heroH);
      if (hero && motionOK() && Math.abs(p - lastP) > 0.0005) { setDepth("--p", p.toFixed(3)); lastP = p; }
      if (bar) bar.classList.toggle("is-stuck", stuck);
      applyActive(current);
      ticking = false;
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });

  /* ---------- Pointer depth on the hero: layers drift a few pixels toward the cursor ---------- */
  if (hero && finePointer.matches && motionOK()) {
    let tx = 0, ty = 0, cx = 0, cy = 0, raf = 0;
    const step = () => {
      cx += (tx - cx) * 0.06;
      cy += (ty - cy) * 0.06;
      setDepth("--mx", cx.toFixed(4));
      setDepth("--my", cy.toFixed(4));
      raf = Math.abs(tx - cx) + Math.abs(ty - cy) > 0.001 ? requestAnimationFrame(step) : 0;
    };
    hero.addEventListener("pointermove", (e) => {
      const r = hero.getBoundingClientRect();
      tx = (e.clientX - r.left) / r.width - 0.5;
      ty = (e.clientY - r.top) / r.height - 0.5;
      if (!raf) raf = requestAnimationFrame(step);
    });
    hero.addEventListener("pointerleave", () => { tx = 0; ty = 0; if (!raf) raf = requestAnimationFrame(step); });
  }

  /* ---------- Pause the hero's loops while it is off screen (saves battery) ---------- */
  if (hero && "IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => hero.classList.toggle("is-paused", !e.isIntersecting)).observe(hero);
  }

  /* ---------- Menu view toggle: photos / list ---------- */
  const viewBtns = $$("[data-view-btn]");
  function setView(view, persist) {
    if (!menu) return;
    menu.dataset.view = view;
    viewBtns.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.viewBtn === view)));
    if (persist) store.set("ic-menu-view", view);
  }
  viewBtns.forEach((b) => b.addEventListener("click", () => setView(b.dataset.viewBtn, true)));
  const savedView = store.get("ic-menu-view");
  if (savedView === "list" || savedView === "photos") setView(savedView, false);

  /* ---------- Active category tab ---------- */
  const tabs = $$(".tab");
  const tabList = $(".menu-bar__cats ul");
  const cats = tabs.map((t) => document.getElementById(t.hash.slice(1))).filter(Boolean);
  let activeId = null;

  function setActive(id) {
    if (id === activeId) return;
    activeId = id;
    tabs.forEach((t) => {
      if (t.hash === "#" + id) {
        t.setAttribute("aria-current", "true");
        // keep the active tab visible inside the horizontally scrolling bar, without moving the page
        const left = t.offsetLeft - tabList.clientWidth / 2 + t.offsetWidth / 2;
        tabList.scrollTo({ left, behavior: motionOK() ? "smooth" : "auto" });
      } else {
        t.removeAttribute("aria-current");
      }
    });
  }
  function currentCategory(headerH) {
    if (!cats.length) return null;
    const line = headerH + (bar ? bar.offsetHeight : 0) + 80;
    let current = null;
    for (const cat of cats) if (cat.getBoundingClientRect().top <= line) current = cat.id;
    return current;
  }
  function applyActive(current) {
    if (current) setActive(current);
    else if (activeId) { tabs.forEach((t) => t.removeAttribute("aria-current")); activeId = null; }
  }

  // After a tab jump, move keyboard focus to the category heading so screen readers follow.
  tabs.forEach((t) => t.addEventListener("click", () => {
    const heading = document.getElementById(t.hash.slice(1))?.querySelector(".cat__title");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      setTimeout(() => heading.focus({ preventScroll: true }), motionOK() ? 500 : 0);
    }
  }));

  /* ---------- Scroll reveals ----------
     Set up during idle time so this work never competes with the hero's intro animation.
     Nothing depends on it: if it runs late, content is simply shown without the reveal. */
  const whenIdle = window.requestIdleCallback || ((cb) => setTimeout(cb, 300));
  whenIdle(setupReveals, { timeout: 2500 });
  function setupReveals() {
  if (motionOK() && "IntersectionObserver" in window) {
    // headings rise word by word (the text stays one accessible string)
    $$(".about h2, .visit h2, .menu__head h2").forEach((h) => {
      const words = h.textContent.trim().split(/\s+/);
      h.setAttribute("aria-label", h.textContent.trim());
      h.innerHTML = words.map((w, i) => `<span class="word" aria-hidden="true"><span style="--w:${i}">${w}</span></span>`).join(" ");
      h.classList.add("split");
    });
    $$(".feature").forEach((f, i) => f.style.setProperty("--i", i));

    const els = $$(".split, .about__text, .feature, .cat, .visit__card, .menu__intro");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -10% 0px" });
    // only hide what is below the fold right now, so nothing visible flashes (measure all, then write)
    // at the top of the page everything after the hero is below the fold: no need to measure
    const fold = window.innerHeight * 0.9;
    const atTop = window.scrollY < 10 && !location.hash;
    const below = atTop ? els : els.filter((el) => el.getBoundingClientRect().top > fold);
    below.forEach((el) => { el.classList.add("reveal"); io.observe(el); });
    // a jump (tab, link, find-in-page) must never land on hidden content
    const revealAll = () => els.forEach((el) => el.classList.add("is-in"));
    window.addEventListener("hashchange", revealAll);
    document.addEventListener("focusin", (e) => { const r = e.target.closest(".reveal"); if (r) r.classList.add("is-in"); });
  }
  }

  onScroll();

  /* ---------- Footer year ---------- */
  const year = $("[data-year]");
  if (year) year.textContent = String(new Date().getFullYear());
})();
