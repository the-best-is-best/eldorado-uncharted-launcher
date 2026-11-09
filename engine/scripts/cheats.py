"""Compile the enabled cheats of one executable into cheats.bin for bb-probe --patches.

Cheats are "health", "ammo", "noreload", "onehit" and the others below (and "rewards": Unlock all rewards). A patch
is written only when the executable's game code is listed and the bytes at its address are the expected ones;
anything else is reported and skipped, never an error.
Addresses are image offsets (virtual addresses of the SELF's load segments).
"""
import hashlib
from pathlib import Path
import struct

import prepare

NOP = '90'
# SHA-1 of the game code: the segments a SELF loads, not its signature header or the metadata a dumper adds at the
# end (launcher GAME_CODE). EU: the original 1.00 build (EU CUSA02343 dumps, US 1.00); US: the 1.02 build (US 1.02
# CUSA02320, EU/Russian CUSA02344).
EU = {'eboot.bin': 'cd749c2f217a842200a9867f7c8af0973c990a74',
      'big2-ps4_Shipping.elf': '1616597c9cf8b4b6d50d7cbf3aeb3677efba6587',
      'big3-ps4_Shipping.elf': '1d949b215bb036fe685511aca4f560d63dd50442'}
US = {'eboot.bin': 'fd024eaeb58c4b778613b54a9e69f6fbc8615a68',
      'big2-ps4_Shipping.elf': 'de8ce6e778f39b3c2914fd71f1df7117282f62e2',
      'big3-ps4_Shipping.elf': 'fed1f511d51613df108101b8a09397beebc70f0c'}

# game code -> cheat -> (address, original bytes, replacement)
PATCHES = {
    # health: jump to the engine's own no-damage path. ammo: the clip decrement is shared with NPC weapons, so U1/U2
    # drop the player Fire's call to it and U3 forces its player-held branch.
    EU['eboot.bin']: {'health': (0x261edb, '7535', 'eb35'),
                      'ammo': (0x71b003, 'e8c8acc2ff', NOP * 5)},
    US['eboot.bin']: {'health': (0x26244b, '7535', 'eb35'),
                      'ammo': (0x730f73, 'e8c854c1ff', NOP * 5)},
    EU['big2-ps4_Shipping.elf']: {'health': (0x35de73, '0f84bc010000', 'e9cf02000090'),
                                  'ammo': (0xa4fd8d, 'e87e8aa6ff', NOP * 5)},
    EU['big3-ps4_Shipping.elf']: {'health': (0x33f87b, '0f84ca020000', 'e96a0b000090'),
                                  'ammo': (0x46a1f9, '4c8d3dc0660501', '41b401eb729090')},
    US['big2-ps4_Shipping.elf']: {'health': (0x7f0143, '0f843c050000', 'e95f06000090'),
                                  'ammo': (0x961ac8, 'e853851800', NOP * 5)},
    US['big3-ps4_Shipping.elf']: {'health': (0x9f9295, '4180bfa7000000007436', 'e9320300009090909090'),
                                  'ammo': (0xd517ac, '4c8d257d92aa0066418b442462', '40b701e9110100009090909090')},
}
# devmode: Naughty Dog's developer mode (the debug menu, the game's own debug text). The check
# "cmp byte [m+A],0 / jne skip / mov cl,[m+B] / test cl,cl / je skip" becomes "mov byte [m+A],0 / jmp / mov byte [m+B],1 /
# jmp": the two flags are set and the developer path runs. On the 1.00 code byte for byte DeathRGH's GoldHEN "Enable
# Debug Menu" (GoldHEN offsets = these + 0x400000); on the 1.02 code the same edit of its check (another register).
DEVMODE = {
    EU['eboot.bin']: (0x2cf8b0, '4180bfe8470000000f85ac0e0000418a8f4448000084c90f849d0e0000',
                      '41c687e847000000eb04ac0e000041c6874448000001eb05849d0e0000'),
    US['eboot.bin']: (0x2cfea0, '4180bfe8470000000f85ac0e0000418a8f4448000084c90f849d0e0000',
                      '41c687e847000000eb04ac0e000041c6874448000001eb05849d0e0000'),
    EU['big2-ps4_Shipping.elf']: (0x14c4fd, '80b921480000000f85c10b00008a898c48000084c90f84b30b0000',
                                  'c6812148000000eb04c10b0000c6818c48000001eb0584b30b0000'),
    US['big2-ps4_Shipping.elf']: (0x3f8f4b, '4180bc2421480000000f85741a0000418a8c248c48000084c90f84641a0000',
                                  '41c684242148000000eb04741a000041c684248c48000001eb0584641a0000'),
    EU['big3-ps4_Shipping.elf']: (0x16218d, '80b9014c0000000f85c10b00008a89fc4b000084c90f84b30b0000',
                                  'c681014c000000eb04c10b0000c681fc4b000001eb0584b30b0000'),
    US['big3-ps4_Shipping.elf']: (0x56cb8b, '4180bc24014c0000000f85551a0000418a8c24fc4b000084c90f84451a0000',
                                  '41c68424014c000000eb04551a000041c68424fc4b000001eb0584451a0000'),
}
for _code, _patch in DEVMODE.items():
    PATCHES[_code]['devmode'] = _patch
