# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The app-level actions QML calls (context property `app`): launcher updates, the game folder (chosen, or the
player's game .pkg unpacked) and game update, the files check, the shader cache, shortcuts, Steam, the player's
folders, reset, the first start, and closing the launcher.

Long work runs in a thread and comes back by signals; core/ does the work and raises clear errors, which become a
`message` for the player. While it runs, `busy`, `statusText` and `progress` say what it is doing (the window shows
them over everything). QML opens the pickers and questions when asked to (pickFolder, pickFile, confirm; see
qml/components/AppDialogs.qml) and answers through folderChosen, fileChosen and confirmed. `filesChanged` says the
game's files or the settings changed (the Settings screen reads them again).
"""
from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, QUrl, Signal, Slot

from core import config as cfg
from core import game_files, games, paths, report, shortcuts, steam, updater
from core.i18n import t
from ui import steam_art

# Errors core/ raises for the player; anything else is shown with its type (a bug, but never swallowed).
PLAYER_ERRORS = (updater.UpdateError, game_files.GameFilesError, steam.SteamError, shortcuts.ShortcutError, OSError)
START_CHECK_DELAY_MS = 1500


REPORT_DONE = ("{file} is on your Desktop: attach it to your report. It holds the logs and the settings, no game "
               "files and no saves.")

class AppModel(QObject):
    changed = Signal()
    message = Signal(str)
    # The game folder, the game update or the settings changed on disk (not for busy or progress steps).
    filesChanged = Signal()
    # Requests to QML: open a folder picker / a file picker / a yes-no question for `kind`.
    pickFolder = Signal(str)
    pickFile = Signal(str)
    confirm = Signal(str, str)
    # From worker threads to the window's thread (Qt queues signals across threads).
    _finished = Signal(object)
    _checked = Signal(object)  # the quiet check at start: its outcome, from its own thread
    _step = Signal(float, str)

    def __init__(self) -> None:
        super().__init__()
        had_config = paths.config_file().exists()
        config = cfg.Config.load()
        self._new_player = not had_config
        self._first_start = not config.data.get("first_start_done") and (
            not had_config or not games.is_game_dir(config.game_dir()))
        self._busy = False
        self._progress = 0.0
        self._status = ""
        self._release: updater.Release | None = None
        self._update_text = ""
        self._pending_pkg: Path | None = None
        self._pending_game_pkg: Path | None = None  # the game .pkg chosen, until its destination is chosen
        self._cancel = threading.Event()
        self._cancellable = False  # the action under way stops on cancel() (the update download)
        # Set by whoever creates the model (e.g. lambda: launcher.running): the actions that change the game's files
        # wait until the game is closed.
        self.running_check: Callable[[], bool] | None = None
        self._finished.connect(self._on_finished)
        self._checked.connect(lambda done: done())
        self._step.connect(self._on_step)
        if config.data.get("check_updates", True):
            QTimer.singleShot(START_CHECK_DELAY_MS, lambda: self._check(manual=False))
        else:
            QTimer.singleShot(START_CHECK_DELAY_MS, self._cleanup_only)

    # --- what QML reads ---------------------------------------------------------------------------------------

    @Property(bool, notify=changed)
    def updateAvailable(self) -> bool:
        return self._release is not None

    @Property(str, notify=changed)
    def updateText(self) -> str:
        return self._update_text

    @Property(float, notify=changed)
    def progress(self) -> float:
        """0..1 while a download or install runs; -1 when its length is unknown."""
        return self._progress

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def statusText(self) -> str:
        """The step of the long action under way (installing the update .pkg, checking files...); "" for the
        quiet check at start, which the window does not show."""
        return self._status

    @Property(bool, notify=changed)
    def cancellable(self) -> bool:
        """Whether cancel() stops the action under way (the update download)."""
        return self._busy and self._cancellable

    @Property(bool, notify=changed)
    def firstStart(self) -> bool:
        return self._first_start

    @Property(str, notify=changed)
    def gameDir(self) -> str:
        folder = cfg.Config.load().game_dir()
        return str(folder) if games.is_game_dir(folder) else ""

    @Property(str, notify=changed)
    def gameUpdate(self) -> str:
        return game_files.update_text(cfg.Config.load())

    @Property(str, notify=changed)
    def version(self) -> str:
        installed = updater.installed_version(paths.ROOT)
        return updater.version_text(installed) if installed else t("source tree")

    @Property(str, notify=changed)
    def pendingPkgFolder(self) -> str:
        """Where the game .pkg being installed is (a URL for the destination picker to start in), else ""."""
        pkg = self._pending_game_pkg
        return QUrl.fromLocalFile(str(pkg.parent)).toString() if pkg else ""

    # --- pickers ----------------------------------------------------------------------------------------------

    @Slot()
    def chooseGameFolder(self) -> None:
        if self._refuse_while_running():
            return
        self.pickFolder.emit("game")

    @Slot()
    def installUpdatePkg(self) -> None:
        if self._refuse_while_running() or not self._has_game_dir():
            return
        self.pickFile.emit("pkg")

    @Slot()
    def installGamePkg(self) -> None:
        """The player's own game .pkg, then the folder to unpack it into; that folder becomes the game folder."""
        if self._refuse_while_running():
            return
        self.pickFile.emit("game_pkg")

    @Slot(str, "QVariant")
    def folderChosen(self, kind: str, url: Any) -> None:
        folder = _local_path(url)
        if folder is None:
            return
        if kind == "game_destination":
            self._install_game(folder)
            return
        config = cfg.Config.load()
        try:
            if kind == "game":
                game_files.set_game_dir(config, folder)
        except game_files.GameFilesError as error:
            self.message.emit(str(error))
        self._files_changed()

    @Slot(str, "QVariant")
    def fileChosen(self, kind: str, url: Any) -> None:
        pkg = _local_path(url)
        if pkg is None:
            return
        if kind == "game_pkg":
            self._pending_game_pkg = pkg
            self.changed.emit()
            self.pickFolder.emit("game_destination")
        elif kind == "pkg":
            self._pending_pkg = pkg
            existing = game_files.existing_update(cfg.Config.load())
            if existing:
                self.confirm.emit("replace_update", t("There is an update folder already:") + f"\n{existing}\n\n" +
                                  t("Replace it with this update?"))
            else:
                self._install_pkg()

    @Slot(str)
    def confirmed(self, kind: str) -> None:
        """The player said yes to the question `kind`."""
        actions = {"replace_update": self._install_pkg, "clear_cache": self._clear_cache,
                   "reset": self._reset, "install": self._download_update, "quit": QCoreApplication.quit}
        action = actions.get(kind)
        if action is not None:
            action()

    # --- game files -------------------------------------------------------------------------------------------

    def _install_pkg(self) -> None:
        pkg, self._pending_pkg = self._pending_pkg, None
        if pkg is None:
            return
        config = cfg.Config.load()

        def work() -> str:
            update = game_files.install_update_pkg(config, pkg, log=lambda text: self._step.emit(-1.0, text))
            return t("Update installed:") + f"\n{update}\n\n" + t("The games use it from their next start.")

        self._run(t("Checking the update..."), work, self._files_changed)

    def _install_game(self, destination: Path) -> None:
        pkg, self._pending_game_pkg = self._pending_game_pkg, None
        self.changed.emit()
        if pkg is None or self._refuse_while_running():
            return
        config = cfg.Config.load()

        def work() -> str:
            game_dir = game_files.install_game_pkg(config, pkg, destination,
                                                   log=lambda text: self._step.emit(-1.0, text))
            return (t("Game installed:") + f"\n{game_dir}\n\n" +
                    t("It is the game folder now. Next, install update 1.02 with Install game update (from its .pkg)."))

        self._run(t("Checking the game package..."), work, self._files_changed)

    @Slot()
    def checkGameFiles(self) -> None:
        config = cfg.Config.load()
        if not self._has_game_dir(config):
            return
        self._run(t("Checking the game files..."), lambda: game_files.check_files(config.game_dir()).summary())

    @Slot()
    def clearShaderCache(self) -> None:
        if self._refuse_while_running():
            return
        if not game_files.SHADER_CACHE.exists():
            self.message.emit(t("There is no shader cache yet."))
            return
        self.confirm.emit("clear_cache", t("Delete the shader cache?") + "\n\n" +
                          t("Shaders are compiled again the next time you play, which brings back stutters for a "
                            "while."))

    def _clear_cache(self) -> None:
        self._run(t("Deleting the shader cache..."),
                  lambda: t("Shader cache cleared.") if game_files.clear_shader_cache() else
                  t("There is no shader cache."))

    @Slot()
    def problemReport(self) -> None:
        """Settings > LAUNCHER > Problem report: the logs and settings in one zip on the Desktop, shown in Explorer."""
        def done(target: Path) -> None:
            self.message.emit(t(REPORT_DONE, file=target.name))
            try:
                import subprocess
                subprocess.Popen(["explorer", "/select,", str(target)])
            except OSError:
                pass
        self._run(t("Making the problem report..."), report.write, done)

    @Slot(str)
    def openFolder(self, name: str) -> None:
        try:
            folder = game_files.player_folder(name)
            os.startfile(folder)  # type: ignore[attr-defined]  # Windows only, as the package
        except (game_files.GameFilesError, OSError) as error:
            self.message.emit(t("The folder could not be opened:") + f"\n{error}")

    @Slot()
    def resetSettings(self) -> None:
        if self._refuse_while_running():
            return
        self.confirm.emit("reset", t("Reset every game's settings to their defaults?") + "\n\n" +
                          t("The game folder, the game update, saves and controls are kept."))

    def _reset(self) -> None:
        try:
            game_files.reset_settings(cfg.Config.load())
        except OSError as error:
            self.message.emit(t("The settings could not be written:") + f"\n{error}")
            return
        self._files_changed(t("Settings reset: every game is on the Medium preset with the default controls."))

    # --- closing ----------------------------------------------------------------------------------------------

    @Slot()
    @Slot(bool)
    def quit(self, ask: bool = False) -> None:
        """Closes the launcher. Asks first when told to (a key press) and always while a game runs: the start
        script and its game end with the launcher."""
        if self.running_check is not None and self.running_check():
            self.confirm.emit("quit", t("The game is still running and closes with the launcher.") + "\n\n" +
                              t("Quit anyway?"))
        elif ask:
            self.confirm.emit("quit", t("Close El Dorado?"))
        else:
            QCoreApplication.quit()

    # --- shortcuts and Steam ----------------------------------------------------------------------------------

    @Slot()
    def createShortcuts(self) -> None:
        game_dir = cfg.Config.load().game_dir()

        def work() -> str:
            made = shortcuts.create_all(game_dir)
            return (t("Shortcuts created on the desktop:") + "\n" + "\n".join(link.name for link in made) +
                    "\n\n" + t("Each game's shortcut starts it directly with the launcher's settings."))

        self._run(t("Creating the shortcuts..."), work)

    @Slot()
    @Slot(bool)
    def addToSteam(self, per_game: bool = False) -> None:
        config = cfg.Config.load()
        game_dir = config.game_dir() if games.is_game_dir(config.game_dir()) else None
        self._run(t("Adding to Steam..."), lambda: _add_to_steam(per_game, game_dir))

    # --- launcher updates -------------------------------------------------------------------------------------

    @Slot()
    def checkForUpdates(self) -> None:
        self._check(manual=True)

    def _cleanup_only(self) -> None:
        threading.Thread(target=updater.cleanup, args=(paths.ROOT,), daemon=True).start()

    def _check(self, manual: bool) -> None:
        current = updater.installed_version(paths.ROOT)
        if current is None:
            if manual:
                self.message.emit(t("This copy runs from the source tree: update it with git."))
            return
        if self._busy and not manual:
            return  # the check at start gives way to whatever the player started

        def work() -> updater.Release | None:
            updater.cleanup(paths.ROOT)
            return updater.newest_release(current)

        def done(release: updater.Release | None) -> None:
            self._release = release
            if release:
                self._update_text = t("Version {version} is available.", version=release.text)
            else:
                self._update_text = t("Version {version} is the newest.", version=updater.version_text(current))
                if manual:
                    self.message.emit(self._update_text)

        if manual:
            self._run(t("Checking for updates..."), work, done)
            return

        # At start: on its own thread, apart from the player's actions (it held them back up to 15 s offline);
        # silent when offline. Its answer is shown on the window's thread.
        def quiet() -> None:
            try:
                release = work()
            except Exception:  # offline, GitHub down, a bad answer: nothing to say at start
                return
            self._checked.emit(lambda: (done(release), self.changed.emit()))

        threading.Thread(target=quiet, daemon=True).start()

    @Slot()
    def installUpdate(self) -> None:
        release = self._release
        if release is None or self._busy or self._refuse_while_running():
            return
        self.confirm.emit("install", t("Install version {version} ({size} MB download)?", version=release.text,
                                       size=f"{release.size / 1e6:.0f}") + "\n\n" +
                          t("Saves, settings and the shader cache are kept. The launcher closes, installs the update "
                            "and starts again.") + "\n\n" + t("What's new: {page}", page=release.page))

    @Slot()
    def cancel(self) -> None:
        """Stops the update download; the file downloaded so far is resumed next time."""
        if self.cancellable:
            self._cancel.set()
            self._status = t("Stopping the download...")
            self.changed.emit()

    def _download_update(self) -> None:
        release = self._release
        if release is None:
            return
        self._cancel.clear()

        def progress(done: int, total: int) -> None:
            if total:
                self._step.emit(done / total, t("Downloading the update... {percent}%",
                                                percent=f"{100 * done / total:.0f}"))
            else:
                self._step.emit(-1.0, t("Downloading the update... {size} MB", size=f"{done / 1e6:.0f}"))

        def work() -> Path:
            archive = updater.download(release, paths.ROOT, progress, self._cancel.is_set)
            self._step.emit(-1.0, t("Unpacking the update..."))
            return updater.stage(archive, paths.ROOT, release.version)

        def done(staged: Path) -> None:
            self._update_text = t("Installing the update... the launcher starts again in a moment.")
            try:
                updater.hand_off(paths.ROOT, staged)
            except updater.UpdateError as error:
                self.message.emit(str(error))
                return
            # The installer waits for this process to end.
            QCoreApplication.quit()

        self._run(t("Downloading the update..."), work, done, cancellable=True)

    # --- first start ------------------------------------------------------------------------------------------

    @Slot()
    @Slot(bool)
    def finishFirstStart(self, recommended_applied: bool = False) -> None:
        """The first start page is done. Without the settings model applying Recommended itself, every game takes
        it as soon as the GPU is known (recommended_pending, as the released launcher)."""
        config = cfg.Config.load()
        config.data["first_start_done"] = True
        if self._new_player and not recommended_applied:
            config.data["recommended_pending"] = True
        try:
            config.save()
        except OSError as error:
            self.message.emit(t("The settings could not be written:") + f"\n{error}")
        self._first_start = False
        self.changed.emit()

    # --- worker threads ---------------------------------------------------------------------------------------

    def _run(self, status: str, work: Callable[[], Any], done: Callable[[Any], None] | None = None,
             quiet: bool = False, cancellable: bool = False) -> None:
        """work() in a thread; then done(result) in the window's thread, or the result (a str) as a message. An
        error is a message unless quiet (the check at start says nothing when offline). cancellable: work() stops
        when cancel() is pressed (it reads self._cancel)."""
        if self._busy:
            self.message.emit(t("Wait for the current action to finish."))
            return
        self._busy = True
        self._cancellable = cancellable
        self._progress = -1.0
        self._status = status
        self.changed.emit()

        def thread() -> None:
            try:
                outcome: tuple[Any, Any] = (work(), None)
            except updater.Cancelled:
                outcome = (None, "")  # the player's own doing: nothing to say
            except PLAYER_ERRORS as error:
                outcome = (None, _player_text(error))
            except Exception as error:  # a bug: shown, never swallowed
                outcome = (None, f"{type(error).__name__}: {error}")
            self._finished.emit((done, quiet, outcome))

        threading.Thread(target=thread, daemon=True).start()

    def _on_finished(self, packet: tuple[Callable[[Any], None] | None, bool, tuple[Any, Any]]) -> None:
        done, quiet, (result, error) = packet
        self._busy = False
        self._cancellable = False
        self._progress = 0.0
        self._status = ""
        if error is not None:
            if error and not quiet:
                self.message.emit(error)
        elif done is not None:
            done(result)
        elif isinstance(result, str) and result:
            self.message.emit(result)
        self.changed.emit()

    def _files_changed(self, text: str = "") -> None:
        """The game's files or the settings changed on disk: the message about it (if any), then everyone reads
        again."""
        if text:
            self.message.emit(text)
        self.filesChanged.emit()
        self.changed.emit()

    def _on_step(self, fraction: float, text: str) -> None:
        if fraction >= 0 and abs(fraction - self._progress) < 0.01 and fraction < 1:
            return  # a redraw per percent is enough
        self._progress = fraction
        self._status = text
        self.changed.emit()

    # --- checks -----------------------------------------------------------------------------------------------

    def _refuse_while_running(self) -> bool:
        if self.running_check is not None and self.running_check():
            self.message.emit(t("Close the game first."))
            return True
        return False

    def _has_game_dir(self, config: cfg.Config | None = None) -> bool:
        config = config or cfg.Config.load()
        if games.is_game_dir(config.game_dir()):
            return True
        self.message.emit(t("Choose the game folder first."))
        return False


