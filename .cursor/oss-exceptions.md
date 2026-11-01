# OSS Exception Register

Exceptions approved by the OSS Manager under [`oss-policy.md`](oss-policy.md) → *Escalation*.
`scripts/oss/exception-review.py` reads this table: an item listed here with a future **Expires** date is treated as approved.

- **Type**: `license` (Item = SPDX expression as reported) or `cve` (Item = CVE / GHSA id).
- **Package**: `ecosystem:name` (e.g. `pypi:pymupdf`, `npm:lodash`).
- **Expires**: required. Re-review on expiry; maximum 12 months.
- Add a row only after written OSS Manager sign-off, and link it in **Reference**.

| ID | Package | Type | Item | Approved by | Approved | Expires | Reason | Reference |
|----|---------|------|------|-------------|----------|---------|--------|-----------|
