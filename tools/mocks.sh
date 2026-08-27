#!/bin/zsh
# start|stop the mock clients
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/build/DofusMock.app"
case "$1" in
  start)
    open -n "$APP" --args --title "Account 1 - Iop - 3.6.10.11 - Release" --pos 80,520
    sleep 0.6
    open -n "$APP" --args --title "Account 2 - Cra - 3.6.10.11 - Release" --pos 520,520
    sleep 0.6
    open -n "$APP" --args --title "Account 3 - Eniripsa - 3.6.10.11 - Release" --pos 960,520
    sleep 0.6
    open -n "$APP" --args --title "Dofus 3.6.10.11 - Release" --pos 80,180
    sleep 1.0
    pgrep -f DofusMock | tr '\n' ' '; echo
    ;;
  stop)
    pkill -f DofusMock 2>/dev/null
    echo stopped
    ;;
esac
