# Multi-Tofu

A Dofus multi-account window switcher for macOS. Instant switch, a character
wheel, team split, and per-character keys, for Dofus 3 (Unity).

**[Website](https://minutesback.github.io/multi-tofu/)** · **English** · **[Français](README.fr.md)** · **[Español](README.es.md)** · **[Português](README.pt.md)**

An independent macOS port of [Dosoft](https://www.dosoft.fr), which is Windows
only. None of the Windows code carries over, since it is built on the Win32 API,
so this is a fresh implementation on the macOS Accessibility API, a CGEventTap
and AppKit.

<p align="center">
  <img src="docs/wheel.png" alt="The character wheel" width="380">
</p>

![Settings](docs/preferences.png)

## What it does

- **Instant switch.** Global shortcuts cycle to the next or previous client and
  jump straight back to your leader.
- **Character wheel.** Hold Option, a wheel appears at the cursor with a class
  icon per character. Move the mouse, release Option, that client is in front.
- **Team split.** Put characters in teams and cycle only inside the active team.
- **Direct binds.** One fixed key per character.
- **Menu bar.** Click any character to focus it, switch rotation, open settings.
- **Four languages.** English, French, Spanish and Portuguese, matched to your
  system on first run and switchable at any time.
- **Roles.** Tag each character and the wheel colours their segment by it, so
  past five clients you read colour instead of six names.
- **Peek.** Hold one key to look at another client, release and you are back
  where you were, rotation position intact.
- **Order by number.** Type a position to sort your rotation, useful when it
  follows initiative rather than the order clients happened to open.
- **Stays saved.** Order, teams, roles, leader and every shortcut are written to
  disk as you change them. Log out, come back tomorrow, it is all still there.
- **Opens where you left it.** Launching Multi-Tofu opens Settings, so it never
  looks like nothing happened. One click turns that off.
- **One key, one action.** Assigning a key another shortcut holds frees it
  there, rather than leaving two actions on one key where only one ever fires.

## Having it running when you play

macOS has no trigger for "start this app when that other app starts". launchd
can watch a path, a mount or a queue, but not another application launching,
and an app can only be told about launches once it is already running.

So there are two honest ways to have Multi-Tofu ready when you open the Ankama
Launcher.

**Start it at login.** A checkbox in Settings. It costs nothing while you are
not playing: with no Dofus client running, a scan never reaches the
accessibility layer, it just finds nothing in the list of running apps.

**Or watch the launcher's files.** Both the Ankama Launcher and the game write
to their own directories on startup, and launchd can watch those.

```
./tools/watch_ankama.sh install    # start Multi-Tofu when either writes
./tools/watch_ankama.sh status
./tools/watch_ankama.sh remove
```

It starts the app in the background, so nothing steals your focus, and
launching it twice is harmless because a second instance refuses to start.

## Where your setup lives

Everything you configure is written to
`~/Library/Application Support/Multi-Tofu/config.json` the moment you change it,
keyed by character name. Rotation order, teams, roles, leader, per character
keys and every shortcut. Close the clients, close the app, come back a week
later, log the same characters in and it is exactly as you left it.

Class icons are read from the game, not guessed. The window title carries the
class, so an Eniripsa shows the Eniripsa icon without you telling it anything.
The last known class is remembered per character, so a client that has not
finished loading still shows the right one.

## Character names

You do not type them in. Multi-Tofu reads the Dofus window title, so the moment
a character logs in their real name appears in the wheel, the menu and the
settings list.

A client that is open but still sitting on the login screen has no character on
it yet, so it shows as `Account 1`, `Account 2` and so on. Those placeholders
stay visible in the menu, where you can click one to go and log it in, but they
are kept out of the F1 rotation so a keypress never lands you on a window with
no character. Set `login_windows_in_rotation` to true if you want them included.

## Install

Download the `.zip` from
[Releases](https://github.com/MinutesBack/multi-tofu/releases), unzip it, drag
`Multi-Tofu.app` into Applications. No toolchain, no Python, no terminal.

The app is not signed with an Apple developer account, so the first time you
open it, right click the icon and choose **Open**, then confirm. If macOS still
refuses, go to System Settings > Privacy & Security and click **Open Anyway**.

Universal binary, runs on Apple Silicon and Intel.

### Accessibility permission

On first launch macOS asks for Accessibility. Multi-Tofu needs it to read Dofus
window titles and to listen for your shortcuts.

System Settings > Privacy & Security > Accessibility, switch Multi-Tofu on. No
need to quit, the shortcuts come on by themselves within a couple of seconds.

If you rebuild from source later, macOS drops the grant because the signature
changed. Run `tccutil reset Accessibility fr.multitofu.app` and approve again.

### Build it yourself instead

```
./tools/build_app.sh --install
```

## Where the interface is

Multi-Tofu is a background utility, so there is no main window. You reach it
three ways:

- **Dock icon**, when `show_dock_icon` is on. Click it to open Settings, right
  click it for the character list.
- **Menu bar icon**, the bird. Click for the character list and Settings.
- **Control+F1** opens Settings from anywhere, even with no client running.

Settings works with no game open. It shows whether Accessibility is on, how
many clients it can see, and lets you change every shortcut. The character list
fills in once clients are running.

A crowded menu bar is worth knowing about: macOS parks an overflow status item
behind the notch where it cannot be drawn, and the app still thinks it is
visible. Multi-Tofu detects that and offers the Dock icon instead.

## Run from source

```
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./run.sh
```

Run that from Terminal.app. macOS attributes Accessibility to whatever owns the
process, which from source is Terminal:

1. `./run.sh --grant` raises the system prompt
2. System Settings > Privacy & Security > Accessibility, switch on **Terminal**
3. Quit Terminal fully with Cmd+Q, reopen, run `./run.sh` again

Check what it can see at any time:

```
./run.sh --probe
```

## Default shortcuts

| Action | Key |
| --- | --- |
| Next character | F1 |
| Previous character | F2 |
| Focus leader | F3 |
| Rescan windows | F4 |
| Character wheel | hold Option |
| Peek at another client | hold ` |

Change any of them in Preferences. Binds are stored as physical keycodes, so
they hold up if you switch between AZERTY and QWERTY.

## Languages

English, French, Spanish and Portuguese. On first run it follows your macOS
language and falls back to English. Change it in Settings under Language, which
takes effect immediately.

<p align="center">
  <img src="docs/preferences-fr.png" alt="Settings in French" width="620">
</p>

Character names, class names and team assignments are never translated, and
teams are stored as `Team 1` internally whatever language you read them in, so
switching language never touches your configuration.

Adding a language means one dictionary in `multitofu/i18n.py`. The test suite
fails if any string is missing from any language or if the placeholders drift
apart between them.

## Config

`~/Library/Application Support/Multi-Tofu/config.json`

- `language` (default auto): auto, en, fr, es or pt.
- `login_windows_in_rotation` (default false): a client still on the login
  screen stays listed in the menu bar so you can click it, but F1 never lands
  on a window with no character on it.
- `hide_login_windows`: drop them entirely, menu included.
- `wheel_delay_ms` (default 200): how long Option must be held before the wheel
  appears, so a normal Option press in game does not trigger it.
- `swallow_bound_keys` (default true): bound keys do not reach Dofus.
- `scan_interval`: seconds between window rescans.

## Testing without several accounts

`tools/` builds `DofusMock.app`, a native stand-in client that opens one window
with a Dofus-shaped title. Several copies run under one bundle id, the way the
Ankama Launcher runs several real clients, so the whole rotation can be tested
with one account or none.

```
./tools/build_mock_app.sh
./tools/mocks.sh start        # 3 characters + 1 login window
MULTITOFU_CONFIG=/tmp/multitofu_test.json ./.venv/bin/python tests/test_rotation.py
./.venv/bin/python tests/test_hotkeys.py
./tools/mocks.sh stop
```

`test_hotkeys.py` posts genuine CGEvents and reads the focused window back from
the accessibility layer, so it exercises the same path your keyboard does. Give
it a quiet machine. Anything that grabs the front window mid-run is reported as
a skipped check rather than a failure, but the fewer of those the better.

## Known limits

- **Fullscreen.** The wheel is an overlay panel. Over a client in exclusive
  fullscreen it may not draw. Run Dofus windowed or borderless.
- **Retro Autofocus is not ported.** It reads Windows toast notifications and
  macOS has no equivalent a third-party app can subscribe to.
- **Dofus Retro is not supported yet.** Unity only.
- **Rebuilding costs the Accessibility grant.** macOS ties the grant to the
  app's code signature, and an ad-hoc signature changes every build. After
  running `build_app.sh` again, run
  `tccutil reset Accessibility fr.multitofu.app`, launch, and approve once.
  The app picks the grant up within two seconds, no relaunch needed.
- **Unity is slow to answer.** Accessibility calls are capped at 350 ms and
  focus work is deferred off the event tap callback, because macOS disables a
  tap whose callback overruns and that shows up as dropped keystrokes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). It lists the macOS quirks that cost the
most time to find, so read it before touching the focus or event tap code.

## If you were looking for

Dofus multi-account on Mac, Dofus multicompte Mac, Dofus multicuenta Mac, Dofus
multiconta Mac, Dofus multiboxing macOS, a Mac alternative to Organizer or
Dosoft, switching between several Dofus clients on macOS, an Ankama Launcher
multi client window switcher, or a Dofus 3 Unity character switcher for a
MacBook. This is that tool.

It does not automate play. No bot, no packet reading, no broadcasting one input
to several clients. It brings windows to the front and nothing else, which is
what keeps it safe to use.

## Licence

Apache License 2.0. See [LICENSE](LICENSE).

This is an independent port of [Dosoft](https://github.com/LuframeCode/dosoft),
which is Apache 2.0. Its class artwork, interface sounds and feature design are
reused under that licence, and [NOTICE](NOTICE) records exactly what came from
where.

Multi-Tofu is not affiliated with, endorsed by, or sponsored by Ankama Games.
DOFUS and all related names and artwork are the property of Ankama Games. The
class icons are included to let a player identify their own characters in their
own client. If you represent Ankama and want them removed, open an issue and
they will be taken out. The app falls back to a neutral icon for any class whose
artwork is missing, so removing them does not break anything.
