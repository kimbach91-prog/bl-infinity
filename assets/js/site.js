(() => {
  const documentLanguage = (document.documentElement.lang || "vi").toLowerCase();
  const isVietnamese = documentLanguage.startsWith("vi");
  const isEnglish = !isVietnamese;

  for (const link of document.querySelectorAll('a[href^="#"]')) {
    link.addEventListener("click", () => {
      history.replaceState(null, "", link.getAttribute("href"));
    });
  }

  const scriptSource =
    document.currentScript?.src ||
    [...document.scripts].find((script) => /\/assets\/js\/site\.js(?:\?|$)/.test(script.src))?.src;
  const siteRoot = scriptSource ? new URL("../../", scriptSource) : new URL("./", location.href);

  const setupNovelReader = () => {
    const prose = document.querySelector("article.prose");
    if (!prose) return;

    document.body.classList.add("bl-novel-reader");
    if (!document.getElementById("bl-novel-reader-style")) {
      const style = document.createElement("style");
      style.id = "bl-novel-reader-style";
      style.textContent = `
:root{--reader-font-size:18px;--reader-line-height:1.78;--reader-measure:62ch;--reader-bg:#fffdf8;--reader-surface:rgba(255,253,248,.95);--reader-ink:#211f1b;--reader-muted:#756f65;--reader-line:#e2dbce;--reader-accent:#6b3fa0;--reader-shadow:0 10px 32px rgba(31,25,20,.14)}
body.bl-novel-reader{background:var(--reader-bg)!important;color:var(--reader-ink)!important;padding-bottom:calc(72px + env(safe-area-inset-bottom));transition:background .18s ease,color .18s ease}body.bl-novel-reader[data-reader-theme="sepia"]{--reader-bg:#f5ecd9;--reader-surface:rgba(245,236,217,.95);--reader-ink:#302a21;--reader-muted:#766a58;--reader-line:#d9cbb1;--reader-accent:#744d2d}body.bl-novel-reader[data-reader-theme="night"]{--reader-bg:#111214;--reader-surface:rgba(23,24,27,.96);--reader-ink:#e9e4db;--reader-muted:#aaa49b;--reader-line:#32343a;--reader-accent:#c6a5ff;--reader-shadow:0 10px 34px rgba(0,0,0,.4)}
body.bl-novel-reader main{width:min(100%,calc(var(--reader-measure) + 44px))!important;max-width:none!important;padding-left:22px!important;padding-right:22px!important}body.bl-novel-reader .hero{max-width:var(--reader-measure);margin-inline:auto}body.bl-novel-reader .hero h1{max-width:14ch!important;text-wrap:balance}body.bl-novel-reader .prose{width:100%;max-width:var(--reader-measure)!important;margin-inline:auto;font-family:var(--reader-font-family,"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif);font-kerning:normal}body.bl-novel-reader .prose p,body.bl-novel-reader .prose li{max-width:none!important;font-size:var(--reader-font-size)!important;line-height:var(--reader-line-height)!important;color:var(--reader-ink);text-wrap:pretty}body.bl-novel-reader .prose p,body.bl-novel-reader .prose p+p{margin:.88em 0!important}body.bl-novel-reader .prose h2,body.bl-novel-reader .prose h3{color:var(--reader-ink);border-color:var(--reader-line)!important;text-wrap:balance}body.bl-novel-reader .prose hr{width:5.5rem;margin:2.55em auto!important;border:0!important;height:1px;background:linear-gradient(90deg,transparent,var(--reader-line),transparent)}body.bl-novel-reader .prose .aura-beat{max-width:34ch!important;margin:1.65em 0!important;padding:.12em 0 .12em 1rem;border-left:2px solid var(--reader-accent);font-size:calc(var(--reader-font-size)*1.08)!important;line-height:1.55!important;font-weight:720;letter-spacing:-.012em;color:var(--reader-ink)}
.reader-progress-track{position:fixed;z-index:1200;top:0;left:0;right:0;height:3px;pointer-events:none}.reader-progress-bar{height:100%;width:0;background:var(--reader-accent)}.reader-dock{position:fixed;z-index:1190;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));display:flex;align-items:center;gap:6px;padding:6px;border:1px solid var(--reader-line);border-radius:999px;background:var(--reader-surface);box-shadow:var(--reader-shadow);backdrop-filter:blur(16px)}.reader-dock button{min-width:42px;min-height:42px;padding:0 11px;border:0;border-radius:999px;background:transparent;color:var(--reader-ink);font:700 .9rem/1 system-ui,-apple-system,sans-serif}.reader-percent{min-width:40px;text-align:center;color:var(--reader-muted);font:650 .76rem/1 system-ui,-apple-system,sans-serif;font-variant-numeric:tabular-nums}.reader-panel{position:fixed;z-index:1185;right:12px;bottom:calc(70px + env(safe-area-inset-bottom));width:min(330px,calc(100vw - 24px));padding:14px;border:1px solid var(--reader-line);border-radius:18px;background:var(--reader-surface);color:var(--reader-ink);box-shadow:var(--reader-shadow);backdrop-filter:blur(18px)}.reader-panel[hidden]{display:none!important}.reader-panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;font:750 .9rem/1.25 system-ui,-apple-system,sans-serif}.reader-panel-close{width:36px;height:36px;border:0;border-radius:50%;background:transparent;color:var(--reader-ink);font-size:1.1rem}.reader-setting-row{display:grid;grid-template-columns:90px 1fr;gap:10px;align-items:center;padding:9px 0;border-top:1px solid var(--reader-line);font:600 .82rem/1.25 system-ui,-apple-system,sans-serif}.reader-controls{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}.reader-controls button{min-height:38px;padding:0 11px;border:1px solid var(--reader-line);border-radius:10px;background:var(--reader-bg);color:var(--reader-ink);font:650 .8rem/1 system-ui,-apple-system,sans-serif}.reader-controls button[aria-pressed="true"]{border-color:var(--reader-accent);box-shadow:inset 0 0 0 1px var(--reader-accent)}.reader-notes{margin-top:3.3em;border-top:1px solid var(--reader-line);color:var(--reader-muted)}.reader-notes summary{cursor:pointer;padding:16px 0;font:700 .9rem/1.4 system-ui,-apple-system,sans-serif}.reader-notes-body p,.reader-notes-body li{font-family:system-ui,-apple-system,sans-serif!important;font-size:15px!important;line-height:1.65!important;color:var(--reader-muted)!important}body.reader-focus .top,body.reader-focus .topic-bar,body.reader-focus .hero .eyebrow,body.reader-focus .hero .meta,body.reader-focus .hero .canon-note{display:none!important}body.reader-focus .hero{padding-top:28px!important}
@media(max-width:720px){:root{--reader-font-size:18px;--reader-line-height:1.76;--reader-measure:100%}body.bl-novel-reader main{width:100%!important;padding-left:18px!important;padding-right:18px!important}body.bl-novel-reader .hero{padding:28px 0 22px!important}body.bl-novel-reader .hero h1{font-size:clamp(2.25rem,12.2vw,3.65rem)!important;line-height:.98!important}body.bl-novel-reader .prose{padding-top:20px!important}.reader-dock{right:10px;bottom:calc(10px + env(safe-area-inset-bottom))}.reader-panel{right:10px;bottom:calc(68px + env(safe-area-inset-bottom));width:calc(100vw - 20px)}}
@media(prefers-reduced-motion:reduce){body.bl-novel-reader{transition:none!important}}
`;
      document.head.append(style);
    }

    const storageKey = "bl-novel-reader-v1";
    const defaults = { theme: "paper", font: "literary", size: 18, lineHeight: 1.78, focus: false };
    let prefs = { ...defaults };
    try { prefs = { ...defaults, ...JSON.parse(localStorage.getItem(storageKey) || "{}") }; } catch (_) {}
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const save = () => { try { localStorage.setItem(storageKey, JSON.stringify(prefs)); } catch (_) {} };
    const apply = () => {
      prefs.size = clamp(Number(prefs.size) || 18, 16, 23);
      prefs.lineHeight = clamp(Number(prefs.lineHeight) || 1.78, 1.62, 2.02);
      if (!["paper", "sepia", "night"].includes(prefs.theme)) prefs.theme = "paper";
      if (!["literary", "system"].includes(prefs.font)) prefs.font = "literary";
      document.body.dataset.readerTheme = prefs.theme;
      document.body.classList.toggle("reader-focus", Boolean(prefs.focus));
      document.documentElement.style.setProperty("--reader-font-size", `${prefs.size}px`);
      document.documentElement.style.setProperty("--reader-line-height", String(prefs.lineHeight));
      document.documentElement.style.setProperty("--reader-font-family", prefs.font === "system" ? 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif' : '"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif');
    };
    apply();

    const progressTrack = document.createElement("div");
    progressTrack.className = "reader-progress-track";
    progressTrack.setAttribute("aria-hidden", "true");
    const progressBar = document.createElement("div");
    progressBar.className = "reader-progress-bar";
    progressTrack.append(progressBar);
    document.body.append(progressTrack);

    const dock = document.createElement("div");
    dock.className = "reader-dock";
    dock.setAttribute("aria-label", isEnglish ? "Reader controls" : "Điều khiển đọc truyện");
    const percent = document.createElement("span"); percent.className = "reader-percent"; percent.textContent = "0%";
    const settingsButton = document.createElement("button"); settingsButton.type = "button"; settingsButton.textContent = "Aa"; settingsButton.setAttribute("aria-label", isEnglish ? "Reading preferences" : "Tuỳ chỉnh đọc"); settingsButton.setAttribute("aria-expanded", "false");
    const themeButton = document.createElement("button"); themeButton.type = "button"; themeButton.textContent = "◐"; themeButton.setAttribute("aria-label", isEnglish ? "Cycle reading theme" : "Đổi nền đọc");
    const focusButton = document.createElement("button"); focusButton.type = "button"; focusButton.textContent = "▣"; focusButton.setAttribute("aria-label", isEnglish ? "Focus reading mode" : "Chế độ đọc tập trung"); focusButton.setAttribute("aria-pressed", String(Boolean(prefs.focus)));
    dock.append(percent, settingsButton, themeButton, focusButton); document.body.append(dock);

    const panel = document.createElement("section");
    panel.className = "reader-panel"; panel.hidden = true; panel.setAttribute("aria-label", isEnglish ? "Reading preferences" : "Tuỳ chỉnh đọc");
    panel.innerHTML = `<div class="reader-panel-head"><span>${isEnglish ? "Reading" : "Chế độ đọc"}</span><button type="button" class="reader-panel-close" aria-label="${isEnglish ? "Close" : "Đóng"}">×</button></div><div class="reader-setting-row"><span>${isEnglish ? "Text size" : "Cỡ chữ"}</span><div class="reader-controls"><button type="button" data-reader-action="smaller">A−</button><button type="button" data-reader-action="larger">A+</button></div></div><div class="reader-setting-row"><span>${isEnglish ? "Typeface" : "Kiểu chữ"}</span><div class="reader-controls"><button type="button" data-reader-font="literary">${isEnglish ? "Serif" : "Văn học"}</button><button type="button" data-reader-font="system">Sans</button></div></div><div class="reader-setting-row"><span>${isEnglish ? "Leading" : "Giãn dòng"}</span><div class="reader-controls"><button type="button" data-reader-leading="1.68">${isEnglish ? "Tight" : "Gọn"}</button><button type="button" data-reader-leading="1.78">${isEnglish ? "Normal" : "Chuẩn"}</button><button type="button" data-reader-leading="1.92">${isEnglish ? "Airy" : "Thoáng"}</button></div></div><div class="reader-setting-row"><span>${isEnglish ? "Theme" : "Nền"}</span><div class="reader-controls"><button type="button" data-reader-theme="paper">${isEnglish ? "Paper" : "Giấy"}</button><button type="button" data-reader-theme="sepia">Sepia</button><button type="button" data-reader-theme="night">${isEnglish ? "Night" : "Đêm"}</button></div></div>`;
    document.body.append(panel);

    const refreshPressedStates = () => {
      panel.querySelectorAll("[data-reader-font]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.readerFont === prefs.font)));
      panel.querySelectorAll("[data-reader-theme]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.readerTheme === prefs.theme)));
      panel.querySelectorAll("[data-reader-leading]").forEach((b) => b.setAttribute("aria-pressed", String(Math.abs(Number(b.dataset.readerLeading) - Number(prefs.lineHeight)) < .03)));
      focusButton.setAttribute("aria-pressed", String(Boolean(prefs.focus)));
    };
    refreshPressedStates();
    const setPanelOpen = (open) => { panel.hidden = !open; settingsButton.setAttribute("aria-expanded", String(open)); if (open) panel.querySelector(".reader-panel-close")?.focus(); };
    settingsButton.addEventListener("click", () => setPanelOpen(panel.hidden));
    panel.querySelector(".reader-panel-close")?.addEventListener("click", () => { setPanelOpen(false); settingsButton.focus(); });
    panel.addEventListener("click", (event) => {
      const button = event.target.closest("button"); if (!button) return;
      if (button.dataset.readerAction === "smaller") prefs.size -= 1;
      if (button.dataset.readerAction === "larger") prefs.size += 1;
      if (button.dataset.readerFont) prefs.font = button.dataset.readerFont;
      if (button.dataset.readerLeading) prefs.lineHeight = Number(button.dataset.readerLeading);
      if (button.dataset.readerTheme) prefs.theme = button.dataset.readerTheme;
      apply(); save(); refreshPressedStates();
    });
    const themes = ["paper", "sepia", "night"];
    themeButton.addEventListener("click", () => { prefs.theme = themes[(themes.indexOf(prefs.theme) + 1) % themes.length]; apply(); save(); refreshPressedStates(); });
    focusButton.addEventListener("click", () => { prefs.focus = !prefs.focus; apply(); save(); refreshPressedStates(); });
    document.addEventListener("click", (event) => { if (!panel.hidden && !panel.contains(event.target) && !settingsButton.contains(event.target)) setPanelOpen(false); });

    const updateProgress = () => {
      const rect = prose.getBoundingClientRect(); const start = window.scrollY + rect.top; const end = start + prose.offsetHeight - window.innerHeight;
      const ratio = end <= start ? 1 : clamp((window.scrollY - start) / (end - start), 0, 1);
      progressBar.style.width = `${(ratio * 100).toFixed(2)}%`; percent.textContent = `${Math.round(ratio * 100)}%`;
    };
    updateProgress(); window.addEventListener("scroll", updateProgress, { passive: true }); window.addEventListener("resize", updateProgress, { passive: true });

    const notesHeading = [...prose.querySelectorAll("h2,h3")].find((heading) => /Ghi chú Reality\s*\/\s*Provenance/i.test(heading.textContent || ""));
    if (notesHeading && !notesHeading.closest("details")) {
      const details = document.createElement("details"); details.className = "reader-notes";
      const summary = document.createElement("summary"); summary.textContent = notesHeading.textContent.trim();
      const body = document.createElement("div"); body.className = "reader-notes-body";
      let node = notesHeading.nextSibling; while (node) { const next = node.nextSibling; body.append(node); node = next; }
      notesHeading.replaceWith(details); details.append(summary, body);
    }

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!panel.hidden) { setPanelOpen(false); settingsButton.focus(); }
      else if (prefs.focus) { prefs.focus = false; apply(); save(); refreshPressedStates(); }
    });
  };

  setupNovelReader();

  const header = document.querySelector(".top");
  const nav = header?.querySelector("nav");
  if (!header || !nav) return;
  const academicDemocracyUrl = new URL("academic-democracy.html", siteRoot);
  const normalizePath = (value) => { const url = new URL(value, location.href); let path = url.pathname.replace(/\/index\.html$/, "/"); if (path.length > 1) path = path.replace(/\/$/, ""); return path; };
  const hasAcademicDemocracyLink = [...nav.querySelectorAll("a[href]")].some((link) => normalizePath(link.href) === normalizePath(academicDemocracyUrl.href));
  const theoryLink = [...nav.querySelectorAll("a[href]")].find((link) => /\/theory\.html$/.test(new URL(link.href, location.href).pathname));
  if (!hasAcademicDemocracyLink && theoryLink) { const link = document.createElement("a"); link.href = academicDemocracyUrl.href; link.textContent = isEnglish ? "Academic Democracy" : "Dân chủ Học thuật"; theoryLink.insertAdjacentElement("afterend", link); }
  const currentPath = normalizePath(location.href);
  for (const link of nav.querySelectorAll("a[href]")) { if (normalizePath(link.href) === currentPath) link.setAttribute("aria-current", "page"); else if (link.getAttribute("aria-current") !== "location") link.removeAttribute("aria-current"); }
  const languageSwitch = nav.querySelector(".lang-switch");
  if (languageSwitch) { languageSwitch.classList.add("header-lang-switch"); languageSwitch.classList.remove("lang-switch"); languageSwitch.setAttribute("aria-label", isEnglish ? "Đọc bằng tiếng Việt" : "Read in English"); languageSwitch.title = isEnglish ? "Đọc bằng tiếng Việt" : "Read in English"; nav.insertAdjacentElement("afterend", languageSwitch); }
  if (!nav.id) nav.id = "site-navigation";
  const toggle = document.createElement("button"); toggle.type = "button"; toggle.className = "nav-toggle"; toggle.setAttribute("aria-controls", nav.id); toggle.setAttribute("aria-expanded", "false"); toggle.textContent = isEnglish ? "Menu" : "Mục lục"; toggle.setAttribute("aria-label", isEnglish ? "Open site navigation" : "Mở điều hướng trang"); header.insertBefore(toggle, nav); header.classList.add("nav-ready");
  const languageMenu = header.querySelector(".language-menu");
  const setNavigationOpen = (open) => { nav.classList.toggle("is-open", open); toggle.setAttribute("aria-expanded", String(open)); toggle.textContent = open ? (isEnglish ? "Close" : "Đóng") : isEnglish ? "Menu" : "Mục lục"; };
  toggle.addEventListener("click", () => { if (languageMenu?.open) languageMenu.open = false; setNavigationOpen(!nav.classList.contains("is-open")); });
  nav.addEventListener("click", (event) => { if (event.target.closest("a")) setNavigationOpen(false); });
  languageMenu?.addEventListener("toggle", () => { if (languageMenu.open) setNavigationOpen(false); });
  document.addEventListener("click", (event) => { if (languageMenu?.open && !languageMenu.contains(event.target)) languageMenu.open = false; });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") { const navWasOpen = nav.classList.contains("is-open"); const languageWasOpen = Boolean(languageMenu?.open); if (navWasOpen) setNavigationOpen(false); if (languageMenu?.open) languageMenu.open = false; if (languageWasOpen) languageMenu?.querySelector("summary")?.focus(); else if (navWasOpen) toggle.focus(); } });
  const mobileQuery = matchMedia("(max-width: 900px)"); mobileQuery.addEventListener?.("change", (event) => { if (!event.matches) setNavigationOpen(false); });

  const tableLabel = isEnglish ? "Data table; scroll horizontally for more columns" : "Bảng dữ liệu; vuốt ngang để xem thêm cột";
  for (const table of document.querySelectorAll("article table")) {
    if (table.parentElement?.classList.contains("table-scroll")) continue;
    const wrapper = document.createElement("div"); wrapper.className = table.classList.contains("shift-table") ? "table-scroll table-scroll--stacked" : "table-scroll"; table.insertAdjacentElement("beforebegin", wrapper); wrapper.append(table);
    const updateTableAccessibility = () => { const scrollable = wrapper.scrollWidth > wrapper.clientWidth + 1; if (scrollable) { wrapper.tabIndex = 0; wrapper.setAttribute("role", "region"); wrapper.setAttribute("aria-label", tableLabel); } else { wrapper.removeAttribute("tabindex"); wrapper.removeAttribute("role"); wrapper.removeAttribute("aria-label"); } };
    requestAnimationFrame(updateTableAccessibility); window.addEventListener("resize", updateTableAccessibility, { passive: true });
  }
})();
