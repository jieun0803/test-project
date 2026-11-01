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

Priority order:

1. SPDX identifier in package metadata
2. LICENSE file in package source
3. Registry API (npm, PyPI, Maven Central, crates.io)
4. GitHub `license` field via API

Run [scripts/oss/scan-deps.sh](../../../scripts/oss/scan-deps.sh) when available for automated discovery.

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

- [license-categories.md](references/license-categories.md)
- [compatibility-matrix.md](references/compatibility-matrix.md)
- [obligations.md](references/obligations.md)
