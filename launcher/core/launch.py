# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Starting and stopping a game through tools/probe_uncharted.py, exactly as the released launcher does
(roadmap section 3: the command, the UNCHARTED_* environment, the ini files), and reading what its output and the
engine's log say: a switch to another game of the Collection, why a run ended."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from . import config as cfg
from . import games, paths, resolution
from . import i18n
from .i18n import t

RUN_SCRIPT = paths.ROOT / "tools" / "probe_uncharted.py"
LAST_RUN_LOG = paths.USER_DIR / "launcher-last-run.log"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# The start script's line when the Collection menu starts another game (the executable follows).
SWITCH_LINE = "Collection: switching to "
NO_GAME_FOLDER = ("Select your Uncharted: The Nathan Drake Collection game folder (the folder with eboot.bin and "
                  "sce_sys).")
LOG_TAIL = 80
# The launcher's STOP: the game sees this file and closes the usual way, keeping the shader cache's last writes
# (engine/gpu/shim/window.cpp, BB_STOP_FILE from the start script); after STOP_WAIT seconds it is ended.
STOP_FILE = paths.USER_DIR / "stop-request"
STOP_WAIT = 15.0  # lines read from the end of a log for the reason a game stopped


class LaunchError(Exception):
    """A game could not start; the message is for the player."""


def environment(config: cfg.Config, base: dict[str, str] | None = None,
                game: games.Game | None = None) -> dict[str, str]:
    """The environment tools/probe_uncharted.py reads: every game's own settings (the Collection menu starts the
    other games itself) and the shared ones. UNCHARTED_LANGUAGE (kept for old scripts) is the started game's,
    else the chosen one's."""
    env = dict(os.environ if base is None else base)
    data = config.data
    started = game.key if game else config.selected
    env["UNCHARTED_DIAGNOSTICS"] = "1" if data.get("diagnostics", True) else "0"
    env["UNCHARTED_JOB_SLEEP"] = {"off": "0", "on": "1"}.get(str(data.get("job_sleep", "auto")), "auto")
    env["UNCHARTED_LANGUAGE"] = str(config.game(started).get("language", "1"))
    env["UNCHARTED_ANISOTROPY"] = str(data.get("anisotropy", "0"))
    env["UNCHARTED_NO_DOF"] = "1" if data.get("no_dof") else "0"
    env["UNCHARTED_TORCH_FORWARD"] = "1" if data.get("torch_forward", True) else "0"
    env["UNCHARTED_U3_EXPOSURE"] = str(data.get("u3_exposure", "0"))
    nate = str(data.get("nate_damage", "off"))
    if nate in ("0", "1", "2", "3"):
        env["UNCHARTED_NATE_DAMAGE"] = nate
    else:
        env.pop("UNCHARTED_NATE_DAMAGE", None)
    env["UNCHARTED_HIRES_SHADOWS"] = "1" if data.get("hires_shadows") else "0"
    env["UNCHARTED_UNLOCK"] = "1" if data.get("unlock") else "0"
    env["UNCHARTED_CHEATS"] = ",".join(config.cheats())
    # The engine's own texts (the close question, the save list, the loading screen) in the launcher's language.
    env["UNCHARTED_UI_LANGUAGE"] = i18n.language()
    # A game's update is the one beside its folder (<folder>-patch), found by the start script: never one chosen for
    # another game folder.
    env.pop("UNCHARTED_UPDATE", None)
    env.pop("GOW3_VBLANK_HZ", None)
    for key in games.KEYS:
        game, name = config.game(key), key.upper()
        render, output = resolution.sizes(game, cfg.read_ini(key))
        env[f"UNCHARTED_RESOLUTION_{name}"] = render
        if output:
            env[f"UNCHARTED_OUTPUT_RES_{name}"] = output
        else:
            env.pop(f"UNCHARTED_OUTPUT_RES_{name}", None)
        env[f"UNCHARTED_MULTITHREADED_{name}"] = "1" if game.get("multithreaded", True) else "0"
        env[f"UNCHARTED_SAVE_PROFILE_{name}"] = str(game.get("save_profile", "1"))
        env[f"UNCHARTED_LANGUAGE_{name}"] = str(game.get("language", "1"))
    return env


def command(game: games.Game, game_dir: Path) -> list[str]:
    python = Path(sys.executable)
    # pythonw has no output to read: the start script runs under python.exe (without a console: NO_WINDOW).
    if python.name.lower() == "pythonw.exe" and python.with_name("python.exe").exists():
        python = python.with_name("python.exe")
    return [str(python), "-u", str(RUN_SCRIPT), "--boot", "--seconds", "0", "--executable", game.executable,
            "--game", str(game_dir)]


