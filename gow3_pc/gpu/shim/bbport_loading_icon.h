// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// El Dorado: each game's own loading icon (Uncharted 1's coin, 2's phurba, 3's ring) on its window and taskbar
// button. The games draw it alone in the lower right corner of a black screen while they load; the first time
// a game shows it, the presenter's small copies of the frame (bbport_thumbnail) are looked at, the icon is cut
// out (black made transparent) and written to BB_LOADING_ICON (a PNG per game, made by the start script's
// environment). Later starts put that file on the window at once (window.cpp). Nothing of the game is shipped:
// the picture is taken from the player's own game.

#pragma once

namespace BbLoadingIcon {

/// Present thread: whether to look at this frame (no icon written yet, a look every 250 ms).
bool Wanted();
/// Present thread: the look (BbThumbnail::Width x Height RGBA8, rows top to bottom).
void Look(const unsigned char* rgba);
/// Window thread: true once after a new icon was written (the window then loads it).
bool TakeNew();
/// The icon file (BB_LOADING_ICON), or nullptr.
const char* Path();

} // namespace BbLoadingIcon
