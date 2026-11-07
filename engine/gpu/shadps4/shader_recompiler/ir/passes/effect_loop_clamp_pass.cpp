// SPDX-FileCopyrightText: Copyright 2026 engine
// SPDX-License-Identifier: GPL-2.0-or-later

#include <cstdio>
#include <cstdlib>
#include <optional>
#include <string>
#include <vector>

#include "shader_recompiler/info.h"
#include "shader_recompiler/ir/basic_block.h"
#include "shader_recompiler/ir/ir_emitter.h"
#include "shader_recompiler/ir/passes/ir_passes.h"
#include "shader_recompiler/ir/program.h"

namespace Shader::Optimization {

// bbport (from BilalReloaded's port 0.8.0, U3 chapter 2 device lost): Naughty Dog's effect and
// crowd skinning compute shaders (cs 8f067540, 7d7e7206, 0c936dd6, all three games) run, per
// vertex, a loop whose trip count is read from buffer 0 (u32 count, u32 offset per vertex):
//     entry = buffer0[vertex]; for (i = 0; i < entry.count; ++i) { ...buffer4[entry.offset + i]... }
// A count that is not a small influence count (stale or garbage data) runs the loop billions of
// times: the GPU hangs and Windows resets it ("Device lost"). The loop's bound is clamped to
// MaxEffectLoopCount, far above any real count. BB_EFFECT_LOOP_CLAMP=0: off (the shaders as
// before; their cache names change with it, see vk_pipeline_serialization.cpp BinaryName).
//
// Pixel shader 689d1af9 (all three games; a soft-shadow filter that samples a depth map along a
// line of taps) has the same shape with a single u32 count: `for (i = 0; i < buffer0[10]; ++i)`.
// An Intel Arc A750 lost the device in it at the U3 chapter 2 museum exit (GPU breadcrumbs,
// 2026-11-03). Its count is a tap count, so the clamp is lower: MaxShadowTapCount per pixel.
constexpr u32 MaxEffectLoopCount = 4096;
constexpr u32 MaxShadowTapCount = 256;
constexpr u64 ShadowTapShader = 0x689d1af9;

// bbport (from BilalReloaded's port 0.8.4, U3 chapter 2 device lost as young Sully streams in):
// the cloth solvers 1c957b01 and 809864d3 (Sully's shirt; 1024-thread groups, 2 KiB LDS) are the
// last new GPU work before every loss on NVIDIA and Intel. Every loop of theirs runs to a count
// read from memory (constant buffers #1/#2, per-vertex counts in buffers): each loop compare of
// such a count with its counter uses min(count, cap), the cap far above any real count
// (ClothBoundCap). A garbage count costs a frame of wrong cloth instead of a reset GPU.
// BB_SAFE_CLOTH=0: off. BB_SAFE_CLOTH_CAP=<n>: one cap for every count. Test:
// BB_TEST_CLOTH_BOUND=<n> raises every count to at least n first (a garbage count). Their cache
// names change with these (SafeClothCacheTag, vk_pipeline_serialization.cpp BinaryName).
// (The out-of-range LDS reads of the same shaders are SharedMemoryBoundsPass.)
constexpr u64 ClothSolverA = 0x1c957b01;
constexpr u64 ClothSolverB = 0x809864d3;

static bool IsClothSolver(u64 pgm_hash) {
    return pgm_hash == ClothSolverA || pgm_hash == ClothSolverB;
}

static u32 EnvU32(const char* name) {
    const char* env = std::getenv(name);
    return env ? static_cast<u32>(std::strtoul(env, nullptr, 0)) : 0u;
}

static u32 TestClothBound() {
    static const u32 value = EnvU32("BB_TEST_CLOTH_BOUND");
    return value;
}

static u32 ForcedClothCap() {
    static const u32 value = EnvU32("BB_SAFE_CLOTH_CAP");
    return value;
}

bool SafeCloth(u64 pgm_hash) {
    static const bool enabled = [] {
        const char* env = std::getenv("BB_SAFE_CLOTH");
        return !(env && env[0] == '0');
    }();
    return enabled && IsClothSolver(pgm_hash);
}

std::string SafeClothCacheTag(u64 pgm_hash) {
    if (!IsClothSolver(pgm_hash)) {
        return {};
    }
    // sc3: Bilal's measured caps, one bound per compare signedness (sc0: caps off).
    std::string tag = SafeCloth(pgm_hash) ? "sc3" : "sc0";
    if (const u32 cap = ForcedClothCap(); cap && SafeCloth(pgm_hash)) {
        tag += "_cap" + std::to_string(cap);
    }
    if (const u32 bound = TestClothBound()) {
        tag += "_tb" + std::to_string(bound);
    }
    return tag;
}

/// The cap of a loop count: constant-buffer words by (binding, dword), per-vertex counts by kind.
/// Real counts (Bilal, 6 Nov, young Sully in the chapter 2 square): cb1[160] substeps 2-9,
/// cb1[163] 3, cb1[164] convergence iterations 128, cb1[165] 1-6, cb2[3] 252-260, cb2[22] 7-8,
/// per-vertex counts 7-9. The caps are 4-16 times those, and all of them at once keep a dispatch
/// far below the 2 s at which Windows resets the GPU.
static u32 ClothBoundCap(const IR::Inst& count) {
    if (const u32 forced = ForcedClothCap()) {
        return forced;
    }
    if (count.GetOpcode() == IR::Opcode::ReadConstBuffer && count.Arg(0).IsImmediate() &&
        count.Arg(1).IsImmediate()) {
        const u32 binding = count.Arg(0).U32(), dword = count.Arg(1).U32();
        if (binding == 1) {
            switch (dword) {
            case 160: // substeps this frame
                return 32;
            case 163:
                return 32;
            case 164: // convergence iterations
                return 512;
            case 165:
                return 64;
            default:
                break;
            }
        } else if (binding == 2) {
            switch (dword) {
            case 3:
                return 4096;
            case 22:
                return 128;
            default:
                break;
            }
        }
        return 1024;
    }
    return 128; // per-vertex counts (buffer loads)
}

static bool IsLoopCounter(const IR::Value& value) {
    if (value.IsPhi()) {
        return true;
    }
    // `i + 1 < count` forms: an add of an immediate to a phi.
    const IR::Inst* inst = value.TryInst();
    return inst && inst->GetOpcode() == IR::Opcode::IAdd32 &&
           ((inst->Arg(0).IsPhi() && inst->Arg(1).IsImmediate()) ||
            (inst->Arg(1).IsPhi() && inst->Arg(0).IsImmediate()));
}

static bool IsSignedCompare(IR::Opcode op) {
    switch (op) {
    case IR::Opcode::SLessThan32:
    case IR::Opcode::SLessThanEqual32:
    case IR::Opcode::SGreaterThan32:
    case IR::Opcode::SGreaterThanEqual32:
        return true;
    default:
        return false;
    }
}

bool EffectLoopClamp(u64 pgm_hash) {
    static const bool enabled = [] {
        const char* env = std::getenv("BB_EFFECT_LOOP_CLAMP");
        return !(env && env[0] == '0');
    }();
    return enabled &&
           (pgm_hash == 0x8f067540 || pgm_hash == 0x7d7e7206 || pgm_hash == 0x0c936dd6 ||
            pgm_hash == ShadowTapShader);
}

static bool IsIntCompare(IR::Opcode op) {
    switch (op) {
    case IR::Opcode::ULessThan32:
    case IR::Opcode::ULessThanEqual32:
    case IR::Opcode::UGreaterThan32:
    case IR::Opcode::UGreaterThanEqual32:
    case IR::Opcode::SLessThan32:
    case IR::Opcode::SLessThanEqual32:
    case IR::Opcode::SGreaterThan32:
    case IR::Opcode::SGreaterThanEqual32:
    case IR::Opcode::IEqual32:
    case IR::Opcode::INotEqual32:
        return true;
    default:
        return false;
    }
}

/// Clamps the loop bounds that use `count` directly. `any_order`: every integer compare of count
/// against a loop counter (a phi), in either operand order; otherwise only `i < count`.
static u32 ClampBounds(IR::Inst* count, u32 max_count, bool any_order = false) {
    std::vector<IR::Use> bounds;
    for (const IR::Use& use : count->Uses()) {
        const IR::Opcode op = use.user->GetOpcode();
        if (op == IR::Opcode::ULessThan32 && use.operand == 1) {
            bounds.push_back(use);
        } else if (any_order && IsIntCompare(op)) {
            const IR::Value other = use.user->Arg(use.operand == 0 ? 1 : 0);
            if (other.IsPhi()) {
                bounds.push_back(use);
            }
        }
    }
    if (bounds.empty()) {
        return 0;
    }
    IR::Block* const parent = count->GetParent();
    IR::IREmitter ir{*parent, std::next(IR::Block::InstructionList::s_iterator_to(*count))};
    const IR::U32 bound = ir.IMin(IR::U32{count}, ir.Imm32(max_count), false);
    for (const IR::Use& use : bounds) {
        use.user->SetArg(use.operand, bound);
    }
    return 1;
}

/// The cloth solvers: every loop compare of a count read from memory (a constant-buffer word, a
/// u32 buffer load, or a component of a u32x2 buffer load) with a loop counter compares with
/// min(count, ClothBoundCap) instead (signed min for signed compares). Returns the counts patched.
static u32 ClampClothLoops(IR::Program& program, bool clamp) {
    u32 patched = 0;
    for (IR::Block* const block : program.blocks) {
        for (IR::Inst& inst : block->Instructions()) {
            const IR::Opcode op = inst.GetOpcode();
            bool count = op == IR::Opcode::ReadConstBuffer || op == IR::Opcode::LoadBufferU32;
            if (op == IR::Opcode::CompositeExtractU32x2) {
                const IR::Inst* source = inst.Arg(0).TryInst();
                count = source && source->GetOpcode() == IR::Opcode::LoadBufferU32x2;
            }
            if (!count) {
                continue;
            }
            std::vector<IR::Use> compares;
            for (const IR::Use& use : inst.Uses()) {
                if (!IsIntCompare(use.user->GetOpcode()) ||
                    !IsLoopCounter(use.user->Arg(use.operand == 0 ? 1 : 0))) {
                    continue;
                }
                compares.push_back(use);
            }
            if (compares.empty()) {
                continue;
            }
            // One bound per signedness: a signed min would let a count with bit 31 set through
            // to an unsigned or equality compare.
            IR::IREmitter ir{*inst.GetParent(),
                             std::next(IR::Block::InstructionList::s_iterator_to(inst))};
            std::optional<IR::U32> bounds[2];
            const auto bound_for = [&](bool is_signed) -> IR::U32 {
                auto& bound = bounds[is_signed ? 1 : 0];
                if (!bound) {
                    IR::U32 value{&inst};
                    if (const u32 test = TestClothBound()) {
                        value = ir.IMax(value, ir.Imm32(test), is_signed);
                    }
                    if (clamp) {
                        value = ir.IMin(value, ir.Imm32(ClothBoundCap(inst)), is_signed);
                    }
                    bound = value;
                }
                return *bound;
            };
            for (const IR::Use& use : compares) {
                use.user->SetArg(use.operand, bound_for(IsSignedCompare(use.user->GetOpcode())));
            }
            ++patched;
        }
    }
    return patched;
}

void EffectLoopClampPass(IR::Program& program) {
    const u64 hash = program.info.pgm_hash;
    if (IsClothSolver(hash)) {
        const bool clamp = SafeCloth(hash);
        if (!clamp && TestClothBound() == 0) {
            return;
        }
        const u32 patched = ClampClothLoops(program, clamp);
        static u32 cloth_reports = 0;
        if (cloth_reports < 8) {
            ++cloth_reports;
            std::printf("GPU: cloth solver %#llx: %u loop count(s) %s%s (BB_SAFE_CLOTH)\n",
                        static_cast<unsigned long long>(hash), patched,
                        clamp ? "capped" : "NOT capped",
                        TestClothBound() ? " [test count forced]" : "");
            std::fflush(stdout);
        }
        return;
    }
    if (!EffectLoopClamp(hash)) {
        return;
    }
    u32 patched = 0;
    if (hash == ShadowTapShader) {
        for (IR::Block* const block : program.blocks) {
            for (IR::Inst& inst : block->Instructions()) {
                // The tap count is a scalar constant-buffer read (s_buffer_load_dword).
                const IR::Opcode op = inst.GetOpcode();
                if (op == IR::Opcode::ReadConstBuffer || op == IR::Opcode::LoadBufferU32) {
                    patched += ClampBounds(&inst, MaxShadowTapCount, true);
                }
            }
        }
    }
    for (IR::Block* const block : program.blocks) {
        for (IR::Inst& inst : block->Instructions()) {
            if (inst.GetOpcode() != IR::Opcode::LoadBufferU32x2) {
                continue;
            }
            const IR::Value handle = inst.Arg(0);
            if (!handle.IsImmediate() || handle.U32() != 0) {
                continue;
            }
            const std::vector<IR::Use> loads(inst.Uses().begin(), inst.Uses().end());
            for (const IR::Use& load_use : loads) {
                IR::Inst* const count = load_use.user;
                if (count->GetOpcode() != IR::Opcode::CompositeExtractU32x2 ||
                    !count->Arg(1).IsImmediate() || count->Arg(1).U32() != 0) {
                    continue;
                }
                // Only the loop bound: `i < count`.
                patched += ClampBounds(count, MaxEffectLoopCount);
            }
        }
    }
    static u32 reports = 0;
    static u32 shadow_reports = 0; // its own count: the compute shaders' variants fill the first
    u32& count = hash == ShadowTapShader ? shadow_reports : reports;
    if (count < 8) {
        ++count;
        std::printf("GPU: effect shader %#llx: loop bound clamped to %u in %u place(s) "
                    "(BB_EFFECT_LOOP_CLAMP)\n",
                    static_cast<unsigned long long>(hash),
                    hash == ShadowTapShader ? MaxShadowTapCount : MaxEffectLoopCount, patched);
        std::fflush(stdout);
    }
}

} // namespace Shader::Optimization
