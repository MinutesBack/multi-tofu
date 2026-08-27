"""Keep backgrounded Dofus clients out of App Nap.

macOS throttles timers and I/O for apps with no visible window, which is
exactly what every client except the one in front looks like. A process cannot
lift that for another process at runtime, but the frameworks read
NSAppSleepDisabled out of the target app's own preference domain at launch, so
writing it there is the documented lever.

Everything here uses CFPreferences in process. An earlier version shelled out
to `defaults`, which froze the app: the read ran inside the event tap callback
while recording a shortcut, and a blocking subprocess there stalls the whole
main run loop.
"""
from Foundation import (
    CFPreferencesAppSynchronize, CFPreferencesCopyAppValue,
    CFPreferencesSetAppValue,
)

KEY = "NSAppSleepDisabled"


def _domains(config):
    return [b for b in config.data.get("bundle_ids", []) if b]


def is_disabled(config):
    """True when every watched client domain already opts out."""
    domains = _domains(config)
    if not domains:
        return False
    for domain in domains:
        try:
            value = CFPreferencesCopyAppValue(KEY, domain)
        except Exception:
            return False
        if not value:
            return False
    return True


def set_disabled(config, enabled):
    """Write or clear the opt-out for every watched client domain."""
    ok = True
    for domain in _domains(config):
        try:
            CFPreferencesSetAppValue(KEY, True if enabled else None, domain)
            CFPreferencesAppSynchronize(domain)
        except Exception:
            ok = False
    return ok
