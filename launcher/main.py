# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""El Dorado Launcher: starts the Qt app and loads the QML window. One launcher runs at a time; a second start
brings the open one to the front.

usage: main.py [--measure]   --measure prints the cold start time (process start to first frame) and quits
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import paths  # noqa: E402
from ui import windows  # noqa: E402

UI_DIR = Path(__file__).resolve().parent / "ui"
WINDOW_TITLE = paths.APP_NAME


def use_own_qt() -> None:
    """Qt from the package's own Python only: a PySide6 in the player's user site-packages, or Qt plugin paths set
    by other programs, made Qt fail with "no Qt platform plugin could be initialized"."""
    import site

    user_site = site.getusersitepackages()
    sys.path[:] = [entry for entry in sys.path if not entry.startswith(user_site)]
    for name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH", "QML_IMPORT_PATH"):
        os.environ.pop(name, None)
    import PySide6

    plugins = Path(PySide6.__file__).resolve().parent / "plugins"
    os.environ["QT_PLUGIN_PATH"] = str(plugins)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins / "platforms")


def direct_game() -> str | None:
    """--play u1|u2|u3 (the games' desktop and Steam shortcuts): that game starts without the launcher's window."""
    args = sys.argv[1:]
    if "--play" in args:
        index = args.index("--play") + 1
        key = args[index] if index < len(args) else ""
        if key in ("u1", "u2", "u3"):
            return key
    return None


def main() -> int:
    measure = "--measure" in sys.argv[1:]
    instance = windows.SingleInstance(paths.APP_ID)
    # A shortcut's --play start runs beside an open launcher window (each its own game).
    if not instance.first and not measure and not direct_game():
        windows.bring_to_front(WINDOW_TITLE)
        return 0
    windows.set_app_id(paths.APP_ID)
    # The Basic style: drawn by Qt Quick alone (the trimmed package ships no other style).
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    use_own_qt()
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine

    # Exact scale factors (125%, 150%) instead of rounding to whole steps: sharp text at every Windows setting.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QGuiApplication(sys.argv)
    app.setApplicationName(paths.APP_NAME)
    app.setWindowIcon(QIcon(str(UI_DIR / "assets" / "eldorado.ico")))

    # The launcher's language (Settings, else Windows' own): Python's t() and QML's qsTr() read the same texts.
    from core import config as cfg
    from core import i18n
    from ui.language_model import LanguageModel, Translator

    i18n.set_language(i18n.chosen(cfg.Config.load().data.get(i18n.SETTING)))
    translator = Translator(app)
    app.installTranslator(translator)

    from ui.bridge import Launcher

    launcher = Launcher()

    def open_window() -> QQmlApplicationEngine | None:
        """The launcher's window and its models; None when the QML does not load."""
        from ui.app_model import AppModel
        from ui.background import BackgroundProvider
        from ui.gallery_model import GalleryModel
        from ui.gamepad import Gamepad
        from ui.saves_model import SavesModel
        from ui.settings_model import SettingsModel
        from ui.trophies_model import TrophiesModel

        app_model = AppModel()
        # Folder, .pkg, shader cache, reset and update actions wait until the game is closed.
        app_model.running_check = lambda: launcher.running
        # What QML sees, by name. Kept in a dict so the objects live as long as the window.
        models = {"launcher": launcher, "app": app_model, "gamepad": Gamepad(), "saves": SavesModel(),
                  "trophies": TrophiesModel(), "gallery": GalleryModel(), "settings": SettingsModel()}
        from ui.profile_model import ProfileModel

        models["profiles"] = ProfileModel()
        language = LanguageModel()
        models["i18n"] = language
        engine = QQmlApplicationEngine()
        language.attach(engine.retranslate, models.values())
        # Another game folder or update (chosen, installed from a .pkg, a reset): every screen reads the files again:
        # the game's version and its saves, the Arabic translation, the trophy packs.
        for reread in (launcher.refresh, models["saves"].refresh, models["trophies"].reload, models["settings"].refresh):
            app_model.filesChanged.connect(reread)
            models["profiles"].switched.connect(reread)  # another player: other saves
        models["settings"].languageWanted.connect(language.setLanguage)
        engine.addImageProvider("background", BackgroundProvider(launcher.picture))
        for name, model in models.items():
            engine.rootContext().setContextProperty(name, model)
        engine.setInitialProperties({"title": WINDOW_TITLE})
        engine.load(QUrl.fromLocalFile(str(UI_DIR / "qml" / "Main.qml")))
        engine.models = models  # the models live as long as the window (QML holds no Python reference)
        return engine if engine.rootObjects() else None

    play = direct_game()
    if play:
        # No window, so none of its models (their first look at the game's files would run beside the start):
        # the launcher only relays the start script and ends with it. A crash or freeze opens the window with the
        # crash screen (PLAY AGAIN, PROBLEM REPORT); the launcher then ends when a game ends normally.
        kept: list = []

        def crashed(reason: str) -> None:
            engine = open_window()
            if engine is None:
                app.exit(1)
                return
            kept.append(engine)
            launcher.crashed.emit(reason)

        launcher.directCrashed.connect(crashed)
        launcher.play_direct(play)
        return app.exec() if launcher.running else 1

    engine = open_window()
    if engine is None:
        return 1
    if measure:
        window = engine.rootObjects()[0]

        def first_frame() -> None:
            print(f"cold start {windows.process_age():.2f} s", flush=True)
            app.quit()

        window.frameSwapped.connect(first_frame)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
