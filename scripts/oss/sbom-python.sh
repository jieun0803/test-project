#!/usr/bin/env bash
# Generate a CycloneDX SBOM for a Python project.
#
# Usage: bash scripts/oss/sbom-python.sh [project-dir] [output-file]
#   project-dir  default: .
#   output-file  default: <project-dir>/bom-python.json
#
# Source, in order:
#   1. requirements.txt  -> cyclonedx-py requirements (declared deps, no install)
#   2. pyproject.toml    -> install the project into a throwaway venv, then
#                           cyclonedx-py environment (resolved direct + transitive deps)
# Exit code: 0 SBOM written, 1 no Python manifest, 2 generation failed.
set -euo pipefail

DIR="$(cd "${1:-.}" && pwd)"
OUT="${2:-$DIR/bom-python.json}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac

if ! command -v cyclonedx-py >/dev/null 2>&1; then
  echo "Installing cyclonedx-bom..."
  python3 -m pip install --quiet --user cyclonedx-bom 2>/dev/null \
    || python3 -m pip install --quiet --user --break-system-packages cyclonedx-bom
  export PATH="$(python3 -m site --user-base)/bin:$PATH"
fi

if [ -f "$DIR/requirements.txt" ]; then
  echo "Source: $DIR/requirements.txt"
  cyclonedx-py requirements "$DIR/requirements.txt" --of JSON -o "$OUT" 2>/dev/null || exit 2
elif [ -f "$DIR/pyproject.toml" ]; then
  echo "Source: $DIR/pyproject.toml (installed into a temporary venv)"
  VENV="$(mktemp -d)/venv"
  trap 'rm -rf "$(dirname "$VENV")"' EXIT
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet "$DIR" || exit 2
  cyclonedx-py environment "$VENV" --of JSON -o "$OUT" 2>/dev/null || exit 2
else
  echo "No requirements.txt or pyproject.toml in $DIR" >&2
  exit 1
fi

python3 - "$OUT" <<'EOF'
import json, sys
bom = json.load(open(sys.argv[1]))
comps = bom.get("components", [])
unpinned = [c["name"] for c in comps if not c.get("version")]
print(f"SBOM: {sys.argv[1]} (CycloneDX {bom['specVersion']}, {len(comps)} components)")
if unpinned:
    print(f"WARNING: {len(unpinned)} unpinned: {', '.join(unpinned)}")
EOF
