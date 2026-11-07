# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The PC's graphics card and its class (the preset that suits it), for the Recommended preset.

The game's own log names the card exactly (and whether it is integrated); Windows' list of video controllers is
the fallback for a PC that has not run the game yet."""
from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from . import paths

# The quality classes from the weakest up (the presets of the same names).
TIERS: tuple[str, ...] = ("igpu", "low", "medium", "high", "ultra")
# The folders tools/probe_uncharted.py writes each game's boot.log into (analysis/<folder>/boot.log).
BOOT_LOG_FOLDERS: tuple[str, ...] = ("uncharted", "big2-ps4_Shipping", "big3-ps4_Shipping")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# The engine's line: "GPU: <name>[ (integrated)], <N> MiB VRAM, driver ...". Older engines listed every card as
# "GPU <n>: <name> (DiscreteGpu)" and the chosen one as "GPU: using <name>".
_CARD_LINE = re.compile(r"^GPU: (.+?)( \(integrated\))?, (\d+) MiB VRAM, driver ")
_LISTED_CARD = re.compile(r"^GPU (\d+): (.+) \((\w+)\)\s*$")
_LOG_LINES = 400  # the card is named at the start of a log

# Low-end integrated graphics by model name: AMD's Vega and 610M-890M APUs and the unnamed "Radeon Graphics";
# Intel's UHD/HD, Iris Xe and the integrated Arc. Not: a discrete Arc (A/B series, laptop and Pro ones too), a
# Radeon RX, Vega 56/64, Radeon VII, and Strix Halo (Radeon 8040S-8060S: integrated but as fast as a mid card).
_INTEGRATED_AMD = re.compile(
    r"\bradeon\s*(?:610m|640m|660m|680m|740m|760m|780m|860m|880m|890m)\b"
    r"|\bradeon\s+graphics\b|\bradeon\s+vega\b|\bvega\s*(?:3|6|7|8|9|10|11)\b"
    r"|\bryzen\s+.*\bgraphics\b")
_DISCRETE_ARC = re.compile(r"\barc\s*(?:pro\s*)?[ab]\d{2,3}")
_STRIX_HALO = re.compile(r"\bradeon\s*80[4-6]0s\b")
_SEPARATE_CARD = re.compile(r"\b(?:nvidia|geforce|radeon vii)\b|\brx\s*(?:\d|vega)")
_NVIDIA = re.compile(r"\b(rtx|gtx|gt|mx)\s*(\d{3,4})\s*(ti)?\s*(super)?")
_AMD = re.compile(r"\brx\s*(\d{3,4})\s*(xtx|xt|gre)?")
_ARC = re.compile(r"\barc\s*([ab])(\d{3})")
_LAPTOP = re.compile(r"\d{3,4}m\b")


@dataclass(frozen=True)
class Gpu:
    name: str
    integrated: bool | None = None   # None: not known (only the name)
    vram_mib: int | None = None


def name_key(name: str | None) -> str:
    """A card's name for matching: lower case, without (TM)/(R), single spaces."""
    return " ".join((name or "").lower().replace("(tm)", " ").replace("(r)", " ").split())


def is_strix_halo(name: str | None) -> bool:
    return bool(_STRIX_HALO.search(name_key(name)))


def is_integrated(name: str | None) -> bool:
    """Low-end integrated graphics (the IGPU preset's), from the model name alone."""
    key = name_key(name)
    if not key or is_strix_halo(key) or "nvidia" in key or "geforce" in key:
        return False
    if "vega 56" in key or "vega 64" in key or "radeon vii" in key or re.search(r"\brx\s*\d", key):
        return False
    if "intel" in key:
        return not _DISCRETE_ARC.search(key)
    return bool(_INTEGRATED_AMD.search(key))


def igpu_class(name: str | None) -> str:
    """How strong an integrated GPU is: "weak" (30 FPS at 360p), "mainstream" (60 FPS at 540p) or "strong"
    (60 FPS at 720p)."""
    key = name_key(name)
    if ("intel" in key and "arc" in key) or re.search(r"\b(880m|890m)\b", key):
        return "strong"
    if re.search(r"\b(680m|760m|780m|860m)\b", key) or ("intel" in key and "iris xe" in key):
        return "mainstream"
    if "intel" in key or "vega" in key or re.search(r"\b(610m|640m|660m|740m)\b", key) or "radeon graphics" in key:
        return "weak"
    return "mainstream"


def tier(name: str | None) -> str | None:
    """The class of a card from its model name (one of TIERS), None for a card not known. Laptop chips of the
    High and Ultra classes count one lower."""
    key = name_key(name)
    if is_strix_halo(key):
        return "medium"
    if is_integrated(key):
        return "igpu"
    found = _nvidia_tier(key) or _amd_tier(key) or _other_tier(key)
    if found is None:
        return None
    if "laptop" in key or "max-q" in key or "mobile" in key or _LAPTOP.search(key):
        found = {"ultra": "high", "high": "medium"}.get(found, found)
    return found


