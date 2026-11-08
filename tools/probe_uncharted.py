#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Starts a game of the Collection for the launcher: the launcher's settings become the engine's.

The launcher (launcher/uncharted_launcher.pyw) calls this script as it always did:

    python -u tools/probe_uncharted.py --boot --seconds 0 --executable <eboot.bin|big2-ps4_Shipping.elf|
        big3-ps4_Shipping.elf> --game <folder>

and passes its settings in the environment (UNCHARTED_* and GOW3_*) and in each game's settings file
analysis/uncharted-user/probe-u<N>.ini. The engine in engine/ (run.py, bb-probe.exe) takes BB_* variables,
a per-game bbport-u<N>.ini and input-u<N>.ini: this script translates one into the other, runs engine/run.py,
and keeps the log where the launcher and the tools look for it: analysis/<game log dir>/boot.log, with a copy
per run in attempts/boot-<time>/ and the boot.json / boot.running.json records.

Folders (all under this install, so an update keeps them):
    analysis/uncharted-user         saves, settings files, controls files, the shader cache (cache/)
    analysis/out/{eboot,big2,big3}  the prepared executables (run.py)
    analysis/<log dir>/boot.log     the game's log (uncharted, big2-ps4_Shipping, big3-ps4_Shipping)

Stopping: the game runs inside a Windows job that ends when this script ends, so the launcher's STOP (which
ends this script) also ends a game that restarted itself ("Apply and restart"), and closing the launcher
alone leaves the game running.
"""
import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import discord_presence  # noqa: E402
from game_update_view import game_with_update  # noqa: E402
from text_languages import LANGUAGE_IDS, cached_text_languages  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
USER = ROOT / "analysis" / "uncharted-user"
STOP_FILE = USER / "stop-request"  # the launcher's STOP (gpu/shim/window.cpp closes the game)
EXECUTABLES = ("eboot.bin", "big2-ps4_Shipping.elf", "big3-ps4_Shipping.elf")
GAME_KEYS = {"eboot.bin": "u1", "big2-ps4_Shipping.elf": "u2", "big3-ps4_Shipping.elf": "u3"}
LOG_DIRS = {"u1": "uncharted", "u2": "big2-ps4_Shipping", "u3": "big3-ps4_Shipping"}
NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# The two builds of the game code, by SHA-1 of the segments an executable loads (as engine/launcher's
# shader preparation knows them): the shader location index to use is chosen by title id and build.
GAME_CODE = {
    "cd749c2f217a842200a9867f7c8af0973c990a74": "1.00", "1616597c9cf8b4b6d50d7cbf3aeb3677efba6587": "1.00",
    "1d949b215bb036fe685511aca4f560d63dd50442": "1.00", "fd024eaeb58c4b778613b54a9e69f6fbc8615a68": "1.02",
    "de8ce6e778f39b3c2914fd71f1df7117282f62e2": "1.02", "fed1f511d51613df108101b8a09397beebc70f0c": "1.02",
    "855ac7a96de3e21587fd01e458baeb53c488fa71": "1.00", "c8b4c0c0c2485246c5373e7445af12d9c4f639a7": "1.00",
    "783e53a7ca38aaa5da74bbd32b00e1891020f86a": "1.00", "d81e699fac808ebd4a1689c108b9a75571c3d62b": "1.02",
    "5c6e20a2296de593635c585c941e2455b10d7c5f": "1.02", "6b66880c4ad373915f939af62194a71d3b56800d": "1.02",
}
SHADER_INDEXES = {
    ("CUSA02343", "1.00"): "shader_locations_CUSA02343.txt",
    ("CUSA02343", "1.02"): "shader_locations_CUSA02343_102.txt",
    ("CUSA02320", "1.00"): "shader_locations_CUSA02320_100.txt",
    ("CUSA02320", "1.02"): "shader_locations_CUSA02320.txt",
    ("CUSA02344", "1.02"): "shader_locations_CUSA02344.txt",
    ("CUSA02826", "1.02"): "shader_locations_CUSA02826.txt",
}
# Render sizes the engine accepts (engine/launcher): about 3440 x 1440 at most, 4K for the 4K choices.
RENDER_PIXELS_MAX = 3440 * 1440
RENDER_PIXELS_MAX_BIG = 3840 * 2160
TEMPORAL_UPSCALERS = ("fsr3", "fsr4", "fsr411", "dlss", "xess")
# The engine's mouse turns the camera 0.15 degrees per pixel at sensitivity 1; the old one about 0.063.
MOUSE_SENSITIVITY_SCALE = 0.42
# Our cheats (launcher names) that the engine's scripts/cheats.py applies, by its names.
CHEAT_NAMES = {"invincible": "health", "ammo": "ammo", "devmode": "devmode", "rewards": "rewards",
               "grenades": "grenades"}
# Unlock all rewards in Uncharted 2 and 3: Naughty Dog's debug switches "Give all Store Items" and "Give All Movies"
# (update 1.02 image offsets), kept set by the engine (BB_POKE, per game through run.py's BB_POKE_U2/U3).
REWARD_POKES = {"u2": "1114178:b=1,1114179:b=1", "u3": "17b2a94:b=1,17b2a95:b=1"}
# Infinite grenades: Uncharted 3's own debug switch "Infinite Grenades" (1.02 image offset), kept set the same way.
# Uncharted 1 and 2 have no such switch: their throw's ammo use is patched out (engine/scripts/cheats.py).
GRENADE_POKES = {"u3": "17faa92:b=1"}
# The games' other debug switches the launcher offers (1.02 image offsets, kept set the same way): "No Reload"
# (Uncharted 2 and 3), "One Hit Kills" (Uncharted 3) and the render setting "hi-res local (lamp / torch) shadow
# buffer" (Uncharted 2 and 3, PS4 default off, ~0% FPS; U1 not mapped).
CHEAT_POKES = {"rewards": REWARD_POKES, "grenades": GRENADE_POKES,
               "noreload": {"u2": "104f84b:b=1", "u3": "17faa93:b=1"}, "onehit": {"u3": "17fab94:b=1"}}
# The same cheats where a game has no such switch: code patches of engine/scripts/cheats.py (its names), per game.
# No reload in Uncharted 1 (the player's shot no longer takes a round from the magazine), one hit kills in
# Uncharted 1 and 2 (Nate's hit on an NPC does 100000 damage).
CHEAT_PATCHES = {"noreload": ("u1",), "onehit": ("u1", "u2")}
HIRES_SHADOW_POKES = {"u2": "1247d04:b=1", "u3": "18c6444:b=1"}
# Mouse button names: the settings file's (GOW3_MOUSE_MAP) to the engine's input.ini names.
MOUSE_NAMES = {"left": "Mouse Left", "right": "Mouse Right", "middle": "Mouse Middle", "x1": "Mouse 4",
               "x2": "Mouse 5", "wheel_up": "Wheel Up", "wheel_down": "Wheel Down"}
# The engine's input.ini actions: buttons (keys and controller) and the stick directions (keys only).
BUTTON_ACTIONS = ("cross", "circle", "square", "triangle", "l1", "r1", "l2", "r2", "l3", "r3", "options",
                  "touchpad", "touchpad_right", "up", "down", "left", "right")
STICK_ACTIONS = ("ls_up", "ls_down", "ls_left", "ls_right", "rs_up", "rs_down", "rs_left", "rs_right")
# The controller buttons of each action as the launcher's defaults name them (SDL names).
PAD_DEFAULTS = {"cross": "a", "circle": "b", "square": "x", "triangle": "y", "l1": "leftshoulder",
                "r1": "rightshoulder", "l3": "leftstick", "r3": "rightstick", "options": "start",
                "touchpad_right": "back", "up": "dpup", "down": "dpdown", "left": "dpleft", "right": "dpright"}
# Job objects: a game that restarts itself stays in the job, and the job ends with this script.
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


# -- settings --------------------------------------------------------------------------------

def read_ini(path):
    values = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def merge_ini(path, updates, header):
    """Updates keys in place and keeps every other line (the in-game menu writes the file too)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = [header]
    done = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}"
                done.add(key)
    lines += [f"{key}={value}" for key, value in updates.items() if key not in done]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def env_flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "on", "yes", "true")


