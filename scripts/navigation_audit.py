from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CONFIG = ROOT / "bl.config.yml"
EXPECTED_PROJECT_ROOT = "/bl-infinity/"
CORE_SECTIONS = (
    "theory",
    "novel",
    "academic",
    "adn",
    "claims",
    "assets",
    "author",
    "provenance",
    "critique",
    "machine",
)
SINGLE_H1_PAGES = (
    "theory.html",
    "bl-adn.html",
    "provenance.html",
    "critique.html",
    "author.html",
    "languages.html",
)
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
URL_ATTRIBUTES = {
    "a": ("href",),
    "area": ("href",),
    "audio": ("src",),
    "embed": ("src",),
    "iframe": ("src",),
    "img": ("src",),
    "input": ("src",),
    "link": ("href",),
    "object": ("data",),
    "script": ("src",),
    "source": ("src",),
    "video": ("src", "poster"),
}


def class_tokens(attrs: dict[str, str]) -> set[str]:
    return set(attrs.get("class", "").split())


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.ids: set[str] = set()
        self.h1_count = 0
        self.top_header_count = 0
        self.in_top_header = False
        self.header_navs: list[dict[str, object]] = []
        self.current_nav: dict[str, object] | None = None
        self.author_marks: list[dict[str, str]] = []
        self.brand_links: list[dict[str, str]] = []
        self.language_menus = 0
        self.in_language_menu = False
        self.language_menu_summaries = 0
        self.language_menu_links: list[dict[str, str]] = []
        self.skip_links: list[dict[str, str]] = []
        self.main_content: list[dict[str, str]] = []
        self.site_scripts: list[str] = []
        self.references: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {key.lower(): value or "" for key, value in attrs_list}
        classes = class_tokens(attrs)

        if tag == "header" and "top" in classes:
            self.top_header_count += 1
            self.in_top_header = True

        if tag == "nav" and self.in_top_header:
            nav: dict[str, object] = {"attrs": attrs, "links": []}
            self.header_navs.append(nav)
            self.current_nav = nav

        if self.in_top_header and "language-menu" in classes:
            self.language_menus += 1
            self.in_language_menu = True
        if tag == "summary" and self.in_language_menu:
            self.language_menu_summaries += 1

        if tag == "a":
            if self.current_nav is not None:
                links = self.current_nav["links"]
                assert isinstance(links, list)
                links.append(attrs)
            if self.in_top_header and "author-mark" in classes:
                self.author_marks.append(attrs)
            if self.in_top_header and "brand" in classes:
                self.brand_links.append(attrs)
            if self.in_language_menu:
                self.language_menu_links.append(attrs)
            if "skip-link" in classes:
                self.skip_links.append(attrs)

        if tag == "main" and attrs.get("id") == "main-content":
            self.main_content.append(attrs)
        if tag == "h1":
            self.h1_count += 1
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "script" and re.search(r"(?:^|/)assets/js/site\.js(?:[?#].*)?$", attrs.get("src", "")):
            self.site_scripts.append(attrs["src"])

        for attribute in URL_ATTRIBUTES.get(tag, ()):
            value = attrs.get(attribute)
            if value:
                self.references.append((tag, attribute, value))

        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs_list)
        if tag.lower() not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "nav" and self.current_nav is not None:
            self.current_nav = None
        if tag in {"details", "div"} and self.in_language_menu:
            # The generated language menu is a <details>; accepting a div keeps the
            # audit compatible with an equivalent accessible container.
            self.in_language_menu = False
        if tag == "header" and self.in_top_header:
            self.in_top_header = False
            self.current_nav = None
            self.in_language_menu = False
        if tag in self.stack:
            while self.stack:
                opened = self.stack.pop()
                if opened == tag:
                    break


def canonical_url() -> str:
    if not CONFIG.exists():
        return "https://kimbach91-prog.github.io/bl-infinity/"
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"^\s*canonical_url:\s*['\"]?([^'\"\s]+)", text, flags=re.M)
    return match.group(1).rstrip("/") + "/" if match else "https://kimbach91-prog.github.io/bl-infinity/"


CANONICAL_URL = canonical_url()
CANONICAL_PARTS = urlparse(CANONICAL_URL)
PROJECT_ROOT = CANONICAL_PARTS.path.rstrip("/") + "/"


def published_url(relative_path: Path) -> str:
    return urljoin(CANONICAL_URL, relative_path.as_posix())


