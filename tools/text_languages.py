# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Which language each text file of a game holds (core.psarc text1/ps4/<n>.common), read from the texts themselves:
the letters of a script, and words or spellings only one language uses. The start script then loads the file of
the language the launcher chose (cheats.py text<n>), whatever the game's own language table or a fan translation
did to the numbers.

usage: text_languages.py <game folder (with its update laid over)> [u1|u2|u3]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabic_language import DATA_DIRS, Psarc  # noqa: E402

# The launcher's languages by the PS4 language number it sends (launcher/core/settings.py LANGUAGES).
LANGUAGE_IDS = {"1": "en-US", "18": "en-GB", "2": "fr", "4": "de", "5": "it", "3": "es", "20": "es-419", "7": "pt",
                "17": "pt-BR", "6": "nl", "14": "da", "15": "no", "13": "sv", "12": "fi", "16": "pl", "23": "cs",
                "25": "el", "8": "ru", "19": "tr", "0": "ja", "9": "ko", "10": "zh-Hant", "ar": "ar"}


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def _words(text: str, *words: str) -> int:
    return sum(_count(rf"\b{word}\b", text) for word in words)


def scores(text: str) -> dict[str, float]:
    """How much a text looks like each language (per thousand letters)."""
    letters = max(1, _count(r"\w", text)) / 1000
    s = {
        "ar": _count(r"[؀-ۿﭐ-﷿ﹰ-﻿]", text),
        "ja": _count(r"[぀-ヿ]", text) * 3,
        "ko": _count(r"[가-힯]", text),
        "zh-Hant": _count(r"[一-鿿]", text) - _count(r"[぀-ヿ]", text) * 2,
        "ru": _count(r"[Ѐ-ӿ]", text),
        "el": _count(r"[Ͱ-Ͽ]", text),
        "pl": _count(r"[łśżźąęń]", text) * 8 + _words(text, "nie", "jest", "się") * 4,
        "cs": _count(r"[řěůť]", text) * 8 + _words(text, "není", "jsou", "nebo") * 4,
        "tr": _count(r"[ışğ]", text) * 8 + _words(text, "bir", "için", "ve") * 4,
        "da": _count(r"[æø]", text) * 3 + _words(text, "af", "hvad", "ikke", "jeg", "og") * 4,
        "no": _count(r"[æø]", text) * 3 + _words(text, "av", "hva", "ikke", "jeg", "og") * 4,
        "sv": _count(r"å", text) * 2 + _words(text, "och", "inte", "jag", "är") * 6,
        "fi": _words(text, "ja", "ei", "on", "että", "sinä") * 6 - _count(r"å", text),
        "de": _words(text, "und", "der", "die", "nicht", "ist") * 6,
        "nl": _words(text, "het", "een", "niet", "van", "je") * 6,
        "fr": _words(text, "les", "vous", "avec", "pour", "est") * 6,
        "it": _words(text, "della", "che", "non", "il", "per") * 6,
        "es": _words(text, "los", "que", "con", "para", "las") * 6,
        "pt": _words(text, "não", "com", "para", "uma", "você") * 6,
        "en": _words(text, "the", "and", "you", "with", "for") * 6,
    }
    return {language: value / letters for language, value in s.items()}


# Languages that come in two regional files: (family, the region a higher regional score means, the other).
REGIONS = {"es": ("es-419", "es"), "pt": ("pt-BR", "pt"), "en": ("en-GB", "en-US"), "nordic": ("da", "no")}


def regional(family: str, text: str) -> int:
    """How much a text leans to the first region of its family (REGIONS)."""
    if family == "es":   # Latin America: ustedes, computadora, agarrar; Spain: vosotros, ordenador, coger
        return _words(text, "ustedes", "computadora", "agarrar", "ahorita", "carro") -             _words(text, "vosotros", "podéis", "tenéis", "habéis", "ordenador", "coger", "vale")
    if family == "pt":   # Brazil: você, tela, arquivo; Portugal: ecrã, ficheiro, estás
        return _words(text, "você", "vocês", "tela", "arquivo", "time") - _words(text, "ecrã", "ficheiro", "estás", "consegues")
    if family == "en":   # British spellings against American ones
        lower = text.lower()
        return _count(r"(colour|honour|armour|centre|realis|recognis)", lower) -             _count(r"(color|honor|armor|center|realiz|recogniz)", lower)
    return _words(text, "af", "hvad", "nu", "efter") - _words(text, "av", "hva", "nå", "etter")  # nordic


def family_of(text: str) -> str:
    best = max((s := scores(text)), key=s.get)
    return "nordic" if best in ("da", "no") else best


def text_languages(game_dir: Path, game: str) -> dict[str, str]:
    """{language: text file number} for one game. Two files of one family (Spanish of Spain and of Latin America,
    say) are told apart by comparing them with each other; a lone one by its own regional words."""
    archive = Path(game_dir) / DATA_DIRS[game] / "build" / "main" / "core.psarc"
    psarc = Psarc(archive)
    try:
        texts = {number: data.decode("utf-8", "replace") for number, data in psarc.text_files().items()}
    finally:
        psarc.close()
    families: dict[str, list[str]] = {}
    for number in sorted(texts, key=int):
        families.setdefault(family_of(texts[number]), []).append(number)
    found: dict[str, str] = {}
    for family, numbers in families.items():
        if family not in REGIONS:
            found.setdefault(family, numbers[0])
            continue
        first, second = REGIONS[family]
        ranked = sorted(numbers, key=lambda number: regional(family, texts[number]), reverse=True)
        if len(ranked) >= 2:
            found.setdefault(first, ranked[0])
            found.setdefault(second, ranked[-1])
        else:
            found.setdefault(first if regional(family, texts[ranked[0]]) > 0 else second, ranked[0])
    return dict(sorted(found.items(), key=lambda item: int(item[1])))


def cached_text_languages(game_dir: Path, game: str, cache_file: Path) -> dict[str, str]:
    """text_languages, kept by the archive's size and time (the first look reads the archive: seconds)."""
    archive = Path(game_dir) / DATA_DIRS[game] / "build" / "main" / "core.psarc"
    info = archive.stat()
    key = f"{archive.resolve()}|{info.st_size}|{int(info.st_mtime)}"
    try:
        cache = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    if isinstance(cache.get(key), dict):
        return cache[key]
    found = text_languages(game_dir, game)
    cache[key] = found
    try:
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(cache_file).with_suffix(".tmp")
        temporary.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        temporary.replace(cache_file)
    except OSError:
        pass
    return found


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    game_dir = Path(sys.argv[1])
    for game in sys.argv[2:] or list(DATA_DIRS):
        print(game, json.dumps(text_languages(game_dir, game), ensure_ascii=False))


if __name__ == "__main__":
    main()
