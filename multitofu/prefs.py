"""Preferences window: characters, teams, order, binds."""
import objc
from AppKit import (
    NSApp, NSBackingStoreBuffered, NSBezelStyleRounded, NSButton,
    NSClosableWindowMask, NSColor, NSFont, NSImageScaleProportionallyUpOrDown,
    NSImageView, NSMakeRect, NSMiniaturizableWindowMask, NSPopUpButton,
    NSResizableWindowMask, NSScrollView, NSSwitchButton, NSTextField,
    NSTitledWindowMask, NSView, NSWindow, NSWindowStyleMaskTitled,
)
from Foundation import NSObject, NSTimer

from .i18n import SUPPORTED, language_name, set_language, t, team_display
from .keys import MODIFIER_MASKS, describe
from .radial import load_icon

ROW_HEIGHT = 34
HEADER_HEIGHT = 118
WINDOW_W = 760
WINDOW_H = 650


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
        return self

    # ---------- window ----------

    def show(self):
        if self.window is None:
            self._build()
        self.reload()
        NSApp.activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)

    def _build(self):
        style = (NSWindowStyleMaskTitled | NSClosableWindowMask
                 | NSMiniaturizableWindowMask | NSResizableWindowMask)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WINDOW_W, WINDOW_H), style, NSBackingStoreBuffered, False)
        self.window.setTitle_(t("prefs_title", name="Multi-Tofu"))
        self.window.center()
        self.window.setReleasedWhenClosed_(False)

        content = FlippedView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WINDOW_W, WINDOW_H))
        self.window.setContentView_(content)

        self.status_label = label("", 20, 14, WINDOW_W - 40, 20, bold=True, size=12)
        content.addSubview_(self.status_label)

        content.addSubview_(label(t("global_shortcuts"), 20, 46, 260, 20, bold=True, size=13))
        specs = [("next", t("bind_next")), ("prev", t("bind_prev")),
                 ("leader", t("bind_leader")), ("refresh", t("bind_refresh")),
                 ("prefs", t("bind_prefs"))]
        for i, (key, title) in enumerate(specs):
            x = 20 + (i % 2) * 370
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

        content.addSubview_(label(t("characters"), 20, 238, 200, 20, bold=True, size=13))
        muted = NSColor.secondaryLabelColor()
        for text, col_x, width in [(t("col_order"), 4, 60), (t("col_on"), 66, 40),
                                   (t("col_character"), 124, 170),
                                   (t("col_class"), 300, 110),
                                   (t("col_team"), 415, 130),
                                   (t("col_key"), 555, 150)]:
            content.addSubview_(
                label(text, 16 + col_x, 262, width, 16, size=10, color=muted))

        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(16, 282, WINDOW_W - 32, WINDOW_H - 300))
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
        code = cfg.get("language", "auto")
        if code in self.language_codes:
            self.language_popup.selectItemAtIndex_(self.language_codes.index(code))
        self.wheel_check.setState_(1 if cfg.get("wheel_enabled", True) else 0)
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
        height = max(10, len(accounts) * ROW_HEIGHT + 10)
        self.rows_view.setFrameSize_((WINDOW_W - 40, height))

        for i, acc in enumerate(accounts):
            y = i * ROW_HEIGHT + 4
            self.rows_view.addSubview_(
                button("^", 4, y, 26, 24, self, "moveUp:", i))
            self.rows_view.addSubview_(
                button("v", 32, y, 26, 24, self, "moveDown:", i))

            check = NSButton.alloc().initWithFrame_(NSMakeRect(66, y, 22, 24))
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
                label(acc["name"], 124, y + 4, 170, 18, bold=not acc["is_menu"]))
            self.rows_view.addSubview_(
                label(acc.get("class_name") or "-", 300, y + 4, 110, 18, size=11,
                      color=NSColor.secondaryLabelColor()))

            popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(415, y, 130, 24), False)
            popup.addItemsWithTitles_([team_display(name) for name in teams])
            current = acc["team"] if acc["team"] in teams else teams[0]
            popup.selectItemAtIndex_(teams.index(current))
            popup.setTarget_(self)
            popup.setAction_("teamChanged:")
            popup.setTag_(i)
            self.rows_view.addSubview_(popup)

            bind = cfg.get("character_binds", {}).get(acc["name"])
            btn = button(describe(bind), 555, y, 150, 24, self, "recordChar:", i)
            self.bind_buttons[acc["name"]] = btn
            self.rows_view.addSubview_(btn)

    # ---------- actions ----------

    @objc.python_method
    def _update_status(self):
        from .accounts import accessibility_trusted
        trusted = accessibility_trusted()
        count = len(self.app.scanner.accounts)
        if not trusted:
            text = t("status_no_access")
            colour = NSColor.systemRedColor()
        elif count == 0:
            text = t("status_no_client")
            colour = NSColor.secondaryLabelColor()
        else:
            rotation = len(self.app.scanner.cycle_list())
            text = t("status_ready", count=count, rotation=rotation)
            colour = NSColor.systemGreenColor()
        self.status_label.setStringValue_(text)
        self.status_label.setTextColor_(colour)

    @objc.python_method
    def _capture(self, button_ref, apply_fn):
        if not self.app.hotkeys_running:
            button_ref.setTitle_(t("grant_first"))
            return
        previous = button_ref.title()
        button_ref.setTitle_(t("press_a_key"))

        def done(keycode, flags):
            apply_fn({"keycode": keycode, "flags": int(flags)})
            self.app.config.save()
            self.reload()

        self.app.hotkeys.capture = done
        del previous

    def recordGlobal_(self, sender):
        keys = ["next", "prev", "leader", "refresh", "prefs"]
        key = keys[sender.tag()]

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
        title = sender.titleOfSelectedItem()
        self.app.config.data["leader_name"] = ("" if title == t("option_none")
                                               else title)
        self.app.config.save()
        self.app.refresh()


    def languageChanged_(self, sender):
        code = self.language_codes[sender.indexOfSelectedItem()]
        self.app.config.data["language"] = code
        self.app.config.save()
        set_language(code)
        self.app.rebuild_menu()
        # every label was built with the old language, so rebuild the window
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0, self, "rebuildWindow:", None, False)

    def rebuildWindow_(self, timer):
        if self.window is not None:
            self.window.orderOut_(None)
        self.window = None
        self.bind_buttons = {}
        self.global_buttons = {}
        self.show()

    def wheelModifierChanged_(self, sender):
        self.app.config.data["wheel_modifier"] = sender.titleOfSelectedItem()
        self.app.config.save()


    def wheelToggled_(self, sender):
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
        self.app.refresh()

