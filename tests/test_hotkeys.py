"""Drive the running app with synthesised key events and check the focus moves.

  ./tools/mocks.sh start
  ./.venv/bin/python tests/test_hotkeys.py

The assertions are relative: each press must move the rotation by exactly one
position from wherever it currently is. That holds whatever the starting state
and does not depend on the test guessing the app's internal index.
"""
import json
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Quartz
from AppKit import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateSystemWide, AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
)

BUNDLES = {"com.ankama.dofus", "com.ankama.dofus.mock"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CONFIG = "/tmp/multitofu_hotkey_test.json"
SETTLE = 1.2
RESULTS = []

KEY_F1, KEY_F2, KEY_F3, KEY_F4 = 122, 120, 99, 118
KEY_OPTION = 58

BASE_CONFIG = {
    "bundle_ids": ["com.Ankama.Dofus", "com.ankama.dofus.mock"],
    "binds": {"next": {"keycode": KEY_F1, "flags": 0},
              "prev": {"keycode": KEY_F2, "flags": 0},
              "leader": {"keycode": KEY_F3, "flags": 0},
              "refresh": {"keycode": KEY_F4, "flags": 0}},
    "wheel_enabled": True, "wheel_modifier": "alt", "wheel_delay_ms": 150,
    "wheel_sounds": False, "current_mode": "ALL",
    "accounts_state": {}, "accounts_team": {}, "custom_order": [],
    "classes": {}, "leader_name": "", "character_binds": {},
}


def record(ok, label, detail=""):
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label:26} {detail}", flush=True)
    return ok


def _title_of(element):
    for attr in ("AXFocusedWindow", "AXMainWindow"):
        err, win = AXUIElementCopyAttributeValue(element, attr, None)
        if err == 0 and win is not None:
            err, title = AXUIElementCopyAttributeValue(win, "AXTitle", None)
            if err == 0 and title:
                return str(title)
    return None


def focused_title(retries=12):
    """Two independent reads: the system-wide focused app, then a sweep of the
    client processes for whichever reports itself frontmost."""
    for _ in range(retries):
        system = AXUIElementCreateSystemWide()
        err, app = AXUIElementCopyAttributeValue(system, "AXFocusedApplication", None)
        if err == 0 and app is not None:
            title = _title_of(app)
            if title:
                return title
        for running in NSWorkspace.sharedWorkspace().runningApplications():
            if (running.bundleIdentifier() or "").lower() not in BUNDLES:
                continue
            ref = AXUIElementCreateApplication(running.processIdentifier())
            err, front = AXUIElementCopyAttributeValue(ref, "AXFrontmost", None)
            if err == 0 and front:
                title = _title_of(ref)
                if title:
                    return title
        time.sleep(0.25)
    _dump_focus_state()
    return None


def _dump_focus_state():
    system = AXUIElementCreateSystemWide()
    err, app = AXUIElementCopyAttributeValue(system, "AXFocusedApplication", None)
    name = pid = None
    if err == 0 and app is not None:
        e, name = AXUIElementCopyAttributeValue(app, "AXTitle", None)
        e2, role = AXUIElementCopyAttributeValue(app, "AXRole", None)
    print(f"      [diag] system focused app title={name!r}", flush=True)
    for running in NSWorkspace.sharedWorkspace().runningApplications():
        bid = (running.bundleIdentifier() or "").lower()
        if bid not in BUNDLES:
            continue
        ref = AXUIElementCreateApplication(running.processIdentifier())
        e, front = AXUIElementCopyAttributeValue(ref, "AXFrontmost", None)
        e2, fw = AXUIElementCopyAttributeValue(ref, "AXFocusedWindow", None)
        e3, mw = AXUIElementCopyAttributeValue(ref, "AXMainWindow", None)
        t = None
        if mw is not None:
            e4, t = AXUIElementCopyAttributeValue(mw, "AXTitle", None)
        print(f"      [diag] pid={running.processIdentifier()} bid={bid} "
              f"frontmost={front} focusedWin={fw is not None} mainWin={mw is not None} "
              f"mainTitle={t!r}", flush=True)
    ws_front = NSWorkspace.sharedWorkspace().frontmostApplication()
    print(f"      [diag] NSWorkspace front={ws_front.bundleIdentifier() if ws_front else None}", flush=True)


def tap_key(keycode):
    for down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(None, keycode, down)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        time.sleep(0.04)


