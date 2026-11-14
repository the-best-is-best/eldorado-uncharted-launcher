/* Copyright (C) 2026 Michelle Raouf
 * Diagnostic: who hurts Nate (Uncharted 2, US 1.02 code only; BB_DAMAGE_SOURCE=1, off by default). Observation only:
 * the hooks read registers and memory and change nothing in the game.
 *
 * Every damage to the player passes the player's Health object (vtable 0x103f200; the player is **(image+0x115bd20)
 * with its id at +0x44 = *(image+0x115bd28), the Health object is [player+0x1f0]; scripts read it the same way,
 * 0x9100f0 set-player-health, 0x910140 get-player-health). Its fields: +0x2c health (int), +0x30 maximum (int),
 * +0x3c byte: may die (0: health stays at 1 or more). Its methods, by vtable offset:
 *   +0x08 0x54c330 TakeDamage(esi)      health = GetHealth() - damage (clamped at 0, at 1 when it may not die)
 *   +0x20 0x54c2b0 SetCurrent(esi)      health = esi (kill-player 0x7f12d6, kill-player-no-anim 0x7ef93f, set-player-health)
 *   +0x40 0x54c260 SetCurrentAtTime(esi, [rdx])
 * Hooks (runtime_pad.c table, "damage source"):
 *   - TakeDamage after its store (0x54c362): amount, health before and after, the caller's return address (the
 *     frame's [rbp+8], regs[28]); the player's attack event handler calls it from 0x7f06e7 (return 0x7f06ec).
 *   - SetCurrent / SetCurrentAtTime at their start: a health set below the current one, or to 0 (a script kill).
 *   - AttackInfo send 0x4c08e0 (all attacks: bullets, melee, explosions, scripts; AttackInfo from 0x4c0680): when
 *     its target is the player, the source is noted (the sending function's return address, type [info+4]: 0
 *     projectile, 1 melee, 3 explosion/physics; damage [info+0x24]; attacker handle [info+8] / [info+0x10]) and the
 *     TakeDamage that follows on the same thread (the event is dispatched in the call) uses it.
 *   - NPC fire 0x24d020 and the helicopter's gun 0xa855e0: the shooting object is remembered, so a bullet whose
 *     attacker is one of them is called "Soldier bullet" or "Helicopter gun" (inferred, see the report).
 * Output: engine log lines "Damage: <source> <amount> health <before>-><after> (caller 0x...)", "ONE-HIT KILL: ..."
 * for a hit of at least the maximum health, and a short text on screen for about 2 s (runtime_damage_notice, drawn
 * by gpu/shim/bbport_overlay.cpp). */
#include "runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define PLAYER_HANDLE 0x115bd20u
#define PLAYER_HANDLE_ID 0x115bd28u
#define ATTACK_CALLER_RET 0x7f06ecu /* TakeDamage called by the player's attack event handler */
#define NOTICES 4
#define NOTICE_SECONDS 2.0

static uint64_t clock_us(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000u + (uint64_t)t.tv_nsec / 1000u;
}

/* ---- the text on screen: the newest NOTICES lines, read by the overlay thread ---- */
typedef struct {
    char text[64];
    uint64_t us;
    int severe;
} Notice;
static Notice notices[NOTICES];
static unsigned notice_next;
static volatile int notice_lock;
static void lock_notices(void) { while (__atomic_exchange_n(&notice_lock, 1, __ATOMIC_ACQUIRE)) {} }
static void unlock_notices(void) { __atomic_store_n(&notice_lock, 0, __ATOMIC_RELEASE); }

static void post_notice(const char *text, int severe) {
    lock_notices();
    Notice *n = &notices[notice_next++ % NOTICES];
    snprintf(n->text, sizeof(n->text), "%s", text);
    n->us = clock_us();
    n->severe = severe;
    unlock_notices();
}

/* index 0 is the newest; 1 when that line is on screen (younger than 2 s) */
int runtime_damage_notice(int index, char *text, int size, float *age, int *severe) {
    int found = 0;
    lock_notices();
    const unsigned newest = notice_next;
    if (index >= 0 && index < NOTICES && newest > (unsigned)index) {
        const Notice *n = &notices[(newest - 1u - (unsigned)index) % NOTICES];
        const double seconds = (double)(clock_us() - n->us) * 1e-6;
        if (n->us && seconds < NOTICE_SECONDS) {
            snprintf(text, (size_t)size, "%s", n->text);
            *age = (float)seconds;
            *severe = n->severe;
            found = 1;
        }
    }
    unlock_notices();
    return found;
}