class Session:
    """One running game: the start script's process and its output, line by line, to on_line."""

    def __init__(self, config: cfg.Config, game: games.Game, on_line: Callable[[str], None],
                 on_end: Callable[[int], None], prepare: bool = False) -> None:
        """prepare: the game's shaders are prepared with no window and no game (the engine's BB_PREPARE_ONLY);
        the progress comes as PREP lines."""
        if not RUN_SCRIPT.exists():
            raise LaunchError(t("The start script is missing:") + f"\n{RUN_SCRIPT}")
        game_dir = config.game_dir()
        if not games.is_game_dir(game_dir):
            raise LaunchError(t(NO_GAME_FOLDER))
        for key in games.KEYS:
            # The keys the game's settings file lacks get their defaults; the in-game menu's own values stay.
            current = cfg.read_ini(key)
            cfg.write_ini(key, {name: current[name] for name in cfg.INI_DEFAULTS})
        args = command(game, game_dir)
        _allow_game_foreground()
        try:
            env = environment(config, game=game)
            if prepare:
                env["UNCHARTED_PREPARE_ONLY"] = "1"
            self.process = subprocess.Popen(args, cwd=str(paths.ROOT), env=env,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, text=True,
                                            encoding="utf-8", errors="replace")
        except OSError as error:
            raise LaunchError(t("Could not start the game:") + f"\n{error}") from error
        self.game = game
        self.prepare = prepare
        self.started = time.time()
        self._on_line, self._on_end = on_line, on_end
        self._log = _open_log(args)
        threading.Thread(target=self._read, daemon=True).start()

    def running(self) -> bool:
        return self.process.poll() is None

    def stop(self) -> None:
        """Asks the game to close (STOP_FILE): it closes the usual way and keeps the shader cache's last writes.
        After STOP_WAIT seconds, or at once while only preparing shaders (no window to close), the start script
        and its game are ended (it owns a Windows job that ends the game with it). Returns at once."""
        if not self.running():
            return
        if not self.prepare:
            try:
                STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
                STOP_FILE.write_text("stop\n", encoding="utf-8")
            except OSError:
                pass
        threading.Thread(target=self._end_after, args=(0.0 if self.prepare else STOP_WAIT,), daemon=True).start()

    def _end_after(self, seconds: float) -> None:
        try:
            self.process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"], creationflags=NO_WINDOW,
                           capture_output=True)
        try:
            STOP_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    def _read(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            line = line.rstrip()
            if self._log:
                self._log.write(line + "\n")
                self._log.flush()
            self._on_line(line)
        code = self.process.wait()
        if self._log:
            self._log.close()
        self._on_end(code)


def _open_log(args: list[str]):
    """The start script's output kept for "the game does not start" reports (as the released launcher)."""
    try:
        LAST_RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
        log = open(LAST_RUN_LOG, "w", encoding="utf-8")
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(args)}\n")
        return log
    except OSError:
        return None


# --- what the output says ----------------------------------------------------------------------------------------


def switched_game(line: str) -> games.Game | None:
    """The game the Collection menu switched to, from the start script's line; None for any other line (or an
    executable no game of the table has)."""
    if not line.startswith(SWITCH_LINE):
        return None
    words = line[len(SWITCH_LINE):].split()
    executable = words[0] if words else ""
    return next((game for game in games.GAMES if game.executable == executable), None)


def tail(path: Path, count: int = LOG_TAIL) -> list[str]:
    """The last lines of a log; none when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-count:]
    except OSError:
        return []


def named_log(lines: list[str]) -> Path | None:
    """The engine's boot.log, as the start script names it at the end of its output ("Log: <path>")."""
    for line in reversed(lines):
        if line.startswith("Log: "):
            return Path(line[5:].strip())
    return None


def written_since(path: Path, moment: float) -> bool:
    try:
        return path.stat().st_mtime >= moment
    except OSError:
        return False


def crash_reason(lines: list[str]) -> str:
    """A short reason from the end of a log: a freeze, the runtime's fault report or an engine stop; "" when the
    lines say nothing. A freeze is reported however the game was closed afterwards."""
    for line in reversed(lines):
        if line.startswith("Freeze: no new frame for"):
            return (t("The game froze") + f" ({line[len('Freeze: '):].strip()}).\n\n" +
                    t("The log folder's boot.log has the threads' stacks."))
        if line.startswith("Hang watchdog:") and " report " in line:
            return (t("The game froze") + ". " + t("A report of where it stopped was saved:") + "\n" +
                    line.split(" report ", 1)[1].strip())
    for index, line in enumerate(lines):
        if line.startswith("Fault:"):
            where = next((entry.strip() for entry in lines[index + 1:index + 6]
                          if entry.lstrip().startswith(("host #0", "#0"))), "")
            return "\n".join(part for part in (line.strip(), where) if part) + \
                "\n\n" + t("The log folder's boot.log has the details.")
    for index, line in enumerate(lines):
        if line.startswith("STOP:") or "Unreachable code" in line or "Assertion" in line:
            context = [entry.strip() for entry in lines[max(0, index - 2):index + 1] if entry.strip()]
            return "\n".join(context)[-600:]
    return ""


def last_run_reason(started: float, run_log: Path = LAST_RUN_LOG) -> str:
    """Why the last run ended: from the engine's boot.log the start script names (when this run wrote it), else
    from the start script's own output; "" when neither says."""
    run_lines = tail(run_log)
    engine_log = named_log(run_lines)
    engine_lines = tail(engine_log) if engine_log is not None and written_since(engine_log, started - 1) else []
    return crash_reason(engine_lines) or crash_reason(run_lines)


def _allow_game_foreground() -> None:
    """The game's window, two processes down, may take the foreground (fullscreen and keyboard need it)."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
