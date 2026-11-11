// bbport: SDL3 window for the Vulkan swapchain (X11 or Wayland).
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <SDL3/SDL.h>
#include "common/assert.h"
#include "common/logging/log.h"
#include "sdl_window.h"
#include "bbport_overlay.h"
#include "bbport_png.h"
#include "bbport_i18n.h"
#include "bbport_loading_icon.h"
#include "bbport_screenshot.h"
#include "video_core/renderer_vulkan/vk_frame_capture.h"
#include "video_core/texture_cache/button_prompts.h"

namespace {
// bbport: mouse input for runtime_pad.c (keyboard and mouse controls). The window thread adds
// the motion, buttons and wheel of its events; the pad sampling takes them (bbgpu_mouse_sample).
std::mutex mouse_mutex;
float mouse_dx{}, mouse_dy{};
// The mouse's movement with the event times (SDL ns), for bbgpu_mouse_rate: the cameras take the
// mouse's rate over a short window instead of whatever reached the last pad read.
struct MouseMark {
    u64 ns;
    double x, y;
};
std::array<MouseMark, 512> mouse_marks{};
size_t mouse_mark_next = 0, mouse_mark_count = 0;
double mouse_cum_x = 0.0, mouse_cum_y = 0.0;
int mouse_wheel{};
u32 mouse_buttons{};
std::atomic<bool> mouse_look{false}, mouse_captured{false};
// A game menu is on screen (bbgpu_menu_cursor, the menu mouse by antikmewzik): the cursor is free and shown;
// cursor_state: its look (0 arrow, 1 hand, 2 pressed), applied by the window thread.
std::atomic<bool> menu_cursor{false};
std::atomic<int> cursor_state{0};
bool window_focused{true};
// Without mouse look (controller play) the cursor was left showing over the game: it hides after
// two seconds without mouse movement and comes back when the mouse moves (the menu shows it too).
constexpr u64 CursorIdleNs = 2'000'000'000ull;
u64 cursor_moved_ns = 0;
bool cursor_hidden = false;
// The game window is in front (Windows' own answer, set each event poll): the controller is read
// only then (runtime_pad.c, bbgpu_window_foreground). SDL's keyboard focus can be lost while the
// window stays in front, and with it SDL dropped the gamepad events (from BilalReloaded's port).
std::atomic<bool> window_foreground{true};
// Alt+Enter switched between window and fullscreen: its Enter is kept from the game until released
// (Enter is a default key for Options).
std::atomic<bool> enter_swallowed{false};
// Alt+Enter switches only between shapes the game was set up for: the ultrawide field of view and the
// native render size are taken once at start (runtime_ultrawide.c: the screen in fullscreen, else
// BB_WINDOW_SIZE), so another shape would be stretched or pillarboxed. start_aspect: that shape;
// windowed_w/h: the window's own size (as created, or the last size while not fullscreen).
double start_aspect = 0.0;
int windowed_w = 0, windowed_h = 0;

double DesktopAspect(SDL_Window* window) {
    const SDL_DisplayMode* mode = SDL_GetDesktopDisplayMode(SDL_GetDisplayForWindow(window));
    return mode && mode->w > 0 && mode->h > 0 ? double(mode->w) / double(mode->h) : 0.0;
}

u32 MouseBit(u8 button) {
    switch (button) {
    case SDL_BUTTON_LEFT: return 1u;
    case SDL_BUTTON_RIGHT: return 2u;
    case SDL_BUTTON_MIDDLE: return 4u;
    case SDL_BUTTON_X1: return 8u;
    case SDL_BUTTON_X2: return 16u;
    default: return 0u;
    }
}
} // namespace

extern "C" void bbgpu_mouse_configure(int look) {
    mouse_look = look != 0;
}

extern "C" void bbgpu_menu_cursor(int open) {
    menu_cursor = open != 0;
}

extern "C" void bbgpu_set_cursor(int state) {
    cursor_state = state;
}

