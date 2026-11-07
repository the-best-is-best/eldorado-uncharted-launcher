// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// El Dorado: the keyboard whose letters the key pictures show (bbport_key_layouts.h).
#include "bbport_key_layouts.h"

#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>

#include "video_core/texture_cache/button_prompts.h"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace BbKeyLayouts {
namespace {

struct Layout {
    std::string name;   ///< shown on the menu
    std::string locale; ///< kept in key-labels.txt ("en-US" for English)
#ifdef _WIN32
    HKL hkl = nullptr;
#endif
};

std::once_flag listed;
std::vector<Layout> layouts;
std::vector<std::string> names;
std::atomic<int> current{0};

std::string Utf8(const wchar_t* text, int length = -1) {
#ifdef _WIN32
    const int size = WideCharToMultiByte(CP_UTF8, 0, text, length, nullptr, 0, nullptr, nullptr);
    if (size <= 0) {
        return {};
    }
    std::string out(size_t(size), '\0');
    WideCharToMultiByte(CP_UTF8, 0, text, length, out.data(), size, nullptr, nullptr);
    if (length < 0 && !out.empty() && out.back() == '\0') {
        out.pop_back();
    }
    return out;
#else
    (void)text;
    (void)length;
    return {};
#endif
}

std::string KeptFile() {
    const char* user = std::getenv("BB_USER_DIR");
    return user && *user ? std::string(user) + "/key-labels.txt" : std::string{};
}

void List() {
    layouts.push_back({"English (US)", "en-US"});
#ifdef _WIN32
    HKL list[64];
    const int count = GetKeyboardLayoutList(64, list);
    for (int i = 0; i < count; ++i) {
        const LANGID language = LANGID(uintptr_t(list[i]) & 0xffff);
        wchar_t locale[LOCALE_NAME_MAX_LENGTH] = {};
        if (!LCIDToLocaleName(MAKELCID(language, SORT_DEFAULT), locale, LOCALE_NAME_MAX_LENGTH, 0)) {
            continue;
        }
        wchar_t shown[128] = {};
        // The language as Windows names it in English ("Arabic (Egypt)"): the menu cannot join Arabic letters at run
        // time (its texts are joined in advance, tools/arabic_shape.py).
        if (!GetLocaleInfoEx(locale, LOCALE_SENGLISHDISPLAYNAME, shown, 128)) {
            continue;
        }
        Layout layout{Utf8(shown), Utf8(locale), list[i]};
        bool known = false;
        for (const Layout& seen : layouts) {
            known = known || seen.locale == layout.locale;
        }
        if (!known) { // English (US) is already first; two layouts of one language show alike
            layouts.push_back(std::move(layout));
        }
    }
#endif
    for (const Layout& layout : layouts) {
        names.push_back(layout.name);
    }
    // The choice kept from an earlier start, if that layout is still installed.
    if (const std::string path = KeptFile(); !path.empty()) {
        if (FILE* f = std::fopen(path.c_str(), "r")) {
            char line[LOCALE_NAME_MAX_LENGTH * 4] = {};
            if (std::fgets(line, sizeof(line), f)) {
                line[std::strcspn(line, "\r\n ")] = 0;
                for (size_t i = 0; i < layouts.size(); ++i) {
                    if (layouts[i].locale == line) {
                        current.store(int(i));
                    }
                }
            }
            std::fclose(f);
        }
    }
    if (current.load() != 0) {
        std::printf("Key labels: the %s keyboard's letters (key-labels.txt)\n", layouts[current.load()].locale.c_str());
        std::fflush(stdout);
    }
}

void EnsureListed() {
    std::call_once(listed, List);
}

/// The PS/2 (set 1) scan code Windows uses for a character key at an SDL (USB) scancode; 0 for other keys.
unsigned Ps2(int sdl) {
    static const unsigned letters[26] = {0x1E, 0x30, 0x2E, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32,
                                         0x31, 0x18, 0x19, 0x10, 0x13, 0x1F, 0x14, 0x16, 0x2F, 0x11, 0x2D, 0x15, 0x2C};
    if (sdl >= 4 && sdl <= 29) { // A..Z
        return letters[sdl - 4];
    }
    if (sdl >= 30 && sdl <= 39) { // 1..9, 0
        return 0x02 + unsigned(sdl - 30);
    }
    switch (sdl) {
    case 45: return 0x0C; // -
    case 46: return 0x0D; // =
    case 47: return 0x1A; // [
    case 48: return 0x1B; // ]
    case 49: return 0x2B; // backslash
    case 51: return 0x27; // ;
    case 52: return 0x28; // '
    case 53: return 0x29; // `
    case 54: return 0x33; // ,
    case 55: return 0x34; // .
    case 56: return 0x35; // /
    case 100: return 0x56; // the key beside left Shift on ISO keyboards
    default: return 0;
    }
}

} // namespace

const std::vector<std::string>& Names() {
    EnsureListed();
    return names;
}

int Current() {
    EnsureListed();
    return current.load();
}

void Set(int index) {
    EnsureListed();
    if (index < 0 || index >= int(layouts.size()) || index == current.load()) {
        return;
    }
    current.store(index);
    if (const std::string path = KeptFile(); !path.empty()) {
        if (FILE* f = std::fopen(path.c_str(), "w")) {
            std::fprintf(f, "%s\n", layouts[size_t(index)].locale.c_str());
            std::fclose(f);
        }
    }
    std::printf("Key labels: the %s keyboard's letters\n", layouts[size_t(index)].locale.c_str());
    std::fflush(stdout);
    VideoCore::ButtonPrompts::KeymapChanged(); // the key pictures are drawn again
}

std::string Letter(int sdl_scancode) {
    EnsureListed();
    const int index = current.load();
#ifdef _WIN32
    const unsigned scan = Ps2(sdl_scancode);
    if (index <= 0 || scan == 0) {
        return {};
    }
    const HKL hkl = layouts[size_t(index)].hkl;
    const UINT vk = MapVirtualKeyExW(scan, MAPVK_VSC_TO_VK_EX, hkl);
    if (vk == 0) {
        return {};
    }
    BYTE state[256] = {};
    wchar_t text[8] = {};
    // Flag 4: the keyboard's state (a pending dead key) is left as it is (Windows 10 1607 and later).
    int length = ToUnicodeEx(vk, scan, state, text, 8, 4, hkl);
    if (length < 0) { // a dead key: its accent on its own
        length = 1;
    }
    if (length <= 0 || text[0] < 0x20) {
        return {};
    }
    CharUpperBuffW(text, DWORD(length));
    return Utf8(text, length);
#else
    (void)sdl_scancode;
    (void)index;
    return {};
#endif
}

} // namespace BbKeyLayouts
