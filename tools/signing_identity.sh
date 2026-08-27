#!/bin/zsh
# Create the self-signed code signing identity that keeps the Accessibility
# grant across rebuilds.
#
#   ./tools/signing_identity.sh create   make it, once
#   ./tools/signing_identity.sh status   is it there
#   ./tools/signing_identity.sh remove   take it back out
#
# Why this exists. An ad-hoc signature ties the app's identity to the hash of
# its own code, so every build is a different app as far as macOS is concerned.
# The Accessibility permission is stored against that identity, which is why a
# rebuilt Multi-Tofu is refused while its row in System Settings still looks
# switched on. Signing with a certificate instead makes the identity the bundle
# id plus the certificate, and neither changes when the code does.
#
# It lives in its own keychain rather than the login one. codesign needs the
# key to be reachable without a dialog on every build, and authorising a key in
# the login keychain means handing over the login password. A separate keychain
# has its own password, generated here and kept beside it. That password guards
# a self-signed certificate whose only power is to keep a permission you
# granted yourself, so it is not protecting anything worth stealing.
#
# This is not an Apple developer account and it does nothing for Gatekeeper.
# Other people downloading a release still right click and Open the first time.
set -e
NAME="${MULTITOFU_IDENTITY:-Multi-Tofu Local Signing}"
STORE="$HOME/Library/Application Support/Multi-Tofu"
KEYCHAIN="$STORE/signing.keychain-db"
PASSFILE="$STORE/signing.keychain.pass"

case "$1" in
  status)
    if [[ -f "$KEYCHAIN" ]] && security find-identity -v -p codesigning "$KEYCHAIN" 2>/dev/null | grep -q "$NAME"; then
      security find-identity -v -p codesigning "$KEYCHAIN" | grep "$NAME"
    else
      echo "no identity called $NAME"
      exit 1
    fi
    ;;

  create)
    if [[ -f "$KEYCHAIN" ]] && security find-identity -v -p codesigning "$KEYCHAIN" 2>/dev/null | grep -q "$NAME"; then
      echo "$NAME already exists, nothing to do"
      exit 0
    fi
    mkdir -p "$STORE"
    WORK="$(mktemp -d)"
    trap 'rm -rf "$WORK"' EXIT
    PASS="$(openssl rand -hex 24)"

    openssl req -x509 -newkey rsa:2048 -sha256 -days 7300 -nodes \
      -keyout "$WORK/key.pem" -out "$WORK/cert.pem" \
      -subj "/CN=$NAME/O=MinutesBack" \
      -addext "basicConstraints=critical,CA:FALSE" \
      -addext "keyUsage=critical,digitalSignature" \
      -addext "extendedKeyUsage=critical,codeSigning" >/dev/null 2>&1
    openssl pkcs12 -export -out "$WORK/id.p12" -inkey "$WORK/key.pem" \
      -in "$WORK/cert.pem" -passout "pass:$PASS" -name "$NAME" >/dev/null

    rm -f "$KEYCHAIN"
    security create-keychain -p "$PASS" "$KEYCHAIN"
    security set-keychain-settings -lut 21600 "$KEYCHAIN"
    security unlock-keychain -p "$PASS" "$KEYCHAIN"
    security import "$WORK/id.p12" -k "$KEYCHAIN" -P "$PASS" \
      -T /usr/bin/codesign -A >/dev/null
    # without this codesign answers errSecInternalComponent, which is what a
    # key it is not allowed to use looks like from the outside
    security set-key-partition-list -S apple-tool:,apple:,codesign: -s \
      -k "$PASS" "$KEYCHAIN" >/dev/null 2>&1
    security add-trusted-cert -p codeSign -k "$KEYCHAIN" "$WORK/cert.pem"

    printf '%s' "$PASS" > "$PASSFILE"
    chmod 600 "$PASSFILE"

    # the build searches the keychain list, so it has to be on it
    EXISTING=$(security list-keychains -d user | sed 's/[",]//g' | xargs)
    if ! echo "$EXISTING" | grep -q "signing.keychain"; then
      security list-keychains -d user -s ${=EXISTING} "$KEYCHAIN"
    fi

    security find-identity -v -p codesigning "$KEYCHAIN" | grep "$NAME"
    echo
    echo "Done. Rebuild once with ./tools/build_app.sh --install, grant"
    echo "Accessibility one last time, and every build after that keeps it."
    ;;

  remove)
    if [[ -f "$KEYCHAIN" ]]; then
      EXISTING=$(security list-keychains -d user | sed 's/[",]//g' | grep -v "signing.keychain" | xargs)
      security list-keychains -d user -s ${=EXISTING}
      security delete-keychain "$KEYCHAIN"
    fi
    rm -f "$PASSFILE"
    echo "removed $NAME"
    ;;

  *)
    echo "usage: $0 create|status|remove"
    exit 1
    ;;
esac
