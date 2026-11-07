#!/usr/bin/env bash
# Builds dist/Uncharted-windows/ and dist/Uncharted-windows.zip: a folder that runs on any Windows
# 10/11 x64 PC with a Vulkan GPU, without Python or MSYS2 installed.
#   Uncharted Launcher.exe   starter (tools/windows_starter) -> python\pythonw.exe launcher\...
#   python\                  Windows Python with Tkinter and Pillow (tools/copy_python.py)
#   launcher\ tools\         the launcher (Qt Quick, PySide6) and the start script (tools/probe_uncharted.py)
#   engine\                 run.py, scripts\ (game preparation), shaders\ (shader lists) and
#                            out\ (bb-probe.exe, the engine, with its DLLs)
# No game files ship: each player selects their own copy of the game in the launcher.
# Run after building the runtime (engine/build.sh), from Git Bash or an MSYS2 CLANG64 shell.
# PYTHON_HOME is a Windows Python 3.10+ with Pillow (default: the `python` on PATH).
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
# The Windows Python (looked up before the CLANG64 tools go first on PATH: MSYS2 has its own).
python=${PYTHON:-python}
python_home=${PYTHON_HOME:-$("$python" -c 'import sys, os; print(os.path.dirname(sys.executable))')}
msys=${MSYS2_ROOT:-/c/msys64}
# Inside the MSYS2 shell (GitHub Actions) its root is "/": without the slash, "$msys/usr" stays a
# local path ("//usr/..." is a network share, each try timed out after ~11 s).
msys=${msys%/}
[[ -d $msys/clang64/bin ]] && export PATH="$msys/clang64/bin:$PATH"
[[ -f engine/out/bb-probe.exe ]] || { echo 'Build the engine first: engine/build.sh' >&2; exit 1; }

stage=dist/stage/Uncharted-windows
rm -rf -- dist/stage
mkdir -p "$stage/engine/out" "$stage/engine/scripts" "$stage/tools" "$stage/launcher/assets" \
    "$stage/analysis/uncharted-user"

# The engine without debug information, and every DLL it loads from the CLANG64 tree.
for exe in bb-probe.exe bb-gpu-capabilities.exe; do
    llvm-strip --strip-debug -o "$stage/engine/out/$exe" "engine/out/$exe"
done
ldd engine/out/bb-probe.exe engine/out/bb-gpu-capabilities.exe | awk '/clang64/ {print $3}' | sort -u |
    while read -r dll; do
        cp "$dll" "$stage/engine/out/"
    done

# What run.py runs to prepare and start a game, and the shader lists of each release.
cp engine/run.py engine/LICENSE "$stage/engine/"
cp engine/scripts/prepare.py engine/scripts/link_modules.py engine/scripts/link_libc.py \
    engine/scripts/content_profile.py engine/scripts/trophies.py engine/scripts/isa_rewrite.py \
    engine/scripts/cheats.py engine/scripts/patches.py engine/scripts/mods.py "$stage/engine/scripts/"
cp -r engine/shaders "$stage/engine/"
cp tools/probe_uncharted.py tools/discord_presence.py tools/hang_report.py tools/apply_update.py tools/install_update.py \
    tools/check_game_files.py tools/game_files_102.json.gz \
    tools/game_update_view.py tools/arabic_language.py tools/text_languages.py tools/health_check.py "$stage/tools/"