def _nvidia_tier(key: str) -> str | None:
    match = _NVIDIA.search(key)
    if not match:
        return None
    kind, number = match.group(1), int(match.group(2))
    ti, super_ = bool(match.group(3)), bool(match.group(4))
    if kind in ("gt", "mx"):
        return "low"
    if kind == "gtx":
        if number == 1080 and ti:
            return "high"
        if 1060 <= number < 1100 or 1660 <= number < 1700 or (number == 1650 and super_):
            return "medium"
        return "low"
    series, model = divmod(number, 100)
    if model >= 80:
        return "ultra" if series >= 30 else "high"
    if model == 70:
        return "ultra" if series >= 40 and (ti or super_) else "high"
    if model == 60:
        return "high" if ti or series >= 50 else "medium"
    return "medium"


def _amd_tier(key: str) -> str | None:
    match = _AMD.search(key)
    if not match:
        return None
    number, suffix = int(match.group(1)), match.group(2) or ""
    if number >= 9000:
        return {7: "ultra", 6: "high"}.get((number % 100) // 10, "medium")
    if number >= 1000:
        series, model = number // 1000, (number % 1000) // 100
        if model >= 9:
            return "ultra"
        if model == 8:
            return "ultra" if suffix.startswith("xt") else "high"
        if model == 7:
            return "medium" if series == 5 else "high"
        return "medium" if model == 6 or number == 5500 else "low"
    return "medium" if number in (470, 480, 570, 580, 590) else "low"


def _other_tier(key: str) -> str | None:
    if "vega 56" in key or "vega 64" in key:
        return "medium"
    if "radeon vii" in key:
        return "high"
    arc = _ARC.search(key)
    if arc:
        return "medium" if int(arc.group(2)) >= 500 else "low"
    if "intel" in key or ("radeon" in key and "graphics" in key):
        return "low"  # other Intel and Radeon graphics the checks above did not place
    return None


def recommendation(name: str | None, integrated: bool | None = None) -> str | None:
    """The preset for a card: IGPU for low-end integrated graphics (the log's word when known, else the model
    name), else its tier. A name that is a separate card never takes IGPU."""
    key = name_key(name)
    if is_strix_halo(key):
        return tier(key)
    if integrated is None or _DISCRETE_ARC.search(key) or _SEPARATE_CARD.search(key):
        integrated = is_integrated(key)
    return "igpu" if integrated else tier(name)


def boot_logs() -> list[Path]:
    return [paths.ROOT / "analysis" / folder / "boot.log" for folder in BOOT_LOG_FOLDERS]


def from_logs(logs: Iterable[Path] | None = None) -> Gpu | None:
    """The card the game used last, as the newest boot.log names it."""
    existing = [log for log in (boot_logs() if logs is None else logs) if log.is_file()]
    for log in sorted(existing, key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            found = _card_in_log(log)
        except OSError:
            continue
        if found:
            return found
    return None


def _card_in_log(log: Path) -> Gpu | None:
    chosen, kinds = None, {}
    with open(log, encoding="utf-8", errors="replace") as lines:
        for number, line in enumerate(lines):
            if number > _LOG_LINES:
                break
            card = _CARD_LINE.match(line)
            if card:
                return Gpu(card.group(1).strip(), bool(card.group(2)), int(card.group(3)))
            if line.startswith("GPU: using "):
                chosen = line[len("GPU: using "):].strip()
                continue
            listed = _LISTED_CARD.match(line)
            if listed:
                kinds[listed.group(2).strip()] = listed.group(3)
    if not chosen:
        return None
    kind = kinds.get(chosen)
    return Gpu(chosen, True if kind == "IntegratedGpu" else False if kind == "DiscreteGpu" else None)


def windows_names() -> list[str]:
    """Windows' video controllers (PowerShell; wmic on systems without CIM cmdlets)."""
    commands = (["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name"],
                ["wmic", "path", "win32_VideoController", "get", "name"])
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            continue
        names = [line.strip() for line in result.stdout.splitlines() if line.strip() and line.strip() != "Name"]
        if names:
            return names
    return []


def detect() -> Gpu | None:
    """The card to recommend for: the log's when the game has run, else the strongest of Windows' list."""
    logged = from_logs()
    if logged:
        return logged
    return strongest(windows_names())


def strongest(names: list[str]) -> Gpu | None:
    if not names:
        return None
    known = [name for name in names if tier(name)]
    name = max(known, key=lambda each: TIERS.index(tier(each) or "igpu")) if known else names[0]
    return Gpu(name)
