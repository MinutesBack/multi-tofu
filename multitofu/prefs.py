"""Preferences window: characters, teams, order, binds."""
import objc
from AppKit import (
    NSAlert, NSApp, NSBackingStoreBuffered, NSBezelStyleRounded, NSButton,
    NSClosableWindowMask, NSColor, NSFont, NSImageScaleProportionallyUpOrDown,
    NSImageView, NSMakeRect, NSMiniaturizableWindowMask, NSPopUpButton,
    NSResizableWindowMask, NSScrollView, NSSwitchButton, NSTextField,
    NSTitledWindowMask, NSView, NSWindow, NSWindowStyleMaskTitled,
)
from Foundation import NSObject, NSTimer

from . import appnap, loginitem
from .i18n import (STRINGS, SUPPORTED, language_name, set_language, t,
                    team_display)
from .roles import ROLE_KEYS
from .keys import MODIFIER_MASKS, conflicts, describe, same_bind
from .radial import load_icon

# The order of the global shortcut buttons. The record handler indexes into
# this by button tag, so it must never be written down twice.
BIND_ORDER = ["next", "prev", "leader", "refresh", "prefs", "peek"]

ROW_HEIGHT = 34
HEADER_HEIGHT = 118
WINDOW_W = 900
WINDOW_H = 780


class FlippedView(NSView):
    def isFlipped(self):
        return True


def label(text, x, y, w, h=18, bold=False, size=12, color=None):
    field = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    field.setStringValue_(text)
    field.setBezeled_(False)
    field.setDrawsBackground_(False)
    field.setEditable_(False)
    field.setSelectable_(False)
    field.setFont_(NSFont.boldSystemFontOfSize_(size) if bold
                   else NSFont.systemFontOfSize_(size))
    if color is not None:
        field.setTextColor_(color)
    return field


def button(title, x, y, w, h, target, action, tag=0):
    btn = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    btn.setTitle_(title)
    btn.setBezelStyle_(NSBezelStyleRounded)
    btn.setTarget_(target)
    btn.setAction_(action)
    btn.setTag_(tag)
    btn.setFont_(NSFont.systemFontOfSize_(11))
    return btn


