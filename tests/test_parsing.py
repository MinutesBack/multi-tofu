"""Pure-logic tests. No windows, no permissions, safe to run in CI."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MULTITOFU_CONFIG", "/tmp/multitofu_parsing_test.json")

from multitofu.accounts import Scanner
from multitofu.classes import to_slug
from multitofu.config import Config
from multitofu.i18n import STRINGS, SUPPORTED, set_language, t, team_display
from multitofu.keys import describe, matches

FAILURES = []


def check(label, actual, expected):
    ok = actual == expected
    if not ok:
        FAILURES.append(f"{label}: got {actual!r}, expected {expected!r}")
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")


def main():
    set_language("en")  # the placeholder is localised, pin it for the test
    scanner = Scanner(Config())

    print("VM target")
    scanner.config.data["vm_target_enabled"] = False
    check("disabled VM has no windows", scanner._raw_vm_windows(), [])
    scanner.config.data["vm_target_enabled"] = True

    class StubScanner(Scanner):
        def _raw_windows(self):
            return [(101, object(), "Mac-Hero - Iop - 3.7.0 - Release")]

        def _raw_vm_windows(self):
            return [(202, object(), "Windows 11 Dofus")]

    with tempfile.TemporaryDirectory() as folder:
        vm_scanner = StubScanner(Config(os.path.join(folder, "config.json")))
        vm_rows = vm_scanner.scan()
        check("VM joins discovered accounts",
              [(a["name"], a["kind"]) for a in vm_rows],
              [("Mac-Hero", "dofus"), ("Dofus (Windows VM)", "vm")])
        check("VM joins shortcut rotation",
              [a["name"] for a in vm_scanner.cycle_list()],
              ["Mac-Hero", "Dofus (Windows VM)"])

    print("window titles")
    cases = [
        ("Account 1 - Iop - 3.6.10.11 - Release", ("Account 1", "Iop", False)),
        ("Account 2 - Cra - 3.7.0.1 - Beta", ("Account 2", "Cra", False)),
        ("Account 3 - 3.6.10.11 - Release", ("Account 3", None, False)),
        ("Dofus 3.6.10.11 - Release", ("Account 1", None, True)),
        ("Dofus", ("Account 1", None, True)),
        ("", ("Account 1", None, True)),
        # a character whose name merely starts with the product name
        ("Dofusman - Iop - 3.6.10.11 - Release", ("Dofusman", "Iop", False)),
    ]
    for title, expected in cases:
        check(f"parse {title!r}", scanner.parse_title(title, 1), expected)

    print("class icons")
    for name, expected in [("Iop", "iop"), ("Crâ", "cra"), ("Xélor", "xelor"),
                           ("Sacrier", "sacrieur"), ("Foggernaut", "steamer"),
                           ("Rogue", "roublard"), ("Masqueraider", "zobal"),
                           ("Forgelance", "forgelance"), ("", None),
                           ("Nonsense", None)]:
        check(f"slug {name!r}", to_slug(name), expected)

    print("keycode binds")
    check("describe F1", describe({"keycode": 122, "flags": 0}), "F1")
    check("describe Control+F1", describe({"keycode": 122, "flags": 262144}),
          "Control + F1")
    check("describe empty", describe(None), "None")
    check("match exact", matches({"keycode": 122, "flags": 0}, 122, 0), True)
    check("match ignores device bits",
          matches({"keycode": 122, "flags": 0}, 122, 0x100), True)
    check("match rejects wrong modifier",
          matches({"keycode": 122, "flags": 0}, 122, 262144), False)
    check("match rejects wrong key",
          matches({"keycode": 122, "flags": 0}, 120, 0), False)

    print("translations")
    missing = []
    for key, entry in STRINGS.items():
        for code in SUPPORTED:
            if not entry.get(code):
                missing.append(f"{key}/{code}")
    check("every string in every language", missing, [])

    placeholders = {}
    for key, entry in STRINGS.items():
        import re as _re
        fields = {tuple(sorted(_re.findall(r"\{(\w+)\}", entry[code])))
                  for code in SUPPORTED}
        if len(fields) > 1:
            placeholders[key] = fields
    check("placeholders match across languages", placeholders, {})

    for code in SUPPORTED:
        set_language(code)
        check(f"{code} team label localised", team_display("Team 2") != "", True)
        check(f"{code} placeholder has a number",
              "1" in t("account_placeholder", number=1), True)
    set_language("en")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for line in FAILURES:
            print("  -", line)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