/* ---- the player ---- */
static uint64_t player_object(uint64_t image) {
    const uint64_t slot = *(const uint64_t *)(uintptr_t)(image + PLAYER_HANDLE);
    const uint32_t id = *(const uint32_t *)(uintptr_t)(image + PLAYER_HANDLE_ID);
    if (slot < 0x10000 || !id) return 0;
    const uint64_t object = *(const uint64_t *)(uintptr_t)slot;
    if (object < 0x10000 || *(const uint32_t *)(uintptr_t)(object + 0x44) != id) return 0;
    return object;
}
static uint64_t player_health(uint64_t image) {
    const uint64_t player = player_object(image);
    if (!player) return 0;
    const uint64_t health = *(const uint64_t *)(uintptr_t)(player + 0x1f0);
    return health < 0x10000 ? 0 : health;
}

static int enabled(void) {
    static int on = -1;
    if (on < 0) {
        const char *e = getenv("BB_DAMAGE_SOURCE");
        on = e && e[0] == '1';
    }
    return on;
}

/* ---- who shoots: the last NPCs that fired and helicopters that fired a gun ---- */
#define SHOOTERS 32
static uint64_t npc_shooters[SHOOTERS], heli_shooters[SHOOTERS];
static unsigned npc_next, heli_next;
static void remember(uint64_t *list, unsigned *next, uint64_t object) {
    for (int i = 0; i < SHOOTERS; ++i) if (list[i] == object) return;
    list[(*next)++ % SHOOTERS] = object;
}
static int remembered(const uint64_t *list, uint64_t object) {
    for (int i = 0; i < SHOOTERS; ++i) if (list[i] == object) return 1;
    return 0;
}
void __attribute__((ms_abi)) runtime_damage_npc_fire(uint64_t rdi, uint64_t rsi, uint64_t image, uint64_t r14,
                                                     const uint64_t *regs) {
    (void)rsi; (void)image; (void)r14; (void)regs;
    if (enabled() && rdi > 0x10000) remember(npc_shooters, &npc_next, rdi);
}
void __attribute__((ms_abi)) runtime_damage_heli_gun(uint64_t rdi, uint64_t rsi, uint64_t image, uint64_t r14,
                                                     const uint64_t *regs) {
    (void)rsi; (void)image; (void)r14; (void)regs;
    if (enabled() && rdi > 0x10000) remember(heli_shooters, &heli_next, rdi);
}

/* ---- the attack in flight (the send and the TakeDamage that follows are one call chain on one thread) ---- */
typedef struct {
    uint64_t caller; /* return address of the 0x4c08e0 call */
    uint64_t attacker;
    uint64_t us;
    int32_t type, damage;
    int valid;
} Attack;
static _Thread_local Attack pending;

/* A function of the game that sends attacks (the sender's start and end; names from the files its asserts name) */
typedef struct {
    uint32_t start, end;
    const char *label;
} Sender;
static const Sender senders[] = {
    {0x9101a0, 0x9102c0, "Script melee damage"},        /* DcPlayerTakeMeleeDamage (player-take-melee-damage), proven */
    {0x98c800, 0x990000, "Explosion"},                  /* process-explosion.cpp, proven */
    {0xaf9890, 0xafb400, "Bullet"},                     /* projectile-bullet.cpp */
    {0xad67d0, 0xad8100, "Shotgun pellets"},            /* multi-projectile-bullet.cpp */
    {0xaf0ca0, 0xaf1920, "Bolt"},                       /* projectile-bolt.cpp */
    {0xaf1920, 0xaf2000, "Projectile"},                 /* projectile-process.cpp */
    {0xb01b70, 0xb02400, "Grenade"},                    /* projectile-grenade.cpp */
    {0x831e30, 0x832920, "NPC melee"},                  /* player-fight-npc-moves.cpp */
    {0x832920, 0x833100, "NPC melee"},
    {0x810970, 0x810b30, "NPC melee"},                  /* skill archetype functions (type 1) */
    {0x8151f0, 0x815500, "NPC melee"},
    {0x821850, 0x821a00, "NPC melee"},
    {0x82d710, 0x82d900, "NPC melee"},
    {0x830040, 0x830200, "NPC melee"},
    {0x8317c0, 0x831db0, "NPC melee"},
    {0x839d20, 0x83a0f0, "NPC melee"},
    {0x22fa20, 0x22fbe0, "NPC manager attack"},         /* npc-manager.cpp */
    {0x45bcd0, 0x45c500, "Carried object"},             /* carry-object.cpp */
    {0x4d86d0, 0x4d9000, "Breakable"},                  /* breakable.cpp */
    {0x619f50, 0x629000, "Physics hit"},                /* gamephys / net-event */
    {0x629460, 0x62a020, "Physics hit"},
    {0x9acf40, 0x9ad4b0, "Attack relay"},
};

