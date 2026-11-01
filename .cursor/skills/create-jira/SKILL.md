---
name: create-jira
description: >
  /create-jira — registers an OSS governance finding (blocked / review-required license,
  CRITICAL / HIGH CVE, code-review BLOCK, expired exception) as a Jira issue with a fixed
  template, priority by severity and duplicate check. Use when the user types /create-jira
  or asks to file / register a Jira issue for an OSS finding ("Jira 이슈 등록해줘",
  "GPL 위반 발견 — Jira 이슈 등록해줘").
---

# /create-jira

Needs the `jira` MCP server (Cursor → Customize → MCPs, Docker running). Payloads come from
`scripts/oss/jira-issue.py`, so issues filed here and by automation share one template and one
duplicate key (`oss-fp-<hash>` label).

## Step 1 — Identify the finding(s)

Use the finding from the conversation (license audit, `/code-review`, exception review, CVE triage).
If there is none, run the matching tool first. Do not file an issue from a guess.

| Finding | type | package | item | severity |
|---------|------|---------|------|----------|
| Blocked license | `license` | `npm:name` / `pypi:name` | SPDX expression | `BLOCK` |
| Review-required license | `license` | same | SPDX expression | `REVIEW` |
| CVE | `cve` | package | CVE id | `CRITICAL` / `HIGH` |
| Code pattern | `code` | file path | rule id | `BLOCK` / `REVIEW` |

Project key: ask the user unless it is known (POC: `SCRUM`). Issue type: `작업` (Task).

## Step 2 — Build the payload (no Jira call)

```bash
python3 scripts/oss/jira-issue.py --project SCRUM --issue-type 작업 \
  --type license --package npm:readline-gpl --item GPL-3.0-only --severity BLOCK \
  --detail "<what and where>" --action "<fix>" --dry-run --json
# several findings at once: <tool> --json | python3 scripts/oss/jira-issue.py --project SCRUM --issue-type 작업 --dry-run --json
```

## Step 3 — Duplicate check, then create (Jira MCP)

For each payload:
1. `jira_search` with the payload's `dedupe_jql`. If an issue comes back, **do not create**; report its key (add a comment with `jira_add_comment` only if the user asks).
2. Otherwise `jira_create_issue`:
   - `project_key`, `summary`, `issue_type` from the payload
   - `description` = `description_markdown`
   - `additional_fields` = `{"priority": <priority>, "labels": <labels>}` (JSON string)
3. `jira_get_issue` on the new key to confirm the priority and labels were applied.

Without MCP (CI, terminal): drop `--dry-run --json` and the script creates the issues itself via REST.

## Automatic registration (no MCP)

Pipe any OSS tool's `--json` into the script. It creates via REST and skips open duplicates:

```bash
python3 scripts/oss/exception-review.py . --json | python3 scripts/oss/jira-issue.py --project SCRUM --issue-type 작업 --min-severity block
python3 scripts/oss/review-diff.py --base main --json | python3 scripts/oss/jira-issue.py --project SCRUM --issue-type 작업 --min-severity block
python3 scripts/oss/license-scan.py vendor/ --json | python3 scripts/oss/jira-issue.py --project SCRUM --issue-type 작업
```

- CI: the `jira-sync` job in `.github/workflows/oss-governance.yml` runs this on push to main once the repo has secrets `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN` and variable `JIRA_PROJECT` (optional `JIRA_ISSUE_TYPE`; use `작업` on a Korean-locale site). Only Blocked / CRITICAL items are registered.
- The same package + license gets the same fingerprint from every tool, so a pymupdf finding from `/code-review` and from the exception review map to one issue.
- Always try `--dry-run` first when running by hand; without it the script creates real issues.

## Step 4 — Report

List `created KEY` / `exists KEY` per finding with the browse URL. Never set an assignee or
close an issue on your own; exception approval stays with the OSS Manager.
