---
name: oss-security-review
description: >
  Scans dependencies for CVEs and reviews code for OWASP security issues in OSS
  supply chain context. Use when the user asks for security review, vulnerability
  scan, CVE check, dependency audit, npm audit, pip audit, or OSS supply chain risk.
  Complements built-in review-security for diff-based code review.
---

# OSS Security Review

Apply thresholds from [`.cursor/oss-policy.md`](../../oss-policy.md).

## Step 1 — Scope

| Scope | Action |
|-------|--------|
| Dependencies only | Run scan script + parse CVE output |
| Code only | OWASP pattern review on changed/new files |
| Full audit | Dependencies + code patterns + AI-generated code risks |

## Step 2 — Dependency CVE Scan

Run from repository root:

```bash
bash scripts/oss/scan-deps.sh
```

If tools are missing, use ecosystem-specific fallbacks:

| Ecosystem | Command |
|-----------|---------|
| Node.js | `npm audit --json` or `pnpm audit --json` |
| Python | `pip-audit -r requirements.txt --format json` |
| Go | `govulncheck ./...` |
| Rust | `cargo audit --json` |
| Universal | `osv-scanner --recursive .` or `trivy fs .` |

OSV API fallback for a single package:

```bash
curl -s -X POST https://api.osv.dev/v1/query \
  -H "Content-Type: application/json" \
  -d '{"package":{"name":"PACKAGE","ecosystem":"npm"},"version":"VERSION"}'
```

Classify by policy:

- **CRITICAL** → BLOCK merge/release
- **HIGH** → REVIEW REQUIRED
- **MEDIUM/LOW** → Track; fix when practical

## Step 3 — Code Pattern Review (OWASP Top 10)

Scan changed files for:

| Category | Patterns to flag |
|----------|------------------|
| Injection | SQL/command/LDAP string concatenation with user input |
| Broken Auth | Hardcoded passwords, weak session tokens |
| Sensitive Data | Secrets in source, logs printing PII/tokens |
| XXE | Unsafe XML parsers without hardening |
| Broken Access Control | Missing auth checks on sensitive endpoints |
| Security Misconfiguration | Debug mode in prod, default credentials |
| XSS | Unescaped user input in HTML/JS templates |
| Insecure Deserialization | `pickle.loads`, unsafe YAML `load()` |
| Vulnerable Components | Outdated deps (Step 2) |
| Logging | Missing audit trail on security events |

## Step 4 — AI-Generated Code Risks

Flag common AI coding assistant mistakes:

- Plausible but non-existent API methods (verify imports exist)
- Outdated crypto examples (MD5, SHA1 for passwords)
- Incomplete error handling that swallows security failures
- Copy-pasted Stack Overflow code without license consideration
- Overly permissive CORS or auth bypass "for testing"

## Step 5 — SonarQube MCP (Optional)

If SonarQube MCP server is configured, also call:

- `search_sonar_issues` — BLOCKER/HIGH security issues
- `search_security_hotspots` — hotspots needing review
- `analyze_code_snippet` — targeted snippet analysis

Skip this step if MCP is unavailable; rely on CLI tools above.

## Step 6 — Report

```markdown
# OSS Security Review Report

## Overview
- Target: [path or branch]
- Scan date: [date]
- Verdict: [PASS | REVIEW REQUIRED | BLOCK]

## Dependency Vulnerabilities
| Severity | Package | Version | CVE/ID | Recommendation |
|----------|---------|---------|--------|----------------|
| HIGH | example | 1.0.0 | CVE-2024-XXXX | Upgrade to 1.0.1 |

## Code Findings
| Severity | Location | Category | Finding | Recommendation |
|----------|----------|----------|---------|----------------|
| CRITICAL | src/db.py:42 | Injection | SQL concat | Use parameterized query |

## AI Code Risks
- [finding or "None identified"]

## Action Items
- [ ] ...
```

Sort findings by severity (CRITICAL → HIGH → MEDIUM → LOW).

## Relationship to review-security

- **oss-security-review** (this skill): supply chain CVEs + OWASP patterns + dependency risk
- **review-security** (built-in): subagent diff review for local code changes

Run both for PR/release readiness when user asks for comprehensive security review.