// The mouse's movement over the last `window_s` seconds, per second (pixels/s), from the event times.
extern "C" void bbgpu_mouse_rate(double window_s, float* rate_x, float* rate_y) {
    std::scoped_lock lock{mouse_mutex};
    *rate_x = *rate_y = 0.0f;
    const u64 now = SDL_GetTicksNS();
    const u64 from = now - static_cast<u64>(window_s * 1e9);
    // the movement up to `from`: the newest mark at or before it (all marks newer: the ring's start)
    double base_x = mouse_mark_count < mouse_marks.size() ? 0.0 : mouse_cum_x;
    double base_y = mouse_mark_count < mouse_marks.size() ? 0.0 : mouse_cum_y;
    bool found = false;
    for (size_t i = 0; i < mouse_mark_count; ++i) { // newest first
        const auto& m = mouse_marks[(mouse_mark_next + mouse_marks.size() - 1 - i) % mouse_marks.size()];
        if (m.ns <= from) {
            base_x = m.x;
            base_y = m.y;
            found = true;
            break;
        }
    }
    if (!found && mouse_mark_count == mouse_marks.size()) { // the ring is newer than the window: its oldest
        const auto& m = mouse_marks[mouse_mark_next];
        base_x = m.x;
        base_y = m.y;
    }
    *rate_x = static_cast<float>((mouse_cum_x - base_x) / window_s);
    *rate_y = static_cast<float>((mouse_cum_y - base_y) / window_s);
}

extern "C" int bbgpu_mouse_sample(float* dx, float* dy, uint32_t* buttons, int* wheel) {
    std::scoped_lock lock{mouse_mutex};
    *dx = mouse_dx;
    *dy = mouse_dy;
    *buttons = mouse_buttons;
    *wheel = mouse_wheel;
    mouse_dx = mouse_dy = 0.0f;
    mouse_wheel = 0;
    return mouse_captured ? 1 : 0;
}

#ifdef _WIN32
// Declared here: windows.h clashes with names used by this file's headers.
extern "C" __declspec(dllimport) void* __stdcall GetForegroundWindow();
extern "C" __declspec(dllimport) void* __stdcall GetAncestor(void* hwnd, unsigned int flags);
#endif

extern "C" int bbgpu_window_foreground(void) {
    return window_foreground.load(std::memory_order_relaxed) ? 1 : 0;
}

// El Dorado: the game's thread asks the window to put the close question on screen (the menus' Quit, back from
// the main menu: runtime_exit_menu.c, runtime_menu_watch.c); the window thread shows it at its next events.
static std::atomic<bool> close_question_wanted{false};

// El Dorado: the window minimized or out of focus stops the game where it is (its threads and clocks, as the
// shader preparation page does: runtime_freeze_reason), and it goes on when the window is back. No menu is opened.
// BB_PAUSE_ON_FOCUS_LOST=0: off.
extern "C" void runtime_freeze_reason(unsigned reason, int on, const char* why);
// Back from the background: runtime_pad.c opens the game's pause menu (bbgpu_take_back_request, bbgpu.cpp).
extern std::atomic<int> bbgpu_back_request;
// Not while the game loads (until its first picture, the shader preparation page included): a start sent to the
// background went on loading instead of standing still for the whole time (12-33 s seen); the pause follows once
// the first picture is up and the window is still away (pause_pending, checked at each event poll).
extern "C" int bbgpu_loading_done(void);
static bool pause_pending = false;
static void PauseRequest(bool away) {
    static const bool off = [] {
        const char* env = std::getenv("BB_PAUSE_ON_FOCUS_LOST");
        return env && env[0] == '0';
    }();
    static bool frozen = false;
    if (away && !frozen && !off && !bbgpu_loading_done()) {
        if (!pause_pending) {
            std::printf("Pause: the window is in the background while the game loads: it loads on\n");
            std::fflush(stdout);
        }
        pause_pending = true;
        return;
    }
    if (!away) {
        pause_pending = false;
    }
    if (off || away == frozen) {
        return;
    }
    frozen = away;
    runtime_freeze_reason(2, away ? 1 : 0, "the game's window is in the background");
    if (!away) {
        bbgpu_back_request = 1;
    }
}

extern "C" void bbgpu_ask_close(void) {
    close_question_wanted.store(true, std::memory_order_release);
}

