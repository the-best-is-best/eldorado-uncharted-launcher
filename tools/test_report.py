# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Which of the things in docs/TESTING.md were tried in the game, and whether they worked, read from the game's logs.

Each start of a game leaves analysis/<game log>/attempts/boot-<n>/ (boot.log, boot.json; uncharted for Uncharted 1,
big2-ps4_Shipping and big3-ps4_Shipping for 2 and 3). The engine writes a line
when a fix runs (docs/TESTING.md names them); this reads the runs since the installed engine was copied and says
for every item: NOT TRIED, PASSED, FAILED, or LOOK (it ran: only your eyes can tell, mark it). Your marks are kept in
analysis/uncharted-user/test-marks.json and win over what the logs say.

usage: python tools/test_report.py [--root <install>] [--since "YYYY-MM-DD HH:MM"] [--all]
       python tools/test_report.py [--root <install>] --mark <id> ok|fail [note...]
The report is printed and written to analysis/test-report.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOT_TRIED, PASSED, FAILED, LOOK, INFO = "NOT TRIED", "PASSED", "FAILED", "LOOK", "INFO"


@dataclass
class Run:
    folder: Path
    started: dt.datetime
    game: str
    text: str
    exit_code: int | None
    seconds: float

    @property
    def crashed(self) -> bool:
        return "Fault:" in self.text or bool(self.exit_code not in (0, None))

    def games(self) -> set[str]:
        """The games this run played: its start, and each the collection switched to."""
        played = {self.game}
        for name in re.findall(r"Collection: switching to (\S+)", self.text):
            played |= {key for key, exe in EXECUTABLES.items() if exe == name}
        return played


EXECUTABLES = {"u1": "eboot.bin", "u2": "big2-ps4_Shipping.elf", "u3": "big3-ps4_Shipping.elf"}


@dataclass
class Result:
    status: str
    evidence: str


@dataclass
class Item:
    id: str
    title: str
    check: object = field(repr=False)


def read_runs(root: Path, since: dt.datetime | None) -> list[Run]:
    runs = []
    # Each game keeps its own log folder: analysis/uncharted (Uncharted 1), analysis/big2-ps4_Shipping and
    # analysis/big3-ps4_Shipping; the game being played now has its log there, in attempts/ only once it ends.
    logs = [root / "analysis" / name for name in ("uncharted", "big2-ps4_Shipping", "big3-ps4_Shipping")]
    lives = [log for log in logs if (log / "boot.log").is_file()]
    for folder in [f for log in logs for f in sorted((log / "attempts").glob("boot-*"))] + lives:
        live = folder if folder in lives else None
        log = folder / "boot.log"
        if not log.is_file():
            continue
        text = log.read_text(encoding="utf-8", errors="replace")
        head = re.match(r"# (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \S+ \((u[123])\)", text)
        if not head:
            continue
        started = dt.datetime.strptime(head.group(1), "%Y-%m-%d %H:%M:%S")
        if since and started < since:
            continue
        if live and any(run.started == started and run.game == head.group(2) for run in runs):
            continue  # already ended and kept in attempts/
        exit_code, seconds = None, 0.0
        if live:  # still running: its play time so far
            seconds = max(0.0, (dt.datetime.fromtimestamp(log.stat().st_mtime) - started).total_seconds())
        try:
            info = json.loads((folder / "boot.json").read_text(encoding="utf-8"))
            exit_code, seconds = info.get("exit_code"), float(info.get("elapsed_seconds") or 0)
        except (OSError, ValueError):
            pass
        runs.append(Run(folder, started, head.group(2), text, exit_code, seconds))
    return runs


def lines(runs: list[Run], pattern: str) -> list[tuple[Run, str]]:
    found = []
    for run in runs:
        for line in run.text.splitlines():
            if re.search(pattern, line):
                found.append((run, line.strip()))
    return found


def when(run: Run) -> str:
    return run.started.strftime("%d %b %H:%M")


def seen(runs, pattern, passed_pattern=None, what="") -> Result:
    hits = lines(runs, pattern)
    if not hits:
        return Result(NOT_TRIED, what)
    if passed_pattern is None:
        return Result(PASSED, f"{when(hits[-1][0])}: {hits[-1][1]}")
    done = lines(runs, passed_pattern)
    if done:
        return Result(PASSED, f"{when(done[-1][0])}: {done[-1][1]}")
    return Result(FAILED, f"seen ({when(hits[-1][0])}: {hits[-1][1]}) but never finished")