def parse_map(spec):
    """The settings file's map syntax (action=name,action=name,...; "action=" = none)."""
    entries = []
    for entry in (spec or "").split(","):
        action, eq, name = entry.partition("=")
        if eq:
            entries.append((action.strip(), name.strip()))
    return entries


def write_input_ini(game, ini, path):
    """input-u<N>.ini for the engine from the game's settings file: every action is listed, so none of
    the engine's own defaults (C for Circle, G for R1, IJKL for the right stick) stays behind."""
    binds = {action: [] for action in BUTTON_ACTIONS + STICK_ACTIONS}
    for action, name in parse_map(ini.get("key_map", "")):
        if action == "touchpad_left":
            action = "touchpad"
        if action in binds and name:
            binds[action].append(name)
    for action, name in parse_map(ini.get("mouse_map", "")):
        if action == "touchpad_left":
            action = "touchpad"
        if action in binds and name and MOUSE_NAMES.get(name):
            binds[action].append(MOUSE_NAMES[name])
    pad = dict(PAD_DEFAULTS)
    replaced = set()
    for action, name in parse_map(ini.get("pad_map", "")):
        if action == "touchpad_left":
            continue  # the left side of the touchpad had a fixed combo; the engine has none for it
        if action in pad and action not in replaced:
            replaced.add(action)
            pad[action] = name
    try:
        sensitivity = float(ini.get("mouse_sens", "1.0")) * MOUSE_SENSITIVITY_SCALE
    except ValueError:
        sensitivity = MOUSE_SENSITIVITY_SCALE
    lines = [f"# {game}: controls written by the launcher at each start (its Controls page)",
             f"mouse_look={1 if ini.get('mouse', '1') != '0' else 0}",
             f"mouse_sensitivity={sensitivity:.3f}",
             f"mouse_invert_y={1 if ini.get('mouse_invert', '0') == '1' else 0}",
             "pad_invert_y=0",
             f"pad_vibration={1 if ini.get('vibration', '1') != '0' else 0}",
             "pad_vibration_strength=100"]
    # The in-game menu's controller shortcut (the launcher's Advanced page): L2 + R3 as before, or the
    # engine's own L3 + R3 (always on), or none but the keyboard's Insert.
    if ini.get("menu_shortcut", "lt_r3") == "lt_r3":
        lines.append("menu_pad=lefttrigger+rightstick")
    # Without a settings file yet (a first start before the launcher wrote one) the engine's own
    # defaults stay; with one, every action is written, bound or not.
    if "key_map" in ini or "mouse_map" in ini:
        lines += [f"key.{action}={'|'.join(binds[action][:2])}" for action in BUTTON_ACTIONS + STICK_ACTIONS]
    if "pad_map" in ini:
        # No controller button for the left side of the touchpad (it was L1+Back): Back stays the right side.
        lines += ["pad.touchpad=none"]
        lines += [f"pad.{action}={pad.get(action) or 'none'}" for action in PAD_DEFAULTS]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fps_limit(ini):
    try:
        value = int(float(ini.get("fps_limit", "60")))
    except ValueError:
        return 60
    return max(20, min(value, 240))


def render_sizes(game):
    """(BB_RENDER_RES, BB_OUTPUT_RES) from the launcher's UNCHARTED_RESOLUTION_<G> (what the game draws)
    and UNCHARTED_OUTPUT_RES_<G> (what it is upscaled to), or None for the game's own 1920 x 1080.
    Widths in steps of 16 and heights in steps of 32 (the game asserts the first; its bloom chain needs
    the second), as the engine's own launcher rounds them."""
    render = os.environ.get(f"UNCHARTED_RESOLUTION_{game.upper()}", "").strip()
    output = os.environ.get(f"UNCHARTED_OUTPUT_RES_{game.upper()}", "").strip()
    try:
        width, height = (int(v) for v in render.lower().split("x"))
    except ValueError:
        return None
    try:
        out_w, out_h = (int(v) for v in output.lower().split("x"))
    except ValueError:
        out_w, out_h = width, height
    limit = RENDER_PIXELS_MAX_BIG if out_h >= 2160 or height >= 2160 else RENDER_PIXELS_MAX
    if width * height > limit:
        shrink = (limit / (width * height)) ** 0.5
        width, height = width * shrink, height * shrink
    height = 1080 if abs(height - 1080) < 16 else max(32, int(round(height / 32)) * 32)
    width = int(width) // 16 * 16
    if width < 640 or height < 360 or (width, height, out_w, out_h) == (1920, 1080, 1920, 1080):
        return None
    return f"{width}x{height}", f"{out_w}x{out_h}"


