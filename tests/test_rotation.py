"""End to end rotation test against live windows.

Run the mock clients first:  ./tools/mocks.sh start
Then:                        MULTITOFU_CONFIG=/tmp/multitofu_test.json ./.venv/bin/python tests/test_rotation.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AppKit import NSApplication, NSApplicationActivationPolicyProhibited, NSApp
from Foundation import NSObject, NSTimer

from helpers import focused_title, outside_app_has_focus, wait_for_client_focus

from multitofu.accounts import Scanner
from multitofu.config import Config

SETTLE = 1.3
RESULTS = []
SKIPPED = [0]


def check(label, account, scanner):
    """A login window has no character name, so compare on the raw title."""
    time.sleep(SETTLE)
    if not wait_for_client_focus():
        SKIPPED[0] += 1
        print(f"  SKIP  {label:28} another app holds the front window", flush=True)
        return True
    title = focused_title() or "<none>"
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
        extra = f", {SKIPPED[0]} skipped (focus stolen)" if SKIPPED[0] else ""
        print(f"\n{passed}/{total} checks passed{extra}")
        # NSApplication.terminate_ always exits with status 0, which made a
        # failed integration run look green to CI and shell scripts.
        sys.stdout.flush()
        os._exit(0 if passed == total else 1)

    def body(self):
        config = Config()
        # The native mock client deliberately uses its own bundle id. Include
        # it here so the README's documented test command works with a fresh
        # throwaway config instead of silently scanning only real Dofus.
        config.data["bundle_ids"] = ["com.Ankama.Dofus", "com.ankama.dofus.mock"]
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
# The test runner itself must never become a focus candidate while checking
# cross-process activation.
app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
suite = Suite.alloc().init()
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    0.5, suite, "run:", None, False)
app.run()
