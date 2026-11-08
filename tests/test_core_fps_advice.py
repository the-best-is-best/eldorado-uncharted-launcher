# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""core/fps_advice.py: when a slow session offers one step lower quality, and which step."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import fps_advice  # noqa: E402

END = 1_800_000_000


def stats(fps=45.0, samples=60, gpu_wait=40.0, end=END):
    return {"u1": {"session_fps": fps, "session_samples": samples, "session_gpu_wait": gpu_wait,
                   "session_end": end}}


DLSS = {"upscaler": "dlss", "fps_limit": "60"}


class AdviceTests(unittest.TestCase):
    def test_slow_on_the_card_one_step_lower(self) -> None:
        step = fps_advice.advice("u1", {"upscale": "quality"}, DLSS, stats())
        self.assertEqual((step.upscaler, step.upscale, step.turn_on_fsr1, step.limit), ("dlss", "balanced", False, 60))
        self.assertEqual(round(step.fps), 45)

    def test_native_aa_goes_to_quality(self) -> None:
        self.assertEqual(fps_advice.advice("u1", {"upscale": "off"}, DLSS, stats()).upscale, "quality")

    def test_without_an_upscaler_fsr1_at_quality(self) -> None:
        step = fps_advice.advice("u1", {"upscale": "off"}, {"upscaler": "taa", "fps_limit": "60"}, stats())
        self.assertEqual((step.upscaler, step.upscale, step.turn_on_fsr1), ("fsr1", "quality", True))

    def test_fsr1_has_no_native_aa(self) -> None:
        ini = {"upscaler": "off", "fsr1": "1", "fps_limit": "60"}
        self.assertEqual(fps_advice.advice("u1", {"upscale": "off"}, ini, stats()).upscale, "balanced")

    def test_nothing_lower_than_ultra(self) -> None:
        self.assertIsNone(fps_advice.advice("u1", {"upscale": "ultra"}, DLSS, stats()))

    def test_fast_enough_short_or_the_cpu_is_the_limit(self) -> None:
        game = {"upscale": "quality"}
        self.assertIsNone(fps_advice.advice("u1", game, DLSS, stats(fps=55.0)))       # above 85% of 60
        self.assertIsNone(fps_advice.advice("u1", game, DLSS, stats(samples=10)))     # under two minutes
        self.assertIsNone(fps_advice.advice("u1", game, DLSS, stats(gpu_wait=5.0)))   # the CPU held it back
        self.assertIsNone(fps_advice.advice("u2", game, DLSS, stats()))               # no session of that game
        self.assertIsNone(fps_advice.advice("u1", game, DLSS, {"u1": {"fps_sum": 1}}))  # stats from before

    def test_the_limit_counts(self) -> None:
        ini = dict(DLSS, fps_limit="120")
        self.assertIsNotNone(fps_advice.advice("u1", {"upscale": "quality"}, ini, stats(fps=90.0)))

    def test_asked_once_per_session(self) -> None:
        game = {"upscale": "quality", fps_advice.ASKED: END}
        self.assertIsNone(fps_advice.advice("u1", game, DLSS, stats()))
        self.assertIsNotNone(fps_advice.advice("u1", game, DLSS, stats(end=END + 600)))

    def test_mark_asked_and_apply(self) -> None:
        config = mock.Mock()
        game = {"upscale": "off", "preset": "recommended"}
        config.game.return_value = game
        fps_advice.mark_asked(config, "u1", stats())
        self.assertEqual(game[fps_advice.ASKED], END)
        step = fps_advice.Step(45.0, 60, "fsr1", "quality", True)
        with mock.patch.object(fps_advice.cfg, "write_ini") as write_ini:
            fps_advice.apply(config, "u1", step)
        self.assertEqual((game["upscale"], game["preset"]), ("quality", "custom"))
        write_ini.assert_called_once_with("u1", {"fsr1": "1"})


class PlayStatsTests(unittest.TestCase):
    def test_the_session_is_written_beside_the_totals(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        import json
        import tempfile

        import probe_uncharted

        with tempfile.TemporaryDirectory() as temp:
            stats_file = Path(temp) / "eldorado-stats.json"
            stats_file.write_text(json.dumps({"u1": {"seconds": 100, "fps_sum": 600.0, "fps_count": 10}}))
            with mock.patch.object(probe_uncharted, "STATS", stats_file):
                play = probe_uncharted.PlayStats("u1")
                line = ("Frame stats: {} FPS, worst frame 34.2 ms (vblank 60 Hz); ... GPU thread 0.00 us/draw, "
                        "1070 draws/frame, idle 1.5%; blocked: recorder 2.2%, host copies 0.6% (1/frame), copy "
                        "threads 0.0%, GPU ticks {}%; reduced-size draws 0/frame of 0 in the scene")
                play.line(line.format(50.0, 40.0))
                play.line(line.format(46.0, 30.0))
                play.line("Frame stats: 60.0 FPS, worst frame 17 ms; 50 draws/frame")  # a menu: not counted
                play.save()
            saved = json.loads(stats_file.read_text())["u1"]
        self.assertEqual((saved["session_fps"], saved["session_samples"], saved["session_gpu_wait"]), (48.0, 2, 35.0))
        self.assertEqual(saved["fps_count"], 12)
        self.assertGreater(saved["session_end"], 0)


if __name__ == "__main__":
    unittest.main()
