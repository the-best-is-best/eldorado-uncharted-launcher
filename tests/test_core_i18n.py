# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import i18n  # noqa: E402


@pytest.fixture(autouse=True)
def english_after() -> None:
    yield
    i18n.set_language("en")


def write_language(folder: Path, texts: dict[str, str]) -> Path:
    (folder / "ar.json").write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    return folder


def test_english_without_a_file(tmp_path: Path) -> None:
    i18n.set_language("ar", tmp_path)  # no ar.json there
    assert i18n.language() == "en"
    assert i18n.t("Close the game first.") == "Close the game first."


def test_translates_with_a_language_file(tmp_path: Path) -> None:
    i18n.set_language("ar", write_language(tmp_path, {"Close the game first.": "أغلق اللعبة أولاً."}))
    assert i18n.language() == "ar"
    assert i18n.is_rtl()
    assert i18n.t("Close the game first.") == "أغلق اللعبة أولاً."
    assert i18n.t("A text without a translation.") == "A text without a translation."


def test_fills_fields(tmp_path: Path) -> None:
    assert i18n.t("Saved for {where}.", where="all games") == "Saved for all games."
    i18n.set_language("ar", write_language(tmp_path, {"Saved for {where}.": "حُفظ لـ {where}."}))
    assert i18n.t("Saved for {where}.", where="Uncharted 2") == "حُفظ لـ Uncharted 2."


def test_broken_field_falls_back_to_english(tmp_path: Path) -> None:
    i18n.set_language("ar", write_language(tmp_path, {"Saved for {where}.": "حُفظ لـ {place}."}))
    assert i18n.t("Saved for {where}.", where="all games") == "Saved for all games."


def test_unknown_language_is_english(tmp_path: Path) -> None:
    i18n.set_language("ar", write_language(tmp_path, {"Today": "اليوم"}))
    i18n.set_language("xx", tmp_path)
    assert i18n.language() == "en"
    assert i18n.t("Today") == "Today"


def test_a_right_to_left_line_starting_with_a_latin_word_reads_from_the_right(tmp_path) -> None:
    import json

    from core import i18n

    (tmp_path / "ar.json").write_text(json.dumps({"El Dorado on the desktop.": "El Dorado على سطح المكتب.",
                                                  "A\nB": "أ\nب"}, ensure_ascii=False), encoding="utf-8")
    try:
        i18n.set_language("ar", folder=tmp_path)
        assert i18n.t("El Dorado on the desktop.") == "\u200fEl Dorado على سطح المكتب."
        assert i18n.t("A\nB") == "\u0623\n\u0628"  # an Arabic first letter: right to left already
        assert i18n.t("Untranslated {x}", x="عربي") == "Untranslated عربي"  # game texts in a field: untouched
    finally:
        i18n.set_language("en")
