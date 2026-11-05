#!/usr/bin/env bash
# Copies this checkout's launcher, start script and built engine into a test install (a copy of a
# played install, whose analysis\ folder with the saves and settings is kept):
#   tools/make_test_install.sh ../test-install [../Launcher 2]
# The second folder is an installed package whose DLSS files (gow3_dlss.dll -> bbport_dlss.dll,
# nvngx_dlss.dll) and FSR 4 shaders are taken. Run from Git Bash or an MSYS2 shell after gow3_pc/build.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
dest=${1:?test install folder}
from=${2:-}
[[ -f gow3_pc/out/bb-probe.exe ]] || { echo 'Build the engine first: gow3_pc/build.sh' >&2; exit 1; }
mkdir -p "$dest/launcher/assets" "$dest/tools" "$dest/gow3_pc/out" "$dest/gow3_pc/scripts" "$dest/gow3_pc/shaders"
cp launcher/*.py launcher/*.pyw "$dest/launcher/"
cp -r launcher/assets/. "$dest/launcher/assets/"
cp tools/probe_uncharted.py tools/apply_update.py tools/install_update.py tools/hang_report.py "$dest/tools/" 2>/dev/null || true
cp tools/VERSION "$dest/tools/" 2>/dev/null || true
# The engine: the runtime, its DLLs (MSYS2 CLANG64's, found with ldd), the start script and the scripts it runs.
cp gow3_pc/out/bb-probe.exe gow3_pc/out/bb-gpu-capabilities.exe "$dest/gow3_pc/out/"
if command -v ldd >/dev/null; then
    ldd gow3_pc/out/bb-probe.exe | awk '/clang64/ {print $3}' | sort -u | while read -r dll; do
        cp "$dll" "$dest/gow3_pc/out/"
    done
fi
cp gow3_pc/run.py gow3_pc/LICENSE "$dest/gow3_pc/"
cp gow3_pc/scripts/prepare.py gow3_pc/scripts/link_modules.py gow3_pc/scripts/link_libc.py \
   gow3_pc/scripts/content_profile.py gow3_pc/scripts/trophies.py gow3_pc/scripts/isa_rewrite.py \
   gow3_pc/scripts/cheats.py gow3_pc/scripts/patches.py gow3_pc/scripts/mods.py "$dest/gow3_pc/scripts/"
cp -r gow3_pc/shaders/. "$dest/gow3_pc/shaders/"
# Upscaler files from the installed package (not in the repository).
if [[ -n $from ]]; then
    if [[ -f "$from/gow3_pc/out/gow3_dlss.dll" && -f "$from/gow3_pc/out/nvngx_dlss.dll" ]]; then
        cp "$from/gow3_pc/out/gow3_dlss.dll" "$dest/gow3_pc/out/bbport_dlss.dll"
        cp "$from/gow3_pc/out/nvngx_dlss.dll" "$dest/gow3_pc/out/"
        echo "DLSS: bbport_dlss.dll (ABI 1 bridge) and nvngx_dlss.dll"
    fi
    if [[ -d "$from/gow3_pc/fsr4_shaders" ]]; then
        mkdir -p "$dest/gow3_pc/fsr4_shaders"
        cp -r "$from/gow3_pc/fsr4_shaders/." "$dest/gow3_pc/fsr4_shaders/"
        echo "FSR 4: shaders"
    fi
fi
# The old engine's files stay in place (gow3-probe.exe and its scripts); nothing reads them any more.
echo "Test install ready: $dest"
