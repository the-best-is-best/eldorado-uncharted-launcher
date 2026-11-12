# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""Uncharted 2's shootable helicopters: how many hits destroy them, as on the launcher's level (Damage to Nate).

A helicopter has no health. Its script counts hits and destroys it at a limit; the script's own dda function sets the
limits from get-dda in three tiers (up to 0.5, up to 3.0, above, which is also what a game without DDA gets, 5.0), and
the script declares the top tier's values as its starting ones. Decoded from the DC files (read-only study, every
offset checked against the original bytes; nothing is guessed about the engine):
  - Nepal (u2data/.../dc1/ps4/ss-warzone.bin, state-script 0x10e0): 'explode-attack' hits, limits stage 2 / stage 3 /
    destroy = 1/2/3, 3/6/10, 4/8/14.
  - The train chapter's cliff helicopter (ss-train.bin, state-script 0x1768): attack type 7 hits (probably the
    anti-aircraft gun), twelve thresholds, destroyed on the hit after the last: 111, 151 or 221 hits.
The two other helicopter scenes of the campaign (ss-war-escape.bin, the other train one) are scripted: no hit limit.

The view of the game (tools/game_update_view.py) holds each file as a link to the game's own; this writes a patched copy
IN THE VIEW ONLY and puts the link back for a level that needs no patch. The game's files are not touched.
"""
import hashlib
import os
from pathlib import Path

DIR = ("u2data", "build", "main", "dc1", "ps4")
# Same-size edits (a low byte each; the values fit in one byte). level -> tier of the game's own dda function:
# 0 Explorer and 1 Easy the lowest, 2 Normal the middle, 3 Hard the top.
TIER_OF_LEVEL = {0: 0, 1: 0, 2: 1, 3: 2}

NEPAL_LIMITS = ((1, 2, 3), (3, 6, 10), (4, 8, 14))
TRAIN_LIMITS = ((1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110),
                (1, 15, 30, 45, 60, 75, 90, 105, 120, 130, 140, 150),
                (1, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220))

# The train helicopter is destroyed on the hit after its last threshold; the game's own numbers (111 / 151 / 221) took
# too long to shoot down with the truck's gun, so the launcher's levels use these hits instead (the stage thresholds
# between 1 and the last are spread evenly, so smoke and fire still come in stages).
TRAIN_KILL_HITS = {0: 30, 1: 30, 2: 50, 3: 100}


def train_thresholds(level):
    kill = TRAIN_KILL_HITS[level]
    last = kill - 1
    return tuple([1] + [1 + round((last - 1) * i / 11) for i in range(1, 12)])


FILES = {
    "ss-warzone.bin": {   # update 1.02's file (Game and Game original agree)
        "md5": "51bd4f5d54af1e18868aac6091edf936",
        "limits": NEPAL_LIMITS,
        "declared": (0x1A004, 0x1A00C, 0x1A014),   # the script's starting values (int32, little endian)
        "tiers": ((0xC0C2, 0xC0E2, 0xC102), (0xC14E, 0xC16E, 0xC18E), (0xC1B2, 0xC1D2, 0xC1F2)),
        "name": "Nepal helicopter",
    },
    "ss-train.bin": {
        "md5": "71d02e22ef5be69d2b6b68d45547c0a6",
        "limits": TRAIN_LIMITS,
        "declared": tuple(0x12834 + 8 * i for i in range(12)),
        "tiers": (tuple(0x55ABE + 0x20 * i for i in range(12)),
                  tuple(0x55CF2 + 0x20 * i for i in range(12)),
                  tuple(0x55F1E + 0x20 * i for i in range(12))),
        "name": "train helicopter",
        "want": train_thresholds,
    },
}

# Kept for the older callers and tests: the Nepal helicopter's table.
REL = DIR + ("ss-warzone.bin",)
ORIGINAL_MD5 = FILES["ss-warzone.bin"]["md5"]
HITS = {level: NEPAL_LIMITS[tier] for level, tier in TIER_OF_LEVEL.items()}


def patched_file(name, data, level):
    """data of file `name` with the hit limits of `level`, or None when it is not the file the offsets came from."""
    spec = FILES[name]
    if hashlib.md5(data).hexdigest() != spec["md5"] or level not in TIER_OF_LEVEL:
        return None
    out = bytearray(data)
    want = spec["want"](level) if "want" in spec else spec["limits"][TIER_OF_LEVEL[level]]
    # The declared values are the top tier's; the dda function's three tiers hold their own.
    for offset, old, value in zip(spec["declared"], spec["limits"][2], want):
        if out[offset] != old:
            return None
        out[offset] = value
    for tier, expect in zip(spec["tiers"], spec["limits"]):
        for offset, old, value in zip(tier, expect, want):
            if out[offset] != old:
                return None
            out[offset] = value
    return bytes(out)


def patched(data, level):
    """The Nepal file (kept for callers and tests)."""
    return patched_file("ss-warzone.bin", data, level)


def _apply_one(view, name, level):
    spec = FILES[name]
    parent = view.joinpath(*DIR)
    path = parent / name
    if not parent.is_dir() or not path.is_file():
        return f"{spec['name']}: file not in the view"
    if os.path.normcase(os.path.realpath(parent)) != os.path.normcase(str(Path(os.path.realpath(view)).joinpath(*DIR))):
        return f"{spec['name']}: the file's folder is a link into the game (left alone)"
    data = path.read_bytes()
    original = data if hashlib.md5(data).hexdigest() == spec["md5"] else None
    cache = parent / (name + ".original")
    if original is None and cache.is_file():
        original = cache.read_bytes()
    if original is None or hashlib.md5(original).hexdigest() != spec["md5"]:
        return f"{spec['name']}: not update 1.02's file (left alone)"
    if level is None:
        if data != original:
            path.unlink()
            path.write_bytes(original)
        return f"{spec['name']}: the game's own hits"
    new = patched_file(name, original, level)
    if new is None:
        return f"{spec['name']}: the file differs from the decoded one (left alone)"
    if not cache.is_file():
        cache.write_bytes(original)
    if data != new:
        path.unlink()          # a hard link: only the view's name goes, the game's file stays
        path.write_bytes(new)
    kill = (spec["want"](level) if "want" in spec else spec["limits"][TIER_OF_LEVEL[level]])[-1]
    return f"{spec['name']}: destroyed at {kill}{'' if name == 'ss-warzone.bin' else ' + 1'} hits (level {level})"


def apply(view, level):
    """Makes the view's copies of the helicopter scripts match `level` (an int 0-3, or None for the game's own).
    Returns the log lines."""
    lines = []
    for name in FILES:
        try:
            lines.append(_apply_one(view, name, level))
        except OSError as error:
            lines.append(f"{FILES[name]['name']}: not changed ({error})")
    return "\n".join(lines)
