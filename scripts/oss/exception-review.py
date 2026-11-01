#!/usr/bin/env python3
"""Governance assistant: list items that need OSS Manager exception approval.

Usage:
  python3 scripts/oss/exception-review.py [PROJECT_DIR] [--register FILE] [--no-cve] [--json]

Collects, for package.json / requirements.txt in PROJECT_DIR (default .):
  - license items: Blocked or Review Required under .cursor/oss-policy.md
    (license from known-licenses.md, then npm / PyPI registry)
  - CVE items: CRITICAL or HIGH advisories from the OSV API for the declared version
and matches them against the exception register (.cursor/oss-exceptions.md):
  Pending approval · Approved (valid) · Expired · Stale (exception no longer needed).

Exit code: 0 nothing pending or expired, 1 items need OSS Manager action, 3 error.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from oss_paths import OutsideWorkspace, safe_path  # CLI paths must stay inside the working directory

_spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("audit-github-repo.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

REGISTER = audit.ROOT / ".cursor" / "oss-exceptions.md"
OSV_ECO = {"npm": "npm", "pypi": "PyPI"}


# ---------------------------------------------------------------- inputs
def read_manifests(d: Path) -> list[dict]:
    pkgs = []
    pj = d / "package.json"
    if pj.exists():
        data = json.loads(pj.read_text(encoding="utf-8"))
        for sec in ("dependencies", "devDependencies"):
            for n, v in (data.get(sec) or {}).items():
                pkgs.append({"eco": "npm", "name": n, "spec": v, "dev": sec == "devDependencies"})
    rq = d / "requirements.txt"
    if rq.exists():
        for line in rq.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            m = re.match(r"([A-Za-z0-9_.\-]+)(\[.*?\])?\s*(.*)", line)
            if m and line and not line.startswith("-"):
                pkgs.append({"eco": "pypi", "name": m.group(1), "spec": m.group(3).strip(), "dev": False})
    return pkgs


def pinned_version(spec: str) -> tuple[str | None, bool]:
    """Version to query OSV with, and whether it is exact. '^4.17.15' -> ('4.17.15', False)."""
    m = re.search(r"\d+(?:\.\d+)*(?:[-.]?[A-Za-z0-9]+)*", spec or "")
    if not m:
        return None, False
    exact = bool(re.fullmatch(r"\s*(==|=)?\s*v?\d[\w.\-]*\s*", spec))
    return m.group(0), exact


def load_register(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("| ID") or line.startswith("|--"):
            continue
        c = [x.strip() for x in line.strip("|").split("|")]
        if len(c) >= 8 and c[0]:
            rows.append({"id": c[0], "pkg": c[1].lower(), "type": c[2].lower(), "item": c[3],
                         "by": c[4], "approved": c[5], "expires": c[6], "reason": c[7]})
    return rows


# ---------------------------------------------------------------- CVE lookup
def osv_post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def severity(v: dict) -> str:
    s = (v.get("database_specific") or {}).get("severity", "")
    if s:
        return {"MODERATE": "MEDIUM"}.get(s.upper(), s.upper())
    for sev in v.get("severity", []):  # CVSS vector only -> approximate from base score if present
        m = re.search(r"/score:([\d.]+)", sev.get("score", ""))
        if m:
            x = float(m.group(1))
            return "CRITICAL" if x >= 9 else "HIGH" if x >= 7 else "MEDIUM" if x >= 4 else "LOW"
    return "UNKNOWN"


def cve_items(pkgs: list[dict]) -> list[dict]:
    queries, owners = [], []
    for p in pkgs:
        ver, exact = pinned_version(p["spec"])
        if ver and p["eco"] in OSV_ECO:
            queries.append({"package": {"name": p["name"], "ecosystem": OSV_ECO[p["eco"]]}, "version": ver})
            owners.append((p, ver, exact))
    if not queries:
        return []
    res = osv_post("https://api.osv.dev/v1/querybatch", {"queries": queries})["results"]
    items, details = [], {}
    for (p, ver, exact), r in zip(owners, res):
        for v in r.get("vulns", []):
            vid = v["id"]
            if vid not in details:
                details[vid] = audit.http_json(f"https://api.osv.dev/v1/vulns/{vid}") or {}
            d = details[vid]
            sev = severity(d)
            if sev not in ("CRITICAL", "HIGH"):
                continue
            cve = next((a for a in d.get("aliases", []) if a.startswith("CVE-")), vid)
            items.append({"pkg": f"{p['eco']}:{p['name'].lower()}", "type": "cve", "item": cve, "ids": {vid, cve},
                          "detail": f"{sev} — {d.get('summary', '').strip()[:80]} (version {ver}"
                                    f"{'' if exact else ', lower bound of ' + p['spec']})",
                          "policy": "Blocked" if sev == "CRITICAL" else "Review Required",
                          "exact": exact, "sev": sev, "spec": p["spec"]})
    return items


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--register", help=f"exception register (default: {REGISTER})")
    ap.add_argument("--no-cve", action="store_true", help="skip the OSV lookup")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        d = safe_path(a.project, "project")
        register_path = safe_path(a.register, "--register") if a.register else REGISTER
    except OutsideWorkspace as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    pkgs = read_manifests(d)
    if not pkgs:
        print(f"error: no package.json or requirements.txt in {d}", file=sys.stderr)
        return 3
    policy, cache = audit.load_policy(), audit.load_cache()

    items = []
    for p in pkgs:
        hit = cache.get((p["eco"], p["name"].lower()))
        if hit:
            lic, src = hit[0], f"known-licenses.md {hit[1]}"
        else:
            lic = audit.npm_license(p["name"]) if p["eco"] == "npm" else audit.pypi_license(p["name"])
            src = f"{p['eco']} registry (cache miss)"
        pol = audit.evaluate(lic, policy)
        if p["dev"] and pol == "Review Required":
            continue  # policy: weak copyleft allowed in devDependencies (test-only exception)
        if pol != "Allowed":
            items.append({"pkg": f"{p['eco']}:{p['name'].lower()}", "type": "license", "item": lic, "ids": {lic},
                          "detail": f"{pol} ({src})", "policy": pol})
    unpinned: dict[str, dict] = {}
    if not a.no_cve:
        for it in cve_items(pkgs):
            if it["exact"]:
                items.append(it)
                continue
            # range spec (e.g. >=3.8.0): CVEs apply to the lower bound only, not necessarily to what is
            # installed. Not an exception item: pin to a fixed version first, then re-run.
            u = unpinned.setdefault(it["pkg"], {"spec": it["spec"], "critical": 0, "high": 0})
            u["critical" if it["sev"] == "CRITICAL" else "high"] += 1

    register = load_register(register_path)
    today = date.today().isoformat()
    pending, approved, expired = [], [], []
    used = set()
    for it in items:
        ex = next((r for r in register if r["pkg"] == it["pkg"] and r["type"] == it["type"]
                   and r["item"] in it["ids"]), None)
        if ex is None:
            pending.append(it)
            continue
        used.add(ex["id"])
        it["exception"] = ex
        (approved if ex["expires"] >= today else expired).append(it)
    stale = [r for r in register if r["id"] not in used]

    if a.json:
        clean = lambda xs: [{k: v for k, v in x.items() if k != "ids"} for x in xs]
        print(json.dumps({"pending": clean(pending), "approved": clean(approved), "expired": clean(expired),
                          "stale": stale, "unpinned": unpinned}, ensure_ascii=False, indent=2))
    else:
        rank = lambda it: (-audit.RANK[it["policy"]], it["type"], it["pkg"])
        print("# OSS Exception Review\n")
        print(f"- Project: {d.resolve()}")
        print(f"- Register: {register_path} ({len(register)} entries)")
        print(f"- Dependencies: {len(pkgs)} · CVE lookup: {'off' if a.no_cve else 'OSV API'}")
        print(f"- Pending approval {len(pending)} · Expired {len(expired)} · Approved {len(approved)} · "
              f"Stale {len(stale)} · Unpinned {len(unpinned)}\n")
        print("## Pending OSS Manager Approval")
        if pending:
            print("| Package | Type | Item | Detail | Options |\n|---|---|---|---|---|")
            for it in sorted(pending, key=rank):
                opt = ("upgrade to a fixed version, or waive with expiry" if it["type"] == "cve"
                       else "replace, or approve exception with scope + expiry" if it["policy"] == "Blocked"
                       else "confirm SaaS / unmodified use, then approve")
                print(f"| {it['pkg']} | {it['type']} | `{it['item']}` | {it['detail']} | {opt} |")
        else:
            print("- None")
        print("\n## Expired — re-review")
        print("\n".join(f"- {it['pkg']} `{it['item']}` — {it['exception']['id']} expired {it['exception']['expires']}"
                        for it in expired) or "- None")
        print("\n## Approved (valid)")
        print("\n".join(f"- {it['pkg']} `{it['item']}` — {it['exception']['id']} by {it['exception']['by']}, "
                        f"until {it['exception']['expires']}" for it in approved) or "- None")
        print("\n## Unpinned — pin a fixed version, then re-run (not an exception item yet)")
        print("\n".join(f"- {k} `{u['spec']}` — lower bound has {u['critical']} CRITICAL / {u['high']} HIGH advisories"
                        for k, u in sorted(unpinned.items(), key=lambda kv: (-kv[1]['critical'], -kv[1]['high'])))
              or "- None")
        print("\n## Stale — exception no longer needed, close it")
        print("\n".join(f"- {r['id']} {r['pkg']} `{r['item']}`" for r in stale) or "- None")
    return 1 if pending or expired else 0


if __name__ == "__main__":
    sys.exit(main())
