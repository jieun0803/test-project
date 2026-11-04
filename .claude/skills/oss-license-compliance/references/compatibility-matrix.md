# License Compatibility Matrix

Use when multiple licenses appear in one deliverable (app binary, shared library, SaaS bundle).

## Legend

| Symbol | Meaning |
|--------|---------|
| OK | Generally compatible with standard compliance |
| REVIEW | Possible conflict; legal/engineering review needed |
| BLOCK | Known incompatibility or high conflict risk |

## Combining Project Code With Dependencies

| Project license | Dependency: Permissive | Dependency: Weak Copyleft | Dependency: Strong Copyleft |
|-----------------|------------------------|----------------------------|----------------------------|
| Proprietary | OK | REVIEW | BLOCK (binary) / REVIEW (SaaS) |
| Apache-2.0 | OK | REVIEW | REVIEW |
| MIT | OK | REVIEW | REVIEW |
| GPL-3.0 | OK (same license family) | OK | OK (same license) |

## Known Incompatibilities

| License A | License B | Result | Notes |
|-----------|-----------|--------|-------|
| Apache-2.0 | GPL-2.0-only | BLOCK | FSF: Apache 2.0 incompatible with GPL v2 only |
| Apache-2.0 | GPL-3.0-or-later | OK | GPL v3 accepts Apache 2.0 |
| GPL-2.0-only | GPL-3.0-only | BLOCK | Cannot combine in single work |
| CDDL-1.0 | GPL-2.0 | BLOCK | Classic OpenSolaris conflict |
| MPL-2.0 | GPL-2.0 | REVIEW | MPL files remain MPL; combined work may need GPL |

## Distribution Context

| Deployment | Strong copyleft in dependency | Typical outcome |
|------------|------------------------------|-----------------|
| SaaS (no distribution) | GPL/AGPL | AGPL triggers; GPL may not — REVIEW |
| Mobile/desktop binary | GPL/LGPL static link | Source disclosure likely required |
| Mobile/desktop binary | LGPL dynamic link | Often OK with notices |
| Source release | Any OSI license | Must preserve license terms |

## Dual-Licensed Packages

Record which license the project elects. Example: "GPL-2.0 OR MIT" → choose MIT for proprietary products.

## Action When Conflict Detected

1. Identify the conflicting packages and licenses.
2. Check if dependency can be replaced with permissive alternative.
3. Check if usage is test-only or optional module.
4. Escalate to OSS Manager if no technical workaround.
