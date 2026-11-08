# El Dorado Launcher v2 — roadmap

> **Done.** Launcher v2 became `main` on 8 Nov 2026 and shipped as **1.0.0-beta1** (the `launcher-v2` branch is
> gone). Beta 2 work is on `release/1.0.0-beta2`: the crash screen, each game in Steam with its own icon and
> pictures, the frame rate advice, F11 and the window fit. This page is kept as the record of how v2 was planned.

Branch (then): `launcher-v2`. Goal: a new launcher written from scratch for El Dorado, in **Python + PySide6 (Qt Quick /
QML)**, with no code from the legacy launcher, and at least every feature the released launcher has.

Only the launcher (the window outside the game) changes. The engine (`engine/`, `bb-probe.exe`), the game start
script (`tools/probe_uncharted.py`) and the update installer (`tools/apply_update.py`) are kept and called the same way.

The released launcher (Tkinter) stays on `main` and keeps shipping until v2 reaches parity. On this branch it lives
in `legacy/launcher-tk/` as a reference only (see its README).

---

## 1. Decisions

| Topic | Decision | Why |
|---|---|---|
| UI toolkit | PySide6 6.x (Qt Quick + QML, Qt Quick Controls Basic style) | GPU-drawn UI, animations, scaling and controller/keyboard focus without drawing by hand; LGPL, official Qt binding |
| Language | Python 3.12+ (the packaged Windows Python, as today) | The start script, saves, trophies, Steam, updater logic is Python already |
| Layout | `launcher/` = new code; `legacy/launcher-tk/` = old code (read only) | One place for the new launcher; the old one is not run on this branch |
| Package growth | Measured 7 Nov 2026: +23 MB zipped, +63 MB unpacked (PySide6 Essentials 6.12.0 trimmed by `tools/copy_pyside.py` to QtCore, QtGui, QtNetwork, QtQml, QtQuick, Controls Basic, Layouts, Dialogs, the Windows platform plugin) | The full PySide6 Essentials wheel is 214 MB unpacked |
| Settings file | Same `%APPDATA%\El Dorado Launcher\launcher.json` and per-game `analysis\uncharted-user\probe-uN.ini` | Players keep their settings across the switch |
| Engine contract | Unchanged (section 3) | The game starts exactly as today |

## 2. Target structure

```
launcher/
  main.py                 entry point: single instance, Qt app, loads the QML
  core/                   no Qt imports; unit-tested
    paths.py              ROOT, USER_DIR, config locations
    config.py             launcher.json + probe-uN.ini read/write, migrations (versions)
    games.py              the three games, executables, edition (Arabic/original from param.sfo), version 1.02 check
    gpu.py                GPU/VRAM detection for the Recommended preset
    presets.py            presets and the Recommended choice
    saves.py              list, delete (to savedata-deleted), restore, delete for good, backups list/restore
    trophies.py           wraps engine/scripts/trophies.py (cache, unlocks, progress)
    gallery.py            screenshots per game, delete to Recycle Bin
    stats.py              eldorado-stats.json (play time, last played, average FPS)
    launch.py             builds the UNCHARTED_* environment, starts/stops tools/probe_uncharted.py, reads its output
    updater.py            GitHub releases check, download, stage, hand-off to tools/apply_update.py
    shortcuts.py          desktop shortcuts per game (icons from the player's trophy packs)
    steam.py              non-Steam shortcuts (ported from legacy steam_library.py logic, rewritten)
    input_map.py          key/mouse/pad bindings model for probe-uN.ini (key_map, mouse_map, pad_map)
  ui/
    bridge.py             QObject models exposed to QML (games, saves, trophies, settings, status)
    gamepad.py            controller input for the UI (SDL3 via ctypes, as the engine ships SDL3.dll)
    qml/                  Main.qml, screens (Games, Saves, Trophies, Gallery, Settings, Loading), components
    assets/               El Dorado's own art only (no game or Sony files)
tests/
  test_core_*.py          one file per core module, run in CI
```

Rules: `core/` never imports Qt (testable without a display); QML holds no logic beyond presentation; every file
written by the launcher is written through a temporary file and renamed (as today).

