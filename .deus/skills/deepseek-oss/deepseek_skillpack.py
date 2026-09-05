#!/usr/bin/env python3
"""DEUS DeepSeek OSS skillpack.

Static-only acquisition and three-pass regression of public DeepSeek-AI repositories.
It never executes upstream code. The design is reuse-first: unchanged repository SHAs
are served from a mastery cache; only deltas are re-scanned.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

USER_AGENT = "deus-deepseek-oss-skillpack/1.0"
DEFAULT_ORG = "deepseek-ai"
DEFAULT_DEPTH = 64
SOURCE_EXTS = {
    ".py", ".pyi", ".md", ".rst", ".txt", ".json", ".toml", ".yaml", ".yml",
    ".c", ".cc", ".cpp", ".cu", ".cuh", ".h", ".hpp", ".rs", ".go", ".java",
    ".kt", ".ts", ".tsx", ".js", ".jsx", ".sh", ".ps1", ".cmake"
}
EXCLUDED_DIRS = {".git", "node_modules", "dist", "build", ".next", ".venv", "venv", "__pycache__"}


def run(cmd: Sequence[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd), cwd=str(cwd) if cwd else None, check=check,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(obj: object) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def github_json(url: str, token: Optional[str] = None) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def discover_public_repos(org: str, token: Optional[str], include_archived: bool = False) -> List[dict]:
    repos: List[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?type=public&per_page=100&page={page}&sort=full_name"
        batch = github_json(url, token)
        if not isinstance(batch, list):
            raise RuntimeError("GitHub API returned a non-list repository response")
        if not batch:
            break
        for repo in batch:
            if repo.get("fork"):
                continue
            if repo.get("archived") and not include_archived:
                continue
            repos.append(repo)
        if len(batch) < 100:
            break
        page += 1
    repos.sort(key=lambda r: str(r.get("full_name", "")).lower())
    return repos


def git_head(repo_dir: Path) -> Optional[str]:
    try:
        return run(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()
    except Exception:
        return None


def sync_repo(repo: Mapping[str, object], root: Path, depth: int = DEFAULT_DEPTH) -> dict:
    name = str(repo["name"])
    url = str(repo["clone_url"])
    default_branch = str(repo.get("default_branch") or "main")
    target = root / name
    if target.exists() and not (target / ".git").exists():
        raise RuntimeError(f"Refusing to overwrite non-git path: {target}")
    if not target.exists():
        run(["git", "clone", "--filter=blob:none", "--depth", str(depth), "--branch", default_branch, url, str(target)])
    else:
        run(["git", "remote", "set-url", "origin", url], cwd=target)
        run(["git", "fetch", "--prune", "--tags", "--depth", str(depth), "origin", default_branch], cwd=target)
        run(["git", "checkout", "-B", default_branch, f"origin/{default_branch}"], cwd=target)
    head = git_head(target)
    return {
        "name": name,
        "full_name": repo.get("full_name"),
        "clone_url": url,
        "html_url": repo.get("html_url"),
        "default_branch": default_branch,
        "head_sha": head,
        "license_spdx": (repo.get("license") or {}).get("spdx_id") if isinstance(repo.get("license"), dict) else None,
        "archived": bool(repo.get("archived")),
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
    }


def sync_all(org: str, root: Path, manifest_path: Path, depth: int, token: Optional[str], include_archived: bool) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    repos = discover_public_repos(org, token, include_archived=include_archived)
    synced = []
    failures = []
    for repo in repos:
        try:
            synced.append(sync_repo(repo, root, depth=depth))
        except Exception as exc:
            failures.append({"name": repo.get("name"), "error": str(exc)})
    manifest = {
        "schema_version": 1,
        "org": org,
        "generated_unix": int(time.time()),
        "static_only": True,
        "repository_count": len(synced),
        "repositories": synced,
        "failures": failures,
    }
    manifest["manifest_sha256"] = canonical_hash({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("techniques"), dict):
        raise ValueError("Registry must contain an object named 'techniques'")
    return data


def iter_source_files(root: Path, max_bytes: int = 2_000_000) -> Iterable[Path]:
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for name in files:
            p = Path(base) / name
            if p.suffix.lower() not in SOURCE_EXTS:
                continue
            try:
                if p.stat().st_size <= max_bytes:
                    yield p
            except OSError:
                continue


def compile_registry(registry: Mapping[str, object]) -> Dict[str, Tuple[str, List[re.Pattern]]]:
    out: Dict[str, Tuple[str, List[re.Pattern]]] = {}
    for name, spec_obj in registry["techniques"].items():
        spec = dict(spec_obj)
        category = str(spec.get("category", "unknown"))
        patterns = [re.compile(str(p), re.IGNORECASE) for p in spec.get("patterns", [])]
        out[str(name)] = (category, patterns)
    return out


def scan_worktree(repo_dir: Path, compiled: Mapping[str, Tuple[str, List[re.Pattern]]]) -> dict:
    counts = {name: 0 for name in compiled}
    examples: Dict[str, List[str]] = {name: [] for name in compiled}
    file_count = 0
    for path in iter_source_files(repo_dir):
        file_count += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(repo_dir))
        for name, (_, patterns) in compiled.items():
            hit_count = 0
            for pattern in patterns:
                hit_count += len(pattern.findall(text))
            if hit_count:
                counts[name] += hit_count
                if len(examples[name]) < 8:
                    examples[name].append(rel)
    techniques = sorted([k for k, v in counts.items() if v > 0])
    return {"file_count": file_count, "techniques": techniques, "counts": counts, "examples": examples}


def git_recent_revisions(repo_dir: Path, n: int = 3) -> List[str]:
    try:
        out = run(["git", "rev-list", f"--max-count={n}", "HEAD"], cwd=repo_dir).stdout
        return [x.strip() for x in out.splitlines() if x.strip()]
    except Exception:
        return []


def revision_changed_files(repo_dir: Path, rev: str) -> List[str]:
    try:
        out = run(["git", "show", "--format=", "--name-only", rev], cwd=repo_dir).stdout
        return sorted(set(x.strip() for x in out.splitlines() if x.strip()))
    except Exception:
        return []


def revision_marker_counts(repo_dir: Path, rev: str, registry: Mapping[str, object]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for name, spec_obj in registry["techniques"].items():
        patterns = list(dict(spec_obj).get("patterns", []))
        if not patterns:
            result[name] = 0
            continue
        ere = "(" + ")|(".join(patterns) + ")"
        try:
            cp = run(["git", "grep", "-I", "-E", "-i", "-n", ere, rev], cwd=repo_dir, check=False)
            lines = [ln for ln in cp.stdout.splitlines() if ln.strip()]
            result[name] = len(lines)
        except Exception:
            result[name] = 0
    return result


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "repos": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("repos"), dict):
            raise ValueError
        return data
    except Exception:
        return {"schema_version": 1, "repos": {}}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def scan_repositories(root: Path, registry: dict, cache_path: Path) -> Tuple[List[dict], dict]:
    compiled = compile_registry(registry)
    reg_hash = canonical_hash(registry)
    cache = load_cache(cache_path)
    repo_results: List[dict] = []
    for repo_dir in sorted([p for p in root.iterdir() if p.is_dir() and (p / ".git").exists()]):
        head = git_head(repo_dir)
        key = repo_dir.name
        cached = cache["repos"].get(key, {})
        if head and cached.get("head_sha") == head and cached.get("registry_hash") == reg_hash:
            result = dict(cached.get("result", {}))
            result["cache_hit"] = True
        else:
            result = scan_worktree(repo_dir, compiled)
            result.update({"repo": key, "head_sha": head, "cache_hit": False})
            cache["repos"][key] = {"head_sha": head, "registry_hash": reg_hash, "result": result}
        repo_results.append(result)
    cache["updated_unix"] = int(time.time())
    cache["registry_hash"] = reg_hash
    save_cache(cache_path, cache)
    return repo_results, cache


def pass1_reconstruct(root: Path, registry: dict, cache_path: Path) -> dict:
    repos, _ = scan_repositories(root, registry, cache_path)
    capability_to_repos: Dict[str, List[str]] = {k: [] for k in registry["techniques"]}
    for r in repos:
        for tech in r.get("techniques", []):
            capability_to_repos.setdefault(tech, []).append(r.get("repo", ""))
    capability_to_repos = {k: sorted(v) for k, v in capability_to_repos.items() if v}
    return {"name": "R1_RECONSTRUCT", "repos": repos, "capability_to_repos": capability_to_repos}


def pass2_regress_history(root: Path, registry: dict) -> dict:
    histories = []
    for repo_dir in sorted([p for p in root.iterdir() if p.is_dir() and (p / ".git").exists()]):
        revisions = git_recent_revisions(repo_dir, 3)
        rows = []
        for rev in revisions:
            rows.append({
                "rev": rev,
                "changed_files": revision_changed_files(repo_dir, rev)[:200],
                "marker_counts": revision_marker_counts(repo_dir, rev, registry),
            })
        deltas = []
        for a, b in zip(rows, rows[1:]):
            changed = {}
            for tech in registry["techniques"]:
                dv = int(a["marker_counts"].get(tech, 0)) - int(b["marker_counts"].get(tech, 0))
                if dv:
                    changed[tech] = dv
            deltas.append({"newer": a["rev"], "older": b["rev"], "marker_delta": changed})
        histories.append({"repo": repo_dir.name, "revisions": rows, "deltas": deltas})
    return {"name": "R2_HISTORY_REGRESSION", "histories": histories}


def observed_sets(pass1: Mapping[str, object]) -> List[Set[str]]:
    return [set(r.get("techniques", [])) for r in pass1.get("repos", []) if r.get("techniques")]


def pass3_synthesize_variants(pass1: dict, registry: dict, limit: int = 24) -> dict:
    observed = observed_sets(pass1)
    support: Dict[str, int] = {k: 0 for k in registry["techniques"]}
    for s in observed:
        for t in s:
            support[t] = support.get(t, 0) + 1
    techniques = [t for t, n in support.items() if n > 0]
    category = {k: str(v.get("category", "unknown")) for k, v in registry["techniques"].items()}
    candidates = []
    for size in (2, 3):
        for combo in itertools.combinations(techniques, size):
            if len({category[t] for t in combo}) < 2:
                continue
            combo_set = set(combo)
            if any(combo_set.issubset(s) for s in observed):
                continue
            pair_novelty = 0
            for a, b in itertools.combinations(combo, 2):
                if not any({a, b}.issubset(s) for s in observed):
                    pair_novelty += 1
            evidence = sum(min(support[t], 5) for t in combo)
            score = pair_novelty * 10 + evidence
            candidates.append({
                "techniques": list(combo),
                "categories": sorted({category[t] for t in combo}),
                "score": score,
                "pair_novelty": pair_novelty,
                "support": {t: support[t] for t in combo},
                "status": "HYPOTHETICAL_VARIANT_NOT_BENCHMARKED",
            })
    candidates.sort(key=lambda x: (-x["score"], x["techniques"]))
    return {"name": "R3_VARIANT_SYNTHESIS", "variants": candidates[:limit]}


def markdown_report(report: dict) -> str:
    r1, r2, r3 = report["passes"]
    lines = [
        "# DEUS DeepSeek OSS — Three-Pass Regression Report",
        "",
        f"Generated: `{report['generated_unix']}`",
        f"Registry hash: `{report['registry_hash']}`",
        "",
        "## Safety / evidence boundary",
        "",
        "- Upstream source was statically inspected; it was not executed.",
        "- A detected technique is a source marker, not proof of model quality or causal contribution.",
        "- R3 variants are hypotheses only until implemented and benchmarked independently.",
        "",
        "## R1 — Reconstruct current capability surface",
        "",
        f"Repositories scanned: **{len(r1['repos'])}**",
    ]
    for tech, repos in sorted(r1["capability_to_repos"].items()):
        lines.append(f"- `{tech}`: {', '.join(repos[:12])}" + (" …" if len(repos) > 12 else ""))
    lines += ["", "## R2 — Regress three revisions", ""]
    changed_repos = 0
    for h in r2["histories"]:
        if any(d["marker_delta"] for d in h["deltas"]):
            changed_repos += 1
    lines.append(f"Repositories with technique-marker deltas across the sampled 3 revisions: **{changed_repos}**")
    lines += ["", "## R3 — Candidate recombinations", ""]
    for i, v in enumerate(r3["variants"], 1):
        lines.append(f"{i}. `{' + '.join(v['techniques'])}` — score {v['score']} — **hypothesis, not benchmarked**")
    lines += ["", "## Reuse-first policy", "", "Unchanged `HEAD` + unchanged registry hash = cache hit; deep scan is skipped. New SHA or registry delta triggers re-analysis.", ""]
    return "\n".join(lines)


def regress(root: Path, registry_path: Path, cache_path: Path, output_json: Path, output_md: Path) -> dict:
    registry = load_registry(registry_path)
    r1 = pass1_reconstruct(root, registry, cache_path)
    r2 = pass2_regress_history(root, registry)
    r3 = pass3_synthesize_variants(r1, registry)
    report = {
        "schema_version": 1,
        "generated_unix": int(time.time()),
        "registry_hash": canonical_hash(registry),
        "passes": [r1, r2, r3],
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(markdown_report(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DEUS DeepSeek OSS skillpack: sync, cache, regress, synthesize variants")
    p.add_argument("--root", type=Path, default=Path(".deus-cache/deepseek-ai"))
    p.add_argument("--registry", type=Path, default=Path(__file__).with_name("technique_registry.json"))
    p.add_argument("--cache", type=Path, default=Path(".deus-state/deepseek-oss/mastery.json"))
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sync")
    ps.add_argument("--org", default=DEFAULT_ORG)
    ps.add_argument("--manifest", type=Path, default=Path(".deus-state/deepseek-oss/source-manifest.json"))
    ps.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    ps.add_argument("--include-archived", action="store_true")

    pr = sub.add_parser("regress")
    pr.add_argument("--json", type=Path, default=Path(".deus-state/deepseek-oss/regression.json"))
    pr.add_argument("--md", type=Path, default=Path(".deus-state/deepseek-oss/regression.md"))

    pa = sub.add_parser("all")
    pa.add_argument("--org", default=DEFAULT_ORG)
    pa.add_argument("--manifest", type=Path, default=Path(".deus-state/deepseek-oss/source-manifest.json"))
    pa.add_argument("--depth", type=int, default=DEFAULT_DEPTH)
    pa.add_argument("--include-archived", action="store_true")
    pa.add_argument("--json", type=Path, default=Path(".deus-state/deepseek-oss/regression.json"))
    pa.add_argument("--md", type=Path, default=Path(".deus-state/deepseek-oss/regression.md"))
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if args.cmd in {"sync", "all"}:
        manifest = sync_all(args.org, args.root, args.manifest, max(3, args.depth), token, args.include_archived)
        print(f"synced={manifest['repository_count']} failures={len(manifest['failures'])} manifest={args.manifest}")
    if args.cmd in {"regress", "all"}:
        if not args.root.exists():
            raise SystemExit(f"Repository root does not exist: {args.root}; run sync first")
        report = regress(args.root, args.registry, args.cache, args.json, args.md)
        print(f"passes={len(report['passes'])} variants={len(report['passes'][2]['variants'])} report={args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
