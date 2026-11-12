# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""Uncharted 2's Nepal attack helicopter: how many hits destroy it, as on the launcher's level (Damage to Nate).

The helicopter has no health. Its script (u2data/build/main/dc1/ps4/ss-warzone.bin, state-script 0x10e0) counts
'explode-attack' hits and destroys it at hits-to-kill. The script's own function (lambda 0x3d78) sets the three limits
from get-dda: 1/2/3 up to 0.5, 3/6/10 up to 3.0, 4/8/14 above (also what a game without DDA gets, 5.0), and the script
declares 4/8/14 as the starting values. Decoded in tools/ notes (see docs/TESTING.md); every value below is an
immediate or a declared int of that file, patched in place (the size does not change).

The view of the game (tools/game_update_view.py) holds the file as a link to the game's own; this writes a patched
copy of it IN THE VIEW ONLY and puts the link back for a level that needs no patch. The game's files are not touched.
"""
import hashlib
import os
import shutil
from pathlib import Path

REL = ("u2data", "build", "main", "dc1", "ps4", "ss-warzone.bin")
ORIGINAL_MD5 = "51bd4f5d54af1e18868aac6091edf936"        # update 1.02's file (Game and Game original agree)
# Hits to stage 2 / stage 3 / destroy for Damage to Nate 0 Explorer, 1 Easy, 2 Normal, 3 Hard.
HITS = {0: (1, 2, 3), 1: (1, 2, 3), 2: (3, 6, 10), 3: (4, 8, 14)}
DECLARED = (0x1A004, 0x1A00C, 0x1A014)                   # the script's starting values (int32, little endian)
# The immediates (low byte) of the dda function's three tiers: stage 2, stage 3, destroy.
TIERS = ((0xC0C2, 0xC0E2, 0xC102), (0xC14E, 0xC16E, 0xC18E), (0xC1B2, 0xC1D2, 0xC1F2))
EXPECT = ((1, 2, 3), (3, 6, 10), (4, 8, 14))


def patched(data, level):
    """data with the hit limits of `level`, or None when this is not the file the offsets were decoded from."""
    if hashlib.md5(data).hexdigest() != ORIGINAL_MD5 or level not in HITS:
        return None
    out = bytearray(data)
    want = HITS[level]
    for offset, value in zip(DECLARED, want):
        out[offset] = value
    for tier, expect in zip(TIERS, EXPECT):
        for offset, old, value in zip(tier, expect, want):
            if out[offset] != old:
                return None
            out[offset] = value
    return bytes(out)


def apply(view, level):
    """Makes the view's copy of the file match `level` (an int 0-3, or None for the game's own). Returns a log line."""
    path = view.joinpath(*REL)
    parent = path.parent
    try:
        if not parent.is_dir() or not path.is_file():
            return "no u2data in the view"
        if os.path.normcase(os.path.realpath(parent)) != os.path.normcase(str(Path(os.path.realpath(view)).joinpath(*REL[:-1]))):
            return "the file's folder is a link into the game (left alone)"
        data = path.read_bytes()
        original = data if hashlib.md5(data).hexdigest() == ORIGINAL_MD5 else None
        cache = parent / (REL[-1] + ".original")
        if original is None and cache.is_file():
            original = cache.read_bytes()
        if original is None or hashlib.md5(original).hexdigest() != ORIGINAL_MD5:
            return "not update 1.02's file (left alone)"
        if level is None:
            if data is not original:
                path.unlink()
                path.write_bytes(original)
            return "helicopter: the game's own hits"
        new = patched(original, level)
        if new is None:
            return "helicopter: the file differs from the decoded one (left alone)"
        if not cache.is_file():
            cache.write_bytes(original)
        if data != new:
            path.unlink()          # a hard link: only the view's name goes, the game's file stays
            path.write_bytes(new)
        return f"helicopter: {HITS[level][2]} hits destroy it (level {level})"
    except OSError as error:
        return f"helicopter: not changed ({error})"
