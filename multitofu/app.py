"""Menu bar controller: wires config, scanner, hotkeys and the wheel together."""
import errno
import fcntl
import os
import subprocess
import sys

import objc
import Quartz
from AppKit import (
    NSApp, NSApplication, NSRunningApplication, NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular, NSAlert, NSImage, NSMakeSize, NSMenu,
    NSMenuItem, NSScreen, NSStatusBar, NSVariableStatusItemLength,
)
from Foundation import NSObject, NSTimer

from . import APP_NAME, __version__
from . import appnap, loginitem
from .accounts import Scanner, accessibility_trusted, request_accessibility
from .config import CONFIG_DIR, CONFIG_PATH, Config
from .i18n import set_language, t, team_display
from .hotkeys import HotkeyManager
from .prefs import PrefsController
from .radial import Wheel, load_icon, play


LOG_PATH = os.path.expanduser("~/Library/Logs/Multi-Tofu.log")
BUNDLE_ID = "fr.multitofu.app"
# The lock belongs to a configuration, not to the machine. Two setups are two
# instances, which is what the test rig needs and what a second config means.
LOCK_PATH = os.path.splitext(CONFIG_PATH)[0] + ".lock"


def log(message):
    """Launched from the Finder there is no console, so keep a small log the
    app can be diagnosed from."""
    print(message, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except OSError:
        pass
_lock_handle = None


def claim_single_instance():
    """A second copy would install a second event tap and every shortcut would
    fire twice, so only one wins."""
    global _lock_handle
    try:
        os.makedirs(os.path.dirname(LOCK_PATH) or CONFIG_DIR, exist_ok=True)
        handle = open(LOCK_PATH, "w")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
            return False
        return True
    handle.write(str(os.getpid()))
    handle.flush()
    _lock_handle = handle
    return True


def cursor_position():
    event = Quartz.CGEventCreate(None)
    loc = Quartz.CGEventGetLocation(event)
    return loc.x, loc.y


def open_accessibility_pane():
    subprocess.run([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    ], capture_output=True)


def bundle_path():
    """Empty when running from source, which is the case the repair path has
    to refuse: there is no bundle to reopen."""
    from Foundation import NSBundle
    path = NSBundle.mainBundle().bundlePath()
    return path if path and path.endswith(".app") else ""


def repair_accessibility():
    """Drop the app's Accessibility record and come back.

    A rebuilt app carries a new ad-hoc signature, so the row left in System
    Settings looks switched on while macOS refuses the new binary. Removing
    the record is the only way to make the system ask again.
    """
    app = bundle_path()
    if not app:
        return False
    script = (f'sleep 1; /usr/bin/tccutil reset Accessibility {BUNDLE_ID} '
              f'>/dev/null 2>&1; /usr/bin/open -a "{app}"')
    subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True)
    return True


