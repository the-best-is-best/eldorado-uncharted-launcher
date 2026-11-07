# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The launcher's own language (not the games'): every text the player reads goes through t(). The English text
is the key; launcher/ui/i18n/<language>.json maps it to the translation. A text without one stays English.

Texts with values use {name} fields: t("Saved for {where}.", where=name)."""
from __future__ import annotations

import ctypes
import json
import re
import sys
from pathlib import Path

from . import paths

# The launcher's languages: (code, name in that language). "rtl": written right to left (the window mirrors).
LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ar", "العربية"), ("en", "English"), ("fr", "Français"), ("de", "Deutsch"), ("it", "Italiano"),
    ("es", "Español (España)"), ("es-419", "Español (Latinoamérica)"), ("pt", "Português (Portugal)"),
    ("pt-BR", "Português (Brasil)"), ("nl", "Nederlands"), ("da", "Dansk"), ("no", "Norsk"), ("sv", "Svenska"),
    ("fi", "Suomi"), ("pl", "Polski"), ("cs", "Čeština"), ("el", "Ελληνικά"), ("ru", "Русский"), ("tr", "Türkçe"),
    ("ja", "日本語"), ("ko", "한국어"), ("zh-Hant", "中文 (繁體)"),
)
RTL = frozenset({"ar"})
# Scripts written without letter spacing: Arabic letters join; Japanese, Korean and Chinese signs stand apart already.
UNSPACED = frozenset({"ar", "ja", "ko", "zh-Hant"})
FOLDER = paths.LAUNCHER_DIR / "ui" / "i18n"
SETTING = "ui_language"  # launcher.json

_language = "en"
_texts: dict[str, str] = {}


def t(text: str, **fields: object) -> str:
    """The text in the launcher's language, its {fields} filled in."""
    translated = _texts.get(text, text) if text else text
    own = text in _texts  # a translation of ours (the right-to-left mark only on those, never on game texts)
    if fields:
        try:
            translated = translated.format(**fields)
        except (KeyError, IndexError, ValueError):
            return text.format(**fields)  # a translation with a broken field: the English one
    return right_to_left(translated) if own else translated


RLM = "\u200f"  # right-to-left mark
ARABIC_LETTER = re.compile("[\u0600-\u06ff]")
FIRST_LETTER = re.compile("[A-Za-z\u0600-\u06ff]")


def right_to_left(text: str) -> str:
    """In a right-to-left language each line of a translation reads from the right, also one that starts with a
    Latin word ("El Dorado و...", "60 FPS • ..."): Qt takes a paragraph's direction from its first letter."""
    if not is_rtl() or not ARABIC_LETTER.search(text):
        return text
    return "\n".join(RLM + line if _starts_latin(line) else line for line in text.split("\n"))


def _starts_latin(line: str) -> bool:
    """A line whose first letter is Latin (one starting with an Arabic letter reads from the right already)."""
    first = FIRST_LETTER.search(line)
    return bool(first) and not ARABIC_LETTER.match(first.group()) and not line.startswith(RLM)


def language() -> str:
    return _language


def is_rtl(code: str | None = None) -> bool:
    return (code or _language) in RTL


def set_language(code: str, folder: Path | None = None) -> None:
    """Loads a language's texts (English: none). An unknown code or an unreadable file leaves English."""
    global _language, _texts
    if code not in dict(LANGUAGES):
        code = "en"
    texts: dict[str, str] = {}
    if code != "en":
        file = (folder or FOLDER) / f"{code}.json"
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            texts = {str(key): str(value) for key, value in data.items() if isinstance(value, str) and value}
        except (OSError, ValueError) as error:
            print(f"Launcher language {code}: {file} could not be read ({error})", file=sys.stderr, flush=True)
            code = "en"
    _language, _texts = code, texts


def windows_language() -> str:
    """The language of Windows' own menus, when the launcher has it (Arabic Windows: Arabic), else English."""
    if sys.platform != "win32":
        return "en"
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError):
        return "en"
    return _windows_code(lang_id)


# Windows' primary language ids (LANGID & 0x3FF) -> the launcher's languages; regional ones by the whole LANGID.
WINDOWS_PRIMARY: dict[int, str] = {0x01: "ar", 0x0C: "fr", 0x07: "de", 0x10: "it", 0x0A: "es", 0x16: "pt", 0x13: "nl",
                                   0x06: "da", 0x14: "no", 0x1D: "sv", 0x0B: "fi", 0x15: "pl", 0x05: "cs", 0x08: "el",
                                   0x19: "ru", 0x1F: "tr", 0x11: "ja", 0x12: "ko"}
WINDOWS_REGIONAL: dict[int, str] = {0x0416: "pt-BR", 0x0404: "zh-Hant", 0x0C04: "zh-Hant", 0x1404: "zh-Hant"}


def _windows_code(lang_id: int) -> str:
    if lang_id in WINDOWS_REGIONAL:
        return WINDOWS_REGIONAL[lang_id]
    code = WINDOWS_PRIMARY.get(lang_id & 0x3FF, "en")
    if code == "es" and lang_id not in (0x040A, 0x0C0A):  # Spanish outside Spain: Latin American Spanish
        return "es-419"
    return code


def chosen(stored: object) -> str:
    """The launcher's language: the one chosen in Settings, else Windows' own."""
    return str(stored) if stored in dict(LANGUAGES) else windows_language()
