"""End to end rotation test against live windows.

Run the mock clients first:  ./tools/mocks.sh start
Then:                        MULTITOFU_CONFIG=/tmp/multitofu_test.json ./.venv/bin/python tests/test_rotation.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSApp
from ApplicationServices import (
    AXUIElementCreateSystemWide, AXUIElementCopyAttributeValue,
)
from Foundation import NSObject, NSTimer

from multitofu.accounts import Scanner
from multitofu.config import Config

SETTLE = 0.9
RESULTS = []


def focused_window_title():
    """Ground truth, read from the system-wide element rather than from the
    same per-app attribute the app itself uses."""
    system = AXUIElementCreateSystemWide()
    err, app = AXUIElementCopyAttributeValue(system, "AXFocusedApplication", None)
    if err != 0 or app is None:
        return None
    err, win = AXUIElementCopyAttributeValue(app, "AXFocusedWindow", None)
    if err != 0 or win is None:
        return None
    err, title = AXUIElementCopyAttributeValue(win, "AXTitle", None)
    return str(title) if err == 0 and title else None


def check(label, account, scanner):
    """A login window has no character name, so compare on the raw title."""
    time.sleep(SETTLE)
    title = focused_window_title() or "<none>"
    expected_name = account["name"]
    ok = title == account["title"]
    actual = title.split(" - ")[0]
    idx = scanner.index_of_focused()
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label:28} expected={expected_name:12} "
          f"front={actual:12} index_of_focused={idx}", flush=True)
    return ok


class Suite(NSObject):
    def run_(self, timer):
        try:
            self.body()
        except Exception:
            import traceback
            traceback.print_exc()
            RESULTS.append(False)
        total = len(RESULTS)
        passed = sum(1 for r in RESULTS if r)
        print(f"\n{passed}/{total} checks passed")
        NSApp.terminate_(self)

    def body(self):
        config = Config()
        config.data["current_mode"] = "ALL"
        config.data["accounts_state"] = {}
        config.data["accounts_team"] = {}
        config.data["leader_name"] = ""
        config.save()

        scanner = Scanner(config)
        accounts = scanner.scan()
        names = [a["name"] for a in accounts]
        print("detected:", names, flush=True)
        if len(names) < 3:
            print("need at least 3 clients, run ./tools/mocks.sh start")
            RESULTS.append(False)
            return

        cycle = scanner.cycle_list()
        login_names = [a["name"] for a in accounts if a["is_menu"]]
        in_rotation = [a["name"] for a in cycle]
        if login_names:
            ok = all(name not in in_rotation for name in login_names)
            RESULTS.append(ok)
            print(f"  {'PASS' if ok else 'FAIL'}  login windows out of rotation: "
                  f"{login_names} not in {in_rotation}", flush=True)

        print("\n-- next through the whole rotation --", flush=True)
        idx = 0
        scanner.focus(cycle[0])
        check("start", cycle[0], scanner)
        for step in range(1, len(cycle) + 1):
            idx = (idx + 1) % len(cycle)
            scanner.focus(cycle[idx])
            check(f"next x{step}", cycle[idx], scanner)

        print("\n-- previous --", flush=True)
        for step in range(1, 3):
            idx = (idx - 1) % len(cycle)
            scanner.focus(cycle[idx])
            check(f"prev x{step}", cycle[idx], scanner)

        print("\n-- leader --", flush=True)
        leader = names[1]
        config.data["leader_name"] = leader
        config.save()
        scanner.scan()
        scanner.focus_by_name(leader)
        check("focus leader",
              next(a for a in scanner.accounts if a["name"] == leader), scanner)

        print("\n-- team split --", flush=True)
        config.data["accounts_team"] = {names[0]: "Team 1", names[1]: "Team 2",
                                        names[2]: "Team 2"}
        config.data["current_mode"] = "Team 2"
        config.save()
        scanner.scan()
        team = scanner.cycle_list()
        team_names = [a["name"] for a in team]
        ok = team_names == [names[1], names[2]]
        RESULTS.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  team 2 rotation = {team_names} "
              f"(expected {[names[1], names[2]]})", flush=True)
        for acc in team:
            scanner.focus(acc)
            check(f"team2 {acc['name']}", acc, scanner)

        print("\n-- deactivated account is skipped --", flush=True)
        config.data["current_mode"] = "ALL"
        config.data["accounts_team"] = {}
        config.data["accounts_state"] = {names[0]: False}
        config.save()
        scanner.scan()
        rotation = [a["name"] for a in scanner.cycle_list()]
        ok = names[0] not in rotation
        RESULTS.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {names[0]} excluded -> {rotation}", flush=True)


app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
suite = Suite.alloc().init()
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    0.5, suite, "run:", None, False)
app.run()
