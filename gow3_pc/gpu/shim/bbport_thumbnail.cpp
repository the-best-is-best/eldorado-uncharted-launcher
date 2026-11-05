// SPDX-License-Identifier: GPL-2.0-or-later
#include "bbport_thumbnail.h"
#include "../bbgpu.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <miniz.h>

extern "C" {
// runtime_file.c: a whole file replaced in one rename (the launcher reads thumb.png while the game runs).
int runtime_file_replace(const char* source, const char* target);
// runtime_pad.c (runtime.h): advances with every call of the camera hooks, i.e. while the game is in play.
extern volatile unsigned runtime_play_calls;
}

namespace BbThumbnail {
namespace {

using Clock = std::chrono::steady_clock;

// The presenter's capture (vk_presenter.cpp, a scaled copy of the game frame into Store) and the runtime's "game in
// play" counter (runtime_pad.c, the camera hooks) are in: a save written while the game is not in play waits for the
// next picture (bbgpu_thumbnail_save returns 2).
constexpr bool CaptureAvailable = true;

std::mutex mutex;
std::vector<unsigned char> picture; // RGB8, Width x Height; empty: none yet
Clock::time_point picture_at{};     // when it was captured
Clock::time_point last_request{}, playing_since{};
unsigned last_calls = 0;
// Saves written while the game was not in play (a chapter's first autosave comes after its cutscene or loading,
// when the last picture still shows the end of the chapter before): they get the first picture taken once play
// has gone on for a while.
struct Pending {
    std::string path;
    Clock::time_point since;
};
std::vector<Pending> pending;
// A save loaded that has no picture yet (made before pictures, or by another build): it gets the first picture
// once play has settled after the load, which shows where that save starts. Only the last one read counts (the
// game reads other saves while its menus list them).
std::string loaded_path;
Clock::time_point loaded_since{};
// The camera hooks keep running behind the pause menu, so pictures go on being taken there. A save made from the
// save list (opened from that menu) gets the picture from the moment Options was last pressed instead, before the
// menu was on screen.
std::vector<unsigned char> before_pause;
Clock::time_point before_pause_at{};
Clock::time_point save_list_at{}, save_list_used{};

constexpr auto Fresh = std::chrono::seconds(3);   // a picture this recent shows the save's place
constexpr auto Settled = std::chrono::seconds(2); // play this long after a break (fade-in over)
constexpr auto GiveUp = std::chrono::minutes(10); // a waiting save keeps the game's picture

// BB_SAVE_PICTURE=0: saves keep the game's own picture.
bool Enabled() {
    static const bool enabled = [] {
        const char* env = std::getenv("BB_SAVE_PICTURE");
        return !(env && env[0] == '0');
    }();
    return CaptureAvailable && enabled;
}

// The game in play: the runtime's camera hooks ran since the last look (a counter that advances with every call).
unsigned InPlayCalls() {
    return __atomic_load_n(&runtime_play_calls, __ATOMIC_RELAXED);
}

// Written beside the file and renamed over it: the launcher, which reads thumb.png while the game runs, never sees
// a half-written picture, and a failure leaves the old one.
bool WritePng(const std::string& path, const std::vector<unsigned char>& rgb) {
    size_t size = 0;
    void* png = tdefl_write_image_to_png_file_in_memory_ex(rgb.data(), int(Width), int(Height), 3, &size, 3,
                                                           MZ_FALSE);
    if (!png) {
        return false;
    }
    const std::string temp = path + ".bbtmp";
    FILE* f = std::fopen(temp.c_str(), "wb");
    bool ok = f && std::fwrite(png, 1, size, f) == size;
    if (f) {
        ok = std::fclose(f) == 0 && ok;
    }
    mz_free(png);
    if (ok) {
        ok = runtime_file_replace(temp.c_str(), path.c_str()) == 0;
    }
    if (!ok) {
        std::remove(temp.c_str());
    }
    return ok;
}

} // namespace

bool Wanted() {
    if (!Enabled()) {
        return false;
    }
    const auto now = Clock::now();
    if (now - last_request < std::chrono::seconds(1)) {
        return false;
    }
    const unsigned calls = InPlayCalls();
    if (calls == last_calls) {
        return false;
    }
    last_calls = calls;
    // A gap since the last request: play (the camera hooks) has just started again.
    if (now - last_request > std::chrono::seconds(2)) {
        std::scoped_lock lock{mutex};
        playing_since = now;
    }
    last_request = now;
    return true;
}

void Store(const unsigned char* rgba) {
    LoadingProbe(rgba);
    std::vector<unsigned char> rgb(size_t(Width) * Height * 3);
    for (size_t i = 0, n = size_t(Width) * Height; i < n; ++i) {
        rgb[i * 3 + 0] = rgba[i * 4 + 0];
        rgb[i * 3 + 1] = rgba[i * 4 + 1];
        rgb[i * 3 + 2] = rgba[i * 4 + 2];
    }
    // A black or nearly black frame (a fade after a skipped cutscene, a loading screen) is no picture of the
    // save's place: it is dropped, and a save made now waits for the next one.
    {
        uint64_t sum = 0;
        size_t samples = 0;
        for (size_t i = 0; i < rgb.size(); i += 3 * 97) {
            sum += rgb[i] + rgb[i + 1] + rgb[i + 2];
            ++samples;
        }
        if (samples && sum / (samples * 3) < 10) {
            return;
        }
    }
    // A still frame is not play: behind the pause menu the cameras keep running while the scene stands
    // frozen (a save picture showed the pause menu, 5 Nov 2026). A picture is kept only when the scene
    // moved both into it and out of it (the one before and the one after differ from it), so the last
    // picture before the menu counts and the menu's do not; it is kept one picture (about a second) late.
    static std::vector<unsigned char> before, middle;
    const auto moved = [](const std::vector<unsigned char>& a, const std::vector<unsigned char>& b) {
        size_t changed = 0, samples = 0;
        for (size_t i = 0; i + 2 < a.size() && i + 2 < b.size(); i += 3 * 97) {
            const int d = std::max({std::abs(a[i] - b[i]), std::abs(a[i + 1] - b[i + 1]), std::abs(a[i + 2] - b[i + 2])});
            changed += d > 6;
            ++samples;
        }
        return samples && changed * 1000 > samples;
    };
    const bool keep = !before.empty() && !middle.empty() && moved(before, middle) && moved(middle, rgb);
    before = std::move(middle);
    middle = rgb;
    if (!keep) {
        return;
    }
    rgb = before; // the middle picture (just moved to `before`)
    const auto now = Clock::now();
    std::vector<std::string> due;
    {
        std::scoped_lock lock{mutex};
        picture = rgb;
        picture_at = now;
        if (!pending.empty() && now - playing_since >= Settled) {
            for (const Pending& p : pending) {
                if (now - p.since < GiveUp) {
                    due.push_back(p.path);
                }
            }
            pending.clear();
        }
        if (!loaded_path.empty() && playing_since > loaded_since && now - playing_since >= Settled) {
            if (now - loaded_since < GiveUp) {
                due.push_back(loaded_path);
            }
            loaded_path.clear();
        }
    }
    if (due.empty()) {
        return;
    }
    // Off the present thread: encoding takes a few milliseconds.
    std::thread([due = std::move(due), rgb = std::move(rgb)] {
        for (const std::string& path : due) {
            if (WritePng(path, rgb)) {
                std::printf("GPU: save picture written once play went on (%s)\n", path.c_str());
            }
        }
    }).detach();
}

namespace {
std::atomic<bool> loading_done{false};
std::atomic<int> loading_lit{0};
Clock::time_point loading_since = Clock::now(), loading_probe_at{};
} // namespace

bool Loading() {
    if (loading_done.load(std::memory_order_relaxed)) {
        return false;
    }
    static const bool on = [] {
        const char* env = std::getenv("BB_LOADING_SCREEN");
        return !(env && env[0] == '0');
    }();
    if (!on || Clock::now() - loading_since > std::chrono::minutes(2)) {
        loading_done = true;
        return false;
    }
    return true;
}

bool LoadingProbeWanted() {
    if (!Loading()) {
        return false;
    }
    const auto now = Clock::now();
    if (now - loading_probe_at < std::chrono::milliseconds(250)) {
        return false;
    }
    loading_probe_at = now;
    return true;
}

void LoadingProbe(const unsigned char* rgba) {
    if (loading_done.load(std::memory_order_relaxed)) {
        return;
    }
    uint64_t sum = 0;
    size_t samples = 0;
    for (size_t i = 0, n = size_t(Width) * Height; i < n; i += 61) {
        sum += rgba[i * 4] + rgba[i * 4 + 1] + rgba[i * 4 + 2];
        ++samples;
    }
    const bool lit = samples && sum / (samples * 3) >= 14;
    if (!lit) {
        loading_lit = 0;
    } else if (++loading_lit >= 2) {
        loading_done = true;
        std::printf("Loading screen: the game shows its first picture after %.1f s\n",
                    std::chrono::duration<double>(Clock::now() - loading_since).count());
    }
}

void NoteSaveList() {
    std::scoped_lock lock{mutex};
    save_list_at = Clock::now();
    save_list_used = {};
}

} // namespace BbThumbnail

