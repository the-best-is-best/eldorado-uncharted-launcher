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
from core import game_files, games, paths, shortcuts, steam, updater

# Errors core/ raises for the player; anything else is shown with its type (a bug, but never swallowed).
PLAYER_ERRORS = (updater.UpdateError, game_files.GameFilesError, steam.SteamError, shortcuts.ShortcutError, OSError)
START_CHECK_DELAY_MS = 1500


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
        return updater.version_text(installed) if installed else "source tree"

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
    def chooseUpdateFolder(self) -> None:
        if self._refuse_while_running() or not self._has_game_dir():
            return
        self.pickFolder.emit("update")

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
            elif kind == "update":
                update = game_files.set_update_folder(config, folder)
                self.message.emit(f"Game update {game_files.app_version(update) or '?'} is used from now on:\n"
                                  f"{update}")
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
                self.confirm.emit("replace_update", f"There is an update folder already:\n{existing}\n\n"
                                                    "Replace it with this update?")
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
            return f"Update installed:\n{update}\n\nThe games use it from their next start."

        self._run("Checking the update...", work, self._files_changed)

    def _install_game(self, destination: Path) -> None:
        pkg, self._pending_game_pkg = self._pending_game_pkg, None
        self.changed.emit()
        if pkg is None or self._refuse_while_running():
            return
        config = cfg.Config.load()

        def work() -> str:
            game_dir = game_files.install_game_pkg(config, pkg, destination,
                                                   log=lambda text: self._step.emit(-1.0, text))
            return (f"Game installed:\n{game_dir}\n\nIt is the game folder now. Next, install update 1.02 with "
                    "Install game update (from its .pkg).")

        self._run("Checking the game package...", work, self._files_changed)

    @Slot()
    def checkGameFiles(self) -> None:
        config = cfg.Config.load()
        if not self._has_game_dir(config):
            return
        self._run("Checking the game files...", lambda: game_files.check_files(config.game_dir()).summary())

    @Slot()
    def clearShaderCache(self) -> None:
        if self._refuse_while_running():
            return
        if not game_files.SHADER_CACHE.exists():
            self.message.emit("There is no shader cache yet.")
            return
        self.confirm.emit("clear_cache", "Delete the shader cache?\n\nShaders are compiled again the next time you "
                                         "play, which brings back stutters for a while.")

    def _clear_cache(self) -> None:
        self._run("Deleting the shader cache...",
                  lambda: "Shader cache cleared." if game_files.clear_shader_cache() else "There is no shader cache.")

    @Slot(str)
    def openFolder(self, name: str) -> None:
        try:
            folder = game_files.player_folder(name)
            os.startfile(folder)  # type: ignore[attr-defined]  # Windows only, as the package
        except (game_files.GameFilesError, OSError) as error:
            self.message.emit(f"The folder could not be opened:\n{error}")

    @Slot()
    def resetSettings(self) -> None:
        if self._refuse_while_running():
            return
        self.confirm.emit("reset", "Reset every game's settings to their defaults?\n\nThe game folder, the game "
                                   "update, saves and controls are kept.")

    def _reset(self) -> None:
        try:
            game_files.reset_settings(cfg.Config.load())
        except OSError as error:
            self.message.emit(f"The settings could not be written:\n{error}")
            return
        self._files_changed("Settings reset: every game is on the Medium preset with the default controls.")

    # --- closing ----------------------------------------------------------------------------------------------

    @Slot()
    @Slot(bool)
    def quit(self, ask: bool = False) -> None:
        """Closes the launcher. Asks first when told to (a key press) and always while a game runs: the start
        script and its game end with the launcher."""
        if self.running_check is not None and self.running_check():
            self.confirm.emit("quit", "The game is still running and closes with the launcher.\n\nQuit anyway?")
        elif ask:
            self.confirm.emit("quit", "Close El Dorado?")
        else:
            QCoreApplication.quit()

    # --- shortcuts and Steam ----------------------------------------------------------------------------------

    @Slot()
    def createShortcuts(self) -> None:
        game_dir = cfg.Config.load().game_dir()

        def work() -> str:
            made = shortcuts.create_all(game_dir)
            return ("Shortcuts created on the desktop:\n" + "\n".join(link.name for link in made) +
                    "\n\nEach game's shortcut starts it directly with the launcher's settings.")

        self._run("Creating the shortcuts...", work)

    @Slot()
    @Slot(bool)
    def addToSteam(self, per_game: bool = False) -> None:
        config = cfg.Config.load()
        game_dir = config.game_dir() if games.is_game_dir(config.game_dir()) else None
        self._run("Adding to Steam...", lambda: _add_to_steam(per_game, game_dir))

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
                self.message.emit("This copy runs from the source tree: update it with git.")
            return
        if self._busy and not manual:
            return  # the check at start gives way to whatever the player started

        def work() -> updater.Release | None:
            updater.cleanup(paths.ROOT)
            return updater.newest_release(current)

        def done(release: updater.Release | None) -> None:
            self._release = release
            if release:
                self._update_text = f"Version {release.text} is available."
            else:
                self._update_text = f"Version {updater.version_text(current)} is the newest."
                if manual:
                    self.message.emit(self._update_text)

        self._run("Checking for updates..." if manual else "", work, done, quiet=not manual)

    @Slot()
    def installUpdate(self) -> None:
        release = self._release
        if release is None or self._busy or self._refuse_while_running():
            return
        self.confirm.emit("install", f"Install version {release.text} ({release.size / 1e6:.0f} MB download)?\n\n"
                                     "Saves, settings and the shader cache are kept. The launcher closes, installs "
                                     f"the update and starts again.\n\nWhat's new: {release.page}")

    @Slot()
    def cancel(self) -> None:
        """Stops the update download; the file downloaded so far is resumed next time."""
        if self.cancellable:
            self._cancel.set()
            self._status = "Stopping the download..."
            self.changed.emit()

    def _download_update(self) -> None:
        release = self._release
        if release is None:
            return
        self._cancel.clear()

        def progress(done: int, total: int) -> None:
            if total:
                self._step.emit(done / total, f"Downloading the update... {100 * done / total:.0f}%")
            else:
                self._step.emit(-1.0, f"Downloading the update... {done / 1e6:.0f} MB")

        def work() -> Path:
            archive = updater.download(release, paths.ROOT, progress, self._cancel.is_set)
            self._step.emit(-1.0, "Unpacking the update...")
            return updater.stage(archive, paths.ROOT, release.version)

        def done(staged: Path) -> None:
            self._update_text = "Installing the update... the launcher starts again in a moment."
            try:
                updater.hand_off(paths.ROOT, staged)
            except updater.UpdateError as error:
                self.message.emit(str(error))
                return
            # The installer waits for this process to end.
            QCoreApplication.quit()

        self._run("Downloading the update...", work, done, cancellable=True)

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
            self.message.emit(f"The settings could not be written:\n{error}")
        self._first_start = False
        self.changed.emit()

    # --- worker threads ---------------------------------------------------------------------------------------

    def _run(self, status: str, work: Callable[[], Any], done: Callable[[Any], None] | None = None,
             quiet: bool = False, cancellable: bool = False) -> None:
        """work() in a thread; then done(result) in the window's thread, or the result (a str) as a message. An
        error is a message unless quiet (the check at start says nothing when offline). cancellable: work() stops
        when cancel() is pressed (it reads self._cancel)."""
        if self._busy:
            self.message.emit("Wait for the current action to finish.")
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
            self.message.emit("Close the game first.")
            return True
        return False

    def _has_game_dir(self, config: cfg.Config | None = None) -> bool:
        config = config or cfg.Config.load()
        if games.is_game_dir(config.game_dir()):
            return True
        self.message.emit("Choose the game folder first.")
        return False


