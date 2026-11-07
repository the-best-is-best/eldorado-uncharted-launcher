// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: the screenshot key (F12, or input.ini key.screenshot= from BB_INPUT_CONFIG). A press asks the presenter for
// the next game frame at its full output size, before the overlay (menu, FPS counter, notices) is drawn over it; a
// worker thread writes it as <folder>/YYYYmmdd-HHMMSS.png (-2, -3 ... when taken) and prints
// "Screenshot: <full path>". The folder is BB_SCREENSHOT_DIR, else <BB_USER_DIR>/screenshots/<u1|u2|u3> by BB_EXE.

#pragma once

#include <cstdint>
#include <vector>

union SDL_Event;

namespace BbScreenshot {

/// Window thread, for every SDL event: true when it is the screenshot key (pressed or released), which then goes
/// nowhere else. A press (not a key repeat) asks for a screenshot.
bool HandleEvent(const SDL_Event& event);

/// Present thread: a screenshot was asked for and not taken yet.
bool Requested();
/// Present thread: the copy of a frame was started for it (the request is taken).
void Started();
/// Present thread: the copy could not be read: the next game frame is taken instead.
void Retry();
/// Present thread: the copied frame, `width` x `height` RGBA8 rows top to bottom; encoded and written on a worker
/// thread.
void Save(std::vector<unsigned char> rgba, uint32_t width, uint32_t height);
/// Present thread: no picture can be taken (logged once per request).
void Fail(const char* why);

} // namespace BbScreenshot
