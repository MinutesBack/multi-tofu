"""Global hotkeys through a CGEventTap. Needs Accessibility permission."""
import Quartz

from .keys import MODIFIER_MASKS, clean_flags, matches

TAP_DISABLED = {Quartz.kCGEventTapDisabledByTimeout,
                Quartz.kCGEventTapDisabledByUserInput}


class HotkeyManager:
    """Watches the key stream and calls back on matching binds.

    on_action(name)          a bound key was pressed
    on_modifier(down)        the wheel modifier went down / up
    on_mouse(x, y)           pointer moved while the wheel modifier is held
    """

    def __init__(self, config, on_action, on_modifier=None, on_mouse=None,
                 on_peek=None):
        self.config = config
        self.on_action = on_action
        self.on_modifier = on_modifier
        self.on_mouse = on_mouse
        self.on_peek = on_peek
        self.peek_down = False
        self.tap = None
        self.source = None
        self.mouse_tap = None
        self.mouse_source = None
        self.modifier_down = False
        self.enabled = True
        self.capture = None  # set to a callable to grab the next keypress

    # ---------- binds ----------

    def _all_binds(self):
        cfg = self.config.data
        binds = dict(cfg.get("binds", {}))
        binds.pop("peek", None)  # handled on its own, it needs the key release
        out = [(f"action:{name}", bind) for name, bind in binds.items()]
        for pseudo, bind in cfg.get("character_binds", {}).items():
            out.append((f"char:{pseudo}", bind))
        return out

    def _wheel_mask(self):
        if not self.config.data.get("wheel_enabled", True):
            return None
        return MODIFIER_MASKS.get(self.config.data.get("wheel_modifier", "alt"))

    # ---------- tap ----------

    def start(self):
        mask = (Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
                | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged))
        self.tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            mask,
            self._callback,
            None,
        )
        if not self.tap:
            return False
        self.source = Quartz.CFMachPortCreateRunLoopSource(None, self.tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(), self.source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self.tap, True)
        return True

    def start_mouse(self):
        """Only while the wheel is on screen."""
        if self.mouse_tap is not None:
            return True
        self.mouse_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            Quartz.CGEventMaskBit(Quartz.kCGEventMouseMoved)
            | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDragged)
            | Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseDragged),
            self._mouse_callback, None)
        if not self.mouse_tap:
            return False
        self.mouse_source = Quartz.CFMachPortCreateRunLoopSource(
            None, self.mouse_tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(),
                                  self.mouse_source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self.mouse_tap, True)
        return True

    def stop_mouse(self):
        if self.mouse_tap:
            Quartz.CGEventTapEnable(self.mouse_tap, False)
        if self.mouse_source:
            Quartz.CFRunLoopRemoveSource(
                Quartz.CFRunLoopGetCurrent(), self.mouse_source,
                Quartz.kCFRunLoopCommonModes)
        self.mouse_tap = None
        self.mouse_source = None

    def _mouse_callback(self, proxy, event_type, event, refcon):
        if event_type in TAP_DISABLED:
            Quartz.CGEventTapEnable(self.mouse_tap, True)
            return event
        try:
            if self.modifier_down and self.on_mouse:
                loc = Quartz.CGEventGetLocation(event)
                self.on_mouse(loc.x, loc.y)
        except Exception:
            pass
        return event

    def stop(self):
        self.stop_mouse()
        if self.tap:
            Quartz.CGEventTapEnable(self.tap, False)
        if self.source:
            Quartz.CFRunLoopRemoveSource(
                Quartz.CFRunLoopGetCurrent(), self.source, Quartz.kCFRunLoopCommonModes)
        self.tap = None
        self.source = None

    def _callback(self, proxy, event_type, event, refcon):
        if event_type in TAP_DISABLED:
            Quartz.CGEventTapEnable(self.tap, True)
            return event
        if not self.enabled:
            return event
        try:
            return self._handle(event_type, event)
        except Exception:
            return event

    def _handle(self, event_type, event):
        flags = clean_flags(Quartz.CGEventGetFlags(event))

        if event_type == Quartz.kCGEventFlagsChanged:
            wheel_mask = self._wheel_mask()
            if wheel_mask is not None:
                down = bool(flags & wheel_mask)
                if down != self.modifier_down:
                    self.modifier_down = down
                    if self.on_modifier:
                        self.on_modifier(down)
            return event

        peek = self.config.data.get("binds", {}).get("peek")
        peek_code = peek.get("keycode") if peek else None

        if event_type == Quartz.kCGEventKeyUp:
            if not self.peek_down:
                return event
            keycode = int(Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode))
            if peek_code is not None and keycode == peek_code:
                self.peek_down = False
                if self.on_peek:
                    self.on_peek(False)
                return None
            return event

        if event_type == Quartz.kCGEventKeyDown:
            keycode = int(Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode))
            if self.capture is None and peek_code is not None \
                    and keycode == peek_code \
                    and clean_flags(peek.get("flags", 0)) == flags:
                if not self.peek_down:
                    self.peek_down = True
                    if self.on_peek:
                        self.on_peek(True)
                return None  # also swallows the auto repeat
            if self.capture is not None:
                callback, self.capture = self.capture, None
                callback(keycode, flags)
                return None
            for name, bind in self._all_binds():
                if matches(bind, keycode, flags):
                    self.on_action(name)
                    if self.config.data.get("swallow_bound_keys", True):
                        return None
                    return event
        return event
