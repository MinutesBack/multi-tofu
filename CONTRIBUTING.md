# Contributing

Thanks for looking.

## Setting up

```
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./run.sh --probe
```

Run from Terminal.app and grant Terminal Accessibility, or build the app with
`./tools/build_app.sh --install` and grant Multi-Tofu itself.

Before your first build, run `./tools/signing_identity.sh create`. It makes a
self-signed code signing certificate in its own keychain. Without it the build
signs ad-hoc, the designated requirement is the hash of the code itself, and
every rebuild costs you the Accessibility grant again while the row in System
Settings still looks switched on.

## Testing

Logic tests need nothing special:

```
./.venv/bin/python tests/test_parsing.py
```

The rotation and shortcut suites drive real windows. You do not need several
Dofus accounts, `tools/` builds stand-in clients:

```
./tools/build_mock_app.sh
./tools/mocks.sh start
MULTITOFU_CONFIG=/tmp/multitofu_test.json ./.venv/bin/python tests/test_rotation.py
./.venv/bin/python tests/test_hotkeys.py
./tools/mocks.sh stop
```

Give the shortcut suite a quiet machine. Anything that steals the front window
mid-run is reported as a skipped check.

## Things worth knowing before you change the core

- The event tap callback runs on the main run loop and macOS disables a tap
  whose callback overruns. Never do focus work inside it, hand it to the next
  run loop pass.
- `NSWorkspace.frontmostApplication()` goes stale inside a background agent.
  Read frontmost through the accessibility layer instead.
- A Unity client can report an empty `AXWindows` list while still answering
  `AXMainWindow`. Handle both.
- Cross-app activation on macOS 14+ needs `AXFrontmost` on the app element.
  `NSRunningApplication.activate` alone does not move a Unity client.
- Rebuilding the app invalidates its Accessibility grant, because the ad-hoc
  signature changes. Run `tccutil reset Accessibility fr.multitofu.app` after a
  rebuild.

## Not currently supported

Dofus Retro, and the Retro Autofocus feature from upstream. Autofocus reads
Windows toast notifications and macOS has no equivalent a third-party app can
subscribe to. Retro support is open if someone wants it.
