#!/usr/bin/env python3
"""Audit dependency licenses of a GitHub repository from its URL.

Usage:
  python3 scripts/oss/audit-github-repo.py https://github.com/OWNER/REPO [--ref BRANCH] [--json]

Sources, in order:
  1. GitHub dependency-graph SBOM API (direct + transitive, SPDX licenses)
  2. Fallback when the dependency graph is disabled/unavailable: root manifests
     (package.json, requirements.txt) read through the contents API (direct deps only)

License per package: SBOM license -> known-licenses.md cache -> npm / PyPI registry.
Each license is classified against .cursor/oss-policy.md (Allowed / Review Required / Blocked).

Auth: GITHUB_TOKEN env, else `gh auth token`, else anonymous (public repos, low rate limit).
Exit code: 0 PASS, 1 REVIEW REQUIRED, 2 BLOCK, 3 error.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / ".cursor" / "oss-policy.md"
CACHE = ROOT / ".cursor" / "skills" / "oss-license-compliance" / "references" / "known-licenses.md"

RANK = {"Allowed": 0, "Review Required": 1, "Blocked": 2}
NO_LICENSE = {"", "NOASSERTION", "NONE", "UNKNOWN"}


# ---------------------------------------------------------------- HTTP helpers
def _token() -> str | None:
    import os

    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


TOKEN = _token()


def http_json(url: str, github: bool = False):
    headers = {"User-Agent": "oss-audit", "Accept": "application/json"}
    if github:
        headers["Accept"] = "application/vnd.github+json"
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise


# ---------------------------------------------------------------- policy + cache
def load_policy() -> dict[str, str]:
    """Map SPDX id -> policy bucket, parsed from bullets under Allowed / Review Required / Blocked."""
    policy: dict[str, str] = {}
    bucket = None
    for line in POLICY.read_text(encoding="utf-8").splitlines():
        h = re.match(r"^###\s+(Allowed|Review Required|Blocked)\b", line)
        if h:
            bucket = h.group(1)
            continue
        if line.startswith("## ") or (line.startswith("### ") and not h):
            bucket = None
            continue
        if bucket and line.startswith("- "):
            for part in line[2:].split("/"):
                lic = part.strip().split(" ")[0]
                if re.fullmatch(r"[A-Za-z0-9.+-]+", lic):
                    policy[lic] = bucket
    return policy


def load_cache() -> dict[tuple[str, str], tuple[str, str]]:
    """(ecosystem, package lower) -> (SPDX expression, verified date)."""
    cache: dict[tuple[str, str], tuple[str, str]] = {}
    eco = None
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        if line.startswith("## npm"):
            eco = "npm"
        elif line.startswith("## PyPI"):
            eco = "pypi"
        elif line.startswith("## "):
            eco = None
        elif eco and line.startswith("|") and not line.startswith("| Package") and not line.startswith("|---"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 6:
                cache[(eco, cols[0].lower())] = (cols[2], cols[5])
    return cache


# ---------------------------------------------------------------- SPDX evaluation
def normalize_id(lic: str) -> str:
    """Deprecated SPDX ids -> current ids (GPL-3.0 -> GPL-3.0-only, GPL-2.0+ -> GPL-2.0-or-later)."""
    if lic.endswith("+"):
        return lic[:-1] + "-or-later"
    if re.fullmatch(r"(A|L)?GPL-\d\.\d", lic):
        return lic + "-only"
    return lic


def classify_id(lic: str, policy: dict[str, str]) -> str:
    base = normalize_id(lic.split(" WITH ")[0].strip())
    if base in policy:
        return policy[base]
    if base.upper() in NO_LICENSE or base.startswith("LicenseRef-"):
        return "Blocked"  # policy: Unknown / missing license -> Blocked
    return "Review Required"  # valid SPDX id not listed in policy -> human review


def evaluate(expr: str, policy: dict[str, str]) -> str:
    """OR -> best option (licensee may elect), AND -> worst. Returns policy bucket."""
    tokens = re.findall(r"\(|\)|\bAND\b|\bOR\b|[^\s()]+(?:\s+WITH\s+[^\s()]+)?", expr)
    pos = 0

    def parse_or():
        nonlocal pos
        vals = [parse_and()]
        while pos < len(tokens) and tokens[pos] == "OR":
            pos += 1
            vals.append(parse_and())
        return min(vals, key=RANK.get)

    def parse_and():
        nonlocal pos
        vals = [parse_atom()]
        while pos < len(tokens) and tokens[pos] == "AND":
            pos += 1
            vals.append(parse_atom())
        return max(vals, key=RANK.get)

    def parse_atom():
        nonlocal pos
        if pos >= len(tokens):
            return "Blocked"
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            v = parse_or()
            if pos < len(tokens) and tokens[pos] == ")":
                pos += 1
            return v
        return classify_id(tok, policy)

    if not expr or expr.upper() in NO_LICENSE:
        return "Blocked"
    return parse_or()


# ---------------------------------------------------------------- registry lookups
def npm_license(name: str) -> str:
    d = http_json(f"https://registry.npmjs.org/{urllib.parse.quote(name, safe='@')}/latest") or {}
    lic = d.get("license")
    if isinstance(lic, dict):
        lic = lic.get("type")
    return lic or "NOASSERTION"


def pypi_license(name: str) -> str:
    d = (http_json(f"https://pypi.org/pypi/{name}/json") or {}).get("info") or {}
    if d.get("license_expression"):
        return d["license_expression"]
    lic = (d.get("license") or "").strip()
    if lic and len(lic) < 60 and "\n" not in lic:
        return lic
    cls = [c.split(" :: ")[-1] for c in d.get("classifiers", []) if c.startswith("License ::")]
    return cls[0] if cls else "NOASSERTION"


# ---------------------------------------------------------------- dependency sources
def from_sbom(owner: str, repo: str):
    d = http_json(f"https://api.github.com/repos/{owner}/{repo}/dependency-graph/sbom", github=True)
    if not d:
        return None
    pkgs = []
    for p in d["sbom"].get("packages", []):
        purl = next((r["referenceLocator"] for r in p.get("externalRefs", []) if r.get("referenceType") == "purl"), "")
        m = re.match(r"pkg:(\w+)/", purl)
        if not m:
            continue  # the repository itself
        eco = m.group(1)
        if eco == "githubactions":
            continue  # CI workflow actions: not shipped with the service, out of license-policy scope
        lic = p.get("licenseConcluded") or p.get("licenseDeclared") or "NOASSERTION"
        pkgs.append({"eco": eco, "name": p["name"].split(":")[-1], "version": p.get("versionInfo", ""), "license": lic, "source": "sbom"})
    return pkgs


def from_manifests(owner: str, repo: str, ref: str | None):
    def get(path):
        q = f"?ref={urllib.parse.quote(ref)}" if ref else ""
        d = http_json(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}{q}", github=True)
        return base64.b64decode(d["content"]).decode("utf-8", "replace") if d and "content" in d else None

    pkgs = []
    if (pj := get("package.json")):
        data = json.loads(pj)
        for sec in ("dependencies", "devDependencies"):
            for n, v in (data.get(sec) or {}).items():
                pkgs.append({"eco": "npm", "name": n, "version": v, "license": "NOASSERTION", "source": "manifest", "dev": sec == "devDependencies"})
    if (rq := get("requirements.txt")):
        for line in rq.splitlines():
            line = line.split("#")[0].strip()
            m = re.match(r"([A-Za-z0-9_.\-]+)(\[.*?\])?\s*(.*)", line)
            if m and line and not line.startswith("-"):
                pkgs.append({"eco": "pypi", "name": m.group(1), "version": m.group(3), "license": "NOASSERTION", "source": "manifest"})
    return pkgs


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--ref")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    m = re.match(r"(?:https?://github\.com/|git@github\.com:)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", a.url.strip())
    if not m:
        print(f"ERROR: not a GitHub repo URL: {a.url}", file=sys.stderr)
        return 3
    owner, repo = m.groups()
    policy, cache = load_policy(), load_cache()

    pkgs = None if a.ref else from_sbom(owner, repo)
    mode = "GitHub dependency-graph SBOM (direct + transitive)"
    if pkgs is None:
        pkgs = from_manifests(owner, repo, a.ref)
        mode = "root manifests via contents API (direct deps only; dependency graph unavailable)"
    if not pkgs:
        print(f"ERROR: no dependencies found for {owner}/{repo} (no SBOM and no package.json / requirements.txt)", file=sys.stderr)
        return 3

    misses = []
    for p in pkgs:
        if p["license"].upper() not in NO_LICENSE:
            continue
        hit = cache.get((p["eco"], p["name"].lower()))
        if hit:
            p["license"], p["source"] = hit[0], f"cache {hit[1]}"
        elif p["eco"] in ("npm", "pypi"):
            p["license"] = npm_license(p["name"]) if p["eco"] == "npm" else pypi_license(p["name"])
            p["source"] = f"{p['eco']} registry"
            misses.append(p)
    for p in pkgs:
        p["policy"] = evaluate(p["license"], policy)
        if p.get("dev") and p["policy"] == "Review Required":
            p["policy"] = "Allowed"
            p["note"] = "devDependency (test-only exception)"

    worst = max((p["policy"] for p in pkgs), key=RANK.get)
    verdict = {"Allowed": "PASS", "Review Required": "REVIEW REQUIRED", "Blocked": "BLOCK"}[worst]

    if a.json:
        print(json.dumps({"repo": f"{owner}/{repo}", "mode": mode, "verdict": verdict, "packages": pkgs, "cache_misses": [p["name"] for p in misses]}, ensure_ascii=False, indent=2))
    else:
        dist: dict[str, list] = {}
        for p in pkgs:
            dist.setdefault(p["license"], []).append(p)
        print("# OSS License Audit Report\n")
        print("## Overview")
        print(f"- Target: https://github.com/{owner}/{repo}{' @ ' + a.ref if a.ref else ''}")
        print(f"- Source: {mode}")
        print(f"- Libraries scanned: {len(pkgs)}")
        print(f"- Verdict: **{verdict}**\n")
        print("## Distribution")
        print("| License | Count | Policy |\n|---------|-------|--------|")
        for lic, ps in sorted(dist.items(), key=lambda kv: (-RANK[kv[1][0]["policy"]], -len(kv[1]))):
            print(f"| {lic} | {len(ps)} | {ps[0]['policy']} |")
        flagged = [p for p in pkgs if p["policy"] != "Allowed"]
        print("\n## Review Items")
        for p in sorted(flagged, key=lambda p: -RANK[p["policy"]]):
            print(f"- **{p['policy']}** — {p['eco']}:{p['name']} {p['version']} — `{p['license']}` ({p['source']})")
        if not flagged:
            print("- None")
        if misses:
            print(f"\n## Cache Misses ({len(misses)}) — verify, then append to known-licenses.md (date {date.today()})")
            for p in misses:
                print(f"- {p['eco']}:{p['name']} → `{p['license']}`")
    return {"PASS": 0, "REVIEW REQUIRED": 1, "BLOCK": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
