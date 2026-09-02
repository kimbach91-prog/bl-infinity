(() => {
  const scriptSource = document.currentScript?.src || [...document.scripts].find((s) => /navigation-system\.js(?:\?|$)/.test(s.src))?.src;
  if (!scriptSource) return;
  const siteRoot = new URL("../../", scriptSource);
  const header = document.querySelector(".top");
  if (!header) return;

  const UI = {
    vi:{index:"Chỉ mục khoa học",close:"Đóng",search:"Tìm học thuyết, claim, asset, chương...",kicker:"BL∞ SCIENTIFIC INDEX",title:"Chỉ mục khoa học toàn hệ",recommended:"Ưu tiên theo ngôn ngữ trình duyệt",detected:"Ngôn ngữ phù hợp đã được đưa lên đầu",open:"Mở bản này",results:"mục",groups:{core:"Lõi nghiên cứu",theory:"Chương học thuyết",claims:"Claim Registry",assets:"Asset Registry",narrative:"Truyện / HALF-CANON",verification:"Kiểm chứng & quản trị",machine:"Machine layer",languages:"Ngôn ngữ"}},
    en:{index:"Scientific index",close:"Close",search:"Search theories, claims, assets, chapters...",kicker:"BL∞ SCIENTIFIC INDEX",title:"Complete scientific index",recommended:"Browser language priority",detected:"A matching language edition is prioritized",open:"Open edition",results:"items",groups:{core:"Core research",theory:"Theory chapters",claims:"Claim Registry",assets:"Asset Registry",narrative:"Narrative / HALF-CANON",verification:"Verification & governance",machine:"Machine layer",languages:"Languages"}},
    es:{index:"Índice científico",close:"Cerrar",search:"Buscar teorías, claims, assets, capítulos...",kicker:"BL∞ ÍNDICE CIENTÍFICO",title:"Índice científico completo",recommended:"Prioridad por idioma del navegador",detected:"Se prioriza una edición compatible",open:"Abrir edición",results:"elementos"},
    fr:{index:"Index scientifique",close:"Fermer",search:"Rechercher théories, claims, assets, chapitres...",kicker:"BL∞ INDEX SCIENTIFIQUE",title:"Index scientifique complet",recommended:"Priorité à la langue du navigateur",detected:"Une édition correspondante est prioritaire",open:"Ouvrir",results:"éléments"},
    de:{index:"Wissenschaftsindex",close:"Schließen",search:"Theorien, Claims, Assets, Kapitel suchen...",kicker:"BL∞ WISSENSCHAFTSINDEX",title:"Vollständiger Wissenschaftsindex",recommended:"Browser-Sprache priorisiert",detected:"Eine passende Sprachfassung wird zuerst gezeigt",open:"Öffnen",results:"Einträge"},
    pt:{index:"Índice científico",close:"Fechar",search:"Buscar teorias, claims, assets, capítulos...",kicker:"BL∞ ÍNDICE CIENTÍFICO",title:"Índice científico completo",recommended:"Prioridade pelo idioma do navegador",detected:"Uma edição compatível foi priorizada",open:"Abrir",results:"itens"},
    zh:{index:"科学索引",close:"关闭",search:"搜索理论、主张、资产、章节...",kicker:"BL∞ 科学索引",title:"完整科学索引",recommended:"优先浏览器语言",detected:"已优先显示匹配语言版本",open:"打开版本",results:"项"},
    ja:{index:"科学索引",close:"閉じる",search:"理論・主張・資産・章を検索...",kicker:"BL∞ 科学索引",title:"完全科学索引",recommended:"ブラウザ言語を優先",detected:"一致する言語版を優先表示",open:"開く",results:"件"},
    ko:{index:"과학 색인",close:"닫기",search:"이론, 주장, 자산, 장 검색...",kicker:"BL∞ 과학 색인",title:"전체 과학 색인",recommended:"브라우저 언어 우선",detected:"일치하는 언어판을 우선 표시",open:"열기",results:"항목"},
    ru:{index:"Научный индекс",close:"Закрыть",search:"Поиск теорий, claims, assets, глав...",kicker:"BL∞ НАУЧНЫЙ ИНДЕКС",title:"Полный научный индекс",recommended:"Приоритет языка браузера",detected:"Подходящая языковая версия показана первой",open:"Открыть",results:"объектов"},
    ar:{index:"الفهرس العلمي",close:"إغلاق",search:"ابحث في النظريات والادعاءات والأصول والفصول...",kicker:"BL∞ الفهرس العلمي",title:"الفهرس العلمي الكامل",recommended:"أولوية لغة المتصفح",detected:"تم تقديم النسخة اللغوية المطابقة",open:"فتح النسخة",results:"عنصر"},
    hi:{index:"वैज्ञानिक सूचकांक",close:"बंद करें",search:"सिद्धांत, दावे, assets, अध्याय खोजें...",kicker:"BL∞ वैज्ञानिक सूचकांक",title:"पूर्ण वैज्ञानिक सूचकांक",recommended:"ब्राउज़र भाषा प्राथमिकता",detected:"मिलती भाषा का संस्करण पहले दिखाया गया",open:"खोलें",results:"आइटम"},
    id:{index:"Indeks ilmiah",close:"Tutup",search:"Cari teori, klaim, aset, bab...",kicker:"BL∞ INDEKS ILMIAH",title:"Indeks ilmiah lengkap",recommended:"Prioritas bahasa browser",detected:"Edisi bahasa yang cocok diprioritaskan",open:"Buka edisi",results:"item"}
  };

  const normalizeLang = (value="") => {
    const v = String(value).toLowerCase();
    if (v.startsWith("zh")) return "zh";
    return v.split("-")[0];
  };
  const currentLang = normalizeLang(document.documentElement.lang || "vi");
  const ui = UI[currentLang] || UI.en;

  const updateHeaderHeight = () => document.documentElement.style.setProperty("--bl-header-h", `${Math.ceil(header.getBoundingClientRect().height)}px`);
  updateHeaderHeight();
  addEventListener("resize", updateHeaderHeight, {passive:true});

  const safeStorageGet = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
  const safeStorageSet = (key,val) => { try { localStorage.setItem(key,val); } catch {} };
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
      const priorityTitle = document.createElement("p");
      priorityTitle.className = "language-priority-title";
      priorityTitle.textContent = (UI[preferredLang] || UI.en).recommended;
      preferredLink.classList.add("language-priority-link");
      panel.prepend(priorityTitle, preferredLink);

      const summary = languageMenu.querySelector("summary");
      if (summary) summary.title = (UI[preferredLang] || UI.en).detected;

      const relativePath = decodeURI(location.pathname).replace(siteRoot.pathname, "").replace(/^\//, "");
      const corePairs = new Map([
        ["", {vi:"index.html",en:"en/"}], ["index.html", {vi:"index.html",en:"en/"}], ["en/", {vi:"index.html",en:"en/"}],
        ["theory.html", {vi:"theory.html",en:"en/theory.html"}], ["en/theory.html", {vi:"theory.html",en:"en/theory.html"}],
        ["author.html", {vi:"author.html",en:"author/en/"}], ["author/en/", {vi:"author.html",en:"author/en/"}]
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

      const topicBar = document.querySelector(".topic-bar");
      const banner = document.createElement("div");
      banner.className = "language-priority-banner";
      const langName = preferredLink.querySelector("span")?.textContent?.trim() || preferredLink.textContent.trim();
      const preferredUI = UI[preferredLang] || UI.en;
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

  const nav = header.querySelector("nav");
  const existingNavToggle = header.querySelector(".nav-toggle");
  const indexToggle = document.createElement("button");
  indexToggle.type = "button";
  indexToggle.className = "index-toggle";
  indexToggle.setAttribute("aria-controls", "scientific-index-drawer");
  indexToggle.setAttribute("aria-expanded", "false");
  indexToggle.innerHTML = `<span>${ui.index}</span>`;
  if (existingNavToggle) existingNavToggle.insertAdjacentElement("afterend", indexToggle);
  else if (nav) nav.insertAdjacentElement("beforebegin", indexToggle);
  else header.append(indexToggle);

  const backdrop = document.createElement("div");
  backdrop.className = "sci-index-backdrop";
  const drawer = document.createElement("aside");
  drawer.className = "sci-index-drawer";
  drawer.id = "scientific-index-drawer";
  drawer.setAttribute("aria-hidden", "true");
  drawer.innerHTML = `<div class="sci-index-head"><div><p class="sci-index-kicker">${ui.kicker}</p><h2>${ui.title}</h2></div><button class="sci-index-close" type="button" aria-label="${ui.close}">×</button></div><div class="sci-index-tools"><input class="sci-index-search" type="search" autocomplete="off" placeholder="${ui.search}" aria-label="${ui.search}"><p class="sci-index-stats"></p></div><div class="sci-index-body"><p class="sci-empty">…</p></div>`;
  document.body.append(backdrop, drawer);

  const closeButton = drawer.querySelector(".sci-index-close");
  const search = drawer.querySelector(".sci-index-search");
  const body = drawer.querySelector(".sci-index-body");
  const stats = drawer.querySelector(".sci-index-stats");
  let loaded = false;
  let loadPromise = null;

  const groupLabels = ui.groups || UI.en.groups;
  const renderIndex = (data) => {
    body.textContent = "";
    let total = 0;
    for (const group of data.groups || []) {
      const entries = group.entries || [];
      total += entries.length;
      const details = document.createElement("details");
      details.className = "sci-group";
      if (["core","theory"].includes(group.id)) details.open = true;
      const summary = document.createElement("summary");
      summary.innerHTML = `<span>${groupLabels?.[group.id] || group.title}</span><small>${entries.length}</small>`;
      const list = document.createElement("ul");
      list.className = "sci-entry-list";
      for (const entry of entries) {
        const li = document.createElement("li");
        li.className = "sci-entry";
        li.dataset.search = [entry.id,entry.title,entry.type,entry.status,entry.meta].filter(Boolean).join(" ").toLowerCase();
        const a = document.createElement("a");
        a.href = /^(?:https?:|mailto:)/.test(entry.url) ? entry.url : new URL(entry.url, siteRoot).href;
        const title = document.createElement("span"); title.className = "sci-entry-title"; title.textContent = entry.title || entry.id;
        const id = document.createElement("span"); id.className = "sci-entry-id"; id.textContent = entry.id || entry.type;
        const meta = document.createElement("span"); meta.className = "sci-entry-meta"; meta.textContent = [entry.type,entry.status,entry.meta].filter(Boolean).join(" · ");
        a.append(title,id,meta); li.append(a); list.append(li);
      }
      details.append(summary,list); body.append(details);
    }
    stats.textContent = `${total} ${ui.results}`;
    loaded = true;
  };

  const ensureLoaded = () => {
    if (loaded) return Promise.resolve();
    if (!loadPromise) {
      loadPromise = fetch(new URL("machine/scientific-index.json", siteRoot), {cache:"no-store"})
        .then((r) => { if (!r.ok) throw new Error(`Index ${r.status}`); return r.json(); })
        .then(renderIndex)
        .catch(() => { body.innerHTML = `<p class="sci-empty">Scientific index unavailable.</p>`; });
    }
    return loadPromise;
  };

  const setOpen = async (open) => {
    if (open) await ensureLoaded();
    drawer.classList.toggle("is-open", open);
    backdrop.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    indexToggle.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("sci-index-open", open);
    if (open) {
      languageMenu && (languageMenu.open = false);
      nav?.classList.remove("is-open");
      existingNavToggle?.setAttribute("aria-expanded", "false");
      setTimeout(() => search.focus(), 20);
    } else indexToggle.focus();
  };

  indexToggle.addEventListener("click", () => setOpen(!drawer.classList.contains("is-open")));
  closeButton.addEventListener("click", () => setOpen(false));
  backdrop.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && drawer.classList.contains("is-open")) setOpen(false); });
  drawer.addEventListener("click", (event) => { if (event.target.closest("a")) setOpen(false); });

  search.addEventListener("input", () => {
    const q = search.value.trim().toLowerCase();
    let visible = 0;
    for (const group of drawer.querySelectorAll(".sci-group")) {
      let groupVisible = 0;
      for (const entry of group.querySelectorAll(".sci-entry")) {
        const show = !q || entry.dataset.search.includes(q);
        entry.hidden = !show;
        if (show) groupVisible += 1;
      }
      group.hidden = groupVisible === 0;
      if (q && groupVisible) group.open = true;
      visible += groupVisible;
    }
    stats.textContent = `${visible} ${ui.results}`;
  });
})();