# grenades (El Dorado's "Infinite grenades", 1.02 code): the player's grenade throw no longer calls the ammo use
# that takes one grenade away. Uncharted 1: weaponcontroller.cpp PostJointUpdate, the kGrenade branch, calls the use
# (dec [weapon+slot*0x30+0x440]) at 0x734a78. Uncharted 2: player-fast-grenade.cpp Release calls it
# (dec word [weapon+slot*0x20+0x620]) at 0x802273. The enemies' throws are other calls. Uncharted 3 has the
# game's own "Infinite Grenades" switch, kept set by run.py (BB_POKE_U3).
PATCHES[US['eboot.bin']]['grenades'] = (0x734a78, 'e8c319c1ff', NOP * 5)
PATCHES[US['big2-ps4_Shipping.elf']]['grenades'] = (0x802273, 'e8a87d2e00', NOP * 5)
# noreload (El Dorado's "No reload", Uncharted 1, 1.02 code): Uncharted 1 has no such switch. A weapon slot is
# [weapon+slot*0x30]: +0x440 the magazine, +0x444 the reserve, +0x448 the magazine size (the pickup's add at 0x344cc5
# fills +0x440 up to +0x448 for grenades, the reserve +0x444 for guns). The player Fire's only magazine use is the
# call to 0x346440 (dec [weapon+slot*0x30+0x440]) that "ammo" drops: the magazine stays full and no reload comes, the
# reserve is left alone. Uncharted 2 and 3 use their own No Reload switch (KEEP).
PATCHES[US['eboot.bin']]['noreload'] = PATCHES[US['eboot.bin']]['ammo']
# onehit (El Dorado's "One hit kills", 1.02 code), Uncharted 1 and 2 (Uncharted 3: its own switch, KEEP; Uncharted 2's
# debug "One Hit Damage" is no such switch: an int 0..200, default 60, read only by player-net-fight.cpp, the
# multiplayer melee). The hit goes where Bluepoint's difficulty tweak "Damage by Player to NPCs" (bp_ucctweaks.cpp,
# getter case 4: Ultra Easy +0x50 / Ultra Ultra Hard +0x20 of its block) is applied: an NPC's damage from an attacker
# of the player's faction. There the attacker is compared with the player itself (the game's player handle and its id
# check) and the damage becomes 100000: the NPC dies of any hit of Nate's (bullet, melee, explosion; an NPC the game
# keeps alive still does). Damage to Nate, and from his buddies, is unchanged.
# Uncharted 1, npc.cpp RespondToAttack (0x13ed0): the damage [attack+0x14] in xmm0 is scaled by the tweak when
# [attacker+0x60] == 1 (0x146f7) and handed to the NPC's damage (0x7da0 -> health 0x274e0, health float at +0x1c)
# after "mov r15b, [rbx+0x2d29]" at 0x1472e, the join of every path (r15 = attacker [attack+8]; rax, rcx free). That
# load jumps to a stub in the code segment's zero padding right after .eh_frame_hdr's table (it ends at 0x911530; the
# ultrawide stubs start 0x100 past the last non-zero byte, so they land where they did): when the attacker exists
# (r15 not null) xmm0 = 100000.0, whoever it is. El Dorado 9 Nov 2026: it was Nate's own hits only (a test of the player
# through g_playerHandle 0xaa5f78), and Elena's shots from the jet ski did not kill; neither did a test with the
# faction [attacker+0x60] == 1 of the tweak above (0x146f7). With any attacker they do, and Nate does not die of a hit.
# Uncharted 2, npc.cpp ComputeArmorDamage (0x244ef0; its int damage [rbp-0x4040] goes to the health vfunc
# [npc+0x1f0]+0x10): the faction-1 block 0x245a95..0x245b39 (cmp dword [r8+0x150], 1 / jne; the tweak's multiply)
# is rewritten in place with the player test first (handle 0x115bd20: slot, id at +8; the object's id at +0x44, as
# this function checks the attacker r8): the player's hit sets the damage to 100000 and skips the multiply; anyone
# else runs the same multiply (only the s_pInternal null assert's message call is dropped, its int 0x41 is kept).
U1_ONEHIT_STUB = '4d85ff7409b80050c347c5f96ec0448abb292d0000e9db3170ff'
PATCHES[US['eboot.bin']]['onehit'] = [
    (0x1472e, '448abb292d0000c683292d000000', 'e90dce8f00' + NOP * 2 + 'c683292d000000'),
    (0x911540, '00' * (len(U1_ONEHIT_STUB) // 2), U1_ONEHIT_STUB)]
PATCHES[US['big2-ps4_Shipping.elf']]['onehit'] = (
    0x245a95,
    '4183b850010000010f85960000004189f6c78560bfffff04000000488b1d095f4e014885db753e488b05b584320131db4885c0742e'
    '488d3d5b62c800488d356062c800488d15f46cc800488d0d8ee8ba0041b8620100004531c9ffd0488b1dc85e4e01cd41c4c1fa2ac6'
    'c5fa118558bfffff488dbbf8080000488db560bfffffe856abb000c5fa5983140a0000c5fa108d58bfffffc5f259c0c4e1fa2cc0'
    '8985c0bfffff',
    '4183b850010000010f8596000000488b057662f1004885c074204c3900751b8b056e62f100413b4044750fc785c0bfffffa0860100'
    'e96a0000004189f6c78560bfffff04000000488b1ddd5e4e014885db7502cd41c4c1fa2ac6c5fa118558bfffff488dbbf8080000'
    '488db560bfffffe866abb000c5fa5983140a0000c5fa108d58bfffffc5f259c0c4e1fa2cc08985c0bfffff' + NOP * 16)
# torch (El Dorado's "Torch light follows the torch", Uncharted 2, 1.02 code): the torch update (Flashlight Active
# 0x69a190) aims the light along the torch joint only in camera mode 9, and every frame the player light (record 0 of
# the light table 0x1157760) is re-aimed along the camera's forward vector (function 0x698b50 and a copy inlined next
# to UpdatePadLightBar, 0x3fd78d): turn the camera to face Nate and the light falls on the wall behind him. Both
# re-aims are skipped (je -> jmp) and the joint path is taken in every camera mode: the light follows the beam.
PATCHES[US['big2-ps4_Shipping.elf']]['torch'] = [(0x3fd799, '7440', 'eb40'), (0x698b5c, '7440', 'eb40'),
                                                 (0x69afc4, '0f8534010000', '90e934010000')]
# exposure<EV> (El Dorado's "Uncharted 3 exposure", 1.02 code; pavlikdcx's patch, GitHub #199: Uncharted 3 too bright
# on some RTX 30/40 PCs): the filmic exposure bias read from the render settings at [rbx+0x72c] on two paths
# (0xed9d30 / 0xed9d49) gets <EV> more before the tonemap. The first load jumps to a stub in the code segment's zero
# padding (0x1648800) that adds the bias; the second path's add of -0.5 (shared constant 0x144b3b8) reads the stub's
# own (-0.5 + EV) instead. Built per value by exposure_patch(); names "exposure-0.5", "exposure+0.25".
U3_EXPOSURE_AT, U3_EXPOSURE_CAVE = 0xed9d30, 0x1648800


def exposure_patch(name):
    """[(address, original, replacement)] for a cheat name exposure<EV> (-2 .. +1), or None."""
    try:
        bias = float(name[len('exposure'):])
    except ValueError:
        return None
    if not -2.0 <= bias <= 1.0 or abs(bias) < 0.05:
        return None
    cave = U3_EXPOSURE_CAVE - U3_EXPOSURE_AT  # from the first load
    stub = bytes.fromhex('c5fa10932c070000')                                         # vmovss xmm2, [rbx+0x72c]
    stub += bytes.fromhex('c5ea5815') + struct.pack('<i', 0x40 - (len(stub) + 8))   # vaddss xmm2, xmm2, [cave+0x40]
    stub += bytes.fromhex('c5f057c9')                                                # vxorps xmm1, xmm1, xmm1
    stub += b'\xe9' + struct.pack('<i', 12 - (cave + len(stub) + 5))                 # jmp back (first load + 12)
    stub = stub.ljust(0x40, b'\xcc') + struct.pack('<ff', bias, -0.5 + bias)
    jump = b'\xe9' + struct.pack('<i', cave - 5) + b'\x90' * 7
    second = struct.pack('<i', (cave + 0x44) - (0x21 + 8))                           # the second path's add
    return [(U3_EXPOSURE_AT, 'c5fa10932c070000c5f057c9', jump.hex()),
            (U3_EXPOSURE_CAVE, '00' * len(stub), stub.hex()),
            (U3_EXPOSURE_AT + 0x25, '5f165700', second.hex())]
# nathealth<L> (El Dorado's "Damage to Nate", 1.02 code): Nate takes damage as on difficulty L (0 Explorer, 1 Easy,
# 2 Normal, 3 Hard: the games' own order, 0..5 = Explorer, Easy, Normal, Hard, Crushing, Brutal) whatever the chosen one; the
# chosen difficulty stays for everything else (enemies, AI, saves, trophies). The damage of an NPC's shot at Nate is
# scaled by difficulty in three places, each read here as level L:
# - Bluepoint's tweaks (bp_ucctweaks.cpp; only Explorer and Brutal have values, the others read 1.0): the getter's
#   cases 2 "Damage by NPCs Multiplier", 3 "Damage by NPCs (Melee)", 5/6 "Player Health Regen Rate/Delay", 8
#   "Explosive Damage to Player" (Explorer field +0x24/+0x28/+0x30/+0x34/+0x44 of the block, Brutal +0/+4/+0xc/+0x10/
#   +0x1c). Each case's "cmp eax, 5 / jne / read Brutal's" becomes "read Explorer's" (L 0) or "return 1.0".
# - Naughty Dog's difficulty value (ApplyDifficultySetting, task.cpp: the difficulty's *<level>-difficulty-settings*
#   interpolated by the dynamic difficulty), read by a shared function whose difficulty load jumps to a stub: when the
#   return address is the NPC damage code's call, the level is L, else the game's own. U1: npc.cpp's damage to the
#   player 0x16150 calls 0x31ef00 (pow of the damage base) at 0x16200 (the weapon damage 0x15e50, which serves every
#   shooter, is left alone). U2: the NPC weapon damage 0x24fbe0 calls
#   0x4aba00 at 0x24fc50/0x24fe4c/0x24fe6e. U3: the NPC weapon damage 0x366af0 calls the difficulty object's
#   (0x16fb750) value 0x552a20 at 0x366c2b/0x366def.
# - The same functions' own Hard/Crushing/Brutal multipliers and Explorer's damage floor: their difficulty loads
#   become "mov reg, L".
# Stubs: U1 after the onehit stub, U2/U3 right after the code's last byte (the ultrawide stubs move 0x100 on).
NATE_LEVELS = 4


def _asm(at, items):
    """Bytes of items at address at: bytes, ('label', name), (op, target) for jmp/je/jne/call (rel32 / rel8 for je,
    jne), ('rip', prefix, target, after) for a rip-relative operand (disp32, then 'after' more bytes)."""
    def size(item):
        if isinstance(item, bytes):
            return len(item)
        if item[0] == 'label':
            return 0
        if item[0] in ('je', 'jne'):
            return 2
        if item[0] in ('jmp', 'call'):
            return 5
        return len(item[1]) + 4 + len(item[3])
    labels, pc = {}, at
    for item in items:
        if not isinstance(item, bytes) and item[0] == 'label':
            labels[item[1]] = pc
        pc += size(item)
    out, pc = b'', at
    for item in items:
        n = size(item)
        if isinstance(item, bytes):
            out += item
        elif item[0] in ('je', 'jne'):
            rel = labels.get(item[1], item[1]) - (pc + 2)
            if not -128 <= rel < 128:
                raise ValueError('short jump out of range')
            out += bytes([0x74 if item[0] == 'je' else 0x75]) + struct.pack('<b', rel)
        elif item[0] in ('jmp', 'call'):
            out += (b'\xe9' if item[0] == 'jmp' else b'\xe8') + struct.pack('<i', labels.get(item[1], item[1]) - (pc + 5))
        elif item[0] == 'rip':
            out += item[1] + struct.pack('<i', item[2] - (pc + n)) + item[3]
        pc += n
    return out


def _jump_to(at, stub, length):
    return (b'\xe9' + struct.pack('<i', stub - (at + 5))).ljust(length, b'\x90')


def _imm(opcode, level, length):
    return (bytes([opcode]) + struct.pack('<I', level)).ljust(length, b'\x90')


def _getter_cases(blocks, explorer_read, default_tail, level):
    """The tweak getter's case blocks [(address, original, Explorer offset)] -> patches for level."""
    patches = []
    for address, original, offset in blocks:
        length = len(original) // 2
        code = (explorer_read(offset) if level == 0 else b'') + default_tail(address + (6 if level == 0 else 0))
        patches.append((address, original, code.ljust(length, b'\x90').hex()))
    return patches


def _u1_nate(level):
    end = 0x3ad16c
    patches = _getter_cases(
        [(0x3ad0a8, '83f805756dc4c17a1006e9b5000000', 0x24), (0x3ad0b7, '83f805756ac4c17a104604e9a5000000', 0x28),
         (0x3ad0d7, '83f8057562c4c17a10460ce985000000', 0x30), (0x3ad0e7, '83f805755ec4c17a104610eb78', 0x34),
         (0x3ad101, '83f805755cc4c17a10461ceb5e', 0x44)],
        lambda offset: bytes.fromhex('c4c17a1046') + bytes([offset]),          # vmovss xmm0, [r14+offset]
        lambda at: b'\xe9' + struct.pack('<i', end - (at + 5)), level)
    stub_a, game = 0x9115a0, 0x958208                                           # the game settings, difficulty +0x4878
    load = [('rip', b'\x48\x8d\x05', game, b''), bytes.fromhex('8bb878480000')]  # lea rax, [game]; mov edi, [rax+0x4878]
    a = _asm(stub_a, [('rip', b'\x48\x8d\x05', 0x16205, b''), bytes.fromhex('48394508'), ('jne', 'orig'),
                      _imm(0xbf, level, 5), ('jmp', 0x31ef8e), ('label', 'orig')] + load + [('jmp', 0x31ef8e)])
    # Not patched: the hard-difficulty factor 0x31edf0 in the weapon damage 0x15e50. That function serves every
    # shooter, the player's shots included, and has no target in a register a stub could check (r15 is not one of
    # its registers): a first version read r15 and gave the player's own shots level L (7 Nov 2026: enemies died
    # from one shot).
    cave = a
    return patches + [
        (0x31ef81, '488d05809263008bb878480000', _jump_to(0x31ef81, stub_a, 13).hex()),
        (0x1629c, '488d05651f94008b8078480000', _imm(0xb8, level, 13).hex()),
        (stub_a, '00' * len(cave), cave.hex())]


def _u23_cases(level, blocks):
    return _getter_cases(blocks, lambda offset: bytes.fromhex('c5fa1047') + bytes([offset]),  # vmovss xmm0, [rdi+offset]
                         lambda at: b'\xc3', level)


def _u2_nate(level):
    patches = _u23_cases(level, [(0xd506cc, '83f8057551c5fa1007c3', 0x24), (0xd506d6, '83f8057551c5fa104704c3', 0x28),
                                 (0xd506ec, '83f805754fc5fa10470cc3', 0x30), (0xd506f7, '83f805754ec5fa104710c3', 0x34),
                                 (0xd5070d, '83f805754dc5fa10471cc3', 0x44)])
    stub, back = 0xfe2be0, 0x4abaf5
    items = [bytes.fromhex('488b4508')]                                         # mov rax, [rbp+8]
    for ret in (0x24fc55, 0x24fe51, 0x24fe73):
        items += [('rip', b'\x48\x8d\x0d', ret, b''), bytes.fromhex('4839c8'), ('je', 'nate')]
    items += [('rip', b'\x48\x8d\x05', 0x1059640, b''), bytes.fromhex('8bb8a4480000'), ('jmp', back),
              ('label', 'nate'), _imm(0xbf, level, 5), ('jmp', back)]
    code = _asm(stub, items)
    return patches + [
        (0x4abae8, '488d0551dbba008bb8a4480000', _jump_to(0x4abae8, stub, 13).hex()),
        (0x24feb0, '488d0d8997e0008b89a4480000', _imm(0xb9, level, 13).hex()),
        (stub, '00' * len(code), code.hex())]


def _u3_nate(level):
    patches = _u23_cases(level, [(0x12c250b, '83f8057551c5fa1007c3', 0x24), (0x12c2515, '83f8057551c5fa104704c3', 0x28),
                                 (0x12c252b, '83f805754fc5fa10470cc3', 0x30), (0x12c2536, '83f805754ec5fa104710c3', 0x34),
                                 (0x12c254c, '83f805754dc5fa10471cc3', 0x44)])
    stub, back = 0x16466d0, 0x552b39                                            # rax holds the call target: rcx only
    items = []
    for ret in (0x366c2e, 0x366df2):
        items += [('rip', b'\x48\x8d\x0d', ret, b''), bytes.fromhex('48394d08'), ('je', 'nate')]
    items += [('rip', b'\x48\x8d\x0d', 0x17b6368, b''), bytes.fromhex('8bb1484c0000'), ('jmp', back),
              ('label', 'nate'), _imm(0xbe, level, 5), ('jmp', back)]
    code = _asm(stub, items)
    return patches + [
        (0x552b2c, '488d0d353826018bb1484c0000', _jump_to(0x552b2c, stub, 13).hex()),
        (0x366e59, '488d0d08f544018b89484c0000', _imm(0xb9, level, 13).hex()),
        (0x366e7f, '488d0de2f444018b89484c0000', _imm(0xb9, level, 13).hex()),
        (0x366f60, '488d0501f444018b80484c0000', _imm(0xb8, level, 13).hex()),
        (0x366fd8, '488d0d89f344018b89484c0000', _imm(0xb9, level, 13).hex()),
        (stub, '00' * len(code), code.hex())]


for _code, _build in ((US['eboot.bin'], _u1_nate), (US['big2-ps4_Shipping.elf'], _u2_nate),
                      (US['big3-ps4_Shipping.elf'], _u3_nate)):
    for _level in range(NATE_LEVELS):
        PATCHES[_code][f'nathealth{_level}'] = _build(_level)
# text<n> (El Dorado's "Arabic" language, 1.02 code): the games load text1/ps4/<n>.common whatever the console language.
# The text loader (text.cpp, "%s/%s%i.%s" with "build/main/text1/ps4/") reads the file number from the language's
# table entry: "mov eax, esi; imul rax, rax, 0x38; lea rdx, [table]; mov r9d, [rdx+rax+0x14]" becomes
# "mov r9d, <n>" (rdx and rax are set again right after). Fan translations replace one file (Arabic: file 2).
TEXT_FILE_LOADS = {US['eboot.bin']: (0x5ca861, '89f0486bc038488d15eaccab00448b4c0214'),
                   US['big2-ps4_Shipping.elf']: (0xcdd9d1, '89f0486bc038488d153a337700448b4c0214'),
                   US['big3-ps4_Shipping.elf']: (0xf328b1, '89f0486bc038488d15daa8b900448b4c0214')}
for _code, (_address, _original) in TEXT_FILE_LOADS.items():
    for _number in range(2, 24):
        PATCHES[_code][f'text{_number}'] = (_address, _original, f'41b9{_number:02x}000000' + NOP * 12)

# Naughty Dog's debug-menu switches, kept set by the runtime (BB_KEEP_BYTES): bytes in memory the game creates, so no
# patch of the file reaches them. Uncharted 3's menu has "No Reload" and "One Hit Kills" in its cheat block (Infinite
# Ammo +0x61, Infinite Grenades +0x62, No Reload +0x63, One Hit Kills +0x164); Uncharted 2 reads no-reload from the
# byte after its Infinite Ammo switch (+0x3b; no menu item). 1.02 addresses by BilalReloaded; the EU 1.00 ones found
# the same way (the menu items' base + offset).
KEEP = {
    US['big2-ps4_Shipping.elf']: {'noreload': [0x104f84b]},
    EU['big2-ps4_Shipping.elf']: {'noreload': [0xe654bb]},
    US['big3-ps4_Shipping.elf']: {'noreload': [0x17faa93], 'onehit': [0x17fab94]},
    EU['big3-ps4_Shipping.elf']: {'noreload': [0x14c0923], 'onehit': [0x14c0a24]},
}


# Unlock all rewards (BB_UNLOCK_REWARDS=1, launcher Game > Unlock all rewards; run.py adds 'rewards' to every
# game's list). From BilalReloaded's Uncharted port (tools/probe_uncharted.py REWARD_POKES / REWARD_PATCHES,
# GPL-2.0-or-later, made for 1.02); the 1.00 sites found the same way. Nothing is written to the save: turned off,
# the Bonuses menus show the player's own progress again; treasures, medals and trophies are not touched.
#
# Uncharted 2 and 3: Naughty Dog's debug-menu switches "Give all Store Items" and "Give All Movies" (the menu is
# unreachable), kept set by the runtime: every reward and story cutscene reads as unlocked while they are set. Each
# is checked against the menu item that points at it: (offset, address of that rip-relative lea, its bytes).
REWARD_SWITCHES = {
    US['big2-ps4_Shipping.elf']: [(0x1114178, 0x3fed99, '488d05d853d100'), (0x1114179, 0x40007f, '488d05f340d100')],
    EU['big2-ps4_Shipping.elf']: [(0xeb67f0, 0x14f1a9, '488d054076d600'), (0xeb67f1, 0x14f570, '488d0d7a72d600')],
    US['big3-ps4_Shipping.elf']: [(0x17b2a94, 0x4bae0b, '488d05827c2f01'), (0x17b2a95, 0x4bb57b, '488d0513752f01')],
    EU['big3-ps4_Shipping.elf']: [(0x1429524, 0x100763, '488d15ba8d3201'), (0x1429525, 0x1008b1, '488d156d8c3201')],
}
# Code patches (address, original, replacement; one byte changes in each). Uncharted 2 and 3 let some rewards
# (tweaks, render modes) be enabled only once the game was finished on that difficulty: the reward screen's item
# info sets "needs the game finished" (+0xe) to 1 before clearing it from the save's finished-difficulty bits; it is
# set to 0. Drake's Fortune keeps each reward's status in its own record (bit 0 unlocked) and its debug switch writes
# them, so its checks are patched instead: every reward reads as unlocked, usable and counted, can be enabled
# without finishing the game first, and the Story Cutscenes list skips no chapter (the status bytes are untouched).
_U1_REWARDS = (
    # IsUnlocked(item): and al, 1 -> mov al, 1
    ('item check', 'b001803f00750d4885f674098a86880000002401', 'b001803f00750d4885f674098a8688000000b001'),
    # IsUnlocked(category, id): the same
    ('id check', '75134d85e4740c418a8424880000002401eb02', '75134d85e4740c418a842488000000b001eb02'),
    # the "Unlocked N of 47" counter: je skip -> je +0
    ('counter', '4c89f275154885c07422f68088000000017419', '4c89f275154885c07422f68088000000017400'),
    # usable-by-id check: je not -> je +0
    ('usable by id', '41803e00750af684088800000001741e488d55d4', '41803e00750af6840888000000017400488d55d4'),
    # CanEnable: test [item+0x88], 1; sete dl (dl = locked) -> setb dl (test clears CF)
    ('enable check', '41f68688000000010f94c24584ff0f95c184c0', '41f68688000000010f92c24584ff0f95c184c0'),
    # CanEnable's "finish the game on this difficulty first": mov r13b, 1 -> mov r13b, 0
    ('finished first', '448bb87848000041b5014183ff067338', '448bb87848000041b5004183ff067338'),
    # Story Cutscenes list: cmp [node+0x50], 0; js skip (chapter not reached) -> js +0
    ('story cutscenes', '488b7840837f50000f88880000004c8b4210', '488b7840837f50000f88000000004c8b4210'),
)
REWARD_PATCHES = {
    US['eboot.bin']: [(label, address, original, replacement) for address, (label, original, replacement) in
                      zip((0x32c330, 0x32c3c8, 0x32c506, 0x32cd44, 0x32c8a8, 0x32c80f, 0x138aad), _U1_REWARDS)],
    EU['eboot.bin']: [(label, address, original, replacement) for address, (label, original, replacement) in
                      zip((0x32bbb0, 0x32bc48, 0x32bd86, 0x32c5c4, 0x32c128, 0x32c08f, 0x13882d), _U1_REWARDS)],
    US['big2-ps4_Shipping.elf']: [('finished first', 0xa4ca2f, '7441c6430e01833d401fa800', '7441c6430e00833d401fa800')],
    EU['big2-ps4_Shipping.elf']: [('finished first', 0x430484, '753641c6450e01e8304bd9ff', '753641c6450e00e8304bd9ff')],
    US['big3-ps4_Shipping.elf']: [('finished first', 0x4bd550, '74054c39f0725c41c6450e01488d05',
                                   '74054c39f0725c41c6450e00488d05')],
    EU['big3-ps4_Shipping.elf']: [('finished first', 0x101f65, '754541c6450e01488d3d65e02f01',
                                   '754541c6450e00488d3d65e02f01')],
}


def reward_switches(data, code):
    """Offsets of the 'give all' switches of this build whose menu items point at them; the rest are reported."""
    switches = REWARD_SWITCHES.get(code, [])
    if not switches:
        return []
    elf, _header, program_headers, _segments, _missing = prepare.parse_self(data)
    offsets = []
    for offset, lea, encoding in switches:
        encoding = bytes.fromhex(encoding)
        target = lea + len(encoding) + struct.unpack_from('<i', encoding, 3)[0]
        if image_bytes(elf, program_headers, lea, len(encoding)) != encoding or target != offset:
            print(f'Unlock all rewards: switch {offset:#x} skipped, unexpected code at {lea:#x}')
            continue
        offsets.append(offset)
    return offsets


def keep_bytes(path, cheats):
    """BB_KEEP_BYTES ("offset=1,...") for the enabled switch cheats of one executable; '' when none applies."""
    if not any(c in ('noreload', 'onehit', 'rewards') for c in cheats):
        return ''
    try:
        data, code = executable(path)
        table = KEEP.get(code, {})
        rewards = reward_switches(data, code) if 'rewards' in cheats else []
    except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
        print(f'Cheats: switches not kept ({error})')
        return ''
    keep = []
    for name in cheats:
        for offset in table.get(name, []):
            keep.append(f'{offset:x}=1')
            print(f'Cheats: {name} on')
    if rewards:
        keep += [f'{offset:x}=1' for offset in rewards]
        print(f'Unlock all rewards: {len(rewards)} give-all switches kept set')
    return ','.join(keep)


def executable(path):
    """(bytes, code hash) of an executable, read once per run of this module for the same file and time
    (El Dorado: compile_cheats and keep_bytes each read and hashed it again)."""
    path = Path(path)
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if _executable_memo.get('key') != key:
        data = path.read_bytes()
        _executable_memo.update(key=key, value=(data, code_hash(data)))
    return _executable_memo['value']


_executable_memo = {}


def code_hash(data):
    """SHA-1 of a SELF's loaded segments, or of the whole file when it is not a SELF."""
    digest = hashlib.sha1()
    if data[:4] == b'\x4f\x15\x3d\x1d' and len(data) >= 0x20:
        count, = struct.unpack_from('<H', data, 0x18)
        for i in range(count):
            props, offset, size, _memsz = struct.unpack_from('<QQQQ', data, 0x20 + 32 * i)
            if props & 0x800:   # a segment with data in the file
                digest.update(data[offset:offset + size])
    else:
        digest.update(data)
    return digest.hexdigest()


def image_bytes(elf, program_headers, address, size):
    for p in program_headers:
        if p['type'] in (1, 0x61000010) and p['vaddr'] <= address and address + size <= p['vaddr'] + p['filesz']:
            start = p['offset'] + address - p['vaddr']
            return bytes(elf[start:start + size])
    return None


def compile_cheats(path, cheats):
    """[(address, replacement bytes)] for the enabled cheats; reasons go to stdout."""
    data, code = executable(path)
    table = PATCHES.get(code)
    if table is None:
        print(f'Cheats: {Path(path).name} is not a supported version; none applied')
        if 'rewards' in cheats:
            print(f'Unlock all rewards: {Path(path).name} is not a supported version; not applied')
        return []
    elf, _header, program_headers, _segments, _missing = prepare.parse_self(data)
    writes = []
    if 'rewards' in cheats:
        applied = []
        for label, address, original, replacement in REWARD_PATCHES.get(code, []):
            original, replacement = bytes.fromhex(original), bytes.fromhex(replacement)
            if image_bytes(elf, program_headers, address, len(original)) != original:
                print(f'Unlock all rewards: {label} skipped, unexpected code at {address:#x}')
                continue
            writes.append((address, replacement))
            applied.append(label)
        if applied:
            print(f'Unlock all rewards: {", ".join(applied)} patched')
    for name in cheats:
        if name.startswith('exposure') and table is PATCHES[US['big3-ps4_Shipping.elf']]:
            entries = exposure_patch(name)
            if entries is None:
                continue
        elif name not in table:
            continue
        else:
            entries = table[name] if isinstance(table[name], list) else [table[name]]
        found = []
        for address, original, replacement in entries:
            original, replacement = bytes.fromhex(original), bytes.fromhex(replacement)
            if image_bytes(elf, program_headers, address, len(original)) != original:
                print(f'Cheats: {name} skipped, unexpected code at {address:#x}')
                found = None
                break
            found.append((address, replacement))
        if found is None:
            continue
        writes.extend(found)
        print(f'Cheats: {name} on')
    return writes


def write_patch_file(out, writes):
    with open(out, 'wb') as f:
        f.write(b'BBPATCH2' + struct.pack('<QQ', 0, len(writes)))
        for address, data in writes:
            f.write(struct.pack('<QQ', address, len(data)) + data)


def build(path, out_dir, cheats):
    """Path of out_dir/cheats.bin for the enabled cheats, or None when nothing applies."""
    out = Path(out_dir) / 'cheats.bin'
    try:
        out.unlink(missing_ok=True)
        writes = compile_cheats(path, cheats) if cheats else []
        if writes:
            write_patch_file(out, writes)
            return out
    except (OSError, ValueError, KeyError, IndexError) as error:
        print(f'Cheats: not applied ({error})')
    return None
