# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Every text of the launcher has its translation in every language the launcher offers, with the same {fields}."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("i18n_texts", ROOT / "tools" / "i18n_texts.py")
i18n_texts = importlib.util.module_from_spec(spec)
sys.modules["i18n_texts"] = i18n_texts
spec.loader.exec_module(i18n_texts)
sys.path.insert(0, str(ROOT / "launcher"))

from core import i18n  # noqa: E402

TRANSLATED = [code for code, _ in i18n.LANGUAGES if code != "en"]


@pytest.mark.parametrize("code", TRANSLATED)
def test_every_text_has_a_translation(code: str) -> None:
    missing, broken = i18n_texts.check(code)
    assert not missing, f"{code}: {len(missing)} texts without a translation: {missing[:20]}"
    assert not broken, f"{code}: translations with other fields: {broken[:20]}"


def test_windows_languages_map_to_the_launchers() -> None:
    assert i18n._windows_code(0x0401) == "ar"      # Arabic (Saudi Arabia)
    assert i18n._windows_code(0x0C01) == "ar"      # Arabic (Egypt)
    assert i18n._windows_code(0x0416) == "pt-BR"
    assert i18n._windows_code(0x0816) == "pt"
    assert i18n._windows_code(0x080A) == "es-419"  # Spanish (Mexico)
    assert i18n._windows_code(0x0C0A) == "es"
    assert i18n._windows_code(0x0404) == "zh-Hant"
    assert i18n._windows_code(0x0804) == "en"      # Simplified Chinese: not offered
    assert i18n._windows_code(0x0409) == "en"