def internal_target(page: Path, raw_url: str) -> tuple[Path | None, str | None, str | None]:
    """Return (target, fragment, error); external URLs return (None, None, None)."""
    value = raw_url.strip()
    if not value:
        return page, None, None
    parsed_raw = urlparse(value)
    if parsed_raw.scheme.lower() in {"mailto", "tel", "data", "blob"}:
        return None, None, None
    if parsed_raw.scheme.lower() == "javascript":
        return None, None, "unsafe javascript URL"

    resolved = urlparse(urljoin(published_url(page.relative_to(SITE)), value))
    if resolved.scheme not in {"http", "https", ""}:
        return None, None, None
    if resolved.netloc and resolved.netloc != CANONICAL_PARTS.netloc:
        return None, None, None

    path = unquote(resolved.path)
    root_without_slash = PROJECT_ROOT.rstrip("/")
    if path == root_without_slash:
        relative = ""
    elif path.startswith(PROJECT_ROOT):
        relative = path[len(PROJECT_ROOT) :]
    else:
        return None, None, f"same-origin URL escapes project root {PROJECT_ROOT}"

    target = (SITE / relative).resolve()
    try:
        target.relative_to(SITE.resolve())
    except ValueError:
        return None, None, "URL resolves outside generated site"
    if not relative or path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target, unquote(resolved.fragment) or None, None


def target_relative(target: Path) -> str:
    try:
        return target.relative_to(SITE.resolve()).as_posix()
    except ValueError:
        return str(target)


def expected_current(relative: str) -> tuple[str, str] | None:
    if relative in {"theory.html", "en/theory.html"}:
        return "theory", "page"
    if relative == "novel/index.html":
        return "novel", "page"
    if relative == "novel/chapter-001.html":
        return "novel", "location"
    if relative == "academic-democracy.html" or re.fullmatch(
        r"academic-democracy/[^/]+/index\.html", relative
    ):
        return "academic", "page"
    if relative in {"academic-democracy/discovery.html", "academic-democracy-technology.html"}:
        return "academic", "location"
    if relative == "bl-adn.html":
        return "adn", "page"
    if relative == "claims.html":
        return "claims", "page"
    if re.fullmatch(r"claims/[^/]+/index\.html", relative):
        return "claims", "location"
    if relative == "assets.html":
        return "assets", "page"
    if re.fullmatch(r"assets/[^/]+/index\.html", relative):
        return "assets", "location"
    if relative in {"author.html", "author/en/index.html"}:
        return "author", "page"
    if relative == "provenance.html":
        return "provenance", "page"
    if relative == "critique.html":
        return "critique", "page"
    if relative == "machine.html":
        return "machine", "page"
    return None


def allowed_section_target(section: str, relative: str) -> bool:
    fixed = {
        "theory": {"theory.html", "en/theory.html"},
        "novel": {"novel/index.html"},
        "adn": {"bl-adn.html"},
        "claims": {"claims.html"},
        "assets": {"assets.html"},
        "author": {"author.html", "author/en/index.html"},
        "provenance": {"provenance.html"},
        "critique": {"critique.html"},
        "machine": {"machine.html"},
    }
    if section == "academic":
        return relative == "academic-democracy.html" or bool(
            re.fullmatch(r"academic-democracy/[^/]+/index\.html", relative)
        )
    return relative in fixed.get(section, set())


parser = argparse.ArgumentParser(description="Audit the materialized BL∞ site navigation contract")
parser.add_argument("--strict", action="store_true", help="exit non-zero when contract errors are found")
args = parser.parse_args()

errors: list[str] = []
warnings: list[str] = []
notes: list[str] = []
pages: dict[Path, PageParser] = {}
reference_count = 0
navigable_count = 0

if PROJECT_ROOT != EXPECTED_PROJECT_ROOT:
    errors.append(
        f"canonical project root is {PROJECT_ROOT}, expected {EXPECTED_PROJECT_ROOT} for this release"
    )

if not SITE.exists():
    errors.append("generated site/ does not exist; run the complete build before navigation audit")
