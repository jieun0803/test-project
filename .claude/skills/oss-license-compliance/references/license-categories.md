# License Categories

SPDX ID → category → default risk. Cross-check with `.cursor/oss-policy.md` for project-specific allow/block lists.

## Permissive (Low Risk)

| SPDX ID | Notes |
|---------|-------|
| MIT | Most common; attribution required |
| Apache-2.0 | Patent grant; NOTICE required |
| BSD-2-Clause | Minimal attribution |
| BSD-3-Clause | No endorsement clause |
| ISC | Functionally similar to MIT |
| 0BSD | Public domain equivalent |
| Unlicense | Public domain dedication |
| CC0-1.0 | Public domain dedication |
| Zlib | Attribution required |

## Weak Copyleft (Medium Risk)

| SPDX ID | Notes |
|---------|-------|
| LGPL-2.1-only / LGPL-2.1-or-later | Dynamic linking often OK; static linking may require source |
| LGPL-3.0-only / LGPL-3.0-or-later | Same as LGPL-2.1 with anti-tivoization |
| EPL-1.0 / EPL-2.0 | File-level copyleft; common in test tools |
| MPL-2.0 | File-level copyleft |
| CDDL-1.0 / CDDL-1.1 | File-level; incompatible with GPL in some combinations |
| LGPL-2.0-only | Prefer LGPL-2.1+; legacy |

## Strong Copyleft (High Risk)

| SPDX ID | Notes |
|---------|-------|
| GPL-2.0-only / GPL-2.0-or-later | Derivative works must be GPL; Apache-2.0 incompatible (v2 only) |
| GPL-3.0-only / GPL-3.0-or-later | Same as GPL-2 + patent/anti-tivoization |
| AGPL-3.0-only / AGPL-3.0-or-later | Network use triggers source disclosure |
| SSPL-1.0 | Treat as strong copyleft; many orgs block |

## Other

| Type | Risk | Action |
|------|------|--------|
| Proprietary / Commercial | Medium–High | Vendor approval required |
| Custom / Non-SPDX | Medium | Legal review; map to closest SPDX |
| UNKNOWN / NOASSERTION | High | Block until resolved |
| Public Domain | Low | Verify jurisdiction; prefer CC0-1.0 tag |

## Test-Scope Exception

These are Medium in production but Low in test-only scope:

- EPL-1.0 / EPL-2.0 (JUnit, etc.)
- Mock/stub libraries used only in CI

Verify scope: `test`, `testImplementation`, `devDependencies`, `[tool.poetry.group.dev]`.