extern "C" int bbgpu_window_enter_swallowed(void) {
    return enter_swallowed.load(std::memory_order_relaxed) ? 1 : 0;
}

// The menu mouse (runtime_menumouse.c): a widened gameplay frame fills the window (its 16:9 layout stretched across it, so
// the pause menu over the play is too); other frames are shown at 16:9 in the middle.
namespace Vulkan {
extern std::atomic<bool> g_last_frame_scene; // vk_rasterizer.cpp
}
extern "C" int runtime_ultrawide_fill;
extern "C" int bbgpu_frame_fills_window(void) {
    return runtime_ultrawide_fill && Vulkan::g_last_frame_scene.load(std::memory_order_relaxed) ? 1 : 0;
}

namespace Frontend {

WindowSDL::WindowSDL(s32 width_, s32 height_, const char* title) : width{width_}, height{height_} {
    // Gamepads are sampled by runtime_pad.c; their events are pumped here with the window's.
    // Their events come whatever SDL thinks of the keyboard focus; whether the game is in front
    // is decided from Windows instead (window_foreground). BB_PAD_BACKGROUND=0: as before;
    // BB_PAD_BACKGROUND=1: the game also takes them while another window is in front (runtime_pad.c).
    if (const char* env = std::getenv("BB_PAD_BACKGROUND"); !(env && env[0] == '0')) {
        SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
    }
    // El Dorado: the close button or Alt+F4 on the game's only window must reach the close question
    // (SDL_EVENT_WINDOW_CLOSE_REQUESTED); by default SDL also sends SDL_EVENT_QUIT for it, which closes at once.
    SDL_SetHint(SDL_HINT_QUIT_ON_LAST_WINDOW_CLOSE, "0");
    // Controllers are updated on the runtime's pad thread (runtime_pad.c): a rescan when one is switched off or on held
    // up this window's event pump, and presenting with it (0.3.6.44). BB_PAD_THREAD=0: the pump updates them.
    if (const char* env = std::getenv("BB_PAD_THREAD"); !(env && env[0] == '0')) {
        SDL_SetHint(SDL_HINT_AUTO_UPDATE_JOYSTICKS, "0");
    }
    if (!SDL_InitSubSystem(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD)) {
        UNREACHABLE_MSG("Failed to initialize SDL video: {}", SDL_GetError());
    }
    SDL_PropertiesID props = SDL_CreateProperties();
    SDL_SetStringProperty(props, SDL_PROP_WINDOW_CREATE_TITLE_STRING, title);
    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_X_NUMBER, SDL_WINDOWPOS_CENTERED);
    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_Y_NUMBER, SDL_WINDOWPOS_CENTERED);
    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_WIDTH_NUMBER, width_);
    SDL_SetNumberProperty(props, SDL_PROP_WINDOW_CREATE_HEIGHT_NUMBER, height_);
    SDL_SetBooleanProperty(props, SDL_PROP_WINDOW_CREATE_RESIZABLE_BOOLEAN, true);
    SDL_SetBooleanProperty(props, SDL_PROP_WINDOW_CREATE_VULKAN_BOOLEAN, true);
    const char* fullscreen = std::getenv("BB_FULLSCREEN");
    SDL_SetBooleanProperty(props, SDL_PROP_WINDOW_CREATE_FULLSCREEN_BOOLEAN, fullscreen && fullscreen[0] == '1');
    base_title = title;
    window = SDL_CreateWindowWithProperties(props);
    SDL_DestroyProperties(props);
    ASSERT_MSG(window, "Failed to create window: {}", SDL_GetError());
    // El Dorado: the game's loading icon on the window and its taskbar button, once taken from a loading screen
    // (bbport_loading_icon.h); until then the executable's icon.
    SetLoadingIcon();
    if (!(fullscreen && fullscreen[0] == '1')) {
        FitWindowToScreen();
    }
    windowed_w = width_;
    windowed_h = height_;
    start_aspect = fullscreen && fullscreen[0] == '1' ? DesktopAspect(window)
                                                      : double(width_) / double(height_ > 0 ? height_ : 1);
    // bbport: a game started from the collection menu (run.py sets BB_RAISE_WINDOW) opened behind
    // other windows, as the menu's process had ended: no input until the window was clicked.
    if (const char* raise = std::getenv("BB_RAISE_WINDOW"); raise && raise[0] == '1') {
        SDL_SetHint(SDL_HINT_FORCE_RAISEWINDOW, "1");
        SDL_RaiseWindow(window);
    }

    const char* driver = SDL_GetCurrentVideoDriver();
    const SDL_PropertiesID wp = SDL_GetWindowProperties(window);
