# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""El Dorado's health check ("Check El Dorado.bat" in the port folder): whether the install is whole and whether the
games ran well, as one page (analysis\\health-report.html, opened in the browser), in Arabic or English.

The install: the files every start needs, the engine's DLLs, Qt, the start scripts, the game folder and its
languages, each game's shader preparation, the free disk space.
The runs: every engine log kept (analysis\\uncharted\\attempts\\boot-*\\boot.log): a crash or a freeze, how the game
was closed, the frame rate, whether the shader preparation page came back after a run that kept its cache, whether
shader cache writes were lost at the exit, whether the title page was passed, shader compiles while playing.

    python tools\\health_check.py [--lang ar|en] [--runs N] [--no-open]
Nothing is changed: the check only reads.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "launcher"), str(ROOT / "tools"), str(ROOT / "engine" / "scripts")]

ANALYSIS = ROOT / "analysis"
ATTEMPTS = ANALYSIS / "uncharted" / "attempts"
USER = ANALYSIS / "uncharted-user"
REPORT = ANALYSIS / "health-report.html"
GAME_NAMES = {"u1": "Uncharted 1", "u2": "Uncharted 2", "u3": "Uncharted 3"}
EXECUTABLE_GAME = {"eboot.bin": "u1", "big2-ps4_Shipping.elf": "u2", "big3-ps4_Shipping.elf": "u3"}
OK, WARN, FAIL, INFO = "ok", "warn", "fail", "info"

