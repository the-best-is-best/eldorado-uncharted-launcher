# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Play time, last played and average FPS per game (analysis/uncharted-user/eldorado-stats.json, written by
tools/probe_uncharted.py)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from . import paths

STATS_FILE = paths.USER_DIR / "eldorado-stats.json"


@dataclass(frozen=True)
class Stats:
    seconds: int = 0
    sessions: int = 0
    last: int = 0
    fps: float = 0.0

    def play_time(self) -> str:
        hours, minutes = divmod(self.seconds // 60, 60)
        return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"

    def last_played(self, now: float | None = None) -> str:
        if not self.last:
            return "Not played yet"
        days = int(((now or time.time()) - self.last) // 86400)
        return "Today" if days <= 0 else "Yesterday" if days == 1 else f"{days} days ago"


def load() -> dict[str, Stats]:
    try:
        data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    result = {}
    for key, entry in (data.items() if isinstance(data, dict) else ()):
        if isinstance(entry, dict):
            count = entry.get("fps_count") or 0
            result[key] = Stats(int(entry.get("seconds", 0)), int(entry.get("sessions", 0)),
                                int(entry.get("last", 0)), entry.get("fps_sum", 0) / count if count else 0.0)
    return result
