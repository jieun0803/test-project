---
name: oss-license-compliance
description: >
  Identifies open-source licenses, analyzes compatibility, and generates obligation
  checklists. Use when the user mentions license check, GPL compatibility, dependency
  audit, SBOM license review, NOTICE update, or asks whether a library license is
  allowed. Also use when auditing package.json, requirements.txt, go.mod, pom.xml,
  build.gradle, or other dependency manifests.
---

# OSS License Compliance

Audit licenses against project policy in [`.cursor/oss-policy.md`](../../oss-policy.md).

## Step 1 — Determine Scope

| User intent | Action |
|-------------|--------|
| Single license question ("Can I use LGPL-2.1?") | Answer from references + policy; skip full scan |
| Full project audit | Scan all dependency manifests in the repo |
| Specific file audit | Parse the named manifest/lockfile only |
| GitHub repository URL ("https://github.com/owner/repo 의존성 라이선스 감사해줘") | Follow **GitHub URL Audit** below |

### GitHub URL Audit

1. Run `python3 scripts/oss/audit-github-repo.py <github-url>` (add `--ref <branch>` for a non-default branch). It needs no clone and uses:
   - the GitHub dependency-graph SBOM (direct + transitive) when the graph is enabled, or
   - root `package.json` / `requirements.txt` via the contents API (direct deps only) as a fallback.
   It fills missing licenses from `known-licenses.md`, then the npm / PyPI registry, and classifies them against `.cursor/oss-policy.md`. Exit code: 0 PASS, 1 REVIEW REQUIRED, 2 BLOCK, 3 error.
2. If the script is unavailable, use the GitHub MCP (`get_file_contents`) to read the manifests, then continue from Step 2.
3. Present the result in the Step 6 report format. State the **Source** line (SBOM vs. manifest fallback). In fallback mode, warn that transitive dependencies were not scanned.
4. For each item under **Cache Misses**, append a verified row to `known-licenses.md`.

Detect ecosystem from file type:

| File | Ecosystem |
|------|-----------|
| package.json, pnpm-lock.yaml, yarn.lock | Node.js |
| requirements.txt, pyproject.toml, poetry.lock | Python |
| go.mod, go.sum | Go |
| pom.xml, build.gradle*, libs.versions.toml | Java/Kotlin/Android |
| Cargo.toml | Rust |
| Gemfile | Ruby |
| composer.json | PHP |

## Step 2 — Identify Licenses

**Check the cache first:** read [references/known-licenses.md](references/known-licenses.md) and follow its *How to Use* rules (hit / stale / miss / mismatch). For a cache hit, cite `known-licenses.md (verified YYYY-MM-DD)` as the source. After looking up a miss, append the verified result to the cache.

Lookup priority on a cache miss:

1. SPDX identifier in package metadata
2. LICENSE file in package source
3. Registry API (npm, PyPI, Maven Central, crates.io)
4. GitHub `license` field via API

Run [scripts/oss/scan-deps.sh](../../../scripts/oss/scan-deps.sh) when available for automated discovery.

**File-level scan (ScanCode) + custom license similarity** — use when metadata is missing or untrusted: vendored / copied code, a downloaded package (`npm pack`, `pip download`), a LICENSE file that looks non-standard, or "이 폴더 라이선스 스캔해줘 / 이 LICENSE 무슨 라이선스야?":

```bash
python3 scripts/oss/license-scan.py --install   # once (ScanCode in ~/.cache/oss-governance; macOS: brew install libmagic)
python3 scripts/oss/license-scan.py <dir-or-file>
```

- `EXACT` = known license text / SPDX id at 100%. `APPROXIMATE` = partial match: in a LICENSE file it may be a **modified license**; check the *Text not in the closest reference* lines (added restrictions such as "no commercial use") with legal. `CUSTOM` = a LICENSE file no known license matches → Blocked as unknown.
- Similarity is computed against ScanCode's ~2,000 reference texts. Trust the similarity ranking over ScanCode's best guess for modified texts (e.g. MIT + an extra clause can be guessed as `JSON`).
- Dual licenses (`MIT OR GPL-3.0-only`) are kept as a choice. Elect the permissive option and record it in `known-licenses.md` Notes.

Flag packages with **missing or UNKNOWN** license as REVIEW REQUIRED.

## Step 3 — Classify and Score Risk

Read [references/license-categories.md](references/license-categories.md) for category and default risk.

Map each license to project policy:

- **Allowed** → Low, PASS
- **Review required** → Medium, REVIEW REQUIRED
- **Blocked** → High, BLOCK

## Step 4 — Compatibility Analysis

Read [references/compatibility-matrix.md](references/compatibility-matrix.md).

Check:

- Strong copyleft + permissive mix in distributed binaries
- Apache-2.0 + GPL-2.0-only incompatibility
- Dual-licensed packages (record which license applies)
- Transitive dependencies with conflicting licenses

## Step 5 — Deployment Obligations

Read [references/obligations.md](references/obligations.md) and `.cursor/oss-policy.md` deployment model.

Apply obligations for the project's deployment type (SaaS / binary / source).

## Step 6 — Report

Always output this structure:

```markdown
# OSS License Audit Report

## Overview
- Target: [file or project path]
- Libraries scanned: N
- Verdict: [PASS | REVIEW REQUIRED | BLOCK]

## Distribution
| License | Count | Category | Risk |
|---------|-------|----------|------|
| MIT | N | Permissive | Low |

## Review Items
- [Package] — [reason]

## Action Items
- [ ] ...

## Obligations Checklist
- [ ] NOTICE / attribution update
- [ ] SBOM regeneration
- [ ] Source disclosure review (if copyleft in binary distribution)
- [ ] OSS Manager approval (if blocked license exception needed)
```

## Single-License Quick Answer Format

```markdown
## [SPDX-ID]

- Category: [Permissive | Weak Copyleft | Strong Copyleft | Proprietary]
- Policy: [Allowed | Review Required | Blocked]
- Risk: [Low | Medium | High]
- Notes: [linking, scope, deployment impact]
- Recommendation: [use / use with conditions / do not use]
```

## References

- [known-licenses.md](references/known-licenses.md) — verified per-package cache (check first)
- [license-categories.md](references/license-categories.md)
- [compatibility-matrix.md](references/compatibility-matrix.md)
- [obligations.md](references/obligations.md)