else:
    html_files = sorted(SITE.rglob("*.html"))
    if not html_files:
        errors.append("generated site contains no HTML pages")
    for path in html_files:
        relative = path.relative_to(SITE).as_posix()
        try:
            page_parser = PageParser()
            page_parser.feed(path.read_text(encoding="utf-8"))
            page_parser.close()
            pages[path.resolve()] = page_parser
        except Exception as exc:
            errors.append(f"cannot parse {relative}: {exc}")
            continue

        if page_parser.top_header_count:
            navigable_count += 1
            if page_parser.top_header_count != 1:
                errors.append(
                    f"{relative}: expected exactly one header.top, found {page_parser.top_header_count}"
                )
            primary_navs = [
                nav
                for nav in page_parser.header_navs
                if str(nav["attrs"].get("aria-label", "")).strip().lower() == "primary"
            ]
            if len(primary_navs) != 1:
                errors.append(
                    f"{relative}: expected exactly one nav[aria-label=Primary], found {len(primary_navs)}"
                )
                primary_nav = page_parser.header_navs[0] if len(page_parser.header_navs) == 1 else None
            else:
                primary_nav = primary_navs[0]

            section_links: dict[str, list[dict[str, str]]] = {section: [] for section in CORE_SECTIONS}
            if primary_nav is not None:
                nav_links = primary_nav["links"]
                assert isinstance(nav_links, list)
                for link in nav_links:
                    assert isinstance(link, dict)
                    section = link.get("data-section", "")
                    if section in section_links:
                        section_links[section].append(link)

            for section in CORE_SECTIONS:
                links = section_links[section]
                if len(links) != 1:
                    errors.append(
                        f"{relative}: primary nav needs exactly one data-section={section}, found {len(links)}"
                    )
                    continue
                target, _, target_error = internal_target(path, links[0].get("href", ""))
                if target_error:
                    errors.append(f"{relative}: data-section={section} {target_error}")
                elif target is None or not allowed_section_target(section, target_relative(target)):
                    shown = links[0].get("href", "") or "<missing>"
                    errors.append(
                        f"{relative}: data-section={section} points to unexpected target {shown}"
                    )

            if len(page_parser.author_marks) != 1:
                errors.append(
                    f"{relative}: expected exactly one linked .author-mark, found {len(page_parser.author_marks)}"
                )
            elif not page_parser.author_marks[0].get("href"):
                errors.append(f"{relative}: .author-mark is missing href")
            else:
                author_target, _, author_error = internal_target(
                    path, page_parser.author_marks[0]["href"]
                )
                if author_error:
                    errors.append(f"{relative}: .author-mark {author_error}")
                elif author_target is None or not allowed_section_target(
                    "author", target_relative(author_target)
                ):
                    errors.append(f"{relative}: .author-mark must link to a canonical author page")

            if page_parser.language_menus != 1:
                errors.append(
                    f"{relative}: expected exactly one .language-menu, found {page_parser.language_menus}"
                )
            if page_parser.language_menu_summaries != 1:
                errors.append(
                    f"{relative}: language menu needs exactly one summary, found {page_parser.language_menu_summaries}"
                )
            menu_languages = {
                link.get("hreflang", "").lower() for link in page_parser.language_menu_links
            }
            for language in ("vi", "en"):
                if language not in menu_languages:
                    errors.append(f"{relative}: language menu is missing hreflang={language}")

            if len(page_parser.skip_links) != 1:
                errors.append(
                    f"{relative}: expected exactly one .skip-link, found {len(page_parser.skip_links)}"
                )
            elif page_parser.skip_links[0].get("href") != "#main-content":
                errors.append(f"{relative}: skip link must target #main-content")
            if len(page_parser.main_content) != 1:
                errors.append(
                    f"{relative}: expected exactly one main#main-content, found {len(page_parser.main_content)}"
                )
            elif page_parser.main_content[0].get("tabindex") != "-1":
                errors.append(f"{relative}: main#main-content must have tabindex=-1")
            if len(page_parser.site_scripts) != 1:
                errors.append(
                    f"{relative}: expected exactly one assets/js/site.js, found {len(page_parser.site_scripts)}"
                )
            else:
                script_target, _, script_error = internal_target(path, page_parser.site_scripts[0])
                if script_error:
                    errors.append(f"{relative}: site navigation script {script_error}")
                elif script_target is None or target_relative(script_target) != "assets/js/site.js":
                    errors.append(f"{relative}: site navigation script is not the local assets/js/site.js")

            if len(page_parser.brand_links) != 1:
                errors.append(
                    f"{relative}: expected exactly one .brand link, found {len(page_parser.brand_links)}"
                )
            elif relative in {"index.html", "en/index.html"}:
                if page_parser.brand_links[0].get("aria-current") != "page":
                    errors.append(f"{relative}: home brand must have aria-current=page")
                brand_target, _, brand_error = internal_target(
                    path, page_parser.brand_links[0].get("href", "")
                )
                if brand_error or brand_target is None or brand_target.resolve() != path.resolve():
                    errors.append(f"{relative}: current home brand must link to the current page")
            elif page_parser.brand_links[0].get("aria-current"):
                errors.append(f"{relative}: non-home brand must not be marked current")

            current_expectation = expected_current(relative)
            if current_expectation:
                expected_section, expected_value = current_expectation
                links = section_links[expected_section]
                if len(links) == 1 and links[0].get("aria-current") != expected_value:
                    errors.append(
                        f"{relative}: data-section={expected_section} needs aria-current={expected_value}"
                    )
                if len(links) == 1 and expected_value == "page":
                    current_target, _, current_error = internal_target(
                        path, links[0].get("href", "")
                    )
                    if (
                        current_error
                        or current_target is None
                        or current_target.resolve() != path.resolve()
                    ):
                        errors.append(
                            f"{relative}: aria-current=page link for {expected_section} must target the current page"
                        )
                for section, candidate_links in section_links.items():
                    if section == expected_section:
                        continue
                    if any(link.get("aria-current") for link in candidate_links):
                        errors.append(
                            f"{relative}: unexpected current state on core data-section={section}"
                        )
                contextual = {
                    "academic-democracy/discovery.html": "academic-discovery",
                    "academic-democracy-technology.html": "academic-technology",
                }.get(relative)
                if contextual and primary_nav is not None:
                    nav_links = primary_nav["links"]
                    assert isinstance(nav_links, list)
                    contextual_links = [
                        link
                        for link in nav_links
                        if isinstance(link, dict) and link.get("data-section") == contextual
                    ]
                    if len(contextual_links) != 1 or contextual_links[0].get("aria-current") != "page":
                        errors.append(
                            f"{relative}: contextual data-section={contextual} needs aria-current=page"
                        )
            else:
                current_core = [
                    section
                    for section, candidate_links in section_links.items()
                    if any(link.get("aria-current") for link in candidate_links)
                ]
                if current_core:
                    errors.append(
                        f"{relative}: unexpected current core section(s): {', '.join(current_core)}"
                    )

        for tag, attribute, value in page_parser.references:
            reference_count += 1
            target, fragment, target_error = internal_target(path, value)
            if target_error:
                errors.append(f"{relative}: {tag}[{attribute}]={value!r}: {target_error}")
                continue
            if target is None:
                continue
            if not target.exists():
                errors.append(
                    f"{relative}: broken local {tag}[{attribute}]={value!r} -> {target_relative(target)}"
                )
                continue
            if fragment and target.suffix.lower() in {".html", ".htm"}:
                target_page = pages.get(target.resolve())
                if target_page is not None and fragment not in target_page.ids:
                    errors.append(
                        f"{relative}: missing fragment #{fragment} in {target_relative(target)}"
                    )

    # Cross-page fragment targets may sort after the referring page, so verify
    # them again after every HTML document has been parsed.
    for path, page_parser in pages.items():
        relative = path.relative_to(SITE.resolve()).as_posix()
        for tag, attribute, value in page_parser.references:
            target, fragment, target_error = internal_target(path, value)
            if target_error or target is None or not fragment or not target.exists():
                continue
            if target.suffix.lower() not in {".html", ".htm"}:
                continue
            target_page = pages.get(target.resolve())
            if target_page is not None and fragment not in target_page.ids:
                errors.append(
                    f"{relative}: missing fragment #{fragment} in {target_relative(target)}"
                )

    for relative in SINGLE_H1_PAGES:
        path = (SITE / relative).resolve()
        page_parser = pages.get(path)
        if page_parser is None:
            errors.append(f"required single-H1 page is missing: {relative}")
        elif page_parser.h1_count != 1:
            errors.append(f"{relative}: expected exactly one h1, found {page_parser.h1_count}")

    not_found_path = (SITE / "404.html").resolve()
    not_found = pages.get(not_found_path)
    if not_found is None:
        errors.append("required 404.html is missing")
    else:
        for tag, attribute, value in not_found.references:
            stripped = value.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parsed = urlparse(stripped)
            if parsed.scheme or stripped.startswith("//"):
                continue
            if not stripped.startswith(EXPECTED_PROJECT_ROOT):
                errors.append(
                    f"404.html: local {tag}[{attribute}] must start with {EXPECTED_PROJECT_ROOT}: {value}"
                )

errors = sorted(set(errors))
warnings = sorted(set(warnings))
notes.append(f"audited {len(pages)} HTML pages, {navigable_count} with header.top")
notes.append(f"checked {reference_count} local/external URL attributes")
result = {
    "audit": "BL-INFINITY-NAVIGATION",
    "mode": "strict" if args.strict else "report",
    "site": "site/",
    "canonical_url": CANONICAL_URL,
    "project_root": PROJECT_ROOT,
    "html_pages": len(pages),
    "navigable_pages": navigable_count,
    "references_checked": reference_count,
    "errors": errors,
    "warnings": warnings,
    "notes": notes,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
if errors and args.strict:
    sys.exit(1)