def _local_path(url: Any) -> Path | None:
    """A picker's answer (a QUrl or its text) as a local path."""
    text = (url if isinstance(url, QUrl) else QUrl(str(url))).toLocalFile()
    return Path(text) if text else None


def _player_text(error: Exception) -> str:
    if isinstance(error, steam.SteamError):
        if error.kind == "no_steam":
            return ("Steam was not found on this PC (no Steam account folder in Steam's userdata). Install Steam and "
                    "sign in once, then try again.")
        return f"Steam's list of non-Steam games could not be read, so it was left as it is:\n{error.detail}"
    return str(error) or type(error).__name__


def _add_to_steam(per_game: bool, game_dir: Path | None) -> str:
    if steam.steam_running():
        return ("Steam is open. Steam saves its own list of games when it closes, so a game added now would be lost."
                "\n\nClose Steam completely (Steam menu -> Exit), then try again.")
    game_list = [(game.key, game.name) for game in games.GAMES] if per_game else None
    wanted = steam.targets(paths.ROOT, shortcuts.STARTER, Path(sys.executable), shortcuts.ENTRY_SCRIPT, game_list)
    names = (steam.COLLECTION_NAME,) + tuple(game.name for game in games.GAMES)
    results = steam.add_to_steam(wanted, str(shortcuts.APP_ICON), game_dir, all_names=names)
    lines = []
    for result in results:
        who = f"{result.persona} ({result.folder.name})" if result.persona else f"Steam account {result.folder.name}"
        changes = [f"{count} {word}" for count, word in ((result.added, "added"), (result.updated, "updated"),
                                                        (result.removed, "replaced")) if count]
        lines.append(f"{who}: {', '.join(changes)}")
    added = "the three games" if per_game else f'"{steam.COLLECTION_NAME}"'
    pictures = ("Library pictures come from your game files." if game_dir
                else "No library pictures: choose the game folder first, then add again.")
    backups = [str(result.backup) for result in results if result.backup]
    text = f"Added {added} to Steam:\n" + "\n".join(lines) + f"\n\n{pictures}"
    if backups:
        text += "\n\nThe previous list was saved as:\n" + "\n".join(backups)
    return text + "\n\nStart Steam again: " + ("they are" if per_game else "it is") + " in your Library."
