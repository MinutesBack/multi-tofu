"""Render the README screenshots without capturing the desktop behind them."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MULTITOFU_QUIET"] = "1"
os.environ.setdefault("MULTITOFU_CONFIG", "/tmp/multitofu_shots.json")

from AppKit import (NSApplication, NSApplicationActivationPolicyRegular, NSApp,
                    NSBitmapImageFileTypePNG, NSMakeRect)
from Foundation import NSObject, NSTimer

from multitofu.app import DosoftApp
from multitofu.accounts import Account
from multitofu.classes import to_slug
from multitofu.radial import Wheel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

CAST = [("Account 1", "Iop", "Team 1", "damage"), ("Account 2", "Cra", "Team 1", "damage"),
        ("Account 3", "Eniripsa", "Team 1", "healer"), ("Account 4", "Sacrieur", "Team 2", "tank"),
        ("Account 5", "Xelor", "Team 2", "support"), ("Account 6", "Sadida", "Team 2", "scout")]


def fake_accounts():
    return [Account({"name": n, "pid": 0, "window": None,
                     "title": f"{n} - {c} - 3.6.10.11 - Release",
                     "class_name": c, "slug": to_slug(c), "active": True,
                     "team": t, "role": r, "is_menu": False}) for n, c, t, r in CAST]


def save_view(view, path):
    rect = view.bounds()
    rep = view.bitmapImageRepForCachingDisplayInRect_(rect)
    view.cacheDisplayInRect_toBitmapImageRep_(rect, rep)
    data = rep.representationUsingType_properties_(NSBitmapImageFileTypePNG, {})
    data.writeToFile_atomically_(path, True)
    print("wrote", path)


class Shots(NSObject):
    def wheel_(self, timer):
        entries = [{"name": n, "slug": to_slug(c), "role": r, "class_name": c}
                   for n, c, _, r in CAST]
        wheel = Wheel(self.app.config)
        wheel._ensure_panel()
        wheel.entries = entries
        wheel.view.entries = entries
        wheel.view.hover = 4
        wheel.hover = 4
        wheel.view.setNeedsDisplay_(True)
        wheel.view.displayIfNeeded()
        save_view(wheel.view, os.path.join(DOCS, "wheel.png"))
        self.wheel = wheel

    def prefs_(self, timer):
        self.app.scan_timer and self.app.scan_timer.invalidate()
        self.app.scanner.accounts = fake_accounts()
        self.app.config.data["leader_name"] = "Account 1"
        self.app.config.data["roles"] = {n: r for n, _, _, r in CAST}
        self.app.prefs.show()

    def grabPrefs_(self, timer):
        window = self.app.prefs.window
        number = window.windowNumber()
        subprocess.run(["screencapture", "-x", "-o", "-l", str(number),
                        os.path.join(DOCS, "preferences.png")])
        print("wrote", os.path.join(DOCS, "preferences.png"))
        NSApp.terminate_(self)


app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
delegate = DosoftApp.alloc().init()
app.setDelegate_(delegate)

shots = Shots.alloc().init()
shots.app = delegate
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(1.4, shots, "wheel:", None, False)
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(2.2, shots, "prefs:", None, False)
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(3.8, shots, "grabPrefs:", None, False)
app.run()
