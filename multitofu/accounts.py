"""Dofus window discovery and focus, via the macOS Accessibility API."""
import re

from AppKit import NSWorkspace, NSRunningApplication
from CoreFoundation import CFEqual
from Foundation import NSTimer
from ApplicationServices import (
    AXUIElementSetMessagingTimeout,
    AXIsProcessTrusted,
    AXIsProcessTrustedWithOptions,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue,
    AXUIElementGetPid,
    AXUIElementSetAttributeValue,
    AXUIElementPerformAction,
)

from .classes import to_slug
from .i18n import t

NSApplicationActivateAllWindows = 1 << 0
# How long to let the window server settle before checking a switch took,
# and how many times to try again when it did not.
FOCUS_CHECK_DELAY = 0.05
FOCUS_RETRIES = 2
MAX_REMEMBERED = 50
# A Unity client can take its time answering. The event tap lives on the main
# run loop, so a slow reply there costs us keystrokes: cap every call.
AX_TIMEOUT_SECONDS = 0.35

VERSION_RE = re.compile(r"^v?\d+(?:\.\d+)+[a-z]?$", re.IGNORECASE)
BUILD_WORDS = {"release", "beta", "debug", "development", "dev", "retro"}
# 'Dofus', 'Dofus 3.6.10.11', 'Dofus Retro' -> the product name, not a character
PRODUCT_RE = re.compile(r"^dofus(\s|$)", re.IGNORECASE)


def accessibility_trusted():
    return bool(AXIsProcessTrusted())


def request_accessibility():
    """Ask the system to show the Accessibility prompt for this process."""
    try:
        return bool(AXIsProcessTrustedWithOptions(
            {"AXTrustedCheckOptionPrompt": True}))
    except Exception:
        return accessibility_trusted()


def _ax(element, attribute):
    try:
        err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    except Exception:
        return None
    return value if err == 0 else None


class Account(dict):
    """Plain dict so it stays easy to serialise and log."""

    @property
    def name(self):
        return self["name"]


