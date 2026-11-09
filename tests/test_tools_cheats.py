# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""tools/probe_uncharted.py + engine/run.py: the launcher's cheats reach the engine, for the running game only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "engine"))

import probe_uncharted  # noqa: E402
import run  # noqa: E402  (engine/run.py)

U102 = next(code for code, version in probe_uncharted.GAME_CODE.items() if version == "1.02")
U100 = next(code for code, version in probe_uncharted.GAME_CODE.items() if version == "1.00")


class CheatEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.user = Path(self.temp.name) / "user"
        self.user.mkdir()
        self.game_dir = Path(self.temp.name) / "Game"
        self.game_dir.mkdir()
        for patcher in (mock.patch.object(probe_uncharted, "USER", self.user),
                        mock.patch.object(probe_uncharted, "TREASURES_FILE", self.user / "treasures-given.json")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def environment(self, cheats="", code=U102, **more):
        """The engine's environment for Uncharted 1 with these launcher cheats (game code 1.02 unless given)."""
        launcher = {k: v for k, v in os.environ.items() if not k.startswith(("UNCHARTED_", "BB_", "GOW3_"))}
        launcher.update({"UNCHARTED_CHEATS": cheats, **more})
        with mock.patch.dict(os.environ, launcher, clear=True), \
                mock.patch.object(probe_uncharted, "executable_hash", return_value=code):
            return probe_uncharted.game_environment(SimpleNamespace(collection_menu=False), "u1", "eboot.bin",
                                                    self.game_dir)

    @staticmethod
    def cheats(env):
        return set(filter(None, env.get("BB_CHEATS", "").split(",")))

    def test_all_default_to_off(self) -> None:
        env = self.environment()
        for name in ("health", "ammo", "devmode", "grenades", "noreload", "onehit", "rewards"):
            self.assertFalse(any(c.endswith(":" + name) for c in self.cheats(env)), name)
        for name in ("BB_UNLOCK_REWARDS", "BB_DEV_MENU", "BB_GIVE_TREASURES", "BB_POKE_U1", "BB_POKE_U2",
                     "BB_POKE_U3"):
            self.assertNotIn(name, env)

    def test_enabled_cheats_are_listed_for_each_game(self) -> None:
        cheats = self.cheats(self.environment("invincible,ammo,grenades"))
        for game in ("u1", "u2", "u3"):
            self.assertTrue({f"{game}:health", f"{game}:ammo", f"{game}:grenades"} <= cheats, game)

    def test_rewards_reach_the_engine_only_when_on(self) -> None:
        self.assertNotIn("BB_UNLOCK_REWARDS", self.environment("ammo"))
        env = self.environment("rewards")
        self.assertEqual(env["BB_UNLOCK_REWARDS"], "1")
        # Mevlock's engine does it (code patches and kept switches, 1.00 and 1.02): no cheat name, no poke.
        self.assertFalse(any(c.endswith(":rewards") for c in self.cheats(env)))
        self.assertNotIn("BB_POKE_U2", env)
        self.assertEqual(self.environment("rewards", code=U100)["BB_UNLOCK_REWARDS"], "1")

    def test_switch_cheats_reach_the_engine(self) -> None:
        env = self.environment("noreload,onehit")
        self.assertIn("104f84b:b=1", env["BB_POKE_U2"])  # Uncharted 2's own "No Reload" switch
        self.assertIn("17faa93:b=1", env["BB_POKE_U3"])
        self.assertIn("17fab94:b=1", env["BB_POKE_U3"])  # "One Hit Kills"
        self.assertTrue({"u1:noreload", "u1:onehit", "u2:onehit"} <= self.cheats(env))  # code patches where none
        # The switches' offsets are 1.02's: another build gets no pokes (a write there would hit other data).
        env = self.environment("noreload,onehit", code=U100)
        self.assertFalse(any(k.startswith("BB_POKE_") for k in env))

    def test_the_running_game_keeps_only_its_own_cheats(self) -> None:
        all_cheats = ",".join(sorted(self.cheats(self.environment("invincible,noreload"))))
        self.assertEqual(set(run.game_cheats(all_cheats, "eboot.bin").split(",")), {"health", "noreload"})
        # Uncharted 2 also has its torch fix (on unless UNCHARTED_TORCH_FORWARD=0).
        self.assertEqual(set(run.game_cheats(all_cheats, "big2-ps4_Shipping.elf").split(",")), {"health", "torch"})


if __name__ == "__main__":
    unittest.main()