# --- the page's words (Arabic first: the player's language; English for everyone else) ------------------------------
WORDS = {
    "title": ("فحص El Dorado", "El Dorado check"),
    "made": ("اتعمل", "Made"),
    "install": ("التثبيت", "The install"),
    "runs": ("مرات اللعب", "The runs"),
    "summary": ("الخلاصة", "Summary"),
    "all_good": ("كله تمام", "All good"),
    "problems": ("فيه {n} مشكلة", "{n} problem(s)"),
    "warnings": ("و{n} ملاحظة", "and {n} note(s)"),
    "files": ("ملفات البرنامج", "Program files"),
    "files_ok": ("كل الملفات اللي التشغيل محتاجها موجودة", "every file a start needs is there"),
    "files_missing": ("ناقص: {list}", "missing: {list}"),
    "dlls": ("مكتبات المحرك (DLL)", "Engine DLLs"),
    "dlls_ok": ("{n} مكتبة موجودة جنب bb-probe.exe", "{n} DLLs next to bb-probe.exe"),
    "dlls_missing": ("ناقص: {list}", "missing: {list}"),
    "qt": ("Qt بتاع اللانشر", "The launcher's Qt"),
    "scripts": ("سكريبتات التشغيل", "Start scripts"),
    "scripts_ok": ("probe_uncharted و cheats و text_languages بيشتغلوا", "probe_uncharted, cheats and text_languages load"),
    "game": ("فولدر اللعبة", "Game folder"),
    "game_missing": ("مش مختار أو مش فيه eboot.bin و sce_sys", "not chosen, or without eboot.bin and sce_sys"),
    "languages": ("لغات {game}", "{game} languages"),
    "languages_ok": ("{n} لغة في النسخة{ar}", "{n} languages in the copy{ar}"),
    "with_arabic": (" (فيها الترجمة العربي)", " (with the Arabic translation)"),
    "shaders": ("شيدرات {game}", "{game} shaders"),
    "shaders_ready": ("متجهّزة: اللعبة تفتح على طول", "prepared: the game opens straight away"),
    "shaders_not": ("لسه: هتتجهّز أول تشغيل (أو من زرار تجهيز الشيدرات)",
                    "not yet: prepared at the first start (or with Prepare shaders)"),
    "disk": ("المساحة الفاضية", "Free disk space"),
    "disk_low": ("{gb} GB بس: الكاش والحفظ محتاجين مساحة", "only {gb} GB: the cache and the saves need room"),
    "gpu": ("كارت الشاشة", "Graphics card"),
    "no_runs": ("مافيش مرات لعب متسجلة لسه: العب وارجع شغّل الفحص", "no runs logged yet: play, then check again"),
    "crashes": ("crash أو تهنيج", "Crashes or freezes"),
    "crashes_none": ("ولا مرة في آخر {n} تشغيل", "none in the last {n} runs"),
    "crashes_some": ("{n} مرة: شوف الجدول تحت", "{n}: see the table below"),
    "prep_again": ("صفحة تجهيز الشيدرات رجعت تاني", "Shader preparation page came back"),
    "prep_again_none": ("لا: بعد أول تجهيز كامل ماظهرتش تاني", "no: not again after a complete preparation"),
    "prep_again_some": ("ظهرت تاني {n} مرة بعد تشغيل اتقفل عادي", "{n} time(s) after a run that closed normally"),
    "cache_lost": ("كتابة الكاش وقت القفل", "Shader cache writes at the exit"),
    "cache_lost_none": ("اتحفظت كلها", "all kept"),
    "cache_lost_some": ("ضاع جزء {n} مرة (اتقفلت والكاش لسه بيتكتب)", "lost some {n} time(s) (closed while writing)"),
    "title_skip": ("تخطّي صفحة البداية", "Title page passed"),
    "title_skip_ok": ("اتعدّت ووقفت عند القايمة {n} مرة", "passed, stopped at the menu {n} time(s)"),
    "title_skip_bad": ("ماوصلتش للقايمة {n} مرة", "did not reach the menu {n} time(s)"),
    "compiles": ("تقطيع من بناء shaders وقت اللعب", "Stutter from shader builds while playing"),
    "compiles_none": ("مافيش", "none"),
    "compiles_some": ("{n} بناء وقت اللعب (ممكن تقطيع خفيف)", "{n} builds while playing (possible small stutter)"),
    "fps": ("متوسط الـ FPS ({game})", "Average FPS ({game})"),
    "fps_value": ("{fps:.0f} (أبطأ لحظة {worst:.0f} ms)", "{fps:.0f} (slowest moment {worst:.0f} ms)"),
    "col_time": ("الوقت", "Time"), "col_game": ("اللعبة", "Game"), "col_length": ("المدة", "Length"),
    "col_end": ("القفل", "Ended"), "col_fps": ("FPS", "FPS"), "col_prep": ("تجهيز", "Prep"),
    "col_note": ("ملاحظة", "Note"),
    "end_confirmed": ("قفل من السؤال", "closed (asked)"), "end_stop": ("STOP", "STOP"),
    "end_close": ("قفل الشباك", "window closed"), "end_menu": ("من قايمة اللعبة", "from the game's menu"),
    "end_none": ("اتقفل فجأة", "ended suddenly"),
    "min": ("د", "min"), "sec": ("ث", "s"),
    "send": ("لو فيه ✗: ابعت الصفحة دي أو زرار تقرير مشكلة من اللانشر (الإعدادات ← المشغّل).",
             "If anything shows ✗: send this page, or the launcher's Problem report (Settings > LAUNCHER)."),
}


def word(key: str, lang: str, **values: object) -> str:
    text = WORDS[key][0 if lang == "ar" else 1]
    return text.format(**values) if values else text


@dataclass
class Check:
    status: str
    title: str
    detail: str = ""


@dataclass
class Run:
    folder: Path
    started: float
    game: str = ""
    seconds: float = 0.0
    exit_code: int | None = None
    ended: str = ""                 # confirmed / stop / close / menu / "" (none: a crash or a kill)
    crash: str = ""
    fps: list[float] = field(default_factory=list)
    worst_ms: float = 0.0
    prep_ms: int = 0
    cache_left: int = 0
    skip_on: bool = False
    skip_menu: bool = False
    compiles_in_play: int = 0
    gpu: str = ""


# --- the install -------------------------------------------------------------------------------------------------------


