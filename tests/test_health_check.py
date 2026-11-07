# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""tools/health_check.py reads the engine logs into runs and finds a crash, lost cache writes, the preparation page
after a clean run, and how each game was closed."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _tool():
    spec = importlib.util.spec_from_file_location("health_check", TOOLS / "health_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["health_check"] = module  # its dataclasses look their module up
    spec.loader.exec_module(module)
    return module


def _run(folder: Path, when: int, lines: list[str], code: int = 0, seconds: float = 300.0) -> None:
    folder.mkdir(parents=True)
    (folder / "boot.log").write_bytes(("\n".join(lines) + "\n").encode())
    (folder / "boot.json").write_text(json.dumps({"executable": "eboot.bin", "exit_code": code,
                                                  "elapsed_seconds": seconds}), encoding="utf-8")
    os.utime(folder / "boot.log", (when, when))


def test_runs_and_their_checks(tmp_path, monkeypatch) -> None:
    tool = _tool()
    monkeypatch.setattr(tool, "ATTEMPTS", tmp_path)
    frames = [f"Frame stats: {fps} FPS, worst frame 18.0 ms (vblank 60 Hz); 0 shader/pipeline compiles, 0.0 ms"
              for fps in (30.0, 40.0, 60.0, 58.0)]
    _run(tmp_path / "boot-1", 1000, ["# 2026-11-07 20:03:00 eboot.bin (u1) from x", "Preparation screen: shown for 9000 ms",
                                     "Skip title: Uncharted 1: on", *frames, "Skip title: Uncharted 1: main menu on screen",
                                     "Window closed (the player confirmed closing the game)"])
    _run(tmp_path / "boot-2", 2000, ["# 2026-11-07 20:10:00 eboot.bin (u1) from x",
                                     "Preparation screen: shown for 5000 ms", *frames,
                                     "Window closed (the launcher's STOP)",
                                     "Shader cache at exit: 40 writes pending, 3 left after 10.0 s"])
    _run(tmp_path / "boot-3", 3000, ["# 2026-11-07 20:20:00 big3-ps4_Shipping.elf (u3) from x", *frames,
                                     "Freeze: no new frame for 30 s"], code=1)
    runs = tool.runs(10)
    assert [run.game for run in runs] == ["u1", "u1", "u3"]
    assert runs[0].ended == "confirmed" and runs[0].skip_menu and runs[0].fps == [60.0, 58.0]
    assert runs[1].ended == "stop" and runs[1].cache_left == 3
    assert runs[2].crash and runs[2].ended == ""
    checks = {check.title: check for check in tool.run_checks(runs, "en")}
    assert checks["Crashes or freezes"].status == tool.FAIL
    assert checks["Shader preparation page came back"].status == tool.WARN  # run 2 after the clean run 1
    assert checks["Shader cache writes at the exit"].status == tool.WARN
    assert checks["Title page passed"].status == tool.OK
    page = tool.page([], list(checks.values()), runs, "ar")
    assert 'dir="rtl"' in page and "Uncharted 3" in page


def test_the_install_reads_dll_imports() -> None:
    tool = _tool()
    names = tool.pe_imports(Path(sys.executable))
    assert any(name.lower().startswith("python") or name.lower().endswith(".dll") for name in names)