#ifdef _WIN32
    if (driver && !std::strcmp(driver, "windows")) {
        window_info.type = WindowSystemType::Windows;
        window_info.render_surface = SDL_GetPointerProperty(wp, SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr);
    } else
#endif
    if (driver && !std::strcmp(driver, "x11")) {
        window_info.type = WindowSystemType::X11;
        window_info.display_connection = SDL_GetPointerProperty(wp, SDL_PROP_WINDOW_X11_DISPLAY_POINTER, nullptr);
        window_info.render_surface = reinterpret_cast<void*>(SDL_GetNumberProperty(wp, SDL_PROP_WINDOW_X11_WINDOW_NUMBER, 0));
    } else if (driver && !std::strcmp(driver, "wayland")) {
        window_info.type = WindowSystemType::Wayland;
        window_info.display_connection = SDL_GetPointerProperty(wp, SDL_PROP_WINDOW_WAYLAND_DISPLAY_POINTER, nullptr);
        window_info.render_surface = SDL_GetPointerProperty(wp, SDL_PROP_WINDOW_WAYLAND_SURFACE_POINTER, nullptr);
    } else {
        UNREACHABLE_MSG("Unsupported SDL video driver {}", driver ? driver : "(none)");
    }
    int w = 0, h = 0;
    SDL_GetWindowSizeInPixels(window, &w, &h);
    width = w;
    height = h;
    LOG_INFO(Frontend, "Window {}x{} on {}", w, h, driver);
}

// El Dorado: a window (not fullscreen) that would not fit the screen's usable area with its frame (the screen's own
// size went past the screen and under the taskbar) is made smaller, keeping its shape, and centred in that area.
void WindowSDL::FitWindowToScreen() {
    SDL_Rect area{};
    const SDL_DisplayID display = SDL_GetDisplayForWindow(window);
    if (!display || !SDL_GetDisplayUsableBounds(display, &area) || area.w <= 0 || area.h <= 0) {
        return;
    }
    int top = 0, left = 0, bottom = 0, right = 0;
    SDL_GetWindowBordersSize(window, &top, &left, &bottom, &right); // 0 when the system does not say
    int w = 0, h = 0;
    SDL_GetWindowSize(window, &w, &h);
    const int room_w = area.w - left - right, room_h = area.h - top - bottom;
    if (w <= 0 || h <= 0 || room_w <= 0 || room_h <= 0 || (w <= room_w && h <= room_h)) {
        return;
    }
    const double scale = std::min(double(room_w) / w, double(room_h) / h);
    const int fit_w = std::max(1, int(w * scale)), fit_h = std::max(1, int(h * scale));
    SDL_SetWindowSize(window, fit_w, fit_h);
    SDL_SetWindowPosition(window, area.x + left + (room_w - fit_w) / 2, area.y + top + (room_h - fit_h) / 2);
    std::printf("Window: %dx%d made %dx%d to fit the screen (usable %dx%d)\n", w, h, fit_w, fit_h, area.w, area.h);
    std::fflush(stdout);
}

WindowSDL::~WindowSDL() {
    SDL_DestroyWindow(window);
}

void WindowSDL::BeginTextInput(const std::string& initial, const std::string& prompt) {
    std::scoped_lock lock{text_mutex};
    text = initial;
    text_prompt = prompt;
    text_state = 0;
    text_requested = true;
}

int WindowSDL::PollTextInput(std::string& out) {
    std::scoped_lock lock{text_mutex};
    out = text;
    return text_state;
}

