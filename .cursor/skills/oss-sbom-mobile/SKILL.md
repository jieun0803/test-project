---
name: oss-sbom-mobile
description: >
  Generates CycloneDX SBOMs for mobile apps: Android (CycloneDX Gradle plugin on the release runtime
  classpath) and iOS (CocoaPods Podfile.lock, SwiftPM Package.resolved,
  Carthage Cartfile.resolved -> CycloneDX 1.4 via Python, no Xcode needed). Use when the user asks
  for an iOS / Android SBOM, mobile dependency inventory, or "iOS SBOM 만들어줘".
---

# Mobile SBOM

Policy: [`.cursor/oss-policy.md`](../../oss-policy.md). A shipped app binary is a **Binary release**: re-check the deployment model in the policy before judging Weak Copyleft.

## iOS — Python + CycloneDX 1.4

```bash
python3 scripts/oss/sbom-ios.py <ios-project-dir> -o bom-ios.json            # licenses from CocoaPods trunk / GitHub
python3 scripts/oss/sbom-ios.py <ios-project-dir> -o bom-ios.json --validate # + schema check (cyclonedx-python-lib)
python3 scripts/oss/sbom-ios.py <ios-project-dir> --no-licenses              # offline
```

- Reads every `Podfile.lock`, `Package.resolved` (also inside `*.xcodeproj` / `*.xcworkspace`) and `Cartfile.resolved`. `Pods/`, `.build/`, `Carthage/` are skipped.
- CocoaPods subspecs (`Firebase/Analytics`) fold into one pod component. The dependency graph comes from `Podfile.lock`.
- purls: `pkg:cocoapods/<Pod>@v`, `pkg:swift/github.com/<owner>/<repo>@v`, `pkg:github/<owner>/<repo>@v` (Carthage).
- A license recorded as `Copyright: ...` / `Commercial: ...` is a **closed-source vendor SDK** (e.g. FirebaseAnalytics). Policy: *Proprietary SDK (vendor-approved only)*, so confirm the vendor terms and record the approval in `oss-exceptions.md`.

## Android — CycloneDX Gradle Plugin

```bash
bash scripts/oss/sbom-android.sh <android-project>                       # :app, releaseRuntimeClasspath
bash scripts/oss/sbom-android.sh <android-project> mobile prodReleaseRuntimeClasspath out/   # module, flavor, output dir
```

- The plugin (`org.cyclonedx.bom` 1.10.0) is injected by `scripts/oss/cyclonedx-android.init.gradle`, so the project's build files stay untouched. A project that already applies the plugin works too.
- Scope = **what ships**: `<variant>RuntimeClasspath` of the release variant. Test (`testImplementation`) and debug-only (`debugImplementation`) dependencies are excluded. With product flavors, pass the flavored name (list them with `./gradlew :app:dependencies`). An empty SBOM is treated as an error (wrong configuration name).
- Licenses come from Maven POMs. Unambiguous POM names / URLs (e.g. "Simplified BSD License") are mapped to SPDX by `sbom-diff.py` / `oss-dashboard.py`; ambiguous ones ("BSD License") stay for review.
- Needs JDK 17 and the Android SDK (`ANDROID_HOME` or `local.properties`). To make it permanent in a project instead, add `id("org.cyclonedx.bom") version "1.10.0"` and the `tasks.cyclonedxBom { ... }` block from `tests/oss-fixtures/android-app/app/build.gradle.kts`.

## After generating

- Store per release: `sboms/ios/<version>.json` → `oss-dashboard.py sboms/ios/` (distribution + timeline), `sbom-diff.py` between releases.
- NOTICE: oss-notice-writer, using the SBOM's components and licenses.
