// SPDX-License-Identifier: GPL-2.0-or-later
#include "bbport_screenshot.h"
#include "bbport_overlay.h"

#include <atomic>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <mutex>
#include <string>
#include <system_error>
#include <thread>
#include <utility>

#include <SDL3/SDL.h>
#include <miniz.h>

namespace BbScreenshot {
namespace {

std::atomic<bool> requested{false};
std::atomic<long long> requested_at{0}; // time() of the press: the file's name
std::atomic<bool> failed_noted{false};
std::mutex name_mutex; // picking a free name and renaming onto it

// The keys (SDL scancodes; up to two, "F12|Print Screen"), read from input.ini once on the window thread.
SDL_Scancode keys[2] = {SDL_SCANCODE_UNKNOWN, SDL_SCANCODE_UNKNOWN};
bool keys_loaded = false;

SDL_Scancode ParseKey(std::string name) {
    while (!name.empty() && std::isspace(static_cast<unsigned char>(name.back()))) name.pop_back();
    while (!name.empty() && std::isspace(static_cast<unsigned char>(name.front()))) name.erase(0, 1);
    if (name.empty() || !SDL_strcasecmp(name.c_str(), "none")) {
        return SDL_SCANCODE_UNKNOWN;
    }
    return SDL_GetScancodeFromName(name.c_str());
}

void LoadKeys() {
    keys_loaded = true;
    std::string value = "F12";
    bool configured = false;
    const char* path = std::getenv("BB_INPUT_CONFIG");
    FILE* f = path && *path ? std::fopen(path, "r") : nullptr;
    char line[256];
    while (f && std::fgets(line, sizeof(line), f)) {
        line[std::strcspn(line, "\r\n")] = 0;
        if (!std::strncmp(line, "key.screenshot=", 15)) {
            value = line + 15;
            configured = true;
        }
    }
    if (f) {
        std::fclose(f);
    }
    const size_t bar = value.find('|');
    keys[0] = ParseKey(value.substr(0, bar));
    keys[1] = bar == std::string::npos ? SDL_SCANCODE_UNKNOWN : ParseKey(value.substr(bar + 1));
    if (keys[1] == keys[0]) {
        keys[1] = SDL_SCANCODE_UNKNOWN;
    }
    if (keys[0] == SDL_SCANCODE_UNKNOWN && keys[1] != SDL_SCANCODE_UNKNOWN) {
        std::swap(keys[0], keys[1]);
    }
    if (keys[0] == SDL_SCANCODE_UNKNOWN) {
        std::printf("Screenshot key: none (key.screenshot=%s in input.ini)\n", value.c_str());
    } else {
        std::printf("Screenshot key: %s%s%s%s\n", SDL_GetScancodeName(keys[0]),
                    keys[1] != SDL_SCANCODE_UNKNOWN ? " or " : "",
                    keys[1] != SDL_SCANCODE_UNKNOWN ? SDL_GetScancodeName(keys[1]) : "",
                    configured ? " (input.ini)" : "");
    }
    std::fflush(stdout);
}

// u1 / u2 / u3 by the executable the runtime runs (BB_EXE, as runtime_user_id in runtime_pad.c reads it).
const char* GameKey() {
    const char* exe = std::getenv("BB_EXE");
    if (!exe || !*exe) {
        return "game";
    }
    std::string name = exe;
    const size_t slash = name.find_last_of("/\\");
    if (slash != std::string::npos) {
        name.erase(0, slash + 1);
    }
    for (char& c : name) {
        c = char(std::tolower(static_cast<unsigned char>(c)));
    }
    if (name.find("big3") != std::string::npos) return "u3";
    if (name.find("big2") != std::string::npos) return "u2";
    if (name.find("eboot") != std::string::npos) return "u1";
    return "game";
}

// The folder as the environment names it, with the separator it already uses.
std::string Folder() {
    const char* dir = std::getenv("BB_SCREENSHOT_DIR");
    std::string folder;
    if (dir && *dir) {
        folder = dir;
    } else {
        const char* user = std::getenv("BB_USER_DIR");
        folder = user && *user ? user : "user";
        const char sep = folder.find('\\') != std::string::npos ? '\\' : '/';
        if (folder.back() != '/' && folder.back() != '\\') {
            folder += sep;
        }
        folder += "screenshots";
        folder += sep;
        folder += GameKey();
    }
    while (folder.size() > 1 && (folder.back() == '/' || folder.back() == '\\') &&
           !(folder.size() == 3 && folder[1] == ':')) {
        folder.pop_back();
    }
    return folder;
}

// The process's code page is UTF-8 (packaging/windows/bb-probe.manifest): the paths are UTF-8 bytes.
std::filesystem::path FsPath(const std::string& utf8) {
    return std::filesystem::path(std::u8string(reinterpret_cast<const char8_t*>(utf8.data()), utf8.size()));
}

void Write(std::vector<unsigned char> rgba, uint32_t width, uint32_t height, long long when) {
    // RGB: the frame's alpha is not a picture's transparency.
    const size_t pixels = size_t(width) * height;
    for (size_t i = 0; i < pixels; ++i) {
        rgba[i * 3 + 0] = rgba[i * 4 + 0];
        rgba[i * 3 + 1] = rgba[i * 4 + 1];
        rgba[i * 3 + 2] = rgba[i * 4 + 2];
    }
    size_t size = 0;
    void* png = tdefl_write_image_to_png_file_in_memory_ex(rgba.data(), int(width), int(height), 3, &size, 3,
                                                           MZ_FALSE);
    rgba = {};
    if (!png) {
        std::printf("Screenshot failed: the picture could not be encoded\n");
        std::fflush(stdout);
        return;
    }
    const std::string folder = Folder();
    const char sep = folder.find('\\') != std::string::npos && folder.find('/') == std::string::npos ? '\\' : '/';
    std::error_code ec;
    std::filesystem::create_directories(FsPath(folder), ec);

    const std::time_t t = std::time_t(when);
    std::tm local{};
#ifdef _WIN32
    localtime_s(&local, &t);
#else
    localtime_r(&t, &local);
#endif
    char stamp[32];
    std::strftime(stamp, sizeof(stamp), "%Y%m%d-%H%M%S", &local);
    const bool has_sep = folder.back() == '/' || folder.back() == '\\';
    const std::string base = has_sep ? folder + stamp : folder + sep + stamp;

    // Written beside its name and renamed onto it (a rename that never replaces): whoever watches the folder never
    // sees a half-written picture, and two pictures in one second get -2, -3 ...
    const std::string temp = base + ".png.bbtmp";
    FILE* f = std::fopen(temp.c_str(), "wb");
    bool ok = f && std::fwrite(png, 1, size, f) == size;
    if (f) {
        ok = std::fclose(f) == 0 && ok;
    }
    mz_free(png);
    std::string path;
    if (ok) {
        ok = false;
        std::scoped_lock lock{name_mutex};
        for (int n = 1; n < 1000 && !ok; ++n) {
            path = n == 1 ? base + ".png" : base + "-" + std::to_string(n) + ".png";
            if (std::filesystem::exists(FsPath(path), ec)) {
                continue;
            }
            ok = std::rename(temp.c_str(), path.c_str()) == 0;
            if (!ok && !std::filesystem::exists(FsPath(path), ec)) {
                break; // not a name taken meanwhile: the rename itself fails
            }
        }
    }
    if (!ok) {
        std::remove(temp.c_str());
        std::printf("Screenshot failed: could not write into %s\n", folder.c_str());
        std::fflush(stdout);
        return;
    }
    std::printf("Screenshot: %s\n", path.c_str());
    std::fflush(stdout);
    BbOverlay::NotifyScreenshot();
}

} // namespace

bool HandleEvent(const SDL_Event& event) {
    if (event.type != SDL_EVENT_KEY_DOWN && event.type != SDL_EVENT_KEY_UP) {
        return false;
    }
    if (!keys_loaded) {
        LoadKeys();
    }
    const SDL_Scancode code = event.key.scancode;
    if (code == SDL_SCANCODE_UNKNOWN || (code != keys[0] && code != keys[1])) {
        return false;
    }
    if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat && !requested.load()) {
        requested_at = static_cast<long long>(std::time(nullptr));
        failed_noted = false;
        requested = true;
    }
    return true;
}

bool Requested() {
    return requested.load(std::memory_order_relaxed);
}

void Started() {
    requested = false;
}

void Retry() {
    requested = true;
}

void Save(std::vector<unsigned char> rgba, uint32_t width, uint32_t height) {
    if (width == 0 || height == 0 || rgba.size() < size_t(width) * height * 4) {
        Fail("empty frame");
        return;
    }
    const long long when = requested_at.load();
    std::thread(Write, std::move(rgba), width, height, when).detach();
}

void Fail(const char* why) {
    requested = false;
    if (!failed_noted.exchange(true)) {
        std::printf("Screenshot failed: %s\n", why);
        std::fflush(stdout);
    }
}

} // namespace BbScreenshot
