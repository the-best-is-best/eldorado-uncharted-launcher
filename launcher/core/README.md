# core/

The launcher's logic: files, settings, games, saves, starting the game. No Qt import here, so every module runs
and is tested without a display. The UI (`../ui/`) calls these functions; nothing here calls the UI.

- `paths.py` — where the package, the player's files and launcher.json live; the app's name and taskbar id.
- `games.py` — the three games (one table) and the game-folder check.
- `config.py` — launcher.json (shared with the released launcher) and each game's probe-uN.ini.
- `resolution.py` — the size a game draws at and the size it is upscaled to.
- `launch.py` — the start script's command and UNCHARTED_* environment; one running game (start, output, stop);
  what the output and the engine's log say (a switch to another game, why a run ended).
- `art.py` — which picture stands behind a game on the home screen (a save's, the player's own art, or a drawn
  map) and which part of it; `ui/background.py` draws the choice.
- `stats.py` — play time, last played and average FPS (eldorado-stats.json).
- `settings.py` — every setting in one table (where it is stored, its options, default) and the editor that saves
  each change at once; `presets.py` (Quick setup and Recommended), `gpu.py` (the graphics card), `input_map.py`
  (key, mouse and controller bindings in probe-uN.ini).
- `saves.py` — saves, deleted saves and backups (moves by rename with rollback; nothing removed but "delete for good").
- `trophies.py`, `gallery.py` — trophy progress from the player's own pack; F12 screenshots (delete to Recycle Bin).
- `updater.py` — releases check, download, staging, hand-off to tools/apply_update.py.
- `game_files.py`, `shortcuts.py`, `steam.py` — game and update folders, file check, shader cache; desktop
  shortcuts; non-Steam entries in the Steam library.
- `safe_write.py` — every file written through a temporary file and a rename.
