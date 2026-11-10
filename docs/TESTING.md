# Testing in the game

What to try in the game after a change, where, and what should happen. Each item leaves a line in the game's log
when it runs, so `tools/test_report.py` can tell from the logs which items were tried and whether they worked:

```bash
python tools/test_report.py --root "<install folder>"           # report since the installed engine was copied
python tools/test_report.py --root "<install folder>" --mark wheel_picture ok "looks right"
```

It prints the report and writes it to `analysis/test-report.md` in the install. A status is **PASSED** or
**FAILED** from the logs, **LOOK** when it ran but only your eyes can tell (mark it with `--mark <id> ok|fail`),
**NOT TRIED** when no log shows it yet, and **INFO** for numbers to compare. A mark wins over the logs and is kept
in `analysis/uncharted-user/test-marks.json`.

## Current list (engine merged up to Mevlock 0.3.6.50, 9 Nov 2026)

| Id | Where | What to do | What should happen | The log line |
| --- | --- | --- | --- | --- |
| `wheel_mouse` | Uncharted 1, any door wheel or valve | When the turn prompt shows, draw circles with the mouse (the other way if it does not move) | Nate turns it and the door opens; the camera keeps still meanwhile | `Mouse: the turn-the-stick prompt went away while the mouse turned the stick (done)` |
| `wheel_picture` | The same place | Look at the prompt under the game's ring arrow | A mouse going round by itself in the launcher's look (no W A S D) | LOOK: mark it |
| `walk` | Any game | Press B, move with W A S D, then press B again | After the first press Nate walks; after the second he runs again | `Pad: walk key pressed: Nate walks`, then `... Nate runs` |
| `mouse_camera` | Uncharted 2 or 3, walking around | Look around with the mouse, not aiming | As smooth as I J K L: no sticky or heavy feel, no drift after the mouse stops | `Mouse: Uncharted N follow camera turned in its input function` (LOOK: mark how it feels) |
| `mounted_guns` | Any game, a mounted gun (turret); Uncharted 1's jeep gun | Get on it and aim with the mouse | The mouse aims it directly, like the camera | `Mouse: Uncharted N mounted gun entered` |
| `rewards` | Settings → CHEATS → Unlock all rewards, then each game's Bonuses | Open Bonuses | Every skin, weapon, render mode and cutscene unlocked; turned off, only your own | `Unlock all rewards: ... patched` |
| `u1_cross_prompt` | Uncharted 1, Nate on the ground after a fall (Drowned City) | Look at the big X at the bottom left | Your key (Space), not the PlayStation X | LOOK: mark it |
| `u1_push_prompt` | Uncharted 1, pushing the stone (Drowned City) | Look at the prompt at the bottom left | W above, A S D below, the one the stick leans to lit; not the PlayStation stick | LOOK: mark it |
| `onehit_jetski` | Uncharted 1 jet ski, One hit kills on | Let Elena shoot; then off the boat hit an enemy yourself and let one hit Elena | On the jet ski Elena's shots kill; off the boat your hits kill and an enemy's hit does not kill Elena | `One hit kills: Uncharted 1 jet ski: Elena's shots count` |
| `u1_crank_mouse` | Uncharted 1, the machine's crank in the engine room | Turn it with the mouse | The prompt shows the mouse going round and the mouse turns the crank | `Mouse: the turn-the-stick prompt is on screen` |
| `trophies_cheat` | Settings → CHEATS → Unlock all trophies | Turn it on, start a game, then open the launcher's Trophies page | Every trophy of that game, the platinum too, shows as earned; nothing already earned is changed | `Unlock all trophies: N added` |
| `menu_sensitivity` | Insert → settings → Mouse | Change Aiming sensitivity and Vertical sensitivity | Aiming and looking up and down follow the new values | `Mouse: aiming or vertical sensitivity changed in the in-game menu` |
| `checkpoint_jump` | Insert → Checkpoints | Double-click a checkpoint | The game goes there at once | `Checkpoints: jumping to task` |
| `fullscreen_keys` | Any game | Press Alt+Enter (and F11) | Window and fullscreen switch | `Window: Alt+Enter, ...` |
| `pause` | Any game | Minimize, or Alt+Tab, then come back | Everything stops (sound too); back, the pause menu is open | `game threads frozen ...` then `Pause: back from the background` |
| `u3_hitches` | Uncharted 3, chapter starts and cutscene starts | Play through a few | Fewer short freezes when a level loads or a cutscene starts | INFO: frames over 50 ms |
| `u2_long` | Uncharted 2 | Play an hour or more in one go | No crash, no slowdown from video memory running out (6 GB cards) | a run of 60+ min without a crash |
| `sound_cuts` | Any game, 20 minutes or more (Uncharted 1 chapter 6 was reported) | Play | The music never cuts out for seconds | no `File: slow read` and no `Audio stats ... starved` lines |
| `u3_triangle` | Uncharted 3, the cargo plane scene (Nate holds the net, Triangle) | Reach it with the keyboard | Today the PlayStation Triangle shows; the engine keeps the picture in `analysis/uncharted-user/prompt-dumps`, the report finds it, and it is added to the prompt table | INFO when captured; LOOK once added |
| `cache_writes` | The first start of each game after an engine update (the shader preparation page shows) | Let the page finish, then start or continue a game | The page stays until the new shaders are on disk; choosing a difficulty and loading no longer hang | `Preparation screen: waited ... for N shader cache writes`; no `Shader cache: one write took` after the page |
| `loading_on` | Any game | Start it, then Alt+Tab away before its first picture | It goes on loading; it pauses only once its first picture is up | `Pause: the window is in the background while the game loads: it loads on` |
| `view_kept` | Any game, the second start on | Start a game twice | The game with its update is not made again (it took 2-6 s) | `# update view: kept in 0.0x s` in the log's header |
| `cache_pack` | Any game, the second start on | Start a game twice | Its shaders load from one file (blobs.pack in its cache folder), no file errors | `Pipeline cache: preloaded N of M`, no `Failed to open the file` |
| `variants_remembered` | Any game, the second start on | Start a game twice | The listed shaders are not built again (U3 waited ~2 s for them at every start) | `N numbers remembered from the last start` |
| `save_pictures` | Any game | Save (a checkpoint or the save list) | Pictures only for the campaign saves, none for the profile or system saves | `save picture written` lines name SAVEDATA0<game><digit> only |
| `crashes` | Everything above; Uncharted 2's end of Heart of Ice (the yeti at the lift) reported a crash | Play | No crash | every run's exit code and `Fault:` lines |

The launcher side (Uncharted 2 above 60 FPS shows a warning on Settings → PERFORMANCE, the Walk row on Settings →
CONTROLS) is covered by `python -m pytest tests`.
