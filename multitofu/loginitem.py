"""Start Multi-Tofu when you log in.

macOS has no trigger for "start my app when that other app starts". launchd
can watch a path, a mount or a queue, but not another application launching,
and an app can only be told about launches once it is already running. So the
supported way to have Multi-Tofu there whenever you open the Ankama Launcher
is to have it there from login.

The cost is small: with no Dofus client running, a scan never reaches the
accessibility layer at all, it just finds nothing in the running application
list.
"""

NOT_REGISTERED, ENABLED, REQUIRES_APPROVAL, NOT_FOUND = 0, 1, 2, 3


def _service():
    try:
        from ServiceManagement import SMAppService
    except ImportError:
        return None
    try:
        return SMAppService.mainAppService()
    except Exception:
        return None


def available():
    """False when running from source, where there is no bundle to register."""
    service = _service()
    if service is None:
        return False
    try:
        return service.status() != NOT_FOUND
    except Exception:
        return False


def status():
    service = _service()
    if service is None:
        return NOT_FOUND
    try:
        return int(service.status())
    except Exception:
        return NOT_FOUND


def is_enabled():
    return status() == ENABLED


def needs_approval():
    return status() == REQUIRES_APPROVAL


def set_enabled(enabled):
    """Returns True when the request went through. The user may still have to
    approve it in System Settings, which is what needs_approval reports."""
    service = _service()
    if service is None:
        return False
    try:
        if enabled:
            ok, _ = service.registerAndReturnError_(None)
        else:
            ok, _ = service.unregisterAndReturnError_(None)
        return bool(ok)
    except Exception:
        return False