static const char *sender_label(uint64_t caller, uint64_t image, int32_t type) {
    const uint64_t offset = caller - image;
    for (size_t i = 0; i < sizeof(senders) / sizeof(*senders); ++i) {
        if (offset >= senders[i].start && offset < senders[i].end) return senders[i].label;
    }
    return type == 3 ? "Blast" : type == 1 ? "Melee" : type == 0 ? "Projectile" : "Unknown attack";
}

/* The attacker's game object: the handle [info+8] (slot) / [info+0x10] (id), checked as 0x4c08e0 does. */
static uint64_t attacker_object(uint64_t info) {
    const uint64_t slot = *(const uint64_t *)(uintptr_t)(info + 8);
    const uint32_t id = *(const uint32_t *)(uintptr_t)(info + 0x10);
    if (slot < 0x10000 || !id) return 0;
    const uint64_t object = *(const uint64_t *)(uintptr_t)slot;
    if (object < 0x10000 || *(const uint32_t *)(uintptr_t)(object + 0x44) != id) return 0;
    return object;
}

/* AttackInfo send 0x4c08e0: rdi the AttackInfo, rsi the target. */
void __attribute__((ms_abi)) runtime_damage_attack_send(uint64_t rdi, uint64_t rsi, uint64_t image, uint64_t r14,
                                                        const uint64_t *regs) {
    (void)r14;
    if (!enabled() || rdi < 0x10000 || rsi < 0x10000) return;
    const uint64_t player = player_object(image);
    if (!player || rsi != player) return;
    Attack *a = &pending;
    a->caller = regs[25];
    a->attacker = attacker_object(rdi);
    a->type = *(const int32_t *)(uintptr_t)(rdi + 4);
    a->damage = *(const int32_t *)(uintptr_t)(rdi + 0x24);
    a->us = clock_us();
    a->valid = 1;
}

static const char *bullet_label(const Attack *a, const char *label, uint64_t image) {
    (void)image;
    if (a->type == 0 && a->attacker) {
        if (remembered(heli_shooters, a->attacker)) return "Helicopter gun";
        if (remembered(npc_shooters, a->attacker)) return "Soldier bullet";
    }
    return label;
}

static void report(const char *source, int32_t amount, int32_t before, int32_t after, int32_t maximum, uint64_t caller,
                   uint64_t image, const Attack *a) {
    const int one_hit = maximum > 0 && amount >= maximum;
    printf("Damage: %s %d health %d->%d (caller 0x%llx)", source, (int)amount, (int)before, (int)after,
           (unsigned long long)(caller - image));
    if (a) {
        printf(" [attack: sender 0x%llx type %d attacker %p]", (unsigned long long)(a->caller - image), (int)a->type,
               (void *)(uintptr_t)a->attacker);
    }
    printf("\n");
    if (one_hit) {
        printf("Damage: ONE-HIT KILL: %s %d >= maximum health %d (caller 0x%llx)\n", source, (int)amount, (int)maximum,
               (unsigned long long)(caller - image));
    }
    if (after <= 0 && !one_hit) {
        printf("Damage: Nate's health reached %d: %s (caller 0x%llx)\n", (int)after, source,
               (unsigned long long)(caller - image));
    }
    fflush(stdout);
    char text[64];
    if (one_hit) snprintf(text, sizeof(text), "ONE-HIT KILL: %s -%d", source, (int)amount);
    else if (amount > 0) snprintf(text, sizeof(text), "%s -%d", source, (int)amount);
    else snprintf(text, sizeof(text), "%s", source);
    post_notice(text, one_hit || after <= 0);
}

