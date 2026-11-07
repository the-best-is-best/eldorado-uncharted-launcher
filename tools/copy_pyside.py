# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Copies the part of PySide6 (Qt for Python, LGPL-3.0) the launcher uses into the package: Qt Core, Gui,
OpenGL (PySide6's QtQuick module imports it: the home screen's image provider needs QtQuick), Qml, Quick, Quick
Controls (Basic style only), Layouts, Quick Dialogs (the folder and file pickers: Windows' own dialogs through the
platform plugin, so no QtWidgets), the Windows platform plugin and its licenses. The full PySide6 Essentials wheel
is about 210 MB unpacked; the launcher needs about a third of it.

usage: copy_pyside.py <site-packages that holds PySide6 and shiboken6> <destination site-packages>
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

QT_MODULES = ("Core", "Gui", "Network", "OpenGL", "Qml", "QmlMeta", "QmlModels", "QmlWorkerScript", "Quick",
              "QuickControls2", "QuickControls2Basic", "QuickControls2BasicStyleImpl", "QuickControls2Impl",
              "QuickTemplates2", "QuickLayouts", "QuickDialogs2", "QuickDialogs2QuickImpl", "QuickDialogs2Utils")
PYTHON_MODULES = ("QtCore", "QtGui", "QtNetwork", "QtOpenGL", "QtQml", "QtQuick")
RUNTIME_DLLS = ("pyside6.abi3.dll", "pyside6qml.abi3.dll", "msvcp140*.dll", "vcruntime140*.dll", "concrt140.dll")
PLUGINS = ("platforms/qwindows.dll", "imageformats/qico.dll", "imageformats/qjpeg.dll")
# QML folders taken whole, and Controls without the styles the launcher does not use.
QML_FOLDERS = ("QtQml", "QtQuick/Layouts", "QtQuick/Templates", "QtQuick/Window", "QtQuick/Controls/Basic",
               "QtQuick/Controls/impl", "QtQuick/Dialogs")
CONTROLS_STYLES = {"FluentWinUI3", "Fusion", "Imagine", "Material", "Native", "Universal", "Windows", "designer"}


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        # "+Fusion", "+Material"...: the Dialogs' drawings for the styles the launcher does not use.
        shutil.copytree(source, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "+*"))
    else:
        shutil.copy2(source, target)


def files(folder: Path) -> list[Path]:
    """The files directly in a folder (its sub-folders are chosen one by one)."""
    return [path for path in folder.iterdir() if path.is_file()]


def main() -> None:
    site, dest = Path(sys.argv[1]), Path(sys.argv[2])
    source, target = site / "PySide6", dest / "PySide6"
    if not (source / "QtQuick.pyd").exists():
        sys.exit(f"PySide6 is not installed in {site} (pip install --target <folder> PySide6-Essentials)")
    copy(site / "shiboken6", dest / "shiboken6")
    for path in source.glob("*.py"):
        copy(path, target / path.name)
    names = [f"Qt6{module}.dll" for module in QT_MODULES] + [f"{module}.pyd" for module in PYTHON_MODULES]
    for name in names:
        copy(source / name, target / name)
    for pattern in RUNTIME_DLLS:
        for path in source.glob(pattern):
            copy(path, target / path.name)
    for plugin in PLUGINS:
        copy(source / "plugins" / plugin, target / "plugins" / plugin)
    qml = source / "qml"
    for path in files(qml) + files(qml / "QtQuick") + files(qml / "QtQuick" / "Controls"):
        copy(path, target / path.relative_to(source))
    for folder in QML_FOLDERS:
        copy(qml / folder, target / "qml" / folder)
    leftover = {path.name for path in (qml / "QtQuick" / "Controls").iterdir() if path.is_dir()}
    unknown = leftover - CONTROLS_STYLES - {"Basic", "impl"}
    if unknown:
        print(f"PySide6 has Controls folders this script does not know (left out): {sorted(unknown)}")
    # Qt's and PySide6's licenses (LGPL-3.0) go with the package.
    for info in site.glob("pyside6_essentials-*.dist-info"):
        copy(info, dest / info.name)
    for info in site.glob("shiboken6-*.dist-info"):
        copy(info, dest / info.name)
    print(f"PySide6 copied from {site}")


if __name__ == "__main__":
    main()
