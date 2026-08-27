"""Reproduces the freeze: record a shortcut, then change language.

The capture callback used to run inside the event tap and call a function that
shelled out to `defaults`, which stalls the main run loop. This asserts the
main thread keeps ticking throughout.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MULTITOFU_QUIET"] = "1"
os.environ.setdefault("MULTITOFU_CONFIG", "/tmp/multitofu_flow_test.json")

from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSApp
from Foundation import NSObject, NSTimer

from multitofu.accounts import Account
from multitofu.app import DosoftApp
from multitofu.classes import to_slug

RESULTS = []
TICKS = [0]
CAST = [("Account 1", "Iop"), ("Account 2", "Cra"), ("Account 3", "Eniripsa")]


def record(ok, label, detail=""):
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label:34} {detail}", flush=True)


class Flow(NSObject):
    def tick_(self, timer):
        TICKS[0] += 1

    def run_(self, timer):
        app = self.app
        app.scan_timer and app.scan_timer.invalidate()
        app.scanner.accounts = [Account({
            "name": n, "pid": 0, "window": None, "role": "none",
            "title": f"{n} - {c} - 3.6.10.11 - Release", "class_name": c,
            "slug": to_slug(c), "active": True, "team": "Team 1",
            "is_menu": False}) for n, c in CAST]
        app.prefs.show()
        record(app.prefs.window is not None, "settings window opens")

        # arm a shortcut recording the way the record button does
        app.hotkeys_running = True
        button = app.prefs.global_buttons["next"]
        app.prefs._capture(button, lambda bind: app.config.data["binds"].__setitem__("next", bind))
        record(app.hotkeys.capture is not None, "capture armed")

        # the tap would call this synchronously, so time it as the tap sees it
        before = TICKS[0]
        started = time.time()
        app.hotkeys.capture(99, 0)
        elapsed = (time.time() - started) * 1000
        record(elapsed < 50, "capture returns immediately",
               f"{elapsed:.1f}ms inside the tap callback")
        record(app.config.data["binds"]["next"]["keycode"] == 99,
               "the new shortcut is stored")

        self.before_ticks = before
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.6, self, "afterCapture:", None, False)

    def afterCapture_(self, timer):
        app = self.app
        record(TICKS[0] > self.before_ticks, "run loop kept ticking",
               f"{TICKS[0] - self.before_ticks} ticks since the keypress")

        started = time.time()
        popup = app.prefs.language_popup
        popup.selectItemAtIndex_(app.prefs.language_codes.index("fr"))
        app.prefs.languageChanged_(popup)
        elapsed = (time.time() - started) * 1000
        record(elapsed < 200, "language change returns immediately", f"{elapsed:.1f}ms")
        record(app.hotkeys.capture is None, "a stale capture cannot survive it")

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.8, self, "finish:", None, False)

    def finish_(self, timer):
        app = self.app
        record(app.prefs.window is not None and app.prefs.window.isVisible(),
               "settings still alive after the switch")
        record(app.config.data["language"] == "fr", "language actually changed")
        total, passed = len(RESULTS), sum(1 for r in RESULTS if r)
        print(f"\n{passed}/{total} checks passed")
        NSApp.terminate_(self)


app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
delegate = DosoftApp.alloc().init()
app.setDelegate_(delegate)
flow = Flow.alloc().init()
flow.app = delegate
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    0.05, flow, "tick:", None, True)
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    1.2, flow, "run:", None, False)
app.run()
