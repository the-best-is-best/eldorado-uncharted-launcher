# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""core/game_files.py on temporary folders: installing the player's game from its .pkg with the unpacking tool
(tools/install_update.py) replaced by a fake, and the tools loaded by path."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import config as cfg  # noqa: E402
from core import game_files  # noqa: E402


class FakeUpdateError(Exception):
    """tools/install_update.py's UpdateError."""


def fake_installer(monkeypatch: pytest.MonkeyPatch, install_game: Any) -> None:
    """game_files loads tools/install_update.py by path; the test gives it this one."""
    fake = SimpleNamespace(install_game=install_game, UpdateError=FakeUpdateError)
    monkeypatch.setattr(game_files, "tool_module", lambda name: fake)


def unpacked_game(parent: Path, title: str = "CUSA02320", complete: bool = True) -> Path:
    """What the tool leaves: <parent>/<title>/uroot with the game's files (the tool returns the uroot)."""
    uroot = parent / title / "uroot"
    (uroot / "sce_sys").mkdir(parents=True)
    if complete:
        (uroot / "eboot.bin").write_bytes(b"")
        (uroot / "sce_sys" / "param.sfo").write_bytes(b"")
    return uroot


def test_install_game_pkg_makes_the_unpacked_folder_the_game_folder(tmp_path: Path,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    file = tmp_path / "launcher.json"
    file.write_text('{"game": "u2", "game_dir": "C:\\\\old"}', encoding="utf-8")
    config = cfg.Config.load(file)
    pkg, destination = tmp_path / "game.pkg", tmp_path / "games"
    seen: dict[str, Any] = {}

    def install_game(given_pkg: Path, parent: Path, log: Any) -> Path:
        seen.update(pkg=Path(given_pkg), parent=Path(parent))
        log("Unpacking the game...")
        # The install takes minutes: another setting changed meanwhile must survive it.
        aside = cfg.Config.load(file)
        aside.data["anisotropy"] = "16"
        aside.save()
        return unpacked_game(Path(parent))

    fake_installer(monkeypatch, install_game)
    steps: list[str] = []
    game_dir = game_files.install_game_pkg(config, pkg, destination, steps.append)
    assert game_dir == destination / "CUSA02320" / "uroot"
    assert seen == {"pkg": pkg, "parent": destination}
    assert steps == ["Unpacking the game..."]
    assert config.game_dir() == game_dir
    stored = json.loads(file.read_text(encoding="utf-8"))
    assert (stored["game_dir"], stored["anisotropy"], stored["game"]) == (str(game_dir), "16", "u2")


def test_install_game_pkg_reports_the_tools_refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = tmp_path / "launcher.json"
    file.write_text('{"game_dir": "C:\\\\old"}', encoding="utf-8")
    config = cfg.Config.load(file)

    def refuse(pkg: Path, parent: Path, log: Any) -> Path:
        raise FakeUpdateError("This is a game update, not the game.")

    fake_installer(monkeypatch, refuse)
    with pytest.raises(game_files.GameFilesError) as caught:
        game_files.install_game_pkg(config, tmp_path / "update.pkg", tmp_path, lambda text: None)
    assert str(caught.value) == "The game was not installed:\nThis is a game update, not the game."
    assert config.game_dir() == Path("C:\\old")
    assert json.loads(file.read_text(encoding="utf-8")) == {"game_dir": "C:\\old"}


def test_install_game_pkg_reports_a_disk_problem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = cfg.Config.load(tmp_path / "launcher.json")

    def fail(pkg: Path, parent: Path, log: Any) -> Path:
        raise PermissionError("no write access")

    fake_installer(monkeypatch, fail)
    with pytest.raises(game_files.GameFilesError) as caught:
        game_files.install_game_pkg(config, tmp_path / "game.pkg", tmp_path, lambda text: None)
    assert str(caught.value) == "The game was not installed:\nPermissionError: no write access"
    assert not (tmp_path / "launcher.json").exists()


def test_install_game_pkg_refuses_a_folder_without_the_game(tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    config = cfg.Config.load(tmp_path / "launcher.json")
    fake_installer(monkeypatch, lambda pkg, parent, log: unpacked_game(Path(parent), complete=False))
    with pytest.raises(game_files.GameFilesError, match="has no eboot.bin"):
        game_files.install_game_pkg(config, tmp_path / "game.pkg", tmp_path, lambda text: None)
    assert not (tmp_path / "launcher.json").exists()


def test_tools_are_loaded_by_path() -> None:
    installer = game_files.tool_module("install_update")
    assert callable(installer.install_game) and callable(installer.install) and installer.UpdateError
    finder = game_files.tool_module("arabic_language")
    assert callable(finder.find_arabic_language) and set(finder.DATA_DIRS) == {"u1", "u2", "u3"}
    with pytest.raises(game_files.GameFilesError, match="missing"):
        game_files.tool_module("no_such_tool")
