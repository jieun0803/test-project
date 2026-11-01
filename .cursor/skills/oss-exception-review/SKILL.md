---
name: oss-exception-review
description: >
  Governance assistant that lists items needing OSS Manager exception approval
  (blocked / review-required licenses, CRITICAL / HIGH CVEs) and checks them against
  the exception register for approved, expired and stale entries. Use when the user asks
  for exception review, items needing OSS Manager approval, waiver status, or
  "OSS Manager 승인이 필요한 예외 항목 정리해줘".
---

# OSS Exception Review

Policy: [`.cursor/oss-policy.md`](../../oss-policy.md) → *Escalation*. Register: [`.cursor/oss-exceptions.md`](../../oss-exceptions.md).

## Step 1 — Run the review

```bash
python3 scripts/oss/exception-review.py [PROJECT_DIR]            # license + CVE (OSV API)
python3 scripts/oss/exception-review.py [PROJECT_DIR] --no-cve   # license only (offline-ish)
python3 scripts/oss/exception-review.py [PROJECT_DIR] --json
```

Exit code: 0 nothing to approve, 1 pending or expired items, 3 error.

## Step 2 — Present the result

Show the `# OSS Exception Review` report, then for each **Pending** item write an approval request the OSS Manager can sign:

| Field | Content |
|-------|---------|
| Package / Item | e.g. `pypi:pymupdf` / `AGPL-3.0 OR LicenseRef-Artifex-Commercial` |
| Risk | Policy bucket + why (oss-license-compliance / oss-security-review) |
| Usage scope | runtime / dev-only, modified or not, SaaS or shipped |
| Alternatives | Permissive replacement or fixed version, and the cost of switching |
| Proposed expiry | ≤ 12 months |

Then list **Expired** (re-request or remove the dependency), **Unpinned** (pin to a fixed version first; these are not exception items yet) and **Stale** (close the register row).

## Rules

- Never add a row to `oss-exceptions.md` yourself. Rows are added only after written OSS Manager sign-off; draft the row text for the user instead.
- Do not treat Review Required as approved because the deployment is SaaS. Show the reasoning and let the OSS Manager decide.
- An exception covers one package + one item (license expression or CVE). A version bump that changes the license or adds a new CVE needs a new exception.
