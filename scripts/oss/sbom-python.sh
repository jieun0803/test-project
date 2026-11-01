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
  # Private venv + hash-locked wheels only: no setup scripts run, nothing installed into the system Python
  SBOM_VENV="${OSS_SBOM_VENV:-$HOME/.cache/oss-governance/sbom-venv}"
  if [ ! -x "$SBOM_VENV/bin/cyclonedx-py" ]; then
    # requirements-sbom.txt is locked for Python 3.10+ (macOS /usr/bin/python3 is 3.9)
    PY=""
    for c in python3.12 python3.13 python3.11 python3.10 python3.14 python3; do
      if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
        PY="$c"; break
      fi
    done
    if [ -z "$PY" ]; then
      echo "error: Python 3.10+ is required to install cyclonedx-bom (brew install python@3.12)" >&2
      exit 2
    fi
    echo "Installing cyclonedx-bom into $SBOM_VENV with $PY (hash-locked)..."
    "$PY" -m venv "$SBOM_VENV" || exit 2
    "$SBOM_VENV/bin/python" -m pip install --quiet --only-binary :all: --require-hashes \
      -r "$(cd "$(dirname "$0")" && pwd)/requirements-sbom.txt" || exit 2
  fi
  export PATH="$SBOM_VENV/bin:$PATH"
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