### 2.1 Code rules (clean code, no copy-paste)
- **Written new, not copied.** The legacy launcher is read to learn *what* a feature does; the code is written again
  in the new structure. No function, class or block is pasted from `legacy/launcher-tk/`.
- **One job per module and per class.** A module owns one topic (saves, trophies, launch...). The UI never
  touches files or processes itself; it calls `core/`.
- **Layers, one direction only:** QML → `ui/bridge.py` → `core/*` → files / processes. `core/` modules do not
  import `ui/`; `core/` modules depend on each other only through clear functions (no shared globals).
- **No duplicated code.** Something needed twice becomes one function (for example one safe-write helper, one
  path helper, one game table). QML repeats become components (Button, Card, Toggle, KeyHint, Page).
- **Data in one place.** The three games (names, executables, ids, keys) are one table in `core/games.py`;
  settings defaults and their limits are one table in `core/config.py`; colors and fonts are one QML theme file.
- **Small functions, clear names, type hints** on every public function; dataclasses for records (Game, Save,
  Trophy, Backup, Settings) instead of loose dicts.
- **Errors are handled where they can be shown:** `core/` raises clear exceptions; the bridge turns them into a
  message for the player. No silent `except: pass`.
- **Checks in CI:** `ruff` (lint + format), `mypy` on `core/`, `pytest`; a pull request does not merge with them red.
- **Short comments** that say why, not what; one README per folder (`core/`, `ui/`, `qml/`) that says what lives there.

## 3. Engine contract (must stay identical)

The launcher starts the game with:

```
python\python.exe -u tools\probe_uncharted.py --boot --seconds 0 --executable <eboot.bin|big2-ps4_Shipping.elf|big3-ps4_Shipping.elf> --game <game folder>
```

and reads its output line by line (`Log:`, `Collection: switching to <exe>`, `Discord:`, engine errors). It writes
before each start:

- `analysis\uncharted-user\probe-u1.ini`, `-u2`, `-u3`: display_mode, vsync, fps_limit, frames_queued, upscaler, fsr1,
  rcas, rcas_strength, frame_gen, show_fps and the overlay_* keys, prompts, menu_shortcut, key_map, mouse_map, pad_map,
  mouse_sens, mouse_aim_sens.
- Environment: `UNCHARTED_RESOLUTION_<G>`, `UNCHARTED_OUTPUT_RES_<G>`, `UNCHARTED_MULTITHREADED_<G>`,
  `UNCHARTED_SAVE_PROFILE_<G>`, `UNCHARTED_LANGUAGE_<G>` (each game its own: a PS4 language id, or `ar` = the
  Arabic translation, found by `tools/arabic_language.py`), `UNCHARTED_LANGUAGE` (the selected game's, kept for old
  scripts), `UNCHARTED_ANISOTROPY`, `UNCHARTED_NO_DOF`, `UNCHARTED_UNLOCK`,
  `UNCHARTED_CHEATS` (skipintro, invincible, ammo, grenades, treasures, rewards), `UNCHARTED_JOB_SLEEP`,
  `UNCHARTED_DIAGNOSTICS`, `UNCHARTED_UPDATE` (a chosen update folder; else a `<game folder>-patch` next to the game
  is found and laid over it by `tools/game_update_view.py`); `UNCHARTED_DISCORD=0` turns Discord presence off.
- The start script writes the first line of every boot.log as before, then `# language (launcher -> engine): ...`
  with what each game got (the quickest check that a setting arrived).

Not carried over (no effect with the current engine; verified 5 Nov 2026): `UNCHARTED_SPEAKERS`,
`UNCHARTED_TORCH_FORWARD`, `UNCHARTED_HIRES_SHADOWS`, `UNCHARTED_FULL_RES_TEXTURES`, `UNCHARTED_UNLOCK_REWARDS`
(the rewards cheat replaced it), the `UNCHARTED_NET_*` LAN settings, and the Multiplayer page. Before phase 4, each
remaining Performance and Display setting is checked the same way (does `probe_uncharted.py` or the engine read it);
whatever is read by nobody is dropped, not copied.