# --- the checks ---------------------------------------------------------------------------------------------------

def wheel_mouse(runs, root):
    return seen(runs, r"turn-the-stick prompt is on screen", r"turn-the-stick prompt went away while the mouse",
                "Uncharted 1: a door wheel or valve")


def wheel_picture(runs, root):
    hits = lines(runs, r"turn-the-stick prompt is on screen")
    return Result(LOOK, f"shown {when(hits[-1][0])}: does it show the mouse going round?") if hits else \
        Result(NOT_TRIED, "Uncharted 1: a door wheel or valve")


def walk(runs, root):
    return seen(runs, r"Pad: walk key pressed: Nate walks", r"Pad: walk key pressed: Nate runs",
                "press B, move, press B again")


def mouse_camera(runs, root):
    hits = lines(runs, r"follow camera turned in its input function")
    if not hits:
        return Result(NOT_TRIED, "Uncharted 2 or 3: look around with the mouse")
    crashed = [run for run, _ in hits if run.crashed]
    if crashed:
        return Result(FAILED, f"ran, and the game crashed ({when(crashed[-1])}): see Crashes")
    minutes = sum({id(run): run.seconds for run, _ in hits}.values()) / 60
    return Result(LOOK, f"ran for {minutes:.0f} min without a crash: is it smooth like I J K L?")


def mounted_guns(runs, root):
    return seen(runs, r"Mouse: Uncharted \d mounted gun entered", what="a mounted gun (turret), or Uncharted 1's jeep gun")


def rewards(runs, root):
    hits = lines(runs, r"Unlock all rewards:")
    if not hits:
        return Result(NOT_TRIED, "turn on Unlock all rewards (CHEATS) and start a game")
    bad = [line for _, line in hits if "skipped" in line or "not applied" in line or "not a supported" in line]
    if bad:
        return Result(FAILED, bad[-1])
    return Result(PASSED, f"{when(hits[-1][0])}: {hits[-1][1]}")


def u1_cross_prompt(runs, root):
    return Result(LOOK, "Uncharted 1: Nate on the ground after a fall: the big X shows as your key. Mark it.")         if runs else Result(NOT_TRIED, "Uncharted 1: let Nate fall and look at the big X")


def u1_push_prompt(runs, root):
    return Result(LOOK, "Uncharted 1: pushing the stone (Drowned City): W A S D show, the pushed key lit. Mark it.")         if runs else Result(NOT_TRIED, "Uncharted 1: push the stone and look at the prompt")


def onehit_jetski(runs, root):
    return seen(runs, r"One hit kills: Uncharted 1 jet ski: Elena's shots count",
                what="Uncharted 1 jet ski with One hit kills on: Elena's shots kill, off the boat only Nate's hits do")


def u1_crank_mouse(runs, root):
    return seen(runs, r"Mouse: the turn-the-stick prompt is on screen",
                what="Uncharted 1 engine room: the machine's crank: the mouse picture shows and the mouse turns it")


def prompts_launcher_look(runs, root):
    return Result(LOOK, "Prompts in the launcher's look: U1 X/Square/push-the-stone (green), U2 weapon d-pad (blue), U3 circle prompts (orange). Mark it.")         if runs else Result(NOT_TRIED, "Play and look at the button prompts: they carry the game's launcher colour")


def u1_square_prompt(runs, root):
    return seen(runs, r"Button prompts: Uncharted 1 square prompt drawn as keyboard and mouse keys",
                what="Uncharted 1, the fight after the boat: the Square prompt shows your Square key (mark it)")


def trophies_cheat(runs, root):
    return seen(runs, r"Unlock all trophies: \d+ added",
                what="Settings > CHEATS > Unlock all trophies, then start a game and open the launcher's Trophies page")


def menu_sensitivity(runs, root):
    return seen(runs, r"aiming or vertical sensitivity changed in the in-game menu",
                what="Insert > Mouse: change Aiming or Vertical sensitivity")


def checkpoint_jump(runs, root):
    return seen(runs, r"Checkpoints: jumping to task", what="Insert > Checkpoints: double-click one")


