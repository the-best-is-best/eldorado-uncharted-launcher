#!/usr/bin/env bash
# Copyright (C) 2026 Michelle Raouf
# SPDX-License-Identifier: GPL-2.0-or-later
# The DLAA and FSR 4 files from an installed package (its engine\out DLLs, engine\fsr4_shaders and
# licenses\nvidia-dlss) instead of tools/fetch_aa_files.sh, for a PC without MSVC to build the DLSS
# bridge. tools/package_windows.sh then ships them as it does fetched ones.
# Usage: tools/copy_aa_files.sh <installed package folder>
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
from=${1:?Usage: tools/copy_aa_files.sh <installed package folder>}
[[ -d $from/engine/out ]] || { echo "No installed package in $from" >&2; exit 1; }

if [[ -f $from/engine/out/gow3_dlss.dll && -f $from/engine/out/nvngx_dlss.dll &&
      -f $from/licenses/nvidia-dlss/LICENSE.txt ]]; then
    mkdir -p engine/out downloads/dlss-sdk-installed
    # The engine loads bbport_dlss.dll (and accepts this older bridge by its Gow3DlssGetApi export).
    cp "$from/engine/out/gow3_dlss.dll" engine/out/bbport_dlss.dll
    cp "$from/engine/out/nvngx_dlss.dll" engine/out/
    # package_windows.sh finds NVIDIA's license under downloads/dlss-sdk-*.
    cp "$from/licenses/nvidia-dlss/LICENSE.txt" downloads/dlss-sdk-installed/LICENSE.txt
    echo "DLAA: the DLSS DLLs and NVIDIA's license from $from"
else
    echo "DLAA: not in $from (the package offers TAA and FSR 3.1)"
fi

if [[ -f $from/engine/fsr4_shaders/fsr4_model_v07_i8_native_1080_pre.spv ]]; then
    mkdir -p engine/fsr4_shaders
    cp -r "$from/engine/fsr4_shaders/." engine/fsr4_shaders/
    echo "FSR 4: the native model from $from"
else
    echo "FSR 4: not in $from"
fi