def pe_imports(path: Path) -> list[str]:
    """The DLL names a Windows executable imports (its import directory)."""
    data = path.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    sections_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    directories = optional + (112 if magic == 0x20B else 96)
    import_rva = struct.unpack_from("<I", data, directories + 8)[0]
    sections = []
    for i in range(sections_count):
        at = optional + optional_size + 40 * i
        size, rva, raw_size, raw = struct.unpack_from("<IIII", data, at + 8)
        sections.append((rva, max(size, raw_size), raw))

    def offset(rva: int) -> int:
        for start, size, raw in sections:
            if start <= rva < start + size:
                return rva - start + raw
        raise ValueError(f"rva {rva:#x} outside the sections")

    names, at = [], offset(import_rva)
    while True:
        name_rva = struct.unpack_from("<I", data, at + 12)[0]
        if not name_rva:
            break
        start = offset(name_rva)
        names.append(data[start:data.index(b"\0", start)].decode("ascii", "replace"))
        at += 20
    return names


def system_dll(name: str) -> bool:
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    return (windows / "System32" / name).exists() or name.lower().startswith("api-ms-") or \
        name.lower().startswith("ext-ms-")


def install_checks(lang: str) -> list[Check]:
    checks: list[Check] = []
    try:
        from core.updater import REQUIRED
    except Exception:  # an old launcher: the list the start needs at least
        REQUIRED = ("launcher/main.py", "tools/probe_uncharted.py", "engine/run.py", "engine/out/bb-probe.exe")
    missing = [name for name in REQUIRED if not (ROOT / name).exists()]
    checks.append(Check(FAIL if missing else OK, word("files", lang),
                        word("files_missing", lang, list=", ".join(missing)) if missing else word("files_ok", lang)))
    probe = ROOT / "engine" / "out" / "bb-probe.exe"
    if probe.is_file():
        try:
            dlls = [name for name in pe_imports(probe) if not system_dll(name)]
            absent = [name for name in dlls if not (probe.parent / name).exists()]
            checks.append(Check(FAIL if absent else OK, word("dlls", lang),
                                word("dlls_missing", lang, list=", ".join(absent)) if absent
                                else word("dlls_ok", lang, n=len(dlls))))
        except (OSError, ValueError, struct.error) as error:
            checks.append(Check(WARN, word("dlls", lang), str(error)))
    try:
        from PySide6 import QtCore  # noqa: F401
        checks.append(Check(OK, word("qt", lang), f"PySide6 {QtCore.qVersion()}"))
    except Exception as error:  # the launcher's window could not open
        checks.append(Check(FAIL, word("qt", lang), str(error)))
    try:
        import cheats  # noqa: F401
        import probe_uncharted  # noqa: F401
        import text_languages  # noqa: F401
        checks.append(Check(OK, word("scripts", lang), word("scripts_ok", lang)))
    except Exception as error:
        checks.append(Check(FAIL, word("scripts", lang), f"{type(error).__name__}: {error}"))
    checks += game_checks(lang)
    try:
        free = shutil.disk_usage(ROOT).free / 1024 ** 3
        checks.append(Check(WARN if free < 5 else OK, word("disk", lang),
                            word("disk_low", lang, gb=f"{free:.1f}") if free < 5 else f"{free:.0f} GB"))
    except OSError:
        pass
    return checks


def game_checks(lang: str) -> list[Check]:
    checks: list[Check] = []
    try:
        from core import config as cfg
        from core import games, settings
        config = cfg.Config.load()
        game_dir = config.game_dir()
    except Exception as error:
        return [Check(WARN, word("game", lang), str(error))]
    if not games.is_game_dir(game_dir):
        return [Check(FAIL, word("game", lang), word("game_missing", lang))]
    checks.append(Check(OK, word("game", lang), str(game_dir)))
    try:
        held = settings.copy_languages(config, log=lambda line: None)
    except Exception as error:
        held = {}
        checks.append(Check(WARN, word("languages", lang, game=""), str(error)))
    for key, name in GAME_NAMES.items():
        languages = held.get(key) or {}
        if languages:
            checks.append(Check(OK, word("languages", lang, game=name),
                                word("languages_ok", lang, n=len(languages),
                                     ar=word("with_arabic", lang) if "ar" in languages else "")))
        prepared = list((USER / "cache").glob(f"*/prepared_{key}_variants"))
        checks.append(Check(OK if prepared else INFO, word("shaders", lang, game=name),
                            word("shaders_ready", lang) if prepared else word("shaders_not", lang)))
    return checks


