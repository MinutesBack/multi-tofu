"""JSON config stored in ~/Library/Application Support/Multi-Tofu/config.json"""
import json
import os
import threading

CONFIG_DIR = os.path.expanduser("~/Library/Application Support/Multi-Tofu")
# MULTITOFU_CONFIG lets the test rig run against a throwaway config
CONFIG_PATH = os.environ.get("MULTITOFU_CONFIG") or os.path.join(CONFIG_DIR, "config.json")

# keycode-based binds: layout agnostic. 122=F1 120=F2 99=F3 118=F4 58=left alt
DEFAULTS = {
    "bundle_ids": ["com.Ankama.Dofus"],
    "title_separator": " - ",
    "classes": {},
    "accounts_state": {},
    "accounts_team": {},
    "custom_order": [],
    "leader_name": "",
    "current_mode": "ALL",
    "teams": ["Team 1", "Team 2", "Team 3"],
    "binds": {
        "next": {"keycode": 122, "flags": 0},
        "prev": {"keycode": 120, "flags": 0},
        "leader": {"keycode": 99, "flags": 0},
        "refresh": {"keycode": 118, "flags": 0},
        # Control+F1. A crowded menu bar can hide the status item behind the
        # notch, so there is always a way in from the keyboard.
        "prefs": {"keycode": 122, "flags": 262144},
        # the key above Tab, same physical spot on AZERTY and QWERTY
        "peek": {"keycode": 50, "flags": 0},
    },
    "character_binds": {},
    "roles": {},
    # what a bare peek looks at: leader, next or previous
    "peek_target": "leader",
    "keep_clients_awake": False,
    "wheel_enabled": True,
    "wheel_modifier": "alt",
    "wheel_radius": 148,
    "wheel_delay_ms": 200,
    "wheel_sounds": True,
    "volume_level": 50,
    "wheel_inner_radius": 44,
    "swallow_bound_keys": True,
    "hide_login_windows": False,
    # login windows stay listed in the menu bar but never come up on F1
    "login_windows_in_rotation": False,
    "scan_interval": 4.0,
    # Switch on when the menu bar is too full to show the status item.
    "show_dock_icon": False,
    # opening a menu bar app that shows nothing looks like it failed to start
    "open_settings_on_launch": True,
    # auto, en, fr, es or pt
    "language": "auto",
}


LEGACY_PATH = os.path.expanduser(
    "~/Library/Application Support/DosoftMac/config.json")


class Config:
    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self._lock = threading.RLock()
        self.data = dict(DEFAULTS)
        self._migrate_legacy()
        self.load()

    def _migrate_legacy(self):
        """Carry over settings from the pre-rename location, once."""
        if self.path != CONFIG_PATH or os.path.exists(self.path):
            return
        if not os.path.exists(LEGACY_PATH):
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(LEGACY_PATH, "r", encoding="utf-8") as src:
                stored = json.load(src)
            with open(self.path, "w", encoding="utf-8") as dst:
                json.dump(stored, dst, indent=2, ensure_ascii=False)
        except (OSError, json.JSONDecodeError):
            pass

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
            merged = dict(DEFAULTS)
            merged.update(stored)
            for key, val in DEFAULTS.items():
                if isinstance(val, dict) and isinstance(merged.get(key), dict):
                    base = dict(val)
                    base.update(merged[key])
                    merged[key] = base
            self.data = merged
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.data = dict(DEFAULTS)
            self.save()
        return self.data

    def save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
