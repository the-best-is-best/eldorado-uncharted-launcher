# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""The Collection (or each game) in the Steam library as a non-Steam game.

Steam keeps non-Steam games in <Steam>/userdata/<account>/config/shortcuts.vdf (binary VDF) and their library
pictures in config/grid/<app id>*.png. Steam reads the file when it starts and writes its own copy when it exits, so
Steam is closed first (steam_running(); shut_down_steam() asks it to exit, start_steam() opens it again).

The file is read and written losslessly: every entry this launcher did not make keeps its exact bytes, field types
Steam rarely uses included. Each write keeps a dated backup (the newest KEEP_BACKUPS).

Pictures come only from the player's own game files (sce_sys/pic1.png or pic0.png, icon0.png, and for one game's
entry that game's emblem, ICON0.PNG of its trophy pack) and from the game's own icon on its window (the loading icon
the engine takes from the game, or El Dorado's drawing of it), which is also that entry's icon in Steam's list.
Nothing is downloaded, and a picture the player already set is never replaced; ours carry PICTURE_MARK and are
made again.
"""
from __future__ import annotations

import binascii
import io
import os
import re
import struct
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

COLLECTION_NAME = "Uncharted: The Nathan Drake Collection"
BACKUP_SUFFIX = ".uncharted-backup"
KEEP_BACKUPS = 5
# The files that start this launcher, in an entry's command (the released launcher's too, so its entries are
# taken over when the package moves).
LAUNCHER_FILES = ("uncharted launcher.exe", "uncharted_launcher.pyw", "launcher\\main.py", "launcher/main.py")

# Binary VDF node types: shortcuts.vdf uses maps, strings and 32-bit numbers; the rest are kept as raw bytes.
MAP, STRING, INT32, FLOAT32, POINTER, WSTRING, COLOR, UINT64, END, INT64 = 0, 1, 2, 3, 4, 5, 6, 7, 8, 10
RAW_SIZES = {FLOAT32: 4, POINTER: 4, COLOR: 4, UINT64: 8, INT64: 8}

TALL = (600, 900)     # <id>p.png: the portrait capsule
WIDE = (920, 430)     # <id>.png: the wide capsule
HERO = (1920, 620)    # <id>_hero.png: the banner behind the game page
LOGO_WIDTH = 1280     # <id>_logo.png: the title over the banner (transparent)
PICTURE_MARK = ("Software", "El Dorado")  # a PNG text field: the library pictures this launcher made


class SteamError(Exception):
    """kind: "no_steam" (no Steam account on this PC) or "bad_file" (a shortcuts.vdf that cannot be read)."""

    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind
        self.detail = detail


@dataclass
class Node:
    """One VDF value. A map's value is a list of nodes; strings and keys are str (bytes that are not UTF-8 survive
    as surrogates); INT32 is an int; the rarer types are their raw bytes."""
    kind: int
    key: str
    value: Any


@dataclass(frozen=True)
class Target:
    """What one Steam entry starts."""
    name: str
    exe: str        # quoted, as Steam stores it
    start_dir: str  # quoted
    options: str
    emblem: bytes | None = field(default=None, compare=False, repr=False)  # one game's title picture (PNG, alpha)
    icon: Path | None = field(default=None, compare=False)  # one game's own icon (PNG): Steam's icon and its art
    art: Path | None = field(default=None, compare=False)  # its library pictures, made (ui/steam_art.py)


@dataclass
class AccountResult:
    folder: Path
    persona: str
    file: Path
    backup: Path | None
    ids: list[int] = field(default_factory=list)
    added: int = 0
    updated: int = 0
    removed: int = 0
    pictures: int = 0


# --- binary VDF -------------------------------------------------------------------------------------------------

def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", "surrogateescape")


def _encode(text: str) -> bytes:
    return text.encode("utf-8", "surrogateescape")


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def cstring(self) -> str:
        end = self.data.index(b"\0", self.pos)
        text = _decode(self.data[self.pos:end])
        self.pos = end + 1
        return text

    def wstring(self) -> bytes:
        end = self.pos
        while self.data[end:end + 2] != b"\0\0":
            end += 2
            if end >= len(self.data):
                raise ValueError("unterminated wide string")
        raw = self.data[self.pos:end]
        self.pos = end + 2
        return raw

    def take(self, size: int) -> bytes:
        if self.pos + size > len(self.data):
            raise ValueError("the file ends inside a number")
        raw = self.data[self.pos:self.pos + size]
        self.pos += size
        return raw

    def nodes(self) -> list[Node]:
        result: list[Node] = []
        while True:
            if self.pos >= len(self.data):
                raise ValueError("the file ends inside a map")
            kind = self.data[self.pos]
            self.pos += 1
            if kind == END:
                return result
            key = self.cstring()
            result.append(Node(kind, key, self.value(kind)))

    def value(self, kind: int) -> Any:
        if kind == MAP:
            return self.nodes()
        if kind == STRING:
            return self.cstring()
        if kind == WSTRING:
            return self.wstring()
        if kind == INT32:
            return struct.unpack("<I", self.take(4))[0]
        if kind in RAW_SIZES:
            return self.take(RAW_SIZES[kind])
        raise ValueError(f"unknown VDF type {kind} at byte {self.pos - 1}")


def parse_vdf(data: bytes) -> list[Node]:
    reader = _Reader(data)
    tree = reader.nodes()
    if reader.pos != len(data) and data[reader.pos:].strip(b"\0"):
        raise ValueError(f"unexpected data after byte {reader.pos}")
    return tree


def dump_vdf(tree: list[Node]) -> bytes:
    out = bytearray()
    _write_nodes(out, tree)
    return bytes(out)


def _write_nodes(out: bytearray, nodes: list[Node]) -> None:
    for node in nodes:
        out.append(node.kind)
        out += _encode(node.key) + b"\0"
        if node.kind == MAP:
            _write_nodes(out, node.value)
        elif node.kind == STRING:
            out += _encode(node.value) + b"\0"
        elif node.kind == WSTRING:
            out += bytes(node.value) + b"\0\0"
        elif node.kind == INT32:
            out += struct.pack("<I", node.value & 0xFFFFFFFF)
        else:
            out += bytes(node.value)
    out.append(END)


def get(entry: list[Node], name: str, default: Any = None) -> Any:
    """A field by name in any letter case (Steam has written both AppName and appname)."""
    wanted = name.lower()
    return next((node.value for node in entry if node.key.lower() == wanted), default)


def put(entry: list[Node], name: str, kind: int, value: Any) -> None:
    """Sets a field in place when it is there (any letter case), else appends it."""
    wanted = name.lower()
    for node in entry:
        if node.key.lower() == wanted:
            node.kind, node.value = kind, value
            return
    entry.append(Node(kind, name, value))


def shortcuts_of(tree: list[Node]) -> list[Node]:
    """The "shortcuts" map's entries (the map is made when the file was empty)."""
    for node in tree:
        if node.kind == MAP and node.key.lower() == "shortcuts":
            return node.value
    shortcuts = Node(MAP, "shortcuts", [])
    tree.append(shortcuts)
    return shortcuts.value


