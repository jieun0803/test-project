#!/usr/bin/env python3
"""Register OSS governance findings as Jira issues (deduplicated).

Usage:
  # findings from another tool's --json output (auto-detected), file or stdin
  python3 scripts/oss/exception-review.py . --json | python3 scripts/oss/jira-issue.py --project KEY
  python3 scripts/oss/jira-issue.py --project KEY --from findings.json [--dry-run]

  # one finding
  python3 scripts/oss/jira-issue.py --project KEY --type license --package npm:readline-gpl \
      --item GPL-3.0-only --severity BLOCK --detail "Strong copyleft in a runtime dependency"

Accepted --json inputs: exception-review (pending + expired), review-diff (BLOCK / REVIEW),
license-scan (non-Allowed), audit-github-repo (non-Allowed), cve-triage (affected).

Each finding gets a fingerprint label `oss-fp-<hash>` (project + package/file + type + item).
An open issue with the same fingerprint is not created again; it is listed as "exists".
Priority: BLOCK / Blocked / CRITICAL -> Highest, HIGH -> High, REVIEW / Review Required -> Medium.

Credentials: JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN (env). Locally, falls back to the
`jira` server env in ~/.cursor/mcp.json. Project: --project or JIRA_PROJECT.
Exit code: 0 done (or dry run), 1 some creations failed, 3 error.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from oss_paths import safe_path  # CLI paths must stay inside the working directory

PRIORITY = {"BLOCK": "Highest", "BLOCKED": "Highest", "CRITICAL": "Highest", "HIGH": "High",
            "REVIEW": "Medium", "REVIEW REQUIRED": "Medium", "MEDIUM": "Medium", "LOW": "Low"}
LEVEL = {"BLOCK": 3, "BLOCKED": 3, "CRITICAL": 3, "HIGH": 2, "REVIEW": 1, "REVIEW REQUIRED": 1, "MEDIUM": 1, "LOW": 0}
TYPE_TAG = {"license": "License", "cve": "CVE", "code": "Code", "exception": "Exception"}


# ---------------------------------------------------------------- input normalization
def finding(type_: str, subject: str, item: str, severity: str, detail: str, action: str,
            location: str = "", fp_key: str | None = None) -> dict:
    return {"type": type_, "subject": subject, "item": item, "severity": severity.upper(),
            "detail": detail, "action": action, "location": location,
            "fp_key": fp_key or f"{subject}|{type_}|{item}"}


def normalize(data: dict) -> tuple[str, list[dict]]:
    out = []
    if "pending" in data and "approved" in data:  # exception-review
        for state, rows in (("pending", data["pending"]), ("expired", data.get("expired", []))):
            for r in rows:
                sev = r["detail"].split(" ")[0] if r["type"] == "cve" else r["policy"]
                act = ("Upgrade to a fixed version, or request an OSS Manager waiver with expiry" if r["type"] == "cve"
                       else "Replace the dependency, or request an OSS Manager exception (scope + expiry)")
                if state == "expired":
                    act = f"Exception {r['exception']['id']} expired {r['exception']['expires']}: re-approve or remove"
                out.append(finding(r["type"], r["pkg"], r["item"], sev, r["detail"], act))
        return "exception-review", out
    if "findings" in data and data["findings"] and "rule" in data["findings"][0]:  # review-diff
        for f in data["findings"]:
            if f["severity"] not in ("BLOCK", "REVIEW"):
                continue
            dep = re.match(r"(\S+) .*? — `(.+?)` →", f["message"]) if f["rule"] == "dependency-license" else None
            if dep:  # same subject / item as exception-review, so both tools share one issue per package
                out.append(finding("license", dep.group(1), dep.group(2), f["severity"], f["message"],
                                   "Replace the dependency, or request an OSS Manager exception (scope + expiry)",
                                   f"{f['file']}:{f['line']}"))
                continue
            out.append(finding("code", f["file"], f["rule"], f["severity"], f["message"],
                               "Fix before merge (see /code-review)", f"{f['file']}:{f['line']}",
                               fp_key=f"{f['file']}|{f['rule']}|{f.get('code') or f['message']}"))
        return "review-diff", out
    if "findings" in data and data["findings"] and "kind" in data["findings"][0]:  # license-scan
        for f in data["findings"]:
            if f["policy"] == "Allowed":
                continue
            near = ((f.get("similarity") or {}).get("closest") or [{}])[0]
            extra = f" · closest {near['spdx']} {near['similarity']}%" if near.get("spdx") else ""
            out.append(finding("license", f["file"], f["expression"], f["policy"],
                               f"{f['kind']} match, score {f['score']}{extra}",
                               "Legal review of the license text, or replace the component", f["file"]))
        return "license-scan", out
    if "packages" in data and "repo" in data:  # audit-github-repo
        for p in data["packages"]:
            if p["policy"] == "Allowed":
                continue
            out.append(finding("license", f"{p['eco']}:{p['name']}", p["license"], p["policy"],
                               f"{data['repo']} — {p['license']} ({p['source']})",
                               "Replace, or request an OSS Manager exception", data["repo"]))
        return "audit-github-repo", out
    if "cve" in data and "affected" in data:  # cve-triage
        for a in data["affected"]:
            out.append(finding("cve", f"{a['project']} · {a['package']}", data["cve"], data["severity"],
                               f"{data['summary']} — {a['project']} uses {a['version']} (fixed: {a.get('fixed') or 'none'})",
                               f"Upgrade to {a.get('fixed') or 'a fixed version'}; owner: {a.get('owner') or 'unassigned'}",
                               a["project"], fp_key=f"{a['project']}|{a['package']}|cve|{data['cve']}"))
        return "cve-triage", out
    raise ValueError("unrecognized --json input (expected exception-review / review-diff / license-scan / "
                     "audit-github-repo / cve-triage output)")


# ---------------------------------------------------------------- Jira REST
def credentials() -> tuple[str, str, str]:
    url, user, token = (os.environ.get(k) for k in ("JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"))
    if not (url and user and token):
        cfg = Path.home() / ".cursor" / "mcp.json"
        if cfg.exists():
            env = (json.loads(cfg.read_text()).get("mcpServers", {}).get("jira") or {}).get("env") or {}
            url, user, token = url or env.get("JIRA_URL"), user or env.get("JIRA_USERNAME"), token or env.get("JIRA_API_TOKEN")
    if not (url and user and token):
        raise RuntimeError("set JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN")
    return url.rstrip("/"), user, token


class Jira:
    def __init__(self):
        self.url, user, token = credentials()
        self.auth = "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode()

    def call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": self.auth, "Accept": "application/json",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Jira {method} {path.split('?')[0]}: HTTP {e.code} {e.read().decode()[:300]}")

    def find_open(self, project: str, label: str) -> str | None:
        jql = f'project = "{project}" AND labels = "{label}" AND statusCategory != Done ORDER BY created DESC'
        r = self.call("POST", "/rest/api/3/search/jql", {"jql": jql, "maxResults": 1, "fields": ["key"]})
        issues = r.get("issues") or []
        return issues[0]["key"] if issues else None

    def create(self, fields: dict) -> str:
        return self.call("POST", "/rest/api/2/issue", {"fields": fields})["key"]


# ---------------------------------------------------------------- main
def build_issue(f: dict, project: str, issue_type: str, extra_labels: list[str], source: str) -> dict:
    fp = "oss-fp-" + hashlib.sha1(f"{project}|{f['fp_key']}".encode()).hexdigest()[:12]
    sev = f["severity"]
    summary = f"[OSS][{TYPE_TAG.get(f['type'], f['type'])}] {f['subject']} — {f['item']} ({ {"BLOCK": "Blocked", "REVIEW": "Review Required"}.get(sev, sev.title()) })"
    sections = [
        ("발견 내용", [f"대상: {{c}}{f['subject']}{{/c}}", f"항목: {{c}}{f['item']}{{/c}}", f"심각도 / 정책: {{b}}{sev}{{/b}}",
                     f"상세: {f['detail']}", *([f"위치: {{c}}{f['location']}{{/c}}"] if f["location"] else [])]),
        ("조치", [f["action"], "예외가 필요하면 OSS Manager 승인 후 등록부에 기록: {c}.cursor/oss-exceptions.md{/c}"]),
        ("근거", ["정책: {c}.cursor/oss-policy.md{/c}", f"출처: {{c}}scripts/oss/{source}{{/c}}",
                f"Fingerprint: {{c}}{fp}{{/c}} (같은 값의 열린 이슈가 있으면 다시 만들지 않음)"]),
    ]

    def render(md: bool) -> str:
        c0, c1, b0, b1, h = ("`", "`", "**", "**", "### ") if md else ("{{", "}}", "*", "*", "h3. ")
        lines = []
        for title, items in sections:
            lines += [f"{h}{title}"] + [("- " if md else "* ") + t.replace("{c}", c0).replace("{/c}", c1)
                                        .replace("{b}", b0).replace("{/b}", b1) for t in items] + [""]
        return "\n".join(lines).strip()
    desc = render(md=False)
    return {"fp": fp, "summary": summary[:250], "description_markdown": render(md=True), "fields": {
        "project": {"key": project}, "issuetype": {"name": issue_type}, "summary": summary[:250],
        "description": desc, "priority": {"name": PRIORITY.get(sev, "Medium")},
        "labels": sorted({"oss-governance", f"oss-{f['type']}", fp, *extra_labels})}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=os.environ.get("JIRA_PROJECT"))
    ap.add_argument("--issue-type", default=os.environ.get("JIRA_ISSUE_TYPE", "Task"))
    ap.add_argument("--from", dest="src", help="--json output file of an OSS tool ('-' = stdin)")
    ap.add_argument("--type", choices=sorted(TYPE_TAG))
    ap.add_argument("--package", help="subject: package (eco:name) or file")
    ap.add_argument("--item", help="license expression, CVE id or rule")
    ap.add_argument("--severity", default="REVIEW")
    ap.add_argument("--detail", default="")
    ap.add_argument("--action", default="Review with the OSS Manager")
    ap.add_argument("--min-severity", choices=["review", "high", "block"], default="review",
                    help="register only findings at or above this level (automation: block)")
    ap.add_argument("--label", action="append", default=[], help="extra label (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be created, no Jira calls")
    ap.add_argument("--json", action="store_true", help="with --dry-run: print the issue payloads (for the Jira MCP)")
    a = ap.parse_args()

    if not a.project:
        print("error: --project (or JIRA_PROJECT) is required", file=sys.stderr)
        return 3
    try:
        if a.package:
            if not (a.type and a.item):
                raise ValueError("--package needs --type and --item")
            source, items = "jira-issue.py", [finding(a.type, a.package, a.item, a.severity, a.detail, a.action)]
        else:
            raw = sys.stdin.read() if a.src in (None, "-") else safe_path(a.src, "--from").read_text(encoding="utf-8")
            source, items = normalize(json.loads(raw))
            source += ".py"
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 3

    floor = {"review": 1, "high": 2, "block": 3}[a.min_severity]
    skipped = [f for f in items if LEVEL.get(f["severity"], 1) < floor]
    items = [f for f in items if LEVEL.get(f["severity"], 1) >= floor]
    issues = [build_issue(f, a.project, a.issue_type, a.label, source) for f in items]
    if a.dry_run and a.json:
        print(json.dumps([{"fingerprint": i["fp"], "dedupe_jql": f'project = "{a.project}" AND labels = "{i["fp"]}" '
                           "AND statusCategory != Done", **i["fields"],
                           "description_markdown": i["description_markdown"]} for i in issues], ensure_ascii=False, indent=2))
        return 0
    print(f"# Jira Registration ({source}) — {len(issues)} finding(s), project {a.project}"
          f"{' [dry run]' if a.dry_run else ''}"
          + (f" · {len(skipped)} below --min-severity {a.min_severity} skipped" if skipped else "") + "\n")
    if not issues:
        print("- Nothing to register")
        return 0
    if a.dry_run:
        for i in issues:
            print(f"- would create [{i['fields']['priority']['name']}] {i['summary']}  ({i['fp']})")
        return 0
    try:
        jira = Jira()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    failed = 0
    for i in issues:
        try:
            existing = jira.find_open(a.project, i["fp"])
            if existing:
                print(f"- exists  {existing}  {i['summary']}")
                continue
            key = jira.create(i["fields"])
            print(f"- created {key}  [{i['fields']['priority']['name']}] {i['summary']}  {jira.url}/browse/{key}")
        except RuntimeError as e:
            failed += 1
            print(f"- FAILED  {i['summary']}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