def host_hardware_threads():
    if os.name == "nt":
        process, system = ctypes.c_size_t(), ctypes.c_size_t()
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        if kernel32.GetProcessAffinityMask(ctypes.c_void_p(kernel32.GetCurrentProcess()),
                                           ctypes.byref(process), ctypes.byref(system)) and process.value:
            return bin(process.value).count("1")
    return os.cpu_count() or 8


def job_sleep(game):
    """BB_JOB_SLEEP: the launcher's Idle game threads choice (UNCHARTED_JOB_SLEEP on|off|auto). auto:
    Spin in Drake's Fortune from 8 hardware threads (its camera is even then), Sleep otherwise."""
    value = os.environ.get("UNCHARTED_JOB_SLEEP", "auto").strip().lower()
    if value in ("0", "off", "no", "spin"):
        return "0"
    if value == "auto":
        return "0" if game == "u1" and host_hardware_threads() >= 8 else "1"
    return "1"


def executable_hash(path):
    """SHA-1 of the game code an executable loads (its segments when it is a signed executable)."""
    import hashlib
    import struct
    digest = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            head = f.read(0x20)
            if head[:4] == b"\x4f\x15\x3d\x1d" and len(head) == 0x20:
                count, = struct.unpack_from("<H", head, 0x18)
                entries = [struct.unpack("<QQQQ", f.read(32)) for _ in range(count)]
                for props, offset, size, _memsz in entries:
                    if props & 0x800:
                        f.seek(offset)
                        digest.update(f.read(size))
            else:
                f.seek(0)
                for block in iter(lambda: f.read(1 << 20), b""):
                    digest.update(block)
    except (OSError, struct.error):
        return ""
    return digest.hexdigest()


def title_id(game_dir):
    try:
        sys.path.insert(0, str(ENGINE / "scripts"))
        from prepare import sfo
        return str(sfo((game_dir / "sce_sys" / "param.sfo").read_bytes()).get("TITLE_ID", ""))
    except Exception:
        return ""
    finally:
        sys.path.pop(0)


def shader_environment(env, game, game_dir, executable):
    """The shader preparation lists: the game builds its shaders once, before play (a full-screen page),
    instead of stuttering through them. Without the location index of this copy's title and build the
    first preparation would read every game file, so a copy without one gets no page."""
    lists = ENGINE / "shaders" / f"{game}_variants.txt"
    if not lists.is_file():
        return
    code = GAME_CODE.get(executable_hash(game_dir / executable), "")
    index = SHADER_INDEXES.get((title_id(game_dir), code))
    if not index or not lists.with_name(index).is_file():
        print(f"Shader preparation: no shader index for this copy ({title_id(game_dir) or '?'}, "
              f"{code or 'unknown build'}); shaders are built while playing")
        return
    env["BB_VARIANT_SHIP"] = str(lists)
    env["BB_SHADER_LOCATIONS"] = str(lists.with_name(index))
    for name, variable in ((f"{game}_keys.txt", "BB_KEY_LIST"), (f"tiling_pipelines_{game}.txt", "BB_TILING_LIST"),
                           (f"{game}_compute_keys.txt", "BB_COMPUTE_LIST")):
        if lists.with_name(name).is_file():
            env[variable] = str(lists.with_name(name))


def language_text_file(game_dir, game, language):
    """The text file holding the launcher's language for this game in this copy, or None (the game's own choice)."""
    try:
        held = cached_text_languages(game_dir, game, USER / "text-languages.json")
    except Exception as error:  # a damaged archive never keeps the game from starting
        print(f"Languages: {game}: the texts could not be read ({error}); the game's own language is used")
        return None
    code = LANGUAGE_IDS.get(language)
    found = held.get(code) if code else None
    if language == "ar":
        if found:
            print(f"Arabic: {game}: the translation is text file {found}")
        else:
            print(f"Arabic: {game}: no Arabic translation in this copy (install it with Install from .pkg); English is used")
            found = held.get("en-US") or held.get("en-GB")
    return found


TREASURES_FILE = USER / "treasures-given.json"  # "u1:<player>" -> when the Give all treasures cheat gave them


def treasure_key(game):
    profile = os.environ.get(f"UNCHARTED_SAVE_PROFILE_{game.upper()}", "1")
    return f"{game}:{profile}"


