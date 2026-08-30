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

# Sign with a stable identity if there is one.
#
# Ad-hoc signing keys the app's identity to the hash of its own code, so the
# designated requirement is a pair of cdhashes that change on every build.
# macOS stores the Accessibility grant against that requirement, which is why
# a rebuilt app is refused while its row in System Settings still looks on.
#
# A self-signed code signing certificate fixes it: the requirement becomes the
# bundle id plus the certificate, and both survive a rebuild. Create one with
#   ./tools/signing_identity.sh create
# There is no Apple developer account involved and no notarisation. It is only
# about keeping the permission, not about Gatekeeper.
IDENTITY="${MULTITOFU_IDENTITY:-Multi-Tofu Local Signing}"
SIGN_KEYCHAIN="$HOME/Library/Application Support/Multi-Tofu/signing.keychain-db"
SIGN_PASS="$HOME/Library/Application Support/Multi-Tofu/signing.keychain.pass"
if [[ -f "$SIGN_KEYCHAIN" ]] \
   && security find-identity -v -p codesigning "$SIGN_KEYCHAIN" 2>/dev/null | grep -q "$IDENTITY"; then
  SIGN_ARGS=(--sign "$IDENTITY" --keychain "$SIGN_KEYCHAIN")
  # it locks itself after six hours, so unlock before every build
  [[ -f "$SIGN_PASS" ]] && security unlock-keychain -p "$(cat "$SIGN_PASS")" "$SIGN_KEYCHAIN"
  echo "signing as $IDENTITY, the Accessibility grant carries over"
else
  SIGN_ARGS=(--sign -)
  echo "no signing identity, falling back to ad-hoc"
  echo "the Accessibility grant will have to be given again after this build"
  echo "run ./tools/signing_identity.sh create once to stop that"
fi

# PlistBuddy and PyInstaller both leave extended attributes behind, and
# codesign refuses to sign over them, so clean and retry once.
if ! codesign --force --deep "${SIGN_ARGS[@]}" --identifier fr.multitofu.app "$APP" 2>/dev/null; then
  xattr -cr "$APP"
  find "$APP" -name "._*" -delete 2>/dev/null || true
  codesign --force --deep "${SIGN_ARGS[@]}" --identifier fr.multitofu.app "$APP"
fi
codesign --verify --deep --strict "$APP" || { echo "signature is not valid"; exit 1; }
codesign -dv "$APP" 2>&1 | head -3
echo "built $APP"
mkdir -p "$ROOT/dist"
ARCHIVE="$STAGE/Multi-Tofu-$VERSION-macOS-universal.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ARCHIVE"
cp "$ARCHIVE" "$ROOT/dist/Multi-Tofu-$VERSION-macOS-universal.zip"
echo "packaged $ROOT/dist/Multi-Tofu-$VERSION-macOS-universal.zip"

# ./tools/build_app.sh --install puts it where macOS expects it, which matters
# because the Accessibility grant is tied to the app's location
if [[ "$1" == "--install" ]]; then
  rm -rf "/Applications/Multi-Tofu.app"
  ditto --noextattr "$APP" "/Applications/Multi-Tofu.app"
  xattr -cr "/Applications/Multi-Tofu.app"
  find "/Applications/Multi-Tofu.app" -name "._*" -delete 2>/dev/null || true
  codesign --force --deep "${SIGN_ARGS[@]}" --identifier fr.multitofu.app "/Applications/Multi-Tofu.app"
  codesign --verify --deep --strict "/Applications/Multi-Tofu.app"
  # leave exactly one launchable copy on disk, two is how you end up granting
  # permission to the wrong one
  # a second copy is a second Dock icon and a second Spotlight hit, and it is
  # how you end up granting Accessibility to the one you are not running
  echo "installed /Applications/Multi-Tofu.app $VERSION"
fi
