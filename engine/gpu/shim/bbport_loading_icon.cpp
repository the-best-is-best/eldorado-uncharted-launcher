// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
#include "bbport_loading_icon.h"
#include "bbport_thumbnail.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <sys/stat.h>
#include <vector>

#include <miniz.h>

extern "C" int runtime_file_replace(const char* source, const char* target); // runtime_file.c

namespace BbLoadingIcon {
namespace {

using Clock = std::chrono::steady_clock;
using BbThumbnail::Height;
using BbThumbnail::Width;

// The corner the icon is drawn in (a share of the frame) and what counts as black around it.
constexpr unsigned CornerLeft = Width * 70 / 100, CornerTop = Height * 55 / 100;
constexpr int Dark = 24;   // brightest channel at most this: black
constexpr int Bright = 60; // brightest channel at least this: part of the icon
constexpr int Steady = 6;  // looks in a row (1.5 s) that show a loading screen before the icon is kept

std::atomic<bool> done{false}, fresh{false};
Clock::time_point last_look{};
int streak = 0;
std::vector<unsigned char> best; // RGBA, best_size x best_size: the widest view of the icon so far (it turns)
unsigned best_size = 0, best_area = 0;

int Peak(const unsigned char* p) {
    return std::max({p[0], p[1], p[2]});
}

bool WritePng(const std::string& path, const std::vector<unsigned char>& rgba, unsigned size) {
    size_t bytes = 0;
    void* png = tdefl_write_image_to_png_file_in_memory_ex(rgba.data(), int(size), int(size), 4, &bytes, 6,
                                                           MZ_FALSE);
    if (!png) {
        return false;
    }
    const std::string temp = path + ".bbtmp";
    FILE* f = std::fopen(temp.c_str(), "wb");
    bool ok = f && std::fwrite(png, 1, bytes, f) == bytes;
    if (f) {
        ok = std::fclose(f) == 0 && ok;
    }
    mz_free(png);
    ok = ok && runtime_file_replace(temp.c_str(), path.c_str()) == 0;
    if (!ok) {
        std::remove(temp.c_str());
    }
    return ok;
}

} // namespace

const char* Path() {
    const char* path = std::getenv("BB_LOADING_ICON");
    return path && path[0] ? path : nullptr;
}

bool Wanted() {
    if (done.load(std::memory_order_relaxed)) {
        return false;
    }
    static const bool wanted = [] {
        struct stat info {};
        return Path() && stat(Path(), &info) != 0; // made once; delete the file to take it again
    }();
    if (!wanted) {
        done = true;
        return false;
    }
    const auto now = Clock::now();
    if (now - last_look < std::chrono::milliseconds(250)) {
        return false;
    }
    last_look = now;
    return true;
}

void Look(const unsigned char* rgba) {
    if (done.load(std::memory_order_relaxed)) {
        return;
    }
    // A loading screen: black everywhere but a small bright shape well inside the lower right corner.
    unsigned lit_outside = 0, seen_outside = 0;
    unsigned x0 = Width, y0 = Height, x1 = 0, y1 = 0, lit = 0;
    for (unsigned y = 0; y < Height; ++y) {
        for (unsigned x = 0; x < Width; ++x) {
            const unsigned char* p = rgba + (size_t(y) * Width + x) * 4;
            const bool corner = x >= CornerLeft && y >= CornerTop;
            if (!corner) {
                if ((x + y) % 5 == 0) {
                    ++seen_outside;
                    lit_outside += Peak(p) > Dark;
                }
            } else if (Peak(p) >= Bright) {
                ++lit;
                x0 = std::min(x0, x), y0 = std::min(y0, y), x1 = std::max(x1, x), y1 = std::max(y1, y);
            }
        }
    }
    // A dark screen: one line every 2 s at most, to see why a loading screen was not taken.
    static Clock::time_point last_note{};
    if (seen_outside && lit_outside * 100 <= seen_outside && Clock::now() - last_note > std::chrono::seconds(2)) {
        last_note = Clock::now();
        std::printf("Loading icon: dark screen, %.2f%% lit outside the corner, %u lit in it (%u,%u)-(%u,%u)\n",
                    100.0 * lit_outside / seen_outside, lit, x0, y0, x1, y1);
        std::fflush(stdout);
    }
    const bool loading = seen_outside && lit_outside * 1000 <= seen_outside * 3 && lit >= 120 && lit <= 20000 &&
                         x0 > CornerLeft + 2 && y0 > CornerTop + 2 && x1 < Width - 2 && y1 < Height - 2;
    if (!loading) {
        streak = 0;
        best.clear();
        best_size = best_area = 0;
        return;
    }
    const unsigned area = (x1 - x0 + 1) * (y1 - y0 + 1);
    if (area > best_area) {
        // A square around the shape, black made transparent (the glow fades out instead of ending in a box).
        const unsigned margin = 3, side = std::max(x1 - x0, y1 - y0) + 1 + 2 * margin;
        const int left = int((x0 + x1) / 2) - int(side / 2), top = int((y0 + y1) / 2) - int(side / 2);
        best.assign(size_t(side) * side * 4, 0);
        for (unsigned y = 0; y < side; ++y) {
            for (unsigned x = 0; x < side; ++x) {
                const int sx = left + int(x), sy = top + int(y);
                if (sx < 0 || sy < 0 || sx >= int(Width) || sy >= int(Height)) {
                    continue;
                }
                const unsigned char* p = rgba + (size_t(sy) * Width + sx) * 4;
                unsigned char* q = best.data() + (size_t(y) * side + x) * 4;
                const int peak = Peak(p);
                q[0] = p[0], q[1] = p[1], q[2] = p[2];
                q[3] = static_cast<unsigned char>(std::clamp((peak - Dark / 2) * 4, 0, 255));
            }
        }
        best_size = side;
        best_area = area;
    }
    if (++streak < Steady) {
        return;
    }
    done = true;
    const char* path = Path();
    if (path && WritePng(path, best, best_size)) {
        std::printf("Loading icon: taken from the loading screen (%ux%u), %s\n", best_size, best_size, path);
        fresh = true;
    } else {
        std::printf("Loading icon: not written\n");
    }
    std::fflush(stdout);
}

bool TakeNew() {
    return fresh.exchange(false, std::memory_order_acq_rel);
}

} // namespace BbLoadingIcon
