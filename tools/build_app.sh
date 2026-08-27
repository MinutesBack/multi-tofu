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
  --distpath "$ROOT/dist" --workpath "$ROOT/build/pyinstaller" \
  --specpath "$ROOT/build" \
  launcher.py

APP="$ROOT/dist/Multi-Tofu.app"
PLIST="$APP/Contents/Info.plist"

# menu bar only, no dock icon
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 0.1.0" "$PLIST" 2>/dev/null || true

# strip extended attributes, codesign refuses to sign over them
xattr -cr "$APP"

# a stable ad-hoc identity keeps the Accessibility grant across rebuilds
codesign --force --deep --sign - --identifier fr.multitofu.app "$APP"
codesign -dv "$APP" 2>&1 | head -3
echo "built $APP"

# ./tools/build_app.sh --install puts it where macOS expects it, which matters
# because the Accessibility grant is tied to the app's location
if [[ "$1" == "--install" ]]; then
  rm -rf "/Applications/Multi-Tofu.app"
  cp -R "$APP" "/Applications/Multi-Tofu.app"
  xattr -cr "/Applications/Multi-Tofu.app"
  codesign --force --deep --sign - --identifier fr.multitofu.app "/Applications/Multi-Tofu.app"
  # leave exactly one launchable copy on disk, two is how you end up granting
  # permission to the wrong one
  rm -rf "$ROOT/dist"
  echo "installed /Applications/Multi-Tofu.app"
fi