/* TakeDamage after its stores (0x54c362): rbx = the Health object (regs[0]), r14d = the damage, eax = health before
 * minus the damage (regs[7]); the frame's return address sits three slots above the saved rbx. */
void __attribute__((ms_abi)) runtime_damage_take(uint64_t rdi, uint64_t rsi, uint64_t image, uint64_t r14,
                                                 const uint64_t *regs) {
    (void)rdi; (void)rsi;
    if (!enabled()) return;
    const uint64_t health = regs[0];
    const uint64_t caller = regs[28];
    const int32_t amount = (int32_t)r14;
    const uint64_t mine = player_health(image);
    if (health < 0x10000 || amount == 0) return;
    /* the player's attack event handler is the player's own: its health object is the player's */
    const uint64_t offset = caller - image;
    if (health != mine && offset != ATTACK_CALLER_RET) return;
    const int32_t before = (int32_t)regs[7] + amount;
    const int32_t after = *(const int32_t *)(uintptr_t)(health + 0x2c);
    const int32_t maximum = *(const int32_t *)(uintptr_t)(health + 0x30);
    Attack a = pending;
    pending.valid = 0;
    const int fresh = a.valid && clock_us() - a.us < 200000u && offset == ATTACK_CALLER_RET;
    const char *source;
    if (fresh) {
        source = bullet_label(&a, sender_label(a.caller, image, a.type), image);
    } else if (offset == ATTACK_CALLER_RET) {
        source = "Attack (sender not seen)";
    } else if (offset == 0x291745) {
        source = "Player damage (0x2916b0)";
    } else {
        source = "Unknown damage";
    }
    report(source, amount, before, after, maximum, caller, image, fresh ? &a : NULL);
}

/* SetCurrent (0x54c2b0) and SetCurrentAtTime (0x54c260) at their start: rdi the Health object, esi the new health. A
 * health set below the current one is logged (a script kill sets 0). */
static void health_set(uint64_t rdi, uint64_t rsi, uint64_t image, const uint64_t *regs, const char *how) {
    if (!enabled()) return;
    if (rdi < 0x10000 || rdi != player_health(image)) return;
    const uint64_t caller = regs[25];
    const int32_t value = (int32_t)rsi;
    const int32_t before = *(const int32_t *)(uintptr_t)(rdi + 0x2c);
    const int32_t maximum = *(const int32_t *)(uintptr_t)(rdi + 0x30);
    if (value >= before) return;
    const uint64_t offset = caller - image;
    const char *source = offset == 0x7ef944 ? "Script kill (kill-player-no-anim)"
                       : offset == 0x7f12db ? "Script kill (kill-player)"
                       : offset == 0x910126 ? "Script set-player-health"
                       : value <= 0 ? "Health set to 0" : "Health set lower";
    printf("Damage: %s %s %d->%d (caller 0x%llx)\n", how, source, (int)before, (int)value,
           (unsigned long long)offset);
    if (value <= 0) printf("Damage: Nate's health set to %d: %s (caller 0x%llx)\n", (int)value, source,
                           (unsigned long long)offset);
    if (maximum > 0 && before >= maximum && value <= 0) {
        printf("Damage: ONE-HIT KILL: %s took Nate from full health %d to %d (caller 0x%llx)\n", source, (int)before,
               (int)value, (unsigned long long)offset);
    }
    fflush(stdout);
    post_notice(source, value <= 0);
}
void __attribute__((ms_abi)) runtime_damage_set(uint64_t rdi, uint64_t rsi, uint64_t image, uint64_t r14,
                                                const uint64_t *regs) {
    (void)r14;
    health_set(rdi, rsi, image, regs, "SetCurrent");
}
void __attribute__((ms_abi)) runtime_damage_set_at(uint64_t rdi, uint64_t rsi, uint64_t image, uint64_t r14,
                                                   const uint64_t *regs) {
    (void)r14;
    health_set(rdi, rsi, image, regs, "SetCurrentAtTime");
}
