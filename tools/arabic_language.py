# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
"""Finds which game language holds an Arabic translation.

Arabic translations of the collection replace one of the game's 22 languages (the one seen so far: file 2, an English
the games read for no console language we could find).
Each game keeps its texts in <uNdata>/build/main/core.psarc as text1/ps4/<n>.common, n being the game's own
number for the language; the file with the most Arabic letters is the translation. The launcher's "Arabic" choice
makes each game load that file whatever the console language (the "text<n>" patch, gow3_pc/scripts/cheats.py). Results are kept in a small cache keyed by the archive's size and time, so a start reads nothing again
until the game or its update changes.
"""
import json
import lzma
import re
import struct
import zlib
from pathlib import Path

DATA_DIRS = {"u1": "u1data", "u2": "u2data", "u3": "u3data"}
TEXT_FILE = re.compile(r"/?text1/ps4/(\d+)\.common$")
# Arabic letters in UTF-8: U+0600-U+06FF (D8-DB xx) and the presentation forms U+FB50-U+FEFF (EF AD-BB xx).
ARABIC = re.compile(rb"[\xd8-\xdb][\x80-\xbf]|\xef[\xad-\xbb][\x80-\xbf]")
MIN_LETTERS = 500  # fewer: a stray name or symbol, not a translation
ZLIB_HEADERS = (b"\x78\x01", b"\x78\x5e", b"\x78\x9c", b"\x78\xda")


class Psarc:
    """A PlayStation archive: the file names and each file's bytes."""

    def __init__(self, path):
        self.file = open(path, "rb")
        header = self.file.read(32)
        magic, _, _, toc_size, entry_size, count, self.block, _ = struct.unpack(">4sI4sIIIII", header)
        if magic != b"PSAR":
            raise ValueError(f"{path} is not a PSARC")
        toc = self.file.read(toc_size - 32)
        self.entries = []
        for i in range(count):
            entry = toc[i * entry_size:(i + 1) * entry_size]
            first_block = struct.unpack(">I", entry[16:20])[0]
            self.entries.append((first_block, int.from_bytes(entry[20:25], "big"), int.from_bytes(entry[25:30], "big")))
        width = 2 if self.block <= 0x10000 else 3 if self.block <= 0x1000000 else 4
        sizes = toc[count * entry_size:]
        self.block_sizes = [int.from_bytes(sizes[i:i + width], "big") for i in range(0, len(sizes) - width + 1, width)]
        self.names = self.read(0).decode("utf-8", "replace").split("\n")  # entry 0: the names of the others

    def close(self):
        self.file.close()

    def read(self, index):
        first_block, size, offset = self.entries[index]
        out = bytearray()
        self.file.seek(offset)
        block = first_block
        while len(out) < size:
            stored = self.block_sizes[block]
            block += 1
            chunk = self.file.read(stored or self.block)
            out += self.unpack(chunk, size - len(out)) if stored else chunk
        return bytes(out[:size])

    def unpack(self, chunk, remaining):
        if chunk[:2] in ZLIB_HEADERS:
            try:
                return zlib.decompress(chunk)
            except zlib.error:
                pass
        if chunk[:3] == b"\x5d\x00\x00":
            try:
                return lzma.decompress(chunk)
            except lzma.LZMAError:
                pass
        return chunk  # a block that did not shrink is stored as it is

    def text_files(self):
        """{language id: bytes} of the archive's text1/ps4/<id>.common files."""
        found = {}
        for index, name in enumerate(self.names, start=1):
            match = TEXT_FILE.search(name.strip())
            if match and index < len(self.entries):
                found[match.group(1)] = self.read(index)
        return found


def arabic_language_in(archive):
    """The number of the text file that holds Arabic in this core.psarc, or None."""
    psarc = Psarc(archive)
    try:
        letters = {language: len(ARABIC.findall(data)) for language, data in psarc.text_files().items()}
    finally:
        psarc.close()
    best = max(letters, key=letters.get, default=None)
    if best is None or letters[best] < MIN_LETTERS:
        return None
    return best


def find_arabic_language(game_dir, game, cache_file):
    """The number of the text file holding Arabic for game ("u1", "u2", "u3") in game_dir (the game with its update), or None."""
    archive = Path(game_dir) / DATA_DIRS[game] / "build" / "main" / "core.psarc"
    try:
        info = archive.stat()
    except OSError:
        return None
    key = f"4|{archive.resolve()}|{info.st_size}|{int(info.st_mtime)}"
    try:
        cache = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    if key in cache:
        return cache[key] or None
    language = arabic_language_in(archive)
    cache[key] = language or ""
    try:
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(cache_file).with_suffix(".tmp")
        temporary.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        temporary.replace(cache_file)
    except OSError:
        pass  # found again at the next start
    return language
