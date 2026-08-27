#!/bin/zsh
# Build DofusMock.app, a native stand-in client used to test the rotation
# without needing several real Dofus accounts.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/DofusMock.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

clang -fobjc-arc -framework Cocoa -O1 \
      -o "$APP/Contents/MacOS/DofusMock" "$ROOT/tools/mock_client.m"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>DofusMock</string>
  <key>CFBundleIdentifier</key><string>com.ankama.dofus.mock</string>
  <key>CFBundleName</key><string>DofusMock</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>3.6.10.11</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

codesign --force --sign - "$APP" >/dev/null 2>&1 || true
echo "built $APP"