Stopping a game: terminate the start script; it owns a Windows job that ends the game with it.

While a game runs the launcher steps aside: its window is hidden once the game's window is up (title ending in
" — El Dorado"), it draws nothing and only checks twice a second whether the start script still runs, and it comes
back by itself however the game ends (its menus, the close question, a crash, STOP). Closing is asked inside the
game, not by the launcher: the engine shows "Close the game?" for the window's close button, Alt+F4, the menus'
Quit and the back button on the main menu (`BB_CONFIRM_CLOSE=0` turns it off).

## 4. Phases

Each phase ends with its acceptance checks passing; nothing ships from this branch before phase 6.

### Phase 0 — Skeleton (1 day)
- `launcher/main.py`, an empty QML window in El Dorado's colors, single instance (named mutex, bring the open window
  to the front), DPI scaling, the app icon, the taskbar identity `ElDorado.Uncharted.Launcher`.
- Packaging proof: `tools/package_windows.sh` builds a zip with the trimmed PySide6; measure size and cold start time.
- Accept: the zip starts on a clean Windows 10/11 PC without Python installed; cold start < 2 s; size within the +35 MB budget.
- DONE 7 Nov 2026 (measured on the RTX 3060 laptop): PySide6 Essentials 6.12.0, trimmed by `tools/copy_pyside.py`
  from 214 MB to 60 MB unpacked, **23 MB zipped**. Cold start (process start to the first frame,
  `main.py --measure`) from the package's own Python with no Python on PATH: **0.91 s** the first time, 0.53–0.56 s
  after. A second start opens no second window (it brings the open one to the front). The open window uses 103 MB
  of RAM. Not yet tried on a second PC without Python.

### Phase 1 — Core (3 days)
- Write every `core/` module listed in section 2 from the behavior of the legacy launcher (read, not copied), with
  tests: config read/write and migrations (an existing launcher.json from 1.0.0 loads unchanged), presets and
  Recommended, edition detection, saves (delete/restore/purge/backups on a temp copy), trophies progress, stats,
  launch environment (compare the built environment and ini files against what the legacy launcher writes for the
  same settings), updater version compare and staging, shortcuts and Steam (VDF round trip tests exist in
  `tools/test_steam_library.py`; port them).
- Accept: `python -m pytest tests` green; the launch environment and ini output match the legacy launcher's for the
  three games and all presets.
- DONE 7 Nov 2026: every `core/` module of section 2 exists (`core/README.md`), `pytest tests` green (76 tests).
  `tests/test_core_settings.py` runs the legacy launcher itself (through the packaged Python, which has Pillow) and
  compares the environment, the three ini files and the launcher.json game entries for every preset, every card class
  and a set of control changes: identical in all 96 cases. The resolution/upscaling sizes match in 560 cases.
  Controls are **one set for the three games (ALL GAMES)** with a game's own items on top, item by item (a key's two
  slots, a controller button, or a mouse/controller setting; `core/controls.py`, launcher.json `shared_controls` +
  per game `own_controls`): a key changed with "These keys are for: Uncharted 1 only" is that game's own,
  everything else keeps following ALL GAMES, and one button ("USE THE ALL GAMES KEYS") gives the game's own keys
  back; the in-game menu's changes go to ALL GAMES unless the game owns that item. The screen shows nothing more
  than that one choice and that one button (a first version with per-key marks was too much). An existing launcher.json keeps every game's controls: the games' most common set becomes ALL GAMES
  and what differs becomes that game's own (the user's copy: Uncharted 2 and 3 alike, Uncharted 1 with 12 own
  items). Dropped because nothing reads them (section 3): async_shaders, mouse_vertical, mouse_invert_x, low_vram,
  XeSS.

### Phase 2 — Home screen (3 days)
- Games: the three games, the background from the latest save picture or the edition's art, Continue (latest save,
  chapter, play time, treasures), play stats, trophies %, PLAY/STOP, the expedition log (latest saves).
