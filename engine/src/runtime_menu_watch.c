/* Copyright (C) 2026 Michelle Raouf
 * El Dorado: going back from a game's main menu asks "Close the game?" (the window's close question,
 * bbgpu_ask_close) instead of leaving the player on the title page ("Press ... to begin").
 *
 * The games' menu hosts (runtime_menu_host, noted by runtime_exit_menu.c) keep the depth of the open pages and the
 * page on screen; found with BB_MENU_PROBE=1 (6 Nov 2026, 1.02 code): the title page is depth 0, the main menu
 * depth 1 (page 0x0c), its pages (Options ...) depth 2. Back from the main menu = depth 1 -> 0 while the page was
 * 0x0c; the pause menu's pages are others, so closing the pause menu in play never asks.
 *   Uncharted 1: depth at host+0x790, page at +0x794;  Uncharted 2: +0x1010, +0x1014;  Uncharted 3: +0xdb0, +0x8.
 * Called every frame from the menu update hooks (runtime_checkpoint.c). BB_MENU_PROBE=1 also logs every field of
 * the host that changes after holding still (to find these fields again in another build). */
#include "runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAIN_MENU_PAGE 0x0cu

void bbgpu_ask_close(void); /* gpu/shim/window.cpp */

typedef struct {
    const char *name;
    size_t depth, page;
} MenuFields;
static const MenuFields fields[3]={{"Uncharted 1",0x790,0x794},{"Uncharted 2",0x1010,0x1014},
                                   {"Uncharted 3",0xdb0,0x8}};

static void probe(const char *game, const unsigned char *manager);

static double now_s(void);
static volatile double pause_menu_seen; /* a menu page on screen after play began (the pause menu and its pages) */
static volatile double main_menu_seen; /* when a menu update last saw the main menu on screen (depth 1, page 0x0c) */
/* Uncharted 1's pause menu Options page has the main menu's depth and page too (7 Nov 2026: Back there asked to close
 * the game). The main menu of a start comes before any play (camera hooks: runtime_play_calls), the pause menu after
 * it; so the question is asked only before the run's first play. (A main menu reached again from the pause menu goes
 * back to the title page, as the game itself does.) */
static int before_play(void) {
    return runtime_play_calls == 0;
}

int runtime_menu_at_main(void) {
    return main_menu_seen > 0 && now_s() - main_menu_seen < 0.25 && before_play();
}

/* The pause menu or one of its pages is on screen (host depth 1 or more once the game was in play; Uncharted 1's pause
 * Options page counts: its depth is the main menu's). */
int runtime_menu_open(void) {
    return pause_menu_seen > 0 && now_s() - pause_menu_seen < 0.25 && !before_play();
}

static void continue_watch(int game, const unsigned char *host);

void runtime_menu_watch(int game, const unsigned char *host) {
    static const unsigned char *last_host[3];
    static uint32_t last_depth[3], last_page[3];
    if (game >= 0 && game <= 2) continue_watch(game, host);
    if (game < 0 || game > 2 || !host) return;
    probe(fields[game].name, host);
    uint32_t depth, page;
    memcpy(&depth, host + fields[game].depth, 4);
    memcpy(&page, host + fields[game].page, 4);
    if (depth == 1 && page == MAIN_MENU_PAGE) main_menu_seen = now_s();
    if (depth >= 1 && depth < 16 && !before_play()) pause_menu_seen = now_s();
    if (host == last_host[game] && last_depth[game] == 1 && depth == 0 && last_page[game] == MAIN_MENU_PAGE &&
        before_play()) {
        printf("Menu: %s: back from the main menu, asking whether to close the game\n", fields[game].name);
        fflush(stdout);
        bbgpu_ask_close();
    }
    last_host[game] = host;
    last_depth[game] = depth;
    last_page[game] = page;
}

