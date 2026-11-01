---
name: oss-dashboard
description: >
  Builds a self-contained HTML dashboard from CycloneDX SBOMs: license distribution
  with policy status for the latest release, and an SBOM change timeline (component
  count, added / removed, risk count) across releases. Use when the user asks for a
  license distribution dashboard, OSS dashboard, SBOM timeline or release-over-release
  dependency trend ("라이선스 분포 대시보드 만들어줘", "SBOM 변경 타임라인 보여줘").
---

# OSS Dashboard

Policy: [`.cursor/oss-policy.md`](../../oss-policy.md). License cache: [known-licenses.md](../oss-license-compliance/references/known-licenses.md).

## Step 1 — Collect SBOMs

- One file per release, named by version: `sboms/<platform>/<version>.json` (e.g. `sboms/web/1.2.0.json`). Releases are ordered by version, so `1.10.0` comes after `1.2.0`.
- Missing the current one → generate it (`npx --yes @cyclonedx/cyclonedx-npm --output-file bom.json` or `bash scripts/oss/sbom-python.sh . bom-python.json`) and copy it in under its version.
- One SBOM gives the distribution only. The timeline needs 2+.

## Step 2 — Build

```bash
python3 scripts/oss/oss-dashboard.py sboms/web/ -o oss-dashboard.html --title "Web OSS 대시보드"
python3 scripts/oss/oss-dashboard.py old.json new.json -o oss-dashboard.html
```

The page is one HTML file (no CDN, no network). It has light / dark mode, hover tooltips and table views.

## Step 3 — Report

Give the file path and the console summary line. Then name:
- the Blocked / Review counts of the latest release, and the largest license group that is `Unknown (NOASSERTION)` (verify those and add them to `known-licenses.md`; they count as Blocked until verified)
- the release that added the most components or the first Blocked item, from the timeline

For the per-package detail of one release step, hand off to oss-sbom-diff.