class DosoftApp(NSObject):
    def init(self):
        self = objc.super(DosoftApp, self).init()
        if self is None:
            return None
        self.config = Config()
        set_language(self.config.data.get("language", "auto"))
        self.scanner = Scanner(self.config)
        self.wheel = Wheel(self.config)
        self.hotkeys = HotkeyManager(
            self.config, self.queueAction, self.onModifier, self.onMouse,
            self.queuePeek)
        self.hotkeys_running = False
        self.prefs = PrefsController.alloc().initWithApp_(self)
        self.current_idx = 0
        self.status_item = None
        self.menu = None
        self.wheel_timer = None
        self.scan_timer = None
        self.trust_timer = None
        self.peek_origin = None
        return self

    # ---------- lifecycle ----------

    def applicationDidFinishLaunching_(self, notification):
        if self.config.data.get("show_dock_icon"):
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        self._build_main_menu()
        self._build_status_item()
        self.refresh()
        trusted = accessibility_trusted()
        self.hotkeys_running = self.hotkeys.start() if trusted else False
        from time import strftime
        log(f"[{strftime('%Y-%m-%d %H:%M:%S')}] {APP_NAME} {__version__} ready | "
            f"accessibility={trusted} | "
            f"shortcuts={'on' if self.hotkeys_running else 'OFF'} | "
            f"dock_icon={bool(self.config.data.get('show_dock_icon'))} | "
            f"{len(self.scanner.accounts)} client(s)")
        self._trusted = trusted
        if not trusted:
            # No blocking alert here. macOS shows its own prompt, and a modal
            # of ours would freeze the run loop so the grant could never be
            # picked up without quitting.
            request_accessibility()
        # The watcher runs for the whole session, in both directions. A grant
        # can land later, and it can also go away: every rebuild gets a new
        # ad-hoc signature, so the row in System Settings still looks on while
        # the app is refused. Silently claiming to be ready in that state is
        # the bug this poll exists to prevent.
        self.trust_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "checkTrust:", None, True)
        if self.config.data.get("keep_clients_awake"):
            appnap.set_disabled(self.config, True)
        if loginitem.available():
            wanted = bool(self.config.data.get("launch_at_login"))
            if wanted != loginitem.is_enabled():
                loginitem.set_enabled(wanted)
        interval = float(self.config.data.get("scan_interval", 2.0))
        self.scan_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            interval, self, "tick:", None, True)
        self.rebuild_menu()
        # Open Settings on launch only while setup is unfinished, or if you
        # explicitly asked for it. Once Accessibility is granted the app is set
        # up, so it sits quietly in the menu bar instead of reopening every
        # time the launcher relaunches it. A background launch never opens it.
        user_launch = "--background" not in sys.argv
        want_settings = (not trusted) or self.config.data.get("open_settings_on_launch", False)
        if user_launch and want_settings:
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.6, self, "openPrefsOnLaunch:", None, False)
        if getattr(self, "_pending_menubar_warning", False) \
                and not os.environ.get("MULTITOFU_QUIET"):
            self._warn_menubar_full()

    @objc.python_method
    def _warn_menubar_full(self):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("menubar_alert_title", name=APP_NAME))
        alert.setInformativeText_(t("menubar_alert_body", name=APP_NAME))
        alert.addButtonWithTitle_(t("menubar_alert_dock"))
        alert.addButtonWithTitle_(t("menubar_alert_keep"))
        NSApp.activateIgnoringOtherApps_(True)
        if alert.runModal() == 1000:
            self.config.data["show_dock_icon"] = True
            self.config.save()
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    def openPrefsOnLaunch_(self, timer):
        from time import strftime
        try:
            self.prefs.show()
            visible = bool(self.prefs.window and self.prefs.window.isVisible())
            log(f"[{strftime('%Y-%m-%d %H:%M:%S')}] settings opened | visible={visible}")
        except Exception as exc:
            # a window that fails to build used to fail in silence, and the
            # app just sat there looking like it had not started
            log(f"[{strftime('%Y-%m-%d %H:%M:%S')}] settings failed to open | {exc!r}")

    def checkTrust_(self, timer):
        """Follow the permission in both directions, so flipping the toggle in
        System Settings is enough. No relaunch."""
        trusted = accessibility_trusted()
        if trusted == getattr(self, "_trusted", None):
            return
        self._trusted = trusted
        if trusted:
            self.hotkeys_running = self.hotkeys.start()
        else:
            self.hotkeys.stop()
            self.hotkeys_running = False
        from time import strftime
        log(f"[{strftime('%Y-%m-%d %H:%M:%S')}] accessibility "
            f"{'granted' if trusted else 'lost'} | "
            f"shortcuts={'on' if self.hotkeys_running else 'OFF'}")
        self.rebuild_menu()
        self._reload_prefs()
        self.refresh()

    @objc.python_method
    def _reload_prefs(self):
        """The Settings window holds the status banner. Nothing else redraws
        it, so anything that changes what it says has to say so."""
        if self.prefs is not None and self.prefs.window is not None \
                and self.prefs.window.isVisible():
            self.prefs.reload()

    def applicationWillTerminate_(self, notification):
        self.hotkeys.stop()
        # never leave someone with clients they cannot see because they quit
        if self.config.data.get("hide_others"):
            try:
                self.scanner.unhide_all()
            except Exception:
                pass

    # ---------- status item ----------

    @objc.python_method
    def _build_main_menu(self):
        """A menu bar app draws no menu bar, but the main menu is still where
        AppKit looks for key equivalents. Without it Command Q does nothing and
        the only way out is the status item, which is exactly the complaint."""
        main = NSMenu.alloc().init()
        app_item = NSMenuItem.alloc().init()
        main.addItem_(app_item)
        sub = NSMenu.alloc().init()
        close = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu_close_window"), "performClose:", "w")
        sub.addItem_(close)
        sub.addItem_(NSMenuItem.separatorItem())
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu_quit"), "terminate:", "q")
        sub.addItem_(quit_item)
        app_item.setSubmenu_(sub)
        NSApp.setMainMenu_(main)

    @objc.python_method
    def _build_status_item(self):
        bar = NSStatusBar.systemStatusBar()
        self.status_item = bar.statusItemWithLength_(NSVariableStatusItemLength)
        button = self.status_item.button()
        image = None
        for symbol in ("bird.fill", "bird", "gamecontroller.fill"):
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                symbol, APP_NAME)
            if image is not None:
                break
        if image is not None:
            image.setTemplate_(True)
            button.setImage_(image)
        else:
            button.setTitle_("MT")
        self.menu = NSMenu.alloc().init()
        self.menu.setAutoenablesItems_(False)
        self.status_item.setMenu_(self.menu)
        self._warn_if_status_item_hidden(button)

    @objc.python_method
    def _warn_if_status_item_hidden(self, button):
        """macOS drops a status item behind the notch when the menu bar is
        full. The item still reports itself visible, so check its position."""
        window = button.window()
        screens = NSScreen.screens()
        if window is None or not screens:
            return
        frame = window.frame()
        width = screens[0].frame().size.width
        notch_left = width / 2.0 - 100
        notch_right = width / 2.0 + 100
        hidden = frame.origin.x + frame.size.width > notch_left \
            and frame.origin.x < notch_right
        if not hidden:
            return
        log("Multi-Tofu: the menu bar is full, so the status item is sitting "
            "behind the notch and will not draw. Set show_dock_icon to true in "
            f"{self.config.path}, or free a menu bar slot.")
        if self.config.data.get("show_dock_icon"):
            return
        self._pending_menubar_warning = True

    @objc.python_method
    def rebuild_menu(self):
        if self.menu is None:
            return
        self.build_menu(self.menu)

    def applicationDockMenu_(self, sender):
        """Right-clicking the Dock icon gives the same list as the menu bar,
        which matters when a full menu bar hides the status item."""
        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        self.build_menu(menu)
        return menu

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_windows):
        """Clicking the Dock icon opens settings. Without this it does nothing,
        because a menu bar app has no window to bring forward."""
        self.refresh()
        self.prefs.show()
        return True

    @objc.python_method
    def build_menu(self, menu):
        cfg = self.config.data
        menu.removeAllItems()

        cycle = self.scanner.cycle_list()
        header = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu_header", name=APP_NAME, version=__version__,
              count=len(cycle)), None, "")
        header.setEnabled_(False)
        menu.addItem_(header)

        if not self.hotkeys_running:
            warn = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                t("menu_access_off"), "openAccessibility:", "")
            warn.setTarget_(self)
            menu.addItem_(warn)

        menu.addItem_(NSMenuItem.separatorItem())

        for i, acc in enumerate(self.scanner.accounts):
            title = acc["name"]
            if acc.get("class_name"):
                title = f"{title}  -  {acc['class_name']}"
            if not acc["active"]:
                title = f"({title})"
            if cfg.get("leader_name") == acc["name"]:
                title = f"{title}   [{t('leader_tag')}]"
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                title, "focusAccount:", "")
            item.setTarget_(self)
            item.setTag_(i)
            icon = load_icon(acc.get("slug"))
            if icon is not None:
                small = icon.copy()
                small.setSize_(NSMakeSize(16, 16))
                item.setImage_(small)
            menu.addItem_(item)

        if not self.scanner.accounts:
            empty = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                t("menu_no_client"), None, "")
            empty.setEnabled_(False)
            menu.addItem_(empty)

        menu.addItem_(NSMenuItem.separatorItem())

        mode_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu_rotation", mode=(t("mode_all")
              if cfg.get("current_mode", "ALL") == "ALL"
              else team_display(cfg.get("current_mode")))), None, "")
        mode_menu = NSMenu.alloc().init()
        mode_menu.setAutoenablesItems_(False)
        for name in ["ALL"] + list(cfg.get("teams", [])):
            label = t("mode_all") if name == "ALL" else team_display(name)
            sub = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                label, "setMode:", "")
            sub.setTarget_(self)
            sub.setRepresentedObject_(name)
            sub.setState_(1 if cfg.get("current_mode") == name else 0)
            mode_menu.addItem_(sub)
        mode_item.setSubmenu_(mode_menu)
        menu.addItem_(mode_item)

        menu.addItem_(NSMenuItem.separatorItem())
        if self.scanner.accounts:
            close = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                t("menu_quit_clients"), "quitClients:", "")
            close.setTarget_(self)
            menu.addItem_(close)
        for title, action, key in [(t("menu_rescan"), "rescan:", "r"),
                                   (t("menu_prefs"), "openPrefs:", ","),
                                   (t("menu_quit"), "quitApp:", "q")]:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
            item.setTarget_(self)
            menu.addItem_(item)

    # ---------- actions from the menu ----------

    def focusAccount_(self, sender):
        accounts = self.scanner.accounts
        idx = sender.tag()
        if 0 <= idx < len(accounts):
            self.scanner.focus(accounts[idx])

    def setMode_(self, sender):
        self.config.data["current_mode"] = sender.representedObject() or "ALL"
        self.config.save()
        self.current_idx = 0
        self.rebuild_menu()

    def rescan_(self, sender):
        self.refresh()

    def openPrefs_(self, sender):
        self.refresh()
        self.prefs.show()

    def openAccessibility_(self, sender):
        request_accessibility()
        open_accessibility_pane()
        # the Settings window carries the banner and the repair button, and a
        # sheet there lands in front instead of behind
        self.prefs.show()

    def quitClients_(self, sender):
        """Ask every client to quit. Behind a confirmation on purpose, this is
        the one irreversible thing the app can do."""
        accounts = list(self.scanner.accounts)
        if not accounts:
            return
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("quit_clients_title", count=len(accounts)))
        alert.setInformativeText_(t("quit_clients_body"))
        alert.addButtonWithTitle_(t("quit_clients_confirm"))
        alert.addButtonWithTitle_(t("quit_clients_cancel"))
        NSApp.activateIgnoringOtherApps_(True)
        if alert.runModal() != 1000:
            return
        for pid in {acc["pid"] for acc in accounts}:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app is not None:
                app.terminate()   # the polite request, not a kill
        self.refresh()

    def quitApp_(self, sender):
        NSApp.terminate_(self)

    def tick_(self, timer):
        self.refresh(rebuild=False)

    # ---------- core ----------

    @objc.python_method
    def refresh(self, rebuild=True):
        before = [(a["name"], a["pid"]) for a in self.scanner.accounts]
        self.scanner.scan()
        after = [(a["name"], a["pid"]) for a in self.scanner.accounts]
        if rebuild or before != after:
            self.rebuild_menu()
            if self.prefs is not None and self.prefs.window is not None \
                    and self.prefs.window.isVisible():
                self.prefs.reload()

    @objc.python_method
    def _sync_index(self):
        idx = self.scanner.index_of_focused()
        if idx >= 0:
            self.current_idx = idx

    @objc.python_method
    def _step(self, delta):
        cycle = self.scanner.cycle_list()
        if not cycle:
            return
        self._sync_index()
        self.current_idx = (self.current_idx + delta) % len(cycle)
        self.scanner.focus(cycle[self.current_idx])

    @objc.python_method
    def queueAction(self, name):
        """Return from the event tap immediately.

        The tap callback runs on the main run loop and macOS disables a tap
        whose callback overruns, which shows up as dropped keystrokes. Focus
        work is handed to the next run loop pass instead.
        """
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0, self, "dispatchAction:", name, False)

    def dispatchAction_(self, timer):
        self.onAction(timer.userInfo())

    @objc.python_method
    def queuePeek(self, down):
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0, self, "dispatchPeek:", bool(down), False)

    def dispatchPeek_(self, timer):
        self.onPeek(bool(timer.userInfo()))

    @objc.python_method
    def onPeek(self, down):
        """Hold to look somewhere else, release to land back where you were.

        Anything you do while holding still works, so peek composes with the
        rotation keys, the direct binds and the wheel.
        """
        cycle = self.scanner.cycle_list()
        if down:
            if not cycle:
                return
            index = self.scanner.index_of_focused()
            self.peek_origin = (cycle[index]["name"]
                                if 0 <= index < len(cycle) else None)
            target = self.config.data.get("peek_target", "leader")
            leader = self.config.data.get("leader_name", "")
            if target == "leader" and leader:
                self.scanner.focus_by_name(leader)
            elif target == "prev":
                self._step(-1)
            else:
                self._step(1)
            return

        origin, self.peek_origin = self.peek_origin, None
        if not origin:
            return
        self.scanner.focus_by_name(origin)
        for i, acc in enumerate(cycle):
            if acc["name"] == origin:
                self.current_idx = i
                break

    @objc.python_method
    def onAction(self, name):
        if name == "action:next":
            self._step(1)
        elif name == "action:prev":
            self._step(-1)
        elif name == "action:leader":
            leader = self.config.data.get("leader_name", "")
            if leader:
                self.scanner.focus_by_name(leader)
                cycle = self.scanner.cycle_list()
                for i, acc in enumerate(cycle):
                    if acc["name"] == leader:
                        self.current_idx = i
                        break
        elif name == "action:refresh":
            self.refresh()
        elif name == "action:prefs":
            self.refresh()
            self.prefs.show()
        elif name.startswith("char:"):
            pseudo = name.split(":", 1)[1]
            if self.scanner.focus_by_name(pseudo):
                cycle = self.scanner.cycle_list()
                for i, acc in enumerate(cycle):
                    if acc["name"] == pseudo:
                        self.current_idx = i
                        break

    # ---------- wheel ----------

    @objc.python_method
    def onModifier(self, down):
        if down:
            self._cancel_wheel_timer()
            delay = float(self.config.data.get("wheel_delay_ms", 200)) / 1000.0
            self.wheel_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                delay, self, "showWheel:", None, False)
        else:
            self._cancel_wheel_timer()
            self.hotkeys.stop_mouse()
            if self.wheel.visible:
                target = self.wheel.selection()
                self.wheel.hide()
                if target:
                    if self.config.data.get("wheel_sounds", True):
                        play("click", self.config.data.get("volume_level", 50) / 100.0)
                    self.scanner.focus_by_name(target)
                    cycle = self.scanner.cycle_list()
                    for i, acc in enumerate(cycle):
                        if acc["name"] == target:
                            self.current_idx = i
                            break

    @objc.python_method
    def _cancel_wheel_timer(self):
        if self.wheel_timer is not None:
            self.wheel_timer.invalidate()
            self.wheel_timer = None

    def showWheel_(self, timer):
        self.wheel_timer = None
        self.hotkeys.start_mouse()
        if not self.config.data.get("wheel_enabled", True):
            return
        if not self.hotkeys.modifier_down:
            return
        cycle = self.scanner.cycle_list()
        # show it with a single client too. One segment is not useful in a
        # fight, but it lets you see the wheel works, and it stops the wheel
        # from silently doing nothing while you test with one account open.
        if not cycle:
            return
        self._sync_index()
        current = cycle[self.current_idx]["name"] if self.current_idx < len(cycle) else None
        x, y = cursor_position()
        self.wheel.show(x, y, cycle, current)

    @objc.python_method
    def onMouse(self, x, y):
        self.wheel.update_pointer(x, y)