# --- the runs ----------------------------------------------------------------------------------------------------------

FPS_LINE = re.compile(r"^Frame stats: ([\d.]+) FPS, worst frame ([\d.]+) ms.*?; (\d+) shader/pipeline compiles")
PREP_LINE = re.compile(r"^Preparation screen: shown for (\d+) ms")
CACHE_EXIT = re.compile(r"^Shader cache at exit: (\d+) writes pending, (\d+) left")


def read_run(folder: Path) -> Run | None:
    log = folder / "boot.log"
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        run = Run(folder, log.stat().st_mtime)
    except OSError:
        return None
    header = re.match(r"^# \S+ \S+ (\S+) \((u[123])\)", lines[0]) if lines else None
    if header:
        run.game = header.group(2)
    try:
        result = json.loads((folder / "boot.json").read_text(encoding="utf-8"))
        run.seconds = float(result.get("elapsed_seconds") or 0.0)
        run.exit_code = result.get("exit_code")
        run.game = run.game or EXECUTABLE_GAME.get(result.get("executable", ""), "")
    except (OSError, ValueError):
        pass
    frames = 0
    for line in lines:
        if line.startswith("Frame stats: "):
            match = FPS_LINE.match(line)
            if match:
                frames += 1
                if frames > 2:  # the first ones are the start (loading, the first picture)
                    run.fps.append(float(match.group(1)))
                    run.worst_ms = max(run.worst_ms, float(match.group(2)))
                    run.compiles_in_play += int(match.group(3))
        elif line.startswith("Preparation screen: "):
            match = PREP_LINE.match(line)
            run.prep_ms += int(match.group(1)) if match else 0
        elif line.startswith("Shader cache at exit: "):
            match = CACHE_EXIT.match(line)
            run.cache_left += int(match.group(2)) if match else 0
        elif line.startswith("Skip title: "):
            run.skip_on = True
            run.skip_menu = run.skip_menu or line.endswith("main menu on screen") or line.endswith("menu page on screen")
        elif line.startswith("Window closed (the player confirmed"):
            run.ended = "confirmed"
        elif line.startswith("Window closed (the launcher's STOP"):
            run.ended = "stop"
        elif line.startswith("Window closed (close button") and not run.ended:
            run.ended = "close"
        elif line.startswith("Quit: ") or line.startswith("Runtime: quit"):
            run.ended = run.ended or "menu"
        elif line.startswith("GPU: ") and "MiB VRAM" in line and not run.gpu:
            run.gpu = line[5:].split(", Vulkan")[0]
    try:
        from core.launch import crash_reason
        run.crash = crash_reason(lines[-200:]).split("\n")[0]
    except Exception:
        run.crash = ""
    if run.exit_code not in (0, None) and not run.crash and run.ended not in ("stop",):
        run.crash = f"exit code {run.exit_code}"
    return run


def runs(count: int) -> list[Run]:
    folders = sorted(ATTEMPTS.glob("boot-*"), key=lambda path: path.stat().st_mtime) if ATTEMPTS.is_dir() else []
    found = [run for run in (read_run(folder) for folder in folders[-count:]) if run]
    return found


