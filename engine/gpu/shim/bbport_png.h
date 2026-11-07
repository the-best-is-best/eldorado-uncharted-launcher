// SPDX-License-Identifier: GPL-2.0-or-later
// bbport: PNG pictures for the overlay (the save list's icon0.png and thumb.png), decoded by FFmpeg to RGBA8.
// The small decoder in bbport_overlay.cpp (DecodePng) stays for the trophy notices: it takes 8-bit pictures up to
// 256 px only; these can be any PNG.

#pragma once

#include <cstddef>
#include <vector>

namespace BbPng {

struct Image {
    int width = 0, height = 0;
    std::vector<unsigned char> rgba; // width * height * 4, rows top to bottom
};

/// False (and `out` empty) when the data is not a PNG FFmpeg can decode. With max_width and max_height a larger
/// picture is scaled down to fit them, keeping its proportions (the save list draws 228x128, at most twice that).
bool DecodeRgba(const unsigned char* data, size_t size, Image& out, int max_width = 0, int max_height = 0);
/// Reads the file and decodes it; false when it is missing or bad.
bool LoadRgba(const char* path, Image& out, int max_width = 0, int max_height = 0);

} // namespace BbPng
