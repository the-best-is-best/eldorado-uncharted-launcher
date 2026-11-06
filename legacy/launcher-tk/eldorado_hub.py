# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""El Dorado: the launcher's window, made for a controller as much as for a mouse.

One window. The rail on the left (a compass emblem, the three games as I / II / III, Saves,
Settings, Logs, Quit; slim on the Settings screen) leads to three screens. Every panel, button and
picture is a plate with two cut corners:

  GAMES     the selected game over the picture of its latest save (or the game's own art), the
            expedition's coordinates, its title, where you left off and PLAY (STOP while it runs);
            the expedition log (its latest saves) along the bottom
  SAVES     the expedition log: the game's saves as a list, the selected one large on the right;
            delete one (moved to savedata-deleted, as the in-game list does) and bring deleted ones back
  SETTINGS  every page of the classic launcher (uncharted_launcher.Launcher), built inside this
            window in El Dorado's colours: Quick setup, Display, Performance, Controls (keyboard,
            mouse and controller actions), Cheats, Advanced

Every action goes through the classic launcher's own handlers (select_game, play, stop, ...), so
the settings files are written exactly as before. --classic starts the classic launcher alone.

Keys: arrows, Enter/Space, Esc/Backspace, Delete, Tab, Q/E (game), F11. Controller: D-pad, Cross (A),
Circle (B), Square (X: delete), Triangle (Y), L1/R1, Options (play). On the Settings screen the keys
and the controller belong to the pages (Controls captures them); Circle goes back, L1/R1 change page.
"""
import importlib.util
import json
import math
import os
import random
import re
import shutil
import struct
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageTk

import eldorado_icons
import game_icons

BRAND = "EL DORADO"
TAGLINE = "UNCHARTED COLLECTION LAUNCHER"
# The Collection's look: dark leather, parchment and treasure gold (each game's gold a little apart).
ACCENTS = {"u1": (222, 176, 88), "u2": (214, 166, 96), "u3": (230, 150, 74)}
INK = "#f1e6cf"
DIM = "#c2b08e"
FAINT = "#8a7a5c"
BASE = (20, 14, 9)
PARCHMENT = (233, 219, 186)
# The classic launcher's palette inside this window: its own (parchment and gold over leather).
CLASSIC_PALETTE = {}
# Journal handwriting for the photo captions (Windows 10/11 fonts).
HAND = "Ink Free"
SCREENS = (("games", "GAMES"), ("saves", "SAVES"), ("trophies", "TROPHIES"), ("gallery", "GALLERY"),
           ("settings", "SETTINGS"))
NUMERALS = {"1": "I", "2": "II", "3": "III"}
# Where each expedition goes (decoration under the title): real places of the three stories.
PLACES = {"u1": "N 08°31′   W 81°02′   ·   PANAMA COAST",
          "u2": "N 27°59′   E 86°55′   ·   HIMALAYA",
          "u3": "N 20°18′   E 52°03′   ·   RUB' AL KHALI"}
RAIL_NAV = {"saves": ("▤", "SAVES"), "trophies": ("★", "TROPHIES"), "gallery": ("▦", "GALLERY"),
            "settings": ("⚙", "SETTINGS"), "update": ("⬇", "UPDATE"),
            "logs": ("☰", "LOGS"), "quit": ("⏻", "QUIT")}
PAD_ACTIONS = {"dpleft": "left", "dpright": "right", "dpup": "up", "dpdown": "down", "a": "ok",
               "b": "back", "x": "delete", "y": "alt", "leftshoulder": "prev", "rightshoulder": "next",
               "start": "play"}
# The key each action is on, as the launcher's Button icons setting shows them.
GRADES = {"P": ("PLATINUM", "#b9d7e6"), "G": ("GOLD", "#e6c25a"), "S": ("SILVER", "#c9cdd2"),
          "B": ("BRONZE", "#c08a5a")}
HINTS = {"keyboard": {"ok": "Enter", "back": "Esc", "delete": "Del", "alt": "Tab", "down": "↓"},
         "playstation": {"ok": "✕", "back": "○", "delete": "□", "alt": "△", "down": "↓"},
         "xbox": {"ok": "A", "back": "B", "delete": "X", "alt": "Y", "down": "↓"}}
# Game saves: SAVEDATA0<game><slot>; SAVEDATA01P and 0CC are the profile and shared saves.
SAVE_DIR = re.compile(r"SAVEDATA0([123])[0-9]$")
PARAM_SIZE = 1328


# -- saves ---------------------------------------------------------------------------------

def readable(text):
    """A save's text as the list shows it: Arabic comes in presentation forms already in display
    order (Tk draws them left to right as they are) with '_' for some spaces."""
    if any("ﹰ" <= ch <= "﻿" for ch in text):
        text = text.replace("_", " ")
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def read_param(meta):
    try:
        data = (meta / "param.bin").read_bytes()
    except OSError:
        return None
    if len(data) < PARAM_SIZE:
        return None

    def field(offset, size):
        return data[offset:offset + size].split(b"\0")[0].decode("utf-8", "replace")
    mtime = struct.unpack_from("<q", data, 1288)[0]
    return {"title": field(0, 128), "subtitle": field(128, 128), "detail": field(256, 1024), "mtime": mtime}


def list_saves(user_dir, profile, game_number, deleted=False, root=None):
    """The game's saves, newest first: dicts with dir, folder, title_dir, meta, picture and texts.
    deleted: the trash layout, also used by the backups (root "savedata-backups")."""
    base = user_dir / (root or ("savedata-deleted" if deleted else "savedata")) / str(profile)
    saves = []
    if not base.is_dir():
        return saves
    for title in sorted(p for p in base.iterdir() if p.is_dir()):
        for entry in title.iterdir():
            if deleted:
                # savedata-deleted/<user>/<title>/<dir>-<time>/<dir> and <dir>.sce_sys
                inner = [p for p in entry.iterdir() if p.is_dir() and not p.name.endswith(".sce_sys")
                         and p.name != "backup"] if entry.is_dir() else []
                if not inner:
                    continue
                folder, name = entry, inner[0].name
                meta = entry / f"{name}.sce_sys"
            else:
                if not entry.is_dir() or entry.name.endswith(".sce_sys") or entry.name.startswith("."):
                    continue
                folder, name = entry, entry.name
                meta = title / f"{name}.sce_sys"
            match = SAVE_DIR.match(name)
            if not match or match.group(1) != game_number:
                continue
            param = read_param(meta)
            if not param or not param["subtitle"].strip():
                continue  # the system and profile saves
            thumb = meta / "thumb.png"
            saves.append({"dir": name, "folder": folder, "title_dir": title, "meta": meta,
                          "picture": thumb if thumb.is_file() else None,
                          "chapter": readable(param["subtitle"]), "detail": readable(param["detail"]),
                          "mtime": param["mtime"]})
    saves.sort(key=lambda s: s["mtime"], reverse=True)
    return saves


def move_all(moves):
    """Renames each (source, target) in turn; a failed rename puts the ones already done back and
    raises. Renames only (the folders are on one drive): no copy that a locked file could leave
    half done, and the save is never split between its place and the trash."""
    done = []
    try:
        for source, target in moves:
            source.rename(target)
            done.append((source, target))
    except OSError:
        for source, target in reversed(done):
            try:
                target.rename(source)
            except OSError:
                pass
        raise


def delete_save(user_dir, profile, save):
    """Moves a save (its folder, its picture and text, its last good copy) to
    savedata-deleted/<user>/<title>/<dir>-<time>, as the in-game list does."""
    title = save["title_dir"]
    trash = user_dir / "savedata-deleted" / str(profile) / title.name / f"{save['dir']}-{time.strftime('%Y%m%d-%H%M%S')}"
    trash.mkdir(parents=True, exist_ok=False)
    moves = [(title / save["dir"], trash / save["dir"])]
    if save["meta"].is_dir():
        moves.append((save["meta"], trash / save["meta"].name))
    backup = title / ".backup" / save["dir"]
    if backup.is_dir():
        moves.append((backup, trash / "backup"))
    try:
        move_all(moves)
    except OSError:
        shutil.rmtree(trash, ignore_errors=True)  # empty: everything went back
        raise


def restore_save(user_dir, profile, save):
    """Moves a deleted save back, its last good copy too; False when a save of that name (or its
    picture and text) exists again."""
    title = user_dir / "savedata" / str(profile) / save["title_dir"].name
    meta = title / save["meta"].name
    if (title / save["dir"]).exists() or meta.exists():
        return False
    title.mkdir(parents=True, exist_ok=True)
    moves = [(save["folder"] / save["dir"], title / save["dir"])]
    if save["meta"].is_dir():
        moves.append((save["meta"], meta))
    backup, backup_target = save["folder"] / "backup", title / ".backup" / save["dir"]
    if backup.is_dir() and not backup_target.exists():
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        moves.append((backup, backup_target))
    move_all(moves)
    try:
        save["folder"].rmdir()  # only when nothing is left in it
    except OSError:
        pass
    return True


def purge_save(user_dir, save):
    """Removes a deleted save for good (its folder in savedata-deleted, nothing else)."""
    trash = (user_dir / "savedata-deleted").resolve()
    folder = Path(save["folder"]).resolve()
    if trash not in folder.parents:
        raise OSError(f"{folder} is not a deleted save")
    shutil.rmtree(folder)
    # Its backup copies go too (those made before it was deleted: a new save in that slot keeps its own).
    deleted_at = "-".join(folder.name.split("-")[-2:])
    copies = Path(user_dir) / "savedata-backups" / folder.parent.parent.name / folder.parent.name
    for copy in copies.glob(f"{save['dir']}-*") if copies.is_dir() else []:
        if copy.is_dir() and "-".join(copy.name.split("-")[-2:]) <= deleted_at:
            shutil.rmtree(copy, ignore_errors=True)


def restore_backup(user_dir, profile, save):
    """Puts a backup copy (savedata-backups, made before a start) back in place. The save there now,
    if any, goes to the deleted saves first, so nothing is lost; the backup itself stays."""
    title = user_dir / "savedata" / str(profile) / save["title_dir"].name
    current, meta = title / save["dir"], title / save["meta"].name
    title.mkdir(parents=True, exist_ok=True)
    # The copy is made first (beside the save, same drive), so the switch below is renames only.
    work = title / f".restore-{save['dir']}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    try:
        shutil.copytree(save["folder"] / save["dir"], work / save["dir"])
        if save["meta"].is_dir():
            shutil.copytree(save["meta"], work / save["meta"].name)
        if current.exists():
            delete_save(user_dir, profile, {"dir": save["dir"], "title_dir": title, "meta": meta})
        moves = [(work / save["dir"], current)]
        if (work / save["meta"].name).is_dir():
            moves.append((work / save["meta"].name, meta))
        move_all(moves)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def backup_time(save):
    """When a backup copy was made: from its folder name <dir>-<YYYYmmdd-HHMMSS>."""
    try:
        return time.mktime(time.strptime("-".join(save["folder"].name.split("-")[-2:]), "%Y%m%d-%H%M%S"))
    except ValueError:
        return 0


def when(mtime):
    return time.strftime("%Y-%m-%d  %H:%M", time.localtime(mtime)) if mtime > 0 else ""


# -- trophies, screenshots, play stats -----------------------------------------------------

def trophies_module(root):
    """The engine's scripts/trophies.py (reads the game's own trophy packs), or None."""
    path = Path(root) / "gow3_pc" / "scripts" / "trophies.py"
    try:
        spec = importlib.util.spec_from_file_location("eldorado_trophies", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def game_window_open():
    """Whether the game's window is up (its title ends in " — El Dorado"; the launcher's starts with it)."""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(window, _param):
        if user32.IsWindowVisible(window):
            length = user32.GetWindowTextLengthW(window)
            if length:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(window, buffer, length + 1)
                if buffer.value.endswith(" \u2014 El Dorado"):
                    found.append(window)
                    return False
        return True
    try:
        user32.EnumWindows(visit, 0)
    except Exception:
        return False
    return bool(found)


def list_screenshots(user_dir, key):
    """The game's screenshots (F12 in the game), newest first."""
    folder = Path(user_dir) / "screenshots" / key
    try:
        shots = [p for p in folder.iterdir() if p.suffix.lower() in (".png", ".jpg") and p.is_file()]
    except OSError:
        return []
    return sorted(shots, key=lambda p: p.stat().st_mtime, reverse=True)


