#!/usr/bin/env python3
"""OSS governance review of a git diff (backs the /code-review skill).

Usage:
  python3 scripts/oss/review-diff.py [--base REF] [--repo DIR] [--json]

Diff scope: --base REF -> REF...HEAD plus working tree; default -> HEAD vs. working tree
(staged + unstaged). Untracked files are included.

Checks on added lines only:
  1. Dependency changes in package.json / requirements.txt -> license + policy
     (known-licenses.md, then npm / PyPI registry; .cursor/oss-policy.md)
  2. Blocked code patterns from oss-policy.md (credentials, SQL concatenation,
     weak crypto, disabled TLS verification, eval / exec)
  3. Copied third-party code markers (SPDX / Copyright headers, "copied from" URLs)

Exit code: 0 no findings, 1 findings to review, 2 blocking findings, 3 error.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("audit-github-repo.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rb", ".php", ".swift", ".cs", ".rs"}

# (rule id, severity, regex on an added line, message)
PATTERNS = [
    ("hardcoded-credential", "BLOCK",
     r"""(?i)\w*(pass(word|wd)?|secret|api[_-]?key|access[_-]?key|token|private[_-]?key)\w*["']?\s*[:=]\s*["'][^"'\s]{6,}["']""",
     "Hardcoded credential. Load it from env / secret manager"),
    ("hardcoded-credential", "BLOCK", r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
     "Secret token / private key literal"),
    ("sql-concat", "BLOCK",
     r"""(?i)("[^"]*\b(select|insert|update|delete)\b[^"]*"|'[^']*\b(select|insert|update|delete)\b[^']*')\s*(\+|%\s*\(?\w|\.format\()"""
     r"""|\bf("[^"]*|'[^']*)\b(select|insert|update|delete)\b[^"']*\{""",
     "SQL built by string concatenation / formatting. Use parameterized queries"),
    ("weak-crypto", "BLOCK", r"(?i)\b(md5|sha1)\s*\(|hashlib\.(md5|sha1)\b|createHash\(\s*['\"](md5|sha1)['\"]|\bDES\b|\bRC4\b|MODE_ECB|/ECB/",
     "Weak cryptography (MD5 / SHA1 / DES / RC4 / ECB)"),
    ("tls-verify-disabled", "BLOCK",
     r"(?i)verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|InsecureSkipVerify\s*:\s*true|CERT_NONE",
     "TLS certificate validation disabled"),
    ("eval-exec", "REVIEW", r"(?<![\w.])(eval|exec)\s*\(|new Function\s*\(",
     "eval / exec: make sure the input is never user-controlled"),
]
COPIED = [
    (r"SPDX-License-Identifier:\s*([\w.\-+ ()]+)", "SPDX header — check the license against policy and keep the header"),
    (r"(?i)copyright\s+(\(c\)\s*)?\d{4}", "Copyright notice — third-party code? Keep the header, add to NOTICE"),
    (r"(?i)(copied|adapted|taken|ported)\s+from\s+\S+|stackoverflow\.com/(a|questions)/",
     "Copied code — record the source and its license (Stack Overflow = CC BY-SA)"),
]


