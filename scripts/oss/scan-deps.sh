#!/usr/bin/env bash
# OSS dependency scanner — license hints + vulnerability scan
# Usage: bash scripts/oss/scan-deps.sh [directory]
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

echo "=== OSS Dependency Scan ==="
echo "Root: $(pwd)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

FOUND=0

scan_npm() {
  if [[ -f package.json ]]; then
    FOUND=1
    echo "--- Node.js (package.json) ---"
    if command -v npm &>/dev/null && [[ -f package-lock.json ]]; then
      npm audit --json 2>/dev/null | head -c 50000 || npm audit 2>/dev/null || true
    elif command -v pnpm &>/dev/null; then
      pnpm audit --json 2>/dev/null | head -c 50000 || pnpm audit 2>/dev/null || true
    else
      echo "WARN: npm/pnpm not available; listing direct deps from package.json"
      node -e "const p=require('./package.json'); console.log(JSON.stringify({...p.dependencies,...p.devDependencies},null,2))" 2>/dev/null || true
    fi
    echo ""
  fi
}

find_python() {
  local candidate
  for candidate in venv/bin/python .venv/bin/python python3; do
    if [[ -x "$candidate" ]] || command -v "$candidate" &>/dev/null; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

ensure_pip_audit() {
  local python="$1"
  if "$python" -m pip_audit --version &>/dev/null; then
    return 0
  fi
  echo "Installing pip-audit into venv ($python)..."
  if ! "$python" -m pip install -q pip-audit; then
    echo "WARN: failed to install pip-audit; run: $python -m pip install pip-audit"
    return 1
  fi
  "$python" -m pip_audit --version &>/dev/null
}

scan_python() {
  if [[ -f requirements.txt ]] || [[ -f pyproject.toml ]]; then
    FOUND=1
    echo "--- Python ---"

    local python rc
    if ! python="$(find_python)"; then
      echo "WARN: Python not found"
      [[ -f requirements.txt ]] && cat requirements.txt
      echo ""
      return
    fi

    if ! ensure_pip_audit "$python"; then
      [[ -f requirements.txt ]] && cat requirements.txt
      echo ""
      return
    fi

    echo "Scanning installed packages from: $python (pip-audit --local)"
    set +e
    "$python" -m pip_audit --local --desc on
    rc=$?
    set -e
    if [[ "$rc" -eq 1 ]]; then
      echo "NOTE: pip-audit reported vulnerabilities (exit code 1)"
    elif [[ "$rc" -ne 0 ]]; then
      echo "WARN: pip-audit failed (exit code $rc)"
    fi
    echo ""
  fi
}

scan_go() {
  if [[ -f go.mod ]]; then
    FOUND=1
    echo "--- Go (go.mod) ---"
    if command -v govulncheck &>/dev/null; then
      govulncheck ./... 2>/dev/null || true
    else
      echo "WARN: govulncheck not installed (go install golang.org/x/vuln/cmd/govulncheck@latest)"
      cat go.mod
    fi
    echo ""
  fi
}

scan_rust() {
  if [[ -f Cargo.toml ]]; then
    FOUND=1
    echo "--- Rust (Cargo.toml) ---"
    if command -v cargo-audit &>/dev/null; then
      cargo audit --json 2>/dev/null || cargo audit 2>/dev/null || true
    else
      echo "WARN: cargo-audit not installed (cargo install cargo-audit)"
    fi
    echo ""
  fi
}

scan_universal() {
  echo "--- Universal (osv-scanner / trivy) ---"
  if command -v osv-scanner &>/dev/null; then
    osv-scanner --recursive . 2>/dev/null || true
  elif command -v trivy &>/dev/null; then
    trivy fs --scanners vuln,license --severity HIGH,CRITICAL . 2>/dev/null || true
  else
    echo "WARN: Install osv-scanner or trivy for cross-ecosystem scanning"
    echo "  osv-scanner: https://google.github.io/osv-scanner/"
    echo "  trivy: https://aquasecurity.github.io/trivy/"
  fi
  echo ""
}

scan_npm
scan_python
scan_go
scan_rust
scan_universal

if [[ "$FOUND" -eq 0 ]]; then
  echo "No supported dependency manifests found in $ROOT"
  echo "Supported: package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, pom.xml, build.gradle*"
  exit 0
fi

echo "=== Scan complete ==="
echo "Next: Run oss-license-compliance skill for license audit report."
