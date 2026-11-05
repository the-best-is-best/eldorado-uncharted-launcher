"""Compile the enabled cheats of one executable into cheats.bin for bb-probe --patches.

Cheats are "health" and "ammo". A patch is written only when the executable's game code is listed and the bytes at
its address are the expected ones; anything else is reported and skipped, never an error.
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
# rewards (El Dorado's "Unlock all rewards", 1.02 code): every reward in Bonuses (skins, weapons, render modes, art,
# gameplay tweaks) and every story cutscene reads as unlocked while it is on; nothing is written to the save.
# Uncharted 1 keeps each reward's status in its own record, so its checks are patched (IsUnlocked by item and by id,
# the "Unlocked N of 47" counter, usable-by-id, CanEnable and its "finish the game first" reason, the Story
# Cutscenes list). Uncharted 2 and 3 only drop "finish the game on this difficulty first" here; their debug switches
# "Give all Store Items" / "Give All Movies" (bss bytes) are kept set by run.py (BB_POKE_U2 / BB_POKE_U3).
REWARDS = {
    US['eboot.bin']: [(0x32c342, '24', 'b0'), (0x32c3d7, '24', 'b0'), (0x32c518, '19', '00'),
                      (0x32cd53, '1e', '00'), (0x32c8b1, '94', '92'), (0x32c818, '01', '00'),
                      (0x138ab7, '88', '00')],
    US['big2-ps4_Shipping.elf']: [(0xa4ca34, '01', '00')],
    US['big3-ps4_Shipping.elf']: [(0x4bd55b, '01', '00')],
}
for _code, _patches in REWARDS.items():
    PATCHES[_code]['rewards'] = _patches
# grenades (El Dorado's "Infinite grenades", 1.02 code): the player's grenade throw no longer calls the ammo use
# that takes one grenade away. Uncharted 1: weaponcontroller.cpp PostJointUpdate, the kGrenade branch, calls the use
# (dec [weapon+slot*0x30+0x440]) at 0x734a78. Uncharted 2: player-fast-grenade.cpp Release calls it
# (dec word [weapon+slot*0x20+0x620]) at 0x802273. The enemies' throws are other calls. Uncharted 3 has the
# game's own "Infinite Grenades" switch, kept set by run.py (BB_POKE_U3).
PATCHES[US['eboot.bin']]['grenades'] = (0x734a78, 'e8c319c1ff', NOP * 5)
PATCHES[US['big2-ps4_Shipping.elf']]['grenades'] = (0x802273, 'e8a87d2e00', NOP * 5)
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
    data = Path(path).read_bytes()
    table = PATCHES.get(code_hash(data))
    if table is None:
        print(f'Cheats: {Path(path).name} is not a supported version; none applied')
        return []
    elf, _header, program_headers, _segments, _missing = prepare.parse_self(data)
    writes = []
    for name in cheats:
        if name not in table:
            continue
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
