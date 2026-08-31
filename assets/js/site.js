(() => {
  const documentLanguage = (document.documentElement.lang || "vi").toLowerCase();
  const isEnglish = documentLanguage.startsWith("en");

  for (const link of document.querySelectorAll('a[href^="#"]')) {
    link.addEventListener("click", () => {
      history.replaceState(null, "", link.getAttribute("href"));
    });
  }

  const header = document.querySelector(".top");
  const nav = header?.querySelector("nav");
  if (!header || !nav) return;

  const scriptSource =
    document.currentScript?.src ||
    [...document.scripts].find((script) => /\/assets\/js\/site\.js(?:\?|$)/.test(script.src))
      ?.src;
  const siteRoot = scriptSource ? new URL("../../", scriptSource) : new URL("./", location.href);
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
    setNavigationOpen(!nav.classList.contains("is-open"));
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) setNavigationOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setNavigationOpen(false);
      toggle.focus();
    }
  });

  const mobileQuery = matchMedia("(max-width: 760px)");
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
