# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import trophies  # noqa: E402

# A made-up set in the engine's cache format (no real trophy text).
CACHE = "\n".join([
    "format\t2", "stamp\tnone", "npcommid\tNPWR00000_00", "title\tTest set", "detail\t", "groups\t0",
    "trophy\t0\tP\t0\tAll of it\tEvery trophy",
    "trophy\t1\tG\t0\tFirst\tDo the first thing",
    "trophy\t2\tB\t1\tSecret\tA hidden one",
    "trophy\t3\tB\t0\tThird\tDo the third thing",
    "trophy\t4\tS\t1\tSecret two\tAnother hidden one",
]) + "\n"


def _user(tmp_path: Path, unlocks: str = "") -> Path:
    user = tmp_path / "uncharted-user"
    cache = trophies.cache_dir("u1", user)
    cache.mkdir(parents=True)
    (cache / "trophies.txt").write_text(CACHE, encoding="utf-8")
    (cache / "TROP001.PNG").write_bytes(b"png")
    (user / "trophy").mkdir()
    (user / "trophy" / "NPWR00000_00.log").write_text(unlocks, encoding="utf-8")
    return user


def test_set_with_unlocks_from_the_cache(tmp_path: Path) -> None:
    user = _user(tmp_path, "1 1700000000\n2 1800000000\nbroken\n1 1600000000\n")
    found = trophies.load("u1", tmp_path / "no-game", user_dir=user)
    assert found is not None and found.npcommid == "NPWR00000_00"
    assert found.count == 2 and found.percent == 40
    # Earned first, newest first; the earliest time of a trophy counts.
    assert [t.number for t in found.trophies] == [2, 1, 0, 3, 4]
    assert found.trophies[1].earned == 1600000000
    assert found.trophies[1].icon == trophies.cache_dir("u1", user) / "TROP001.PNG"
    assert found.trophies[2].icon is None
    grades = {g.grade: (g.earned, g.total) for g in found.grades()}
    assert grades == {"P": (0, 1), "G": (1, 1), "S": (0, 1), "B": (1, 2)}


def test_hidden_trophies_stay_hidden_until_earned(tmp_path: Path) -> None:
    found = trophies.load("u1", tmp_path, user_dir=_user(tmp_path, "2 1\n"))
    assert found is not None
    by_number = {t.number: t for t in found.trophies}
    assert by_number[2].shown_name() == "Secret" and by_number[2].earned_text() == "EARNED"
    assert by_number[4].secret and by_number[4].shown_name() == "Hidden trophy"
    assert by_number[3].earned_text() == "LOCKED"


def test_no_cache_no_set(tmp_path: Path) -> None:
    assert trophies.load("u2", tmp_path, user_dir=tmp_path / "user") is None


def test_old_logs_are_merged_once(tmp_path: Path) -> None:
    folder = tmp_path / "trophy"
    folder.mkdir()
    (folder / "NPWR09798_00.log").write_text("5 100", encoding="utf-8")
    (folder / "trophy01.txt").write_text("5 50\n6 60\nbroken\n6 70\n", encoding="utf-8")
    assert trophies.migrate_old_logs(tmp_path) == 1
    assert (folder / "NPWR09798_00.log").read_text(encoding="utf-8") == "5 100\n6 60\n"
    assert (folder / "trophy01.txt.migrated").is_file() and not (folder / "trophy01.txt").exists()
    assert trophies.migrate_old_logs(tmp_path) == 0


def _old_engine_logs(user: Path) -> Path:
    """The old engine's trophy/trophy0N.txt ("id time" lines, a trophy can repeat) next to Mevlock's logs."""
    folder = user / "trophy"
    folder.mkdir(parents=True)
    (folder / "NPWR09798_00.log").write_text("5 100", encoding="utf-8")       # no line end at the end
    (folder / "trophy01.txt").write_text("5 50\n6 60\nbroken\n6 70\n7 x\n", encoding="utf-8")
    (folder / "trophy03.txt").write_text("0 10\n", encoding="utf-8")           # no NPWR09801_00.log yet
    return folder


def _check_merged(folder: Path) -> None:
    assert (folder / "NPWR09798_00.log").read_text(encoding="utf-8") == "5 100\n6 60\n"
    assert (folder / "NPWR09801_00.log").read_text(encoding="utf-8") == "0 10\n"
    assert not (folder / "NPWR09799_00.log").exists()
    for name in ("trophy01.txt", "trophy03.txt"):
        assert (folder / f"{name}.migrated").is_file() and not (folder / name).exists()


def test_launcher_merges_old_engine_logs_once(tmp_path: Path) -> None:
    folder = _old_engine_logs(tmp_path)
    assert trophies.migrate_old_logs(tmp_path) == 2
    _check_merged(folder)
    assert trophies.migrate_old_logs(tmp_path) == 0
    _check_merged(folder)


def test_start_script_merges_old_engine_logs_once(tmp_path: Path) -> None:
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "tools" / "probe_uncharted.py"
    spec = importlib.util.spec_from_file_location("probe_uncharted_trophy_test", script)
    assert spec is not None and spec.loader is not None
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    folder = _old_engine_logs(tmp_path)
    probe.migrate_trophy_logs(tmp_path)
    _check_merged(folder)
    probe.migrate_trophy_logs(tmp_path)
    _check_merged(folder)
    # The launcher finds nothing left to move after the start script did it.
    assert trophies.migrate_old_logs(tmp_path) == 0


def test_language_numbers() -> None:
    assert trophies.language_number("3") == 3
    assert trophies.language_number("ar") == 1


if __name__ == "__main__":
    import tempfile

    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            with tempfile.TemporaryDirectory() as folder:
                test(Path(folder)) if test.__code__.co_argcount else test()
            print("ok", name)