def fullscreen_keys(runs, root):
    hits = lines(runs, r"Window: (Alt\+Enter|F11),")
    if not hits:
        return Result(NOT_TRIED, "press Alt+Enter while playing")
    keys = {re.search(r"Window: (Alt\+Enter|F11)", line).group(1) for _, line in hits}
    if "Alt+Enter" not in keys:
        return Result(NOT_TRIED, "F11 worked; press Alt+Enter too")
    return Result(PASSED, f"{when(hits[-1][0])}: {hits[-1][1]}")


def pause(runs, root):
    return seen(runs, r"game threads frozen \(the game's window is in the background\)",
                r"Pause: back from the background", "minimize the game or Alt+Tab")


def u3_hitches(runs, root):
    u3 = [run for run in runs if "u3" in run.games()]
    if not u3:
        return Result(NOT_TRIED, "play Uncharted 3: chapter starts and cutscenes")
    over50 = 0
    for run in u3:
        for a, b, c in re.findall(r"frames over 25/33/50 ms: (\d+)/(\d+)/(\d+)", run.text):
            over50 += int(c)
    minutes = sum(run.seconds for run in u3) / 60
    return Result(INFO, f"{minutes:.0f} min of Uncharted 3: {over50} frames over 50 ms (fewer is better)")


def u2_long(runs, root):
    u2 = [run for run in runs if "u2" in run.games()]
    longest = max((run.seconds for run in u2), default=0) / 60
    if longest < 60:
        return Result(NOT_TRIED, f"play Uncharted 2 an hour in one go (longest so far {longest:.0f} min)")
    crashed = [run for run in u2 if run.crashed and run.seconds >= 3600]
    if crashed:
        return Result(FAILED, f"crashed after {crashed[-1].seconds / 60:.0f} min ({when(crashed[-1])})")
    return Result(PASSED, f"{longest:.0f} min in one go without running out of video memory")


def sound_cuts(runs, root):
    minutes = sum(run.seconds for run in runs) / 60
    if minutes < 20:
        return Result(NOT_TRIED, f"play 20 minutes or more ({minutes:.0f} so far)")
    slow = lines(runs, r"File: slow read")
    starved = lines(runs, r"Audio stats port .*starved [1-9]")
    if starved or slow:
        last = (starved or slow)[-1]
        return Result(FAILED, f"{len(starved)} sound gaps, {len(slow)} slow reads; last {when(last[0])}: {last[1]}")
    return Result(PASSED, f"{minutes:.0f} min played without a sound gap or a slow read")


def u3_triangle(runs, root):
    if lines(runs, r"Uncharted 3 triangle .*prompt drawn as keyboard"):
        return Result(LOOK, "the Triangle prompt is in the table: does the cargo plane show a key?")
    found = triangle_dumps(root / "analysis" / "uncharted-user" / "prompt-dumps")
    if found:
        return Result(INFO, "captured, ready to add: " + ", ".join(path.name for path, _ in found[:3]))
    return Result(NOT_TRIED, "Uncharted 3: the cargo plane scene where Nate holds the net (Triangle)")


def triangle_dumps(folder: Path) -> list[tuple[Path, float]]:
    """The engine's captured 512x512 BC1 pictures whose blocks are mostly the Triangle prompt's green (55, 216, 104)
    over a dark puck: the share of green blocks, best first. The blocks' order (tiling) does not matter here."""
    found = []
    for path in sorted(folder.glob("*-512x512-bc1-*.bin")) if folder.is_dir() else []:
        data = path.read_bytes()
        blocks = len(data) // 8
        green = 0
        for i in range(blocks):
            c0, = struct.unpack_from("<H", data, i * 8)
            r, g, b = (c0 >> 11) * 255 // 31, ((c0 >> 5) & 63) * 255 // 63, (c0 & 31) * 255 // 31
            if g > 150 and g > r + 70 and g > b + 50:
                green += 1
        share = green / max(blocks, 1)
        if share > 0.02:
            found.append((path, share))
    return sorted(found, key=lambda item: -item[1])


def cache_writes(runs, root):
    """After an engine update the preparation page stays up until the new shader cache is on disk: no long cache
    writes once the game plays (they held up loading, e.g. choosing a difficulty in Uncharted 3)."""
    waited = lines(runs, r"Preparation screen: waited .* shader cache writes")
    late = []
    for run in runs:
        text = run.text.split("Preparation screen: shown for", 1)
        if len(text) == 2 and "Shader cache: one write took" in text[1]:
            late.append(run)
    if late:
        return Result(FAILED, f"long shader cache writes while playing ({when(late[-1])})")
    if waited:
        return Result(PASSED, f"{when(waited[-1][0])}: {waited[-1][1]}")
    return Result(NOT_TRIED, "happens once after an engine update: the first start of each game")