# The health check, beside the launcher (tools/health_check.py: the install and the logs, as one page).
cp "tools/Check El Dorado.bat" "$stage/"
# PkgTool (LibOrbisPkg, LGPL-3.0): Advanced -> Install game update unpacks the player's own update PKG.
mkdir -p "$stage/tools/pkgtool"
cp tools/pkgtool/PkgTool.exe tools/pkgtool/LibOrbisPkg.dll "$stage/tools/pkgtool/"
# The launcher: launcher/main.py with core/ (logic) and ui/ (the Qt Quick window and El Dorado's art).
cp launcher/main.py "$stage/launcher/"
cp -r launcher/core launcher/ui "$stage/launcher/"
# The package's version (tools/VERSION; the launcher's updates compare it with the releases).
cp tools/VERSION "$stage/VERSION"
# El Dorado's own loading icons (tools/draw_loading_icons.py): each game's taskbar icon until the engine has taken
# the game's own from the player's first loading screen.
mkdir -p "$stage/launcher/assets/loading"
cp launcher/assets/loading/u1.png launcher/assets/loading/u2.png launcher/assets/loading/u3.png \
    "$stage/launcher/assets/loading/"
cp tools/README-Windows.txt "$stage/README.txt"
cp engine/LICENSE "$stage/LICENSE.txt"

# Licenses of the sources built into the runtime, and of every MSYS2 package whose DLL ships: its
# license files and, in THIRD-PARTY.txt, its version, license and source (some packages, FFmpeg
# among them, carry no license file).
licenses=$stage/licenses
mkdir -p "$licenses"
for dir in engine/gpu/third_party/* engine/third_party/*; do
    for file in "$dir"/LICENSE* "$dir"/COPYING* "$dir"/COPYRIGHT*; do
        [[ -f $file ]] || continue
        mkdir -p "$licenses/$(basename -- "$dir")"
        cp "$file" "$licenses/$(basename -- "$dir")/"
    done
done
head -n 24 engine/gpu/third_party/gcn/include/gcn/si_ci_vi_merged_offset.h > "$licenses/gcn-headers.txt"
mkdir -p "$licenses/liborbispkg"
cp tools/pkgtool/LICENSE.txt "$licenses/liborbispkg/LICENSE.txt"
echo "PkgTool and LibOrbisPkg 0.2.231 by Maxton, unchanged; source: https://github.com/maxton/LibOrbisPkg" \
    > "$licenses/liborbispkg/SOURCE.txt"
pacman=$(command -v pacman || echo "$msys/usr/bin/pacman")
# Three pacman calls in all (one per DLL took minutes on the CI runner).
dlls=()
for dll in "$stage"/engine/out/*.dll; do
    dlls+=("$(cygpath -m "$msys/clang64/bin/$(basename -- "$dll")")")
done
mapfile -t packages < <({ "$pacman" -Qqo "${dlls[@]}" 2>/dev/null || true; } | sort -u)
{ "$pacman" -Qlq "${packages[@]}" | grep '/share/licenses/.*[^/]$' || true; } | while read -r file; do
    name=${file#*/share/licenses/}
    mkdir -p "$licenses/msys2/$(dirname -- "$name")"
    cp "$msys$file" "$licenses/msys2/$name"
done
{
    echo "Third-party packages whose DLLs ship in engine\\out (MSYS2 CLANG64 builds)."
    echo "Their sources: https://repo.msys2.org/mingw/sources/ and https://packages.msys2.org/"
    "$pacman" -Qi "${packages[@]}" | awk '/^Name /{print ""} /^(Name|Version|Licenses|URL) /{print}'
} > "$licenses/THIRD-PARTY.txt"

# DLAA and FSR 4 Native AA (tools/fetch_aa_files.sh), when fetched: NVIDIA's DLSS DLL and the
# bridge under their own licenses, and the FSR 4 native model. Without them the menus leave the
# two out.
# The engine loads the bridge as bbport_dlss.dll (an older gow3_dlss.dll works under that name).
if [[ -f engine/out/gow3_dlss.dll && ! -f engine/out/bbport_dlss.dll ]]; then
    cp engine/out/gow3_dlss.dll engine/out/bbport_dlss.dll
