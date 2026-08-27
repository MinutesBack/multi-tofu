"""Hiding the other clients. Needs the mock clients running.

  ./tools/mocks.sh start && ./.venv/bin/python tests/test_hide_others.py

The point of the suite is the promise that nothing is left invisible: the
option going off, and the app quitting, both have to give the clients back.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MULTITOFU_CONFIG", "/tmp/multitofu_hide_test.json")

from ApplicationServices import (
    AXUIElementCopyAttributeValue, AXUIElementCreateApplication,
)

from multitofu.accounts import Scanner, accessibility_trusted
from multitofu.config import Config

RESULTS = []


def record(ok, label, detail=""):
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<46} {detail}")


def is_hidden(pid):
    """Read it back through Accessibility, not NSRunningApplication.

    NSRunningApplication properties refresh through KVO on a run loop, and a
    plain script has none, so its isHidden answers with whatever was true when
    the object was made. That cost an hour once already.
    """
    err, value = AXUIElementCopyAttributeValue(
        AXUIElementCreateApplication(pid), "AXHidden", None)
    return bool(err == 0 and value)


def hidden_pids(pids):
    return {pid for pid in pids if is_hidden(pid)}


def main():
    if not accessibility_trusted():
        print("accessibility not granted, skipping")
        return 0
    cfg = Config()
    cfg.data["hide_others"] = True
    cfg.data["bundle_ids"] = ["com.Ankama.Dofus", "com.ankama.dofus.mock"]
    scanner = Scanner(cfg)
    scanner.scan()
    if len(scanner.accounts) < 2:
        print(f"needs at least 2 clients, found {len(scanner.accounts)}, skipping")
        return 0

    target = scanner.accounts[0]
    others = {a["pid"] for a in scanner.accounts[1:]}
    every = {a["pid"] for a in scanner.accounts}
    scanner.focus(target)
    time.sleep(1.0)
    hidden = hidden_pids(every)
    record(others <= hidden, "every other client is hidden",
           f"{len(hidden & others)}/{len(others)}")
    record(target["pid"] not in hidden, "the one in front stays visible")

    # switching again has to bring the next one back on its own
    second = scanner.accounts[1]
    scanner.focus(second)
    time.sleep(1.0)
    record(not is_hidden(second["pid"]),
           "switching to a hidden client shows it again")

    scanner.unhide_all()
    time.sleep(0.6)
    left = hidden_pids(every)
    record(not left, "unhide_all gives every client back",
           f"{len(left)} still hidden")

    total, passed = len(RESULTS), sum(1 for r in RESULTS if r)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
