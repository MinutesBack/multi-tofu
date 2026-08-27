#!/bin/zsh
# Package Multi-Tofu.app so the Accessibility grant attaches to the app itself
# instead of Terminal.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Build outside the project. ~/Documents is an iCloud file provider and it
# re-stamps com.apple.FinderInfo and com.apple.fileprovider onto the bundle
# faster than xattr can strip them, and codesign refuses to sign over those.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# icon first, PyInstaller needs it at bundle time
./.venv/bin/python tools/make_icon.py

./.venv/bin/python -m PyInstaller --noconfirm --clean --windowed \
  --name "Multi-Tofu" \
  --osx-bundle-identifier fr.multitofu.app \
  --add-data "$ROOT/multitofu/assets:multitofu/assets" \
  --icon "$ROOT/build/MultiTofu.icns" \
  --target-arch universal2 \
  --distpath "$STAGE/dist" --workpath "$STAGE/work" \
  --specpath "$ROOT/build" \
  launcher.py

APP="$STAGE/dist/Multi-Tofu.app"
PLIST="$APP/Contents/Info.plist"

# menu bar only, no dock icon
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
# the version belongs to the package, not to this script
VERSION="$(./.venv/bin/python -c 'import multitofu; print(multitofu.__version__)')"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$PLIST"

# strip extended attributes and AppleDouble files, codesign refuses to sign
# over com.apple.FinderInfo and friends
xattr -cr "$APP"
find "$APP" -name "._*" -delete 2>/dev/null || true

# Ad-hoc signing keys the identity to the code hash, so every rebuild is a new
# app to TCC and the Accessibility grant has to be given again. The Settings
# window has a Fix access button that resets the record for exactly this.
# PlistBuddy and PyInstaller both leave extended attributes behind, and
# codesign refuses to sign over them, so clean and retry once.
if ! codesign --force --deep --sign - --identifier fr.multitofu.app "$APP" 2>/dev/null; then
  xattr -cr "$APP"
  find "$APP" -name "._*" -delete 2>/dev/null || true
  codesign --force --deep --sign - --identifier fr.multitofu.app "$APP"
fi
codesign --verify --deep --strict "$APP" || { echo "signature is not valid"; exit 1; }
codesign -dv "$APP" 2>&1 | head -3
echo "built $APP"
mkdir -p "$ROOT/dist"

# ./tools/build_app.sh --install puts it where macOS expects it, which matters
# because the Accessibility grant is tied to the app's location
if [[ "$1" == "--install" ]]; then
  rm -rf "/Applications/Multi-Tofu.app"
  cp -R "$APP" "/Applications/Multi-Tofu.app"
  xattr -cr "/Applications/Multi-Tofu.app"
  find "/Applications/Multi-Tofu.app" -name "._*" -delete 2>/dev/null || true
  codesign --force --deep --sign - --identifier fr.multitofu.app "/Applications/Multi-Tofu.app"
  # leave exactly one launchable copy on disk, two is how you end up granting
  # permission to the wrong one
  # a second copy is a second Dock icon and a second Spotlight hit, and it is
  # how you end up granting Accessibility to the one you are not running
  echo "installed /Applications/Multi-Tofu.app $VERSION"
fi
