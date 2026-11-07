# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Quick setup's presets. The games have one detail level (the PS4's): a preset is the resolution the game draws
at, the upscaling, the sharpening and the frame rate. Recommended is made for the PC's graphics card."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from . import config, gpu

UPSCALER_TITLES = {"dlss": "DLSS", "fsr4": "FSR 4", "fsr3": "FSR 3.1"}
QUALITY_TITLES = {"off": "Native AA", "quality": "Quality", "balanced": "Balanced", "performance": "Performance",
                  "ultra": "Ultra Performance"}


@dataclass(frozen=True)
class Preset:
    name: str
    title: str
    summary: str
    detail: str
    resolution: str                  # the output size (launcher.json "resolution")
    upscale: str                     # the upscaling quality (launcher.json "upscale")
    values: dict[str, str] = field(default_factory=dict)  # probe-uN.ini keys
    base: str = ""                   # Recommended: the preset it was made from
    upscaler: str | None = None      # Recommended: the temporal upscaler it chose

    @property
    def kind(self) -> str:
        return self.base or self.name


def _values(fps: str, fsr1: str, sharpening: str, **more: str) -> dict[str, str]:
    # async_shaders, which the released launcher's presets also wrote, is read by nothing any more (section 3).
    return {"fps_limit": fps, "frames_queued": "1", "vsync": "1", "fsr1": fsr1, "rcas": "1",
            "rcas_strength": sharpening, **more}


PRESETS: dict[str, Preset] = {preset.name: preset for preset in (
    Preset("igpu", "IGPU", "30–60 FPS  •  540–720p, FSR 1",
           "Integrated Intel and AMD graphics: the game draws at 540p (720p on the strongest, 360p on the weakest) "
           "and FSR 1 brings it up to 1080p. About 30 FPS on Vega and small Radeon chips, 60 on Radeon "
           "680M/760M/780M and Iris Xe. No anti-aliasing and the least memory.",
           "1920x1080", "performance", _values("60", "1", "75", upscaler="off")),
    Preset("low", "LOW", "60 FPS  •  1080p, FSR 1",
           "Older graphics cards: the game draws at half of 1080p and FSR 1 brings it up; the HUD stays sharp.",
           "1920x1080", "performance", _values("60", "1", "75")),
    Preset("medium", "MEDIUM", "60 FPS  •  as on PS4",
           "As on the PS4: 1080p at 60 FPS. Right for most PCs.",
           "1920x1080", "off", _values("60", "0", "75")),
    Preset("high", "HIGH", "60 FPS  •  1440p",
           "Sharper: the game draws at 1440p.",
           "2560x1440", "off", _values("60", "0", "50")),
    Preset("ultra", "ULTRA", "4K  •  up to 120 FPS",
           "Fast graphics cards: native 4K and up to 120 FPS (experimental). Drake's Fortune draws at 1620p and "
           "scales up.",
           "3840x2160", "off", _values(str(config.MAX_FPS), "0", "50")),
)}
ORDER: tuple[str, ...] = ("recommended",) + gpu.TIERS


def for_igpu(preset: Preset, card_name: str | None) -> Preset:
    """The IGPU preset's own steps for the integrated GPU's class: how far below 1080p it draws, the limit."""
    kind = gpu.igpu_class(card_name)
    if kind == "weak":
        return replace(preset, upscale="ultra", values={**preset.values, "fps_limit": "30"})
    if kind == "strong":
        return replace(preset, upscale="quality")
    return preset


def recommended(card: gpu.Gpu | None, upscalers: set[str]) -> Preset:
    """The preset of the card's class (Medium when not known) with the best upscaler the card has: DLSS on a
    GeForce RTX, FSR 4 on a Radeon RX 9000 (when their files are installed: `upscalers`), else TAA or FSR 1."""
    base_name = (gpu.recommendation(card.name, card.integrated) if card else None) or "medium"
    base = PRESETS[base_name]
    values, upscale = dict(base.values), base.upscale
    key = gpu.name_key(card.name if card else "")
    upscaler = None
    if "dlss" in upscalers and _matches(r"\brtx\s*\d", key):
        upscaler = "dlss"
    elif "fsr4" in upscalers and _matches(r"\brx\s*9\d{3}", key):
        upscaler = "fsr4"
    if upscaler:
        # Quality: sharper than TAA and lighter than drawing at the output size; the weakest classes draw at half.
        upscale = "performance" if base_name in ("igpu", "low") else "quality"
        values.update(upscaler=upscaler, fsr1="0", rcas_strength="75")
    elif "upscaler" not in values:
        values["upscaler"] = "taa"
    preset = replace(base, name="recommended", title="RECOMMENDED", upscale=upscale, values=values, base=base_name,
                     upscaler=upscaler)
    if base_name == "igpu" and not upscaler:
        preset = for_igpu(preset, card.name if card else None)
    height = int(preset.resolution.split("x")[1])
    size = "4K" if height == 2160 else f"{height}p"
    if upscaler:
        method = f"{UPSCALER_TITLES[upscaler]} {QUALITY_TITLES[preset.upscale]}"
    else:
        method = "FSR 1" if preset.values.get("fsr1") == "1" else "TAA"
    fps = preset.values["fps_limit"]
    detail = (f"Made for your PC ({card.name}): {size} at {fps} FPS with {method}." if card else
              "Made for your PC once its graphics card is found: Medium until then.")
    return replace(preset, summary=f"{fps} FPS  •  {size}, {method}", detail=detail)


def resolve(name: str, card: gpu.Gpu | None, upscalers: set[str]) -> Preset:
    """The preset as it is applied on this PC."""
    if name == "recommended":
        return recommended(card, upscalers)
    if name not in PRESETS:
        raise KeyError(f"no preset {name!r}")
    preset = PRESETS[name]
    return for_igpu(preset, card.name if card else None) if name == "igpu" else preset


def all_for(card: gpu.Gpu | None, upscalers: set[str]) -> list[Preset]:
    """Quick setup's cards in their order (the IGPU card shows its plain values)."""
    return [recommended(card, upscalers) if name == "recommended" else PRESETS[name] for name in ORDER]


def _matches(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None
