# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""ui/steam_art.py: each game's four Steam pictures at Steam's sizes, the logo on a clear ground."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

try:
    from PySide6.QtGui import QGuiApplication, QImage
except ImportError:
    QGuiApplication = None


@unittest.skipIf(QGuiApplication is None, "Qt is needed for the pictures")
class SteamArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_four_pictures_per_game(self) -> None:
        from core import steam
        from ui import steam_art

        with tempfile.TemporaryDirectory() as temp:
            for key in ("u1", "u2", "u3"):
                folder = steam_art.make(key, Path(temp) / key)
                sizes = {name: QImage(str(folder / name)).size() for name in steam.ART_FILES.values()}
                self.assertEqual((sizes["p.png"].width(), sizes["p.png"].height()), steam_art.TALL)
                self.assertEqual((sizes["wide.png"].width(), sizes["wide.png"].height()), steam_art.WIDE)
                self.assertEqual((sizes["hero.png"].width(), sizes["hero.png"].height()), steam_art.HERO)
                logo = QImage(str(folder / "logo.png"))
                self.assertEqual(logo.width(), steam_art.LOGO_WIDTH)
                self.assertEqual(logo.pixelColor(logo.width() - 1, 0).alpha(), 0)  # clear around the title
                self.assertEqual(set(steam.made_pictures(folder)), set(steam.ART_FILES))


if __name__ == "__main__":
    unittest.main()
