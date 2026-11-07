# El Dorado — Uncharted: The Nathan Drake Collection on PC

**El Dorado** plays the PS4 **Uncharted: The Nathan Drake Collection** (CUSA02344: *Drake's Fortune*,
*Among Thieves* and *Drake's Deception*) natively on Windows. The games' own x86-64 code runs directly on
the PC; a runtime supplies the PS4 system libraries, and a Vulkan renderer executes the PS4 GPU work.

> **No game files are in this repository or its builds.** You need your own copy of the game.

## What El Dorado brings

- **A launcher made for the series:** dark leather, parchment and gold; each game over the picture of
  where you left off, your chapter, progress and play time, and a big PLAY. Keyboard, mouse or
  controller (D-pad, Cross, Circle, L1/R1), with the key hints of the device you use.
- **Saves page:** every save with its picture and chapter; delete (kept in `savedata-deleted`) and
  restore.
- **Every setting in the same window:** quick presets, display, upscaling (FSR 1, FSR 3.1, FSR 4,
  DLSS/DLAA), performance, controls (keyboard, mouse and controller actions), cheats, advanced.
- **In-game save list:** readable Arabic titles with chapter, play time and treasures; delete a save
  with Delete / Triangle; each save shows a picture of where it was made.
- **Mouse on the Uncharted 1 jeep gun**, and renderer and stability fixes.
- Desktop shortcuts per game with that game's icon, made from your own game files.

## Requirements

Windows 10 or 11 (64-bit); a CPU from Intel's 4th-generation Core (2013) or newer, or any AMD Ryzen;
a graphics card or integrated GPU with **Vulkan 1.3** and a current driver; 16 GB of RAM recommended.

## Playing

1. Download **Uncharted-windows.zip** from the latest [release](../../releases) and extract it anywhere.
2. Start **Uncharted Launcher.exe** and, on the first Play, select your game folder: the dumped
   `CUSA02344` folder (the one holding `eboot.bin` and `sce_sys`).
3. Recommended: update **1.02**, extracted next to the game folder with `-patch` added to its name (for
   example `CUSA02344-patch`).
4. Pick a game and press **PLAY**. The first start of each game prepares files and compiles shaders.

`Insert` or `LT + R3` opens the in-game menu. Saves, logs and settings stay in the `analysis` folder.
The launcher offers new releases as updates and keeps your saves and settings.

## Building

From an MSYS2 **CLANG64** shell:

```bash
pacman -S --needed git patch \
  mingw-w64-clang-x86_64-{toolchain,cmake,ninja,pkgconf,python} \
  mingw-w64-clang-x86_64-{vulkan-headers,vulkan-loader,vulkan-memory-allocator,glslang} \
  mingw-w64-clang-x86_64-{sdl3,fmt,boost,robin-map,xxhash,ffmpeg,zydis} \
  mingw-w64-clang-x86_64-{spirv-tools,spirv-headers,spirv-cross} \n  mingw-w64-clang-x86_64-{protobuf,openssl,zlib,miniupnpc,nlohmann-json}
git clone --recursive https://github.com/the-best-is-best/eldorado-uncharted-launcher.git
cd eldorado-uncharted-launcher
BB_PGO=use engine/build.sh      # the engine: engine/out/bb-probe.exe (profile-optimized)
tools/package_windows.sh         # dist/Uncharted-windows(.zip); needs a Windows Python 3.10+ with Pillow
                                 # (and iced-x86 for older Intel CPUs)
```

Actions → Build Windows → Run workflow asks for the version (X.Y.Z), builds the package
on the self-hosted runner and publishes the release ([build-windows.yml](.github/workflows/build-windows.yml)).

## License

El Dorado is licensed under the GNU GPL v2 or later (see `engine/LICENSE`). It includes code from other
open-source projects, each under its own license: the copyright notices are kept in the source files and
the Windows package carries every bundled library's license in its `licenses` folder. NVIDIA, RTX and DLSS
are trademarks of NVIDIA Corporation; DLAA uses the NVIDIA DLSS SDK under NVIDIA's license.
