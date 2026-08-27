"""Virtual keycode helpers. Binds are stored as keycodes so they survive
an AZERTY / QWERTY switch: the physical key is what matters."""

import Quartz

from .i18n import t

MASK_CMD = Quartz.kCGEventFlagMaskCommand
MASK_ALT = Quartz.kCGEventFlagMaskAlternate
MASK_CTRL = Quartz.kCGEventFlagMaskControl
MASK_SHIFT = Quartz.kCGEventFlagMaskShift
MASK_ALL = MASK_CMD | MASK_ALT | MASK_CTRL | MASK_SHIFT

MODIFIER_MASKS = {
    "cmd": MASK_CMD,
    "alt": MASK_ALT,
    "ctrl": MASK_CTRL,
    "shift": MASK_SHIFT,
}

# Physical keys that only ever act as modifiers.
MODIFIER_KEYCODES = {54, 55, 56, 57, 58, 59, 60, 61, 62, 63}

# Label per keycode on a US layout. Letter keys differ on AZERTY, so the
# prefs window records what you actually press and shows this as a hint.
KEYCODE_LABELS = {
    0: "A", 1: "S", 2: "D", 3: "F", 4: "H", 5: "G", 6: "Z", 7: "X", 8: "C",
    9: "V", 11: "B", 12: "Q", 13: "W", 14: "E", 15: "R", 16: "Y", 17: "T",
    18: "1", 19: "2", 20: "3", 21: "4", 22: "6", 23: "5", 24: "=", 25: "9",
    26: "7", 27: "-", 28: "8", 29: "0", 30: "]", 31: "O", 32: "U", 33: "[",
    34: "I", 35: "P", 37: "L", 38: "J", 39: "'", 40: "K", 41: ";", 42: "\\",
    43: ",", 44: "/", 45: "N", 46: "M", 47: ".", 50: "`",
    36: "Return", 48: "Tab", 49: "Space", 51: "Delete", 53: "Escape",
    65: "Num .", 67: "Num *", 69: "Num +", 71: "Num Clear", 75: "Num /",
    76: "Num Enter", 78: "Num -", 81: "Num =", 82: "Num 0", 83: "Num 1",
    84: "Num 2", 85: "Num 3", 86: "Num 4", 87: "Num 5", 88: "Num 6",
    89: "Num 7", 91: "Num 8", 92: "Num 9",
    96: "F5", 97: "F6", 98: "F7", 99: "F3", 100: "F8", 101: "F9",
    103: "F11", 105: "F13", 107: "F14", 109: "F10", 111: "F12", 113: "F15",
    114: "Help", 115: "Home", 116: "Page Up", 117: "Forward Delete",
    118: "F4", 119: "End", 120: "F2", 121: "Page Down", 122: "F1",
    123: "Left", 124: "Right", 125: "Down", 126: "Up",
    54: "Right Cmd", 55: "Cmd", 56: "Shift", 57: "Caps Lock", 58: "Option",
    59: "Control", 60: "Right Shift", 61: "Right Option", 62: "Right Control",
}


def clean_flags(flags):
    return int(flags) & MASK_ALL


def describe(bind):
    """'Control + F1' for display."""
    if not bind:
        return t("bind_empty")
    flags = clean_flags(bind.get("flags", 0))
    parts = []
    if flags & MASK_CTRL:
        parts.append("Control")
    if flags & MASK_ALT:
        parts.append("Option")
    if flags & MASK_SHIFT:
        parts.append("Shift")
    if flags & MASK_CMD:
        parts.append("Command")
    code = bind.get("keycode")
    if code is None:
        return " + ".join(parts) if parts else t("bind_empty")
    parts.append(KEYCODE_LABELS.get(code, f"Key {code}"))
    return " + ".join(parts)


def matches(bind, keycode, flags):
    if not bind or bind.get("keycode") is None:
        return False
    return bind["keycode"] == keycode and clean_flags(bind.get("flags", 0)) == clean_flags(flags)
