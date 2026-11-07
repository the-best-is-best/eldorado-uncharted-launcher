# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""What the QML window sees: the games, the chosen one, where the player left off (its latest save), the
expedition log (the latest saves of all three), the background picture's address, PLAY/STOP and the game's state.
It calls core/ and turns its errors into a message for the player; QML only draws."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, Signal, Slot

from core import art
from core import config as cfg
from core import game_files, games, launch, paths, saves, stats
from core.i18n import t
from ui import windows
from ui.saves_model import picture_url, shown

# The start script's lines worth showing under PLAY while the game prepares (the rest is for the log).
STATUS_PREFIXES = ("Prepar", "Shader", "Starting", "Linking", "Patching")
LOG_ROWS = 5           # the expedition log's length
NO_SAVE = "No save yet. The expedition starts here."
NO_WINDOW_NOTE = "The log is analysis\\uncharted-user\\launcher-last-run.log."
LEFT_TO_RIGHT_MARK = "‎"


def as_stored(text: str) -> str:
    """Arabic save text as the game stored it (presentation forms, already in display order), on one line that
    starts at the left: the Saves screen's left-to-right override, with a left-to-right mark first so the line's
    direction is left to right too (else Qt lays the line out right to left and swaps its parts)."""
    if not saves.is_presentation_text(text):
        return text
    return LEFT_TO_RIGHT_MARK + shown(text.replace("\n", "   "))


def backwards(text: str) -> bool:
    """Whether a line shown as stored runs from the sentence's end to its start (display order of a right-to-left
    text): QML then cuts it at the left, so the chapter's name survives and the "N% complete" tail goes."""
    return saves.is_presentation_text(text)