void WindowSDL::UpdateTextTitle() {
    const std::string title = text_active ? base_title + " \u2014 " + text_prompt + ": " + text + "_  (Enter = OK, Esc = cancel)"
                                          : base_title;
    SDL_SetWindowTitle(window, title.c_str());
    BbOverlay::SetTextEntry(text_active, text_prompt, text);
}

void WindowSDL::SetLoadingIcon() {
    // The one taken from this player's game, else El Dorado's drawn one (BB_LOADING_ICON_DEFAULT).
    const char* path = BbLoadingIcon::Path();
    const char* drawn = std::getenv("BB_LOADING_ICON_DEFAULT");
    BbPng::Image icon;
    if (!(path && BbPng::LoadRgba(path, icon, 256, 256)) && !(drawn && BbPng::LoadRgba(drawn, icon, 256, 256))) {
        return;
    }
    if (SDL_Surface* surface =
            SDL_CreateSurfaceFrom(icon.width, icon.height, SDL_PIXELFORMAT_RGBA32, icon.rgba.data(), icon.width * 4)) {
        SDL_SetWindowIcon(window, surface); // SDL keeps its own copy
        SDL_DestroySurface(surface);
    }
}

bool WindowSDL::PollEvents() {
    if (BbLoadingIcon::TakeNew()) { // taken from this start's first loading screen
        SetLoadingIcon();
    }
    // El Dorado: the launcher's STOP writes BB_STOP_FILE; the game then closes the usual way, so the shader cache's
    // last writes are kept (a kill lost them, and the next start prepared the shaders again). Looked at 4 times a
    // second; the launcher ends the game itself when this takes too long.
    {
        static const char* stop_file = std::getenv("BB_STOP_FILE");
        static u64 next_look = 0;
        if (stop_file && *stop_file && SDL_GetTicks() >= next_look) {
            next_look = SDL_GetTicks() + 250;
            if (std::filesystem::exists(std::filesystem::u8path(stop_file))) {
                std::printf("Window closed (the launcher's STOP)\n");
                std::fflush(stdout);
                is_open = false;
                return false;
            }
        }
    }
    if (close_question_wanted.exchange(false, std::memory_order_acq_rel) && !close_asked &&
        !BbOverlay::ChoiceOpen()) {
        BbOverlay::BeginChoice(4, {BbI18n::T("Keep playing"), BbI18n::T("Close the game")}, {}, 0, -1);
        close_asked = true;
    }
    if (close_asked) { // the close question: entry 1 closes, Keep playing or Esc goes back to the game
        const int answer = BbOverlay::PollChoice();
        if (answer != -1) {
            close_asked = false;
            close_request_ms = 0;
            BbOverlay::EndChoice();
            if (answer == 1) {
                std::printf("Window closed (the player confirmed closing the game)\n");
                std::fflush(stdout);
                is_open = false;
                return false;
            }
        }
    }
    {
        std::scoped_lock lock{text_mutex};
        if (text_requested) { // SDL text input must be toggled from the window thread
            text_requested = false;
            text_active = true;
            SDL_StartTextInput(window);
            UpdateTextTitle();
        }
    }
    if (!text_active) {
        BbOverlay::UpdateTextInput(window);
    }
#ifdef _WIN32
    {
        // In front: the game window, a window it owns (an overlay in exclusive fullscreen), or
        // SDL's keyboard focus on it.
        void* hwnd = SDL_GetPointerProperty(SDL_GetWindowProperties(window),
                                            SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr);
        void* foreground = GetForegroundWindow();
        constexpr unsigned int GA_ROOTOWNER = 3;
        window_foreground = !hwnd || foreground == hwnd ||
                            (foreground && GetAncestor(foreground, GA_ROOTOWNER) == hwnd) ||
                            SDL_GetKeyboardFocus() == window;
    }
#endif
    // Mouse look holds the cursor in the window (relative mode) while the game has the focus;
    // the settings menu, text entry and a held Left Alt give it back.
    {
        const bool* keys = SDL_GetKeyboardState(nullptr);
        const bool want = mouse_look && window_focused && !text_active && !menu_cursor &&
                          !BbOverlay::CapturesInput() && !(keys && keys[SDL_SCANCODE_LALT]);
        if (want != mouse_captured) {
            SDL_SetWindowRelativeMouseMode(window, want);
            mouse_captured = want;
            std::scoped_lock lock{mouse_mutex};
            mouse_dx = mouse_dy = 0.0f;
            mouse_buttons = 0;
        }
        // Mouse look's relative mode hides the cursor itself; otherwise an idle cursor is hidden
        // while the game has the focus and nothing needs it (menu, text entry).
        const bool hide = window_focused && !text_active && !BbOverlay::CapturesInput() &&
                          SDL_GetTicksNS() - cursor_moved_ns > CursorIdleNs;
        // In a game menu the cursor shows a hand over what answers a click (the menu mouse).
        {
            static SDL_Cursor* arrow = nullptr;
            static SDL_Cursor* hand = nullptr;
            static int shown = -1;
            const int state = menu_cursor ? cursor_state.load() : 0;
            const int want_shape = state == 0 ? 0 : 1;
            if (want_shape != shown) {
                if (!arrow) {
                    arrow = SDL_CreateSystemCursor(SDL_SYSTEM_CURSOR_DEFAULT);
                    hand = SDL_CreateSystemCursor(SDL_SYSTEM_CURSOR_POINTER);
                }
                if (SDL_Cursor* c = want_shape ? hand : arrow) {
                    SDL_SetCursor(c);
                }
                shown = want_shape;
            }
        }
        if (!mouse_captured && hide != cursor_hidden) {
            if (hide) {
                SDL_HideCursor();
            } else {
                SDL_ShowCursor();
            }
            cursor_hidden = hide;
        }
    }
    if (pause_pending && bbgpu_loading_done()) {
        PauseRequest(true); // loaded while away: the pause follows now
    }
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_EVENT_MOUSE_MOTION && !mouse_captured) {
            cursor_moved_ns = SDL_GetTicksNS();
            if (cursor_hidden) { // back at once, not at the next poll
                SDL_ShowCursor();
                cursor_hidden = false;
            }
        }
        if (text_active && (event.type == SDL_EVENT_TEXT_INPUT || event.type == SDL_EVENT_KEY_DOWN)) {
            std::scoped_lock lock{text_mutex};
            if (event.type == SDL_EVENT_TEXT_INPUT) {
                text += event.text.text;
            } else if (event.key.key == SDLK_BACKSPACE && !text.empty()) {
                size_t cut = text.size() - 1; // drop one UTF-8 code point
                while (cut > 0 && (static_cast<unsigned char>(text[cut]) & 0xC0) == 0x80) --cut;
                text.erase(cut);
            } else if (event.key.key == SDLK_RETURN || event.key.key == SDLK_KP_ENTER || event.key.key == SDLK_ESCAPE) {
                text_state = event.key.key == SDLK_ESCAPE ? 2 : 1;
                text_active = false;
                SDL_StopTextInput(window);
            }
            UpdateTextTitle();
            continue;
        }
        // The screenshot key (F12 or input.ini key.screenshot): the next game frame as a PNG; the key goes nowhere else.
        if (BbScreenshot::HandleEvent(event)) {
            continue;
        }
        // Alt+Enter: window <-> fullscreen while playing (the launcher's Fullscreen is SDL's borderless
        // fullscreen on the desktop's mode, as here). The swapchain follows the size change through the
        // resize events below (the presenter recreates it when the window size differs). Leaving
        // fullscreen gives the window its own size back (BB_WINDOW_SIZE as the game started, or the
        // last window size). The Enter is kept from the game (Options) until it is released.
        // Only when the screen and the window have the same shape (within 1%): the game's field of
        // view and render size stay as they were set up at start (start_aspect above).
        if (event.type == SDL_EVENT_KEY_DOWN && !event.key.repeat &&
            (event.key.key == SDLK_RETURN || event.key.key == SDLK_KP_ENTER) && (event.key.mod & SDL_KMOD_ALT)) {
            const bool full = (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN) != 0;
            const double target = full ? double(windowed_w) / double(windowed_h > 0 ? windowed_h : 1)
                                       : DesktopAspect(window);
            if (start_aspect <= 0.0 || target <= 0.0 || std::abs(target / start_aspect - 1.0) > 0.01) {
                LOG_WARNING(Frontend,
                            "Alt+Enter: window and screen shapes differ ({:.3f} set up at start, {:.3f} for {}); "
                            "not switched, change it in the launcher",
                            start_aspect, target, full ? "the window" : "fullscreen");
                std::printf("Alt+Enter: window and screen shapes differ; change it in the launcher\n");
                std::fflush(stdout);
            } else if (SDL_SetWindowFullscreen(window, !full)) {
                // El Dorado: as F11, a window left from fullscreen fits the screen's usable area with its frame.
                // A borderless start's window is the screen's own size, so the switch showed no change at all.
                if (full) {
                    FitWindowToScreen();
                }
                LOG_INFO(Frontend, "Alt+Enter: {}", full ? "window" : "fullscreen");
                std::printf("Window: Alt+Enter, %s\n", full ? "windowed" : "fullscreen"); // tools/test_report.py
                std::fflush(stdout);
            } else {
                LOG_WARNING(Frontend, "Alt+Enter: could not switch: {}", SDL_GetError());
            }
            enter_swallowed = true;
            continue;
        }
        if (event.type == SDL_EVENT_KEY_UP && (event.key.key == SDLK_RETURN || event.key.key == SDLK_KP_ENTER)) {
            enter_swallowed = false;
        }
        // BB_TEXTURE_DUMP=1: F10 saves the textures of the next frame (user/texture_dump).
        if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_F10 && !event.key.repeat) {
            Vulkan::FrameCapture::ArmTextureDump();
        }
        // El Dorado: F11 switches between a window and fullscreen while playing (for this run; the launcher's Display
        // setting is the start's). Not with BB_DEV_MENU=1, where F11 opens Naughty Dog's developer menu.
        if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_F11 && !event.key.repeat) {
            static const bool dev_menu = [] {
                const char* env = std::getenv("BB_DEV_MENU");
                return env && env[0] == '1';
            }();
            if (!dev_menu) {
                const bool now_fullscreen = (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN) != 0;
                SDL_SetWindowFullscreen(window, !now_fullscreen);
                if (now_fullscreen) {
                    FitWindowToScreen();
                }
                std::printf("Window: F11, %s\n", now_fullscreen ? "windowed" : "fullscreen");
                std::fflush(stdout);
                continue;
            }
        }
        // The controller finishes the text dialog too: Cross (A) accepts, Circle (B) cancels.
        if (text_active && event.type == SDL_EVENT_GAMEPAD_BUTTON_DOWN &&
            (event.gbutton.button == SDL_GAMEPAD_BUTTON_SOUTH ||
             event.gbutton.button == SDL_GAMEPAD_BUTTON_EAST)) {
            std::scoped_lock lock{text_mutex};
            text_state = event.gbutton.button == SDL_GAMEPAD_BUTTON_SOUTH ? 1 : 2;
            text_active = false;
            SDL_StopTextInput(window);
            UpdateTextTitle();
            continue;
        }
        if (event.type == SDL_EVENT_MOUSE_BUTTON_UP) {
            // A release always reaches the game's mouse state, also when the overlay takes the event: the click
            // that opens the in-game save list is released over the list, and its button would stay held for the
            // game (its next click no press).
            std::scoped_lock lock{mouse_mutex};
            mouse_buttons &= ~MouseBit(event.button.button);
        }
        if (BbOverlay::HandleEvent(event)) {
            continue;
        }
        switch (event.type) {
        case SDL_EVENT_MOUSE_MOTION:
            if (mouse_captured) {
                std::scoped_lock lock{mouse_mutex};
                mouse_dx += event.motion.xrel;
                mouse_dy += event.motion.yrel;
                mouse_cum_x += event.motion.xrel;
                mouse_cum_y += event.motion.yrel;
                mouse_marks[mouse_mark_next] = {event.motion.timestamp, mouse_cum_x, mouse_cum_y};
                mouse_mark_next = (mouse_mark_next + 1) % mouse_marks.size();
                mouse_mark_count = std::min(mouse_mark_count + 1, mouse_marks.size());
            }
            break;
        case SDL_EVENT_MOUSE_BUTTON_DOWN:
        case SDL_EVENT_MOUSE_BUTTON_UP: {
            std::scoped_lock lock{mouse_mutex};
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && !BbOverlay::CapturesInput()) {
                mouse_buttons |= MouseBit(event.button.button);
            } else {
                mouse_buttons &= ~MouseBit(event.button.button);
            }
            break;
        }
        case SDL_EVENT_MOUSE_WHEEL: {
            std::scoped_lock lock{mouse_mutex};
            const float y = event.wheel.direction == SDL_MOUSEWHEEL_FLIPPED ? -event.wheel.y : event.wheel.y;
            mouse_wheel += y > 0 ? 1 : y < 0 ? -1 : 0;
            break;
        }
        case SDL_EVENT_WINDOW_FOCUS_GAINED:
        case SDL_EVENT_WINDOW_RESTORED:
            window_focused = true;
            PauseRequest(false); // El Dorado: back: the game goes on where it stood
            break;
        case SDL_EVENT_KEYMAP_CHANGED: // another keyboard layout: the prompts show its letters
            VideoCore::ButtonPrompts::KeymapChanged();
            break;
        case SDL_EVENT_WINDOW_FOCUS_LOST: {
            window_focused = false;
            PauseRequest(true); // El Dorado: Alt+Tab or a click elsewhere stops the game where it is
            enter_swallowed = false; // its key-up may go to another window
            std::scoped_lock lock{mouse_mutex};
            mouse_buttons = 0;
            break;
        }
        case SDL_EVENT_WINDOW_MINIMIZED:
            PauseRequest(true); // El Dorado: minimized, the game stands still
            break;
        case SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED:
        case SDL_EVENT_WINDOW_RESIZED: {
            int w = 0, h = 0;
            SDL_GetWindowSizeInPixels(window, &w, &h);
            width = w;
            height = h;
            if (event.type == SDL_EVENT_WINDOW_RESIZED && event.window.data1 > 0 && event.window.data2 > 0 &&
                !(SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN)) {
                windowed_w = event.window.data1;
                windowed_h = event.window.data2;
            }
            break;
        }
        case SDL_EVENT_WINDOW_CLOSE_REQUESTED: {
            // El Dorado: the close button or Alt+F4 asks first (kind 4: "Close the game?", over the in-game menu
            // too), so a slip of the hand does not lose the play since the last save. A second request closes at
            // once, but only a second later: Alt+F4 held down repeats, and its repeats are one press.
            // BB_CONFIRM_CLOSE=0: closes at once, as before.
            const char* confirm = std::getenv("BB_CONFIRM_CLOSE");
            if (confirm && confirm[0] == '0') {
                is_open = false;
                break;
            }
            const u64 now = SDL_GetTicks();
            if (close_request_ms == 0) {
                close_request_ms = now;
                if (!close_asked && !BbOverlay::ChoiceOpen()) { // another dialog up: the next request closes
                    BbOverlay::BeginChoice(4, {BbI18n::T("Keep playing"), BbI18n::T("Close the game")}, {}, 0, -1);
                    close_asked = true;
                    std::printf("Close: the question is on screen (close button or Alt+F4)\n");
                    std::fflush(stdout);
                }
                break;
            }
            if (now - close_request_ms < 1000) {
                break; // the same press repeating
            }
            std::printf("Window closed (a second close request)\n");
            std::fflush(stdout);
            is_open = false;
            break;
        }
        case SDL_EVENT_QUIT: // Windows shutting down, or the launcher's STOP: no question
            is_open = false;
            break;
        default:
            break;
        }
    }
    // The window mode change (or another window holding the keys meanwhile) can swallow Enter's key-up:
    // once neither Enter is held, the game gets Enter again.
    if (enter_swallowed.load(std::memory_order_relaxed)) {
        const bool* keys = SDL_GetKeyboardState(nullptr);
        if (!keys || (!keys[SDL_SCANCODE_RETURN] && !keys[SDL_SCANCODE_KP_ENTER])) enter_swallowed = false;
    }
    return is_open;
}

} // namespace Frontend