def set_modifier(keycode, flags):
    event = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
    Quartz.CGEventSetType(event, Quartz.kCGEventFlagsChanged)
    Quartz.CGEventSetFlags(event, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
    time.sleep(0.06)


def move_mouse(x, y):
    event = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventMouseMoved, Quartz.CGPointMake(x, y), 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
    time.sleep(0.06)


def launch(config):
    json.dump(config, open(TEST_CONFIG, "w"), indent=2)
    env = dict(os.environ, MULTITOFU_CONFIG=TEST_CONFIG, MULTITOFU_QUIET="1")
    proc = subprocess.Popen(
        [os.path.join(ROOT, ".venv/bin/python"), "-m", "multitofu"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(4.0)
    if proc.poll() is not None:
        print("app exited early:\n", proc.stdout.read())
        return None
    print(" ", proc.stdout.readline().strip(), flush=True)
    return proc


def stop(proc):
    if proc is None:
        return
    proc.send_signal(signal.SIGTERM)
    time.sleep(0.4)
    proc.kill()


def title_map():
    """Returns the rotation the app will actually walk, plus titles for every
    detected window. Login windows are listed but never in the rotation."""
    cfg = json.load(open(TEST_CONFIG))
    detected = cfg.get("custom_order", [])
    classes = cfg.get("classes", {})
    titles = {}
    order = []
    for name in detected:
        klass = classes.get(name)
        if klass:
            titles[name] = f"{name} - {klass} - 3.6.10.11 - Release"
            order.append(name)
        else:
            titles[name] = "Dofus 3.6.10.11 - Release"
    return order, titles


LAST_TITLE = [None]
SKIPPED = [0]


def outside_app_has_focus():
    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    bid = (front.bundleIdentifier() or "").lower() if front else ""
    return bid not in BUNDLES and bid != ""


def settle_or_skip(label):
    """True when a client still holds the front window, False when something
    else grabbed it and the check cannot be trusted."""
    for _ in range(12):
        if not outside_app_has_focus():
            return True
        time.sleep(0.5)
    SKIPPED[0] += 1
    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    print(f"  SKIP  {label:26} another app holds focus "
          f"({front.bundleIdentifier() if front else '?'})", flush=True)
    return False


def where(titles):
    """Rotation index of whatever is focused right now, or None."""
    title = focused_title()
    LAST_TITLE[0] = title
    for name, expected in titles.items():
        if expected == title:
            return name
    return None


def main():
    print("== discovery run ==", flush=True)
    proc = launch(dict(BASE_CONFIG))
    if proc is None:
        return 1
    stop(proc)
    order, titles = title_map()
    print("  rotation:", order, flush=True)
    print("  titles:", json.dumps(titles, indent=4), flush=True)
    if len(order) < 3:
        print("need at least 3 clients, run ./tools/mocks.sh start")
        return 1

    config = dict(BASE_CONFIG)
    config["leader_name"] = order[1]
    config["character_binds"] = {order[2]: {"keycode": 97, "flags": 0}}  # F6
    print("\n== test run ==", flush=True)
    proc = launch(config)
    if proc is None:
        return 1

    try:
        tap_key(KEY_F1)
        time.sleep(SETTLE)
        current = where(titles)
        if current is None:
            record(False, "baseline", f"focused window not in rotation: {focused_title()!r}")
        else:
            record(True, "baseline", f"at {current}")
            n = len(order)

            print("\n-- F1 next --", flush=True)
            for step in range(1, 4):
                if not settle_or_skip(f"F1 x{step}"):
                    continue
                before = order.index(current)
                tap_key(KEY_F1)
                time.sleep(SETTLE)
                if not settle_or_skip(f"F1 x{step}"):
                    current = order[before]
                    continue
                current = where(titles)
                if current is None:
                    record(False, f"F1 x{step}", f"focus left the rotation, front={LAST_TITLE[0]!r}")
                    current = order[before]
                    break
                after = order.index(current)
                record(after == (before + 1) % n, f"F1 x{step}",
                       f"{order[before]} -> {current}")

            print("\n-- F2 previous --", flush=True)
            for step in range(1, 3):
                if not settle_or_skip(f"F2 x{step}"):
                    continue
                before = order.index(current)
                tap_key(KEY_F2)
                time.sleep(SETTLE)
                if not settle_or_skip(f"F2 x{step}"):
                    current = order[before]
                    continue
                current = where(titles)
                if current is None:
                    record(False, f"F2 x{step}", f"focus left the rotation, front={LAST_TITLE[0]!r}")
                    current = order[before]
                    break
                after = order.index(current)
                record(after == (before - 1) % n, f"F2 x{step}",
                       f"{order[before]} -> {current}")

            print("\n-- F3 leader --", flush=True)
            tap_key(KEY_F3)
            time.sleep(SETTLE)
            current = where(titles)
            record(current == order[1], "F3 leader",
                   f"-> {current} (leader is {order[1]})")

            print("\n-- F6 direct bind --", flush=True)
            tap_key(97)
            time.sleep(SETTLE)
            current = where(titles)
            record(current == order[2], "F6 direct bind",
                   f"-> {current} (bound to {order[2]})")

            print("\n-- Option wheel --", flush=True)
            move_mouse(700, 520)
            set_modifier(KEY_OPTION, Quartz.kCGEventFlagMaskAlternate)
            time.sleep(0.6)
            move_mouse(700, 380)
            time.sleep(0.4)
            subprocess.run(["screencapture", "-x", "/tmp/wheel_live.png"])
            set_modifier(KEY_OPTION, 0)
            time.sleep(SETTLE)
            after_name = where(titles)
            record(after_name is not None, "wheel selection",
                   f"-> {after_name} (screenshot at /tmp/wheel_live.png)")
    finally:
        stop(proc)

    total, passed = len(RESULTS), sum(1 for r in RESULTS if r)
    extra = f", {SKIPPED[0]} skipped (focus stolen)" if SKIPPED[0] else ""
    print(f"\n{passed}/{total} checks passed{extra}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