class Launcher(QObject):
    changed = Signal()
    message = Signal(str)
    # From the start script's reader thread to the window's thread (Qt queues signals across threads).
    _line = Signal(str)
    _ended = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._config = cfg.Config.load()
        self._stats = stats.load()
        self._selected = self._config.selected
        self._session: launch.Session | None = None
        self._status = ""
        self._game_window = False
        self._switching = False      # the Collection menu starts another game: no window for a while
        self._stopping = False       # STOP pressed: the exit code it causes is not an error
        self._started = 0.0
        # Started with --play: no window, the launcher ends with the game.
        self._direct = False
        self._saves: list[saves.Save] = []                  # every game's story saves, newest first
        self._pictures: dict[str, art.Picture] = {}         # what stands behind each game
        self._line.connect(self._on_line)
        self._ended.connect(self._on_ended)
        # While a game runs: twice a second, is its window up (hide the launcher) or has it ended (come back).
        self._watch = QTimer(self)
        self._watch.setInterval(500)
        self._watch.timeout.connect(self._check_game_window)
        self._load_saves()

    # --- what QML reads ---------------------------------------------------------------------------------------

    @Property("QVariantList", notify=changed)
    def games(self) -> list[dict]:
        rows = []
        for game in games.GAMES:
            played = self._stats.get(game.key, stats.Stats())
            rows.append({"key": game.key, "number": game.number, "title": game.title, "name": game.name,
                         "place": t(game.place), "playTime": played.play_time(), "lastPlayed": played.last_played(),
                         "fps": round(played.fps), "hasSave": saves.latest(self._saves, game.key) is not None})
        return rows

    @Property(int, notify=changed)
    def selectedIndex(self) -> int:
        return games.KEYS.index(self._selected)

    @Property(bool, notify=changed)
    def running(self) -> bool:
        return self._session is not None

    @Property(bool, notify=changed)
    def loading(self) -> bool:
        """From PLAY until the game's window is up: the home screen shows the loading layer."""
        return self._session is not None and not self._game_window

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(bool, constant=True)
    def direct(self) -> bool:
        return self._direct

    @Property(bool, notify=changed)
    def gameWindowOpen(self) -> bool:
        return self._game_window

    @Property(str, notify=changed)
    def continueTitle(self) -> str:
        """The selected game's latest save, as the Saves screen shows it; "" without a save."""
        latest = saves.latest(self._saves, self._selected)
        return as_stored(latest.chapter) if latest else ""

    @Property(str, notify=changed)
    def continueText(self) -> str:
        """The latest save's detail (play time, treasures) and when it was made, or that there is none."""
        latest = saves.latest(self._saves, self._selected)
        if latest is None:
            return t(NO_SAVE)
        stored = "   ·   ".join(line for line in latest.detail.split("\n") if line.strip())
        when = saves.when_text(saves.saved_at(latest))
        # Only the game's own text is shown as stored; the launcher's "today 12:50" is a line of its own (its own
        # direction, Arabic included), so a narrow window never cuts it off.
        return "\n".join(part for part in (as_stored(stored), when) if part)

    @Property(bool, notify=changed)
    def continueBackwards(self) -> bool:
        """The Continue lines run from their sentence's end to its start (Arabic shown as stored)."""
        latest = saves.latest(self._saves, self._selected)
        return backwards(latest.chapter) if latest else False

    @Property("QVariantList", notify=changed)
    def logRows(self) -> list[dict]:
        """The expedition log: the latest saves of all three games, newest first. A picture's address carries the
        file's version: a slot the game wrote again shows its new picture, not Qt's cached one."""
        rows = []
        for save in saves.recent(self._saves, LOG_ROWS):
            game = games.by_key(save.game)
            rows.append({"game": game.key, "gameName": game.name, "number": game.number,
                         "title": as_stored(save.chapter), "backwards": backwards(save.chapter),
                         "when": saves.when_text(saves.saved_at(save)), "picture": picture_url(save.picture)})
        return rows

    @Property(str, notify=changed)
    def backgroundSource(self) -> str:
        """The selected game's background (ui/background.py draws it); the address changes with the picture."""
        return f"image://background/{self._selected}?{self.picture(self._selected).version}"

    def picture(self, key: str) -> art.Picture:
        """For ui/background.py, from Qt's image thread: what stands behind a game, as last read."""
        return self._pictures.get(key, art.NOTHING)

    # --- what QML calls ---------------------------------------------------------------------------------------

    @Slot(int)
    def select(self, index: int) -> None:
        """The chosen game, kept in launcher.json ("game") so the next start, the Settings screen and the game's
        shortcuts begin with it."""
        if self._session is not None or not 0 <= index < len(games.GAMES):
            return
        self._selected = games.GAMES[index].key
        config = cfg.Config.load()  # as the file is now: the Settings screen writes it too
        if config.selected != self._selected:
            config.selected = self._selected
            try:
                config.save()
            except OSError as error:
                self.message.emit(t("The chosen game could not be saved:") + f"\n{error}")
        self._config = config
        self.changed.emit()

    @Slot(str)
    def selectGame(self, key: str) -> None:
        if key in games.KEYS:
            self.select(games.KEYS.index(key))

    @Slot()
    def refresh(self) -> None:
        """Reads the saves, the play stats and the settings again (after the Saves or Settings screen, and when
        the game ends)."""
        self._config = cfg.Config.load()
        self._stats = stats.load()
        self._load_saves()
        self.changed.emit()

    @Slot()
    def play(self) -> None:
        if self._session is not None:
            return
        self._config = cfg.Config.load()  # the released launcher may have changed the settings meanwhile
        game = games.by_key(self._selected)
        try:
            self._session = launch.Session(self._config, game, self._line.emit, self._ended.emit)
        except launch.LaunchError as error:
            self.message.emit(str(error))
            return
        self._started = time.time()
        self._stopping = False
        self._switching = False
        self._status = t("Starting {game}...", game=game.name)
        self._watch.start()
        self.changed.emit()

    def play_direct(self, key: str) -> None:
        """--play u1|u2|u3 (desktop and Steam shortcuts): the game starts at once with the saved settings."""
        self._direct = True
        self._selected = games.by_key(key).key
        self.play()
        if self._session is None:
            QCoreApplication.exit(1)

    @Slot()
    def stop(self) -> None:
        if self._session is not None:
            self._stopping = True
            self._status = t("Stopping...")
            self.changed.emit()
            self._session.stop()

    # --- the saves ----------------------------------------------------------------------------------------------

    def _load_saves(self) -> None:
        profiles = {key: str(self._config.game(key).get("save_profile") or "1") for key in games.KEYS}
        try:
            self._saves = saves.playable(saves.list_saves(paths.USER_DIR, saves.SAVES, profiles),
                                         game_files.version_in_use(self._config))
        except OSError as error:
            self._saves = []
            self._status = t("The saves could not be read: {error}", error=error)
        game_dir = self._config.game_dir()
        # A new dict each time: the image thread reads the old one or the new one, never a half-made one.
        self._pictures = {game.key: art.choose(self._latest_picture(game.key), game_dir, game)
                          for game in games.GAMES}

    def _latest_picture(self, key: str) -> Path | None:
        latest = saves.latest(self._saves, key)
        return latest.picture if latest else None

    # --- the running game ---------------------------------------------------------------------------------------

    def _on_line(self, line: str) -> None:
        switched = launch.switched_game(line)
        if switched is not None:
            # The first game's window closes seconds before the next one's is up: the launcher stays aside.
            self._switching = True
            self._status = t("Switching to {game}...", game=switched.name)
            self.changed.emit()
        elif line.startswith(STATUS_PREFIXES):
            self._status = line[:120]
            self.changed.emit()

    def _on_ended(self, code: int) -> None:
        self._session = None
        self._watch.stop()
        self._game_window = False
        self._switching = False
        stopped, self._stopping = self._stopping, False
        if self._direct:
            QCoreApplication.exit(code)
            return
        reason = launch.last_run_reason(self._started)
        froze = reason.startswith(t("The game froze"))
        if (code == 0 or stopped) and not froze:
            self._status = ""
        else:
            self._status = t("The game froze.") if froze else \
                t("The game stopped unexpectedly (code {code}).", code=code)
            self.message.emit(reason or t("The game ended with code {code}.", code=code) + "\n\n" +
                              t(NO_WINDOW_NOTE))
        self.refresh()

    def _check_game_window(self) -> None:
        open_now = windows.game_window_open()
        if open_now:
            self._switching = False
        elif self._switching:
            return  # between two games of the Collection: not back until the next window, or the end
        if open_now != self._game_window:
            self._game_window = open_now
            self.changed.emit()
