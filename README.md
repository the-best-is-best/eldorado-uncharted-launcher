# El Dorado — Uncharted: The Nathan Drake Collection on PC

**El Dorado** plays the PS4 **Uncharted: The Nathan Drake Collection** (*Drake's Fortune*, *Among Thieves* and
*Drake's Deception*) natively on Windows. The games' own x86-64 code runs directly on the PC; a runtime supplies
the PS4 system libraries, and a Vulkan renderer executes the PS4 GPU work. On top of it sits a launcher made for
the series.

> **No game files are in this repository or its builds.** You need your own copy of the game.

## Highlights

- **One launcher for the three games**, in **22 languages** (Arabic first, right to left). Each game has its own
  color, Uncharted 1 jungle green, 2 ice blue, 3 desert orange, and the home screen shows where you left off,
  your play time, average FPS and trophy progress. Mouse, keyboard or controller.
- **It reads your copy:** the game languages your files hold (a fan translation is listed in the place of the
  language it replaced), the update beside the game folder, and which saves your game version can open.
- **Prepare shaders before you play** (Settings → GAME FILES): the first start of each game then opens straight
  away. The shader cache is kept when a game closes, the launcher's STOP included.
- **A fast engine** with DLSS, FSR 3.1, FSR 4, XeSS and frame generation, and a **Recommended** preset picked for
  your graphics card.
- **Straight to the main menu:** the title page is passed by itself; the loading and preparation screens wear
  the launcher's look.
- **El Dorado's in-game menu** (`Insert`, or `L3 + R3`) in your language, with an FPS / GPU / CPU / RAM / VRAM
  counter, checkpoints and save slots.
- **Key prompts that read as keys:** keyboard keys drawn in the game's colors, with English (US) letters or any
  keyboard layout installed in Windows (Insert → Key letters). Keys work by their place on the keyboard.
- **No lost progress by accident:** the close button and Alt+F4 ask first.
- **Saves:** a picture of the moment each save was made, a Saves page to delete and restore them, and a backup
  of every changed save before each start. **Players:** named profiles with their own saves.
- **Cheats for all three games:** infinite ammo and grenades, no reload, one hit kills, all treasures (once),
  every reward and chapter unlocked, and **Damage to Nate**, so that on any difficulty Nate takes damage as on
  Explorer, Easy, Normal or Hard while the enemies stay as chosen.
- **Mouse on mounted guns:** Uncharted 1's jeep gun and the turrets of all three games.
- **Trophies and Gallery** pages (F12 takes a full-size screenshot), Desktop shortcuts per game, Add to Steam.
- **Help when something goes wrong:** *Problem report* (Settings → LAUNCHER) puts the logs and settings in one
  zip on your Desktop, and **Check El Dorado.bat** checks the install and your last runs as one page.

## Requirements

Windows 10 or 11 (64-bit); a CPU from Intel's 4th-generation Core (2013) or newer, or any AMD Ryzen; a graphics
card or integrated GPU with **Vulkan 1.3** and a current driver; 16 GB of RAM recommended.

## Playing

1. Download **Uncharted-windows.zip** from the latest [release](../../releases) and extract it anywhere.
2. Start **Uncharted Launcher.exe** and select your game folder: the dumped game folder (the one holding
   `eboot.bin` and `sce_sys`).
3. Recommended: update **1.02**, extracted next to the game folder with `-patch` added to its name (for example
   `CUSA02320-patch`), or installed from its `.pkg` in Settings → GAME FILES. Most fixes and the cheats need it.
4. Optional: Settings → GAME FILES → **Prepare shaders**.
5. Pick a game and press **PLAY**.

Saves, logs and settings stay in the `analysis` folder next to the launcher. The launcher offers new releases
(betas included) as updates and keeps your saves and settings.

## Building

From an MSYS2 **CLANG64** shell:

```bash
pacman -S --needed git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross} \
  mingw-w64-clang-x86_64-{protobuf,openssl,zlib,miniupnpc,nlohmann-json}
git clone --recursive https://github.com/the-best-is-best/eldorado-uncharted-launcher.git
cd eldorado-uncharted-launcher
BB_PGO=use engine/build.sh      # the engine: engine/out/bb-probe.exe (profile-optimized)
tools/package_windows.sh         # dist/Uncharted-windows(.zip); needs a Windows Python 3.10+ with Pillow
                                 # (and iced-x86 for older Intel CPUs) and PySide6 in downloads/pyside6
```

The launcher is `launcher/` (Python with a Qt Quick window: `core/` for the logic, `ui/` for the screens); its
tests run with `python -m pytest tests`. Actions → Build Windows → Run workflow asks for the version (`X.Y.Z` or a
pre-release like `1.0.0-beta1`), builds the package on the self-hosted runner and publishes the release
([build-windows.yml](.github/workflows/build-windows.yml)).

## License

El Dorado is licensed under the GNU GPL v2 or later (see `engine/LICENSE`). It includes code from other
open-source projects, each under its own license: the copyright notices are kept in the source files and the
Windows package carries every bundled library's license in its `licenses` folder. NVIDIA, RTX and DLSS are
trademarks of NVIDIA Corporation; DLAA uses the NVIDIA DLSS SDK under NVIDIA's license.