def loading_on(runs, root):
    return seen(runs, r"Pause: the window is in the background while the game loads: it loads on",
                what="start a game, then Alt+Tab before its first picture")


def view_kept(runs, root):
    hits = lines(runs, r"^# update view: kept")
    if hits:
        return Result(PASSED, f"{when(hits[-1][0])}: {hits[-1][1][2:]}")
    made = lines(runs, r"^# update view: made")
    return Result(NOT_TRIED, "kept from the second start on" if made else "start any game twice")


def cache_pack(runs, root):
    bad = lines(runs, r"in the pack does not read back whole")
    if bad:
        return Result(FAILED, f"{when(bad[-1][0])}: {bad[-1][1]}")
    loaded = [(run, int(m.group(1))) for run in runs
              for m in re.finditer(r"Pipeline cache: preloaded (\d+) of", run.text)]
    loaded = [(run, n) for run, n in loaded if n > 0]
    if not loaded:
        return Result(NOT_TRIED, "start a game twice: the second start loads its shaders from the pack")
    errors = sum(run.text.count("Failed to open the file") for run, _ in loaded)
    run, n = loaded[-1]
    return Result(PASSED if not errors else FAILED,
                  f"{when(run)}: {n} pipelines loaded from the pack" + (f"; {errors} open errors" if errors else ""))


def variants_remembered(runs, root):
    hits = [(run, int(m.group(1))) for run in runs
            for m in re.finditer(r"(\d+) numbers remembered from the last start", run.text)]
    if not any(n for _, n in hits):
        return Result(NOT_TRIED, "start a game twice")
    rebuilt = [int(m.group(1)) for run, _ in hits for m in re.finditer(r"Variant ship: (\d+) listed variants", run.text)]
    run, n = [h for h in hits if h[1]][-1]
    return Result(PASSED, f"{when(run)}: {n} remembered; listed variants built: {rebuilt[-1] if rebuilt else 0}")


def save_pictures(runs, root):
    pictures = lines(runs, r"save picture (written|waits)")
    if not pictures:
        return Result(NOT_TRIED, "save the game (a checkpoint or the save list)")
    system = [line for _, line in pictures if "SAVEDATA01P" in line or "SAVEDATA0CC" in line]
    if system:
        return Result(FAILED, f"pictures still made for system saves: {system[-1]}")
    return Result(PASSED, f"{len(pictures)} save pictures, all for campaign saves")


def crashes(runs, root):
    bad = [run for run in runs if run.crashed]
    if not runs:
        return Result(NOT_TRIED, "no game started yet with this engine")
    if not bad:
        minutes = sum(run.seconds for run in runs) / 60
        return Result(PASSED, f"{len(runs)} starts, {minutes:.0f} min played, no crash")
    notes = []
    for run in bad[-3:]:
        fault = re.search(r"Fault: .*", run.text)
        chapter = re.findall(r"save data '(SAVEDATA\w+)'", run.text)
        notes.append(f"{when(run)} {','.join(sorted(run.games()))}: "
                     f"{fault.group(0)[:120] if fault else f'exit code {run.exit_code}'}"
                     f"{' (' + chapter[-1] + ')' if chapter else ''}")
    return Result(FAILED, f"{len(bad)} of {len(runs)} starts crashed; " + " | ".join(notes))


