#!/usr/bin/env bash
# Copies this checkout's launcher, start script and built engine into a test install (a copy of a
# played install, whose analysis\ folder with the saves and settings is kept):
#   tools/make_test_install.sh ../test-install [../Launcher 2]
# The second folder is an installed package whose DLSS files (gow3_dlss.dll -> bbport_dlss.dll,
# nvngx_dlss.dll) and FSR 4 shaders are taken. Run from Git Bash or an MSYS2 shell after engine/build.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
dest=${1:?test install folder}
from=${2:-}
[[ -f engine/out/bb-probe.exe ]] || { echo 'Build the engine first: engine/build.sh' >&2; exit 1; }
mkdir -p "$dest/launcher/assets" "$dest/tools" "$dest/engine/out" "$dest/engine/scripts" "$dest/engine/shaders"
cp launcher/*.py launcher/*.pyw "$dest/launcher/"
cp -r launcher/assets/. "$dest/launcher/assets/"
cp tools/probe_uncharted.py tools/apply_update.py tools/install_update.py tools/hang_report.py "$dest/tools/" 2>/dev/null || true
cp tools/VERSION "$dest/tools/" 2>/dev/null || true
# The engine: the runtime, its DLLs (MSYS2 CLANG64's, found with ldd), the start script and the scripts it runs.
cp engine/out/bb-probe.exe engine/out/bb-gpu-capabilities.exe "$dest/engine/out/"
if command -v ldd >/dev/null; then
    ldd engine/out/bb-probe.exe | awk '/clang64/ {print $3}' | sort -u | while read -r dll; do
        cp "$dll" "$dest/engine/out/"
    done
fi
cp engine/run.py engine/LICENSE "$dest/engine/"
cp engine/scripts/prepare.py engine/scripts/link_modules.py engine/scripts/link_libc.py \
   engine/scripts/content_profile.py engine/scripts/trophies.py engine/scripts/isa_rewrite.py \
   engine/scripts/cheats.py engine/scripts/patches.py engine/scripts/mods.py "$dest/engine/scripts/"
cp -r engine/shaders/. "$dest/engine/shaders/"
# Upscaler files from the installed package (not in the repository).
if [[ -n $from ]]; then
    if [[ -f "$from/engine/out/gow3_dlss.dll" && -f "$from/engine/out/nvngx_dlss.dll" ]]; then
        cp "$from/engine/out/gow3_dlss.dll" "$dest/engine/out/bbport_dlss.dll"
        cp "$from/engine/out/nvngx_dlss.dll" "$dest/engine/out/"
        echo "DLSS: bbport_dlss.dll (ABI 1 bridge) and nvngx_dlss.dll"
    fi
    if [[ -d "$from/engine/fsr4_shaders" ]]; then
        mkdir -p "$dest/engine/fsr4_shaders"
        cp -r "$from/engine/fsr4_shaders/." "$dest/engine/fsr4_shaders/"
        echo "FSR 4: shaders"
    fi
fi
# The old engine's files stay in place (gow3-probe.exe and its scripts); nothing reads them any more.
echo "Test install ready: $dest"
