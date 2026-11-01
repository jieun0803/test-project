#!/usr/bin/env python3
"""ScanCode license scan + custom / modified license similarity analysis.

Usage:
  python3 scripts/oss/license-scan.py PATH [--json] [--keep-scan FILE]
  python3 scripts/oss/license-scan.py --install          # set up ScanCode once

What it reports for every file under PATH (source tree, vendored code, node_modules/pkg ...):
  EXACT        ScanCode matched a known license text / SPDX id at 100%  -> policy bucket
  APPROXIMATE  ScanCode matched with score < 100 (3-seq / partial)       -> may be modified, review
  CUSTOM       a LICENSE / COPYING / NOTICE file with no detection        -> unknown license, blocked
For APPROXIMATE and CUSTOM files, the text is compared with ScanCode's reference license
texts (word 5-gram similarity): the closest licenses with % similarity, and sentences that
are NOT in the closest reference (added restrictions / custom terms).

ScanCode location: $SCANCODE, `scancode` on PATH, or ~/.cache/oss-governance/scancode-venv
(created by --install with python3.12; needs `brew install libmagic` on macOS).
Exit code: 0 PASS, 1 REVIEW REQUIRED, 2 BLOCK, 3 error.
"""
from __future__ import annotations

import argparse
import difflib
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("audit-github-repo.py"))
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

VENV = Path.home() / ".cache" / "oss-governance" / "scancode-venv"
LICENSE_FILE = re.compile(r"^(licen[cs]e|copying|notice|unlicense|copyright)([.\-_].*)?$", re.I)
BUCKET_TO_VERDICT = {"Allowed": "PASS", "Review Required": "REVIEW REQUIRED", "Blocked": "BLOCK"}


# ---------------------------------------------------------------- ScanCode setup
def find_scancode() -> str | None:
    if os.environ.get("SCANCODE"):
        return os.environ["SCANCODE"]
    venv_bin = VENV / "bin" / "scancode"
    if venv_bin.exists():
        return str(venv_bin)
    return shutil.which("scancode")


def install() -> int:
    py = shutil.which("python3.12") or shutil.which("python3.11") or shutil.which("python3.10")
    if not py:
        print("error: ScanCode needs Python 3.10-3.12 (brew install python@3.12)", file=sys.stderr)
        return 3
    VENV.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([py, "-m", "venv", str(VENV)], check=True)
    pip = str(VENV / "bin" / "pip")
    subprocess.run([pip, "install", "-q", "--upgrade", "pip"], check=True)
    # pluggy >= 1.6 breaks plugincode 32 ("did not find any 'pre_scan' hooks")
    subprocess.run([pip, "install", "-q", "scancode-toolkit-mini", "pluggy<1.6"], check=True)
    out = subprocess.run([str(VENV / "bin" / "scancode"), "--version"], capture_output=True, text=True, env=sc_env())
    if out.returncode:
        print(out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "scancode failed", file=sys.stderr)
        print("hint: macOS needs libmagic -> brew install libmagic", file=sys.stderr)
        return 3
    print(out.stdout.strip().splitlines()[0], "->", VENV)
    return 0


def sc_env() -> dict:
    env = dict(os.environ)
    for db in ("/opt/homebrew/share/misc/magic.mgc", "/usr/local/share/misc/magic.mgc", "/usr/share/misc/magic.mgc"):
        if Path(db).exists():
            env.setdefault("TYPECODE_LIBMAGIC_DB_PATH", db)
            break
    return env


def run_scancode(scancode: str, target: Path, out: Path) -> None:
    cmd = [scancode, "--license", "--copyright", "--info", "--license-text", "--quiet",
           "-n", str(max(1, (os.cpu_count() or 2) - 1)), "--json", str(out), str(target)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=sc_env())
    except OSError as e:
        raise RuntimeError(f"cannot run {scancode} ({e.strerror}). Run: python3 scripts/oss/license-scan.py --install")
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "scancode failed")


# ---------------------------------------------------------------- similarity
def reference_dir(scancode: str) -> Path | None:
    root = Path(scancode).resolve().parent.parent
    hits = glob.glob(str(root / "lib" / "python3*" / "site-packages" / "licensedcode" / "data" / "licenses"))
    return Path(hits[0]) if hits else None


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def shingles(ws: list[str], n: int = 5) -> set[tuple]:
    return {tuple(ws[i:i + n]) for i in range(max(1, len(ws) - n + 1))}


_REFS: list[tuple[str, str, set, str]] | None = None


