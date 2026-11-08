# ui/

The launcher's window. QML draws; the Python models hand it the data from `../core/` and turn core's errors into
messages for the player. Nothing here reads or writes the player's files itself.

- `bridge.py` — `launcher`: the games, the chosen one (kept in launcher.json), where the player left off, the
  expedition log, the background's address, PLAY/STOP, the running game's state and status (a switch to another
  game of the Collection, why a run ended); the crash screen (`crashed`, and `directCrashed` for a --play start
  from Steam or a shortcut, which then opens the window) and the frame rate advice (`advise`, `takeAdvice`).
- `app_model.py` — `app`: launcher updates, the game folder and game update (chosen, or from a .pkg), the files
  check, the shader cache, shortcuts, Steam, the player's folders, reset, the first start, quit; `busy`,
  `statusText` and `progress` while a long action runs. The update check at start runs on its own thread and
  never holds the buttons back.
- `steam_art.py` — each game's Steam library pictures in El Dorado's look (the drawn map, the game's drawn icon,
  its title in the launcher's fonts); nothing of the game's.
- `language_model.py`, `profile_model.py` — `i18n` (the launcher's language, right to left for Arabic) and
  `profiles` (the players).
- `saves_model.py`, `trophies_model.py`, `gallery_model.py` — the Saves, Trophies and Gallery screens.
- `settings_model.py` — the Settings screen's tabs, presets and the key, mouse and controller binding capture.
- `background.py` — the home screen's picture (image://background), drawn with QPainter on Qt's image thread.
- `theme.py` — the colors of `qml/Theme.qml` for `background.py` (one place for every color).
- `gamepad.py` — controller input for the window (SDL3 through ctypes); `device` says which key hints to show.
- `windows.py` — Windows calls made before Qt starts: one launcher at a time (named mutex; a second start brings
  the open window to the front), the taskbar id, the game window check, the process age for the cold start measure.
- `qml/` — `Main.qml` (the window, the rail, the keys), `Theme.qml` (every color and font, one place),
  `components/` (buttons, rows, key hints, the dialogs, the loading overlay), `pages/` (one file per screen).
- `assets/` — El Dorado's own art only. No game or Sony pictures.