- Loading overlay after PLAY until the game window opens (the engine shows its own loading screen inside the game);
  then the window hides and comes back when the game ends (section 3).
- Status line from the start script's output; crash/exit messages.
- Keyboard, mouse and controller navigation everywhere, with key hints for the device in use.
- Accept: a game starts, stops and restarts from the hub; switching games from the Collection menu is reported.
- DONE 7 Nov 2026 (code): the selected game's latest save picture behind the home screen (else the player's own
  art from the game folder at runtime, else El Dorado's drawn map: `core/art.py`, `ui/background.py`), CONTINUE
  (the latest save, when it was saved), the expedition log (the latest saves of all games), the loading overlay
  after PLAY (Enter twice stops), the reason a run ended from the engine's log (`core/launch.py`), key hints for the
  device in use on every screen, the rail's UPDATE (when a release is ready), LOGS and QUIT, `--play` from a game's
  shortcut. A Collection switch keeps the launcher hidden and names the next game. The drop-downs, toggles and
  buttons are drawn in El Dorado's colors (`components/DropDown.qml`). Not yet tried by hand with a running game.

### Phase 3 — Saves, Trophies, Gallery (2 days)
- Saves: list with pictures; delete (twice), Deleted saves (restore, delete for good), Backups (restore twice; only
  backups of saves that exist).
- Trophies: progress, per-grade counts, the list with icons from the player's own trophy pack.
- Gallery: F12 screenshots per game, open, open folder, delete to the Recycle Bin.
- Accept: every action works on a copy of a real save folder; nothing is ever deleted outright except "delete for good".
- DONE 7 Nov 2026: `core/saves.py`, `core/trophies.py`, `core/gallery.py` with their screens; moves are rename-only
  with rollback; save titles from `<dir>.sce_sys/param.bin` (what the saves actually have); the trophy list uses the
  player's own pack through `engine/scripts/trophies.py`. Tested on temporary copies; not yet tried by hand on the
  real saves (delete, restore, Recycle Bin).

### Phase 4 — Settings (4 days)
- Quick setup (presets with Recommended), Display, Performance, Controls (key, mouse and controller binding capture,
  prompt style, sensitivity, invert, vibration), Cheats (as listed in section 3, all off by default, "made for update
  1.02"), Advanced (save profile, language per game with "Arabic (translation)", texture filtering, depth of field,
  in-game menu shortcut, updates,
  performance log, shortcuts, Steam, game folder, game update folder/.pkg, check game files, clear shader cache, reset).
- Settings are per game where they are today, except the controls: one set for the three games (ALL GAMES) and a
  game's own items on top, item by item (decided 7 Nov 2026); changes are saved at once.
- Accept: every setting written by v2 produces the same probe-uN.ini / environment as the legacy launcher (tests from
  phase 1 extended); binding capture works for keyboard, mouse buttons/wheel and controller.
- DONE 7 Nov 2026: `core/settings.py` (one table of every setting and the editor that saves each change at once),
  `core/presets.py`, `core/gpu.py`, `core/input_map.py`, the Settings screen with its six tabs. Key capture binds
  letters and digits by scancode (an Arabic layout binds the right key); Insert and Left Alt are refused. Controller
  buttons are chosen from a list (no capture by pressing). "Arabic (translation)" is listed only when the player's
  copy has the translation (checked in the background with `tools/arabic_language.py`, as the start script does).

