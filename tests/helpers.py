"""Shared ground truth for the window suites.

Read the focused client independently of the code under test, and never
report a result taken while some other app holds the front window.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AppKit import NSWorkspace
from ApplicationServices import (
    AXUIElementCopyAttributeValue, AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
)

BUNDLES = {"com.ankama.dofus", "com.ankama.dofus.mock"}


def _title_of(element):
    for attr in ("AXFocusedWindow", "AXMainWindow"):
        err, win = AXUIElementCopyAttributeValue(element, attr, None)
        if err == 0 and win is not None:
            err, title = AXUIElementCopyAttributeValue(win, "AXTitle", None)
            if err == 0 and title:
                return str(title)
    return None


def client_apps():
    return [a for a in NSWorkspace.sharedWorkspace().runningApplications()
            if (a.bundleIdentifier() or "").lower() in BUNDLES]


def outside_app_has_focus():
    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    bid = (front.bundleIdentifier() or "").lower() if front else ""
    return bool(bid) and bid not in BUNDLES


def focused_title(retries=16):
    """Two independent reads: the system wide focused app, then a sweep of the
    client processes for whichever calls itself frontmost."""
    for _ in range(retries):
        system = AXUIElementCreateSystemWide()
        err, app = AXUIElementCopyAttributeValue(system, "AXFocusedApplication", None)
        if err == 0 and app is not None:
            title = _title_of(app)
            if title:
                return title
        for running in client_apps():
            ref = AXUIElementCreateApplication(running.processIdentifier())
            err, front = AXUIElementCopyAttributeValue(ref, "AXFrontmost", None)
            if err == 0 and front:
                title = _title_of(ref)
                if title:
                    return title
        time.sleep(0.25)
    return None


def wait_for_client_focus(timeout=6.0):
    """True once a client holds the front window again. Anything else grabbing
    it mid run is an environment problem, not a result."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not outside_app_has_focus():
            return True
        time.sleep(0.4)
    return False
