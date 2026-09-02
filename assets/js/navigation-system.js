(() => {
  const scriptSource = document.currentScript?.src || [...document.scripts].find((s) => /navigation-system\.js(?:\?|$)/.test(s.src))?.src;
  if (!scriptSource) return;

  const siteRoot = new URL("../../", scriptSource);
  const header = document.querySelector(".top");
  if (!header) return;

  const UI = {
    vi:{index:"Chỉ mục khoa học",close:"Đóng",search:"Tìm học thuyết, claim, asset, chương...",kicker:"BL∞ SCIENTIFIC INDEX",title:"Chỉ mục khoa học toàn hệ",recommended:"Ưu tiên theo ngôn ngữ trình duyệt",detected:"Ngôn ngữ phù hợp đã được đưa lên đầu",open:"Mở bản này",results:"mục",unavailable:"Chỉ mục khoa học tạm thời không khả dụng.",groups:{core:"Lõi nghiên cứu",theory:"Chương học thuyết",narrative:"Tiểu thuyết / HALF-CANON",claims:"Claim Registry",assets:"Asset Registry",verification:"Kiểm chứng & quản trị",machine:"Machine layer",languages:"Ngôn ngữ"}},
    en:{index:"Scientific index",close:"Close",search:"Search theories, claims, assets, chapters...",kicker:"BL∞ SCIENTIFIC INDEX",title:"Complete scientific index",recommended:"Browser language priority",detected:"A matching language edition is prioritized",open:"Open edition",results:"items",unavailable:"Scientific index is temporarily unavailable.",groups:{core:"Core research",theory:"Theory chapters",narrative:"Novel / HALF-CANON",claims:"Claim Registry",assets:"Asset Registry",verification:"Verification & governance",machine:"Machine layer",languages:"Languages"}},
    es:{index:"Índice científico",close:"Cerrar",search:"Buscar teorías, claims, assets, capítulos...",kicker:"BL∞ ÍNDICE CIENTÍFICO",title:"Índice científico completo",recommended:"Prioridad por idioma del navegador",detected:"Se prioriza una edición compatible",open:"Abrir edición",results:"elementos",unavailable:"El índice científico no está disponible temporalmente."},
    fr:{index:"Index scientifique",close:"Fermer",search:"Rechercher théories, claims, assets, chapitres...",kicker:"BL∞ INDEX SCIENTIFIQUE",title:"Index scientifique complet",recommended:"Priorité à la langue du navigateur",detected:"Une édition correspondante est prioritaire",open:"Ouvrir",results:"éléments",unavailable:"L’index scientifique est temporairement indisponible."},
    de:{index:"Wissenschaftsindex",close:"Schließen",search:"Theorien, Claims, Assets, Kapitel suchen...",kicker:"BL∞ WISSENSCHAFTSINDEX",title:"Vollständiger Wissenschaftsindex",recommended:"Browser-Sprache priorisiert",detected:"Eine passende Sprachfassung wird zuerst gezeigt",open:"Öffnen",results:"Einträge",unavailable:"Der Wissenschaftsindex ist vorübergehend nicht verfügbar."},
    pt:{index:"Índice científico",close:"Fechar",search:"Buscar teorias, claims, assets, capítulos...",kicker:"BL∞ ÍNDICE CIENTÍFICO",title:"Índice científico completo",recommended:"Prioridade pelo idioma do navegador",detected:"Uma edição compatível foi priorizada",open:"Abrir",results:"itens",unavailable:"O índice científico está temporariamente indisponível."},
    zh:{index:"科学索引",close:"关闭",search:"搜索理论、主张、资产、章节...",kicker:"BL∞ 科学索引",title:"完整科学索引",recommended:"优先浏览器语言",detected:"已优先显示匹配语言版本",open:"打开版本",results:"项",unavailable:"科学索引暂时不可用。"},
    ja:{index:"科学索引",close:"閉じる",search:"理論・主張・資産・章を検索...",kicker:"BL∞ 科学索引",title:"完全科学索引",recommended:"ブラウザ言語を優先",detected:"一致する言語版を優先表示",open:"開く",results:"件",unavailable:"科学索引は一時的に利用できません。"},
    ko:{index:"과학 색인",close:"닫기",search:"이론, 주장, 자산, 장 검색...",kicker:"BL∞ 과학 색인",title:"전체 과학 색인",recommended:"브라우저 언어 우선",detected:"일치하는 언어판을 우선 표시",open:"열기",results:"항목",unavailable:"과학 색인을 일시적으로 사용할 수 없습니다."},
    ru:{index:"Научный индекс",close:"Закрыть",search:"Поиск теорий, claims, assets, глав...",kicker:"BL∞ НАУЧНЫЙ ИНДЕКС",title:"Полный научный индекс",recommended:"Приоритет языка браузера",detected:"Подходящая языковая версия показана первой",open:"Открыть",results:"объектов",unavailable:"Научный индекс временно недоступен."},
    ar:{index:"الفهرس العلمي",close:"إغلاق",search:"ابحث في النظريات والادعاءات والأصول والفصول...",kicker:"BL∞ الفهرس العلمي",title:"الفهرس العلمي الكامل",recommended:"أولوية لغة المتصفح",detected:"تم تقديم النسخة اللغوية المطابقة",open:"فتح النسخة",results:"عنصر",unavailable:"الفهرس العلمي غير متاح مؤقتًا."},
    hi:{index:"वैज्ञानिक सूचकांक",close:"बंद करें",search:"सिद्धांत, दावे, assets, अध्याय खोजें...",kicker:"BL∞ वैज्ञानिक सूचकांक",title:"पूर्ण वैज्ञानिक सूचकांक",recommended:"ब्राउज़र भाषा प्राथमिकता",detected:"मिलती भाषा का संस्करण पहले दिखाया गया",open:"खोलें",results:"आइटम",unavailable:"वैज्ञानिक सूचकांक अस्थायी रूप से उपलब्ध नहीं है।"},
    id:{index:"Indeks ilmiah",close:"Tutup",search:"Cari teori, klaim, aset, bab...",kicker:"BL∞ INDEKS ILMIAH",title:"Indeks ilmiah lengkap",recommended:"Prioritas bahasa browser",detected:"Edisi bahasa yang cocok diprioritaskan",open:"Buka edisi",results:"item",unavailable:"Indeks ilmiah untuk sementara tidak tersedia."}
  };

  const normalizeLang = (value = "") => {
    const v = String(value).toLowerCase();
    if (v.startsWith("zh")) return "zh";
    return v.split("-")[0];
  };
  const fold = (value = "") => String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const currentLang = normalizeLang(document.documentElement.lang || "vi");
  const ui = UI[currentLang] || UI.en;

  const primaryNav = header.querySelector('nav[aria-label="Primary"], nav');
  const theoryPrimary = primaryNav?.querySelector('a[data-section="theory"]');
  const novelPrimary = primaryNav?.querySelector('a[data-section="novel"]');
  if (theoryPrimary && novelPrimary) theoryPrimary.insertAdjacentElement("afterend", novelPrimary);

  const topicBar = document.querySelector(".topic-bar");
  const topicInner = topicBar?.querySelector(".topic-bar-inner");
  const topicOrder = ["overview", "theory", "novel", "regressor", "system", "academic", "claims", "critique"];
  if (topicInner) {
    for (const key of topicOrder) {
      const link = topicInner.querySelector(`[data-topic="${key}"]`);
      if (link) topicInner.append(link);
    }
    const active = topicInner.querySelector('[aria-current="page"]');
    if (active) requestAnimationFrame(() => {
      const left = active.offsetLeft - (topicInner.clientWidth - active.offsetWidth) / 2;
      topicInner.scrollTo({left: Math.max(0, left), behavior: "instant"});
    });
  }

  const homeGrid = document.querySelector(".home-directory-grid");
  if (homeGrid) {
    const order = [
      "theory.html", "novel/", "regressor-proposition.html", "system.html",
      "academic-democracy.html", "open-academic-publishing.html", "unknown.html",
      "grand-ending.html", "world.html", "bl-adn.html", "claims.html", "assets.html",
      "provenance.html", "critique.html", "author.html", "languages.html", "machine.html",
      "academic-democracy-technology.html", "academic-democracy/discovery.html"
    ];
    const items = [...homeGrid.children];
    const routeOf = (item) => {
      const a = item.querySelector("a[href]");
      if (!a) return "";
      const u = new URL(a.href, location.href);
      let route = decodeURI(u.pathname).replace(siteRoot.pathname, "").replace(/^\//, "");
      if (route === "novel/index.html") route = "novel/";
      return route;
    };
    const rank = new Map(order.map((route, i) => [route, i]));
    items.sort((a, b) => (rank.get(routeOf(a)) ?? 999) - (rank.get(routeOf(b)) ?? 999));
    items.forEach((item) => homeGrid.append(item));
    for (const item of items.slice(0, 2)) item.classList.add("bl-reading-pair");
  }

  const updateStickyMetrics = () => {
    const headerH = Math.ceil(header.getBoundingClientRect().height);
    const topicH = Math.ceil(topicBar?.getBoundingClientRect().height || 0);
    document.documentElement.style.setProperty("--bl-header-h", `${headerH}px`);
    document.documentElement.style.setProperty("--bl-topic-h", `${topicH}px`);
  };
  updateStickyMetrics();
  if ("ResizeObserver" in window) {
    const ro = new ResizeObserver(updateStickyMetrics);
    ro.observe(header);
    if (topicBar) ro.observe(topicBar);
  } else {
    addEventListener("resize", updateStickyMetrics, {passive: true});
  }

  const safeStorageGet = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
  const safeStorageSet = (key, val) => { try { localStorage.setItem(key, val); } catch {} };
  const languageMenu = header.querySelector(".language-menu");
  const languageLinks = languageMenu ? [...languageMenu.querySelectorAll(".language-menu-panel a[hreflang]")] : [];
  languageLinks.forEach((link) => link.addEventListener("click", () => safeStorageSet("bl-preferred-language", normalizeLang(link.hreflang || link.lang))));

  const storedLang = normalizeLang(safeStorageGet("bl-preferred-language") || "");
  const browserLangs = (navigator.languages?.length ? navigator.languages : [navigator.language]).map(normalizeLang).filter(Boolean);
  const preferredLang = storedLang || browserLangs.find((lang) => languageLinks.some((link) => normalizeLang(link.hreflang || link.lang) === lang)) || currentLang;
  const preferredLink = languageLinks.find((link) => normalizeLang(link.hreflang || link.lang) === preferredLang);

  if (preferredLink && languageMenu) {
    const panel = languageMenu.querySelector(".language-menu-panel");
    if (panel && normalizeLang(preferredLink.hreflang || preferredLink.lang) !== currentLang) {
      const preferredUI = UI[preferredLang] || UI.en;
      const priorityTitle = document.createElement("p");
      priorityTitle.className = "language-priority-title";
      priorityTitle.textContent = preferredUI.recommended;
      preferredLink.classList.add("language-priority-link");
      panel.prepend(priorityTitle, preferredLink);

      const summary = languageMenu.querySelector("summary");
      if (summary) summary.title = preferredUI.detected;

      const relativePath = decodeURI(location.pathname).replace(siteRoot.pathname, "").replace(/^\//, "");
      const corePairs = new Map([
        ["", {vi:"index.html", en:"en/"}], ["index.html", {vi:"index.html", en:"en/"}], ["en/", {vi:"index.html", en:"en/"}],
        ["theory.html", {vi:"theory.html", en:"en/theory.html"}], ["en/theory.html", {vi:"theory.html", en:"en/theory.html"}],
        ["author.html", {vi:"author.html", en:"author/en/"}], ["author/en/", {vi:"author.html", en:"author/en/"}]
      ]);
      const pair = corePairs.get(relativePath);
      const canAutoRoute = pair && (preferredLang === "vi" || preferredLang === "en") && pair[preferredLang];
      const sessionKey = `bl-lang-routed:${relativePath}:${preferredLang}`;
      if (canAutoRoute && !sessionStorage.getItem(sessionKey)) {
        sessionStorage.setItem(sessionKey, "1");
        const target = new URL(pair[preferredLang], siteRoot).href;
        if (new URL(location.href).pathname !== new URL(target).pathname) {
          location.replace(target);
          return;
        }
      }

      const banner = document.createElement("div");
      banner.className = "language-priority-banner";
      const langName = preferredLink.querySelector("span")?.textContent?.trim() || preferredLink.textContent.trim();
      banner.innerHTML = `<span><strong>${preferredUI.recommended}:</strong> ${langName}. ${preferredUI.detected}.</span>`;
      const open = document.createElement("a");
      open.href = preferredLink.href;
      open.hreflang = preferredLink.hreflang;
      open.textContent = preferredUI.open;
      open.addEventListener("click", () => safeStorageSet("bl-preferred-language", preferredLang));
      banner.append(open);
      (topicBar || header).insertAdjacentElement("afterend", banner);
    }
  }

  const nav = primaryNav;
  const existingNavToggle = header.querySelector(".nav-toggle");
  const indexToggle = document.createElement("button");
  indexToggle.type = "button";
  indexToggle.className = "index-toggle";
  indexToggle.setAttribute("aria-controls", "scientific-index-drawer");
  indexToggle.setAttribute("aria-expanded", "false");
  indexToggle.setAttribute("aria-label", ui.index);
  indexToggle.title = ui.index;
  indexToggle.innerHTML = `<span>${ui.index}</span>`;
  if (existingNavToggle) existingNavToggle.insertAdjacentElement("afterend", indexToggle);
  else if (nav) nav.insertAdjacentElement("beforebegin", indexToggle);
  else header.append(indexToggle);

  const backdrop = document.createElement("div");
  backdrop.className = "sci-index-backdrop";
  const drawer = document.createElement("aside");
  drawer.className = "sci-index-drawer";
  drawer.id = "scientific-index-drawer";
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");
  drawer.setAttribute("aria-hidden", "true");
  drawer.setAttribute("aria-labelledby", "scientific-index-title");
  drawer.innerHTML = `<div class="sci-index-head"><div><p class="sci-index-kicker">${ui.kicker}</p><h2 id="scientific-index-title">${ui.title}</h2></div><button class="sci-index-close" type="button" aria-label="${ui.close}">×</button></div><div class="sci-index-tools"><input class="sci-index-search" type="search" autocomplete="off" placeholder="${ui.search}" aria-label="${ui.search}"><p class="sci-index-stats" aria-live="polite"></p></div><div class="sci-index-body"><p class="sci-empty">…</p></div>`;
  document.body.append(backdrop, drawer);

  const closeButton = drawer.querySelector(".sci-index-close");
  const search = drawer.querySelector(".sci-index-search");
  const body = drawer.querySelector(".sci-index-body");
  const stats = drawer.querySelector(".sci-index-stats");
  let loaded = false;
  let loadPromise = null;
  let returnFocus = indexToggle;

  const groupLabels = ui.groups || UI.en.groups;
  const currentPath = new URL(location.href).pathname.replace(/\/index\.html$/, "/");
  const currentGroup = currentPath.includes("/novel/") ? "narrative"
    : currentPath.includes("/claims/") ? "claims"
    : currentPath.includes("/assets/") ? "assets"
    : currentPath.endsWith("/theory.html") ? "theory"
    : currentPath.endsWith("/machine.html") ? "machine"
    : "core";

  const sameTarget = (href) => {
    const u = new URL(href, siteRoot);
    const a = `${u.pathname.replace(/\/index\.html$/, "/")}${u.hash}`;
    const b = `${new URL(location.href).pathname.replace(/\/index\.html$/, "/")}${location.hash}`;
    return a === b || (!u.hash && u.pathname.replace(/\/index\.html$/, "/") === new URL(location.href).pathname.replace(/\/index\.html$/, "/"));
  };

  const renderIndex = (data) => {
    body.textContent = "";
    let total = 0;
    const groupRank = new Map(["core", "theory", "narrative", "claims", "assets", "verification", "machine", "languages"].map((id, i) => [id, i]));
    const groups = [...(data.groups || [])].sort((a, b) => (groupRank.get(a.id) ?? 99) - (groupRank.get(b.id) ?? 99));
    for (const group of groups) {
      const entries = group.entries || [];
      total += entries.length;
      const details = document.createElement("details");
      details.className = "sci-group";
      details.dataset.group = group.id;
      details.open = group.id === "core" || group.id === currentGroup;
      const summary = document.createElement("summary");
      const groupName = groupLabels?.[group.id] || UI.en.groups?.[group.id] || group.title;
      summary.innerHTML = `<span>${groupName}</span><small>${entries.length}</small>`;
      const list = document.createElement("ul");
      list.className = "sci-entry-list";
      for (const entry of entries) {
        const li = document.createElement("li");
        li.className = "sci-entry";
        li.dataset.search = fold([entry.id, entry.title, entry.type, entry.status, entry.meta].filter(Boolean).join(" "));
        const a = document.createElement("a");
        a.href = /^(?:https?:|mailto:)/.test(entry.url) ? entry.url : new URL(entry.url, siteRoot).href;
        if (sameTarget(a.href)) {
          a.setAttribute("aria-current", "page");
          li.classList.add("is-current");
          details.open = true;
        }
        const title = document.createElement("span"); title.className = "sci-entry-title"; title.textContent = entry.title || entry.id;
        const id = document.createElement("span"); id.className = "sci-entry-id"; id.textContent = entry.id || entry.type;
        const meta = document.createElement("span"); meta.className = "sci-entry-meta"; meta.textContent = [entry.type, entry.status, entry.meta].filter(Boolean).join(" · ");
        a.append(title, id, meta); li.append(a); list.append(li);
      }
      details.append(summary, list); body.append(details);
    }
    stats.textContent = `${total} ${ui.results}`;
    loaded = true;
  };

  const ensureLoaded = () => {
    if (loaded) return Promise.resolve();
    if (!loadPromise) {
      loadPromise = fetch(new URL("machine/scientific-index.json", siteRoot), {cache: "no-store"})
        .then((r) => { if (!r.ok) throw new Error(`Index ${r.status}`); return r.json(); })
        .then(renderIndex)
        .catch(() => { body.innerHTML = `<p class="sci-empty">${ui.unavailable || UI.en.unavailable}</p>`; });
    }
    return loadPromise;
  };

  const resetMobileNavToggle = () => {
    if (!existingNavToggle) return;
    existingNavToggle.setAttribute("aria-expanded", "false");
    existingNavToggle.textContent = currentLang === "vi" ? "Mục lục" : "Menu";
    existingNavToggle.setAttribute("aria-label", currentLang === "vi" ? "Mở điều hướng trang" : "Open site navigation");
  };

  const focusables = () => [...drawer.querySelectorAll('button:not([disabled]), input:not([disabled]), a[href], summary, [tabindex]:not([tabindex="-1"])')].filter((el) => !el.hidden && el.getClientRects().length);

  const setOpen = async (open) => {
    if (open) {
      returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : indexToggle;
      await ensureLoaded();
    }
    drawer.classList.toggle("is-open", open);
    backdrop.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    indexToggle.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("sci-index-open", open);
    if (open) {
      if (languageMenu) languageMenu.open = false;
      nav?.classList.remove("is-open");
      resetMobileNavToggle();
      setTimeout(() => search.focus(), 20);
    } else {
      (returnFocus?.isConnected ? returnFocus : indexToggle).focus();
    }
  };

  indexToggle.addEventListener("click", () => setOpen(!drawer.classList.contains("is-open")));
  closeButton.addEventListener("click", () => setOpen(false));
  backdrop.addEventListener("click", () => setOpen(false));
  drawer.addEventListener("click", (event) => { if (event.target.closest("a")) setOpen(false); });
  existingNavToggle?.addEventListener("click", () => { if (drawer.classList.contains("is-open")) setOpen(false); }, {capture: true});
  languageMenu?.addEventListener("toggle", () => { if (languageMenu.open && drawer.classList.contains("is-open")) setOpen(false); });

  document.addEventListener("keydown", (event) => {
    if (!drawer.classList.contains("is-open")) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      return;
    }
    if (event.key !== "Tab") return;
    const els = focusables();
    if (!els.length) return;
    const first = els[0], last = els[els.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });

  search.addEventListener("input", () => {
    const tokens = fold(search.value.trim()).split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const group of drawer.querySelectorAll(".sci-group")) {
      let groupVisible = 0;
      for (const entry of group.querySelectorAll(".sci-entry")) {
        const show = !tokens.length || tokens.every((token) => entry.dataset.search.includes(token));
        entry.hidden = !show;
        if (show) groupVisible += 1;
      }
      group.hidden = groupVisible === 0;
      if (tokens.length && groupVisible) group.open = true;
      visible += groupVisible;
    }
    stats.textContent = `${visible} ${ui.results}`;
  });
})();