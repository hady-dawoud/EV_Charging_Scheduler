# Android Release Runbook

Scope: EV-side mobile application release builds for tester APK distribution.

Do not store or commit private keystores, Gradle signing secrets, APK/AAB files, `release-artifacts/`, build outputs, `.keystore`, `.jks`, `.p12`, or local secret files.

## Current Recommended Tester APK

```text
GitHub Release: v0.1.2
Asset: ev-smart-charging-v0.1.2.apk
Status: release-signed and verified with apksigner
Android versionCode: 3
Android versionName: 0.1.2
SHA256: EA8D2091694329FF4E6836EB269694AC2A6EBCEBC903C2747320E4F20E1BD99B
```

`v0.1.2` is the recommended Android APK for testers.

Older APK releases `v0.1.0` and `v0.1.1` are retained only for history and should not be recommended for new tester installs.

## Source Configuration

Release metadata lives in:

```text
apps/mobile/android/app/build.gradle
```

Expected values for `v0.1.2`:

```gradle
versionCode 3
versionName "0.1.2"
```

The release build uses `signingConfigs.release` and reads signing configuration from external Gradle `EV_UPLOAD_*` properties. Keep those properties outside the repo.

The debug build uses the standard tracked Android debug keystore:

```text
apps/mobile/android/app/debug.keystore
```

That debug keystore is acceptable to keep tracked. Private release/upload keystores are not.

## Build And Verify

From the repo root:

```powershell
cd apps/mobile
npm run typecheck
cd android
.\gradlew.bat clean
```

If needed, remove the app build directory only after verifying the resolved path is inside `apps/mobile/android`:

```powershell
$target = Join-Path (Get-Location) 'app\build'
$root = (Resolve-Path -LiteralPath (Get-Location)).Path
if (Test-Path -LiteralPath $target) {
  $resolved = (Resolve-Path -LiteralPath $target).Path
  if (-not ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase))) {
    throw "Refusing to remove outside Android workspace: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Recurse -Force
}
```

Build the release APK:

```powershell
.\gradlew.bat assembleRelease
cd ..\..\..
```

Verify with `apksigner` from Android SDK build-tools:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\build-tools\<version>\apksigner.bat" verify --verbose --print-certs apps\mobile\android\app\build\outputs\apk\release\app-release.apk
```

Expected result includes:

```text
Verifies
Verified using v2 scheme (APK Signature Scheme v2): true
Number of signers: 1
```

Copy the verified APK for upload:

```powershell
New-Item -ItemType Directory -Force -Path release-artifacts | Out-Null
Copy-Item -LiteralPath apps\mobile\android\app\build\outputs\apk\release\app-release.apk -Destination release-artifacts\ev-smart-charging-v0.1.2.apk -Force
Get-FileHash -Algorithm SHA256 -LiteralPath release-artifacts\ev-smart-charging-v0.1.2.apk
```

`release-artifacts/` is ignored and must not be committed.

## GitHub Release Notes

For `v0.1.2`:

```text
Tag: v0.1.2
Title: EV Smart Charging v0.1.2 - Signed Android Demo APK
Release type: Pre-release
Asset: ev-smart-charging-v0.1.2.apk
SHA256: EA8D2091694329FF4E6836EB269694AC2A6EBCEBC903C2747320E4F20E1BD99B
```

Tell testers to download the APK asset only. GitHub automatically adds source `.zip` and `.tar.gz` archives; those are not installable Android builds.

## Release Hygiene Checklist

- Confirm working tree only contains intended source/doc changes before committing.
- Run `git diff --check`.
- Run `npm run typecheck` from `apps/mobile`.
- Run `.\gradlew.bat clean` and `.\gradlew.bat assembleRelease` from `apps/mobile/android`.
- Verify the APK with `apksigner verify --verbose --print-certs`.
- Hash the exact APK uploaded to GitHub Releases.
- Do not commit APKs, AABs, `release-artifacts/`, build outputs, private signing files, Gradle signing secrets, or local secret files.
