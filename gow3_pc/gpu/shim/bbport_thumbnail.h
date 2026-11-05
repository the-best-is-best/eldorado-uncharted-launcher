// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: a small picture of the game for the save list and the launcher. The presenter scales a game frame down
// about once a second while the game plays (not in the pause menu or a cutscene), before the overlay is drawn; a
// save then gets the last one as <dir>.sce_sys/thumb.png (runtime_savedata.c save_umount). BB_SAVE_PICTURE=0 turns
// it off.

#pragma once

#include <cstdint>

namespace BbThumbnail {

constexpr uint32_t Width = 960, Height = 540; // sharp enough for the launcher's background

/// Present thread: whether to capture this frame (a second since the last request, and the game in play in
/// between, runtime_play_calls).
bool Wanted();
/// Present thread: the captured picture, Width x Height RGBA8 rows top to bottom.
void Store(const unsigned char* rgba);
/// The game's save list ("Save game") was shown: the next save written within two minutes gets the picture from
/// before the pause menu (bbgpu_thumbnail_pause).
void NoteSaveList();

} // namespace BbThumbnail