extern "C" int bbgpu_thumbnail_save(const char* path) {
    using namespace BbThumbnail;
    if (!path || !*path || !Enabled()) {
        return 0;
    }
    std::vector<unsigned char> rgb;
    {
        std::scoped_lock lock{mutex};
        const auto now = Clock::now();
        // The saves written right after the save list (the chosen one and the profile save around it, within 10 s
        // of the first) get the picture from before the menu; a checkpoint save later in play gets its own.
        bool from_list = false;
        const bool list_recent = save_list_at != Clock::time_point{} && now - save_list_at < std::chrono::minutes(2);
        // The picture from before the pause menu counts only when Options was pressed shortly before that list
        // (a New Game's slot list comes from the main menu: no pause, and the menu scene is not the save's place).
        const bool pause_fits = !before_pause.empty() && before_pause_at <= save_list_at &&
                                save_list_at - before_pause_at < std::chrono::minutes(2);
        bool in_window = false;
        if (list_recent) {
            if (save_list_used == Clock::time_point{}) {
                save_list_used = now;
            }
            in_window = now - save_list_used <= std::chrono::seconds(10);
        }
        if (!in_window) {
            save_list_at = {};
            save_list_used = {};
        }
        from_list = in_window && pause_fits;
        if (from_list) {
            rgb = before_pause;
        } else if (in_window || picture.empty() || now - picture_at > Fresh || now - playing_since < Settled) {
            // Not in play now: the save waits for the next picture (one entry per save).
            std::erase_if(pending, [&](const Pending& p) { return p.path == path; });
            if (pending.size() < 16) {
                pending.push_back({path, now});
            }
            return 2;
        } else {
            rgb = picture;
        }
    }
    return WritePng(path, rgb) ? 1 : 0;
}

// The game is closing: saves still waiting for a picture of play get the last one there is (closed before play went
// on, a save had no picture at all, 5 Nov 2026).
extern "C" void bbgpu_thumbnail_flush(void) {
    using namespace BbThumbnail;
    std::vector<std::string> paths;
    std::vector<unsigned char> rgb;
    {
        std::scoped_lock lock{mutex};
        if (picture.empty()) {
            return;
        }
        rgb = picture;
        for (const Pending& p : pending) {
            paths.push_back(p.path);
        }
        pending.clear();
    }
    for (const std::string& path : paths) {
        if (WritePng(path, rgb)) {
            std::printf("GPU: save picture written at exit (%s)\n", path.c_str());
        }
    }
}

extern "C" void bbgpu_thumbnail_loaded(const char* path) {
    using namespace BbThumbnail;
    if (!path || !*path || !Enabled()) {
        return;
    }
    std::scoped_lock lock{mutex};
    loaded_path = path;
    loaded_since = Clock::now();
}

extern "C" void bbgpu_thumbnail_pause(void) {
    using namespace BbThumbnail;
    std::scoped_lock lock{mutex};
    before_pause = picture;
    before_pause_at = Clock::now();
}