def probe():
    """Print what the app can see, then exit. No GUI."""
    config = Config()
    scanner = Scanner(config)
    print(f"{APP_NAME} {__version__}")
    trusted = accessibility_trusted()
    print("Accessibility trusted:", trusted)
    if not trusted:
        print("  -> window titles will be empty and shortcuts will not fire.")
        print("  -> run  ./run.sh --grant  to raise the system prompt.")
    running = scanner._dofus_apps()
    print(f"Dofus processes running: {len(running)}")
    for app in running:
        print(f"  pid={app.processIdentifier()} bundle={app.bundleIdentifier()}")
    accounts = scanner.scan()
    if not accounts:
        print("No Dofus window detected.")
        print("Bundle ids watched:", config.data.get("bundle_ids"))
        if not running:
            print("Nothing is running under that bundle id. Launch a Dofus 3 "
                  "client from the Ankama Launcher first.")
        return 1
    for i, acc in enumerate(accounts):
        print(f"  [{i}] name={acc['name']!r} class={acc['class_name']!r} "
              f"slug={acc['slug']!r} pid={acc['pid']} login={acc['is_menu']} "
              f"raw_title={acc['title']!r}")
    print("In rotation:", [a["name"] for a in scanner.cycle_list()])
    return 0


def grant():
    """Trigger the system Accessibility prompt for whatever owns this process."""
    if accessibility_trusted():
        print("Already trusted. Nothing to do.")
        return 0
    print("Asking macOS for Accessibility access...")
    request_accessibility()
    print()
    print("A system dialog should have appeared. If it did, click "
          "'Open System Settings'.")
    print("Then in Privacy & Security > Accessibility, switch ON the entry that "
          "just appeared (Terminal, or iTerm, or Python).")
    print("Quit that terminal app completely with Cmd+Q, reopen it, and run "
          "./run.sh --probe again.")
    return 0


def main():
    if "--probe" in sys.argv:
        raise SystemExit(probe())
    if "--grant" in sys.argv:
        raise SystemExit(grant())
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Multi-Tofu\n"
              "  --probe       list the Dofus clients it can see\n"
              "  --grant       raise the Accessibility prompt\n"
              "  --background  start without opening the settings window")
        raise SystemExit(0)
    if not claim_single_instance():
        print("Multi-Tofu is already running.", flush=True)
        try:
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write("second instance refused, one was already running\n")
        except OSError:
            pass
        raise SystemExit(0)
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = DosoftApp.alloc().init()
    app.setDelegate_(delegate)
    app.run()
