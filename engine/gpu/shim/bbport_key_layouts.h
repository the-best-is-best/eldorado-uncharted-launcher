// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// El Dorado: which keyboard's letters the key pictures show. Keys are bound by place (runtime_pad.c, the US-QWERTY
// names in input.ini); the pictures show English (US) letters, or, chosen on the in-game menu's Settings page, the
// letters one of the keyboard layouts installed in Windows prints on those keys. The choice is kept in
// BB_USER_DIR/key-labels.txt (the layout's language name, "en-US" for English).
#pragma once

#include <string>
#include <vector>

namespace BbKeyLayouts {

/// The choices: "English (US)" first, then each layout installed in Windows (its language's name).
const std::vector<std::string>& Names();
/// The one shown (an index into Names), 0 for English (US).
int Current();
/// Choose one (kept for the next starts); the key pictures are drawn again.
void Set(int index);
/// The chosen layout's letter on the key at this SDL scancode, in UTF-8 (upper case), or "" for English (US), a key
/// the layout prints nothing on, or a key that is not a character key.
std::string Letter(int sdl_scancode);

} // namespace BbKeyLayouts
