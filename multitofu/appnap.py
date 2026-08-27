"""Keep backgrounded Dofus clients out of App Nap.

macOS throttles timers and I/O for apps with no visible windows, which is
exactly what every client except the one in front looks like. A process cannot
lift that for another process at runtime, but the frameworks read
NSAppSleepDisabled out of the target app's own preference domain at launch, so
writing it there is the documented lever.

Takes effect the next time a client starts.
"""
import subprocess

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
            out = subprocess.run(["defaults", "read", domain, KEY],
                                 capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return False
        if out.returncode != 0 or out.stdout.strip() not in ("1", "YES", "true"):
            return False
    return True


def set_disabled(config, enabled):
    """Write or remove the opt-out for every watched client domain."""
    ok = True
    for domain in _domains(config):
        args = (["defaults", "write", domain, KEY, "-bool", "YES"] if enabled
                else ["defaults", "delete", domain, KEY])
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            ok = False
            continue
        # deleting a key that was never there is not a failure
        if result.returncode != 0 and enabled:
            ok = False
    return ok
