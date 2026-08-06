# License Obligations by Deployment Type

Cross-reference with `.cursor/oss-policy.md` deployment model.

## All Deployments

| Obligation | Description |
|------------|-------------|
| Copyright notice | Preserve copyright statements |
| License text | Include full license text or link in NOTICE |
| Attribution | Credit authors per license terms |
| SBOM | Maintain CycloneDX SBOM per release |
| Change log | Track dependency adds/removes for audit trail |

## SaaS (No Binary Distribution)

| License type | Source disclosure | Same license on app code |
|--------------|-------------------|---------------------------|
| Permissive | Not required | Not required |
| Weak copyleft | Usually not for network-only use | Not required for separate process |
| GPL-3.0 | Not triggered by SaaS alone (no distribution) | REVIEW if combined into single work |
| AGPL-3.0 | **Triggered by network use** | Source must be offered to users |

## Binary Distribution (Mobile, Desktop, Embedded)

| License type | Source disclosure | Same license on app code |
|--------------|-------------------|---------------------------|
| Permissive | Not required | Not required |
| LGPL (dynamic link) | Provide LGPL library source + linking info | App may stay proprietary |
| LGPL (static link) | Provide object files or source to relink | REVIEW |
| GPL / AGPL | **Required** for combined work | Combined work must be GPL/AGPL |

## Source Distribution

| License type | Obligation |
|--------------|------------|
| Permissive | Include license and copyright |
| Copyleft | Recipient receives same freedoms; source under copyleft terms |

## Checklist by Release Type

### SaaS Release

- [ ] NOTICE page updated
- [ ] SBOM archived
- [ ] No AGPL in stack unless source offer planned
- [ ] No unapproved proprietary SDKs

### Binary Release

- [ ] NOTICE bundled in app (Settings > Open Source Licenses)
- [ ] SBOM archived
- [ ] Copyleft source packages identified
- [ ] Source offer mechanism ready if GPL/LGPL requires it

### Library/SDK Release

- [ ] License compatibility with downstream consumers verified
- [ ] SPDX headers on shipped source files
- [ ] NOTICE includes transitive dependencies

## Common Package Obligations

| License | Required actions |
|---------|------------------|
| MIT | Copyright + permission notice |
| Apache-2.0 | NOTICE with copyright, patent, attribution; state changes |
| BSD-3-Clause | Copyright + no-endorsement clause preserved |
| LGPL | Provide library source; allow reverse engineering for LGPL portion |
| GPL | Provide complete corresponding source of combined work |