def run_checks(found: list[Run], lang: str) -> list[Check]:
    if not found:
        return [Check(INFO, word("runs", lang), word("no_runs", lang))]
    checks: list[Check] = []
    crashed = [run for run in found if run.crash]
    checks.append(Check(FAIL if crashed else OK, word("crashes", lang),
                        word("crashes_some", lang, n=len(crashed)) if crashed
                        else word("crashes_none", lang, n=len(found))))
    # The page again after a run of the same game that prepared and closed normally (its cache was kept).
    again = 0
    last_clean: dict[str, bool] = {}
    for run in found:
        if run.prep_ms > 3000 and last_clean.get(run.game):
            again += 1
        clean = bool(run.ended) and run.cache_left == 0 and not run.crash
        last_clean[run.game] = clean
    checks.append(Check(WARN if again else OK, word("prep_again", lang),
                        word("prep_again_some", lang, n=again) if again else word("prep_again_none", lang)))
    lost = [run for run in found if run.cache_left]
    checks.append(Check(WARN if lost else OK, word("cache_lost", lang),
                        word("cache_lost_some", lang, n=len(lost)) if lost else word("cache_lost_none", lang)))
    skipped = [run for run in found if run.skip_on]
    if skipped:
        bad = [run for run in skipped if not run.skip_menu and run.seconds > 60]
        checks.append(Check(WARN if bad else OK, word("title_skip", lang),
                            word("title_skip_bad", lang, n=len(bad)) if bad
                            else word("title_skip_ok", lang, n=len([r for r in skipped if r.skip_menu]))))
    builds = sum(run.compiles_in_play for run in found)
    checks.append(Check(WARN if builds > 20 else OK, word("compiles", lang),
                        word("compiles_some", lang, n=builds) if builds else word("compiles_none", lang)))
    for key, name in GAME_NAMES.items():
        samples = [fps for run in found if run.game == key for fps in run.fps]
        if samples:
            worst = max((run.worst_ms for run in found if run.game == key), default=0.0)
            mean = sum(samples) / len(samples)
            checks.append(Check(OK if mean >= 50 else WARN, word("fps", lang, game=name),
                                word("fps_value", lang, fps=mean, worst=worst)))
    gpu = next((run.gpu for run in reversed(found) if run.gpu), "")
    if gpu:
        checks.append(Check(INFO, word("gpu", lang), gpu))
    return checks


# --- the page ----------------------------------------------------------------------------------------------------------

MARK = {OK: "✓", WARN: "!", FAIL: "✗", INFO: "•"}