# --- the entries ------------------------------------------------------------------------------------------------

def app_id(exe: str, name: str) -> int:
    """Steam's id for a non-Steam game (its pictures are named by it): CRC-32 of the quoted executable and the name,
    top bit set."""
    return (binascii.crc32(_encode(exe + name)) & 0xFFFFFFFF) | 0x80000000


def targets(root: Path, starter: Path, python: Path, script: Path,
            games: list[tuple[str, str]] | None = None,
            emblems: dict[str, bytes | None] | None = None,
            icons: dict[str, Path | None] | None = None,
            art: dict[str, Path | None] | None = None) -> list[Target]:
    """One Collection entry (games None), or one per game ((key, name): started with --play <key>, with that game's
    emblem from `emblems` by key). The package's starter when it is there, else the source tree's script under
    pythonw."""
    if starter.is_file():
        exe, base = f'"{starter}"', ""
    else:
        pythonw = python.with_name("pythonw.exe")
        exe, base = f'"{pythonw if pythonw.is_file() else python}"', f'"{script}"'
    start = f'"{root}"'
    if games is None:
        return [Target(COLLECTION_NAME, exe, start, base)]
    emblems, icons, art = emblems or {}, icons or {}, art or {}
    return [Target(name, exe, start, f"{base} --play {key}".strip(), emblems.get(key), icons.get(key), art.get(key))
            for key, name in games]


