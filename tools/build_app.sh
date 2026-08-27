#!/bin/zsh
# Package Multi-Tofu.app so the Accessibility grant attaches to the app itself
# instead of Terminal.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# icon first, PyInstaller needs it at bundle time
./.venv/bin/python tools/make_icon.py

./.venv/bin/python -m PyInstaller --noconfirm --clean --windowed \
  --name "Multi-Tofu" \
  --osx-bundle-identifier fr.multitofu.app \
  --add-data "$ROOT/multitofu/assets:multitofu/assets" \
  --icon "$ROOT/build/MultiTofu.icns" \
  --target-arch universal2 \
  --distpath "$ROOT/build/staging" --workpath "$ROOT/build/pyinstaller" \
  --specpath "$ROOT/build" \
  launcher.py

APP="$ROOT/build/staging/Multi-Tofu.app"
PLIST="$APP/Contents/Info.plist"

# menu bar only, no dock icon
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 0.1.0" "$PLIST" 2>/dev/null || true

# strip extended attributes and AppleDouble files, codesign refuses to sign
# over com.apple.FinderInfo and friends
xattr -cr "$APP"
find "$APP" -name "._*" -delete 2>/dev/null || true

# a stable ad-hoc identity keeps the Accessibility grant across rebuilds.
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
  rm -rf "$ROOT/build/staging"
  echo "installed /Applications/Multi-Tofu.app"
fi