def references(ref_dir: Path) -> list[tuple[str, str, set, str]]:
    """(spdx key, name, 5-gram set, text) for every reference license that has an SPDX key."""
    global _REFS
    if _REFS is None:
        _REFS = []
        for f in ref_dir.glob("*.LICENSE"):
            raw = f.read_text(encoding="utf-8", errors="replace")
            m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
            if not m:
                continue
            meta, body = m.groups()
            spdx = re.search(r"^spdx_license_key:\s*(\S+)", meta, re.M)
            name = re.search(r"^name:\s*(.+)$", meta, re.M)
            if not spdx or spdx.group(1).startswith("LicenseRef") or len(body) < 200:
                continue
            ws = words(body)
            _REFS.append((spdx.group(1), name.group(1).strip() if name else spdx.group(1), shingles(ws), body))
    return _REFS


def similarity(text: str, ref_dir: Path, top: int = 3) -> dict:
    sh = shingles(words(text))
    scored = []
    for spdx, name, rsh, body in references(ref_dir):
        inter = len(sh & rsh)
        if not inter:
            continue
        # Dice coefficient: penalizes both missing reference text and added custom text
        scored.append((2 * inter / (len(sh) + len(rsh)), inter / len(rsh), spdx, name, body))
    scored.sort(reverse=True)
    best = scored[:top]
    added = []
    if best:
        ref_sents = {" ".join(words(s)) for s in re.split(r"(?<=[.;:])\s+|\n\s*\n", best[0][4])}
        for s in re.split(r"(?<=[.;:])\s+|\n\s*\n", text):
            norm = " ".join(words(s))
            if len(norm.split()) < 4 or norm in ref_sents or re.match(r"copyright\b", norm):
                continue
            close = difflib.get_close_matches(norm, ref_sents, n=1, cutoff=0.85)
            if not close:
                added.append(" ".join(s.split()))
    return {"closest": [{"spdx": s, "name": n, "similarity": round(d * 100, 1), "reference_coverage": round(c * 100, 1)}
                        for d, c, s, n, _ in best],
            "added_text": added[:8]}


# ---------------------------------------------------------------- per-file match cleanup
POINTER = "LicenseRef-scancode-unknown-license-reference"  # "see LICENSE" -- a pointer, not a license


def own_matches(f: dict) -> list[dict]:
    """License matches that describe this file, with ScanCode's aggregation noise removed:
    1. drop matches pulled in from a referenced file (from_file != this file; that file is reported itself)
    2. drop "see LICENSE" pointers
    3. overlapping matches on the same lines -> keep the highest score
    4. a single license that is one option of an OR match in the file is a mention of that choice, not AND
    """
    ms = [m for d in f.get("license_detections") or [] for m in d["matches"]
          if m.get("from_file") in (None, f["path"]) and m["license_expression_spdx"] != POINTER]
    ms.sort(key=lambda m: -m["score"])
    kept = []
    for m in ms:
        if any(k["start_line"] <= m["end_line"] and m["start_line"] <= k["end_line"] for k in kept):
            continue
        kept.append(m)
    choices = {lic.strip("() ") for m in kept if " OR " in m["license_expression_spdx"]
               for lic in re.split(r"\s+OR\s+", m["license_expression_spdx"])}
    return [m for m in kept if " OR " in m["license_expression_spdx"]
            or m["license_expression_spdx"].strip("() ") not in choices]