def treasures_given():
    try:
        return json.loads(TREASURES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def note_treasures_given(game):
    """The engine gave this game's treasures to the current player: not again (treasure_key)."""
    if not game:
        return
    given = treasures_given()
    given[treasure_key(game)] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        TREASURES_FILE.write_text(json.dumps(given, indent=2), encoding="utf-8")
    except OSError as error:
        print(f"Treasures: could not note the gift ({error})")


def game_environment(args, game, executable, game_dir):
    """The engine's environment from the launcher's: BB_* from UNCHARTED_*/GOW3_* and probe-u<N>.ini."""
    ini = read_ini(USER / f"probe-{game}.ini")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["BB_EXE"] = game
    env["BB_GAME_DIR"] = str(game_dir)
    env["BB_DATA_DIR"] = str(ROOT / "analysis")
    env["BB_USER_DIR"] = str(USER)
    env.setdefault("BB_GPU_CACHE_DIR", str(USER / "cache"))
    env["BB_CONFIG"] = str(USER / f"bbport-{game}.ini")
    # A profiling build (BB_PGO=generate) rewrites its counts every 30 s: one file per game process (%p), each
    # write replacing the last. Without it clang's default name (default_%m) adds every write to the file again
    # and the counts overflow. Read by nothing else.
    env.setdefault("LLVM_PROFILE_FILE", str(ENGINE / "pgo-runs" / "run-%p.profraw"))
    env["BB_INPUT_CONFIG"] = str(USER / f"input-{game}.ini")
    if executable == "eboot.bin" and not args.collection_menu:
        env["BB_SKIP_COLLECTION_MENU"] = "1"
    else:
        env.pop("BB_SKIP_COLLECTION_MENU", None)
    # Window and presentation.
    display = ini.get("display_mode", "windowed")
    sizes = render_sizes(game)
    output = sizes[1] if sizes else "1920x1080"
    env["BB_FULLSCREEN"] = "0" if display == "windowed" else "1"
    if display == "windowed":
        env["BB_WINDOW_SIZE"] = output
    else:
        env.pop("BB_WINDOW_SIZE", None)
    env["BB_PRESENT_MODE"] = "Fifo" if ini.get("vsync", "1") != "0" else "Mailbox"
    limit = fps_limit(ini)
    if limit < 60:
        env["BB_VBLANK_HZ"], env["BB_FPS_LIMIT"] = "60", str(limit)
    else:
        env["BB_VBLANK_HZ"] = str(limit)
        env.pop("BB_FPS_LIMIT", None)
    env["BB_FRAMES_AHEAD"] = ini.get("frames_queued", "1") if ini.get("frames_queued", "1") in ("0", "1", "2") else "1"
    # Picture: the upscaler (and its anti-aliasing) is given every start, as the engine's own launcher does;
    # the in-game menu's changes last for the session.
    upscaler = ini.get("upscaler", "off").lower()
    if upscaler in TEMPORAL_UPSCALERS or upscaler == "taa":
        env["BB_UPSCALER"] = upscaler
    else:
        env["BB_UPSCALER"] = "off"
    env["BB_FSR1"] = "1" if upscaler not in TEMPORAL_UPSCALERS and ini.get("fsr1", "0") == "1" else "0"
    # Frame generation (the Display page): FSR 3's on any card; one generated frame per drawn one.
    env["BB_FRAME_GEN"] = "fsr3" if ini.get("frame_gen", "off") == "fsr3" else "off"
    env["BB_FRAME_GEN_MULTIPLIER"] = "2"
    if sizes:
        env["BB_RENDER_RES"], env["BB_OUTPUT_RES"] = sizes
    else:
        env.pop("BB_RENDER_RES", None)
        env.pop("BB_OUTPUT_RES", None)
    env["BB_ULTRAWIDE"] = "auto"
    env["BB_RCAS"] = "1" if ini.get("rcas", "1") != "0" else "0"
    try:  # the old setting: 0..100 %, attenuation 2 * (1 - s / 100); the engine's: 0..1000 thousandths
        strength = float(ini.get("rcas_strength", "75"))
    except ValueError:
        strength = 75.0
    env["BB_RCAS_ATTENUATION"] = str(int(max(0.0, min(1000.0, 2000.0 * (1.0 - strength / 100.0)))))
    # El Dorado's performance counter: the items, corner, size, background and layout of the Display page.
    items = 0
    for bit, key in enumerate(("overlay_fps", "overlay_frametime", "overlay_upscaler", "overlay_gpu", "overlay_cpu",
                               "overlay_ram", "overlay_vram")):
        if ini.get(key, "1") != "0":
            items |= 1 << bit
    env["BB_OVERLAY_ITEMS"] = str(items if ini.get("show_fps", "1") != "0" else 0)
    for key, name, default in (("overlay_corner", "BB_OVERLAY_CORNER", "1"), ("overlay_scale", "BB_OVERLAY_SCALE", "100"),
                               ("overlay_opacity", "BB_OVERLAY_OPACITY", "50"), ("overlay_layout", "BB_OVERLAY_LAYOUT", "0")):
        value = ini.get(key, default)
        env[name] = value if value.isdigit() else default
    merge_ini(USER / f"bbport-{game}.ini", {"show_fps": "1" if ini.get("show_fps", "1") != "0" else "0"},
              "# El Dorado: this game's in-game menu settings (in-game menu: Insert / L3+R3)")
    # Game options.
    # Each game its own language (the launcher's UNCHARTED_LANGUAGE_U1/U2/U3; run.py picks the one of the game it
    # starts, also after a switch from the Collection menu), else the shared UNCHARTED_LANGUAGE.
    shared = os.environ.get("UNCHARTED_LANGUAGE", "1")
    arabic_cheats = []  # games set to Arabic: the patch that loads the translation's text file (cheats.py text<n>)
    for key in GAME_KEYS.values():
        language = os.environ.get(f"UNCHARTED_LANGUAGE_{key.upper()}", shared)
        # The text file of the chosen language in this copy, read from the files themselves: the game then shows
        # that language whatever its own table or its main menu (Square) would pick, and a translation is the
        # language of the file it took (tools/text_languages.py).
        text_file = language_text_file(game_dir, key, language)
        if text_file:
            arabic_cheats.append(f"{key}:text{text_file}")
        env[f"BB_LANGUAGE_{key.upper()}"] = language if language.isdigit() else "1"
    env["BB_LANGUAGE"] = env[f"BB_LANGUAGE_{game.upper()}"]
    # Each game's loading icon for its window and taskbar button: taken by the engine from the game's first loading
    # screen into this file, used from then on (bbport_loading_icon.h; run.py picks the started game's).
    for key in GAME_KEYS.values():
        env[f"BB_LOADING_ICON_{key.upper()}"] = str(USER / "icons" / f"loading-{key}.png")
        # Until then El Dorado's own drawing of it (tools/draw_loading_icons.py).
        env[f"BB_LOADING_ICON_DEFAULT_{key.upper()}"] = str(ROOT / "launcher" / "assets" / "loading" / f"{key}.png")
    (USER / "icons").mkdir(parents=True, exist_ok=True)
    anisotropy = os.environ.get("UNCHARTED_ANISOTROPY", "0")
    if anisotropy in ("2", "4", "8", "16"):
        env["BB_ANISO"] = anisotropy
    if env_flag("UNCHARTED_NO_DOF"):
        env["BB_DOF"] = "0"
    if env_flag("UNCHARTED_UNLOCK"):
        env["BB_UNLOCK_CHAPTERS"] = "1"
    env["BB_OFFLINE_NPID"] = "1"
    # The launcher's language for the engine's own texts (close question, save list, loading screen); the engine
    # shows English for one it lacks.
    env["BB_UI_LANGUAGE"] = os.environ.get("UNCHARTED_UI_LANGUAGE", "en") or "en"
    env["BB_FREEZE_DUMP_SECONDS"] = "30"
    env["BB_BUTTON_PROMPTS"] = ini.get("prompts", "auto") if ini.get("prompts", "auto") in ("auto", "keyboard", "playstation", "xbox") else "auto"
    try:
        aim = float(ini.get("mouse_aim_sens", "1.0"))
        if abs(aim - 1.0) > 0.005:
            env["BB_AIM_SCALE"] = f"{aim:g}"
    except ValueError:
        pass
    cheats = [c.strip() for c in os.environ.get("UNCHARTED_CHEATS", "").split(",") if c.strip()]
    # Code patches of the launcher's options (engine/scripts/cheats.py, 1.02 code only; it skips any other build):
    # Uncharted 2's torch light along the torch (on unless UNCHARTED_TORCH_FORWARD=0), Uncharted 3's exposure.
    option_cheats = [] if os.environ.get("UNCHARTED_TORCH_FORWARD", "1") == "0" else ["u2:torch"]
    try:
        exposure = max(-2.0, min(1.0, float(os.environ.get("UNCHARTED_U3_EXPOSURE", "0").strip() or 0)))
    except ValueError:
        exposure = 0.0
    if abs(exposure) >= 0.05:
        option_cheats.append(f"u3:exposure{exposure:+.2f}")
    # Damage to Nate as on difficulty 0 Explorer / 1 Easy / 2 Normal / 3 Hard (cheats.py nathealth<L>); unset: the chosen one's.
    nate = os.environ.get("UNCHARTED_NATE_DAMAGE", "").strip()
    if nate in ("0", "1", "2", "3"):
        option_cheats += [f"{g}:nathealth{nate}" for g in ("u1", "u2", "u3")]
    env["BB_CHEATS"] = ",".join([f"{g}:{CHEAT_NAMES[c]}" for g in ("u1", "u2", "u3") for c in cheats if c in CHEAT_NAMES]
                                + [f"{g}:{c}" for c in cheats for g in CHEAT_PATCHES.get(c, ())]
                                + option_cheats + arabic_cheats)
    if "devmode" in cheats:
        env["BB_DEV_MENU"] = "1"
    if "treasures" in cheats:  # the games' own Dev Menu "Give all Treasures" (runtime_checkpoint.c)
        # Once per game and player: given, the treasures are in that player's saves; given again, the game showed
        # its "all treasures found" message at every start.
        due = [key for key in GAME_KEYS.values() if treasure_key(key) not in treasures_given()]
        if due:
            env["BB_GIVE_TREASURES"] = ",".join(due)
        else:
            env.pop("BB_GIVE_TREASURES", None)
    pokes = {}
    for name, table in CHEAT_POKES.items():
        if name in cheats:
            for key, value in table.items():
                pokes.setdefault(key, []).append(value)
    if env_flag("UNCHARTED_HIRES_SHADOWS"):
        for key, value in HIRES_SHADOW_POKES.items():
            pokes.setdefault(key, []).append(value)
    # The offsets are update 1.02's: a game of another build gets none (a write there would hit other data).
    for key, values in pokes.items():
        executable = next(name for name, game_key in GAME_KEYS.items() if game_key == key)
        if GAME_CODE.get(executable_hash(game_dir / executable)) == "1.02":
            env[f"BB_POKE_{key.upper()}"] = ",".join(values)
        else:
            print(f"Cheats: {key}: memory switches need update 1.02 of the game (not used)")
    # Skip intro (the launcher's cheat, on by default): the boot logo movie of all three games (runtime_file.c).
    if "skipintro" in cheats:
        env.setdefault("BB_SKIP_INTRO", "1")
    env["BB_JOB_SLEEP"] = job_sleep(game)
    # U3 characters sinking into the ground, floating or twitching (SuperMedo dca99bb): what the raycaster
    # copy shader writes is read back at the end-of-pipe label. On in Uncharted 3 unless already set;
    # the _AUTO mark lets run.py turn it off again when the collection switches to another game.
    if "BB_COPY64_EOP_READBACK" not in env and game == "u3":
        env["BB_COPY64_EOP_READBACK"] = "1"
        env["BB_COPY64_EOP_READBACK_AUTO"] = "1"
    # Multithreaded rendering (the launcher's default: on): on or off as the launcher says; the engine's own
    # choice (on from 8 hardware threads) only when the launcher says nothing.
    if os.environ.get(f"UNCHARTED_MULTITHREADED_{game.upper()}") == "1":
        env["BB_DRAW_PIPE"] = "1"
    elif os.environ.get(f"UNCHARTED_MULTITHREADED_{game.upper()}") in ("0", "force-off"):
        env["BB_DRAW_PIPE"] = "0"
    profile = os.environ.get(f"UNCHARTED_SAVE_PROFILE_{game.upper()}", "1")
    env[f"BB_USER_ID_{game.upper()}"] = profile if profile.isdigit() and 1 <= int(profile) <= 16 else "1"
    # Straight to the game's main menu: the engine taps through the title page ("Press ... to begin") and stops at
    # the first menu (runtime_menu_watch.c). Not with the collection menu first (its taps would pick a game there);
    # a game the collection menu switches to gets it from run.py.
    collection_menu = executable == "eboot.bin" and args.collection_menu
    if not collection_menu:
        env["BB_SKIP_TITLE"] = "1"
    else:
        env.pop("BB_SKIP_TITLE", None)
    # The launcher's STOP: it writes this file and the game closes the usual way, keeping the shader cache's last
    # writes (gpu/shim/window.cpp); the launcher ends it itself when that takes too long.
    env["BB_STOP_FILE"] = str(STOP_FILE)
    # The launcher's Prepare shaders: no window and no game, the progress as PREP lines (the engine's
    # BB_PREPARE_ONLY); the same cache and lists as a start.
    if env_flag("UNCHARTED_PREPARE_ONLY", "0"):
        env["BB_PREPARE_ONLY"] = "1"
        env.pop("BB_SKIP_TITLE", None)
    if env_flag("UNCHARTED_DIAGNOSTICS", "1"):
        env["BB_FRAME_STATS"] = "1"
    # Scripted input (tools/drive_game.py) only when asked: the engine then ignores the keyboard and the pad.
    if env_flag("UNCHARTED_PAD_FILE"):
        env.setdefault("BB_PAD_FILE", str(USER / "probe-pad.txt"))
    shader_environment(env, game, game_dir, executable)
    write_input_ini(game, ini, USER / f"input-{game}.ini")
    # A developer's test-env.txt beside the settings: NAME=value lines that win over everything above.
    for line in read_ini(USER / "test-env.txt").items():
        env[line[0]] = line[1]
    return env


# -- running ---------------------------------------------------------------------------------

class GameJob:
    """A Windows job the game's processes live in: it ends when this script ends (STOP from the launcher,
    or a crash of the script), restarts of the game included."""

    def __init__(self):
        self.handle = None
        if os.name != "nt":
            return
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class BasicLimits(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
                        ("SchedulingClass", ctypes.c_uint32)]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(ctypes.c_void_p(handle), JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                         ctypes.byref(limits), ctypes.sizeof(limits))
        self.handle = handle

    def assign(self, process):
        if self.handle:
            ctypes.windll.kernel32.AssignProcessToJobObject(ctypes.c_void_p(self.handle), ctypes.c_void_p(process._handle))

    def terminate(self):
        if self.handle:
            ctypes.windll.kernel32.TerminateJobObject(ctypes.c_void_p(self.handle), 1)


def python_executable():
    python = Path(sys.executable)
    if python.name.lower() == "pythonw.exe" and python.with_name("python.exe").exists():
        python = python.with_name("python.exe")
    return str(python)


BACKUP_KEEP = 5  # copies kept of each save
GAME_SAVE = re.compile(r"SAVEDATA0[123][0-9]$")


def save_signature(folder, meta):
    """Names, sizes and times of a save's files: a backup is made only when this changed."""
    parts = []
    for base in (folder, meta):
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    stat = path.stat()
                    parts.append(f"{path.relative_to(base.parent).as_posix()}:{stat.st_size}:{stat.st_mtime_ns}")
    return "\n".join(parts)


def back_up_saves():
    """Before each start: a copy of every game save that changed since its last copy, in
    analysis/uncharted-user/savedata-backups/<user>/<title>/<dir>-<YYYYmmdd-HHMMSS>/ (the same layout
    as savedata-deleted, so the launcher lists and restores them alike); the newest BACKUP_KEEP are kept.
    Never stops the game from starting."""
    saves = USER / "savedata"
    if not saves.is_dir():
        return
    made = 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for profile in saves.iterdir():
        if not profile.is_dir():
            continue
        for title in profile.iterdir():
            if not title.is_dir() or title.name.startswith(".") or "." in title.name:
                continue
            for folder in title.iterdir():
                if not folder.is_dir() or not GAME_SAVE.match(folder.name):
                    continue
                meta = title / f"{folder.name}.sce_sys"
                try:
                    signature = save_signature(folder, meta)
                    if not signature:
                        continue
                    root = USER / "savedata-backups" / profile.name / title.name
                    copies = sorted((p for p in root.glob(f"{folder.name}-*") if p.is_dir()), reverse=True) \
                        if root.is_dir() else []
                    last = copies[0] / "signature.txt" if copies else None
                    if last and last.is_file() and last.read_text(encoding="utf-8") == signature:
                        continue
                    target = root / f"{folder.name}-{stamp}"
                    if target.exists():
                        continue
                    work = root / f".{folder.name}-{stamp}.part"
                    shutil.rmtree(work, ignore_errors=True)
                    shutil.copytree(folder, work / folder.name)
                    if meta.is_dir():
                        shutil.copytree(meta, work / meta.name)
                    (work / "signature.txt").write_text(signature, encoding="utf-8")
                    work.rename(target)
                    made += 1
                    for old in ([target] + copies)[BACKUP_KEEP:]:
                        shutil.rmtree(old, ignore_errors=True)
                except OSError as error:
                    print(f"Save backup: {folder.name} skipped ({error})")
    if made:
        print(f"Save backup: {made} save{'s' if made != 1 else ''} copied to {USER / 'savedata-backups'}")


# Which version of the game wrote a save (<dir>.sce_sys/<this file>, "01.03"): a save made with a newer update than
# the copy now chosen does not load in the game, and the launcher leaves it out (launcher/core/saves.py).
SAVE_VERSION_FILE = "eldorado-game-version.txt"


def game_version(game_dir):
    """APP_VER of the game as it runs (the update's when it is laid over the game), "" when unreadable."""
    try:
        sys.path.insert(0, str(ENGINE / "scripts"))
        from prepare import sfo
        return str(sfo((game_dir / "sce_sys" / "param.sfo").read_bytes()).get("APP_VER", ""))
    except Exception:
        return ""
    finally:
        sys.path.pop(0)


def stamp_saves(since, version):
    """After a run: every game save written during it records the game version that wrote it."""
    saves = USER / "savedata"
    if not version or not saves.is_dir():
        return
    for meta in saves.glob("*/*/SAVEDATA0*.sce_sys"):
        try:
            param = meta / "param.bin"
            if GAME_SAVE.match(meta.name[:-len(".sce_sys")]) and param.is_file() and param.stat().st_mtime >= since:
                (meta / SAVE_VERSION_FILE).write_text(version, encoding="utf-8")
        except OSError as error:
            print(f"Save version: {meta.name} not marked ({error})")


STATS = USER / "eldorado-stats.json"
FRAME_STATS = re.compile(r"^Frame stats: ([0-9.]+) FPS.*?, ([0-9]+) draws/frame")
# The share of time the game waited for the graphics card (high: the card is the limit).
GPU_WAIT = re.compile(r"GPU ticks ([0-9.]+)%")


class PlayStats:
    """Play time, last play and the average FPS of each game, for the launcher's home screen:
    analysis/uncharted-user/eldorado-stats.json {"u1": {"seconds", "sessions", "last", "fps_sum",
    "fps_count"}, ...}. The FPS is the engine's "Frame stats" lines (about every 5 s) taken in play
    (scenes of 200 draws or more: not the menus, which run at the display rate)."""

    def __init__(self, game):
        self.game, self.since = game, time.time()
        self.data = {}

    def line(self, line):
        match = FRAME_STATS.match(line)
        if match and int(match.group(2)) >= 200:
            entry = self.data.setdefault(self.game, {"seconds": 0.0, "fps_sum": 0.0, "fps_count": 0})
            entry["fps_sum"] += float(match.group(1))
            entry["fps_count"] += 1
            wait = GPU_WAIT.search(line)
            entry["gpu_wait_sum"] = entry.get("gpu_wait_sum", 0.0) + (float(wait.group(1)) if wait else 0.0)

    def switch(self, game):
        self.close()
        self.game, self.since = game, time.time()

    def close(self):
        if self.game:
            entry = self.data.setdefault(self.game, {"seconds": 0.0, "fps_sum": 0.0, "fps_count": 0})
            entry["seconds"] += max(0.0, time.time() - self.since)
            entry["last"] = int(time.time())
        self.game = None

    def save(self):
        self.close()
        try:
            stats = json.loads(STATS.read_text(encoding="utf-8"))
            if not isinstance(stats, dict):
                stats = {}
        except (OSError, ValueError):
            stats = {}
        for game, entry in self.data.items():
            if entry["seconds"] < 20 and not entry["fps_count"]:
                continue  # a start that never got going
            total = stats.setdefault(game, {})
            total["seconds"] = int(total.get("seconds", 0) + entry["seconds"])
            total["sessions"] = int(total.get("sessions", 0)) + 1
            total["last"] = entry.get("last", int(time.time()))
            total["fps_sum"] = round(float(total.get("fps_sum", 0.0)) + entry["fps_sum"], 1)
            total["fps_count"] = int(total.get("fps_count", 0)) + entry["fps_count"]
            # This session alone (the launcher's frame rate advice, launcher/core/fps_advice.py).
            total["session_fps"] = round(entry["fps_sum"] / entry["fps_count"], 1) if entry["fps_count"] else 0.0
            total["session_samples"] = entry["fps_count"]
            total["session_gpu_wait"] = round(entry.get("gpu_wait_sum", 0.0) / entry["fps_count"], 1) \
                if entry["fps_count"] else 0.0
            total["session_end"] = int(time.time())
        try:
            work = STATS.with_suffix(".tmp")
            work.write_text(json.dumps(stats, indent=2), encoding="utf-8")
            os.replace(work, STATS)
        except OSError as error:
            print(f"Play stats: not saved ({error})")


def _trophy_unlock_id(line):
    """The trophy number of an unlock line ("<number> <time>"), or None for a broken line."""
    part = line.split()
    return part[0] if len(part) >= 2 and part[0].isdigit() and part[1].isdigit() else None


def migrate_trophy_logs(user=None):
    """The old engine kept unlocks in trophy/trophy0N.txt; this one in trophy/<NP id>.log (same "id time"
    lines): the old ones are merged in once, one line per trophy (the old file is renamed *.migrated).
    Same rules as launcher/core/trophies.py migrate_old_logs()."""
    user = user or USER
    ids = {"trophy01.txt": "NPWR09798_00", "trophy02.txt": "NPWR09799_00", "trophy03.txt": "NPWR09801_00"}
    for old_name, npcommid in ids.items():
        old = user / "trophy" / old_name
        if not old.is_file():
            continue
        try:
            new = user / "trophy" / f"{npcommid}.log"
            have = new.read_text(encoding="utf-8", errors="replace") if new.is_file() else ""
            seen = {_trophy_unlock_id(line) for line in have.splitlines()} - {None}
            lines = []
            for line in old.read_text(encoding="utf-8", errors="replace").splitlines():
                number = _trophy_unlock_id(line)
                if number is not None and number not in seen:
                    seen.add(number)
                    lines.append(line.strip())
            if lines:
                with new.open("a", encoding="utf-8", newline="\n") as log:
                    if have and not have.endswith("\n"):
                        log.write("\n")
                    log.write("\n".join(lines) + "\n")
            old.rename(old.with_name(old_name + ".migrated"))
            print(f"Trophies: {len(lines)} unlocks of {old_name} moved to {new.name}")
        except OSError as error:
            print(f"Trophies: {old_name} not moved ({error})")


def run(args, game, executable, game_dir):
    out = ROOT / "analysis" / LOG_DIRS[game]
    out.mkdir(parents=True, exist_ok=True)
    env = game_environment(args, game, executable, game_dir)
    command = [python_executable(), "-u", str(ENGINE / "run.py")]
    result = {"executable": executable, "command": command, "guest_execution_requested": args.boot,
              "timeout_seconds": args.seconds}
    log_path = out / "boot.log"
    started = time.monotonic()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the launcher reads the pipe as UTF-8
    print(f"El Dorado: starting {executable} from {game_dir}")
    print(f"Log: {log_path}", flush=True)
    job = GameJob()
    with log_path.open("wb") as log:
        header = (f"# {time.strftime('%Y-%m-%d %H:%M:%S')} {executable} ({game}) from {game_dir}\n"
                  f"# settings: {USER / ('probe-' + game + '.ini')}\n# engine: {ENGINE}\n"
                  "# language (launcher -> engine): " + ", ".join(
                      f"{key} {os.environ.get('UNCHARTED_LANGUAGE_' + key.upper(), '-')} -> "
                      f"{env.get('BB_LANGUAGE_' + key.upper(), '-')}" for key in GAME_KEYS.values())
                  + f"; cheats {env.get('BB_CHEATS', '') or 'none'}\n"
                  + ("# Straight to the main menu (BB_SKIP_TITLE=1)\n"
                     if env.get("BB_SKIP_TITLE") == "1" else "")).encode("utf-8")
        log.write(header)
        try:
            process = subprocess.Popen(command, cwd=str(ENGINE), env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
        except OSError as error:
            print(f"Could not start the game: {error}")
            return {"exit_code": 1, "timed_out": False, "elapsed_seconds": 0.0}
        job.assign(process)
        result["process_id"] = process.pid
        running = {"pid": process.pid, "runtime": str(ENGINE / "out" / "bb-probe.exe"),
                   "started_unix_ns": time.time_ns(), "active": True}
        (out / "boot.running.json").write_text(json.dumps(running, indent=2), encoding="utf-8")
        timed_out = False
        STOP_FILE.unlink(missing_ok=True)
        stats = PlayStats(game)
        presence = discord_presence.Presence(USER)
        preparing = env.get("BB_PREPARE_ONLY") == "1"  # no game is played: no presence, no play time
        if not preparing:
            presence.start(game)
        last_prep = 0.0
        deadline = started + args.seconds if args.seconds else None
        # The pipe is read to its end, not until run.py exits: a game that restarts itself ("Apply and
        # restart") starts a new run.py with the same handles, and the first run.py ends.
        for raw in iter(process.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if line.startswith("PREP "):
                if time.monotonic() - last_prep >= 1.0:  # the launcher's progress, once a second
                    last_prep = time.monotonic()
                    print(line, flush=True)
                continue
            log.write(raw.replace(b"\r\n", b"\n") if raw.endswith(b"\r\n") else raw)
            log.flush()
            print(line, flush=True)
            stats.line(line)
            if line.startswith("Treasures: Uncharted ") and line.rstrip().endswith("Give all Treasures"):
                note_treasures_given(GAME_KEYS.get({"1": "eboot.bin", "2": "big2-ps4_Shipping.elf",
                                                    "3": "big3-ps4_Shipping.elf"}.get(line[21:22], "")))
            if line.startswith("Switching to "):
                target = line[len("Switching to "):].strip()
                # The launcher's message, and the log of the game started next.
                print(f"Collection: switching to {target}", flush=True)
                stats.switch(GAME_KEYS.get(target))
                presence.switch(GAME_KEYS.get(target))
            if deadline and time.monotonic() > deadline:
                timed_out = True
                job.terminate()
                process.kill()
        code = process.wait()
    if not preparing:
        stats.save()
    presence.stop()
    job.terminate()  # nothing left: a restart chain that outlived the pipe would be a stray
    result.update(exit_code=code, timed_out=timed_out, elapsed_seconds=round(time.monotonic() - started, 3))
    running.update(active=False, exit_code=code)
    (out / "boot.running.json").write_text(json.dumps(running, indent=2), encoding="utf-8")
    (out / "boot.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    attempt = out / "attempts" / f"boot-{time.time_ns()}"
    try:
        attempt.mkdir(parents=True)
        shutil.copy2(log_path, attempt / "boot.log")
        shutil.copy2(out / "boot.json", attempt / "boot.json")
    except OSError:
        pass
    print(json.dumps(result, indent=2))
    print(f"Log: {log_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game", type=Path, default=ROOT / "game/CUSA02344/uroot")
    parser.add_argument("--analysis-root", type=Path, help="Ignored (kept for older callers)")
    parser.add_argument("--user-dir", type=Path, help="Ignored (kept for older callers)")
    parser.add_argument("--runtime-executable", type=Path, help="Run this bb-probe.exe instead of engine/out's")
    parser.add_argument("--boot", action="store_true", help="Run the game (without it: only prepare its files)")
    parser.add_argument("--executable", choices=EXECUTABLES, default="eboot.bin")
    parser.add_argument("--guest-arg", action="append", default=None, help="Ignored (the engine sets the game's argv)")
    parser.add_argument("--collection-menu", action="store_true",
                        help="Start eboot.bin with the Collection's game selection instead of Drake's Fortune")
    parser.add_argument("--cpu-only", action="store_true", help="Ignored")
    parser.add_argument("--capture", action="store_true", help="Ignored")
    parser.add_argument("--seconds", type=int, default=0, help="External process time limit; 0 disables it")
    args = parser.parse_args()
    if args.seconds < 0:
        parser.error("--seconds must be nonnegative")
    game_dir = args.game.resolve()
    if not (game_dir / "eboot.bin").is_file():
        print(f"No eboot.bin in {game_dir}: choose the game folder (the one with eboot.bin and sce_sys).")
        return 2
    if args.runtime_executable:
        os.environ["BB_PROBE"] = str(args.runtime_executable.resolve())
    if not os.environ.get("BB_PROBE") and not (ENGINE / "out" / "bb-probe.exe").is_file() \
            and not (ENGINE / "bin" / "bb-probe.exe").is_file():
        print(f"The game engine is missing: {ENGINE / 'out' / 'bb-probe.exe'} (build it with engine/build.sh "
              "or install a package).")
        return 2
    USER.mkdir(parents=True, exist_ok=True)
    game = GAME_KEYS[args.executable]
    if not args.boot:
        print("Preparation only is done by the engine at the first start; nothing to do.")
        return 0
    try:
        migrate_trophy_logs()
    except Exception as error:
        print(f"Trophies: old logs not moved ({error})")
    try:
        back_up_saves()
    except Exception as error:  # a backup problem never keeps the game from starting
        print(f"Save backup: skipped ({error})")
    try:
        game_dir = game_with_update(game_dir, ROOT / "analysis" / "views")
    except Exception as error:  # the game still starts, without its update
        print(f"Update: not used ({error})")
    started = time.time() - 2  # file times are coarse on some drives
    version = game_version(game_dir)
    result = run(args, game, args.executable, game_dir)
    stamp_saves(started, version)
    return 124 if result["timed_out"] else result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
