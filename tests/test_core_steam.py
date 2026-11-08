# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""core/steam.py on temporary folders only: Steam's real files are never read or written here.
Run: python tests/test_core_steam.py (or pytest)."""
import binascii
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import steam  # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None

GAMES = [("u1", "Uncharted: Drake's Fortune"), ("u2", "Uncharted 2: Among Thieves"),
         ("u3", "Uncharted 3: Drake's Deception")]
ALL_NAMES = (steam.COLLECTION_NAME,) + tuple(name for _, name in GAMES)


def text(key: bytes, value: bytes) -> bytes:
    return b"\x01" + key + b"\0" + value + b"\0"


def number(key: bytes, value: int) -> bytes:
    return b"\x02" + key + b"\0" + struct.pack("<I", value)


def table(key: bytes, *body: bytes) -> bytes:
    return b"\x00" + key + b"\0" + b"".join(body) + b"\x08"


# Two shortcuts as Steam writes them, plus fields Steam rarely uses (a float, a 64-bit number), a lower-case key
# from older Steam versions and a name that is not UTF-8: all must survive byte for byte.
OTHER_A = table(b"0", number(b"appid", 0x9ABCDEF0), text(b"AppName", b"Other Game"),
                text(b"Exe", b'"C:\\Games\\other.exe"'), text(b"StartDir", b'"C:\\Games\\"'),
                text(b"LaunchOptions", b"-windowed"), number(b"LastPlayTime", 1700000000),
                table(b"tags", text(b"0", b"favorite"), text(b"1", b"Shooters")))
OTHER_B = table(b"1", text(b"appname", b"Caf\xe9 \xff"), text(b"exe", b'"D:\\Emu\\emu.exe"'),
                b"\x03ratio\0" + struct.pack("<f", 1.5), b"\x07big\0" + struct.pack("<Q", 2 ** 40 + 7), table(b"tags"))
STEAM_FILE = table(b"shortcuts", OTHER_A, OTHER_B) + b"\x08"
ODD_NAME = "Caf\udce9 \udcff"


def entries(file: Path) -> list:
    return [node.value for node in steam.shortcuts_of(steam.parse_vdf(file.read_bytes()))]


def by_name(file: Path) -> dict:
    return {steam.get(entry, "AppName"): entry for entry in entries(file)}


class VdfTests(unittest.TestCase):
    def test_round_trip_is_byte_exact(self) -> None:
        tree = steam.parse_vdf(STEAM_FILE)
        self.assertEqual(steam.dump_vdf(tree), STEAM_FILE)
        shortcuts = steam.shortcuts_of(tree)
        self.assertEqual(steam.get(shortcuts[0].value, "AppName"), "Other Game")
        self.assertEqual(steam.get(shortcuts[1].value, "Exe"), '"D:\\Emu\\emu.exe"')

    def test_empty_file_steam_writes(self) -> None:
        empty = b"\x00shortcuts\x00\x08\x08"
        self.assertEqual(steam.parse_vdf(empty), [steam.Node(steam.MAP, "shortcuts", [])])
        self.assertEqual(steam.dump_vdf(steam.parse_vdf(empty)), empty)

    def test_truncated_or_unknown_data_is_refused(self) -> None:
        with self.assertRaises((ValueError, IndexError)):
            steam.parse_vdf(STEAM_FILE[:-5])
        with self.assertRaises(ValueError):
            steam.parse_vdf(b"\x00shortcuts\x00\x09x\x00\x08\x08")

    def test_app_id_is_the_crc_of_exe_and_name_with_the_top_bit(self) -> None:
        exe = '"C:\\Uncharted\\Uncharted Launcher.exe"'
        expected = binascii.crc32((exe + steam.COLLECTION_NAME).encode()) | 0x80000000
        self.assertEqual(steam.app_id(exe, steam.COLLECTION_NAME), expected)
        self.assertGreaterEqual(expected, 0x80000000)


class TempSteam(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="steam-test-"))
        self.addCleanup(shutil.rmtree, self.temp, True)
        # Nothing here may find the real Steam.
        patch = mock.patch.object(steam, "steam_roots", side_effect=AssertionError("real Steam looked up"))
        patch.start()
        self.addCleanup(patch.stop)
        self.port = self.temp / "Uncharted"
        (self.port / "launcher").mkdir(parents=True)
        self.starter = self.port / "Uncharted Launcher.exe"
        self.starter.write_bytes(b"MZ")
        self.script = self.port / "launcher" / "main.py"
        self.icon = str(self.port / "launcher" / "ui" / "assets" / "eldorado.ico")
        self.account = self.temp / "Steam" / "userdata" / "12345"
        (self.account / "config").mkdir(parents=True)
        self.file = self.account / "config" / "shortcuts.vdf"
        self.file.write_bytes(STEAM_FILE)

    def targets(self, games=None, starter=None) -> list:
        return steam.targets(self.port, starter or self.starter, Path(sys.executable), self.script, games)

    def add(self, games=None, accounts=None, game_dir=None, starter=None) -> list:
        return steam.add_to_steam(self.targets(games, starter), self.icon, game_dir,
                                  accounts or [(self.account, "Tester")], ALL_NAMES)

    def assert_others_intact(self) -> None:
        tree = steam.parse_vdf(self.file.read_bytes())
        others = [node for node in steam.shortcuts_of(tree)
                  if steam.get(node.value, "AppName") in ("Other Game", ODD_NAME)]
        self.assertEqual(len(others), 2)
        # Steam's own bytes (the slot numbers stay 0 and 1).
        self.assertEqual(steam.dump_vdf(others)[:-1], OTHER_A + OTHER_B)


class AddTests(TempSteam):
    def test_adds_the_collection_and_keeps_every_other_shortcut(self) -> None:
        (result,) = self.add()
        self.assertEqual((result.added, result.updated, result.removed), (1, 0, 0))
        self.assert_others_intact()
        ours = by_name(self.file)[steam.COLLECTION_NAME]
        exe = f'"{self.starter}"'
        self.assertEqual(steam.get(ours, "Exe"), exe)
        self.assertEqual(steam.get(ours, "StartDir"), f'"{self.port}"')
        self.assertEqual(steam.get(ours, "LaunchOptions"), "")
        self.assertEqual(steam.get(ours, "icon"), self.icon)
        self.assertEqual(steam.get(ours, "appid"), steam.app_id(exe, steam.COLLECTION_NAME))
        self.assertEqual([node.key for node in steam.shortcuts_of(steam.parse_vdf(self.file.read_bytes()))],
                         ["0", "1", "2"])
        self.assertEqual(result.backup.read_bytes(), STEAM_FILE)
        self.assertTrue(result.backup.name.startswith("shortcuts.vdf."))

    def test_adding_again_updates_in_place_and_keeps_the_players_fields(self) -> None:
        self.add()
        tree = steam.parse_vdf(self.file.read_bytes())
        ours = steam.shortcuts_of(tree)[2].value
        steam.put(ours, "LastPlayTime", steam.INT32, 1234)  # as Steam would after playing
        steam.put(ours, "tags", steam.MAP, [steam.Node(steam.STRING, "0", "Uncharted")])
        self.file.write_bytes(steam.dump_vdf(tree))
        (result,) = self.add()
        self.assertEqual((result.added, result.updated, result.removed), (0, 1, 0))
        self.assertEqual(len(entries(self.file)), 3)
        ours = by_name(self.file)[steam.COLLECTION_NAME]
        self.assertEqual(steam.get(ours, "LastPlayTime"), 1234)
        self.assertEqual(steam.get(ours, "tags"), [steam.Node(steam.STRING, "0", "Uncharted")])
        self.assert_others_intact()

    def test_switching_between_one_entry_and_one_per_game(self) -> None:
        self.add()
        (result,) = self.add(GAMES)
        self.assertEqual((result.added, result.removed), (3, 1))
        names = by_name(self.file)
        self.assertNotIn(steam.COLLECTION_NAME, names)
        for key, name in GAMES:
            self.assertEqual(steam.get(names[name], "LaunchOptions"), f"--play {key}")
        self.assertEqual(len(set(result.ids)), 3)
        self.assert_others_intact()
        (result,) = self.add()
        self.assertEqual((result.added, result.removed), (1, 3))
        self.assertEqual(sorted(by_name(self.file)), sorted(["Other Game", ODD_NAME, steam.COLLECTION_NAME]))
        self.assert_others_intact()

    def test_from_source_the_script_is_the_launch_option(self) -> None:
        missing = self.port / "no starter.exe"
        self.add(GAMES[:1], starter=missing)
        ours = by_name(self.file)[GAMES[0][1]]
        self.assertEqual(steam.get(ours, "LaunchOptions"), f'"{self.script}" --play u1')
        self.assertTrue(steam.get(ours, "Exe").lower().endswith(('pythonw.exe"', 'python.exe"')))

    def test_another_python_program_with_the_same_python_is_left_alone(self) -> None:
        missing = self.port / "no starter.exe"
        exe = self.targets(starter=missing)[0].exe
        tree = steam.parse_vdf(self.file.read_bytes())
        tool = steam.Target("Tool", exe, '"C:\\"', '"C:\\tool.pyw"')
        steam.shortcuts_of(tree).append(steam.Node(steam.MAP, "2", steam.new_entry(tool, "")))
        self.file.write_bytes(steam.dump_vdf(tree))
        self.add(starter=missing)
        self.add(GAMES, starter=missing)
        self.assertEqual(steam.get(by_name(self.file)["Tool"], "LaunchOptions"), '"C:\\tool.pyw"')

    def test_an_entry_from_a_moved_port_is_pointed_at_the_new_folder(self) -> None:
        old = steam.Target(steam.COLLECTION_NAME, '"E:\\Old\\Uncharted Launcher.exe"', '"E:\\Old"', "")
        tree = steam.parse_vdf(self.file.read_bytes())
        steam.shortcuts_of(tree).append(steam.Node(steam.MAP, "2", steam.new_entry(old, "")))
        self.file.write_bytes(steam.dump_vdf(tree))
        (result,) = self.add()
        self.assertEqual((result.added, result.updated), (0, 1))
        self.assertEqual(steam.get(by_name(self.file)[steam.COLLECTION_NAME], "Exe"), f'"{self.starter}"')

    def test_a_missing_file_is_made(self) -> None:
        self.file.unlink()
        (result,) = self.add()
        self.assertIsNone(result.backup)
        self.assertEqual(list(by_name(self.file)), [steam.COLLECTION_NAME])

    def test_an_unreadable_file_stops_before_any_account_is_written(self) -> None:
        second = self.temp / "Steam" / "userdata" / "999"
        (second / "config").mkdir(parents=True)
        (second / "config" / "shortcuts.vdf").write_bytes(STEAM_FILE[:-7])
        with self.assertRaises(steam.SteamError) as caught:
            self.add(accounts=[(self.account, "A"), (second, "B")])
        self.assertEqual(caught.exception.kind, "bad_file")
        self.assertEqual(self.file.read_bytes(), STEAM_FILE)
        self.assertEqual(list(self.file.parent.glob("*" + steam.BACKUP_SUFFIX)), [])

    def test_every_account_gets_it(self) -> None:
        second = self.temp / "Steam" / "userdata" / "999"
        (second / "config").mkdir(parents=True)
        results = self.add(accounts=[(self.account, "A"), (second, "B")])
        self.assertEqual(len(results), 2)
        self.assertEqual(list(by_name(second / "config" / "shortcuts.vdf")), [steam.COLLECTION_NAME])

    def test_no_steam(self) -> None:
        with self.assertRaises(steam.SteamError) as caught:
            steam.add_to_steam(self.targets(), self.icon, None, [], ALL_NAMES)
        self.assertEqual(caught.exception.kind, "no_steam")

    def test_only_the_newest_backups_are_kept(self) -> None:
        for _ in range(steam.KEEP_BACKUPS + 3):
            self.add()
        self.assertEqual(len(list(self.file.parent.glob("*" + steam.BACKUP_SUFFIX))), steam.KEEP_BACKUPS)


class AccountTests(TempSteam):
    def test_accounts_and_their_names(self) -> None:
        steam_dir = self.temp / "Steam"
        (steam_dir / "userdata" / "0").mkdir()
        (steam_dir / "userdata" / "anonymous").mkdir()
        (steam_dir / "config").mkdir()
        (steam_dir / "config" / "loginusers.vdf").write_text(
            '"users"\n{\n\t"76561197960278073"\n\t{\n\t\t"AccountName"\t\t"nate"\n'
            '\t\t"PersonaName"\t\t"Nathan"\n\t}\n}\n', encoding="utf-8")
        found = steam.find_accounts([steam_dir, steam_dir])
        self.assertEqual([(folder.name, name) for folder, name in found], [("12345", "Nathan")])
        self.assertEqual(steam.find_accounts([self.temp / "nothing"]), [])


@unittest.skipIf(Image is None, "Pillow is needed for the pictures")
class PictureTests(TempSteam):
    def setUp(self) -> None:
        super().setUp()
        self.game = self.temp / "game"
        (self.game / "sce_sys").mkdir(parents=True)
        Image.new("RGB", (1920, 1080), (220, 205, 180)).save(self.game / "sce_sys" / "pic1.png")
        cover = Image.new("RGB", (512, 512), (225, 210, 185))
        cover.paste((30, 20, 10), (60, 270, 450, 310))  # the title's dark letters
        cover.save(self.game / "sce_sys" / "icon0.png")

    def test_pictures_from_the_game_files(self) -> None:
        pictures = steam.make_pictures(self.game)
        self.assertEqual(pictures["p"].size, steam.TALL)
        self.assertEqual(pictures[""].size, steam.WIDE)
        self.assertEqual(pictures["_hero"].size, steam.HERO)
        logo = pictures["_logo"]
        self.assertEqual((logo.mode, logo.width), ("RGBA", steam.LOGO_WIDTH))
        self.assertEqual(logo.getpixel((logo.width // 2, logo.height // 2))[3], 255)

    def test_written_per_app_id_without_replacing_the_players_own(self) -> None:
        grid = self.account / "config" / "grid"
        grid.mkdir()
        appid = steam.app_id(self.targets()[0].exe, steam.COLLECTION_NAME)
        (grid / f"{appid}p.jpg").write_bytes(b"player's own")
        (result,) = self.add(game_dir=self.game)
        self.assertEqual(result.pictures, 3)
        self.assertEqual((grid / f"{appid}p.jpg").read_bytes(), b"player's own")
        self.assertFalse((grid / f"{appid}p.png").exists())
        for suffix in ("", "_hero", "_logo"):
            self.assertTrue((grid / f"{appid}{suffix}.png").is_file())

    def test_no_game_files_no_pictures(self) -> None:
        self.assertEqual(steam.make_pictures(self.temp / "nowhere"), {})

    @staticmethod
    def emblem(colour: tuple[int, int, int]) -> bytes:
        import io
        picture = Image.new("RGBA", (320, 176), (0, 0, 0, 0))
        picture.paste((*colour, 255), (40, 20, 280, 156))
        out = io.BytesIO()
        picture.save(out, format="PNG")
        return out.getvalue()

    def test_each_game_gets_its_own_emblem(self) -> None:
        colours = {"u1": (200, 160, 40), "u2": (150, 150, 150), "u3": (90, 90, 90)}
        emblems = {key: self.emblem(colour) for key, colour in colours.items()}
        wanted = steam.targets(self.temp, self.temp / "nothing.exe", Path(sys.executable), self.temp / "main.py",
                               GAMES, emblems)
        (result,) = steam.add_to_steam(wanted, "icon.ico", self.game, accounts=[(self.account, "")],
                                       all_names=ALL_NAMES)
        self.assertEqual(result.pictures, 12)
        grid = self.account / "config" / "grid"
        for appid, (key, _) in zip(result.ids, GAMES):
            wide = Image.open(grid / f"{appid}.png").convert("RGB")
            self.assertEqual(wide.size, steam.WIDE)
            self.assertEqual(wide.getpixel((steam.WIDE[0] // 2, steam.WIDE[1] // 2)), colours[key])
            logo = Image.open(grid / f"{appid}_logo.png")
            self.assertEqual((logo.mode, logo.size), ("RGBA", (720, 408)))  # the emblem without its edge, x3

    def test_each_games_own_icon_is_its_steam_icon_and_ours_are_made_again(self) -> None:
        icon = self.temp / "u1.png"
        Image.new("RGBA", (256, 256), (10, 200, 10, 255)).save(icon)
        wanted = steam.targets(self.temp, self.temp / "nothing.exe", Path(sys.executable), self.temp / "main.py",
                               GAMES[:1], {"u1": self.emblem((200, 160, 40))}, {"u1": icon})
        (result,) = steam.add_to_steam(wanted, "icon.ico", self.game, accounts=[(self.account, "")],
                                       all_names=ALL_NAMES)
        (entry,) = [node for node in steam.shortcuts_of(steam._read(self.account / "config" / "shortcuts.vdf"))
                    if steam.get(node.value, "AppName") == GAMES[0][1]]
        self.assertEqual(steam.get(entry.value, "icon"), str(icon))
        grid = self.account / "config" / "grid"
        wide = Image.open(grid / f"{result.ids[0]}.png").convert("RGB")
        self.assertEqual(wide.getpixel((50 + 165, steam.WIDE[1] // 2)), (10, 200, 10))  # the icon on the left
        player = grid / f"{result.ids[0]}_hero.png"
        Image.new("RGB", (8, 8)).save(player)  # the player's own banner (no mark)
        (again,) = steam.add_to_steam(wanted, "icon.ico", self.game, accounts=[(self.account, "")],
                                      all_names=ALL_NAMES)
        self.assertEqual(again.pictures, 3)  # ours made again, the player's kept
        self.assertEqual(Image.open(player).size, (8, 8))

    def test_an_emblem_that_is_not_a_picture_keeps_the_collections(self) -> None:
        pictures = steam.make_pictures(self.game, b"not a png")
        self.assertEqual(pictures["_logo"].width, steam.LOGO_WIDTH)


class SteamProcessTests(unittest.TestCase):
    def test_steam_exe_from_the_first_folder_that_has_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "a", Path(temp) / "b"
            first.mkdir()
            second.mkdir()
            (second / "steam.exe").write_bytes(b"")
            self.assertEqual(steam.steam_exe([first, second]), second / "steam.exe")
            self.assertIsNone(steam.steam_exe([first]))

    def test_shut_down_waits_until_steam_is_gone(self) -> None:
        running = iter([True, True, False])
        with mock.patch.object(steam.subprocess, "Popen") as popen, \
                mock.patch.object(steam, "steam_running", side_effect=lambda: next(running)), \
                mock.patch.object(steam.time, "sleep"):
            self.assertTrue(steam.shut_down_steam(Path("C:/Steam/steam.exe")))
        self.assertEqual(popen.call_args[0][0], [str(Path("C:/Steam/steam.exe")), "-shutdown"])

    def test_shut_down_gives_up(self) -> None:
        clock = iter(range(0, 1000, 10))
        with mock.patch.object(steam.subprocess, "Popen"), \
                mock.patch.object(steam, "steam_running", return_value=True), \
                mock.patch.object(steam.time, "sleep"), \
                mock.patch.object(steam.time, "monotonic", side_effect=lambda: next(clock)):
            self.assertFalse(steam.shut_down_steam(Path("C:/Steam/steam.exe"), wait=40))


if __name__ == "__main__":
    unittest.main()
