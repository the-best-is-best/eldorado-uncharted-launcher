# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Every text of the launcher that a translation needs: qsTr("...") in the QML and t("...") in the Python
(launcher/). Checks a language file against them.

usage: i18n_texts.py [--check ar]      the texts without a translation, and translations whose fields differ
       i18n_texts.py --list            every text, one JSON string per line
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[1] / "launcher"
QSTR = re.compile(r'qsTr\(\s*"((?:[^"\\]|\\.)*)"')
FIELD = re.compile(r"\{[a-zA-Z_]\w*\}|%\d")


def qml_texts(folder: Path = LAUNCHER / "ui" / "qml") -> set[str]:
    texts = set()
    for file in folder.rglob("*.qml"):
        for match in QSTR.finditer(file.read_text(encoding="utf-8")):
            texts.add(json.loads(f'"{match.group(1)}"'))
    return texts


def python_texts(folder: Path = LAUNCHER) -> set[str]:
    """The first argument of every t(...) / i18n.t(...) call that is a plain string."""
    texts = set()
    for file in folder.rglob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"), str(file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args:
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                first = node.args[0]
                if name == "t" and isinstance(first, ast.Constant) and isinstance(first.value, str):
                    texts.add(first.value)
    return texts


# Tables whose texts reach t() through a variable (t(setting.title), t(VIEW_NAMES[view])...): file -> names.
TABLES: dict[str, tuple[str, ...]] = {
    "core/settings.py": ("SETTINGS", "TABS", "CHEAT_TEXTS", "OVERLAY_ITEMS"),
    "core/input_map.py": ("GROUPS", "PROMPT_STYLES"),
    "core/presets.py": ("PRESETS", "QUALITY_TITLES", "RECOMMENDED_TITLE"),
    "core/games.py": ("PLACES",),
    "core/trophies.py": ("GRADE_NAMES",),
    "core/profiles.py": ("NO_NAME", "SAME_NAME", "NO_PROFILE", "TOO_MANY"),
    "ui/settings_model.py": ("FILES_LAYOUT", "LAUNCHER_LAYOUT", "CAPTURE_HINT", "CHEATS_NOTE", "CREDITS"),
    "ui/saves_model.py": ("VIEW_NAMES", "VIEW_LINES", "ACCEPT_HINTS", "REMOVE_HINTS", "ARMED_NOTES"),
    "ui/bridge.py": ("NO_SAVE", "NO_WINDOW_NOTE"),
}
# Words for the player, not keys: two letters in a row, and not an identifier (save_profile, fsr1, chooseGameFolder).
WORDS = re.compile(r"[A-Za-z]{2}")
IDENTIFIER = re.compile(r"^(?:[a-z0-9_]+|[a-z]+[A-Z]\w*)$")


def table_texts(folder: Path = LAUNCHER) -> set[str]:
    texts = set()
    for relative, names in TABLES.items():
        tree = ast.parse((folder / relative).read_text(encoding="utf-8"))
        for node in tree.body:
            targets = [node.target] if isinstance(node, ast.AnnAssign) else getattr(node, "targets", [])
            if not any(isinstance(target, ast.Name) and target.id in names for target in targets):
                continue
            for part in ast.walk(node.value):
                if isinstance(part, ast.JoinedStr):
                    continue
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    text = part.value
                    if WORDS.search(text) and not IDENTIFIER.match(text):
                        texts.add(text)
    return texts


def all_texts() -> set[str]:
    return {text for text in qml_texts() | python_texts() | table_texts() if text.strip()}


def fields(text: str) -> list[str]:
    return sorted(FIELD.findall(text))


def check(code: str) -> tuple[list[str], list[str]]:
    """(texts without a translation, texts whose translation lost or added a field)."""
    data = json.loads((LAUNCHER / "ui" / "i18n" / f"{code}.json").read_text(encoding="utf-8"))
    texts = all_texts()
    missing = sorted(text for text in texts if not data.get(text))
    broken = sorted(text for text, value in data.items() if text in texts and value and fields(text) != fields(value))
    return missing, broken


def main() -> None:
    if "--list" in sys.argv:
        for text in sorted(all_texts()):
            print(json.dumps(text, ensure_ascii=False))
        return
    code = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else "ar"
    missing, broken = check(code)
    sys.stdout.reconfigure(encoding="utf-8")
    for text in missing:
        print("missing:", json.dumps(text, ensure_ascii=False))
    for text in broken:
        print("fields differ:", json.dumps(text, ensure_ascii=False))
    print(f"{len(all_texts())} texts, {len(missing)} missing, {len(broken)} with other fields")
    sys.exit(1 if missing or broken else 0)


if __name__ == "__main__":
    main()
