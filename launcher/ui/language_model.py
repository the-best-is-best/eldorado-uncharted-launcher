# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The launcher's language for QML (context property `i18n`): qsTr() in QML and core.i18n.t() in Python read the
same texts (a QTranslator over core.i18n). Changing the language saves it, re-reads every qsTr() and asks the
models to hand their texts again; Arabic mirrors the window (right to left)."""
from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Property, QObject, QTranslator, Signal, Slot

from core import config as cfg
from core import i18n


class Translator(QTranslator):
    """Every qsTr() of the QML through core.i18n (no .qm files to build)."""

    def translate(self, context: str, source: str, disambiguation: str | None = None, n: int = -1) -> str:
        return i18n.t(source) if source else source

    def isEmpty(self) -> bool:
        return False


class LanguageModel(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._retranslate: Callable[[], None] = lambda: None
        self._models: list[QObject] = []

    def attach(self, retranslate: Callable[[], None], models: Iterable[QObject]) -> None:
        """What a language change re-reads: the QML engine's qsTr() and the models' own texts."""
        self._retranslate = retranslate
        self._models = [model for model in models if model is not self]

    @Property(str, notify=changed)
    def language(self) -> str:
        return i18n.language()

    @Property(bool, notify=changed)
    def rtl(self) -> bool:
        return i18n.is_rtl()

    @Property(bool, notify=changed)
    def unspaced(self) -> bool:
        """The language's script takes no letter spacing (Theme.tracking)."""
        return i18n.language() in i18n.UNSPACED

    @Property("QVariantList", constant=True)
    def languages(self) -> list[dict[str, str]]:
        return [{"value": code, "label": name} for code, name in i18n.LANGUAGES]

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        if code == i18n.language():
            return
        i18n.set_language(code)
        config = cfg.Config.load()
        config.data[i18n.SETTING] = i18n.language()
        config.save()
        self._retranslate()
        for model in self._models:
            signal = getattr(model, "changed", None)
            if signal is not None:
                signal.emit()
        self.changed.emit()