def length(seconds: float, lang: str) -> str:
    minutes = int(seconds // 60)
    return f"{minutes} {word('min', lang)}" if minutes else f"{int(seconds)} {word('sec', lang)}"


def page(install: list[Check], played: list[Check], found: list[Run], lang: str) -> str:
    rtl = lang == "ar"
    problems = sum(check.status == FAIL for check in install + played)
    notes = sum(check.status == WARN for check in install + played)
    verdict = word("all_good", lang) if not problems and not notes else \
        word("problems", lang, n=problems) + (" " + word("warnings", lang, n=notes) if notes else "")
    tone = FAIL if problems else WARN if notes else OK

    def rows(checks: list[Check]) -> str:
        return "".join(f'<div class="row {c.status}"><span class="mark">{MARK[c.status]}</span>'
                       f'<span class="what">{html.escape(c.title)}</span>'
                       f'<span class="detail">{html.escape(c.detail)}</span></div>' for c in checks)

    table = ""
    if found:
        head = "".join(f"<th>{word(k, lang)}</th>" for k in
                       ("col_time", "col_game", "col_length", "col_end", "col_fps", "col_prep", "col_note"))
        body = ""
        for run in reversed(found):
            fps = f"{sum(run.fps) / len(run.fps):.0f}" if run.fps else "–"
            ended = word("end_" + (run.ended or "none"), lang)
            note = run.crash or (f"cache −{run.cache_left}" if run.cache_left else "")
            body += (f'<tr class="{FAIL if run.crash else ""}"><td>{time.strftime("%m-%d %H:%M", time.localtime(run.started))}</td>'
                     f"<td>{GAME_NAMES.get(run.game, '?')}</td><td>{length(run.seconds, lang)}</td>"
                     f"<td>{html.escape(ended)}</td><td>{fps}</td>"
                     f"<td>{f'{run.prep_ms / 1000:.0f} s' if run.prep_ms else '–'}</td>"
                     f'<td class="note">{html.escape(note)}</td></tr>')
        table = f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    return f"""<!doctype html>
<html lang="{lang}" dir="{'rtl' if rtl else 'ltr'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{word('title', lang)}</title>
<style>
:root {{ --base:#0c0e12; --panel:#1a1e26; --line:#2c323d; --ink:#eef1f6; --dim:#aeb6c3; --faint:#717b8a;
        --gold:#deb058; --ok:#34c98a; --warn:#ffb347; --fail:#ff6b5e; }}
body {{ margin:0; background:linear-gradient(#151920,#0c0e12) fixed; color:var(--ink);
       font:15px/1.6 "Segoe UI", Tahoma, sans-serif; }}
main {{ max-width:960px; margin:0 auto; padding:32px 16px 48px; }}
.brand {{ color:var(--gold); letter-spacing:{'0' if rtl else '.3em'}; font-size:13px; }}
h1 {{ font:400 34px Georgia, serif; margin:4px 0 2px; }}
.made {{ color:var(--faint); font-size:13px; }}
.verdict {{ margin:22px 0; padding:16px 20px; border-radius:12px; background:var(--panel); font-size:20px;
           border-inline-start:4px solid var(--{tone}); }}
h2 {{ color:var(--gold); font-size:13px; letter-spacing:{'0' if rtl else '.15em'}; margin:28px 0 8px; }}
.row {{ display:grid; grid-template-columns:28px minmax(150px,240px) 1fr; gap:10px; padding:9px 12px;
       border-bottom:1px solid var(--line); align-items:baseline; }}
.mark {{ font-weight:700; text-align:center; }}
.ok .mark {{ color:var(--ok); }} .warn .mark {{ color:var(--warn); }} .fail .mark {{ color:var(--fail); }}
.info .mark {{ color:var(--dim); }}
.detail {{ color:var(--dim); overflow-wrap:anywhere; }}
.fail .detail {{ color:var(--fail); }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th {{ color:var(--faint); font-weight:400; text-align:start; padding:6px 8px; border-bottom:1px solid var(--line); }}
td {{ padding:6px 8px; border-bottom:1px solid var(--line); color:var(--dim); }}
tr.fail td {{ color:var(--fail); }} td.note {{ overflow-wrap:anywhere; }}
.send {{ margin-top:28px; color:var(--faint); font-size:13px; }}
@media (max-width:640px) {{ .row {{ grid-template-columns:24px 1fr; }} .detail {{ grid-column:2; }}
  table {{ font-size:12px; }} }}
</style></head><body><main>
<div class="brand">EL DORADO</div><h1>{word('title', lang)}</h1>
<div class="made">{word('made', lang)} {time.strftime('%Y-%m-%d %H:%M')}</div>
<div class="verdict">{html.escape(verdict)}</div>
<h2>{word('install', lang)}</h2>{rows(install)}
<h2>{word('runs', lang)}</h2>{rows(played)}{table}
<p class="send">{word('send', lang)}</p>
</main></body></html>
"""


def language() -> str:
    """The launcher's language: Arabic for Arabic, English for every other."""
    try:
        from core import config as cfg
        from core import i18n
        return "ar" if i18n.chosen(cfg.Config.load().data.get(i18n.SETTING)) == "ar" else "en"
    except Exception:
        return "en"


def main() -> int:
    parser = argparse.ArgumentParser(description="El Dorado's health check (read only).")
    parser.add_argument("--lang", choices=("ar", "en"))
    parser.add_argument("--runs", type=int, default=30, help="the last N runs read (default 30)")
    parser.add_argument("--no-open", action="store_true", help="do not open the page in the browser")
    args = parser.parse_args()
    lang = args.lang or language()
    print("El Dorado check: reading the install and the logs...", flush=True)
    install = install_checks(lang)
    found = runs(args.runs)
    played = run_checks(found, lang)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(page(install, played, found, lang), encoding="utf-8")
    failures = [check for check in install + played if check.status == FAIL]
    notes = [check for check in install + played if check.status == WARN]
    print(f"{len(failures)} problem(s), {len(notes)} note(s). The page: {REPORT}")
    if not args.no_open:
        try:
            os.startfile(str(REPORT))  # type: ignore[attr-defined]  # Windows
        except OSError:
            pass
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
