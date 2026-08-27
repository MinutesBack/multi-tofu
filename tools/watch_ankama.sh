#!/bin/zsh
# Start Multi-Tofu when the Ankama Launcher or a Dofus client touches its data.
#
# macOS has no "when app X launches" trigger. launchd can watch paths though,
# and both the launcher and the game write to theirs on startup, so watching
# those is the closest thing to the trigger you actually want.
#
#   ./tools/watch_ankama.sh install
#   ./tools/watch_ankama.sh remove
#   ./tools/watch_ankama.sh status
set -e
LABEL="fr.multitofu.watch"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP="/Applications/Multi-Tofu.app"

case "${1:-status}" in
install)
  [ -d "$APP" ] || { echo "install $APP first"; exit 1; }
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-c</string>
    <string>pgrep -f "Multi-Tofu.app/Contents/MacOS" >/dev/null || /usr/bin/open -g -a "$APP" --args --background</string>
  </array>
  <key>WatchPaths</key>
  <array>
    <string>$HOME/Library/Application Support/zaap</string>
    <string>$HOME/Library/Application Support/Ankama</string>
    <string>$HOME/Library/Preferences/com.Ankama.Dofus.plist</string>
  </array>
  <key>ThrottleInterval</key><integer>60</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>/tmp/multitofu-watch.log</string>
  <key>StandardErrorPath</key><string>/tmp/multitofu-watch.log</string>
</dict>
</plist>
PLISTEOF
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$PLIST"
  echo "watching. Multi-Tofu starts when the Ankama Launcher or a client writes."
  ;;
remove)
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed"
  ;;
status)
  if launchctl print "gui/$UID/$LABEL" >/dev/null 2>&1; then
    echo "installed and loaded"
  else
    echo "not installed"
  fi
  ;;
esac
