# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Discord Rich Presence for El Dorado: "Playing El Dorado", the game being played, the chapter of its
newest save and the time since the start. Talks to the Discord app on this PC over its local pipe
(\\\\.\\pipe\\discord-ipc-N); nothing goes over the network from here. Without Discord running it does
nothing. UNCHARTED_DISCORD=0 turns it off."""
import json
import os
import struct
import threading
import time
import unicodedata
import uuid
from pathlib import Path

CLIENT_ID = "1567829645414375445"  # the El Dorado application on the Discord Developer Portal
NAMES = {"u1": "Uncharted: Drake's Fortune", "u2": "Uncharted 2: Among Thieves",
         "u3": "Uncharted 3: Drake's Deception"}
NUMBERS = {"u1": "1", "u2": "2", "u3": "3"}
PARAM_SIZE = 1328


def logical(text):
    """Save texts hold Arabic as presentation forms in display order (the game draws them left to
    right): back to logical order and plain letters, which Discord lays out itself."""
    if not any("\ufb50" <= ch <= "\ufeff" for ch in text):
        return text
    text = text.replace("_", " ")
    out, run = [], []
    for ch in reversed(text):  # whole line reversed, then runs of digits/Latin put back in order
        if ch.isascii() and (ch.isalnum() or ch in "%.,:+-/"):
            run.append(ch)
            continue
        if run:
            out.extend(reversed(run))
            run = []
        out.append(ch)
    out.extend(reversed(run))
    return unicodedata.normalize("NFKC", "".join(out)).strip()


def newest_chapter(user_dir, game):
    """The chapter line of the game's newest save (param.bin subtitle), or ''."""
    best, text = 0, ""
    base = Path(user_dir) / "savedata"
    number = NUMBERS.get(game)
    if not number or not base.is_dir():
        return ""
    for param in base.glob(f"*/*/SAVEDATA0{number}[0-9].sce_sys/param.bin"):
        try:
            stat = param.stat()
            if stat.st_mtime <= best:
                continue
            data = param.read_bytes()
        except OSError:
            continue
        if len(data) < PARAM_SIZE:
            continue
        subtitle = data[128:256].split(b"\0")[0].decode("utf-8", "replace").strip()
        if subtitle:
            best, text = stat.st_mtime, subtitle
    return logical(text.splitlines()[0]) if text else ""


class Presence:
    def __init__(self, user_dir):
        self.user_dir = user_dir
        self.game = None
        self.started = int(time.time())
        self.pipe = None
        self.stop_event = threading.Event()
        self.changed = threading.Event()
        self.thread = None
        self.enabled = os.environ.get("UNCHARTED_DISCORD", "1") != "0" and os.name == "nt"

    # -- the pipe ------------------------------------------------------------------------
    def send(self, op, payload):
        body = json.dumps(payload).encode("utf-8")
        self.pipe.write(struct.pack("<II", op, len(body)) + body)
        self.pipe.flush()
        header = self.pipe.read(8)  # every frame gets an answer: read it, or the pipe fills
        if len(header) < 8:
            raise OSError("Discord closed the pipe")
        _op, length = struct.unpack("<II", header)
        return json.loads(self.pipe.read(length) or b"{}")

    def connect(self):
        for n in range(10):
            try:
                pipe = open(rf"\\.\pipe\discord-ipc-{n}", "r+b", buffering=0)
            except OSError:
                continue
            self.pipe = pipe
            try:
                reply = self.send(0, {"v": 1, "client_id": CLIENT_ID})
                if reply.get("evt") == "READY":
                    return True
            except (OSError, ValueError):
                pass
            self.close_pipe()
        return False

    def close_pipe(self):
        if self.pipe:
            try:
                self.pipe.close()
            except OSError:
                pass
        self.pipe = None

    def activity(self):
        if not self.game:
            return None
        chapter = newest_chapter(self.user_dir, self.game)
        activity = {"details": NAMES.get(self.game, "Uncharted"), "timestamps": {"start": self.started},
                    "assets": {"large_image": "eldorado", "large_text": "El Dorado"}}
        if chapter:
            activity["state"] = chapter[:128]
        return activity

    def update(self):
        reply = self.send(1, {"cmd": "SET_ACTIVITY", "args": {"pid": os.getpid(), "activity": self.activity()},
                              "nonce": str(uuid.uuid4())})
        if reply.get("evt") == "ERROR":
            print(f"Discord: {reply.get('data', {}).get('message', 'refused')}", flush=True)

    # -- the worker ----------------------------------------------------------------------
    def loop(self):
        announced = False
        while not self.stop_event.is_set():
            if not self.pipe and not self.connect():
                self.stop_event.wait(30)  # Discord not running (yet)
                continue
            try:
                self.update()
                if not announced:
                    print("Discord: presence shown", flush=True)
                    announced = True
            except (OSError, ValueError):
                self.close_pipe()
                continue
            # Again on a game switch, else every 30 s (a checkpoint save moves the chapter on).
            self.changed.wait(30)
            self.changed.clear()
        if self.pipe:
            try:
                self.game = None
                self.update()  # clears it
            except (OSError, ValueError):
                pass
            self.close_pipe()

    def start(self, game):
        self.game = game
        if self.enabled:
            self.thread = threading.Thread(target=self.loop, name="discord", daemon=True)
            self.thread.start()

    def switch(self, game):
        self.game = game
        self.changed.set()

    def stop(self):
        self.stop_event.set()
        self.changed.set()
        if self.thread:
            self.thread.join(timeout=3)
