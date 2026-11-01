#!/usr/bin/env bash
# Generate a CycloneDX SBOM for an Android app with the CycloneDX Gradle plugin,
# injected through an init script (the project's build files are not modified).
#
# Usage: bash scripts/oss/sbom-android.sh <android-project> [module] [configuration] [output-dir]
#   module         default: app
#   configuration  default: releaseRuntimeClasspath  (what ships in the release APK / AAB:
#                  test, debug and build-tool classpaths are excluded)
#   output-dir     default: <project>/<module>/build/reports
# Output: <output-dir>/bom-android.json (CycloneDX 1.5, licenses from Maven POMs)
#
# Needs: JDK 17, the Android SDK (ANDROID_HOME, or sdk.dir in local.properties), the project's
# Gradle wrapper (falls back to `gradle` on PATH).
# Exit code: 0 SBOM written, 1 not an Android Gradle project, 2 Gradle failed or empty SBOM.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROJ="$(cd "${1:?usage: sbom-android.sh <android-project> [module] [configuration] [output-dir]}" && pwd)"
MODULE="${2:-app}"
CONFIG="${3:-releaseRuntimeClasspath}"
OUT="${4:-$PROJ/$MODULE/build/reports}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac

if ! ls "$PROJ"/settings.gradle* >/dev/null 2>&1 || ! grep -qs "com.android" "$PROJ/$MODULE"/build.gradle*; then
  echo "error: $PROJ is not an Android Gradle project with module '$MODULE'" >&2
  exit 1
fi
if [ ! -f "$PROJ/local.properties" ] && [ -z "${ANDROID_HOME:-}" ] && [ -d "$HOME/Library/Android/sdk" ]; then
  export ANDROID_HOME="$HOME/Library/Android/sdk"
fi

GRADLE="$PROJ/gradlew"; [ -x "$GRADLE" ] || GRADLE="gradle"
echo "Project: $PROJ · module :$MODULE · configuration $CONFIG"
if ! (cd "$PROJ" && "$GRADLE" --no-daemon -q -I "$HERE/cyclonedx-android.init.gradle" \
      -PossModule="$MODULE" -PossConfig="$CONFIG" -PossOut="$OUT" ":$MODULE:cyclonedxBom"); then
  echo "error: Gradle failed (check the Android SDK and that '$CONFIG' exists: ./gradlew :$MODULE:dependencies)" >&2
  exit 2
fi

python3 - "$OUT/bom-android.json" <<'EOF'
import json, sys
b = json.load(open(sys.argv[1]))
comps = b.get("components", [])
if not comps:
    # Gradle resolves an unknown configuration name to nothing instead of failing: never report that as clean
    print(f"error: SBOM has 0 components: check the configuration name (./gradlew :<module>:dependencies)", file=sys.stderr)
    sys.exit(2)
named = [c for c in comps if any("id" not in (l.get("license") or {}) and "expression" not in l for l in c.get("licenses") or [])]
none = [c for c in comps if not c.get("licenses")]
print(f"SBOM: {sys.argv[1]} (CycloneDX {b['specVersion']}, {len(comps)} components)")
if named: print(f"Licenses as names only ({len(named)}): " + ", ".join(sorted({c['group'] + ':' + c['name'] for c in named})[:8]))
if none: print(f"WARNING: no license in POM ({len(none)}): " + ", ".join(sorted(c['group'] + ':' + c['name'] for c in none)[:8]))
EOF
