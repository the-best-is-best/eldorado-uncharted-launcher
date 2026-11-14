// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// El Dorado's menu cursor, drawn in code (no pictures): an arrow in the launcher's treasure gold (Theme.qml `gold`,
// #deb058) with a dark edge like its ground. Three looks, as the menu mouse asks for them (cursor_state):
// 0 normal, 1 over something that answers a click (a lighter gold with a soft glow), 2 pressed (a darker gold).
// Included inside window.cpp's anonymous namespace. The cursors are made for the window's height (about 26 px high
// at 1080p, 16..128) and made again when it changes; shown only while a game menu is on screen and the overlay
// does not have the input. If SDL cannot make them, the system arrow and hand stay. BB_MENU_CURSOR=0: the system ones.

struct ArrowPoint {
    float x, y;
};
// The arrow in a 100 x 100 box, its tip at the top left (the hot spot).
constexpr ArrowPoint ArrowShape[] = {{10, 4}, {10, 80}, {28, 63}, {40, 92}, {54, 86}, {42, 58}, {68, 58}};
constexpr int ArrowPoints = sizeof(ArrowShape) / sizeof(ArrowShape[0]);
constexpr float ArrowTopY = 4.0f, ArrowBottomY = 92.0f;

struct CursorColor {
    float r, g, b;
};
CursorColor MixColor(CursorColor a, CursorColor b, float t) {
    return {a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t};
}

// Even-odd test of the arrow's inside (units of the 100 box).
bool ArrowInside(float x, float y) {
    bool inside = false;
    for (int i = 0, j = ArrowPoints - 1; i < ArrowPoints; j = i++) {
        const ArrowPoint& a = ArrowShape[i];
        const ArrowPoint& b = ArrowShape[j];
        if ((a.y > y) != (b.y > y) && x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x) {
            inside = !inside;
        }
    }
    return inside;
}

// The distance to the arrow's edge (units of the 100 box).
float ArrowEdgeDistance(float x, float y) {
    float best = 1e9f;
    for (int i = 0, j = ArrowPoints - 1; i < ArrowPoints; j = i++) {
        const ArrowPoint& a = ArrowShape[i];
        const ArrowPoint& b = ArrowShape[j];
        const float dx = b.x - a.x, dy = b.y - a.y;
        const float length2 = dx * dx + dy * dy;
        float t = length2 > 0.0f ? ((x - a.x) * dx + (y - a.y) * dy) / length2 : 0.0f;
        t = std::clamp(t, 0.0f, 1.0f);
        const float px = a.x + dx * t - x, py = a.y + dy * t - y;
        best = std::min(best, std::sqrt(px * px + py * py));
    }
    return best;
}

SDL_Cursor* menu_cursors[3]{};
int menu_cursor_size = 0;
bool menu_cursors_failed = false;

bool MenuCursorsOn() {
    static const bool on = [] {
        const char* e = std::getenv("BB_MENU_CURSOR");
        return !(e && e[0] == '0');
    }();
    return on && !menu_cursors_failed;
}

void FreeMenuCursors() {
    for (SDL_Cursor*& c : menu_cursors) {
        if (c) {
            SDL_DestroyCursor(c);
            c = nullptr;
        }
    }
}

// One look drawn `size` x `size` px, RGBA, 4 x 4 samples a pixel (smooth edges at any size).
void DrawMenuCursor(int state, int size, unsigned char* pixels) {
    constexpr CursorColor Edge = {0.071f, 0.063f, 0.043f}; // the launcher's dark ground, a little warmer
    constexpr CursorColor Glow = {0.871f, 0.690f, 0.345f}; // Theme.gold
    // The fill runs from its top to its bottom colour (a vertical gradient), per look.
    const CursorColor top = state == 1 ? CursorColor{1.000f, 0.906f, 0.651f}
                            : state == 2 ? CursorColor{0.737f, 0.557f, 0.231f}
                                         : CursorColor{0.941f, 0.800f, 0.478f};
    const CursorColor bottom = state == 1 ? CursorColor{0.949f, 0.784f, 0.447f}
                               : state == 2 ? CursorColor{0.604f, 0.447f, 0.173f}
                                            : CursorColor{0.757f, 0.584f, 0.247f};
    const float unit = 100.0f / static_cast<float>(size); // one pixel in the 100 box
    const float edge = std::max(1.0f, size * 0.045f) * unit;
    const float glow = state == 1 ? std::max(2.0f, size * 0.09f) * unit : 0.0f;
    constexpr int N = 4;
    for (int py = 0; py < size; ++py) {
        for (int px = 0; px < size; ++px) {
            float r = 0, g = 0, b = 0, a = 0;
            for (int sy = 0; sy < N; ++sy) {
                for (int sx = 0; sx < N; ++sx) {
                    const float x = (px + (sx + 0.5f) / N) * unit;
                    const float y = (py + (sy + 0.5f) / N) * unit;
                    const bool inside = ArrowInside(x, y);
                    const float d = ArrowEdgeDistance(x, y);
                    CursorColor c{};
                    float alpha = 0.0f;
                    if (d <= edge) {
                        c = Edge;
                        alpha = 1.0f;
                    } else if (inside) {
                        c = MixColor(top, bottom, std::clamp((y - ArrowTopY) / (ArrowBottomY - ArrowTopY), 0.0f, 1.0f));
                        alpha = 1.0f;
                    } else if (glow > 0.0f && d <= edge + glow) {
                        const float f = 1.0f - (d - edge) / glow;
                        c = Glow;
                        alpha = 0.55f * f * f;
                    }
                    r += c.r * alpha;
                    g += c.g * alpha;
                    b += c.b * alpha;
                    a += alpha;
                }
            }
            unsigned char* q = &pixels[(static_cast<size_t>(py) * size + px) * 4];
            if (a > 0.0f) {
                q[0] = static_cast<unsigned char>(std::min(255.0f, r / a * 255.0f + 0.5f));
                q[1] = static_cast<unsigned char>(std::min(255.0f, g / a * 255.0f + 0.5f));
                q[2] = static_cast<unsigned char>(std::min(255.0f, b / a * 255.0f + 0.5f));
                q[3] = static_cast<unsigned char>(std::min(255.0f, a / (N * N) * 255.0f + 0.5f));
            } else {
                q[0] = q[1] = q[2] = q[3] = 0;
            }
        }
    }
}

// Every look made at `size` px, or none (false).
bool BuildMenuCursors(int size) {
    FreeMenuCursors();
    menu_cursor_size = size;
    std::vector<unsigned char> pixels(static_cast<size_t>(size) * size * 4);
    const int hot_x = static_cast<int>(ArrowShape[0].x * size / 100.0f + 0.5f);
    const int hot_y = static_cast<int>(ArrowShape[0].y * size / 100.0f + 0.5f);
    for (int s = 0; s < 3; ++s) {
        DrawMenuCursor(s, size, pixels.data());
        SDL_Surface* surface = SDL_CreateSurfaceFrom(size, size, SDL_PIXELFORMAT_RGBA32, pixels.data(), size * 4);
        if (surface) {
            menu_cursors[s] = SDL_CreateColorCursor(surface, hot_x, hot_y);
            SDL_DestroySurface(surface);
        }
        if (!menu_cursors[s]) {
            std::printf("Window: the menu cursor could not be made (%s): system cursors\n", SDL_GetError());
            FreeMenuCursors();
            return false;
        }
    }
    std::printf("Window: menu cursor built at %d px (BB_MENU_CURSOR=0: system cursors)\n", size);
    return true;
}