class PrefsController(NSObject):
    def initWithApp_(self, app):
        self = objc.super(PrefsController, self).init()
        if self is None:
            return None
        self.app = app
        self.window = None
        self.rows_view = None
        self.bind_buttons = {}
        self.global_buttons = {}
        self.status_timer = None
        return self

    # ---------- window ----------

    def show(self):
        self.app.hotkeys.capture = None
        if self.window is None:
            self._build()
        self.reload()
        NSApp.activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)
        if self.status_timer is None:
            # Permission, clients and conflicts all change behind the window's
            # back. A banner that only redraws on a rescan goes stale.
            self.status_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.5, self, "statusTick:", None, True)

    def statusTick_(self, timer):
        if self.window is None or not self.window.isVisible():
            timer.invalidate()
            self.status_timer = None
            return
        self._update_status()

    def windowWillClose_(self, notification):
        if self.status_timer is not None:
            self.status_timer.invalidate()
            self.status_timer = None
        self._cancel_capture()

    def _build(self):
        style = (NSWindowStyleMaskTitled | NSClosableWindowMask
                 | NSMiniaturizableWindowMask | NSResizableWindowMask)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WINDOW_W, WINDOW_H), style, NSBackingStoreBuffered, False)
        self.window.setTitle_(t("prefs_title", name="Multi-Tofu"))
        self.window.center()
        self.window.setReleasedWhenClosed_(False)
        self.window.setDelegate_(self)

        content = FlippedView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WINDOW_W, WINDOW_H))
        self.window.setContentView_(content)

        self.status_label = label("", 20, 14, WINDOW_W - 250, 20, bold=True, size=12)
        content.addSubview_(self.status_label)
        self.fix_button = button(t("fix_access"), WINDOW_W - 220, 10, 200, 26,
                                 self, "fixAccess:")
        self.fix_button.setHidden_(True)
        content.addSubview_(self.fix_button)

        content.addSubview_(label(t("global_shortcuts"), 20, 46, 260, 20, bold=True, size=13))
        specs = [(key, t("bind_" + key)) for key in BIND_ORDER]
        for i, (key, title) in enumerate(specs):
            x = 20 + (i % 2) * 430
            y = 74 + (i // 2) * 30
            content.addSubview_(label(title + t("colon"), x, y + 4, 175))
            btn = button(describe(self.app.config.data["binds"].get(key)),
                         x + 180, y, 160, 24, self, "recordGlobal:", i)
            self.global_buttons[key] = btn
            content.addSubview_(btn)

        content.addSubview_(label(t("wheel_modifier"), 20, 174, 130))
        self.wheel_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(135, 170, 120, 24), False)
        self.wheel_popup.addItemsWithTitles_(["alt", "ctrl", "cmd", "shift"])
        self.wheel_popup.setTarget_(self)
        self.wheel_popup.setAction_("wheelModifierChanged:")
        content.addSubview_(self.wheel_popup)

        self.wheel_check = NSButton.alloc().initWithFrame_(NSMakeRect(270, 170, 110, 24))
        self.wheel_check.setButtonType_(NSSwitchButton)
        self.wheel_check.setTitle_(t("wheel_on"))
        self.wheel_check.setTarget_(self)
        self.wheel_check.setAction_("wheelToggled:")
        content.addSubview_(self.wheel_check)

        content.addSubview_(label(t("wheel_style_label"), 626, 174, 94))
        self.style_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(722, 170, 156, 24), False)
        self.style_codes = ["wheel", "panel"]
        self.style_popup.addItemsWithTitles_(
            [t("wheel_style_wheel"), t("wheel_style_panel")])
        self.style_popup.setTarget_(self)
        self.style_popup.setAction_("wheelStyleChanged:")
        content.addSubview_(self.style_popup)

        content.addSubview_(label(t("leader_label"), 395, 174, 60))
        self.leader_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(450, 170, 160, 24), False)
        self.leader_popup.setTarget_(self)
        self.leader_popup.setAction_("leaderChanged:")
        content.addSubview_(self.leader_popup)

        content.addSubview_(label(t("language_label"), 20, 208, 110))
        self.language_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(135, 204, 180, 24), False)
        self.language_codes = ["auto"] + list(SUPPORTED)
        self.language_popup.addItemsWithTitles_(
            [language_name(code) for code in self.language_codes])
        self.language_popup.setTarget_(self)
        self.language_popup.setAction_("languageChanged:")
        content.addSubview_(self.language_popup)

        content.addSubview_(button(t("rescan_button"), 630, 204, 110, 24,
                                   self, "rescan:"))

        content.addSubview_(label(t("peek_target_label"), 20, 242, 150))
        self.peek_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(175, 238, 140, 24), False)
        self.peek_targets = ["leader", "next", "prev"]
        self.peek_popup.addItemsWithTitles_(
            [t("peek_target_" + key) for key in self.peek_targets])
        self.peek_popup.setTarget_(self)
        self.peek_popup.setAction_("peekTargetChanged:")
        content.addSubview_(self.peek_popup)

        # One checkbox per line on the left, the long explanation on the
        # right. Two columns of stacked checkboxes overlapped in French, where
        # every label is a third longer than in English.
        self.awake_check = NSButton.alloc().initWithFrame_(NSMakeRect(540, 238, 340, 22))
        self.awake_check.setButtonType_(NSSwitchButton)
        self.awake_check.setTitle_(t("awake_label"))
        self.awake_check.setTarget_(self)
        self.awake_check.setAction_("awakeToggled:")
        content.addSubview_(self.awake_check)
        content.addSubview_(label(t("awake_help"), 540, 264, WINDOW_W - 560, 60,
                                  size=10, color=NSColor.secondaryLabelColor()))

        self.launch_check = NSButton.alloc().initWithFrame_(NSMakeRect(20, 276, 500, 22))
        self.launch_check.setButtonType_(NSSwitchButton)
        self.launch_check.setTitle_(t("open_on_launch"))
        self.launch_check.setTarget_(self)
        self.launch_check.setAction_("launchToggled:")
        content.addSubview_(self.launch_check)

        self.hide_check = NSButton.alloc().initWithFrame_(NSMakeRect(20, 304, 500, 22))
        self.hide_check.setButtonType_(NSSwitchButton)
        self.hide_check.setTitle_(t("hide_others_label"))
        self.hide_check.setToolTip_(t("hide_others_help"))
        self.hide_check.setTarget_(self)
        self.hide_check.setAction_("hideOthersToggled:")
        content.addSubview_(self.hide_check)

        self.login_check = NSButton.alloc().initWithFrame_(NSMakeRect(20, 332, 500, 22))
        self.login_check.setButtonType_(NSSwitchButton)
        self.login_check.setTitle_(t("login_label"))
        self.login_check.setTarget_(self)
        self.login_check.setAction_("loginToggled:")
        content.addSubview_(self.login_check)
        self.login_note = label("", 20, 356, 500, 16, size=10,
                                color=NSColor.secondaryLabelColor())
        content.addSubview_(self.login_note)

        self.vm_check = NSButton.alloc().initWithFrame_(NSMakeRect(540, 332, 340, 22))
        self.vm_check.setButtonType_(NSSwitchButton)
        self.vm_check.setTitle_(t("vm_target_label"))
        self.vm_check.setToolTip_(t("vm_target_help"))
        self.vm_check.setTarget_(self)
        self.vm_check.setAction_("vmTargetToggled:")
        content.addSubview_(self.vm_check)

        content.addSubview_(label(t("characters"), 20, 386, 200, 20, bold=True, size=13))
        muted = NSColor.secondaryLabelColor()
        for text, col_x, width in [(t("col_order"), 8, 40), (t("col_on"), 64, 40),
                                   (t("col_character"), 124, 165),
                                   (t("col_class"), 300, 95),
                                   (t("role_label"), 400, 125),
                                   (t("col_team"), 532, 125),
                                   (t("col_key"), 666, 150)]:
            content.addSubview_(
                label(text, 16 + col_x, 416, width, 16, size=10, color=muted))

        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(16, 436, WINDOW_W - 32, WINDOW_H - 454))
        scroll.setHasVerticalScroller_(True)
        scroll.setDrawsBackground_(False)
        scroll.setAutoresizingMask_(2 | 16)  # width + height sizable
        self.rows_view = FlippedView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WINDOW_W - 40, 10))
        scroll.setDocumentView_(self.rows_view)
        content.addSubview_(scroll)

    # ---------- data ----------

    def reload(self):
        if self.window is None:
            return
        cfg = self.app.config.data
        self._update_status()
        self.wheel_popup.selectItemWithTitle_(cfg.get("wheel_modifier", "alt"))
        target = cfg.get("peek_target", "leader")
        if target in self.peek_targets:
            self.peek_popup.selectItemAtIndex_(self.peek_targets.index(target))
        self.awake_check.setState_(1 if appnap.is_disabled(self.app.config) else 0)
        self.launch_check.setState_(
            1 if cfg.get("open_settings_on_launch", True) else 0)
        self.hide_check.setState_(1 if cfg.get("hide_others") else 0)
        self.vm_check.setState_(1 if cfg.get("vm_target_enabled", True) else 0)
        self.login_check.setEnabled_(loginitem.available())
        self.login_check.setState_(1 if loginitem.is_enabled() else 0)
        if not loginitem.available():
            self.login_note.setStringValue_("")
        elif loginitem.needs_approval():
            self.login_note.setStringValue_(t("login_approve"))
        else:
            self.login_note.setStringValue_(t("login_help")[:110])
        code = cfg.get("language", "auto")
        if code in self.language_codes:
            self.language_popup.selectItemAtIndex_(self.language_codes.index(code))
        self.wheel_check.setState_(1 if cfg.get("wheel_enabled", True) else 0)
        style = cfg.get("wheel_style", "wheel")
        self.style_popup.selectItemAtIndex_(
            self.style_codes.index(style) if style in self.style_codes else 0)
        for key, btn in self.global_buttons.items():
            btn.setTitle_(describe(cfg["binds"].get(key)))

        accounts = self.app.scanner.accounts
        names = [a["name"] for a in accounts]
        self.leader_popup.removeAllItems()
        self.leader_popup.addItemsWithTitles_([t("option_none")] + names)
        leader = cfg.get("leader_name", "")
        self.leader_popup.selectItemWithTitle_(
            leader if leader in names else t("option_none"))

        for sub in list(self.rows_view.subviews()):
            sub.removeFromSuperview()
        self.bind_buttons = {}

        teams = cfg.get("teams", ["Team 1"])
        rank = {}
        for acc in accounts:
            if not acc["is_menu"]:
                rank[acc["name"]] = len(rank) + 1
        height = max(10, len(accounts) * ROW_HEIGHT + 10)
        self.rows_view.setFrameSize_((WINDOW_W - 40, height))

        for i, acc in enumerate(accounts):
            y = i * ROW_HEIGHT + 4
            # type a number to place a character, which beats clicking an
            # arrow six times to sort a team by initiative
            position = NSTextField.alloc().initWithFrame_(NSMakeRect(8, y, 38, 24))
            position.setStringValue_("" if acc["is_menu"] else str(rank.get(acc["name"], "")))
            position.setAlignment_(1)  # centred
            position.setEditable_(not acc["is_menu"])
            position.setEnabled_(not acc["is_menu"])
            position.setTarget_(self)
            position.setAction_("positionChanged:")
            position.setTag_(i)
            self.rows_view.addSubview_(position)

            check = NSButton.alloc().initWithFrame_(NSMakeRect(64, y, 22, 24))
            check.setButtonType_(NSSwitchButton)
            check.setTitle_("")
            check.setState_(1 if acc["active"] else 0)
            check.setTarget_(self)
            check.setAction_("toggleActive:")
            check.setTag_(i)
            self.rows_view.addSubview_(check)

            icon_view = NSImageView.alloc().initWithFrame_(NSMakeRect(92, y, 24, 24))
            icon_view.setImage_(load_icon(acc.get("slug")))
            icon_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
            self.rows_view.addSubview_(icon_view)

            self.rows_view.addSubview_(
                label(acc["name"], 124, y + 4, 165, 18, bold=not acc["is_menu"]))
            self.rows_view.addSubview_(
                label(acc.get("class_name") or "-", 300, y + 4, 95, 18, size=11,
                      color=NSColor.secondaryLabelColor()))

            role_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(400, y, 125, 24), False)
            role_popup.addItemsWithTitles_([t("role_" + key) for key in ROLE_KEYS])
            current_role = cfg.get("roles", {}).get(acc["name"], "none")
            role_popup.selectItemAtIndex_(
                ROLE_KEYS.index(current_role) if current_role in ROLE_KEYS else 0)
            role_popup.setTarget_(self)
            role_popup.setAction_("roleChanged:")
            role_popup.setTag_(i)
            self.rows_view.addSubview_(role_popup)

            popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(532, y, 125, 24), False)
            popup.addItemsWithTitles_([team_display(name) for name in teams])
            current = acc["team"] if acc["team"] in teams else teams[0]
            popup.selectItemAtIndex_(teams.index(current))
            popup.setTarget_(self)
            popup.setAction_("teamChanged:")
            popup.setTag_(i)
            self.rows_view.addSubview_(popup)

            bind = cfg.get("character_binds", {}).get(acc["name"])
            btn = button(describe(bind), 666, y, 150, 24, self, "recordChar:", i)
            self.bind_buttons[acc["name"]] = btn
            self.rows_view.addSubview_(btn)

    # ---------- actions ----------

    @objc.python_method
    def _update_status(self):
        from .accounts import accessibility_trusted
        trusted = accessibility_trusted()
        count = len(self.app.scanner.accounts)
        clashes = conflicts(self.app.config.data.get("binds", {}),
                            self.app.config.data.get("character_binds", {}))
        if not trusted:
            text = t("status_no_access")
            colour = NSColor.systemRedColor()
        elif clashes:
            names = ", ".join(t("bind_" + n) if ("bind_" + n) in STRINGS else n
                              for n in clashes[0])
            text = t("status_conflict", actions=names)
            colour = NSColor.systemOrangeColor()
        elif count == 0:
            text = t("status_no_client")
            colour = NSColor.secondaryLabelColor()
        else:
            rotation = len(self.app.scanner.cycle_list())
            text = t("status_ready", count=count, rotation=rotation)
            colour = NSColor.systemGreenColor()
        self.status_label.setStringValue_(text)
        self.status_label.setTextColor_(colour)
        self.fix_button.setHidden_(trusted)

    def fixAccess_(self, sender):
        self._cancel_capture()
        from .app import APP_NAME
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("fix_access_title", name=APP_NAME))
        alert.setInformativeText_(t("fix_access_body", name=APP_NAME))
        alert.addButtonWithTitle_(t("fix_reset"))
        alert.addButtonWithTitle_(t("fix_open_settings"))
        alert.addButtonWithTitle_(t("fix_cancel"))
        NSApp.activateIgnoringOtherApps_(True)
        # A sheet, not runModal. A free standing alert from an accessory app
        # opens behind the window that raised it.
        alert.beginSheetModalForWindow_completionHandler_(
            self.window, self._fixAccessDone)

    @objc.python_method
    def _fixAccessDone(self, choice):
        from .app import open_accessibility_pane, repair_accessibility
        if choice == 1000:
            if repair_accessibility():
                NSApp.terminate_(None)
                return
            open_accessibility_pane()
        elif choice == 1001:
            open_accessibility_pane()

    @objc.python_method
    def _capture(self, button_ref, apply_fn):
        if not self.app.hotkeys_running:
            button_ref.setTitle_(t("grant_first"))
            return
        previous = button_ref.title()
        button_ref.setTitle_(t("press_a_key"))

        def done(keycode, flags):
            # hand the work to the next run loop pass, never do it inside the
            # event tap callback
            bind = {"keycode": keycode, "flags": int(flags)}
            self._release_elsewhere(bind)
            apply_fn(bind)
            self.app.config.save()
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0, self, "reloadLater:", None, False)

        self.app.hotkeys.capture = done
        del previous

    def reloadLater_(self, timer):
        self.reload()

    @objc.python_method
    def _release_elsewhere(self, bind):
        """One key, one action. Whoever held it loses it."""
        cfg = self.app.config.data
        for name, existing in list(cfg.get("binds", {}).items()):
            if same_bind(existing, bind):
                cfg["binds"][name] = {"keycode": None, "flags": 0}
        for name, existing in list(cfg.get("character_binds", {}).items()):
            if same_bind(existing, bind):
                cfg["character_binds"].pop(name, None)

    @objc.python_method
    def _cancel_capture(self):
        """Touching any other control abandons a recording in progress. A
        capture that outlives the control it belongs to fires into a button
        that no longer exists."""
        if self.app.hotkeys.capture is not None:
            self.app.hotkeys.capture = None

    def recordGlobal_(self, sender):
        index = sender.tag()
        if not (0 <= index < len(BIND_ORDER)):
            return
        key = BIND_ORDER[index]

        def apply(bind):
            self.app.config.data["binds"][key] = bind
        self._capture(sender, apply)


    def recordChar_(self, sender):
        accounts = self.app.scanner.accounts
        if sender.tag() >= len(accounts):
            return
        name = accounts[sender.tag()]["name"]

        def apply(bind):
            self.app.config.data.setdefault("character_binds", {})[name] = bind
        self._capture(sender, apply)


    def toggleActive_(self, sender):
        accounts = self.app.scanner.accounts
        if sender.tag() >= len(accounts):
            return
        name = accounts[sender.tag()]["name"]
        state = bool(sender.state())
        self.app.config.data["accounts_state"][name] = state
        accounts[sender.tag()]["active"] = state
        self.app.config.save()


    def teamChanged_(self, sender):
        self._cancel_capture()
        accounts = self.app.scanner.accounts
        if sender.tag() >= len(accounts):
            return
        name = accounts[sender.tag()]["name"]
        teams = self.app.config.data.get("teams", ["Team 1"])
        index = sender.indexOfSelectedItem()
        team = teams[index] if 0 <= index < len(teams) else teams[0]
        self.app.config.data["accounts_team"][name] = team
        accounts[sender.tag()]["team"] = team
        self.app.config.save()
        self.app.rebuild_menu()


    def leaderChanged_(self, sender):
        self._cancel_capture()
        title = sender.titleOfSelectedItem()
        self.app.config.data["leader_name"] = ("" if title == t("option_none")
                                               else title)
        self.app.config.save()
        self.app.refresh()


    def positionChanged_(self, sender):
        self._cancel_capture()
        accounts = self.app.scanner.accounts
        if sender.tag() >= len(accounts):
            return
        account = accounts[sender.tag()]
        if account["is_menu"]:
            return
        try:
            wanted = int(sender.stringValue().strip())
        except ValueError:
            self.reload()
            return
        ordered = [a["name"] for a in accounts if not a["is_menu"]]
        if account["name"] not in ordered:
            return
        wanted = max(1, min(len(ordered), wanted)) - 1
        ordered.remove(account["name"])
        ordered.insert(wanted, account["name"])
        self._apply_order(ordered)

    @objc.python_method
    def _apply_order(self, ordered):
        """Rewrite the saved order, keeping characters that are offline right
        now in the slots they already hold."""
        saved = self.app.config.data.get("custom_order", [])
        slots = [i for i, name in enumerate(saved) if name in ordered]
        for slot, name in zip(slots, ordered):
            saved[slot] = name
        for name in ordered:
            if name not in saved:
                saved.append(name)
        self.app.config.data["custom_order"] = saved
        self.app.config.save()
        self.app.refresh()

    def roleChanged_(self, sender):
        self._cancel_capture()
        accounts = self.app.scanner.accounts
        if sender.tag() >= len(accounts):
            return
        name = accounts[sender.tag()]["name"]
        role = ROLE_KEYS[sender.indexOfSelectedItem()]
        self.app.config.data.setdefault("roles", {})[name] = role
        accounts[sender.tag()]["role"] = role
        self.app.config.save()

    def peekTargetChanged_(self, sender):
        self._cancel_capture()
        self.app.config.data["peek_target"] = \
            self.peek_targets[sender.indexOfSelectedItem()]
        self.app.config.save()

    def loginToggled_(self, sender):
        self._cancel_capture()
        wanted = bool(sender.state())
        loginitem.set_enabled(wanted)
        self.app.config.data["launch_at_login"] = wanted
        self.app.config.save()
        self.reload()

    def launchToggled_(self, sender):
        self._cancel_capture()
        self.app.config.data["open_settings_on_launch"] = bool(sender.state())
        self.app.config.save()

    def hideOthersToggled_(self, sender):
        self._cancel_capture()
        wanted = bool(sender.state())
        self.app.config.data["hide_others"] = wanted
        self.app.config.save()
        if not wanted:
            # turning it off has to give the clients back, not leave them
            # invisible until the next switch
            self.app.scanner.unhide_all()

    def vmTargetToggled_(self, sender):
        self._cancel_capture()
        self.app.config.data["vm_target_enabled"] = bool(sender.state())
        self.app.config.save()
        self.app.refresh()

    def wheelStyleChanged_(self, sender):
        self._cancel_capture()
        self.app.config.data["wheel_style"] = self.style_codes[sender.indexOfSelectedItem()]
        self.app.config.save()

    def awakeToggled_(self, sender):
        self._cancel_capture()
        wanted = bool(sender.state())
        appnap.set_disabled(self.app.config, wanted)
        self.app.config.data["keep_clients_awake"] = wanted
        self.app.config.save()
        sender.setState_(1 if appnap.is_disabled(self.app.config) else 0)

    def languageChanged_(self, sender):
        self._cancel_capture()
        code = self.language_codes[sender.indexOfSelectedItem()]
        self.app.config.data["language"] = code
        self.app.config.save()
        set_language(code)
        self.app.rebuild_menu()
        # every label was built with the old language, so rebuild the window
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0, self, "rebuildWindow:", None, False)

    def rebuildWindow_(self, timer):
        self.app.hotkeys.capture = None
        if self.window is not None:
            self.window.orderOut_(None)
        self.window = None
        self.bind_buttons = {}
        self.global_buttons = {}
        self.show()

    def wheelModifierChanged_(self, sender):
        self._cancel_capture()
        self.app.config.data["wheel_modifier"] = sender.titleOfSelectedItem()
        self.app.config.save()


    def wheelToggled_(self, sender):
        self._cancel_capture()
        self.app.config.data["wheel_enabled"] = bool(sender.state())
        self.app.config.save()


    @objc.python_method
    def _move(self, index, delta):
        accounts = self.app.scanner.accounts
        if not (0 <= index < len(accounts)):
            return
        order = self.app.config.data.get("custom_order", [])
        name = accounts[index]["name"]
        target = index + delta
        if not (0 <= target < len(accounts)):
            return
        other = accounts[target]["name"]
        try:
            i, j = order.index(name), order.index(other)
        except ValueError:
            return
        order[i], order[j] = order[j], order[i]
        self.app.config.save()
        self.app.refresh()

    def moveUp_(self, sender):
        self._move(sender.tag(), -1)


    def moveDown_(self, sender):
        self._move(sender.tag(), 1)


    def rescan_(self, sender):
        self._cancel_capture()
        self.app.refresh()
