// SPDX-License-Identifier: GPL-2.0-or-later
// The in-game menu's translations (bbport_i18n.h).
#include "bbport_i18n.h"

#include <cstdlib>
#include <cstring>
#include <string_view>
#include <unordered_map>

namespace {

// The menu's six, then the launcher's others (only the texts over the game outside the menu: the close question,
// the save list, the loading screen). Arabic rows are stored joined, in display order (tools/arabic_shape.py).
constexpr const char* languages[] = {"es", "pt", "fr", "de", "it", "ja", "ar", "nl", "da",
                                     "no", "sv", "fi", "pl", "cs", "el", "ru", "tr", "ko", "zh"};
constexpr int language_count = sizeof(languages) / sizeof(languages[0]);

struct Row {
    const char* english;
    const char* text[language_count];  // in the order of `languages`
};
const Row rows[] = {
#include "bbport_overlay_i18n.inc"
};

// The index into `languages`, -1 for English (also for an unknown language).
int LanguageIndex() {
    static const int index = [] {
        const char* env = std::getenv("BB_UI_LANGUAGE");
        if (!env) {
            return -1;
        }
        for (int i = 0; i < language_count; ++i) {
            // "pt" also for "pt_BR" or "pt-BR"
            if (std::strncmp(env, languages[i], 2) == 0 && (env[2] == 0 || env[2] == '_' || env[2] == '-')) {
                return i;
            }
        }
        return -1;
    }();
    return index;
}

} // namespace

namespace BbI18n {

// El Dorado: the menu's font cannot draw the language (Korean or Chinese without its Windows font): English.
static bool forced_english = false;

void ForceEnglish() {
    forced_english = true;
}

const char* Language() {
    const int index = LanguageIndex();
    return index < 0 || forced_english ? "en" : languages[index];
}

const char* T(const char* english) {
    const int index = LanguageIndex();
    if (index < 0 || forced_english || !english) {
        return english;
    }
    static const std::unordered_map<std::string_view, const char*> table = [index] {
        std::unordered_map<std::string_view, const char*> map;
        for (const Row& row : rows) {
            if (row.text[index] && row.text[index][0]) {
                map.emplace(row.english, row.text[index]);
            }
        }
        return map;
    }();
    const auto it = table.find(english);
    return it == table.end() ? english : it->second;
}

} // namespace BbI18n