/* ---- El Dorado: straight to the main menu (BB_SKIP_TITLE=1) ----
 * The launcher starts each game with BB_SKIP_TITLE=1: the title page ("Press ... to begin") and the start screens
 * before the main menu are moved on by Cross taps, every 2 s, until a menu page shows; the main menu (depth 1, page
 * 0x0c) is then the player's. No tap ever lands on a menu, so nothing is picked for the player.
 *   Stops for good: a menu page on screen, the game in play (camera hooks running), or 3 minutes. */
#define SKIP_CROSS 0x4000u /* the PS4 pad's Cross bit (runtime_pad.c BTN_CROSS) */
#define SKIP_TAP_S 0.12

static volatile int skip_state = -1; /* -1 unread, 0 off or finished, 1 before the main menu */
static volatile double skip_press_until;

static void skip_stop(const char *game, const char *why) {
    if (skip_state > 0) {
        printf("Skip title: %s: %s\n", game, why);
        fflush(stdout);
    }
    skip_state = 0;
}

uint32_t runtime_continue_buttons(void) {
    return skip_state > 0 && now_s() < skip_press_until ? SKIP_CROSS : 0;
}

static void continue_watch(int game, const unsigned char *host) {
    static double started, next_tap;
    const char *name = fields[game].name;
    const double t = now_s();
    if (skip_state < 0) {
        const char *e = getenv("BB_SKIP_TITLE");
        skip_state = e && e[0] == '1' ? 1 : 0;
        started = t;
        next_tap = t + 3.0;
        if (skip_state) {
            printf("Skip title: %s: on (BB_SKIP_TITLE=1): the start page is passed, the main menu is yours\n", name);
            fflush(stdout);
        }
    }
    if (skip_state <= 0) return;
    if (runtime_play_calls) { skip_stop(name, "the game is in play"); return; }
    if (t - started > 180.0) { skip_stop(name, "no menu after 3 minutes; stopping"); return; }
    uint32_t depth = 0, page = 0;
    if (host) {
        memcpy(&depth, host + fields[game].depth, 4);
        memcpy(&page, host + fields[game].page, 4);
    }
    if (host && depth >= 1) {
        skip_stop(name, depth == 1 && page == MAIN_MENU_PAGE ? "main menu on screen" : "a menu page on screen");
        return;
    }
    if (t >= next_tap) { /* the title page and the start screens: a Cross tap moves them on */
        skip_press_until = t + SKIP_TAP_S;
        next_tap = t + 2.0;
    }
}

/* ---- BB_MENU_PROBE=1: the host's fields that follow the pages ---- */

#define PROBE_BYTES 0x1900
#define FIELDS (PROBE_BYTES / 4)

static double now_s(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + t.tv_nsec * 1e-9;
}

static void probe(const char *game, const unsigned char *manager) {
    static int state = -1; /* -1 unread, 0 off, 1 on */
    static const unsigned char *last_manager;
    static uint32_t last[FIELDS];
    static double since[FIELDS];
    static unsigned changes[FIELDS];
    static unsigned printed;
    if (state < 0) {
        const char *e = getenv("BB_MENU_PROBE");
        state = e && e[0] == '1';
    }
    if (!state || !manager || printed > 4000) return;
    const double t = now_s();
    if (manager != last_manager) { /* another host: start over */
        last_manager = manager;
        memcpy(last, manager, sizeof(last));
        for (int i = 0; i < FIELDS; ++i) since[i] = t, changes[i] = 0;
        printf("Menu probe: %s manager %p\n", game, (const void *)manager);
        fflush(stdout);
        return;
    }
    uint32_t now[FIELDS];
    memcpy(now, manager, sizeof(now));
    for (int i = 0; i < FIELDS; ++i) {
        if (now[i] == last[i]) continue;
        if (changes[i] < 12 && t - since[i] > 0.5) {
            printf("Menu probe: %s +0x%x: %08x -> %08x (held %.1f s)\n", game, (unsigned)(i * 4), last[i], now[i],
                   t - since[i]);
            ++printed;
        }
        ++changes[i];
        last[i] = now[i];
        since[i] = t;
    }
    fflush(stdout);
}