class Scanner:
    def __init__(self, config):
        self.config = config
        self.accounts = []
        self.leader = None
        self._app_refs = {}
        self._last_focused_pid = None
        self._focus_token = 0

    # ---------- discovery ----------

    def _dofus_apps(self):
        wanted = {b.lower() for b in self.config.data.get("bundle_ids", [])}
        found = []
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            bid = (app.bundleIdentifier() or "").lower()
            if bid in wanted:
                found.append(app)
        return found

    def _app_ref(self, pid):
        ref = self._app_refs.get(pid)
        if ref is None:
            ref = AXUIElementCreateApplication(pid)
            try:
                AXUIElementSetMessagingTimeout(ref, AX_TIMEOUT_SECONDS)
            except Exception:
                pass
            self._app_refs[pid] = ref
        return ref

    def _windows_for(self, app_ref):
        """A client in native fullscreen reports an empty AXWindows list but
        still answers AXMainWindow, so fall back to that."""
        windows = list(_ax(app_ref, "AXWindows") or [])
        if not windows:
            for attr in ("AXMainWindow", "AXFocusedWindow"):
                win = _ax(app_ref, attr)
                if win is not None and win not in windows:
                    windows.append(win)
        return windows

    def _raw_windows(self):
        """[(pid, window_ref, title)] for every Dofus window we can reach."""
        out = []
        live_pids = set()
        for app in self._dofus_apps():
            pid = app.processIdentifier()
            live_pids.add(pid)
            for win in self._windows_for(self._app_ref(pid)):
                role = _ax(win, "AXRole")
                if role and role != "AXWindow":
                    continue
                title = _ax(win, "AXTitle")
                if title is None:
                    title = _ax(self._app_ref(pid), "AXTitle") or ""
                out.append((pid, win, str(title).strip()))
        for pid in list(self._app_refs):
            if pid not in live_pids:
                self._app_refs.pop(pid, None)
        if self._last_focused_pid not in live_pids:
            self._last_focused_pid = None
        return out

    def _raw_vm_windows(self):
        """[(pid, window_ref, title)] for the configured Fusion VM.

        The Dofus process lives inside Windows and is therefore invisible to
        macOS Accessibility. Fusion's VM window is the honest macOS target.
        Requiring its configured title avoids adding Fusion's library or
        settings windows to the character rotation.
        """
        cfg = self.config.data
        if not cfg.get("vm_target_enabled", True):
            return []
        wanted = {b.lower() for b in cfg.get("vm_bundle_ids", [])}
        title_match = str(cfg.get("vm_window_title", "")).strip().lower()
        if not wanted or not title_match:
            return []
        out = []
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            bid = (app.bundleIdentifier() or "").lower()
            if bid not in wanted:
                continue
            pid = app.processIdentifier()
            for win in self._windows_for(self._app_ref(pid)):
                if _ax(win, "AXRole") not in (None, "AXWindow"):
                    continue
                title = str(_ax(win, "AXTitle") or "").strip()
                if title_match in title.lower():
                    out.append((pid, win, title))
        return out[:1]

    # ---------- title parsing ----------

    def parse_title(self, title, menu_counter):
        """Return (pseudo, class_name, is_menu).

        The Mac client titles a logged-in window
            'Kaeso - Iop - 3.6.10.11 - Release'
        and a window still on the login screen
            'Dofus 3.6.10.11 - Release'
        so the version and build tokens are stripped before parsing.

        A client with no character on it yet is shown as 'Account 1',
        'Account 2' and so on. The moment a character logs in, the window title
        carries their real name and that is what appears everywhere.
        """
        sep = self.config.data.get("title_separator", " - ")
        clean = (title or "").strip()
        login = (t("account_placeholder", number=menu_counter), None, True)
        if not clean:
            return login

        parts = [p.strip() for p in clean.split(sep) if p.strip()]
        while parts and (VERSION_RE.match(parts[-1])
                         or parts[-1].lower() in BUILD_WORDS):
            parts.pop()
        if not parts:
            return login
        if len(parts) == 1 and PRODUCT_RE.match(parts[0]):
            return login

        pseudo = parts[0]
        klass = parts[1] if len(parts) > 1 else None
        return pseudo, klass, False

    # ---------- public API ----------

    def scan(self):
        cfg = self.config.data
        rows = []
        menu_counter = 1
        seen_names = {}
        for pid, win, title in self._raw_windows():
            pseudo, klass, is_menu = self.parse_title(title, menu_counter)
            if is_menu:
                if cfg.get("hide_login_windows"):
                    menu_counter += 1
                    continue
                # skip a number a logged in character already answers to
                while pseudo in seen_names:
                    menu_counter += 1
                    pseudo = self.parse_title(title, menu_counter)[0]
                menu_counter += 1
            # Teams, roles, binds and rotation order are all stored per name,
            # so two windows must never answer to the same one.
            count = seen_names.get(pseudo, 0) + 1
            seen_names[pseudo] = count
            if count > 1:
                pseudo = f"{pseudo} ({count})"
            if klass and not is_menu:
                cfg["classes"][pseudo] = klass
            else:
                klass = cfg["classes"].get(pseudo)
            rows.append(Account({
                "name": pseudo,
                "pid": pid,
                "window": win,
                "title": title,
                "kind": "dofus",
                "class_name": klass,
                "slug": to_slug(klass),
                "active": bool(cfg["accounts_state"].get(pseudo, True)),
                "team": cfg["accounts_team"].get(pseudo, cfg.get("teams", ["Team 1"])[0]),
                "role": cfg.get("roles", {}).get(pseudo, "none"),
                "is_menu": is_menu,
            }))

        # A VM is one switch destination even if several Dofus windows exist
        # inside the guest. Switching accounts inside Windows remains a guest
        # concern; Multi-Tofu only brings the VM itself to the foreground.
        for pid, win, title in self._raw_vm_windows():
            pseudo = str(cfg.get("vm_display_name") or "Dofus (Windows VM)")
            rows.append(Account({
                "name": pseudo,
                "pid": pid,
                "window": win,
                "title": title,
                "kind": "vm",
                "class_name": "VMware Fusion",
                "slug": None,
                "active": bool(cfg["accounts_state"].get(pseudo, True)),
                "team": cfg["accounts_team"].get(
                    pseudo, cfg.get("teams", ["Team 1"])[0]),
                "role": cfg.get("roles", {}).get(pseudo, "none"),
                "is_menu": False,
            }))

        # A login placeholder is positional. Its number shifts the moment a
        # neighbour logs in, so it must never earn a slot in the saved order.
        order = cfg.get("custom_order", [])
        for row in rows:
            if not row["is_menu"] and row["name"] not in order:
                order.append(row["name"])
        if len(order) > MAX_REMEMBERED:
            live = {r["name"] for r in rows}
            stale = [n for n in order if n not in live]
            while len(order) > MAX_REMEMBERED and stale:
                order.remove(stale.pop(0))
        cfg["custom_order"] = order
        self.config.save()

        def position(row):
            if row["is_menu"]:
                return (1, row["pid"], "")
            try:
                return (0, order.index(row["name"]), "")
            except ValueError:
                return (0, len(order), row["name"])

        rows.sort(key=position)
        self.accounts = rows

        leader_name = cfg.get("leader_name", "")
        self.leader = next((r for r in rows if r["name"] == leader_name), None)
        return rows

    def cycle_list(self):
        """The rotation the shortcuts walk.

        A window still on the login screen has no character on it, so landing
        there mid fight is only ever a wasted keypress. It stays listed in the
        menu bar, where you can still click it to go and log in.
        """
        cfg = self.config.data
        mode = cfg.get("current_mode", "ALL")
        allow_login = cfg.get("login_windows_in_rotation", False)
        return [a for a in self.accounts
                if a["active"]
                and (allow_login or not a["is_menu"])
                and (mode == "ALL" or a["team"] == mode)]

    def index_of_focused(self):
        """Which entry of the rotation is in front, or -1.

        NSWorkspace.frontmostApplication() goes stale inside a background
        agent, so ask the accessibility layer directly instead.
        """
        cycle = self.cycle_list()
        if not cycle:
            return -1
        front_pid = None

        # Several Dofus clients share one bundle id. macOS can leave
        # AXFrontmost=true on more than one of those process elements after a
        # switch, so scanning that flag may pick an arbitrary old client. The
        # system-wide focused application is the one authoritative element and
        # carries the exact process id.
        focused_app = _ax(AXUIElementCreateSystemWide(), "AXFocusedApplication")
        if focused_app is not None:
            try:
                err, pid = AXUIElementGetPid(focused_app, None)
                if err == 0:
                    front_pid = int(pid)
            except Exception:
                pass

        # Some transition frames briefly expose no focused application. Prefer
        # the last client we deliberately focused; unlike AXFrontmost it cannot
        # be true for several same-bundle processes at once.
        cycle_pids = {a["pid"] for a in cycle}
        if front_pid not in cycle_pids and self._last_focused_pid in cycle_pids:
            front_pid = self._last_focused_pid

        # Keep the old flag scan only for startup, before this Scanner has
        # focused anything itself.
        if front_pid is None:
            for pid in cycle_pids:
                if _ax(self._app_ref(pid), "AXFrontmost"):
                    front_pid = pid
                    break
        if front_pid is None:
            return -1
        candidates = [i for i, a in enumerate(cycle) if a["pid"] == front_pid]
        if not candidates:
            return -1
        if len(candidates) == 1:
            return candidates[0]
        for i in candidates:
            if _ax(cycle[i]["window"], "AXMain"):
                return i
        return candidates[0]

    def focus(self, account):
        """Bring one client to the front, with the keyboard and the mouse.

        A window can be on top without being key: Unity then gets no keyDown
        and no mouseMoved, so shortcuts and hover die while the client looks
        focused. So the app is activated once, then the window is made main,
        raised and focused, and a short timer checks that it really holds the
        focus before trying again. Hiding the other clients waits for that
        check, so it never deactivates the target mid transition.
        """
        if not account:
            return False
        pid = account.get("pid")
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is None:
            return False
        self._focus_token += 1
        token = self._focus_token
        self._bring_forward(account, app)
        self._last_focused_pid = pid
        self._after(FOCUS_CHECK_DELAY,
                    lambda: self._check_focus(token, account, FOCUS_RETRIES))
        return True

    def _bring_forward(self, account, app):
        win = account.get("window")
        pid = account.get("pid")
        app_ref = self._app_ref(pid)
        if self.config.data.get("hide_others"):
            # a hidden app cannot be raised, and only this option ever hides
            # one, so the round trip stays off the path when it is off
            self._set_hidden(pid, False)
        try:
            if _ax(win, "AXMinimized"):
                AXUIElementSetAttributeValue(win, "AXMinimized", False)
        except Exception:
            pass
        # Activate the app first: activation hands key status to whatever the
        # app thinks is its main window, so the window has to be chosen after.
        # AXFrontmost is what gets through macOS 14's cooperative activation
        # for a background caller; activateWithOptions covers the Spaces
        # switch of a client in native fullscreen.
        try:
            AXUIElementSetAttributeValue(app_ref, "AXFrontmost", True)
        except Exception:
            pass
        try:
            if not app.activateWithOptions_(NSApplicationActivateAllWindows):
                app.activate()
        except Exception:
            pass
        try:
            AXUIElementSetAttributeValue(win, "AXMain", True)
            AXUIElementPerformAction(win, "AXRaise")
            # AXMain + AXRaise put the window on top but do not make it key
            AXUIElementSetAttributeValue(win, "AXFocused", True)
        except Exception:
            pass

    def _has_focus(self, account):
        """Read back, independently of what we asked for, who holds the focus."""
        focused_app = _ax(AXUIElementCreateSystemWide(), "AXFocusedApplication")
        if focused_app is None:
            return False
        try:
            err, pid = AXUIElementGetPid(focused_app, None)
        except Exception:
            return False
        if err != 0 or int(pid) != account.get("pid"):
            return False
        focused_win = _ax(self._app_ref(account["pid"]), "AXFocusedWindow")
        win = account.get("window")
        if focused_win is None or win is None:
            # some clients never expose a focused window; the app is enough
            return True
        try:
            return bool(CFEqual(focused_win, win))
        except Exception:
            return True

    def _check_focus(self, token, account, retries):
        if token != self._focus_token:
            return  # the user already moved on to another client
        if not self._has_focus(account) and retries > 0:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(
                account.get("pid"))
            if app is not None:
                self._bring_forward(account, app)
                self._after(FOCUS_CHECK_DELAY,
                            lambda: self._check_focus(token, account, retries - 1))
                return
        if self.config.data.get("hide_others"):
            self.hide_others(account.get("pid"))

    @staticmethod
    def _after(delay, fn):
        """Run fn on a later pass of the main run loop.

        Never sleep here: focus runs on the main run loop, next to the event
        tap, and a blocked callback gets the tap disabled by macOS.
        """
        def fire(_timer):
            try:
                fn()
            except Exception:
                pass
        NSTimer.scheduledTimerWithTimeInterval_repeats_block_(delay, False, fire)

    def _set_hidden(self, pid, hidden):
        """Through the Accessibility API, not NSRunningApplication.

        NSRunningApplication.hide() answers False for another application's
        process, so it silently does nothing. AXHidden on the app element is
        the same system-wide hide, and it is the permission we already hold.
        """
        try:
            AXUIElementSetAttributeValue(self._app_ref(pid), "AXHidden", bool(hidden))
        except Exception:
            pass

    def hide_others(self, keep_pid):
        """Hide every client except the one in front.

        Hiding is at the application level, which is what you want here: a
        client with several windows goes away whole. It is reversible and the
        process keeps running, so nothing disconnects.
        """
        for acc in self.accounts:
            pid = acc.get("pid")
            if pid != keep_pid:
                self._set_hidden(pid, True)

    def unhide_all(self):
        """Nobody should be left with invisible clients because they quit
        Multi-Tofu, so this runs on exit and when the option goes off."""
        for acc in self.accounts:
            self._set_hidden(acc.get("pid"), False)

    def focus_by_name(self, name):
        for acc in self.accounts:
            if acc["name"] == name:
                return self.focus(acc)
        return False