# ---------------------------------------------------------------- main
def classify(scan: dict, root: Path, ref_dir: Path | None, policy: dict) -> list[dict]:
    out = []
    base = root.parent  # ScanCode paths start with the target's own name
    for f in scan["files"]:
        if f["type"] != "file":
            continue
        path = f["path"]
        matches = own_matches(f)
        is_license_file = bool(LICENSE_FILE.match(f["name"])) and not f.get("is_source")
        if not matches and not is_license_file:
            continue
        item = {"file": path, "license_file": is_license_file,
                "copyright": sorted({c["copyright"] for c in f.get("copyrights", [])})[:3]}
        if not matches:
            item.update(kind="CUSTOM", expression="NOASSERTION", policy="Blocked", score=0)
        else:
            exprs = sorted({m["license_expression_spdx"] for m in matches})
            expr = exprs[0] if len(exprs) == 1 else " AND ".join(f"({e})" if " OR " in e else e for e in exprs)
            score = min(m["score"] for m in matches)
            approx = any(m["matcher"].startswith("3-seq") or m["score"] < 100 or m["match_coverage"] < 100
                         for m in matches)
            item.update(kind="APPROXIMATE" if approx else "EXACT", expression=expr, score=score,
                        matches=[{"spdx": m["license_expression_spdx"], "score": m["score"],
                                  "coverage": m["match_coverage"], "lines": f"{m['start_line']}-{m['end_line']}",
                                  "matcher": m["matcher"]} for m in matches])
            pol = audit.evaluate(expr, policy)
            # a modified license is never better than Review Required, whatever it resembles
            item["policy"] = max(pol, "Review Required", key=audit.RANK.get) if approx else pol
        if item["kind"] != "EXACT" and ref_dir and is_license_file:
            p = base / path
            if p.exists():
                item["similarity"] = similarity(p.read_text(encoding="utf-8", errors="replace"), ref_dir)
        out.append(item)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?")
    ap.add_argument("--install", action="store_true", help="install ScanCode into ~/.cache/oss-governance")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--keep-scan", help="also save the raw ScanCode JSON here")
    a = ap.parse_args()
    if a.install:
        return install()
    if not a.path:
        ap.error("PATH is required")
    target = Path(a.path).resolve()
    if not target.exists():
        print(f"error: {a.path} not found", file=sys.stderr)
        return 3
    scancode = find_scancode()
    if not scancode:
        print("error: ScanCode not found. Run: python3 scripts/oss/license-scan.py --install", file=sys.stderr)
        return 3
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(a.keep_scan) if a.keep_scan else Path(tmp) / "scan.json"
        try:
            run_scancode(scancode, target, raw)
        except RuntimeError as e:
            print(f"error: scancode: {e}", file=sys.stderr)
            return 3
        scan = json.loads(raw.read_text(encoding="utf-8"))
    items = classify(scan, target, reference_dir(scancode), audit.load_policy())
    worst = max((i["policy"] for i in items), key=audit.RANK.get, default="Allowed")
    verdict = BUCKET_TO_VERDICT[worst]
    files_scanned = sum(1 for f in scan["files"] if f["type"] == "file")

    if a.json:
        print(json.dumps({"target": str(target), "verdict": verdict, "files_scanned": files_scanned,
                          "findings": items}, ensure_ascii=False, indent=2))
    else:
        order = {"Blocked": 0, "Review Required": 1, "Allowed": 2}
        print("# License Scan Report (ScanCode)\n")
        print(f"- Target: {target}")
        print(f"- Files scanned: {files_scanned} · with license info: {len(items)}")
        print(f"- Verdict: **{verdict}**\n")
        print("| File | Kind | License | Score | Policy |\n|---|---|---|---|---|")
        for i in sorted(items, key=lambda i: (order[i["policy"]], i["file"])):
            print(f"| `{i['file']}` | {i['kind']} | `{i['expression']}` | {i['score']:g} | {i['policy']} |")
        sims = [i for i in items if i.get("similarity")]
        if sims:
            print("\n## Similarity Analysis (approximate / custom licenses)")
        for i in sims:
            s = i["similarity"]
            print(f"\n### `{i['file']}` — {i['kind']}")
            if i["kind"] == "APPROXIMATE":
                print(f"- ScanCode best match: `{i['expression']}` at {i['score']:g}% (not an exact text match)")
            close = [c for c in s["closest"] if c["similarity"] >= 10]
            print("- Closest reference licenses: " + (", ".join(
                f"`{c['spdx']}` {c['similarity']}%" for c in close)
                or "none — under 10% similar to every known license (custom terms)"))
            if s["added_text"]:
                print("- Text not in the closest reference (review these terms):")
                for t in s["added_text"]:
                    print(f"  - \"{t[:200]}\"")
        print("\n## Action Items")
        acts = []
        for i in sorted(items, key=lambda i: order[i["policy"]]):
            if i["kind"] == "CUSTOM":
                acts.append(f"- [ ] `{i['file']}`: custom license — legal review, or replace the component")
            elif i["kind"] == "APPROXIMATE" and not i["license_file"]:
                acts.append(f"- [ ] `{i['file']}`: partial license statement (`{i['expression']}`, {i['score']:g}%) "
                            "— confirm it matches the package LICENSE")
            elif i["kind"] == "APPROXIMATE":
                near = ((i.get("similarity") or {}).get("closest") or [{}])[0].get("spdx") or i["expression"]
                acts.append(f"- [ ] `{i['file']}`: modified `{near}`-like text — check the added terms with legal")
            elif i["policy"] == "Blocked":
                acts.append(f"- [ ] `{i['file']}`: `{i['expression']}` is blocked — remove, or OSS Manager exception")
        print("\n".join(acts) or "- None")
    return {"PASS": 0, "REVIEW REQUIRED": 1, "BLOCK": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
