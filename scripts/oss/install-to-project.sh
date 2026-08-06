#!/usr/bin/env bash
# Copy OSS governance tooling to another project.
# Usage: bash scripts/oss/install-to-project.sh /path/to/your-project
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/oss/install-to-project.sh /path/to/your-project"
  exit 1
fi

TARGET="$(cd "$1" && pwd)"
SOURCE="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== OSS Governance Install ==="
echo "From: $SOURCE"
echo "To:   $TARGET"
echo ""

copy_dir() {
  local name="$1"
  if [[ -d "$SOURCE/$name" ]]; then
    if [[ -d "$TARGET/$name" ]]; then
      echo "WARN: $TARGET/$name already exists — merging (existing files kept)"
      cp -Rn "$SOURCE/$name/." "$TARGET/$name/" 2>/dev/null || cp -R "$SOURCE/$name/." "$TARGET/$name/"
    else
      cp -R "$SOURCE/$name" "$TARGET/$name"
    fi
    echo "OK: $name"
  fi
}

copy_dir ".cursor"
copy_dir "scripts"

if [[ -d "$SOURCE/.github" ]]; then
  read -r -p "Copy .github/workflows (CI)? [y/N] " ans
  if [[ "$ans" == [yY] || "$ans" == [yY][eE][sS] ]]; then
    mkdir -p "$TARGET/.github/workflows"
    cp -R "$SOURCE/.github/workflows/." "$TARGET/.github/workflows/"
    echo "OK: .github/workflows"
  fi
fi

chmod +x "$TARGET/scripts/oss/scan-deps.sh" 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Next steps:"
echo "  1. Open $TARGET in Cursor"
echo "  2. Edit .cursor/oss-policy.md for your product"
echo "  3. Follow docs/TEST-SCENARIOS.md phase by phase"