fi
if [[ -f engine/out/bbport_dlss.dll && -f engine/out/nvngx_dlss.dll ]]; then
    cp engine/out/bbport_dlss.dll engine/out/nvngx_dlss.dll "$stage/engine/out/"
    mkdir -p "$licenses/nvidia-dlss" "$licenses/dlss-bridge"
    dlss_license=${NVIDIA_DLSS_LICENSE:-}
    if [[ -z $dlss_license ]]; then
        for file in downloads/dlss-sdk-*/LICENSE.txt; do
            [[ -f $file ]] && { dlss_license=$file; break; }
        done
    fi
    [[ -f $dlss_license ]] || { echo 'Need the DLSS license (NVIDIA_DLSS_LICENSE).' >&2; exit 1; }
    cp "$dlss_license" "$licenses/nvidia-dlss/LICENSE.txt"
    cp engine/gpu/dlss_bridge/LICENSE.txt "$licenses/dlss-bridge/LICENSE.txt"
fi
# Intel XeSS (engine/packaging/windows/fetch_xess.sh), when fetched.
if [[ -f engine/out/libxess.dll && -f engine/out/Intel-XeSS-LICENSE.txt ]]; then
    cp engine/out/libxess.dll "$stage/engine/out/"
    mkdir -p "$licenses/intel-xess"
    cp engine/out/Intel-XeSS-LICENSE.txt "$licenses/intel-xess/LICENSE.txt"
fi
if [[ -f engine/fsr4_shaders/fsr4_model_v07_i8_native_1080_pre.spv ]]; then
    mkdir -p "$stage/engine/fsr4_shaders" "$licenses/fsr4"
    cp engine/fsr4_shaders/LICENSE-FSR4-v07.txt engine/fsr4_shaders/*.spv engine/fsr4_shaders/*.bin \
        engine/fsr4_shaders/*.json "$stage/engine/fsr4_shaders/"
    cp engine/fsr4_shaders/LICENSE-FSR4-v07.txt "$licenses/fsr4/"
fi

"$python_home/python.exe" tools/copy_python.py "$python_home" "$stage/python"
# Qt for the launcher's window, trimmed to what it uses (tools/copy_pyside.py). PYSIDE_SITE holds PySide6
# Essentials: pip install --target downloads/pyside6 PySide6-Essentials
"$python_home/python.exe" tools/copy_pyside.py "${PYSIDE_SITE:-downloads/pyside6}" "$stage/python/Lib/site-packages"
# Python's own license is python\LICENSE.txt; Pillow's goes with the others.
for file in "$python_home"/Lib/site-packages/pillow-*.dist-info/licenses/* \
    "$python_home"/Lib/site-packages/pillow-*.dist-info/LICENSE*; do
    [[ -f $file ]] && { mkdir -p "$licenses/pillow"; cp "$file" "$licenses/pillow/"; }
done

windres tools/windows_starter/starter.rc -O coff -o dist/stage/starter.res.o
clang -O2 -municode -mwindows tools/windows_starter/starter.c dist/stage/starter.res.o \
    -o "$stage/Uncharted Launcher.exe"

find "$stage" -name __pycache__ -prune -exec rm -rf {} +
# Nothing from the game or a player (game executables, saves, shader caches, logs) may ship.
forbidden=$(find "$stage" \( -iname eboot.bin -o -iname '*.elf' -o -iname sce_sys -o -iname savedata \
    -o -iname cache -o -iname '*.log' -o -iname 'probe*.ini' -o -iname '*.pkg' -o -iname '*.psarc' \
    -o -iname '*.pak' -o -iname 'boot*.bin' \) -print)
if [[ -n $forbidden ]]; then
    echo "Package holds files that must not ship:" >&2
    echo "$forbidden" >&2
    exit 1
fi

rm -f dist/Uncharted-windows.zip
"$python_home/python.exe" -m zipfile -c dist/Uncharted-windows.zip "$stage"
rm -rf dist/Uncharted-windows
mv "$stage" dist/Uncharted-windows
du -sh dist/Uncharted-windows dist/Uncharted-windows.zip
