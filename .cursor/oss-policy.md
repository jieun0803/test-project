# OSS Governance Policy

Single source of truth for license and security decisions. Skills and Rules in this project MUST reference this file.

## Deployment Model

| Field | Value |
|-------|-------|
| Primary deployment | SaaS (web service — server-side, no binary shipped to end users) |
| Secondary distribution | Not applicable |
| Source distribution | Not distributed |

> **Customize per project.** Set Primary deployment to the project's real service form (SaaS / Binary release / Source). If the project ships a mobile or desktop binary, change it to `Binary release` and move Weak Copyleft from *Review Required* to *Blocked*.

SaaS (network-only) use does not distribute the software, so Weak Copyleft obligations are usually not triggered; Strong Copyleft remains blocked because AGPL/SSPL trigger on network use and GPL code may later ship in a binary or source release.

## License Policy

### Allowed (Low Risk)

Use without prior approval:

- MIT
- Apache-2.0
- BSD-2-Clause
- BSD-3-Clause
- ISC
- 0BSD
- Unlicense
- CC0-1.0

### Review Required (Medium Risk)

Requires context review (linking scope, modification, deployment form) before adding:

**Weak Copyleft**

- LGPL-2.0-only
- LGPL-2.1-only / LGPL-2.1-or-later
- LGPL-3.0-only / LGPL-3.0-or-later
- EPL-1.0 / EPL-2.0
- MPL-2.0
- CDDL-1.0 / CDDL-1.1

**Other**

- Proprietary SDK (vendor-approved only)

**Test-only exception:** Weak Copyleft libraries used exclusively in test/CI scope (e.g. JUnit under EPL-2.0) are allowed in `test`, `testImplementation`, or `devDependencies` only — not shipped in the distributed binary.

### Blocked (High Risk)

Do not add without OSS Manager exception approval. **Strong Copyleft** may require source disclosure of the whole application (AGPL/SSPL even for SaaS); block for production/runtime dependencies:

**Strong Copyleft**

- GPL-2.0-only / GPL-2.0-or-later
- GPL-3.0-only / GPL-3.0-or-later
- AGPL-3.0-only / AGPL-3.0-or-later
- SSPL-1.0

**Other**

- Unapproved proprietary libraries
- Unknown / missing license

## Security Policy

| Criterion | Threshold |
|-----------|-----------|
| Framework | OWASP Top 10 (2021) |
| Dependency CVE | Block CRITICAL; review HIGH |
| Known exploit in the wild | Block regardless of CVSS |
| Unmaintained dependency | Review if no release in 24 months |

### Blocked Code Patterns

- Hardcoded credentials, API keys, tokens
- SQL built via string concatenation with user input
- Weak cryptography (MD5, SHA1 for passwords, DES, RC4, ECB mode)
- Disabled TLS certificate validation
- `eval()` / `exec()` with untrusted input

## Compliance Obligations

| Obligation | When |
|------------|------|
| NOTICE / OSS attribution file | Every release with dependency changes |
| SBOM (CycloneDX) | Every release |
| Source disclosure | Strong Copyleft blocked by policy. Weak Copyleft: disclose modifications to the library itself if distributed; re-check when deployment changes to Binary |
| License header on copied code | Always when importing external code |

## Escalation

AI-assisted checks produce recommendations. Final approval for exceptions (Weak/Strong Copyleft use, proprietary SDK, HIGH CVE waiver) requires OSS Manager sign-off.

## Policy Version

- Version: 1.2.0
- Last updated: 2026-11-01
- Changes: 1.2.0 — Primary deployment SaaS (matches web target project); Weak Copyleft moved Blocked → Review Required. 1.1.0 — Binary release, Weak Copyleft+ blocked.