### Phase 5 — Updates and first start (2 days)
- Update check at start (optional), download with progress, staging, hand-off to `tools/apply_update.py`, restart.
- First start: choose the game folder, apply Recommended to all games, desktop shortcuts offer.
- Settings migration from the legacy launcher's launcher.json (same file, version bump only).
- Accept: an installed 1.0.x package updates to a v2 build and back to the release channel without losing settings or saves.
- DONE 7 Nov 2026 (code): `core/updater.py`, `core/shortcuts.py`, `core/steam.py`, `core/game_files.py` (game and
  update folders, update .pkg and game .pkg install, file check, shader cache, reset), `ui/app_model.py`, the first
  start page, `--play u1|u2|u3` from a game's shortcut (no window, the launcher ends with the game). The pickers are
  Qt Quick Dialogs (Windows' own dialogs, no QtWidgets). NOT yet tried: a real release download and the hand-off to
  `apply_update.py`, real desktop shortcuts, the real Steam library (they write outside the repo).

### Phase 6 — Parity, switch, release (2 days)
- Go through the parity checklist (section 5) on the user's PC with both game editions.
- Package and workflow: `package_windows.sh` copies `launcher/` (new) and PySide6; `updater.py` REQUIRED lists the
  new entry point; `tools/windows_starter` starts `launcher\main.py`. DONE 7 Nov 2026 (the GitHub workflow downloads
  PySide6 Essentials 6.12.0 into `downloads/pyside6`; `tools/copy_pyside.py` trims it into the package). Pillow stays
  for the shortcut and Steam icons, Tkinter for the update installer's window (a later trim: both through Qt).
- Delete `legacy/launcher-tk/`; merge `launcher-v2` into `main`; the first public release (nothing has been released yet: its version is chosen then).

Estimate: about 17 working days for one developer working by hand; the code of most phases takes a working
session or two here, and the time that counts is the player's testing on a real PC after each phase.

## 5. Parity checklist (from the released launcher, 5 Nov 2026)

Home: game list (I/II/III) · background (save picture / edition art) · Continue info · play stats line · trophies % ·
PLAY/STOP · expedition log · loading overlay · status line · rail: Saves, Trophies, Gallery, Settings, Update (when
available), Logs, Quit · controller/keyboard/mouse navigation · key hints per device.

Saves: list · delete twice · Deleted saves: restore, delete for good · Backups: restore twice, only for existing saves.

Trophies: % and grade counts · list with earned dates and locked/hidden entries · icons from the trophy pack.

Gallery: grid per game · open · open folder · delete to Recycle Bin.

Settings → Quick setup: Recommended (GPU-based), iGPU, Low, Medium, High, Ultra; per-game note.
Settings → Display: aspect ratio, resolution, upscaling (off/FSR 1/FSR 3.1/FSR 4/DLSS, by GPU), upscaling quality,
anti-aliasing, display mode, VSync, frame generation, sharpening, performance counter (items, corner, layout, size,
background).
Settings → Performance: frame rate limit, frames queued, multithreaded rendering (on by default), idle game threads
(plus any other setting confirmed read by the engine).
Settings → Controls: key/mouse bindings by group, controller bindings, button prompt style, mouse sensitivity, aim
sensitivity, invert, vibration, reset; ALL GAMES | Uncharted 1 | 2 | 3 at the top: one set for the three games, a
game's own items on top (the legacy launcher's vertical sensitivity and invert-X are dropped: the engine reads
neither).
Settings → Cheats: skip intro, invincible, infinite ammo, infinite grenades, give all treasures, unlock all rewards,
unlock all chapters.
Settings → Advanced: save profile, language per game (+voices; "Arabic (translation)" when the copy has one; the box
shows the selected game's own), texture filtering, no depth of field, in-game menu shortcut,
check for updates, performance log, desktop/game shortcuts, add to Steam (collection / per game), open log/save
folders, change game folder, install game from .pkg, check game files, game update folder / .pkg, check for updates,
clear shader cache, reset all settings, credits.

App: single instance · El Dorado icon and taskbar identity · settings migration · update flow · Discord presence
(started by the start script, nothing in the launcher) · no game or Sony files shipped · hidden while a game runs,
back when it ends · game update (.pkg, e.g. the Arabic translation) installed and laid over the game.

In the engine/start script (nothing to rebuild in the launcher, only keep passing the same settings): each game's
loading icon on its window and taskbar button (`launcher/assets/loading/u1-3.png` drawn by
`tools/draw_loading_icons.py` until the player's own is taken from the first loading screen) · the close question ·
the Arabic text patch · per-game language.

## 6. Risks

- **PySide6 size or start time** over budget → trim plugins/QML modules further; measured in phase 0 before anything else.
- **Controller input in Qt** (Qt has no gamepad module in Qt 6) → SDL3 via ctypes, as the engine already ships SDL3.dll.
- **Behavior drift** from the legacy launcher (a setting written differently) → phase 1 comparison tests against the
  legacy output for every preset and game.
- **Engine changes on `main`** during the work → merge `main` into `launcher-v2` weekly; only `tools/probe_uncharted.py`
  and the engine are shared, the contract in section 3 is updated with them.

---

## 7. Engine performance track (separate from the launcher; done on `main`)

The launcher rewrite does not change game FPS. Game speed is the engine's (`engine/`). This track runs on `main`
next to the launcher work. Rule: **only changes with a measured gain ship; no feature is removed or turned off**
(save pictures, backups, screenshots, trophies, cheats, prompts, multithreaded rendering, mouse on guns, Discord
all stay as they are).

### 7.1 Where the time goes (measured)
- Heavy scenes (Uncharted 1 jungle): 3,700–4,000 draws per frame at about 8 µs each on one GPU command thread →
  28–35 FPS on an i3-class CPU; the GPU is not the limit there.
- Multithreaded rendering (`BB_DRAW_PIPE`, stage A/B/C) is already on by default for all games (launcher config 9).

Status (6 Nov 2026): steps 1 and 2 done and pushed (new profile recorded on all three games; LTO on by default in
`engine/build.sh`). The Uncharted 1 jungle went from dips to about 55 FPS to a steady 59-60 (57 at worst).

### 7.2 Step 1 — new PGO profile for our code (guaranteed; do first) — DONE
- Why: Mevlock measured LTO + PGO at −4.8% GPU-thread time per draw (7.72 → 7.35 µs, 73.2 → 76.3 FPS, three runs,
  >800 draws/frame; `mevlock-src/docs/parallel_gpu.md`). Our `pgo/merged.profdata` (4 Nov 2026) was made from
  Mevlock's 0.3.6.43 code; our ports changed many functions, and builds report them as "changed / new since the
  profile" — those get no PGO at all now.
- How:
  1. `BB_PGO=generate ./build.sh` (instrumented build; writes `pgo/*.profraw` every 30 s while the game runs).
  2. Play with that build: each game, about 5 minutes of real play (U1 jungle, U2 convoy/streets, U3 desert or
     chateau), plus the save list, a save, the in-game menu. The instrumented build is slower; that is expected.
  3. `llvm-profdata merge -o pgo/merged.profdata pgo/*.profraw`.
  4. `BB_PGO=use ./build.sh`; the build log must show (almost) no "changed / new since the profile" functions.
- Accept: same spot, same settings (1080p, DLSS Quality, 60 FPS limit off for the test), U1 jungle `Frame stats`
  in boot.log: µs/draw and FPS not worse than before; normally 3–5% better.
- Time: about 30–40 min build + 20–30 min play + 30–40 min build → **about 2 hours**, half of it the player's.
- Redo it after any large engine change (a merge from Mevlock, a big port).

### 7.3 Step 2 — LTO on, A/B tested (likely, not guaranteed) — DONE, kept
- Mevlock: LTO alone −1.8% µs/draw once (`parallel_gpu.md`), "no gain" another time (`PERFORMANCE_2026-10-18.md`).
- How: `BB_LTO=ON BB_PGO=use ./build.sh`; compare against step 1's build in the same spot (three runs each).
  Keep it only if it wins in all three runs.
- Time: about 1 hour build + 15 min test.

### 7.4 Not now (no measured gain, or risk)
- `-O3` (`BB_OPT=3`): not measured; can grow code and lose. Only as an A/B like step 2, after it.
- A different memory allocator (mimalloc): not measured in this engine; touches every allocation. Later, A/B only.
- Lower settings or turning features off: not part of this track (the player chooses settings in the launcher).
- Frame generation: already in the engine and the launcher (Display); it adds frames, not CPU speed.

### 7.5 Order
1. Step 1 (PGO for our code). 2. Step 2 (LTO A/B). 3. Commit the new profile with the engine change it was made for.
4. Later, one item of 7.4 at a time, each with the same A/B.
