#!/usr/bin/env bash
# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
# The DLAA and FSR 4 files from an installed package (its gow3_pc\out DLLs, gow3_pc\fsr4_shaders and
# licenses\nvidia-dlss) instead of tools/fetch_aa_files.sh, for a PC without MSVC to build the DLSS
# bridge. tools/package_windows.sh then ships them as it does fetched ones.
# Usage: tools/copy_aa_files.sh <installed package folder>
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
from=${1:?Usage: tools/copy_aa_files.sh <installed package folder>}
[[ -d $from/gow3_pc/out ]] || { echo "No installed package in $from" >&2; exit 1; }

if [[ -f $from/gow3_pc/out/gow3_dlss.dll && -f $from/gow3_pc/out/nvngx_dlss.dll &&
      -f $from/licenses/nvidia-dlss/LICENSE.txt ]]; then
    mkdir -p gow3_pc/out downloads/dlss-sdk-installed
    # The engine loads bbport_dlss.dll (and accepts this older bridge by its Gow3DlssGetApi export).
    cp "$from/gow3_pc/out/gow3_dlss.dll" gow3_pc/out/bbport_dlss.dll
    cp "$from/gow3_pc/out/nvngx_dlss.dll" gow3_pc/out/
    # package_windows.sh finds NVIDIA's license under downloads/dlss-sdk-*.
    cp "$from/licenses/nvidia-dlss/LICENSE.txt" downloads/dlss-sdk-installed/LICENSE.txt
    echo "DLAA: the DLSS DLLs and NVIDIA's license from $from"
else
    echo "DLAA: not in $from (the package offers TAA and FSR 3.1)"
fi

if [[ -f $from/gow3_pc/fsr4_shaders/fsr4_model_v07_i8_native_1080_pre.spv ]]; then
    mkdir -p gow3_pc/fsr4_shaders
    cp -r "$from/gow3_pc/fsr4_shaders/." gow3_pc/fsr4_shaders/
    echo "FSR 4: the native model from $from"
else
    echo "FSR 4: not in $from"
fi
