# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Frame rate advice: after a session that ran clearly below the frame rate limit while the graphics card was the
limit, one step lower picture quality is offered (the player says yes or no; nothing changes on its own).

The start script writes each session's own numbers into eldorado-stats.json (tools/probe_uncharted.py PlayStats):
session_fps (the average in play), session_samples (Frame stats lines, one per 5 s), session_gpu_wait (the share
of time the game waited for the card, the engine's "GPU ticks") and session_end. A card that is not the limit
(the CPU is) gains nothing from a lower picture, so no advice then.

The steps: with an upscaler (DLSS, FSR 3.1, FSR 4, FSR 1) its quality one step down (Native AA, Quality,
Balanced, Performance, Ultra Performance); without one, FSR 1 at Quality (it works on every card)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from . import config as cfg
from . import resolution
from .stats import STATS_FILE

LADDER = ("off", "quality", "balanced", "performance", "ultra")
SLOW = 0.85         # below 85% of the limit (51 FPS at 60) is clearly slow
LEAST_SAMPLES = 24  # two minutes of play: not a cutscene or a loading moment
GPU_LIMIT = 20.0    # the game waited for the card at least this share of the time: the card is the limit
ASKED = "fps_advice_asked"  # in the game's entry: the session_end already asked about (asked once per session)


@dataclass(frozen=True)
class Step:
    fps: float           # the session's average
    limit: int           # the frame rate limit
    upscaler: str        # the upscaler after the step ("fsr1" when it is turned on)
    upscale: str         # its quality after the step
    turn_on_fsr1: bool   # no upscaler before: FSR 1 is turned on


def session(key: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    if data is None:
        try:
            data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    entry = data.get(key) if isinstance(data, dict) else None
    return entry if isinstance(entry, dict) else {}


def advice(key: str, game: dict[str, Any], ini: dict[str, str],
           stats: dict[str, Any] | None = None) -> Step | None:
    """The step to offer after this game's last session, or None (fast enough, too short, the CPU is the limit,
    already asked, or nothing lower)."""
    last = session(key, stats)
    end = int(last.get("session_end") or 0)
    if not end or int(game.get(ASKED) or 0) >= end:
        return None
    fps = float(last.get("session_fps") or 0.0)
    try:
        limit = int(ini.get("fps_limit") or cfg.INI_DEFAULTS["fps_limit"])
    except ValueError:
        return None
    if (int(last.get("session_samples") or 0) < LEAST_SAMPLES or limit <= 0 or fps <= 0 or fps >= limit * SLOW
            or float(last.get("session_gpu_wait") or 0.0) < GPU_LIMIT):
        return None
    upscaler = resolution.upscaler(ini)
    if upscaler == "off":
        return Step(fps, limit, "fsr1", "quality", True)
    current = str(game.get("upscale", "off"))
    index = LADDER.index(current) if current in LADDER else 0
    if upscaler == "fsr1" and current == "off":
        index = 1  # FSR 1 has no Native AA: it runs at Quality
    if index + 1 >= len(LADDER):
        return None
    return Step(fps, limit, upscaler, LADDER[index + 1], False)


def mark_asked(config: cfg.Config, key: str, stats: dict[str, Any] | None = None) -> None:
    """This session's advice was shown (taken or not): not again until the next session."""
    end = int(session(key, stats).get("session_end") or 0)
    if end:
        config.game(key)[ASKED] = end
        config.save()


def apply(config: cfg.Config, key: str, step: Step) -> None:
    """The step into the game's settings (as Settings > Upscaling would set it); the settings are custom then."""
    game = config.game(key)
    game["upscale"] = step.upscale
    if game.get("preset") != "custom":
        game["preset"] = "custom"
    config.save()
    if step.turn_on_fsr1:
        cfg.write_ini(key, {"fsr1": "1"})
