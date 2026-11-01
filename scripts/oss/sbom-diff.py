#!/usr/bin/env python3
"""Compare two CycloneDX JSON SBOMs and flag new license risk.

Usage:
  python3 scripts/oss/sbom-diff.py OLD_BOM.json NEW_BOM.json [--json]

Reports added / removed components, version changes (upgrade / downgrade) and
license changes. Every added or license-changed component is classified against
.cursor/oss-policy.md (same SPDX rules as audit-github-repo.py: OR = best, AND = worst).
SBOM entries without an SPDX license fall back to known-licenses.md.

Exit code: 0 no new risk, 1 REVIEW REQUIRED, 2 BLOCK, 3 error.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from oss_paths import safe_path  # CLI paths must stay inside the working directory

_spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("audit-github-repo.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

RANK = audit.RANK


def comp_key(c: dict) -> tuple[str, str]:
    """(ecosystem, normalized name). PyPI names compare case/[-_.]-insensitively."""
    purl = c.get("purl") or ""
    m = re.match(r"pkg:([^/]+)/", purl)
    eco = m.group(1) if m else (c.get("type") or "library")
    name = c.get("name", "")
    if c.get("group"):
        name = f"{c['group']}/{name}"
    if eco == "pypi":
        name = re.sub(r"[-_.]+", "-", name).lower()
    return eco, name.lower() if eco == "npm" else name


# Unambiguous license names / URLs as Maven POMs and registries write them -> SPDX id.
# Ambiguous names ("BSD License", "GPL") are deliberately absent: they stay unresolved for review.
NAME_TO_SPDX = {
    "the apache software license, version 2.0": "Apache-2.0", "apache license, version 2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0", "the apache license, version 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0", "simplified bsd license": "BSD-2-Clause", "the bsd 2-clause license": "BSD-2-Clause",
    "new bsd license": "BSD-3-Clause", "the bsd 3-clause license": "BSD-3-Clause", "bsd 3-clause license": "BSD-3-Clause",
    "the mit license": "MIT", "mit license": "MIT", "eclipse public license 1.0": "EPL-1.0",
    "eclipse public license - v 1.0": "EPL-1.0", "eclipse public license v2.0": "EPL-2.0",
    "eclipse public license - v 2.0": "EPL-2.0", "mozilla public license 2.0": "MPL-2.0",
    "gnu lesser general public license v2.1": "LGPL-2.1-only", "gnu general public license, version 2": "GPL-2.0-only",
}
URL_TO_SPDX = {
    "apache.org/licenses/license-2.0": "Apache-2.0", "opensource.org/licenses/mit": "MIT",
    "opensource.org/licenses/bsd-license": "BSD-2-Clause", "opensource.org/licenses/bsd-2-clause": "BSD-2-Clause",
    "opensource.org/licenses/bsd-3-clause": "BSD-3-Clause", "eclipse.org/legal/epl-v10": "EPL-1.0",
    "eclipse.org/legal/epl-2.0": "EPL-2.0", "mozilla.org/mpl/2.0": "MPL-2.0",
}


def name_to_spdx(lic: dict) -> str | None:
    name = (lic.get("name") or "").strip().lower()
    if name in NAME_TO_SPDX:
        return NAME_TO_SPDX[name]
    url = re.sub(r"^https?://(www\.)?", "", (lic.get("url") or "").strip().lower()).rstrip("/")
    url = re.sub(r"\.(txt|html|php)$", "", url)
    return URL_TO_SPDX.get(url)


def comp_license(c: dict) -> str:
    """SPDX expression from a CycloneDX component, or '' when only unrecognized free text is present."""
    ids = []
    for entry in c.get("licenses") or []:
        if entry.get("expression"):
            return entry["expression"]
        lic = entry.get("license") or {}
        spdx = lic.get("id") or name_to_spdx(lic)
        if spdx and spdx not in ids:
            ids.append(spdx)
    return " AND ".join(ids)


def load(path: str) -> dict[tuple[str, str], dict]:
    bom = json.loads(Path(path).read_text(encoding="utf-8"))
    if bom.get("bomFormat") != "CycloneDX":
        raise ValueError(f"{path}: not a CycloneDX JSON SBOM")
    return {comp_key(c): c for c in bom.get("components", [])}


def version_tuple(v: str):
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"[.\-+]", v or ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    try:
        old, new = load(safe_path(args.old, "old SBOM")), load(safe_path(args.new, "new SBOM"))
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 3

    policy, cache = audit.load_policy(), audit.load_cache()

    def license_of(key, c):
        expr = comp_license(c)
        if expr:
            return expr, "sbom"
        hit = cache.get(key)
        if hit:
            return hit[0], f"cache {hit[1]}"
        names = [(e.get("license") or {}).get("name") for e in c.get("licenses") or []]
        names = [n.split(" :: ")[-1] for n in names if n]
        return "NOASSERTION", (f"non-SPDX name: {', '.join(names)} — verify" if names else "no license data")

    added, removed, changed, lic_changed = [], [], [], []
    for key in sorted(new.keys() - old.keys()):
        lic, src = license_of(key, new[key])
        added.append({"pkg": f"{key[0]}:{key[1]}", "version": new[key].get("version"),
                      "license": lic, "source": src, "policy": audit.evaluate(lic, policy)})
    for key in sorted(old.keys() - new.keys()):
        removed.append({"pkg": f"{key[0]}:{key[1]}", "version": old[key].get("version")})
    for key in sorted(old.keys() & new.keys()):
        o, n = old[key], new[key]
        ov, nv = o.get("version") or "", n.get("version") or ""
        if ov != nv:
            direction = "downgrade" if nv and ov and version_tuple(nv) < version_tuple(ov) else "upgrade"
            changed.append({"pkg": f"{key[0]}:{key[1]}", "from": ov, "to": nv, "direction": direction})
        ol, nl = license_of(key, o)[0], license_of(key, n)
        if ol != nl[0]:
            lic_changed.append({"pkg": f"{key[0]}:{key[1]}", "from": ol, "to": nl[0], "source": nl[1],
                                "policy_from": audit.evaluate(ol, policy),
                                "policy": audit.evaluate(nl[0], policy)})

    risks = [a for a in added if a["policy"] != "Allowed"] + \
            [l for l in lic_changed if RANK[l["policy"]] > RANK[l["policy_from"]] or l["policy"] != "Allowed"]
    worst = max((r["policy"] for r in risks), key=RANK.get, default="Allowed")
    verdict = {"Allowed": "PASS", "Review Required": "REVIEW REQUIRED", "Blocked": "BLOCK"}[worst]

    if args.json:
        print(json.dumps({"verdict": verdict, "added": added, "removed": removed,
                          "version_changed": changed, "license_changed": lic_changed}, indent=2))
    else:
        print("# SBOM Diff Report\n")
        print(f"- Old: {args.old} ({len(old)} components)")
        print(f"- New: {args.new} ({len(new)} components)")
        print(f"- Added {len(added)} · Removed {len(removed)} · Version changed {len(changed)} · "
              f"License changed {len(lic_changed)}")
        print(f"- Verdict: **{verdict}**\n")
        print("## Added")
        print("\n".join(f"- {a['pkg']}@{a['version']} — `{a['license']}` ({a['source']}) → {a['policy']}"
                        for a in added) or "- None")
        print("\n## Removed")
        print("\n".join(f"- {r['pkg']}@{r['version']}" for r in removed) or "- None")
        print("\n## Version Changed")
        print("\n".join(f"- {c['pkg']}: {c['from']} → {c['to']}"
                        + (" ⚠️ **downgrade**" if c["direction"] == "downgrade" else "")
                        for c in changed) or "- None")
        print("\n## License Changed")
        print("\n".join(f"- {l['pkg']}: `{l['from']}` ({l['policy_from']}) → `{l['to']}` ({l['policy']})"
                        for l in lic_changed) or "- None")
        print("\n## Action Items")
        items = [f"- [ ] **{r['policy']}** — {r['pkg']}: `{r.get('license') or r.get('to')}` → "
                 + ("verify the real license, then add it to known-licenses.md"
                    if (r.get("license") or r.get("to")) == "NOASSERTION"
                    else "replace or get OSS Manager approval" if r["policy"] == "Blocked"
                    else "review obligations")
                 for r in risks]
        if added or removed or lic_changed:
            items.append("- [ ] Update NOTICE (oss-notice-writer) for added / removed / relicensed components")
        if any(c["direction"] == "downgrade" for c in changed):
            items.append("- [ ] Check downgrades for reintroduced CVEs (oss-security-review)")
        print("\n".join(items) or "- None")

    return {"PASS": 0, "REVIEW REQUIRED": 1, "BLOCK": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