ITEMS = [
    Item("wheel_mouse", "U1 door wheel turns with the mouse", wheel_mouse),
    Item("wheel_picture", "U1 wheel prompt shows the mouse going round", wheel_picture),
    Item("walk", "Walk / run switch (B)", walk),
    Item("mouse_camera", "U2/U3 mouse camera smooth (in the game's input function)", mouse_camera),
    Item("mounted_guns", "Mouse aims mounted guns (turrets, U1 jeep gun)", mounted_guns),
    Item("rewards", "Unlock all rewards (Mevlock's)", rewards),
    Item("u1_cross_prompt", "U1 big X prompt (Nate on the ground) shows your key", u1_cross_prompt),
    Item("u1_push_prompt", "U1 push-the-stone prompt shows W A S D", u1_push_prompt),
    Item("onehit_jetski", "One hit kills counts Elena's shots on the jet ski only", onehit_jetski),
    Item("u1_crank_mouse", "U1 engine room crank turns with the mouse (the arrow the other way)", u1_crank_mouse),
    Item("prompts_launcher_look", "Button prompts take the launcher look (key face, accent glow, lit key)", prompts_launcher_look),
    Item("u1_square_prompt", "U1 fight: the big Square prompt shows your Square key", u1_square_prompt),
    Item("trophies_cheat", "Unlock all trophies (CHEATS)", trophies_cheat),
    Item("menu_sensitivity", "Insert menu: aiming and vertical sensitivity", menu_sensitivity),
    Item("checkpoint_jump", "Insert menu: double-click a checkpoint", checkpoint_jump),
    Item("fullscreen_keys", "Alt+Enter switches window / fullscreen", fullscreen_keys),
    Item("pause", "The game stops in the background and pauses on return", pause),
    Item("u3_hitches", "U3: fewer hitches at chapter starts and cutscenes", u3_hitches),
    Item("u2_long", "U2: an hour without running out of video memory", u2_long),
    Item("sound_cuts", "No music or sound cuts", sound_cuts),
    Item("u3_triangle", "U3 cargo plane: Triangle prompt as a key", u3_triangle),
    Item("cache_writes", "After an update: the shader page waits for the cache, no hang in play", cache_writes),
    Item("loading_on", "A start sent to the background keeps loading", loading_on),
    Item("view_kept", "The update view is kept between starts", view_kept),
    Item("cache_pack", "Shaders kept in one pack per game and loaded back", cache_pack),
    Item("variants_remembered", "Listed shader variants are not rebuilt each start", variants_remembered),
    Item("save_pictures", "Save pictures only for campaign saves", save_pictures),
    Item("crashes", "No crashes (U2 Heart of Ice end included)", crashes),
]


def load_marks(root: Path) -> dict:
    try:
        return json.loads((root / "analysis" / "uncharted-user" / "test-marks.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_mark(root: Path, item: str, result: str, note: str) -> None:
    if item not in {i.id for i in ITEMS}:
        sys.exit(f"no test {item!r}; one of: {', '.join(i.id for i in ITEMS)}")
    marks = load_marks(root)
    marks[item] = {"result": PASSED if result == "ok" else FAILED, "note": note,
                   "at": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    path = root / "analysis" / "uncharted-user" / "test-marks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marks, indent=1, ensure_ascii=False), encoding="utf-8")


def report(root: Path, since: dt.datetime | None) -> str:
    runs = read_runs(root, since)
    marks = load_marks(root)
    rows = []
    for item in ITEMS:
        result = item.check(runs, root)
        mark = marks.get(item.id)
        if mark:
            result = Result(mark["result"], f"marked {mark['at']}: {mark.get('note') or ''} (logs: {result.evidence})")
        rows.append((item, result))
    out = [f"# El Dorado test report ({dt.datetime.now():%Y-%m-%d %H:%M})", "",
           f"{len(runs)} game starts since {since:%Y-%m-%d %H:%M}" if since else f"{len(runs)} game starts", "",
           "| Test | Status | Evidence |", "| --- | --- | --- |"]
    for item, result in rows:
        out.append(f"| {item.title} (`{item.id}`) | **{result.status}** | {result.evidence.replace('|', '/')} |")
    counts = {status: sum(1 for _, r in rows if r.status == status) for status in (PASSED, FAILED, LOOK, NOT_TRIED)}
    out += ["", ", ".join(f"{n} {status.lower()}" for status, n in counts.items())]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--since")
    parser.add_argument("--all", action="store_true", help="every run, not only those since the engine was copied")
    parser.add_argument("--mark", nargs="+", metavar="ARG")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.mark:
        if len(args.mark) < 2 or args.mark[1] not in ("ok", "fail"):
            parser.error("--mark <id> ok|fail [note...]")
        save_mark(root, args.mark[0], args.mark[1], " ".join(args.mark[2:]))
    since = None
    if args.since:
        since = dt.datetime.strptime(args.since, "%Y-%m-%d %H:%M")
    elif not args.all:
        engine = root / "engine" / "out" / "bb-probe.exe"
        if engine.is_file():
            since = dt.datetime.fromtimestamp(engine.stat().st_mtime).replace(second=0, microsecond=0)
    text = report(root, since)
    (root / "analysis").mkdir(exist_ok=True)
    (root / "analysis" / "test-report.md").write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
