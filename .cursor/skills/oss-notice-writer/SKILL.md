---
name: oss-notice-writer
description: >
  Generates and updates OSS NOTICE/attribution HTML files for releases. Use when
  the user mentions OSS notice, open source licenses page, attribution file, release
  notice update, or asks to add/remove libraries from the notice document.
---

# OSS Notice Writer

Automate OSS attribution pages per release. Policy: [`.cursor/oss-policy.md`](../../oss-policy.md).

## Step 1 — Gather Inputs

Required from user:

- Platform (Android / iOS / Web / other)
- Version number (e.g. 2.64.0)
- Libraries to add (name + license if known)
- Libraries to remove (name)

Optional:

- Path to previous notice file (auto-detect latest if omitted)
- SBOM file (CycloneDX JSON) for bulk library list

## Step 2 — Select Base Template

1. Find the previous version notice file (e.g. `notices/ios/2.63.0.html`).
2. Copy structure and styling; do not drop existing entries.
3. If no prior file exists, use the HTML skeleton in `scripts/oss/notice-template.html`.

## Step 3 — Update Library List

For each **added** library:

1. Insert alphabetically by library name.
2. Include: name, version (if known), copyright holder, license SPDX ID.
3. Fetch full license text from SPDX (https://spdx.org/licenses/) or npm/PyPI registry.
4. Wrap in standard HTML block:

```html
<section class="oss-library" id="library-alamofire">
  <h3>Alamofire (5.8.0)</h3>
  <p>Copyright (c) Alamofire Software Foundation</p>
  <p>License: MIT</p>
  <pre class="license-text">[full license text]</pre>
</section>
```

For each **removed** library: delete its `<section>` block.

## Step 4 — Validate

Run validation script:

```bash
python scripts/oss/validate-notice.py path/to/new-notice.html
```

Checks:

- Alphabetical order of library names
- Every section has name, license, and license text
- No duplicate library IDs
- Valid HTML structure

## Step 5 — Save and Summarize

1. Save to versioned path: `notices/{platform}/{version}.html`
2. Update version router/config if the project uses one (e.g. `NoticeVersionRouter.java`).
3. Output change summary:

```markdown
# OSS Notice Update

- Base: [previous file]
- Output: [new file]
- Added: [list]
- Removed: [list]
- Validation: PASS/FAIL
- Reminder: Regenerate SBOM and run license audit
```

## SBOM Integration

When CycloneDX SBOM is available:

1. Parse `bom.json` components.
2. Diff against previous SBOM to find added/removed packages.
3. Pre-fill add/remove lists before manual edits.

Generate SBOM (examples):

- Node: `@cyclonedx/cyclonedx-npm`
- Gradle: `org.cyclonedx.bom` plugin
- Python: `cyclonedx-bom`

## Unregistered Licenses

If license is not in SPDX list:

1. Draft notice entry from package LICENSE file.
2. Mark as `[DRAFT — legal review required]` in summary.
3. Do not ship until OSS Manager approves.
