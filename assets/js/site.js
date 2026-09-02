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
    [...document.scripts].find((script) => /\/assets\/js\/site\.js(?:\?|$)/.test(script.src))
      ?.src;
  const siteRoot = scriptSource ? new URL("../../", scriptSource) : new URL("./", location.href);

  const setupNovelReader = () => {
    const prose = document.querySelector("article.prose");
    if (!prose) return;

    document.body.classList.add("bl-novel-reader");
    const cssUrl = new URL("assets/css/novel-reader.css", siteRoot).href;
    if (![...document.styleSheets].some((sheet) => sheet.href === cssUrl)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = cssUrl;
      document.head.append(link);
    }

    const storageKey = "bl-novel-reader-v1";
    const defaults = {
      theme: "paper",
      font: "literary",
      size: 18,
      lineHeight: 1.78,
      focus: false,
    };
    let prefs = { ...defaults };
    try {
      prefs = { ...defaults, ...JSON.parse(localStorage.getItem(storageKey) || "{}") };
    } catch (_) {
      prefs = { ...defaults };
    }

    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const save = () => {
      try { localStorage.setItem(storageKey, JSON.stringify(prefs)); } catch (_) {}
    };
    const apply = () => {
      prefs.size = clamp(Number(prefs.size) || defaults.size, 16, 23);
      prefs.lineHeight = clamp(Number(prefs.lineHeight) || defaults.lineHeight, 1.62, 2.02);
      if (!["paper", "sepia", "night"].includes(prefs.theme)) prefs.theme = "paper";
      if (!["literary", "system"].includes(prefs.font)) prefs.font = "literary";
      document.body.dataset.readerTheme = prefs.theme;
      document.body.classList.toggle("reader-focus", Boolean(prefs.focus));
      document.documentElement.style.setProperty("--reader-font-size", `${prefs.size}px`);
      document.documentElement.style.setProperty("--reader-line-height", String(prefs.lineHeight));
      document.documentElement.style.setProperty(
        "--reader-font-family",
        prefs.font === "system"
          ? 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
          : '"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif',
      );
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
    const percent = document.createElement("span");
    percent.className = "reader-percent";
    percent.textContent = "0%";

    const settingsButton = document.createElement("button");
    settingsButton.type = "button";
    settingsButton.textContent = "Aa";
    settingsButton.setAttribute("aria-label", isEnglish ? "Reading preferences" : "Tuỳ chỉnh đọc");
    settingsButton.setAttribute("aria-expanded", "false");

    const themeButton = document.createElement("button");
    themeButton.type = "button";
    themeButton.textContent = "◐";
    themeButton.setAttribute("aria-label", isEnglish ? "Cycle reading theme" : "Đổi nền đọc");

    const focusButton = document.createElement("button");
    focusButton.type = "button";
    focusButton.textContent = "▣";
    focusButton.setAttribute("aria-label", isEnglish ? "Focus reading mode" : "Chế độ đọc tập trung");
    focusButton.setAttribute("aria-pressed", String(Boolean(prefs.focus)));

    dock.append(percent, settingsButton, themeButton, focusButton);
    document.body.append(dock);

    const panel = document.createElement("section");
    panel.className = "reader-panel";
    panel.hidden = true;
    panel.setAttribute("aria-label", isEnglish ? "Reading preferences" : "Tuỳ chỉnh đọc");
    panel.innerHTML = `
      <div class="reader-panel-head">
        <span>${isEnglish ? "Reading" : "Chế độ đọc"}</span>
        <button type="button" class="reader-panel-close" aria-label="${isEnglish ? "Close" : "Đóng"}">×</button>
      </div>
      <div class="reader-setting-row">
        <span>${isEnglish ? "Text size" : "Cỡ chữ"}</span>
        <div class="reader-controls">
          <button type="button" data-reader-action="smaller" aria-label="${isEnglish ? "Smaller text" : "Giảm cỡ chữ"}">A−</button>
          <button type="button" data-reader-action="larger" aria-label="${isEnglish ? "Larger text" : "Tăng cỡ chữ"}">A+</button>
        </div>
      </div>
      <div class="reader-setting-row">
        <span>${isEnglish ? "Typeface" : "Kiểu chữ"}</span>
        <div class="reader-controls">
          <button type="button" data-reader-font="literary">${isEnglish ? "Serif" : "Văn học"}</button>
          <button type="button" data-reader-font="system">Sans</button>
        </div>
      </div>
      <div class="reader-setting-row">
        <span>${isEnglish ? "Leading" : "Giãn dòng"}</span>
        <div class="reader-controls">
          <button type="button" data-reader-leading="1.68">${isEnglish ? "Tight" : "Gọn"}</button>
          <button type="button" data-reader-leading="1.78">${isEnglish ? "Normal" : "Chuẩn"}</button>
          <button type="button" data-reader-leading="1.92">${isEnglish ? "Airy" : "Thoáng"}</button>
        </div>
      </div>
      <div class="reader-setting-row">
        <span>${isEnglish ? "Theme" : "Nền"}</span>
        <div class="reader-controls">
          <button type="button" data-reader-theme="paper">${isEnglish ? "Paper" : "Giấy"}</button>
          <button type="button" data-reader-theme="sepia">Sepia</button>
          <button type="button" data-reader-theme="night">${isEnglish ? "Night" : "Đêm"}</button>
        </div>
      </div>`;
    document.body.append(panel);

    const refreshPressedStates = () => {
      for (const button of panel.querySelectorAll("[data-reader-font]")) {
        button.setAttribute("aria-pressed", String(button.dataset.readerFont === prefs.font));
      }
      for (const button of panel.querySelectorAll("[data-reader-theme]")) {
        button.setAttribute("aria-pressed", String(button.dataset.readerTheme === prefs.theme));
      }
      for (const button of panel.querySelectorAll("[data-reader-leading]")) {
        button.setAttribute(
          "aria-pressed",
          String(Math.abs(Number(button.dataset.readerLeading) - Number(prefs.lineHeight)) < 0.03),
        );
      }
      focusButton.setAttribute("aria-pressed", String(Boolean(prefs.focus)));
    };
    refreshPressedStates();

    const setPanelOpen = (open) => {
      panel.hidden = !open;
      settingsButton.setAttribute("aria-expanded", String(open));
      if (open) panel.querySelector(".reader-panel-close")?.focus();
    };
    settingsButton.addEventListener("click", () => setPanelOpen(panel.hidden));
    panel.querySelector(".reader-panel-close")?.addEventListener("click", () => {
      setPanelOpen(false);
      settingsButton.focus();
    });

    panel.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      if (button.dataset.readerAction === "smaller") prefs.size -= 1;
      if (button.dataset.readerAction === "larger") prefs.size += 1;
      if (button.dataset.readerFont) prefs.font = button.dataset.readerFont;
      if (button.dataset.readerLeading) prefs.lineHeight = Number(button.dataset.readerLeading);
      if (button.dataset.readerTheme) prefs.theme = button.dataset.readerTheme;
      apply();
      save();
      refreshPressedStates();
    });

    const themes = ["paper", "sepia", "night"];
    themeButton.addEventListener("click", () => {
      prefs.theme = themes[(themes.indexOf(prefs.theme) + 1) % themes.length];
      apply(); save(); refreshPressedStates();
    });
    focusButton.addEventListener("click", () => {
      prefs.focus = !prefs.focus;
      apply(); save(); refreshPressedStates();
    });

    document.addEventListener("click", (event) => {
      if (!panel.hidden && !panel.contains(event.target) && !settingsButton.contains(event.target)) {
        setPanelOpen(false);
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!panel.hidden) {
        setPanelOpen(false);
        settingsButton.focus();
      } else if (prefs.focus) {
        prefs.focus = false;
        apply(); save(); refreshPressedStates();
      }
    });

    const updateProgress = () => {
      const rect = prose.getBoundingClientRect();
      const start = window.scrollY + rect.top;
      const end = start + prose.offsetHeight - window.innerHeight;
      const ratio = end <= start ? 1 : clamp((window.scrollY - start) / (end - start), 0, 1);
      progressBar.style.width = `${(ratio * 100).toFixed(2)}%`;
      percent.textContent = `${Math.round(ratio * 100)}%`;
    };
    updateProgress();
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress, { passive: true });

    const notesHeading = [...prose.querySelectorAll("h2,h3")].find((heading) =>
      /Ghi chú Reality\s*\/\s*Provenance/i.test(heading.textContent || ""),
    );
    if (notesHeading && !notesHeading.closest("details")) {
      const details = document.createElement("details");
      details.className = "reader-notes";
      const summary = document.createElement("summary");
      summary.textContent = notesHeading.textContent.trim();
      const body = document.createElement("div");
      body.className = "reader-notes-body";
      let node = notesHeading.nextSibling;
      while (node) {
        const next = node.nextSibling;
        body.append(node);
        node = next;
      }
      notesHeading.replaceWith(details);
      details.append(summary, body);
    }
  };

  setupNovelReader();

  const header = document.querySelector(".top");
  const nav = header?.querySelector("nav");
  if (!header || !nav) return;

  const academicDemocracyUrl = new URL("academic-democracy.html", siteRoot);

  const normalizePath = (value) => {
    const url = new URL(value, location.href);
    let path = url.pathname.replace(/\/index\.html$/, "/");
    if (path.length > 1) path = path.replace(/\/$/, "");
    return path;
  };

  const hasAcademicDemocracyLink = [...nav.querySelectorAll("a[href]")].some(
    (link) => normalizePath(link.href) === normalizePath(academicDemocracyUrl.href),
  );
  const theoryLink = [...nav.querySelectorAll("a[href]")].find((link) =>
    /\/theory\.html$/.test(new URL(link.href, location.href).pathname),
  );

  if (!hasAcademicDemocracyLink && theoryLink) {
    const link = document.createElement("a");
    link.href = academicDemocracyUrl.href;
    link.textContent = isEnglish ? "Academic Democracy" : "Dân chủ Học thuật";
    theoryLink.insertAdjacentElement("afterend", link);
  }

  const currentPath = normalizePath(location.href);
  for (const link of nav.querySelectorAll("a[href]")) {
    if (normalizePath(link.href) === currentPath) {
      link.setAttribute("aria-current", "page");
    } else if (link.getAttribute("aria-current") === "location") {
      // Build-time section state for claim/asset/discovery detail routes.
    } else {
      link.removeAttribute("aria-current");
    }
  }

  const languageSwitch = nav.querySelector(".lang-switch");
  if (languageSwitch) {
    languageSwitch.classList.add("header-lang-switch");
    languageSwitch.classList.remove("lang-switch");
    languageSwitch.setAttribute(
      "aria-label",
      isEnglish ? "Đọc bằng tiếng Việt" : "Read in English",
    );
    languageSwitch.title = isEnglish ? "Đọc bằng tiếng Việt" : "Read in English";
    nav.insertAdjacentElement("afterend", languageSwitch);
  }

  if (!nav.id) nav.id = "site-navigation";
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "nav-toggle";
  toggle.setAttribute("aria-controls", nav.id);
  toggle.setAttribute("aria-expanded", "false");
  toggle.textContent = isEnglish ? "Menu" : "Mục lục";
  toggle.setAttribute(
    "aria-label",
    isEnglish ? "Open site navigation" : "Mở điều hướng trang",
  );
  header.insertBefore(toggle, nav);
  header.classList.add("nav-ready");
  const languageMenu = header.querySelector(".language-menu");

  const setNavigationOpen = (open) => {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? (isEnglish ? "Close" : "Đóng") : isEnglish ? "Menu" : "Mục lục";
    toggle.setAttribute(
      "aria-label",
      open
        ? isEnglish
          ? "Close site navigation"
          : "Đóng điều hướng trang"
        : isEnglish
          ? "Open site navigation"
          : "Mở điều hướng trang",
    );
  };

  toggle.addEventListener("click", () => {
    if (languageMenu?.open) languageMenu.open = false;
    setNavigationOpen(!nav.classList.contains("is-open"));
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) setNavigationOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const navWasOpen = nav.classList.contains("is-open");
      const languageWasOpen = Boolean(languageMenu?.open);
      if (!navWasOpen && !languageWasOpen) return;
      if (navWasOpen) setNavigationOpen(false);
      if (languageMenu?.open) languageMenu.open = false;
      if (languageWasOpen) {
        languageMenu?.querySelector("summary")?.focus();
      } else {
        toggle.focus();
      }
    }
  });

  languageMenu?.addEventListener("toggle", () => {
    if (languageMenu.open) setNavigationOpen(false);
  });
  document.addEventListener("click", (event) => {
    if (languageMenu?.open && !languageMenu.contains(event.target)) {
      languageMenu.open = false;
    }
  });

  const mobileQuery = matchMedia("(max-width: 900px)");
  const closeWhenDesktop = (event) => {
    if (!event.matches) setNavigationOpen(false);
  };
  mobileQuery.addEventListener?.("change", closeWhenDesktop);

  const tableLabel = isEnglish
    ? "Data table; scroll horizontally for more columns"
    : "Bảng dữ liệu; vuốt ngang để xem thêm cột";
  for (const table of document.querySelectorAll("article table")) {
    if (table.parentElement?.classList.contains("table-scroll")) continue;
    const wrapper = document.createElement("div");
    wrapper.className = table.classList.contains("shift-table")
      ? "table-scroll table-scroll--stacked"
      : "table-scroll";
    table.insertAdjacentElement("beforebegin", wrapper);
    wrapper.append(table);

    const updateTableAccessibility = () => {
      const scrollable = wrapper.scrollWidth > wrapper.clientWidth + 1;
      if (scrollable) {
        wrapper.tabIndex = 0;
        wrapper.setAttribute("role", "region");
        wrapper.setAttribute("aria-label", tableLabel);
      } else {
        wrapper.removeAttribute("tabindex");
        wrapper.removeAttribute("role");
        wrapper.removeAttribute("aria-label");
      }
    };
    requestAnimationFrame(updateTableAccessibility);
    window.addEventListener("resize", updateTableAccessibility, { passive: true });
  }
})();