def recycle(path):
    """To the Recycle Bin (Windows), so a screenshot deleted by mistake can come back."""
    if os.name != "nt":
        Path(path).unlink()
        return
    import ctypes
    from ctypes import wintypes

    class Operation(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("aborted", wintypes.BOOL),
                    ("mappings", ctypes.c_void_p), ("title", wintypes.LPCWSTR)]
    # FO_DELETE; FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT
    op = Operation(None, 3, str(path) + "\0", None, 0x40 | 0x10 | 0x400 | 0x4, False, None, None)
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if code or op.aborted:
        raise OSError(f"the Recycle Bin refused it (code {code})")


def read_stats(user_dir):
    try:
        data = json.loads((Path(user_dir) / "eldorado-stats.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def played(seconds):
    hours, minutes = int(seconds) // 3600, int(seconds) % 3600 // 60
    return f"{hours} H {minutes:02d} M" if hours else f"{minutes} M"


def ago(stamp):
    if not stamp:
        return ""
    days = (time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1)) -
            time.mktime(time.localtime(stamp)[:3] + (0, 0, 0, 0, 0, -1))) // 86400
    return "TODAY" if days <= 0 else "YESTERDAY" if days == 1 else f"{int(days)} DAYS AGO" if days < 30 else \
        time.strftime("%d %b %Y", time.localtime(stamp)).upper()


# -- pictures ------------------------------------------------------------------------------

def rounded(size, radius, fill, outline=None, width=0):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill,
                                            outline=outline, width=width)
    return image


def cover(image, size):
    """Scales and crops to fill the size."""
    w, h = size
    scale = max(w / image.width, h / image.height)
    image = image.resize((max(1, int(image.width * scale + 0.5)), max(1, int(image.height * scale + 0.5))),
                         Image.LANCZOS)
    left, top = (image.width - w) // 2, (image.height - h) // 2
    return image.crop((left, top, left + w, top + h))