def _local_path(url: Any) -> Path | None:
    """A picker's answer (a QUrl or its text) as a local path."""
    text = (url if isinstance(url, QUrl) else QUrl(str(url))).toLocalFile()
    return Path(text) if text else None


def _player_text(error: Exception) -> str:
    if isinstance(error, steam.SteamError):
        if error.kind == "no_steam":
            return t("Steam was not found on this PC (no Steam account folder in Steam's userdata). Install Steam "
                     "and sign in once, then try again.")
        return t("Steam's list of non-Steam games could not be read, so it was left as it is:") + f"\n{error.detail}"
    return str(error) or type(error).__name__


def _add_to_steam(per_game: bool, game_dir: Path | None) -> str:
    # Steam saves its own list of games when it closes, so an open Steam is asked to exit first (as its own Exit
    # does) and is opened again afterwards.
    restart = None
    if steam.steam_running():
        exe = steam.steam_exe()
        if exe is None or not steam.shut_down_steam(exe):
            return (t("Steam is open. Steam saves its own list of games when it closes, so a game added now would be "
                      "lost.") + "\n\n" + t("Close Steam completely (Steam menu -> Exit), then try again."))
        restart = exe
    try:
        text = _write_to_steam(per_game, game_dir)
    finally:
        if restart is not None:
            steam.start_steam(restart)
    if restart is not None:
        return text + "\n\n" + (t("Steam was closed for this and opened again: they are in your Library.") if per_game
                                else t("Steam was closed for this and opened again: it is in your Library."))
    return text + "\n\n" + (t("Start Steam again: they are in your Library.") if per_game else
                             t("Start Steam again: it is in your Library."))