REMOVED: dict[str, set[str]] = {}  # file -> removed lines (normalized), filled by added_lines()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def added_lines(repo: Path, base: str | None) -> dict[str, list[tuple[int, str]]]:
    diff = git(repo, "diff", "--unified=0", "--no-color", *([f"{base}...HEAD"] if base else ["HEAD"]))
    if base:  # plus uncommitted work on top of HEAD
        diff += git(repo, "diff", "--unified=0", "--no-color", "HEAD")
    out: dict[str, list[tuple[int, str]]] = {}
    path, ln, old_path = None, 0, None
    for line in diff.splitlines():
        if line.startswith("--- "):
            old_path = None if line[4:] == "/dev/null" else line[6:]
        elif old_path and line.startswith("-"):
            REMOVED.setdefault(old_path, set()).add(line[1:].strip().rstrip(","))
        if line.startswith("+++ "):
            path = None if line[4:] == "/dev/null" else line[6:]
        elif line.startswith("@@"):
            ln = int(re.search(r"\+(\d+)", line).group(1))
        elif path and line.startswith("+"):
            out.setdefault(path, []).append((ln, line[1:]))
            ln += 1
    for f in git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        try:
            text = (repo / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        out[f] = list(enumerate(text.splitlines(), 1))
    return out


def dep_changes(path: str, lines: list[tuple[int, str]]) -> list[dict]:
    name = Path(path).name
    deps = []
    for ln, text in lines:
        if text.strip().rstrip(",") in REMOVED.get(path, set()):
            continue  # same entry, only reformatted (e.g. trailing comma added)
        if name == "package.json":
            m = re.match(r'\s*"(@?[\w.\-/]+)"\s*:\s*"([^"]*)"', text)
            if m and not m.group(1).startswith(("name", "version", "description", "main", "license", "_")) \
                    and re.match(r"[\^~<>=*\d]|latest|npm:|git", m.group(2)):
                deps.append({"eco": "npm", "name": m.group(1), "spec": m.group(2), "line": ln})
        elif name.startswith("requirements") and name.endswith(".txt"):
            t = text.split("#")[0].strip()
            m = re.match(r"([A-Za-z0-9_.\-]+)(\[.*?\])?\s*(.*)", t)
            if m and t and not t.startswith("-"):
                deps.append({"eco": "pypi", "name": m.group(1), "spec": m.group(3), "line": ln})
    return deps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    try:
        files = added_lines(repo, a.base)
    except subprocess.CalledProcessError as e:
        msg = next((l for l in e.stderr.splitlines() if l.strip()), "git failed")
        print(f"error: {msg.removeprefix('warning: ')} ({repo})", file=sys.stderr)
        return 3

    policy, cache = audit.load_policy(), audit.load_cache()
    findings = []
    for path, lines in sorted(files.items()):
        for d in dep_changes(path, lines):
            hit = cache.get((d["eco"], d["name"].lower()))
            if hit:
                lic, src = hit[0], f"known-licenses.md {hit[1]}"
            else:
                lic = audit.npm_license(d["name"]) if d["eco"] == "npm" else audit.pypi_license(d["name"])
                src = f"{d['eco']} registry"
            pol = audit.evaluate(lic, policy)
            sev = {"Allowed": "INFO", "Review Required": "REVIEW", "Blocked": "BLOCK"}[pol]
            findings.append({"file": path, "line": d["line"], "rule": "dependency-license", "severity": sev,
                             "message": f"{d['eco']}:{d['name']} {d['spec']} — `{lic}` → {pol} ({src})"})
        if path.endswith((".md", ".lock")) or "oss-fixtures" in path or path.startswith("scripts/oss/review-diff"):
            continue  # docs, lockfiles, test fixtures, and this rule file itself
        is_code = Path(path).suffix in CODE_EXT
        for ln, text in lines:
            if is_code:
                seen = set()
                for rule, sev, rx, msg in PATTERNS:
                    if rule not in seen and re.search(rx, text):
                        seen.add(rule)
                        findings.append({"file": path, "line": ln, "rule": rule, "severity": sev, "message": msg,
                                         "code": text.strip()[:120]})
            for rx, msg in COPIED:
                if re.search(rx, text):
                    findings.append({"file": path, "line": ln, "rule": "copied-code", "severity": "REVIEW",
                                     "message": msg, "code": text.strip()[:120]})

    deps_changed = any(f["rule"] == "dependency-license" for f in findings)
    order = {"BLOCK": 0, "REVIEW": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["file"], f["line"]))
    verdict = "BLOCK" if any(f["severity"] == "BLOCK" for f in findings) else \
        "REVIEW REQUIRED" if any(f["severity"] == "REVIEW" for f in findings) else "PASS"

    if a.json:
        print(json.dumps({"verdict": verdict, "files": len(files), "findings": findings}, ensure_ascii=False, indent=2))
    else:
        print("# OSS Code Review\n")
        print(f"- Scope: {a.base + '...HEAD + ' if a.base else ''}working tree vs. HEAD · {len(files)} files changed")
        print(f"- Verdict: **{verdict}**\n")
        print("## Findings")
        if not findings:
            print("- None")
        for f in findings:
            print(f"- **{f['severity']}** `{f['file']}:{f['line']}` [{f['rule']}] {f['message']}")
            if f.get("code"):
                print(f"  `{f['code']}`")
        if deps_changed:
            print("\n## Reminders\n- [ ] Dependencies changed: update NOTICE (oss-notice-writer) and regenerate the SBOM")
    return {"PASS": 0, "REVIEW REQUIRED": 1, "BLOCK": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