def map_art(size, accent, seed):
    """El Dorado's own picture for a game: a dark treasure map, the contour lines of a hill in the
    game's colour around a glow on the right, and a dotted route (no picture from the game files)."""
    w, h = size
    rng = random.Random(seed)
    base = Image.new("RGB", (w, h), BASE)
    glow = Image.new("L", (w, h), 0)
    cx, cy = int(w * (0.68 + rng.random() * 0.1)), int(h * (0.42 + rng.random() * 0.12))
    ImageDraw.Draw(glow).ellipse((cx - w * 0.42, cy - h * 0.62, cx + w * 0.42, cy + h * 0.62), fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(max(8, w // 9)))
    base = Image.composite(Image.new("RGB", (w, h), tuple(int(c * 0.55) for c in accent)), base, glow)
    lines = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(lines)
    phases = [rng.random() * math.tau for _ in range(4)]
    width = max(1, w // 900)
    for ring in range(1, 26):
        radius = ring * max(w, h) / 34
        points = []
        for step in range(181):
            a = step / 180 * math.tau
            wobble = (1 + 0.16 * math.sin(3 * a + phases[0]) + 0.09 * math.sin(5 * a + phases[1])
                      + 0.05 * math.sin(9 * a + phases[2] + ring * 0.3))
            points.append((cx + math.cos(a) * radius * wobble * 1.25, cy + math.sin(a) * radius * wobble * 0.82))
        draw.line(points, fill=70 if ring % 5 == 0 else 34, width=width * (2 if ring % 5 == 0 else 1))
    # A dotted route toward the hill's top, and an X.
    x, y = w * 0.08, h * 0.92
    for step in range(46):
        t = step / 45
        px = x + (cx - x) * t + math.sin(t * 7 + phases[3]) * w * 0.03
        py = y + (cy - y) * t + math.cos(t * 5 + phases[3]) * h * 0.04
        if step % 2 == 0:
            r = max(1, w // 520)
            draw.ellipse((px - r, py - r, px + r, py + r), fill=90)
    r = max(4, w // 90)
    draw.line((cx - r, cy - r, cx + r, cy + r), fill=150, width=max(2, w // 400))
    draw.line((cx - r, cy + r, cx + r, cy - r), fill=150, width=max(2, w // 400))
    tint = Image.new("RGB", (w, h), accent)
    return Image.composite(tint, base, lines)


def shade(image, left=0.62, bottom=0.30):
    """Darkens toward the left and the bottom, where the text and the cards are."""
    w, h = image.size
    ramp = Image.linear_gradient("L")  # 256x256, black at the top to white at the bottom
    vertical = ramp.resize((w, h)).point(lambda p: int(220 * max(0.0, (p / 255 - bottom) / (1 - bottom)) ** 1.25))
    # rotate(90): black at the left to white at the right, so p / 255 is x / width.
    horizontal = ramp.rotate(90).resize((w, h)).point(lambda p: int(175 * max(0.0, 1 - (p / 255) / left) ** 1.3))
    mask = ImageChops.add(vertical, horizontal, offset=26).point(lambda p: min(236, p))
    # A touch of sepia, as an old photograph in Drake's journal.
    sepia = Image.merge("RGB", [image.convert("L").point(lambda v, k=k: min(255, int(v * k))) for k in (1.07, 0.92, 0.72)])
    image = Image.blend(image, sepia, 0.22)
    return Image.composite(Image.new("RGB", (w, h), BASE), image, mask)


def chamfer_points(w, h, cut):
    """A plate with its top-left and bottom-right corners cut: El Dorado's shape for every panel,
    button and picture (as a brass plate on an expedition case)."""
    return [(cut, 0), (w - 1, 0), (w - 1, h - 1 - cut), (w - 1 - cut, h - 1), (0, h - 1), (0, cut)]


def chamfer(size, cut, fill, outline=None, width=1):
    w, h = size
    scale = 3  # drawn larger and scaled down: smooth cut edges
    big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    points = chamfer_points(w * scale, h * scale, cut * scale)
    draw.polygon(points, fill=fill)
    if outline:
        draw.line(points + [points[0]], fill=outline, width=width * scale, joint="curve")
    return big.resize((w, h), Image.LANCZOS)


def chamfer_mask(size, cut):
    return chamfer(size, cut, (255, 255, 255, 255)).split()[3]


def compass(size, color):
    """El Dorado's emblem: an eight-point compass rose in a ring, drawn here (no picture shipped)."""
    s = size * 4
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    c = s / 2
    r, g, b = color
    light, dark = (r, g, b, 255), (int(r * 0.55), int(g * 0.55), int(b * 0.55), 255)
    ring = s * 0.035
    draw.ellipse((s * 0.08, s * 0.08, s * 0.92, s * 0.92), outline=light, width=int(ring))
    draw.ellipse((s * 0.17, s * 0.17, s * 0.83, s * 0.83), outline=dark, width=max(1, int(ring * 0.5)))
    for k in range(8):
        a = k * math.pi / 4 - math.pi / 2
        long = k % 2 == 0
        tip = s * (0.47 if long else 0.30)
        side = s * (0.075 if long else 0.06)
        tx, ty = c + math.cos(a) * tip, c + math.sin(a) * tip
        lx, ly = c + math.cos(a - math.pi / 2) * side, c + math.sin(a - math.pi / 2) * side
        rx, ry = c + math.cos(a + math.pi / 2) * side, c + math.sin(a + math.pi / 2) * side
        # Each point in two halves, light and dark, as an engraving.
        draw.polygon([(c, c), (lx, ly), (tx, ty)], fill=light)
        draw.polygon([(c, c), (rx, ry), (tx, ty)], fill=dark if long else light)
    draw.ellipse((c - s * 0.04, c - s * 0.04, c + s * 0.04, c + s * 0.04), fill=(20, 14, 9, 255), outline=light,
                 width=max(1, int(ring * 0.6)))
    return image.resize((size, size), Image.LANCZOS)


def rail_texture(size, accent):
    """The rail: dark leather with the faint contour lines of a map, darker toward the bottom."""
    w, h = size
    base = Image.new("RGB", (w, h), (15, 11, 8))
    lines = map_art((max(w, 2) * 2, h), accent, seed="rail").crop((0, 0, w, h))
    base = Image.blend(base, lines, 0.16)
    ramp = Image.linear_gradient("L").resize((w, h)).point(lambda p: int(110 * p / 255))
    return Image.composite(Image.new("RGB", (w, h), (8, 6, 4)), base, ramp)


class EmbeddedRoot(tk.Frame):
    """The classic launcher's root, as a frame of this window: its window calls do nothing, and
    destroying it (the launcher closes itself to install an update) closes the window."""

    def __init__(self, master, on_close, **kw):
        super().__init__(master, **kw)
        self.on_close = on_close
        self.closing = False

    def title(self, *args):
        return ""

    def resizable(self, *args):
        pass

    def iconbitmap(self, *args, **kw):
        pass

    def minsize(self, *args):
        pass

    def geometry(self, *args):
        return ""

    def protocol(self, *args):
        pass

    def destroy(self):
        if self.closing:
            return super().destroy()
        self.closing = True
        self.on_close()


class Hub:
    def __init__(self, root, module):
        self.root, self.m = root, module
        self.s = max(1.0, root.winfo_fpixels("1i") / 96.0)
        self.screen = "games"
        self.focus_zone = "main"   # "top" (the strip) or "main"
        self.top_index = 0
        self.save_index = 0
        self.view = "saves"   # the Saves screen's list: "saves", "deleted" or "backups"
        self.armed_delete = None
        self.saves_cache = {}
        self.trophy_cache = {}
        self.loading = None  # {"key", "since", "checked"} from PLAY until the game's window is up
        self.hidden = False  # out of sight while the game's window is up (no drawing, a slow tick)
        self.trophy_lib = None
        self.grid_columns = 1
        self.photos = {}
        self.bg_cache = {}
        self.bg_item = None
        self.bg_photo = None
        self.bg_image = None
        self.fade = None
        self.size = (0, 0)
        self.last_pad = set()
        self.pad = None
        self.last_device = "keyboard"  # what was used last, for the Auto button icons
        root.title("El Dorado — Uncharted: The Nathan Drake Collection")
        root.configure(bg="#0d0e12")
        try:
            root.iconbitmap(default=str(module.ASSETS / "eldorado.ico"))
        except tk.TclError:
            pass
        width, height = self.px(1280), self.px(780)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        width, height = min(width, sw - self.px(40)), min(height, sh - self.px(90))
        root.geometry(f"{width}x{height}+{max(0, (sw - width) // 2)}+{max(0, (sh - height) // 2 - self.px(20))}")
        root.minsize(self.px(1040), self.px(660))
        self.canvas = tk.Canvas(root, bg="#0d0e12", highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        # The classic launcher, built inside this window for the Settings screen.
        for name, value in CLASSIC_PALETTE.items():
            setattr(module, name, value)
        self.settings_frame = EmbeddedRoot(root, self.quit_now, bg=module.BG)
        self.launcher = module.Launcher(self.settings_frame)
        self.trim_classic()
        for keys, action in ((("<Left>",), "left"), (("<Right>",), "right"), (("<Up>",), "up"),
                             (("<Down>",), "down"), (("<Return>", "<space>"), "ok"),
                             (("<Escape>", "<BackSpace>"), "back"), (("<Delete>",), "delete"),
                             (("<Tab>",), "alt"), (("q", "Q"), "prev"), (("e", "E"), "next")):
            for key in keys:
                root.bind(key, lambda event, a=action: self.key(event, a))
        root.bind("<F11>", lambda event: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.protocol("WM_DELETE_WINDOW", self.quit)
        try:
            module.dark_title_bar(root)
        except Exception:
            pass
        root.after(60, self.tick)

    def px(self, value):
        return int(value * self.s)

    def trim_classic(self):
        """Only the classic launcher's pages stay: its picture, game cards and footer (the status
        line and PLAY, which this window shows itself) are hidden."""
        keep = self.launcher.body
        while keep.master is not self.settings_frame:
            keep = keep.master
        for child in self.settings_frame.pack_slaves():
            if child is not keep:
                child.pack_forget()
        keep.pack_configure(pady=(self.px(10), self.px(14)))

    # -- state ---------------------------------------------------------------------------

    @property
    def game(self):
        return self.launcher.config.get("game", "u1")

    def game_info(self, key=None):
        key = key or self.game
        return next(g for g in self.m.GAMES if g["key"] == key)

    def accent(self, key=None, alpha=None):
        r, g, b = ACCENTS.get(key or self.game, ACCENTS["u1"])
        return (r, g, b, alpha) if alpha is not None else f"#{r:02x}{g:02x}{b:02x}"

    def profile(self, key=None):
        return self.launcher.config["games"][key or self.game].get("save_profile", "1")

    @property
    def show_deleted(self):
        return self.view == "deleted"

    @property
    def show_backups(self):
        return self.view == "backups"

    def saves(self, key=None, deleted=False, view=None):
        key = key or self.game
        view = view or ("deleted" if deleted else "saves")
        cache_key = (key, view)
        if cache_key not in self.saves_cache:
            try:
                found = list_saves(self.m.USER_DIR, self.profile(key), self.game_info(key)["number"],
                                   view != "saves", "savedata-backups" if view == "backups" else None)
                if view == "backups":  # newest copy first, the time it was made shown
                    # Only copies of saves that are there now: a deleted save's copies go with it (Deleted
                    # saves brings the save back, and its copies show again).
                    live = self.m.USER_DIR / "savedata" / str(self.profile(key))
                    found = [s for s in found if (live / s["title_dir"].name / s["dir"]).is_dir()]
                    for save in found:
                        save["mtime"] = backup_time(save) or save["mtime"]
                    found.sort(key=lambda s: s["mtime"], reverse=True)
                self.saves_cache[cache_key] = found
            except OSError:
                self.saves_cache[cache_key] = []
        return self.saves_cache[cache_key]

    def trophies(self, key=None):
        """(info, unlocked, progress) of the game's trophy set, read from the game's own pack
        (sce_sys/trophy) into the shader cache folder once; None without a pack."""
        key = key or self.game
        if key not in self.trophy_cache:
            result = None
            if self.trophy_lib is None:
                self.trophy_lib = trophies_module(self.m.ROOT) or False
            lib = self.trophy_lib
            if lib:
                try:
                    language = str(self.launcher.config.get("language", "1"))
                    folder = lib.prepare(self.launcher.game_dir(), key, self.m.USER_DIR / "cache" / "hub-trophy" / key,
                                         int(language) if language.isdigit() else 1)
                    info = lib.read_cache(folder) if folder else None
                    if info:
                        unlocked = lib.read_unlocks(self.m.USER_DIR, info["npcommid"])
                        result = (info, unlocked, lib.progress(info, unlocked), folder)
                except Exception:
                    result = None
            self.trophy_cache[key] = result
        return self.trophy_cache[key]

    def trophy_rows(self):
        """Earned ones first (newest first), then the rest in the game's order."""
        data = self.trophies()
        if not data:
            return []
        info, unlocked = data[0], data[1]
        rows = [(number, grade, hidden, name, detail, unlocked.get(number))
                for number, grade, hidden, name, detail in info["trophies"]]
        return sorted([r for r in rows if r[5]], key=lambda r: -r[5]) + [r for r in rows if not r[5]]

    def trophy_icon(self, folder, number, size, earned):
        def make():
            try:
                image = Image.open(Path(folder) / f"TROP{number:03d}.PNG").convert("RGBA")
            except OSError:
                image = Image.new("RGBA", (size, size), (40, 32, 22, 255))
            image = image.resize((size, size), Image.LANCZOS)
            if not earned:
                grey = ImageOps.grayscale(image.convert("RGB")).point(lambda v: int(v * 0.45))
                image = Image.merge("RGBA", (grey, grey, grey, image.getchannel("A")))
            return image
        return self.photo(("trop", str(folder), number, size, earned), make)

    def shots(self, key=None):
        return list_screenshots(self.m.USER_DIR, key or self.game)

    def logo(self, key):
        """The game's own icon (its logo on a coin), from the player's trophy pack; None without."""
        if not hasattr(self, "logos"):
            self.logos = {}
        if key not in self.logos:
            self.logos[key] = game_icons.trophy_icon(self.launcher.game_dir(), self.game_info(key)["number"])
        return self.logos[key]

    def collection_art(self):
        """The Collection's own picture from the chosen game folder (sce_sys/pic1.png, else pic0.png),
        as the classic launcher shows it."""
        for name in ("pic1.png", "pic0.png"):
            path = Path(self.launcher.game_dir()) / "sce_sys" / name
            if path.is_file():
                return path
        return None

    def game_picture(self, key, size):
        """The game's picture from the chosen game folder's own art (sce_sys/pic0.png, else pic1.png):
        the third of it the game's cover sits in when the art shows the three games side by side, the
        upper part where the faces are."""
        # Only the Arabic edition's art is the three covers side by side (the original's is one picture
        # of Drake): told apart by the title in param.sfo.
        if not self.m.is_arabic_copy(self.launcher.game_dir()):
            return None
        path = None
        for name in ("pic0.png", "pic1.png"):
            candidate = Path(self.launcher.game_dir()) / "sce_sys" / name
            if candidate.is_file():
                path = candidate
                break
        if path is None:
            return None
        try:
            art = Image.open(path).convert("RGB")
        except OSError:
            return None
        third = art.width // 3
        index = int(self.game_info(key)["number"]) - 1
        part = art.crop((third * index, 0, third * (index + 1), art.height))
        w, h = size
        part = part.resize((w, max(h, int(part.height * w / part.width))), Image.LANCZOS)
        top = min(part.height - h, int(part.height * 0.17))  # below a repack's corner mark
        return part.crop((0, top, w, top + h))

    def latest_picture(self, key):
        return next((s["picture"] for s in self.saves(key) if s["picture"]), None)

    def running(self):
        return bool(self.launcher.process)

    def rail_items(self):
        """The rail's items in order: the three games, Saves, Settings, the update when there is
        one, Logs and Quit (these two at the rail's foot)."""
        items = [("game", g["key"]) for g in self.m.GAMES] + [("saves", None), ("trophies", None),
                                                             ("gallery", None), ("settings", None)]
        if getattr(self.launcher, "update_release", None):
            items.append(("update", None))
        return items + [("logs", None), ("quit", None)]

    def capturing(self):
        """A Controls slot waits for a key, mouse button or controller button."""
        return (getattr(self.launcher, "capturing", None) is not None
                or getattr(self.launcher, "pad_capture", None) is not None)

    # -- input ---------------------------------------------------------------------------

    def key(self, event, action):
        if self.screen == "settings":
            return  # the pages' own widgets (and Controls' capture) take the keys
        self.used("keyboard")
        self.act(action)
        return "break"

    def used(self, device):
        if device != self.last_device:
            self.last_device = device
            self.draw()

    def hint(self, action):
        """The key or button an action is on: the Button icons setting (Controls), Auto following
        the keyboard or the controller, whichever was used last."""
        style = self.launcher.game_settings().get("prompts", "auto")
        if style not in HINTS:
            style = "keyboard"
            if self.last_device == "pad" and self.pad is not None and self.pad.sdl:
                style = self.pad.style() or "xbox"
        return HINTS[style].get(action, "")

    def tick(self):
        """Controller input (edges of the held buttons) while this window has the focus and no
        game runs, and the status from the classic launcher."""
        if self.hidden:
            # The launcher is out of sight while the game plays: nothing drawn, only a look twice a second
            # whether the game has ended (closed in any way: its menu, the close question, a crash, STOP).
            if not self.running():
                self.hidden = False
                self.root.deiconify()
                self.root.lift()
                try:
                    self.root.focus_force()
                except tk.TclError:
                    pass
                self.shown_state = None  # redraw with what the game left (saves, pictures, stats)
            else:
                self.root.after(500, self.tick)
                return
        try:
            focused = self.root.focus_displayof() is not None
        except (KeyError, tk.TclError):
            focused = False
        if focused and not self.running():
            if self.pad is None:
                self.pad = self.m.Gamepads()
            held = self.pad.held() if self.pad.sdl else set()
            for name in held - self.last_pad:
                if name in PAD_ACTIONS:
                    self.used("pad")
                    self.pad_action(PAD_ACTIONS[name])
            self.last_pad = held
        else:
            self.last_pad = set()
        if self.loading:
            now = time.monotonic()
            if not self.running() or now - self.loading["since"] > 240:
                self.loading = None
                self.draw()
            elif now - self.loading["checked"] > 0.4:
                self.loading["checked"] = now
                if game_window_open():
                    # The game's window is up: the launcher steps aside until it ends (no CPU, GPU or
                    # drawing while the game runs).
                    self.loading = None
                    self.hidden = True
                    self.root.withdraw()
                    self.root.after(500, self.tick)
                    return
                self.draw()
            elif int(now * 8) != self.loading.get("frame"):
                self.loading["frame"] = int(now * 8)
                self.draw()
        state = (self.status_text(), self.running(), bool(getattr(self.launcher, "update_release", None)))
        if state != getattr(self, "shown_state", None):
            self.shown_state = state
            self.saves_cache.clear()  # a game that ran may have saved
            self.bg_cache.clear()
            self.change_background(self.game, fade=False)
            self.draw()
        self.root.after(50, self.tick)

    def pad_action(self, action):
        if self.screen != "settings":
            self.act(action)
            return
        if self.capturing():
            return
        if action == "back":
            self.show("games")
        elif action in ("prev", "next"):
            tabs = list(self.launcher.pages)
            current = getattr(self.launcher, "current_tab", tabs[0])
            index = tabs.index(current) if current in tabs else 0
            self.launcher.show_tab(tabs[(index + (-1 if action == "prev" else 1)) % len(tabs)])
        self.draw()

    def status_text(self):
        label = getattr(self.launcher, "status", None)
        try:
            return label.cget("text") if label else ""
        except tk.TclError:
            return ""

    def act(self, action):
        if self.fade:
            self.finish_fade()
        if action == "play":
            self.play_or_stop()
            return
        if action in ("prev", "next"):
            self.change_game(-1 if action == "prev" else 1)
            return
        if self.focus_zone == "top":
            self.act_top(action)
        elif self.screen == "games":
            self.act_games(action)
        elif self.screen == "saves":
            self.act_saves(action)
        elif self.screen == "trophies":
            self.act_trophies(action)
        elif self.screen == "gallery":
            self.act_gallery(action)
        self.draw()

    def act_top(self, action):
        """The rail: up and down through its items, OK opens one, right or back returns."""
        items = self.rail_items()
        if action == "up":
            self.top_index = (self.top_index - 1) % len(items)
        elif action == "down":
            self.top_index = (self.top_index + 1) % len(items)
        elif action in ("right", "back"):
            self.focus_zone = "main"
        elif action == "ok":
            self.open_rail(items[self.top_index])

    def open_rail(self, item):
        kind, value = item
        self.focus_zone = "main"
        if kind == "game":
            if self.screen != "games":
                self.show("games")
            if value != self.game:
                keys = [g["key"] for g in self.m.GAMES]
                self.change_game(keys.index(value) - keys.index(self.game))
        elif kind in dict(SCREENS):
            self.show(kind)
        elif kind == "update":
            self.launcher.install_update()
        elif kind == "logs":
            self.launcher.open_logs()
        elif kind == "quit":
            self.quit()

    def show(self, screen):
        self.screen, self.focus_zone, self.armed_delete = screen, "main", None
        self.save_index = 0
        self.view = "saves"
        self.top_index = self.current_rail_index()
        if screen == "settings":
            self.launcher.reload_ini()
            self.place_settings()
            self.settings_frame.lift()
        else:
            self.settings_frame.place_forget()
            self.root.focus_set()
            self.saves_cache.clear()
            self.trophy_cache.clear()  # unlocks read again
        self.draw()

    def place_settings(self):
        rw, top = self.rail_width("settings"), self.px(18)
        self.settings_frame.place(x=rw, y=top, relwidth=1, width=-rw, relheight=1,
                                  height=-top - self.bottom_height())

    def current_rail_index(self):
        items = self.rail_items()
        item = ("game", self.game) if self.screen == "games" else (self.screen, None)
        return items.index(item) if item in items else 0

    def to_top(self):
        self.focus_zone = "top"
        self.top_index = self.current_rail_index()

    def act_games(self, action):
        if action in ("left", "right"):
            self.change_game(-1 if action == "left" else 1)
        elif action == "ok":
            self.play_or_stop()
        elif action == "up":
            self.to_top()
        elif action == "down":
            self.show("saves")
        elif action == "alt":
            self.show("settings")
        elif action == "back":
            self.focus_zone, self.top_index = "top", len(self.rail_items()) - 1

    def act_saves(self, action):
        saves = self.saves(view=self.view)
        if action != ("ok" if self.show_backups else "delete"):
            self.armed_delete = None
        if action == "up":
            if self.save_index == 0:
                self.to_top()
            else:
                self.save_index -= 1
        elif action == "down" and self.save_index + 1 < len(saves):
            self.save_index += 1
        elif action == "left":
            self.to_top()
        elif action == "alt":  # saves -> deleted saves -> backups -> saves
            self.view = {"saves": "deleted", "deleted": "backups"}.get(self.view, "saves")
            self.save_index = 0
        elif action in ("view_saves", "view_deleted", "view_backups"):
            self.view, self.save_index = action[5:], 0
        elif action == "back":
            if self.view != "saves":
                self.view, self.save_index = "saves", 0
            else:
                self.show("games")
        elif action == "ok" and saves and self.show_backups:
            self.restore_backup_selected(saves)
        elif self.show_backups:
            pass
        elif action == "delete" and saves and not self.show_deleted:
            self.delete_selected(saves)
        elif action == "delete" and saves and self.show_deleted:
            self.purge_selected(saves)
        elif action == "ok" and saves and self.show_deleted:
            self.restore_selected(saves)

    def act_trophies(self, action):
        count = len(self.trophy_rows())
        if action == "up":
            if self.save_index == 0:
                self.to_top()
            else:
                self.save_index -= 1
        elif action == "down" and self.save_index + 1 < count:
            self.save_index += 1
        elif action == "left":
            self.to_top()
        elif action == "back":
            self.show("games")

    def act_gallery(self, action):
        shots = self.shots()
        cols = max(1, self.grid_columns)
        if action != "delete":
            self.armed_delete = None
        if action == "left":
            if self.save_index % cols == 0:
                self.to_top()
            else:
                self.save_index -= 1
        elif action == "right" and self.save_index + 1 < len(shots):
            self.save_index += 1
        elif action == "up":
            if self.save_index < cols:
                self.to_top()
            else:
                self.save_index -= cols
        elif action == "down" and shots:
            self.save_index = min(len(shots) - 1, self.save_index + cols)
        elif action == "back":
            self.show("games")
        elif action == "ok" and shots:
            self.open_path(shots[min(self.save_index, len(shots) - 1)])
        elif action == "alt":
            folder = self.m.USER_DIR / "screenshots" / self.game
            folder.mkdir(parents=True, exist_ok=True)
            self.open_path(folder)
        elif action == "delete" and shots:
            shot = shots[min(self.save_index, len(shots) - 1)]
            if self.armed_delete != "shot:" + str(shot):
                self.armed_delete = "shot:" + str(shot)
                return
            self.armed_delete = None
            try:
                recycle(shot)
                self.launcher.set_status(f"{shot.name} moved to the Recycle Bin.")
            except OSError as error:
                messagebox.showerror("El Dorado", f"The screenshot could not be deleted:\n{error}")
            self.save_index = max(0, min(self.save_index, len(self.shots()) - 1))

    def open_path(self, path):
        try:
            os.startfile(str(path))
        except (OSError, AttributeError) as error:
            self.launcher.set_status(f"Could not open {path}: {error}")

    def delete_selected(self, saves):
        if self.running():
            self.launcher.set_status("Close the game before deleting a save.")
            return
        save = saves[min(self.save_index, len(saves) - 1)]
        if self.armed_delete != save["dir"]:
            self.armed_delete = save["dir"]
            return
        self.armed_delete = None
        try:
            delete_save(self.m.USER_DIR, self.profile(), save)
            self.launcher.set_status(f"Save {save['dir']} deleted (kept in savedata-deleted).")
        except OSError as error:
            messagebox.showerror("El Dorado", f"The save could not be moved:\n{error}")
        self.after_save_change()
        self.save_index = max(0, min(self.save_index, len(self.saves()) - 1))

    def purge_selected(self, saves):
        """Deleted saves: Delete twice removes the selected one for good."""
        save = saves[min(self.save_index, len(saves) - 1)]
        key = str(save["folder"])
        if self.armed_delete != key:
            self.armed_delete = key
            return
        self.armed_delete = None
        try:
            purge_save(self.m.USER_DIR, save)
            self.launcher.set_status(f"Save {save['dir']} removed for good.")
        except OSError as error:
            messagebox.showerror("El Dorado", f"The save could not be removed:\n{error}")
        self.saves_cache.clear()
        self.save_index = max(0, min(self.save_index, len(self.saves(deleted=True)) - 1))

    def restore_selected(self, saves):
        if self.running():
            self.launcher.set_status("Close the game before restoring a save.")
            return
        save = saves[min(self.save_index, len(saves) - 1)]
        try:
            ok = restore_save(self.m.USER_DIR, self.profile(), save)
        except OSError as error:
            messagebox.showerror("El Dorado", f"The save could not be restored:\n{error}")
            return
        self.launcher.set_status(f"Save {save['dir']} restored." if ok else
                                 f"A save named {save['dir']} exists: delete it first.")
        self.after_save_change()
        self.save_index = max(0, min(self.save_index, len(self.saves(deleted=True)) - 1))

    def restore_backup_selected(self, saves):
        """Backups: OK twice puts the selected copy back (the save there now goes to deleted saves)."""
        if self.running():
            self.launcher.set_status("Close the game before restoring a backup.")
            return
        save = saves[min(self.save_index, len(saves) - 1)]
        key = "restore:" + str(save["folder"])
        if self.armed_delete != key:
            self.armed_delete = key
            return
        self.armed_delete = None
        try:
            restore_backup(self.m.USER_DIR, self.profile(), save)
        except OSError as error:
            messagebox.showerror("El Dorado", f"The backup could not be restored:\n{error}")
            return
        self.launcher.set_status(f"Save {save['dir']} restored from the backup of {when(save['mtime'])} "
                                 "(the one it replaced is in deleted saves).")
        self.after_save_change()

    def after_save_change(self):
        self.saves_cache.clear()
        self.bg_cache.clear()
        self.change_background(self.game, fade=False)

    def change_game(self, step):
        keys = [g["key"] for g in self.m.GAMES]
        key = keys[(keys.index(self.game) + step) % len(keys)]
        if self.running():
            self.launcher.set_status("A game is running: close it to choose another.")
            self.draw()
            return
        self.launcher.select_game(key)
        self.save_index = 0
        self.armed_delete = None
        self.change_background(key)
        self.draw()

    def play_or_stop(self):
        if self.running():
            if messagebox.askyesno("El Dorado", "Stop the game? Progress since the last checkpoint is lost."):
                self.launcher.stop()
        else:
            self.launcher.play()
            if self.running():
                self.loading = {"key": self.game, "since": time.monotonic(), "checked": 0.0}
        self.draw()

    def quit(self):
        if self.running() and not messagebox.askyesno(
                "El Dorado", "The game is still running. Close the launcher anyway? (The game keeps running.)"):
            return
        self.quit_now()

    def quit_now(self):
        try:
            self.m.write_config(self.launcher.config)
        except Exception:
            pass
        self.settings_frame.closing = True
        self.root.destroy()

    # -- mouse ---------------------------------------------------------------------------

    def clickable_at(self, x, y):
        for item in self.canvas.find_overlapping(x, y, x, y)[::-1]:
            for tag in self.canvas.gettags(item):
                if tag.startswith("click:"):
                    return tag[6:]
        return None

    def on_motion(self, event):
        self.canvas.configure(cursor="hand2" if self.clickable_at(event.x, event.y) else "")

    def on_click(self, event):
        what = self.clickable_at(event.x, event.y)
        if what:
            self.clicked(what)

    def clicked(self, what):
        kind, _, value = what.partition("=")
        self.focus_zone = "main"
        if kind == "rail":
            items = self.rail_items()
            index = int(value)
            if index < len(items):
                self.open_rail(items[index])
            return
        if kind == "do":
            self.act(value)
            return
        if kind == "log":  # an entry of the expedition log on the games screen
            self.show("saves")
            self.save_index = int(value)
        elif kind == "pick":  # a trophy or a screenshot; a screenshot clicked again opens
            index = int(value)
            if index == self.save_index and self.screen == "gallery":
                self.act_gallery("ok")
            elif index != self.save_index:
                self.armed_delete = None
            self.save_index = index
        elif kind == "save":
            index = int(value)
            if index == self.save_index and self.show_deleted:
                self.restore_selected(self.saves(deleted=True))
            elif index == self.save_index and self.show_backups:
                self.restore_backup_selected(self.saves(view="backups"))
            elif index != self.save_index:
                self.armed_delete = None
            self.save_index = index
        self.draw()

    def on_wheel(self, event):
        if self.screen in ("saves", "trophies"):
            self.act("up" if event.delta > 0 else "down")
        elif self.screen == "gallery":
            self.act("left" if event.delta > 0 else "right")

    # -- drawing -------------------------------------------------------------------------

    def rail_width(self, screen=None):
        """The rail on the left: wide with the games' names, slim on the Settings screen (its pages
        need the width)."""
        return self.px(84) if (screen or self.screen) == "settings" else self.px(300)

    def bottom_height(self):
        return self.px(64)

    def on_resize(self, event):
        size = (event.width, event.height)
        if size == self.size or size[0] < 50:
            return
        self.size = size
        self.bg_cache.clear()
        if self.screen == "settings":
            self.place_settings()
        if getattr(self, "resize_job", None):
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(60, lambda: (self.change_background(self.game, fade=False), self.draw()))

    def background(self, key):
        """The game's picture: its latest save's (where you left off), else the game's own cover from the
        game files on the right, fading into the dark, else El Dorado's map art."""
        w, h = self.size
        if (key, w, h) in self.bg_cache:
            return self.bg_cache[(key, w, h)]
        image = None
        path = self.latest_picture(key)
        if path is None:
            image = self.cover_background(key, (w, h))
        if path:
            try:
                image = cover(Image.open(path).convert("RGB"), (w, h))
                if image.width > Image.open(path).width * 1.6:  # an older, small save picture
                    image = image.filter(ImageFilter.GaussianBlur(max(1, w // 900)))
            except OSError:
                image = None
        if image is None:
            image = map_art((w, h), ACCENTS[key], seed=key)
        image = shade(image)
        self.bg_cache[(key, w, h)] = image
        return image

    def cover_background(self, key, size):
        """The game's cover (its third of the game files' art, without the top strip where a repack
        may have put its mark) at the window's height on the right, fading to the left."""
        w, h = size
        source = None
        for name in ("pic0.png", "pic1.png"):
            path = Path(self.launcher.game_dir()) / "sce_sys" / name
            if path.is_file():
                source = path
                break
        if source is None:
            return None
        try:
            art = Image.open(source).convert("RGB")
        except OSError:
            return None
        third = art.width // 3
        index = int(self.game_info(key)["number"]) - 1
        part = art.crop((third * index, int(art.height * 0.17), third * (index + 1), art.height))
        # As tall as the window, or wider when the window is wide (then cut evenly top and bottom).
        scale = max(h / part.height, w * 0.42 / part.width)
        part = part.resize((max(1, int(part.width * scale)), max(1, int(part.height * scale))), Image.LANCZOS)
        top = (part.height - h) // 2
        part = part.crop((0, top, part.width, top + h))
        image = Image.new("RGB", (w, h), BASE)
        x = max(0, w - part.width)
        # Its left half fades into the dark, smoothly; the top and bottom edges a little.
        ramp = Image.linear_gradient("L").rotate(90).resize((part.width, h))  # black left, white right
        alpha = ramp.point(lambda p: int(255 * min(1.0, p / 255 / 0.6) ** 1.6))
        vertical = Image.linear_gradient("L").resize((part.width, h))  # black top, white bottom
        edges = vertical.point(lambda p: int(255 * min(1.0, p / 255 / 0.12, (255 - p) / 255 / 0.12)))
        image.paste(part, (x, 0), ImageChops.multiply(alpha, edges))
        return image

    def change_background(self, key, fade=True):
        if self.size[0] < 50:
            return
        target = self.background(key)
        if not fade or self.bg_image is None:
            self.set_background(target)
            return
        self.fade = {"from": self.bg_image, "to": target, "step": 0}
        self.fade_step()

    def fade_step(self):
        fade = self.fade
        if not fade:
            return
        fade["step"] += 1
        steps = 7
        if fade["step"] >= steps or fade["from"].size != fade["to"].size:
            self.finish_fade()
            return
        self.show_background(Image.blend(fade["from"], fade["to"], fade["step"] / steps))
        self.root.after(18, self.fade_step)

    def finish_fade(self):
        if self.fade:
            target = self.fade["to"]
            self.fade = None
            self.set_background(target)

    def set_background(self, image):
        self.bg_image = image
        self.show_background(image)

    def show_background(self, image):
        self.bg_photo = ImageTk.PhotoImage(image)
        if self.bg_item is None:
            self.bg_item = self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        else:
            self.canvas.itemconfig(self.bg_item, image=self.bg_photo)
        self.canvas.tag_lower(self.bg_item)

    def photo(self, key, make):
        if key not in self.photos:
            self.photos[key] = ImageTk.PhotoImage(make())
        return self.photos[key]

    def card_image(self, key, size, path, selected=False):
        """A save's picture (or the game's own art, else its icon over the map) on a cut-corner
        plate with a thin edge, gold when selected."""
        def make():
            image = None
            if path:
                try:
                    image = cover(Image.open(path).convert("RGB"), size)
                except OSError:
                    image = None
            if image is None:
                image = self.game_picture(key, size)
            # Else the game's own logo (its trophy pack, in every copy), else "NO PICTURE".
            if image is None:
                image = Image.new("RGB", size, (24, 18, 12))
                logo = self.logo(key)
                if logo is not None:
                    copy = logo.convert("RGBA")
                    copy.thumbnail((int(size[0] * 0.8), int(size[1] * 0.8)), Image.LANCZOS)
                    image = image.convert("RGBA")
                    image.alpha_composite(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
                    image = image.convert("RGB")
                else:
                    draw = ImageDraw.Draw(image)
                    text = "NO PICTURE"
                    box = draw.textbbox((0, 0), text)
                    draw.text(((size[0] - box[2]) // 2, (size[1] - box[3]) // 2), text, fill=(110, 94, 68))
            return self.plate_picture(image.resize(size), key, selected)
        try:  # a save written again keeps its file name: its time tells the pictures apart
            stamp = path.stat().st_mtime if path else 0
        except OSError:
            stamp = 0
        return self.photo(("card", key, str(path), stamp, size, selected), make)

    def plate_picture(self, image, key, selected):
        w, h = image.size
        cut = self.cut(min(w, h))
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.paste(image, (0, 0), chamfer_mask((w, h), cut))
        edge = (*ACCENTS[key], 255) if selected else (120, 98, 66, 200)
        out.alpha_composite(chamfer((w, h), cut, (0, 0, 0, 0), outline=edge,
                                    width=max(1, self.px(2) if selected else self.px(1))))
        return out

    def cut(self, side):
        return max(self.px(6), min(self.px(18), side // 9))

    def plate(self, x, y, w, h, fill, outline=None, width=1, tags=(), cut=None):
        cut = self.cut(min(w, h)) if cut is None else cut
        photo = self.photo(("plate", w, h, fill, outline, width, cut),
                           lambda: chamfer((w, h), cut, fill, outline=outline, width=width))
        return self.canvas.create_image(x, y, image=photo, anchor="nw", tags=("ui",) + tuple(tags))

    def text_width(self, text, font):
        probe = self.canvas.create_text(0, 0, text=text, font=font, anchor="nw")
        x1, _, x2, _ = self.canvas.bbox(probe)
        self.canvas.delete(probe)
        return x2 - x1

    def button(self, x, y, text, font, style="ghost", focused=False, key_hint=None, tags=(), anchor="nw",
               accent=None, height=None):
        """A cut-corner plate button: style "solid" (filled with the accent), "ghost" (outlined) or
        "flat" (text only, a light fill when focused). key_hint: a small key cap after the text."""
        accent = accent or self.accent()
        r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
        pad = self.px(16)
        tw = self.text_width(text, font)
        hint_w = self.text_width(key_hint, self.f_hint) + self.px(12) if key_hint else 0
        w = tw + pad * 2 + (hint_w + self.px(8) if key_hint else 0)
        h = height or self.px(36)
        if anchor == "ne":
            x -= w
        elif anchor == "n":
            x -= w // 2
        if style == "solid":
            fill, outline = (r, g, b, 240), (255, 244, 214, 235) if focused else None
        elif style == "ghost":
            fill, outline = (18, 13, 9, 215 if focused else 175), ((r, g, b, 255) if focused else (r, g, b, 140))
        else:
            fill, outline = ((255, 255, 255, 30) if focused else (0, 0, 0, 0)), None
        all_tags = ("ui",) + tuple(tags)
        self.plate(x, y, w, h, fill, outline=outline, width=max(1, self.px(2) if focused else self.px(1)),
                   tags=tags, cut=self.px(8))
        ink = "#17120a" if style == "solid" else INK
        self.canvas.create_text(x + pad, y + h // 2, text=text, font=font, fill=ink, anchor="w", tags=all_tags)
        if key_hint:
            kx = x + pad + tw + self.px(8)
            kw, kh = hint_w, self.px(20)
            self.plate(kx, y + (h - kh) // 2, kw, kh, (0, 0, 0, 60) if style == "solid" else (255, 255, 255, 30),
                       tags=tags, cut=self.px(4))
            pad_button = eldorado_icons.PAD_GLYPHS.get(key_hint)
            if pad_button:  # the PlayStation buttons drawn in their colors
                size = self.px(14)
                self.canvas.create_image(kx + kw // 2, y + h // 2, tags=all_tags, image=self.photo(
                    ("icon", pad_button, size), lambda: eldorado_icons.icon(pad_button, size)))
            else:
                self.canvas.create_text(kx + kw // 2, y + h // 2, text=key_hint, font=self.f_hint, fill=ink,
                                        tags=all_tags)
        return w, h

    def fonts(self):
        w, _ = self.size
        stage = max(400, w - self.rail_width())
        self.f_brand = ("Georgia", max(14, int(17 * self.s)), "bold")
        self.f_tag = ("Bahnschrift", max(7, int(7.5 * self.s)))
        self.f_top = ("Bahnschrift SemiBold", max(10, int(11 * self.s)))
        self.f_kicker = ("Bahnschrift SemiBold", max(10, int(12 * self.s)))
        self.f_coord = ("Bahnschrift", max(8, int(9.5 * self.s)))
        self.f_huge = ("Georgia", max(26, int(min(stage / 24, 52))), "bold")
        self.f_title = ("Georgia", max(16, int(20 * self.s)), "bold")
        self.f_big = ("Bahnschrift SemiBold", max(12, int(14 * self.s)))
        self.f_body = ("Segoe UI", max(9, int(10.5 * self.s)))
        self.f_small = ("Segoe UI", max(8, int(9 * self.s)))
        self.f_hint = ("Bahnschrift", max(7, int(8 * self.s)))
        self.f_play = ("Georgia", max(14, int(17 * self.s)), "bold")
        self.f_numeral = ("Georgia", max(17, int(22 * self.s)), "bold")
        self.f_rail = ("Bahnschrift SemiBold", max(9, int(10.5 * self.s)))
        self.f_rail_sub = ("Bahnschrift", max(7, int(8 * self.s)))
        self.f_glyph = ("Segoe UI Symbol", max(11, int(13 * self.s)))
        self.f_entry = ("Bahnschrift SemiBold", max(9, int(10 * self.s)))

    def draw(self):
        if self.size[0] < 50:
            return
        self.canvas.delete("ui")
        if len(self.photos) > 220:  # between draws, so no picture of this one goes blank
            self.photos.clear()
        self.fonts()
        if self.screen == "settings":
            w, h = self.size
            self.canvas.create_rectangle(self.rail_width(), 0, w, h, fill=self.m.BG, outline="", tags="ui")
        self.draw_rail()
        if self.screen == "games":
            self.draw_games()
        elif self.screen == "saves":
            self.draw_saves()
        elif self.screen == "trophies":
            self.draw_trophies()
        elif self.screen == "gallery":
            self.draw_gallery()
        self.draw_bottom()
        if self.loading:
            self.draw_loading()

    # -- the rail ------------------------------------------------------------------------

    def draw_rail(self):
        w, h = self.size
        rw = self.rail_width()
        slim = self.screen == "settings"
        accent = ACCENTS.get(self.game, ACCENTS["u1"])
        self.canvas.create_image(0, 0, anchor="nw", tags="ui",
                                 image=self.photo(("rail", rw, h, self.game), lambda: rail_texture((rw, h), accent)))
        # Its edge: a gold hairline and a shadow over the stage.
        def edge_shadow():
            sw = self.px(22)
            image = Image.new("RGBA", (sw, h), (0, 0, 0, 0))
            image.putalpha(Image.linear_gradient("L").rotate(90).resize((sw, h)).point(
                lambda p: int(150 * (1 - p / 255) ** 2)))
            return image
        self.canvas.create_image(rw, 0, anchor="nw", tags="ui", image=self.photo(("rail-shadow", h), edge_shadow))
        self.canvas.create_line(rw, 0, rw, h, fill=self.accent(), width=1, tags="ui")
        # The emblem and the name.
        size = self.px(46) if not slim else self.px(42)
        emblem = self.photo(("compass", size, self.game), lambda: compass(size, accent))
        if slim:
            self.canvas.create_image(rw // 2, self.px(26), image=emblem, anchor="n", tags=("ui", "click:rail=0"))
        else:
            self.canvas.create_image(self.px(26), self.px(28), image=emblem, anchor="nw", tags="ui")
            self.canvas.create_text(self.px(84), self.px(30), text="EL  DORADO", font=self.f_brand, fill=self.accent(),
                                    anchor="nw", tags="ui")
            self.canvas.create_text(self.px(85), self.px(58), text="T H E   C O L L E C T I O N", font=self.f_tag,
                                    fill=FAINT, anchor="nw", tags="ui")
        items = self.rail_items()
        y = self.px(118)
        games = [i for i, item in enumerate(items) if item[0] == "game"]
        if not slim:
            self.canvas.create_text(self.px(28), y, text="EXPEDITIONS", font=self.f_tag, fill=FAINT, anchor="nw",
                                    tags="ui")
            y += self.px(20)
        row = self.px(68) if not slim else self.px(54)
        for index in games:
            self.rail_game_row(index, items[index][1], y, row, rw, slim)
            y += row
        # A rule with a diamond at its middle.
        y += self.px(14)
        x1, x2 = self.px(24 if not slim else 18), rw - self.px(24 if not slim else 18)
        self.canvas.create_line(x1, y, x2, y, fill="#3d3022", tags="ui")
        d = self.px(4)
        mx = (x1 + x2) // 2
        self.canvas.create_polygon(mx, y - d, mx + d, y, mx, y + d, mx - d, y, fill=self.accent(), outline="",
                                   tags="ui")
        y += self.px(18)
        nav = self.px(46) if not slim else self.px(50)
        pinned = [i for i, item in enumerate(items) if item[0] in ("logs", "quit")]
        middle = len(items) - len(games) - len(pinned)
        room = h - self.px(24) - nav * len(pinned) - self.px(8) - y
        if middle and room < nav * middle:
            nav = max(self.px(30), room // middle)
        for index, item in enumerate(items):
            if item[0] == "game" or index in pinned:
                continue
            self.rail_nav_row(index, item[0], y, nav, rw, slim)
            y += nav
        y = h - self.px(24) - nav * len(pinned)
        for index in pinned:
            self.rail_nav_row(index, items[index][0], y, nav, rw, slim)
            y += nav

    def rail_band(self, index, y, row, rw, selected, key=None):
        focused = self.focus_zone == "top" and self.top_index == index
        r, g, b = ACCENTS.get(key or self.game, ACCENTS["u1"])
        if selected or focused:
            fill = (r, g, b, 40 if selected else 18)
            outline = (r, g, b, 255) if focused else None
            self.plate(self.px(10), y + self.px(3), rw - self.px(20), row - self.px(6), fill, outline=outline,
                       width=max(1, self.px(2)), tags=(f"click:rail={index}",), cut=self.px(9))
        if selected:
            self.canvas.create_rectangle(self.px(10), y + self.px(12), self.px(13), y + row - self.px(12),
                                         fill=f"#{r:02x}{g:02x}{b:02x}", outline="", tags="ui")

    def rail_game_row(self, index, key, y, row, rw, slim):
        info = self.game_info(key)
        selected = key == self.game
        tag = f"click:rail={index}"
        self.rail_band(index, y, row, rw, selected, key)
        # An invisible plate keeps the whole row clickable.
        self.canvas.create_rectangle(0, y, rw - 1, y + row, fill="", outline="", tags=("ui", tag))
        numeral = NUMERALS.get(info["number"], info["number"])
        colour = self.accent(key) if selected else FAINT
        if slim:
            self.canvas.create_text(rw // 2, y + row // 2, text=numeral, font=self.f_numeral, fill=colour,
                                    tags=("ui", tag))
            return
        self.canvas.create_text(self.px(46), y + row // 2, text=numeral, font=self.f_numeral, fill=colour,
                                tags=("ui", tag))
        title = " ".join(word.capitalize() for word in info["title"].split())
        self.canvas.create_text(self.px(82), y + row // 2 - self.px(9), text=title.upper(), font=self.f_rail,
                                fill=INK if selected else DIM, anchor="w", tags=("ui", tag))
        count = len(self.saves(key))
        sub = f"UNCHARTED {info['number']}" + (f"   ·   {count} SAVE{'S' if count != 1 else ''}" if count else "")
        self.canvas.create_text(self.px(83), y + row // 2 + self.px(11), text=sub, font=self.f_rail_sub,
                                fill=FAINT, anchor="w", tags=("ui", tag))

    def rail_nav_row(self, index, kind, y, row, rw, slim):
        tag = f"click:rail={index}"
        selected = kind == self.screen
        self.rail_band(index, y, row, rw, selected)
        self.canvas.create_rectangle(0, y, rw - 1, y + row, fill="", outline="", tags=("ui", tag))
        glyph, label = RAIL_NAV[kind]
        colour = "#5fc48a" if kind == "update" else (self.accent() if selected else DIM)
        # El Dorado's own drawn icons (eldorado_icons.py), not a symbol font.
        size = self.px(24)
        picture = self.photo(("icon", kind, size, colour), lambda: eldorado_icons.icon(kind, size, colour))
        if slim:
            self.canvas.create_image(rw // 2, y + row // 2, image=picture, tags=("ui", tag))
            return
        self.canvas.create_image(self.px(46), y + row // 2, image=picture, tags=("ui", tag))
        self.canvas.create_text(self.px(82), y + row // 2, text=label, font=self.f_rail,
                                fill=INK if selected else colour if kind == "update" else DIM, anchor="w",
                                tags=("ui", tag))

    # -- the bottom line -----------------------------------------------------------------

    def draw_bottom(self):
        """The status line and this screen's actions, as buttons."""
        w, h = self.size
        y = h - self.px(48)
        status = self.status_text()
        x = self.rail_width() + self.px(36)
        if self.screen == "games":
            actions = [("do=down", "SAVES", self.hint("down")), ("do=alt", "SETTINGS", self.hint("alt"))]
        elif self.screen == "saves":
            if self.show_backups:
                actions = [("do=ok", "PRESS AGAIN TO RESTORE" if self.armed_delete else "RESTORE COPY",
                            self.hint("ok")),
                           ("do=view_saves", "BACK TO SAVES", self.hint("alt"))]
            elif self.show_deleted:
                actions = [("do=ok", "RESTORE", self.hint("ok")),
                           ("do=delete", "PRESS AGAIN TO DELETE FOREVER" if self.armed_delete else "DELETE FOREVER",
                            self.hint("delete")),
                           ("do=view_backups", "BACKUPS", self.hint("alt"))]
            else:
                actions = [("do=delete", "PRESS AGAIN TO DELETE" if self.armed_delete else "DELETE",
                            self.hint("delete")),
                           ("do=view_deleted", "DELETED SAVES", self.hint("alt")),
                           ("do=view_backups", "BACKUPS", None)]
            actions.append(("do=back", "BACK", self.hint("back")))
        elif self.screen == "trophies":
            actions = [("do=back", "BACK", self.hint("back"))]
        elif self.screen == "gallery":
            actions = [("do=ok", "OPEN", self.hint("ok")),
                       ("do=delete", "PRESS AGAIN TO DELETE" if self.armed_delete else "DELETE", self.hint("delete")),
                       ("do=alt", "OPEN FOLDER", self.hint("alt")),
                       ("do=back", "BACK", self.hint("back"))]
        else:
            # On the pages the keyboard belongs to them (Controls captures keys): Back is the controller's.
            style = self.launcher.game_settings().get("prompts", "auto")
            pad_hint = self.hint("back") if style in ("playstation", "xbox") or self.last_device == "pad" else None
            actions = [("rail=" + str(self.rail_items().index(("game", self.game))), "BACK", pad_hint)]
        rx = w - self.px(36)
        for tag, label, hint in reversed(actions):
            danger = label.startswith("PRESS AGAIN")
            bw, _ = self.button(rx, y, label, self.f_top, style="solid" if danger else "ghost",
                                accent="#c8463c" if danger else None, key_hint=hint, tags=(f"click:{tag}",),
                                anchor="ne")
            rx -= bw + self.px(10)
        if self.screen != "settings":  # the status line in what the buttons leave free
            self.canvas.create_text(x, y + self.px(18), text=status, font=self.f_small, fill=DIM, anchor="w",
                                    tags="ui", width=max(self.px(80), rx - x - self.px(10)))

    # -- games ---------------------------------------------------------------------------

    def draw_games(self):
        w, h = self.size
        rw = self.rail_width()
        info = self.game_info()
        accent = self.accent()
        x = rw + self.px(64)
        stage = w - x - self.px(48)
        top = int(h * 0.15)
        # Where the expedition goes: a diamond and the coordinates.
        d = self.px(4)
        cy = top + self.px(7)
        self.canvas.create_polygon(x + d, cy - d, x + 2 * d, cy, x + d, cy + d, x, cy, fill=accent, outline="",
                                   tags="ui")
        self.canvas.create_text(x + self.px(16), cy, text=PLACES.get(self.game, ""), font=self.f_coord, fill=accent,
                                anchor="w", tags="ui")
        self.canvas.create_text(x, top + self.px(28), text=f"UNCHARTED {info['number']}", font=self.f_kicker,
                                fill=DIM, anchor="nw", tags="ui")
        title = self.canvas.create_text(x - self.px(3), top + self.px(48), text=info["title"], font=self.f_huge,
                                        fill=INK, anchor="nw", width=stage, tags="ui")
        y = self.canvas.bbox(title)[3] + self.px(14)
        self.canvas.create_rectangle(x, y, x + self.px(72), y + max(2, self.px(3)), fill=accent, outline="",
                                     tags="ui")
        facts = self.game_facts()
        if facts:  # a dark copy under it: readable over any picture
            self.canvas.create_text(x + self.px(89), y + self.px(2), text="   ·   ".join(facts), font=self.f_hint,
                                    fill="#000000", anchor="w", tags="ui")
            self.canvas.create_text(x + self.px(88), y + self.px(1), text="   ·   ".join(facts), font=self.f_hint,
                                    fill=INK, anchor="w", tags=("ui", "click:rail=" + str(self.rail_items().index(
                                        ("trophies", None)))))
        y += self.px(22)
        saves = self.saves()
        if saves:
            latest = saves[0]
            self.canvas.create_text(x, y, text="CONTINUE", font=self.f_hint, fill=accent, anchor="nw", tags="ui")
            self.canvas.create_text(x, y + self.px(16), text=latest["chapter"], font=self.f_big, fill=INK,
                                    anchor="nw", tags="ui", width=int(stage * 0.8))
            lines = [line for line in latest["detail"].splitlines() if line.strip()] + [when(latest["mtime"])]
            self.canvas.create_text(x, y + self.px(42), text="   ·   ".join(lines), font=self.f_body, fill=DIM,
                                    anchor="nw", tags="ui", width=int(stage * 0.85))
        else:
            self.canvas.create_text(x, y + self.px(6), text="No saves yet. The expedition starts here.",
                                    font=self.f_big, fill=DIM, anchor="nw", tags="ui")
        running = self.running()
        by = y + self.px(82)
        bw, bh = self.px(232), self.px(58)
        focused = self.focus_zone == "main"
        r, g, b = ACCENTS.get(self.game)
        fill = (196, 70, 58, 245) if running else (r, g, b, 250)
        self.plate(x, by, bw, bh, fill, outline=(255, 244, 214, 240) if focused else None,
                   width=self.px(2), tags=("click:do=play",), cut=self.px(14))
        self.canvas.create_text(x + bw // 2, by + bh // 2, text="■   STOP" if running else "▶   PLAY",
                                font=self.f_play, fill="#ffffff" if running else "#17120a",
                                tags=("ui", "click:do=play"))
        hint = self.hint("ok")
        if hint and not running:
            self.canvas.create_text(x + bw + self.px(16), by + bh // 2, text=f"{hint}  to start", font=self.f_small,
                                    fill=FAINT, anchor="w", tags="ui")
        self.draw_log(x, by + bh, stage, saves)

    def game_facts(self):
        """Play time, last play, average FPS (from the launcher's play stats) and trophies."""
        facts = []
        entry = read_stats(self.m.USER_DIR).get(self.game) or {}
        if entry.get("seconds"):
            facts.append(f"{played(entry['seconds'])} PLAYED")
        if entry.get("last"):
            facts.append(f"LAST PLAYED {ago(entry['last'])}")
        if entry.get("fps_count"):
            facts.append(f"{entry['fps_sum'] / entry['fps_count']:.0f} FPS AVERAGE")
        data = self.trophies()
        if data:
            facts.append(f"TROPHIES {data[2]['percent']}%")
        return facts

    def draw_log(self, x, above, stage, saves):
        """The expedition log: the latest saves along the bottom, each opening the Saves screen."""
        if not saves:
            return
        w, h = self.size
        count = max(1, min(3, len(saves), (stage + self.px(20)) // self.px(230)))
        tw = min(self.px(220), (stage - self.px(20) * (count - 1)) // count)
        th = int(tw * 9 / 16)
        caption = self.px(38)
        top = h - self.bottom_height() - self.px(22) - th - caption
        if top - self.px(30) < above + self.px(24):
            return  # no room under PLAY in a short window
        self.canvas.create_text(x, top - self.px(24), text="EXPEDITION LOG", font=self.f_entry, fill=self.accent(),
                                anchor="nw", tags="ui")
        more = len(saves) - count
        if more > 0:
            self.canvas.create_text(x + self.px(132), top - self.px(24), text=f"+{more} MORE  ›", font=self.f_entry,
                                    fill=FAINT, anchor="nw", tags=("ui", "click:log=0"))
        for index, save in enumerate(saves[:count]):
            tx = x + index * (tw + self.px(20))
            tag = f"click:log={index}"
            self.canvas.create_image(tx, top, anchor="nw", tags=("ui", tag),
                                     image=self.card_image(self.game, (tw, th), save["picture"]))
            self.canvas.create_text(tx, top + th + self.px(8), text=save["chapter"], font=self.f_small, fill=DIM,
                                    anchor="nw", width=tw, tags=("ui", tag))

    # -- saves ---------------------------------------------------------------------------

    def save_columns(self):
        return 1

    def draw_saves(self):
        w, h = self.size
        rw = self.rail_width()
        x0 = rw + self.px(52)
        top = self.px(40)
        info = self.game_info()
        accent = self.accent()
        saves = self.saves(view=self.view)
        kicker = {"deleted": "DELETED ENTRIES", "backups": "BACKUP COPIES  ·  MADE BEFORE EACH START"}.get(
            self.view, "EXPEDITION LOG")
        self.canvas.create_text(x0, top, text=kicker, font=self.f_kicker, fill=accent, anchor="nw", tags="ui")
        name = self.canvas.create_text(x0, top + self.px(20), text=info["name"], font=self.f_title, fill=INK,
                                       anchor="nw", tags="ui")
        count = f"{len(saves)} {'entry' if len(saves) == 1 else 'entries'}"
        self.canvas.create_text(self.canvas.bbox(name)[2] + self.px(16), self.canvas.bbox(name)[3] - self.px(4),
                                text=count, font=self.f_small, fill=FAINT, anchor="sw", tags="ui")
        ly = self.canvas.bbox(name)[3] + self.px(22)
        lh = h - ly - self.bottom_height() - self.px(14)
        if not saves:
            text = {"deleted": "No deleted saves.",
                    "backups": "No backups yet: each save is copied before the game starts."}.get(
                self.view, "No saves for this game yet.")
            self.canvas.create_text(x0, ly + self.px(20), text=text, font=self.f_big, fill=DIM, anchor="nw", tags="ui")
            return
        stage = w - x0 - self.px(44)
        # A dark plate under the log: the text stays readable over any picture.
        self.plate(x0 - self.px(20), ly - self.px(18), stage + self.px(40), lh + self.px(24), (12, 9, 6, 185),
                   outline=(120, 98, 66, 120), cut=self.px(18))
        lw = int(stage * 0.56)
        row = self.px(76)
        visible = max(1, lh // row)
        self.save_index = min(self.save_index, len(saves) - 1)
        first = max(0, self.save_index - visible + 1)
        r, g, b = ACCENTS.get(self.game)
        for index in range(first, min(len(saves), first + visible)):
            save = saves[index]
            y = ly + (index - first) * row
            tag = f"click:save={index}"
            selected = index == self.save_index
            armed = self.armed_delete == ("restore:" + str(save["folder"]) if self.show_backups else
                                          str(save["folder"]) if self.show_deleted else save["dir"])
            if selected:
                fill = (200, 70, 60, 70) if armed else (r, g, b, 38)
                outline = (r, g, b, 255) if self.focus_zone == "main" else None
                self.plate(x0, y, lw, row - self.px(8), fill, outline=outline, width=max(1, self.px(2)), tags=(tag,),
                           cut=self.px(10))
                self.canvas.create_rectangle(x0, y + self.px(10), x0 + self.px(3), y + row - self.px(18),
                                             fill=accent, outline="", tags=("ui", tag))
            else:
                self.canvas.create_line(x0 + self.px(14), y + row - self.px(4), x0 + lw - self.px(14),
                                        y + row - self.px(4), fill="#33281c", tags=("ui", tag))
            self.canvas.create_rectangle(x0, y, x0 + lw, y + row - self.px(8), fill="", outline="", tags=("ui", tag))
            self.canvas.create_text(x0 + self.px(18), y + self.px(14), text=f"No.{index + 1:02d}", font=self.f_entry,
                                    fill=accent if selected else FAINT, anchor="nw", tags=("ui", tag))
            self.canvas.create_text(x0 + self.px(78), y + self.px(10), text=save["chapter"], font=self.f_big,
                                    fill=INK if selected else DIM, anchor="nw", width=lw - self.px(92),
                                    tags=("ui", tag))
            if armed:
                detail, colour = ("PRESS OK AGAIN: THIS COPY REPLACES THE SAVE" if self.show_backups else
                                  "PRESS DELETE AGAIN TO REMOVE IT FOR GOOD" if self.show_deleted
                                  else "PRESS DELETE AGAIN TO DELETE"), "#ff8a7a"
            else:
                parts = [line for line in save["detail"].splitlines() if line.strip()] + [
                    time.strftime("%d %b %H:%M", time.localtime(save["mtime"])) if self.show_backups
                    else when(save["mtime"])[:10]]
                detail, colour = "  ·  ".join(parts), FAINT
            self.canvas.create_text(x0 + self.px(78), y + self.px(40), text=detail, font=self.f_small, fill=colour,
                                    anchor="nw", width=lw - self.px(92), tags=("ui", tag))
        if len(saves) > visible:
            self.canvas.create_text(x0 + lw, ly + visible * row + self.px(2), anchor="ne", font=self.f_small,
                                    fill=FAINT, tags="ui", text=f"{self.save_index + 1} / {len(saves)}")
        # The selected entry, large.
        save = saves[self.save_index]
        px0 = x0 + lw + self.px(36)
        pw = w - px0 - self.px(44)
        ph = int(pw * 9 / 16)
        if ph > lh - self.px(120):
            ph = max(self.px(80), lh - self.px(120))
            pw = int(ph * 16 / 9)
        self.canvas.create_image(px0, ly, anchor="nw", tags="ui",
                                 image=self.card_image(self.game, (pw, ph), save["picture"], selected=True))
        item = self.canvas.create_text(px0, ly + ph + self.px(16), text=save["chapter"], font=self.f_big, fill=INK,
                                       anchor="nw", width=pw, tags="ui")
        parts = [line for line in save["detail"].splitlines() if line.strip()]
        item = self.canvas.create_text(px0, self.canvas.bbox(item)[3] + self.px(6), text="   ·   ".join(parts),
                                       font=self.f_body, fill=DIM, anchor="nw", width=pw, tags="ui")
        self.canvas.create_text(px0, self.canvas.bbox(item)[3] + self.px(6),
                                text=when(save["mtime"]) + f"     {save['dir']}", font=self.f_small, fill=FAINT,
                                anchor="nw", width=pw, tags="ui")

    # -- trophies ------------------------------------------------------------------------

    def page_header(self, kicker, extra=""):
        rw = self.rail_width()
        x0, top = rw + self.px(52), self.px(40)
        self.canvas.create_text(x0, top, text=kicker, font=self.f_kicker, fill=self.accent(), anchor="nw", tags="ui")
        name = self.canvas.create_text(x0, top + self.px(20), text=self.game_info()["name"], font=self.f_title,
                                       fill=INK, anchor="nw", tags="ui")
        box = self.canvas.bbox(name)
        if extra:
            self.canvas.create_text(box[2] + self.px(16), box[3] - self.px(4), text=extra, font=self.f_small,
                                    fill=FAINT, anchor="sw", tags="ui")
        return x0, box[3] + self.px(22)

    def draw_trophies(self):
        w, h = self.size
        data = self.trophies()
        rows = self.trophy_rows()
        x0, ly = self.page_header("TROPHIES", f"{data[2]['count']} of {len(rows)} earned" if data else "")
        if not data:
            self.canvas.create_text(x0, ly + self.px(20), font=self.f_big, fill=DIM, anchor="nw", tags="ui",
                                    text="No trophy list: the game folder has no sce_sys/trophy pack for this game.")
            return
        info, unlocked, progress, folder = data
        stage = w - x0 - self.px(44)
        lh = h - ly - self.bottom_height() - self.px(14)
        self.plate(x0 - self.px(20), ly - self.px(18), stage + self.px(40), lh + self.px(24), (12, 9, 6, 185),
                   outline=(120, 98, 66, 120), cut=self.px(18))
        # Left column: the progress and the count of each grade.
        cw = min(self.px(250), int(stage * 0.3))
        accent = self.accent()
        self.canvas.create_text(x0, ly, text=f"{progress['percent']}%", font=self.f_huge, fill=INK, anchor="nw",
                                tags="ui")
        by = ly + self.px(70)
        bar = max(3, self.px(6))
        self.canvas.create_rectangle(x0, by, x0 + cw, by + bar, fill="#33281c", outline="", tags="ui")
        self.canvas.create_rectangle(x0, by, x0 + int(cw * progress["percent"] / 100), by + bar, fill=accent,
                                     outline="", tags="ui")
        gy = by + self.px(22)
        for grade in "PGSB":
            if not progress["total"][grade]:
                continue
            label, colour = GRADES[grade]
            self.canvas.create_text(x0, gy, text="●", font=self.f_body, fill=colour, anchor="nw", tags="ui")
            self.canvas.create_text(x0 + self.px(20), gy, text=label, font=self.f_entry, fill=DIM, anchor="nw",
                                    tags="ui")
            self.canvas.create_text(x0 + cw, gy, text=f"{progress['earned'][grade]} / {progress['total'][grade]}",
                                    font=self.f_entry, fill=INK, anchor="ne", tags="ui")
            gy += self.px(26)
        # Right: the list.
        lx = x0 + cw + self.px(36)
        lw = x0 + stage - lx
        row = self.px(66)
        visible = max(1, lh // row)
        self.save_index = min(self.save_index, len(rows) - 1)
        first = max(0, self.save_index - visible + 1)
        icon = self.px(48)
        r, g, b = ACCENTS.get(self.game)
        for index in range(first, min(len(rows), first + visible)):
            number, grade, hidden, name, detail, earned = rows[index]
            y = ly + (index - first) * row
            tag = f"click:pick={index}"
            selected = index == self.save_index
            if selected:
                self.plate(lx, y, lw, row - self.px(6), (r, g, b, 38),
                           outline=(r, g, b, 255) if self.focus_zone == "main" else None, width=max(1, self.px(2)),
                           tags=(tag,), cut=self.px(10))
            self.canvas.create_rectangle(lx, y, lx + lw, y + row - self.px(6), fill="", outline="", tags=("ui", tag))
            self.canvas.create_image(lx + self.px(10), y + (row - self.px(6)) // 2, anchor="w", tags=("ui", tag),
                                     image=self.trophy_icon(folder, number, icon, bool(earned)))
            secret = hidden and not earned
            tx = lx + self.px(10) + icon + self.px(14)
            label, colour = GRADES.get(grade, GRADES["B"])
            when_text = time.strftime("%d %b %Y", time.localtime(earned)) if earned and earned > 1 else \
                ("EARNED" if earned else "LOCKED")
            self.canvas.create_text(lx + lw - self.px(14), y + self.px(12), text=when_text, font=self.f_hint,
                                    fill=accent if earned else FAINT, anchor="ne", tags=("ui", tag))
            self.canvas.create_text(tx, y + self.px(9), text=("Hidden trophy" if secret else name), font=self.f_big,
                                    fill=INK if earned else DIM, anchor="nw", width=lw - (tx - lx) - self.px(110),
                                    tags=("ui", tag))
            self.canvas.create_text(tx, y + self.px(33), anchor="nw", width=lw - (tx - lx) - self.px(20),
                                    text=(f"{label}  ·  " + ("Keep playing to find it." if secret else detail)),
                                    font=self.f_small, fill=colour if earned else FAINT, tags=("ui", tag))
        if len(rows) > visible:
            self.canvas.create_text(lx + lw, ly + visible * row + self.px(2), anchor="ne", font=self.f_small,
                                    fill=FAINT, tags="ui", text=f"{self.save_index + 1} / {len(rows)}")

    # -- gallery -------------------------------------------------------------------------

    def draw_gallery(self):
        w, h = self.size
        shots = self.shots()
        x0, ly = self.page_header("GALLERY", f"{len(shots)} screenshot{'' if len(shots) == 1 else 's'}")
        if not shots:
            self.canvas.create_text(x0, ly + self.px(20), font=self.f_big, fill=DIM, anchor="nw", tags="ui",
                                    text="No screenshots yet: press F12 in the game to take one.")
            return
        stage = w - x0 - self.px(44)
        lh = h - ly - self.bottom_height() - self.px(14)
        gap = self.px(18)
        cols = max(1, (stage + gap) // (self.px(250) + gap))
        self.grid_columns = cols
        tw = (stage - gap * (cols - 1)) // cols
        th = int(tw * 9 / 16)
        caption = self.px(26)
        row = th + caption + gap
        visible_rows = max(1, (lh + gap) // row)
        self.plate(x0 - self.px(20), ly - self.px(18), stage + self.px(40), lh + self.px(24), (12, 9, 6, 185),
                   outline=(120, 98, 66, 120), cut=self.px(18))
        self.save_index = min(self.save_index, len(shots) - 1)
        first_row = max(0, self.save_index // cols - visible_rows + 1)
        for index in range(first_row * cols, min(len(shots), (first_row + visible_rows) * cols)):
            shot = shots[index]
            r, c = divmod(index, cols)
            tx, ty = x0 + c * (tw + gap), ly + (r - first_row) * row
            tag = f"click:pick={index}"
            selected = index == self.save_index
            armed = selected and self.armed_delete == "shot:" + str(shot)
            self.canvas.create_image(tx, ty, anchor="nw", tags=("ui", tag),
                                     image=self.card_image(self.game, (tw, th), shot,
                                                           selected=selected and self.focus_zone == "main"))
            try:
                stamp = time.strftime("%d %b %Y  %H:%M", time.localtime(shot.stat().st_mtime))
            except OSError:
                stamp = shot.stem
            self.canvas.create_text(tx, ty + th + self.px(6), anchor="nw", tags=("ui", tag), font=self.f_small,
                                    text="PRESS DELETE AGAIN TO DELETE" if armed else stamp,
                                    fill="#ff8a7a" if armed else INK if selected else FAINT)
        rows_total = (len(shots) + cols - 1) // cols
        if rows_total > visible_rows:
            self.canvas.create_text(x0 + stage, ly + visible_rows * row - self.px(4), anchor="ne", font=self.f_small,
                                    fill=FAINT, tags="ui", text=f"{self.save_index + 1} / {len(shots)}")


    # -- loading -------------------------------------------------------------------------

    def draw_loading(self):
        """From PLAY until the game's window opens: the game's own screen over the hub (its picture, its
        logo, its name), a moving gold bar, what the start is doing."""
        w, h = self.size
        key = self.loading["key"]
        info = self.game_info(key)
        accent = self.accent(key)

        def make():
            image = self.background(key).convert("RGBA").resize((w, h))
            image = Image.alpha_composite(image, Image.new("RGBA", (w, h), (10, 7, 4, 205)))
            return image
        self.canvas.create_image(0, 0, anchor="nw", tags="ui", image=self.photo(("loading-bg", key, w, h), make))
        cx, cy = w // 2, int(h * 0.42)
        logo = self.logo(key)
        if logo is not None:
            size = self.px(220)
            picture = self.photo(("loading-logo", key, size), lambda: self.fit_logo(logo, size))
            self.canvas.create_image(cx, cy - self.px(70), image=picture, tags="ui")
        self.canvas.create_text(cx, cy + self.px(60), text=f"UNCHARTED {info['number']}", font=self.f_kicker,
                                fill=accent, tags="ui")
        self.canvas.create_text(cx, cy + self.px(96), text=info["title"], font=self.f_title, fill=INK, tags="ui")
        # The bar: a gold run sliding along a dark track (the start has no steps to count).
        bw, bh = self.px(420), max(3, self.px(4))
        bx, by = cx - bw // 2, cy + self.px(140)
        self.canvas.create_rectangle(bx, by, bx + bw, by + bh, fill="#2b2016", outline="", tags="ui")
        elapsed = time.monotonic() - self.loading["since"]
        run = bw // 4
        x = bx + int(((elapsed * 0.55) % 1.0) * (bw + run)) - run
        self.canvas.create_rectangle(max(bx, x), by, min(bx + bw, x + run), by + bh, fill=accent, outline="",
                                     tags="ui")
        status = self.status_text() or "Starting..."
        self.canvas.create_text(cx, by + self.px(26), text=status, font=self.f_small, fill=DIM, tags="ui",
                                width=bw + self.px(200))

    def fit_logo(self, logo, size):
        copy = logo.convert("RGBA").copy()
        copy.thumbnail((size, size), Image.LANCZOS)
        return copy


def start(root, module):
    """El Dorado's window, with the classic launcher's pages inside it."""
    hub = Hub(root, module)
    # However the window goes, the embedded launcher's frame must not close it a second time.
    destroy = root.destroy

    def closing():
        hub.settings_frame.closing = True
        destroy()
    root.destroy = closing
    return hub