def new_entry(target: Target, icon: str) -> list[Node]:
    """A shortcut with the fields Steam itself writes, in its order."""
    icon = str(target.icon) if target.icon else icon
    return [Node(INT32, "appid", app_id(target.exe, target.name)), Node(STRING, "AppName", target.name),
            Node(STRING, "Exe", target.exe), Node(STRING, "StartDir", target.start_dir), Node(STRING, "icon", icon),
            Node(STRING, "ShortcutPath", ""), Node(STRING, "LaunchOptions", target.options),
            Node(INT32, "IsHidden", 0), Node(INT32, "AllowDesktopConfig", 1), Node(INT32, "AllowOverlay", 1),
            Node(INT32, "OpenVR", 0), Node(INT32, "Devkit", 0), Node(STRING, "DevkitGameID", ""),
            Node(INT32, "DevkitOverrideAppID", 0), Node(INT32, "LastPlayTime", 0), Node(STRING, "FlatpakAppID", ""),
            Node(MAP, "tags", [])]


def _options(entry: list[Node]) -> str:
    return str(get(entry, "LaunchOptions", "")).strip().lower()


def is_ours(entry: list[Node], exe: str, base: str) -> bool:
    """Started by this launcher: the same executable and, from the source tree, the same script (other Python
    programs started by the same pythonw are left alone)."""
    if str(get(entry, "Exe", "")).strip().strip('"').lower() != exe.strip('"').lower():
        return False
    options = _options(entry)
    if base:
        return options.startswith(base.lower())
    return options == "" or options.startswith("--play")


def is_moved(entry: list[Node], names: set[str]) -> bool:
    """One of this launcher's entries from another folder: one of our names, started by a launcher file."""
    if str(get(entry, "AppName", "")) not in names:
        return False
    command = f"{get(entry, 'Exe', '')} {get(entry, 'LaunchOptions', '')}".lower()
    return any(name in command for name in LAUNCHER_FILES)


@dataclass
class MergeResult:
    ids: list[int]
    added: int = 0
    updated: int = 0
    removed: int = 0


def merge(tree: list[Node], wanted: list[Target], icon: str, all_names: tuple[str, ...] = ()) -> MergeResult:
    """Puts this launcher's entries into the file. An entry it made before (or a moved one) is updated in place:
    only its id, name, paths, icon and options change, so play time, categories and every other field stay.
    Entries of the other kind (per game versus the Collection) and duplicates go. Every other shortcut is
    untouched; the slots are numbered 0, 1, 2... again as Steam does."""
    shortcuts = shortcuts_of(tree)
    exe = wanted[0].exe
    base = wanted[0].options.partition("--play")[0].strip()
    by_options = {target.options.lower(): target for target in wanted}
    options_by_name = {target.name: target.options.lower() for target in wanted}
    names = set(all_names) | set(options_by_name)
    result = MergeResult(ids=[app_id(target.exe, target.name) for target in wanted])
    kept: list[Node] = []
    done: set[str] = set()
    for node in shortcuts:
        entry = node.value if node.kind == MAP else None
        if entry is not None and is_ours(entry, exe, base):
            options: str | None = _options(entry)
        elif entry is not None and is_moved(entry, names):
            options = options_by_name.get(str(get(entry, "AppName", "")))
        else:
            kept.append(node)
            continue
        if options not in by_options or options in done:
            result.removed += 1
            continue
        target = by_options[options]
        for name, kind, value in (("appid", INT32, app_id(target.exe, target.name)), ("AppName", STRING, target.name),
                                  ("Exe", STRING, target.exe), ("StartDir", STRING, target.start_dir),
                                  ("icon", STRING, str(target.icon) if target.icon else icon),
                                  ("LaunchOptions", STRING, target.options)):
            put(entry, name, kind, value)
        kept.append(node)
        done.add(options)
        result.updated += 1
    for target in wanted:
        if target.options.lower() not in done:
            kept.append(Node(MAP, "", new_entry(target, icon)))
            result.added += 1
    for number, node in enumerate(kept):
        node.key = str(number)
    shortcuts[:] = kept
    return result


