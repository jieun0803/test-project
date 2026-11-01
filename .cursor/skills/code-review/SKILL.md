---
name: code-review
description: >
  /code-review — OSS governance review of the current changes (working tree, or a branch
  against its base): licenses of added dependencies, blocked code patterns from
  oss-policy.md, and copied third-party code. Use when the user types /code-review or asks
  to review the current diff, a branch, or a PR before merge ("변경사항 리뷰해줘").
---

# /code-review

Policy: [`.cursor/oss-policy.md`](../../oss-policy.md).

## Step 1 — Pick the scope

| Request | Command |
|---------|---------|
| `/code-review` (uncommitted work) | `python3 scripts/oss/review-diff.py` |
| `/code-review main` or "this branch / PR" | `python3 scripts/oss/review-diff.py --base main` (use the PR's base branch) |
| A subfolder / submodule | add `--repo <dir>` (must be inside the working directory) |

Exit code: 0 PASS, 1 REVIEW REQUIRED, 2 BLOCK, 3 error.

## Step 2 — Run the scanner, then read the diff

1. Run the command and keep its findings as is. They are deterministic. Do not drop a BLOCK finding without saying why (e.g. a test fixture or a false positive, with the line).
2. Read the diff yourself (`git diff [--base]...`) for what regexes miss, in this order:
   - Injection beyond SQL: command (`subprocess(..., shell=True)` with input), path traversal, SSRF, XSS (`innerHTML`, `dangerouslySetInnerHTML`)
   - Secrets in config / test files, logs that print tokens or personal data
   - Unsafe deserialization (`pickle.load`, `yaml.load` without SafeLoader, `torch.load` on untrusted files)
   - AI-generated code risks: invented package names (check that each new dependency exists in its registry), deprecated APIs, copied snippets without attribution
   - Correctness bugs in the changed lines (only when clear and concrete)
3. For each new dependency marked REVIEW or BLOCK, apply oss-license-compliance. For any version pin change, run oss-security-review on that package.

## Step 3 — Report

```markdown
# Code Review

- Scope: <working tree | base...HEAD> · <N> files
- Verdict: **PASS | REVIEW REQUIRED | BLOCK**

## Findings
| Severity | Location | Rule | Issue | Fix |
|----------|----------|------|-------|-----|
| BLOCK | `app.py:10` | sql-concat | ... | parameterized query |

## Action Items
- [ ] ...
```

- Verdict is the worst of scanner + manual findings.
- Point to `file:line` for every finding and give a concrete fix.
- Dependency changes → remind to update NOTICE (oss-notice-writer) and the SBOM.
- Escalate license exceptions and HIGH CVE waivers to the OSS Manager (oss-exception-review). Do not approve them.