def _write_to_steam(per_game: bool, game_dir: Path | None) -> str:
    game_list = [(game.key, game.name) for game in games.GAMES] if per_game else None
    # Each game's own emblem (its trophy pack's picture, from the player's files) for its library pictures.
    # Each game's icon in Steam's list and on its pictures: El Dorado's own drawing (launcher/assets/loading).
    icons = {game.key: path for game in games.GAMES
             if (path := paths.LAUNCHER_DIR / "assets" / "loading" / f"{game.key}.png").is_file()} if per_game else None
    # Their library pictures in El Dorado's own look (the drawn map, that icon, the title in the launcher's
    # fonts): nothing of the game's.
    art = {game.key: steam_art.make(game.key, shortcuts.ICON_DIR / "steam" / game.key)
           for game in games.GAMES} if per_game else None
    wanted = steam.targets(paths.ROOT, shortcuts.STARTER, Path(sys.executable), shortcuts.ENTRY_SCRIPT, game_list,
                           None, icons, art)
    names = (steam.COLLECTION_NAME,) + tuple(game.name for game in games.GAMES)
    results = steam.add_to_steam(wanted, str(shortcuts.APP_ICON), game_dir, all_names=names)
    lines = []
    for result in results:
        who = f"{result.persona} ({result.folder.name})" if result.persona else \
            t("Steam account {account}", account=result.folder.name)
        changes = [text for count, text in ((result.added, t("{count} added", count=result.added)),
                                            (result.updated, t("{count} updated", count=result.updated)),
                                            (result.removed, t("{count} replaced", count=result.removed))) if count]
        lines.append(f"{who}: {', '.join(changes)}")
    pictures = (t("Library pictures come from your game files.") if game_dir
                else t("No library pictures: choose the game folder first, then add again."))
    backups = [str(result.backup) for result in results if result.backup]
    added = t("Added the three games to Steam:") if per_game else \
        t("Added {name} to Steam:", name=f'"{steam.COLLECTION_NAME}"')
    # The three games' pictures are El Dorado's own (steam_art): no game folder needed, nothing to say.
    text = added + "\n" + "\n".join(lines) + ("" if per_game else f"\n\n{pictures}")
    if backups:
        text += "\n\n" + t("The previous list was saved as:") + "\n" + "\n".join(backups)
    return text
