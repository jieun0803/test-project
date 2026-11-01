# Known Licenses (Package Cache)

Package-level cache of **verified** license results. Check this file before calling a registry or GitHub API.

- Policy column follows [`.cursor/oss-policy.md`](../../../oss-policy.md) (deployment: SaaS). If the policy changes, re-derive the Policy column. Do not trust it blindly.
- Only add entries you verified from a primary source (registry metadata, LICENSE file in the repo). Never add a guess.
- Dual / choice licenses (`A OR B`): record the expression as published, and write the option the project elects in **Notes**.

## How to Use

1. **Hit**: package found and `Verified` is within 180 days → use the cached SPDX and Policy, and cite `known-licenses.md (verified YYYY-MM-DD)` in the report.
2. **Stale**: `Verified` older than 180 days, or the requested version is a new major version → re-verify, then update the row (version, date).
3. **Miss**: look up via Step 2 of the skill, then **append a row** to the matching ecosystem table with today's date and the source.
4. **Mismatch**: if a fresh lookup differs from the cache, trust the fresh lookup, update the row, and add the change to Notes (e.g. `was LGPL-2.1 until 1.x`).

Source codes: `npm` = registry.npmjs.org `license` field · `pypi-expr` = PyPI `license_expression` (PEP 639) · `pypi-lic` = PyPI `license` field · `pypi-cls` = PyPI trove classifier · `gh` = GitHub repo LICENSE (`/repos/{owner}/{repo}/license`)

## npm

| Package | Version checked | SPDX | Policy | Source | Verified | Notes |
|---------|-----------------|------|--------|--------|----------|-------|
| axios | 1.21.0 | MIT | Allowed | npm | 2026-11-01 | |
| dayjs | 1.11.23 | MIT | Allowed | npm | 2026-11-01 | |
| express | 5.3.0 | MIT | Allowed | npm | 2026-11-01 | |
| jszip | 3.10.2 | MIT OR GPL-3.0-or-later | Allowed | npm | 2026-11-01 | Dual license: elect **MIT**. Do not elect GPL |
| lodash | 4.18.1 | MIT | Allowed | npm | 2026-11-01 | Fixture: mit-package, vulnerable-package (4.17.15 has CVEs) |
| minimist | 1.2.8 | MIT | Allowed | npm | 2026-11-01 | Fixture: vulnerable-package (1.2.0 has CVEs) |
| node-forge | 1.4.2 | BSD-3-Clause OR GPL-2.0 | Allowed | npm | 2026-11-01 | Dual license: elect **BSD-3-Clause** |
| react | 19.3.1 | MIT | Allowed | npm | 2026-11-01 | |
| readline | 1.3.0 | Apache-2.0 | Allowed | gh (maleck13/readline) | 2026-11-01 | npm `license` says non-SPDX `BSD`, repo LICENSE is Apache-2.0. Permissive either way. **Not GNU Readline** (see Other) |

## PyPI

| Package | Version checked | SPDX | Policy | Source | Verified | Notes |
|---------|-----------------|------|--------|--------|----------|-------|
| certifi | 2026.10.23 | MPL-2.0 | Review Required | pypi-lic | 2026-11-01 | Transitive via requests/httpx. SaaS: file-level copyleft not triggered unless modified and distributed |
| chromadb | 1.5.9 | Apache-2.0 | Allowed | pypi-cls | 2026-11-01 | |
| httpx | 0.28.1 | BSD-3-Clause | Allowed | pypi-lic | 2026-11-01 | |
| langchain | 1.4.7 | MIT | Allowed | pypi-lic | 2026-11-01 | |
| langchain-community | 0.4.2 | MIT | Allowed | pypi-lic | 2026-11-01 | |
| langchain-openai | 1.7.3 | MIT | Allowed | pypi-lic | 2026-11-01 | |
| langchain-upstage | 0.7.7 | MIT | Allowed | pypi-lic | 2026-11-01 | |
| marisa-trie | 1.4.1 | MIT AND (BSD-2-Clause OR LGPL-2.1-or-later) | Allowed | pypi-expr | 2026-11-01 | Transitive via spacy. Elect **BSD-2-Clause** → no LGPL obligation. Older audits listed it as LGPL-2.1 |
| nltk | 3.10.4 | Apache-2.0 | Allowed | pypi-lic | 2026-11-01 | |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Allowed* | pypi-expr | 2026-11-01 | *Zlib is permissive but not in the policy Allowed list |
| openai | 3.42.0 | Apache-2.0 | Allowed | pypi-expr | 2026-11-01 | |
| pandas | 3.1.0 | BSD-3-Clause | Allowed | pypi-expr | 2026-11-01 | |
| pdfplumber | 0.11.10 | MIT | Allowed | pypi-cls | 2026-11-01 | Recommended replacement for PyMuPDF |
| pydantic | 2.14.2 | MIT | Allowed | pypi-expr | 2026-11-01 | |
| pymupdf | 2.0 | AGPL-3.0 OR LicenseRef-Artifex-Commercial | **Blocked** | pypi-lic | 2026-11-01 | AGPL triggers on SaaS network use. Replace with pdfplumber / pypdf, or buy the Artifex commercial license |
| pypdf | 6.21.4 | BSD-3-Clause | Allowed | pypi-expr | 2026-11-01 | |
| python-dotenv | 1.2.4 | BSD-3-Clause | Allowed | pypi-lic | 2026-11-01 | |
| python-multipart | 0.0.33 | Apache-2.0 | Allowed | pypi-expr | 2026-11-01 | |
| requests | 2.34.2 | Apache-2.0 | Allowed | pypi-lic | 2026-11-01 | |
| scikit-learn | 1.9.1 | BSD-3-Clause | Allowed | pypi-expr | 2026-11-01 | |
| spacy | 3.8.18 | MIT | Allowed | pypi-lic | 2026-11-01 | Pulls marisa-trie (see above) |
| sqlalchemy | 2.1.6 | MIT | Allowed | pypi-expr | 2026-11-01 | |
| streamlit | 1.66.1 | Apache-2.0 | Allowed | pypi-expr | 2026-11-01 | |
| torch | 2.15.0 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND ISC AND MIT AND Zlib | Allowed* | pypi-expr | 2026-11-01 | *BSL-1.0, LLVM-exception, Zlib are permissive but not in the policy Allowed list |
| tqdm | 4.70.1 | MPL-2.0 AND MIT | Review Required | pypi-lic | 2026-11-01 | MPL-2.0 part. SaaS: obligations not triggered unless tqdm files are modified and distributed |
| transformers | 5.22.1 | Apache-2.0 | Allowed | pypi-lic | 2026-11-01 | PyPI field says "Apache 2.0 License" (normalized) |
| tzdata | 2026.6 | Apache-2.0 | Allowed | pypi-lic | 2026-11-01 | |

## Other (system libraries, name collisions)

| Package | Version checked | SPDX | Policy | Source | Verified | Notes |
|---------|-----------------|------|--------|--------|----------|-------|
| GNU Readline (C library) | 6.0+ | GPL-3.0-or-later | **Blocked** | gnu.org | 2026-11-01 | Different from npm `readline` (Apache-2.0). Python's `readline` stdlib module links GNU Readline on Linux builds |
