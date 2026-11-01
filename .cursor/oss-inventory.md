# OSS Project Inventory

Lightweight stand-in for a CMDB (Jira Assets): which projects exist, where their dependency
manifests live, and who owns them. `scripts/oss/cve-triage.py` reads this table.

- **Path**: project root (absolute, or relative to this repo's root). The triage reads
  `package-lock.json`, `bom*.json` / `sbom*.json` (CycloneDX), `package.json`, `requirements.txt` there.
- **Owner**: the person accountable for upgrades (Jira account or e-mail). Leave empty to fall back
  to the project's `CODEOWNERS`.
- Keep it current when projects or owners change. Replace with the Jira Assets lookup once a CMDB exists.

| Project | Path | Owner | Team |
|---------|------|-------|------|
| <project-name> | <path/to/project> | <owner> | <team> |
