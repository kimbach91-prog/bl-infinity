from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def copy(src: str, dst: str) -> None:
    source = ROOT / src
    target = ROOT / dst
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def inject_regressor_feature() -> None:
    index = SITE / "index.html"
    text = index.read_text(encoding="utf-8")
    marker = "<main><article>"
    feature = '''<section class="author-spotlight" aria-labelledby="regressor-feature-title">
<p class="eyebrow">Công bố mới · 02.09.2026 · BL-RP-FRC</p>
<h2 id="regressor-feature-title">Mệnh đề Kẻ Hồi Quy — Liên kết Kết quả Tương lai với Hiện tại</h2>
<p>Một kết quả tương lai còn vô khả định lượng đầy đủ được dùng như <strong>điều kiện biên giả định</strong>: suy ngược các ràng buộc cần hình thành, tạo hành động ở hiện tại, rồi để Reality Veto liên tục phá những nhánh sai.</p>
<p><strong>FutureBoundary ≠ FutureFact.</strong> BackwardInference ≠ BackwardSignal. Phần vật lý được giữ ở trạng thái giả thuyết mở cho tới khi có bằng chứng thực nghiệm thích hợp.</p>
<p><a class="primary-link" href="regressor-proposition.html">Đọc Mệnh đề Kẻ Hồi Quy, sơ đồ phả hệ và claim map →</a></p>
</section>'''
    if "regressor-feature-title" not in text:
        if marker not in text:
            raise RuntimeError("homepage main/article marker not found")
        text = text.replace(marker, marker + feature, 1)
        index.write_text(text, encoding="utf-8")

    sitemap = SITE / "sitemap.xml"
    sm = sitemap.read_text(encoding="utf-8")
    route = '<url><loc>https://kimbach91-prog.github.io/bl-infinity/regressor-proposition.html</loc><lastmod>2026-09-02</lastmod></url>'
    if "regressor-proposition.html" not in sm:
        sm = sm.replace("</urlset>", route + "\n</urlset>")
        sitemap.write_text(sm, encoding="utf-8")

    llms = SITE / "llms.txt"
    if llms.exists():
        lm = llms.read_text(encoding="utf-8")
        if "regressor-proposition.html" not in lm:
            lm += "\n\n## Regressor Proposition / Mệnh đề Kẻ Hồi Quy\nPublic route: /regressor-proposition.html\nStatus: research proposition; future-boundary backcasting is a current epistemic mechanism, while controllable backward physical information remains an unverified physics hypothesis.\n"
            llms.write_text(lm, encoding="utf-8")


def register_era_atlas() -> None:
    route = "https://kimbach91-prog.github.io/bl-infinity/novel/era-language-style-atlas.html"
    sitemap = SITE / "sitemap.xml"
    if sitemap.exists():
        sm = sitemap.read_text(encoding="utf-8")
        entry = f"<url><loc>{route}</loc><lastmod>2026-09-02</lastmod></url>"
        if route not in sm:
            sm = sm.replace("</urlset>", entry + "\n</urlset>")
            sitemap.write_text(sm, encoding="utf-8")
    llms = SITE / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        if "era-language-style-atlas.html" not in text:
            text += "\n\n## Novel Era-Language & Literary Style Atlas\nPublic route: /novel/era-language-style-atlas.html\nMachine registry: /machine/novel-era-language-style-registry.json\nUse: resolve historical scenes by year/era, region, generation, social relation, communication medium and literary mode; do not reduce an era to one authorial style or one national voice.\n"
            llms.write_text(text, encoding="utf-8")


def main() -> None:
    run(sys.executable, "scripts/git_publication_gate.py", "--strict", "--tree")
    run(sys.executable, "scripts/audit.py", "--strict", "--release")
    run(sys.executable, "scripts/audit_unified_system.py")
    run(sys.executable, "scripts/disclosure_audit.py", "--strict")
    run(sys.executable, "scripts/security_audit.py", "--strict")
    run(sys.executable, "scripts/challenge_disclosure_audit.py")

    run(sys.executable, "scripts/build.py")
    for name in (
        "academic-democracy.html",
        "academic-democracy-technology.html",
        "unknown.html",
        "grand-ending.html",
        "world.html",
        "regressor-proposition.html",
    ):
        copy(f"public/{name}", f"site/{name}")

    run(sys.executable, "scripts/stage_novel.py")
    # Reader CSS is an explicit reader asset; build.py historically copied only main.css.
    copy("assets/css/novel-reader.css", "site/assets/css/novel-reader.css")

    run(sys.executable, "scripts/stage_grand_ending_home.py")
    inject_regressor_feature()

    for name in ("challenge.html", "research-puzzles.html"):
        target = SITE / name
        if target.exists():
            target.unlink()

    run(sys.executable, "scripts/run_discovery.py")
    register_era_atlas()

    for name in ("challenge.html", "research-puzzles.html"):
        copy(f"public/{name}", f"site/{name}")

    for name in (
        "bl-reverse-system.json",
        "bl-hrd.json",
        "bl-infinity-unified-system.json",
        "unified-constituents.json",
        "reality-gia-tai-topology.json",
        "open-ended-epistemic-phase-space.json",
        "unknown-doctrine.json",
        "grand-ending-unknown.json",
        "compressed-regression-hypothesis.json",
    ):
        copy(f"machine/{name}", f"site/machine/{name}")

    run(sys.executable, "scripts/harden_site.py")
    run(sys.executable, "scripts/humanize_public_text.py")
    run(sys.executable, "scripts/apply_hypothesis_science_patch.py")
    run(sys.executable, "scripts/seo_release_guard.py")
    run(sys.executable, "scripts/security_audit.py", "--strict", "--site")
    run(sys.executable, "scripts/challenge_disclosure_audit.py", "--site")
    run(sys.executable, "scripts/navigation_audit.py", "--strict")
    print("OWNER_PAGES_BUILD_OK")


if __name__ == "__main__":
    main()
