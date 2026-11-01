---
name: oss-sbom-diff
description: >
  Compares two CycloneDX SBOMs (previous release vs. current) and reports added,
  removed, upgraded/downgraded and relicensed components with policy verdicts.
  Use when the user asks to compare SBOMs, diff SBOM versions, or see what changed
  in dependencies between releases ("이전 SBOM과 이번 SBOM 변경 내역 비교해줘").
---

# OSS SBOM Diff

Policy source: [`.cursor/oss-policy.md`](../../oss-policy.md). License cache: [known-licenses.md](../oss-license-compliance/references/known-licenses.md).

## Step 1 — Locate the two SBOMs

- If the user named two files, use them (old first).
- Otherwise look for CycloneDX JSON files (`bom*.json`, `sbom*.json`) in the project and in `sboms/`. Pick the two most recent by release version or git history (`git log --follow -- bom.json`). To get the previous version from git: `git show <prev-tag>:bom.json > /tmp/bom-old.json`.
- If only one SBOM exists, generate the current one first (`npx --yes @cyclonedx/cyclonedx-npm --output-file bom.json` or `bash scripts/oss/sbom-python.sh . bom-python.json`). Never guess the old one.

## Step 2 — Run the diff

```bash
python3 scripts/oss/sbom-diff.py OLD.json NEW.json        # Markdown report
python3 scripts/oss/sbom-diff.py OLD.json NEW.json --json # machine-readable
```

Exit code: 0 PASS, 1 REVIEW REQUIRED, 2 BLOCK, 3 error.

## Step 3 — Present the report

Show the script's `# SBOM Diff Report` as is, then add:

1. **Blocked** items first, with permissive alternatives (see oss-license-compliance).
2. `NOASSERTION` items: the SBOM had no SPDX id. Look the license up (registry / LICENSE file), append it to `known-licenses.md`, and re-run. Do not call them Blocked in the summary until verified.
3. **Downgrades**: hand off to oss-security-review to check for reintroduced CVEs.
4. Added / removed / relicensed components: hand off to oss-notice-writer for the next NOTICE.

## Rules

- Only compare CycloneDX JSON. Ask for a conversion if given SPDX or XML.
- Compare at the same scope (direct vs. resolved/transitive). If one SBOM is direct-only and the other is resolved, say so: most "added" entries are then transitive deps, not new choices.
