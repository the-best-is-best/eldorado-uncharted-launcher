# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Every file the launcher writes goes through here: a temporary file, then a rename, so a write cut short (power
off, a second launcher) never leaves half a file."""
from __future__ import annotations

import os
from pathlib import Path


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    try:
        os.replace(temporary, path)
    except OSError:
        # Windows refuses the rename while another process holds the file open (a virus scanner): written in place.
        temporary.unlink(missing_ok=True)
        path.write_text(text, encoding="utf-8")