# --- Steam's folders --------------------------------------------------------------------------------------------

def steam_running() -> bool:
    """Whether steam.exe runs; False when Windows cannot tell."""
    try:
        listing = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"], capture_output=True,
                                 text=True, errors="replace", timeout=15,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return False
    return "steam.exe" in listing.stdout.lower()


def steam_exe(roots: list[Path] | None = None) -> Path | None:
    """steam.exe of the first Steam installation that has one."""
    for root in steam_roots() if roots is None else roots:
        if (root / "steam.exe").is_file():
            return root / "steam.exe"
    return None


def shut_down_steam(exe: Path, wait: float = 40.0) -> bool:
    """Asks Steam to exit the way its own Exit does (steam.exe -shutdown: it writes its lists first) and waits for
    it to be gone. False when it still runs after `wait` seconds."""
    try:
        subprocess.Popen([str(exe), "-shutdown"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        return False
    end = time.monotonic() + wait
    while time.monotonic() < end:
        time.sleep(1.0)
        if not steam_running():
            time.sleep(1.0)  # its helper processes finish writing
            return True
    return False


def start_steam(exe: Path) -> bool:
    """Opens Steam again, apart from this launcher (it stays open when the launcher closes)."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        subprocess.Popen([str(exe)], cwd=str(exe.parent), creationflags=flags, close_fds=True)
    except OSError:
        return False
    return True


def steam_roots() -> list[Path]:
    """Steam installation folders: the registry's first, then the usual places."""
    roots: list[Path] = []
    try:
        import winreg
    except ImportError:
        winreg = None  # type: ignore[assignment]
    if winreg is not None:
        for hive, key_path, value in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                      (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                                      (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")):
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    roots.append(Path(winreg.QueryValueEx(key, value)[0]))
            except OSError:
                continue  # that registry key is not there: Steam installed another way
    for variable in ("ProgramFiles(x86)", "ProgramFiles"):
        if os.environ.get(variable):
            roots.append(Path(os.environ[variable]) / "Steam")
    unique: dict[str, Path] = {}
    for root in roots:
        unique.setdefault(os.path.normcase(os.path.abspath(root)), root)
    return list(unique.values())


def persona_names(root: Path) -> dict[str, str]:
    """{account folder id: persona name} from config/loginusers.vdf (text VDF); {} when it cannot be read."""
    try:
        text = (root / "config" / "loginusers.vdf").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    names = {}
    for steam_id, body in re.findall(r'"(\d{17})"\s*\{([^{}]*)\}', text):
        persona = re.search(r'"PersonaName"\s*"([^"]*)"', body)
        names[str(int(steam_id) & 0xFFFFFFFF)] = persona.group(1) if persona else ""
    return names


def find_accounts(roots: list[Path] | None = None) -> list[tuple[Path, str]]:
    """(userdata/<id> folder, persona name) of every Steam account that used this PC."""
    found: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for root in steam_roots() if roots is None else roots:
        userdata = root / "userdata"
        if not userdata.is_dir():
            continue
        names = persona_names(root)
        for folder in sorted(userdata.iterdir()):
            if not (folder.is_dir() and folder.name.isdigit() and folder.name != "0"):
                continue
            real = os.path.normcase(str(folder.resolve()))
            if real not in seen:
                seen.add(real)
                found.append((folder, names.get(folder.name, "")))
    return found


# --- library pictures --------------------------------------------------------------------------------------------

def _cover(image: Any, size: tuple[int, int], focus: tuple[float, float] = (0.5, 0.5)) -> Any:
    """The picture scaled to cover `size`, cropped around `focus` (0..1 on each axis)."""
    from PIL import Image

    scale = max(size[0] / image.width, size[1] / image.height)
    scaled = image.resize((max(size[0], round(image.width * scale)), max(size[1], round(image.height * scale))),
                          Image.LANCZOS)
    left = round((scaled.width - size[0]) * focus[0])
    top = round((scaled.height - size[1]) * focus[1])
    return scaled.crop((left, top, left + size[0], top + size[1]))


def _blend_in(base: Any, picture: Any, at: tuple[int, int], fade: int) -> None:
    """`picture` on `base` at `at`, its edges fading into base over `fade` pixels."""
    from PIL import Image, ImageDraw

    mask = Image.new("L", picture.size, 255)
    draw = ImageDraw.Draw(mask)
    for step in range(fade):
        draw.rectangle((step, step, picture.width - 1 - step, picture.height - 1 - step),
                       outline=round(255 * step / fade))
    base.paste(picture, at, mask)


def _title_logo(cover: Any) -> Any:
    """The Collection's title cut from the PS4 cover (icon0.png): dark ink opaque, the parchment transparent."""
    from PIL import Image

    width, height = cover.size
    area = cover.crop((round(width * 0.06), round(height * 0.47), round(width * 0.94), round(height * 0.74)))

    def ink(value: int) -> int:
        return 255 if value <= 60 else 0 if value >= 110 else round(255 * (110 - value) / 50)

    alpha = area.convert("L").point(ink)
    logo = area.convert("RGBA")
    logo.putalpha(alpha)
    box = alpha.getbbox()
    if box:
        logo = logo.crop(box)
    return logo.resize((LOGO_WIDTH, round(logo.height * LOGO_WIDTH / logo.width)), Image.LANCZOS)


def _fit(picture: Any, room: tuple[int, int]) -> Any:
    """`picture` as large as fits in `room`, its shape kept."""
    from PIL import Image

    scale = min(room[0] / picture.width, room[1] / picture.height)
    return picture.resize((max(1, round(picture.width * scale)), max(1, round(picture.height * scale))), Image.LANCZOS)


def _trimmed(picture: Any) -> Any:
    box = picture.getchannel("A").getbbox()
    return picture.crop(box) if box else picture  # without its empty edge


def _emblem_pictures(paper: Any, emblem: Any | None, icon: Any | None = None) -> dict[str, Any]:
    """One game's capsules on the parchment: its own icon (the one on its window) large with its emblem (title and
    coin) as the name, or the emblem alone; the emblem is also the logo over the banner."""
    emblem = _trimmed(emblem) if emblem is not None else None
    icon = _trimmed(icon) if icon is not None else None
    pictures: dict[str, Any] = {}
    tall = _cover(paper, TALL).convert("RGBA")
    wide = _cover(paper, WIDE).convert("RGBA")
    if icon is not None:
        # Portrait: the icon in the upper part, the name below it. Wide: the icon on the left, the name beside it.
        mark = _fit(icon, (TALL[0] - 140, 470 if emblem is not None else TALL[1] - 200))
        top = 90 if emblem is not None else (TALL[1] - mark.height) // 2
        tall.alpha_composite(mark, ((TALL[0] - mark.width) // 2, top + (470 - mark.height) // 2
                                    if emblem is not None else top))
        mark = _fit(icon, (330, WIDE[1] - 60) if emblem is not None else (WIDE[0] - 120, WIDE[1] - 60))
        left = 50 if emblem is not None else (WIDE[0] - mark.width) // 2
        wide.alpha_composite(mark, (left + (330 - mark.width) // 2 if emblem is not None else left,
                                    (WIDE[1] - mark.height) // 2))
        if emblem is not None:
            name = _fit(emblem, (TALL[0] - 60, TALL[1] - 600))
            tall.alpha_composite(name, ((TALL[0] - name.width) // 2, 590 + (TALL[1] - 620 - name.height) // 2))
            name = _fit(emblem, (WIDE[0] - 420, WIDE[1] - 60))
            wide.alpha_composite(name, (400 + (WIDE[0] - 420 - name.width) // 2, (WIDE[1] - name.height) // 2))
    elif emblem is not None:
        for card, size, room in ((tall, TALL, (TALL[0] - 40, TALL[1] // 2)), (wide, WIDE, (WIDE[0] - 120, WIDE[1] - 70))):
            mark = _fit(emblem, room)
            card.alpha_composite(mark, ((size[0] - mark.width) // 2, (size[1] - mark.height) // 2))
    pictures["p"], pictures[""] = tall.convert("RGB"), wide.convert("RGB")
    if emblem is None:
        return pictures
    from PIL import Image

    logo = emblem
    width = min(LOGO_WIDTH, logo.width * 3)  # the trophy picture is small: no more than three times its size
    pictures["_logo"] = logo.resize((width, round(logo.height * width / logo.width)), Image.LANCZOS)
    return pictures


ART_FILES = {"p": "p.png", "": "wide.png", "_hero": "hero.png", "_logo": "logo.png"}


def made_pictures(folder: Path) -> dict[str, Any]:
    """One game's pictures made in El Dorado's look (ui/steam_art.py: p, wide, hero, logo .png); {} without them or
    without Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return {}
    pictures: dict[str, Any] = {}
    for suffix, name in ART_FILES.items():
        try:
            with Image.open(folder / name) as picture:
                pictures[suffix] = picture.convert("RGBA" if suffix == "_logo" else "RGB")
        except (OSError, ValueError):
            continue
    return pictures


def make_pictures(game_dir: Path, emblem: bytes | None = None, icon: Path | None = None) -> dict[str, Any]:
    """{suffix: image} from the game's sce_sys pictures ("p" portrait, "" wide, "_hero", "_logo"); with `emblem`
    (one game's trophy ICON0.PNG) and `icon` (its own icon, a PNG) the capsules and logo show that game instead of
    the Collection. {} without them or without Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return {}
    sce = game_dir / "sce_sys"
    background = next((sce / name for name in ("pic1.png", "pic0.png") if (sce / name).is_file()), None)
    cover_file = sce / "icon0.png"
    art = Image.open(background).convert("RGB") if background else None
    cover = Image.open(cover_file).convert("RGB") if cover_file.is_file() else None
    pictures: dict[str, Any] = {}
    if art is not None:
        pictures["_hero"] = _cover(art, HERO, (0.5, 0.25))
    if cover is not None:
        # The cover on plain parchment (the empty left of the background picture), so Drake shows once.
        paper = art.crop((0, 0, round(art.width * 0.3), art.height)) if art is not None else cover.crop((0, 0, 8, 8))
        tall = _cover(paper, TALL)
        _blend_in(tall, cover.resize((TALL[0], TALL[0]), Image.LANCZOS), (0, 210), 130)
        wide = _cover(paper, WIDE)
        _blend_in(wide, cover.resize((WIDE[1], WIDE[1]), Image.LANCZOS), ((WIDE[0] - WIDE[1]) // 2, 0), 100)
        pictures.update({"p": tall, "": wide, "_logo": _title_logo(cover)})
    mark = own = None
    if emblem:
        try:
            mark = Image.open(io.BytesIO(emblem)).convert("RGBA")
        except (OSError, ValueError):
            mark = None  # not a picture: the Collection's capsules stay
    if icon is not None:
        try:
            own = Image.open(icon).convert("RGBA")
        except (OSError, ValueError):
            own = None  # no icon yet: the emblem alone
    if mark is not None or own is not None:
        paper = art.crop((0, 0, round(art.width * 0.3), art.height)) if art is not None else \
            Image.new("RGB", (64, 64), (226, 214, 188))
        pictures.update(_emblem_pictures(paper, mark, own))
    return pictures


def _mark() -> Any:
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_text(*PICTURE_MARK)
    return info


def _ours(path: Path) -> bool:
    """A library picture this launcher made (PICTURE_MARK): made again. The player's own are kept."""
    if path.suffix.lower() != ".png":
        return False
    try:
        from PIL import Image

        with Image.open(path) as picture:
            return picture.text.get(PICTURE_MARK[0]) == PICTURE_MARK[1]
    except (ImportError, OSError, ValueError, AttributeError):
        return False


def save_pictures(grid: Path, ids: list[int], pictures: dict[str, Any] | list[dict[str, Any]]) -> int:
    """Writes each app id's pictures (one set for all, or one per id) into grid/, skipping any the player set (in
    any format). Returns the count."""
    grid.mkdir(parents=True, exist_ok=True)
    written = 0
    for number, appid in enumerate(ids):
        own = pictures[number] if isinstance(pictures, list) else pictures
        for suffix, image in own.items():
            stem = f"{appid}{suffix}"
            if any(not _ours(path) for path in grid.glob(stem + ".*")):
                continue
            image.save(grid / f"{stem}.png", pnginfo=_mark())
            written += 1
    return written


# --- writing ----------------------------------------------------------------------------------------------------

def backup(file: Path) -> Path | None:
    """shortcuts.vdf copied to shortcuts.vdf.<time>.uncharted-backup; only the newest few are kept."""
    if not file.is_file():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    copy = file.with_name(f"{file.name}.{stamp}{BACKUP_SUFFIX}")
    number = 1
    while copy.exists():
        number += 1
        copy = file.with_name(f"{file.name}.{stamp}-{number}{BACKUP_SUFFIX}")
    copy.write_bytes(file.read_bytes())
    old = sorted(file.parent.glob(f"{file.name}.*{BACKUP_SUFFIX}"), key=lambda path: path.stat().st_mtime)
    for path in old[:-KEEP_BACKUPS]:
        path.unlink(missing_ok=True)
    return copy


def _read(file: Path) -> list[Node]:
    data = file.read_bytes() if file.is_file() else b""
    if not data.strip(b"\0"):
        return []
    try:
        return parse_vdf(data)
    except (ValueError, IndexError) as error:
        raise SteamError("bad_file", f"{file}: {error}") from error


def update_account(folder: Path, persona: str, wanted: list[Target], icon: str,
                   pictures: dict[str, Any] | list[dict[str, Any]],
                   all_names: tuple[str, ...] = ()) -> AccountResult:
    """This launcher's entries in one account's shortcuts.vdf (backed up first) and their pictures."""
    config = folder / "config"
    file = config / "shortcuts.vdf"
    tree = _read(file)
    merged = merge(tree, wanted, icon, all_names)
    config.mkdir(parents=True, exist_ok=True)
    saved = backup(file)
    _write_bytes(file, dump_vdf(tree))
    written = save_pictures(config / "grid", merged.ids, pictures) if any(pictures) else 0
    return AccountResult(folder, persona, file, saved, merged.ids, merged.added, merged.updated, merged.removed,
                         written)


def _write_bytes(file: Path, data: bytes) -> None:
    """Through a temporary file and a rename (safe_write holds the text version)."""
    temporary = file.with_name(file.name + ".writing")
    temporary.write_bytes(data)
    os.replace(temporary, file)


def add_to_steam(wanted: list[Target], icon: str, game_dir: Path | None,
                 accounts: list[tuple[Path, str]] | None = None,
                 all_names: tuple[str, ...] = ()) -> list[AccountResult]:
    """Writes the entries into every Steam account found (or `accounts`). Every file is read and checked before the
    first one is written. Raises SteamError("no_steam") when there is no account."""
    accounts = find_accounts() if accounts is None else accounts
    if not accounts:
        raise SteamError("no_steam")
    for folder, _ in accounts:
        _read(folder / "config" / "shortcuts.vdf")
    pictures: list[dict[str, Any]] = []
    for target in wanted:  # in merge()'s id order
        try:
            if target.art is not None:
                pictures.append(made_pictures(target.art))
            else:
                pictures.append(make_pictures(game_dir, target.emblem, target.icon) if game_dir else {})
        except OSError:
            pictures.append({})  # unreadable pictures: the entry is added without them
    return [update_account(folder, persona, wanted, icon, pictures, all_names) for folder, persona in accounts]
