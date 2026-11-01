#!/usr/bin/env python3
"""Generate a CycloneDX 1.4 SBOM for an iOS project (no Xcode needed).

Usage:
  python3 scripts/oss/sbom-ios.py [PROJECT_DIR] [-o bom-ios.json] [--no-licenses] [--validate]

Sources (all that exist are merged):
  - Podfile.lock                     CocoaPods  -> pkg:cocoapods/<Pod>@<version>  (subspecs folded into the pod)
  - Package.resolved (v1, v2, v3)    SwiftPM    -> pkg:swift/<host>/<owner>/<repo>@<version>
    (also inside *.xcodeproj / *.xcworkspace)
  - Cartfile.resolved                Carthage   -> pkg:github/<owner>/<repo>@<version>
Licenses (unless --no-licenses): CocoaPods trunk podspec `license`, else / for SwiftPM and Carthage
the GitHub repo license (GITHUB_TOKEN or `gh auth token`). Unknown stays without a license entry.
Dependency graph: from Podfile.lock nesting; DEPENDENCIES / SwiftPM / Carthage entries are direct.
--validate checks the output against the CycloneDX 1.4 JSON schema (needs cyclonedx-python-lib).

Exit code: 0 SBOM written, 1 no iOS dependency file found, 3 error.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import urllib.error
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from oss_paths import OutsideWorkspace, safe_path  # CLI paths must stay inside the working directory

_spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("audit-github-repo.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

SKIP_DIRS = {"Pods", ".build", "Carthage", "DerivedData", "node_modules", ".git"}
SPDX_ALIASES = {
    "mit": "MIT", "the mit license": "MIT", "mit license": "MIT",
    "apache": "Apache-2.0", "apache 2": "Apache-2.0", "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0", "apache license 2.0": "Apache-2.0", "apache2": "Apache-2.0",
    "bsd": None, "bsd-2-clause": "BSD-2-Clause", "bsd-3-clause": "BSD-3-Clause", "bsd 3-clause": "BSD-3-Clause",
    "isc": "ISC", "zlib": "Zlib", "mpl-2.0": "MPL-2.0", "mpl 2.0": "MPL-2.0", "unlicense": "Unlicense",
    "gpl-2.0": "GPL-2.0-only", "gpl-3.0": "GPL-3.0-only", "gpl v3": "GPL-3.0-only", "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-3.0": "LGPL-3.0-only", "0bsd": "0BSD", "cc0-1.0": "CC0-1.0",
}


# ---------------------------------------------------------------- parsers
def parse_podfile_lock(path: Path) -> tuple[list[dict], dict[str, set], set]:
    """Components, pod-level dependency edges, direct pod names."""
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^(?=[A-Z][A-Z ]+:\s*$)", text, flags=re.M)
    get = lambda name: next((s for s in sections if s.startswith(name + ":")), "")
    pods: dict[str, str] = {}
    edges: dict[str, set] = {}
    current = None
    for line in get("PODS").splitlines()[1:]:
        m = re.match(r"^  - \"?([^\s\"(]+) \(([^)]+)\)\"?:?\s*$", line)
        if m:
            current = m.group(1).split("/")[0]
            pods[current] = m.group(2)
            edges.setdefault(current, set())
            continue
        d = re.match(r"^    - \"?([^\s\"(]+)", line)
        if d and current:
            dep = d.group(1).split("/")[0]
            if dep != current:
                edges[current].add(dep)
    direct = {re.match(r"^  - \"?([^\s\"(]+)", l).group(1).split("/")[0]
              for l in get("DEPENDENCIES").splitlines()[1:] if re.match(r"^  - ", l)}
    git = {}
    for sec in ("EXTERNAL SOURCES", "CHECKOUT OPTIONS"):
        cur = None
        for line in get(sec).splitlines()[1:]:
            if re.match(r"^  \S", line):
                cur = line.strip().rstrip(":").strip('"')
            elif cur and ":git:" in line:
                git[cur.split("/")[0]] = line.split(":git:")[1].strip()
    comps = [{"ecosystem": "cocoapods", "name": n, "version": v, "purl": f"pkg:cocoapods/{n}@{v}",
              "vcs": git.get(n), "source": path.name} for n, v in sorted(pods.items())]
    return comps, edges, direct


def repo_purl(url: str, kind: str) -> tuple[str, str, str]:
    """(purl-path, display name, https url) from a git URL."""
    u = re.sub(r"\.git$", "", url.strip().rstrip("/"))
    u = re.sub(r"^git@([^:]+):", r"https://\1/", u)
    p = urllib.parse.urlparse(u if "://" in u else "https://" + u)
    parts = p.path.strip("/").split("/")
    owner, repo = (parts + ["", ""])[:2]
    path = f"{p.netloc}/{owner}/{repo}" if kind == "swift" else f"{owner}/{repo}"
    return path, repo, f"https://{p.netloc}/{owner}/{repo}"


def parse_package_resolved(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pins = data.get("pins") or (data.get("object") or {}).get("pins") or []
    out = []
    for p in pins:
        url = p.get("location") or p.get("repositoryURL") or ""
        st = p.get("state") or {}
        ver = st.get("version") or st.get("branch") or (st.get("revision") or "")[:12]
        ppath, name, https = repo_purl(url, "swift")
        out.append({"ecosystem": "swift", "name": p.get("package") or name, "version": ver,
                    "purl": f"pkg:swift/{ppath}@{ver}", "vcs": https, "source": str(path.name)})
    return out


def parse_cartfile_resolved(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^(github|git|binary)\s+"([^"]+)"\s+"([^"]+)"', line.strip())
        if not m:
            continue
        kind, src, ver = m.groups()
        url = f"https://github.com/{src}" if kind == "github" else src
        ppath, name, https = repo_purl(url, "github")
        out.append({"ecosystem": "carthage", "name": name, "version": ver,
                    "purl": f"pkg:github/{ppath}@{ver}" if kind == "github" else f"pkg:generic/{name}@{ver}",
                    "vcs": https if kind != "binary" else None, "source": path.name})
    return out


def find(d: Path, name: str) -> list[Path]:
    hits = []
    for p in d.rglob(name):
        if not SKIP_DIRS & set(p.relative_to(d).parts[:-1]):
            hits.append(p)
    return sorted(hits)


# ---------------------------------------------------------------- licenses
def to_spdx(raw) -> tuple[str | None, str | None]:
    """(spdx id, free-text name) from a podspec / GitHub license value."""
    if isinstance(raw, dict):
        if (raw.get("type") or "").lower() in ("copyright", "commercial", "proprietary") and raw.get("text"):
            return None, f"{raw['type']}: {' '.join(raw['text'].split())[:120]}"  # closed-source vendor SDK
        raw = raw.get("type") or ""
    raw = (raw or "").strip()
    if not raw or raw.upper() in ("NOASSERTION", "OTHER"):
        return None, None
    key = raw.lower()
    if key in SPDX_ALIASES:
        return SPDX_ALIASES[key], (raw if SPDX_ALIASES[key] is None else None)
    if re.fullmatch(r"[A-Za-z0-9.+-]+", raw) and any(ch.isdigit() for ch in raw) or raw in ("MIT", "ISC", "Zlib"):
        return raw, None
    return None, raw


def github_license(https: str | None) -> str | None:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)", https or "")
    if not m:
        return None
    d = audit.http_json(f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}/license", github=True)
    return ((d or {}).get("license") or {}).get("spdx_id")


def pod_license(name: str, version: str) -> tuple[object, str | None]:
    """(license value, git url) from the CocoaPods trunk podspec (302 -> raw GitHub podspec JSON)."""
    try:
        spec = audit.http_json(f"https://trunk.cocoapods.org/api/v1/pods/{urllib.parse.quote(name)}/specs/{version}") or {}
    except (urllib.error.URLError, json.JSONDecodeError):
        spec = {}
    return spec.get("license"), (spec.get("source") or {}).get("git")


def fill_licenses(comps: list[dict]) -> None:
    for c in comps:
        lic, src = None, None
        if c["ecosystem"] == "cocoapods":
            raw, git = pod_license(c["name"], c["version"])
            c["vcs"] = c["vcs"] or (re.sub(r"\.git$", "", git) if git else None)
            spdx, text = to_spdx(raw)
            lic, src = (spdx, "podspec") if spdx else (None, None)
            c["license_name"] = text
        if not lic and c.get("vcs"):
            gh = github_license(c["vcs"])
            spdx, text = to_spdx(gh)
            if spdx:
                lic, src = spdx, "github"
        c["license"], c["license_source"] = lic, src


# ---------------------------------------------------------------- CycloneDX 1.4
def to_cyclonedx(project: str, comps: list[dict], edges: dict[str, set], direct: set) -> dict:
    by_pod = {c["name"]: c["purl"] for c in comps if c["ecosystem"] == "cocoapods"}
    root_ref = f"app:{project}"
    out_comps = []
    for c in comps:
        e = {"type": "library", "bom-ref": c["purl"], "name": c["name"], "version": c["version"], "purl": c["purl"]}
        if c.get("license"):
            e["licenses"] = [{"license": {"id": c["license"]}}]
        elif c.get("license_name"):
            e["licenses"] = [{"license": {"name": c["license_name"]}}]
        if c.get("vcs"):
            e["externalReferences"] = [{"type": "vcs", "url": c["vcs"]}]
        e["properties"] = [{"name": "oss:source", "value": c["source"]}] + (
            [{"name": "oss:license-source", "value": c["license_source"]}] if c.get("license_source") else [])
        out_comps.append(e)
    roots = [by_pod[n] for n in sorted(direct) if n in by_pod] + \
            [c["purl"] for c in comps if c["ecosystem"] != "cocoapods"]
    deps = [{"ref": root_ref, "dependsOn": roots}]
    deps += [{"ref": by_pod[n], "dependsOn": sorted(by_pod[x] for x in edges.get(n, ()) if x in by_pod)} for n in sorted(by_pod)]
    deps += [{"ref": c["purl"], "dependsOn": []} for c in comps if c["ecosystem"] != "cocoapods"]
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.4", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
        "metadata": {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "tools": [{"vendor": "oss-governance", "name": "sbom-ios.py", "version": "1.0.0"}],
                     "component": {"type": "application", "bom-ref": root_ref, "name": project}},
        "components": out_comps, "dependencies": deps,
    }


def validate(path: Path) -> str:
    try:
        from cyclonedx.schema import SchemaVersion
        from cyclonedx.validation.json import JsonStrictValidator
    except ImportError:
        return "skipped (pip install cyclonedx-python-lib to validate)"
    err = JsonStrictValidator(SchemaVersion.V1_4).validate_str(path.read_text(encoding="utf-8"))
    return f"FAILED: {err}" if err else "valid CycloneDX 1.4"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("-o", "--output")
    ap.add_argument("--no-licenses", action="store_true", help="skip registry / GitHub license lookups")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    try:
        d = safe_path(a.project, "project")
        out = safe_path(a.output, "--output") if a.output else d / "bom-ios.json"
    except OutsideWorkspace as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    if not d.is_dir():
        print(f"error: {a.project} is not a directory", file=sys.stderr)
        return 3

    comps, edges, direct, used = [], {}, set(), []
    for f in find(d, "Podfile.lock"):
        c, e, dr = parse_podfile_lock(f)
        comps += c; edges.update(e); direct |= dr; used.append(f)
    seen = set()
    for f in find(d, "Package.resolved"):
        for c in parse_package_resolved(f):
            if c["purl"] not in seen:
                seen.add(c["purl"]); comps.append(c)
        used.append(f)
    for f in find(d, "Cartfile.resolved"):
        comps += parse_cartfile_resolved(f); used.append(f)
    if not used:
        print(f"error: no Podfile.lock / Package.resolved / Cartfile.resolved under {d}", file=sys.stderr)
        return 1

    if not a.no_licenses:
        fill_licenses(comps)
    bom = json.dumps(to_cyclonedx(d.name, comps, edges, direct), indent=2) + "\n"
    with open(out, "w", encoding="utf-8") as fh:  # out: checked by safe_path(); bom: JSON text, not a path
        fh.write(bom)

    eco = {}
    for c in comps:
        eco[c["ecosystem"]] = eco.get(c["ecosystem"], 0) + 1
    print(f"Sources: {', '.join(str(f.relative_to(d)) for f in used)}")
    print(f"SBOM: {out} (CycloneDX 1.4, {len(comps)} components: "
          + ", ".join(f"{k} {v}" for k, v in sorted(eco.items())) + ")")
    if not a.no_licenses:
        missing = [c["name"] for c in comps if not c.get("license")]
        print(f"Licenses: {len(comps) - len(missing)}/{len(comps)} resolved"
              + (f" · unresolved: {', '.join(missing)}" if missing else ""))
    if a.validate:
        res = validate(out)
        print(f"Schema: {res}")
        if res.startswith("FAILED"):
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
