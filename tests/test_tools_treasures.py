# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""tools/probe_uncharted.py: Give all treasures once per save (the slot from the engine's line), per player."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import probe_uncharted  # noqa: E402


class TreasuresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.file = Path(self.temp.name) / "treasures-given.json"
        patcher = mock.patch.object(probe_uncharted, "TREASURES_FILE", self.file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp.cleanup)

    def test_the_engines_line_names_the_save(self) -> None:
        match = probe_uncharted.TREASURES_LINE.match("Treasures: Uncharted 1 1.02: Give all Treasures (SAVEDATA012)")
        self.assertEqual((match.group(1), match.group(2)), ("1", "SAVEDATA012"))
        self.assertIsNone(probe_uncharted.TREASURES_LINE.match("Treasures: Uncharted 1 1.02: already given to "
                                                               "SAVEDATA012"))

    def test_each_save_once_for_its_player(self) -> None:
        self.file.write_text(json.dumps({"u1:1": "old, once per player"}))  # no longer counts
        with mock.patch.dict(os.environ, {"UNCHARTED_SAVE_PROFILE_U1": "1", "UNCHARTED_SAVE_PROFILE_U3": "1"}):
            self.assertEqual(probe_uncharted.treasures_done(), [])
            probe_uncharted.note_treasures_given("u1", "SAVEDATA012")
            probe_uncharted.note_treasures_given("u3", "SAVEDATA030")
            self.assertEqual(sorted(probe_uncharted.treasures_done()), ["SAVEDATA012", "SAVEDATA030"])
        with mock.patch.dict(os.environ, {"UNCHARTED_SAVE_PROFILE_U1": "2", "UNCHARTED_SAVE_PROFILE_U3": "1"}):
            self.assertEqual(probe_uncharted.treasures_done(), ["SAVEDATA030"])  # player 2's u1 saves: not given
        probe_uncharted.note_treasures_given("u1", "")  # no slot: nothing noted
        self.assertEqual(len(json.loads(self.file.read_text())), 3)


if __name__ == "__main__":
    unittest.main()
