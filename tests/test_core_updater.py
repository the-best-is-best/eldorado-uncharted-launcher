# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""core/updater.py on temporary folders and a local web server (127.0.0.1) only.
Run: python tests/test_core_updater.py (or pytest)."""
import hashlib
import http.server
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

from core import updater  # noqa: E402


def release_entry(tag: str, digest: str | None = "sha256:" + "ab" * 32, draft: bool = False,
                  asset: str = updater.ASSET) -> dict:
    assets = [{"name": asset, "browser_download_url": f"https://example.invalid/{tag}.zip", "size": 10,
               **({"digest": digest} if digest else {})}]
    return {"tag_name": tag, "draft": draft, "html_url": f"https://example.invalid/{tag}", "body": "notes",
            "assets": assets}


class VersionTests(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertEqual(updater.parse_version("v1.2.3"), (1, 2, 3, 3, 0))
        self.assertEqual(updater.parse_version(" 2.0.10\n"), (2, 0, 10, 3, 0))
        self.assertEqual(updater.parse_version("1.0.0-beta1"), (1, 0, 0, 1, 1))
        for bad in ("1.2", "v1.2.3-gamma1", "1.2.3-", "", None, "latest"):
            self.assertIsNone(updater.parse_version(bad))
        self.assertEqual(updater.version_text((2, 0, 10, 3, 0)), "2.0.10")
        for text in ("1.0.0-beta1", "1.0.0-rc2", "1.0.0-alpha", "3.1.4"):
            self.assertEqual(updater.version_text(updater.parse_version(text)), text)

    def test_pre_releases_come_before_the_release(self) -> None:
        order = ["1.0.0-alpha1", "1.0.0-beta1", "1.0.0-beta2", "1.0.0-rc1", "1.0.0", "1.0.1-beta1", "1.0.1"]
        self.assertEqual(sorted(order, key=updater.parse_version), order)

    def test_compare_is_numeric(self) -> None:
        self.assertLess(updater.parse_version("1.9.0"), updater.parse_version("1.10.0"))

    def test_installed_version_from_the_package_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertIsNone(updater.installed_version(root))
            (root / "VERSION").write_text("1.0.0\n", encoding="ascii")
            self.assertEqual(updater.installed_version(root), (1, 0, 0, 3, 0))

    def test_the_repository_version_file_parses(self) -> None:
        self.assertIsNotNone(updater.installed_version(Path(__file__).resolve().parents[1] / "tools"))

    def test_newest_installable_release_is_picked(self) -> None:
        releases = [release_entry("v1.1.0"), release_entry("v2.0.0", draft=True), release_entry("v1.3.0", digest=None),
                    release_entry("v1.2.0"), release_entry("v1.4.0", asset="Other.zip"), release_entry("nightly"),
                    release_entry("v0.9.0")]
        found = updater.pick_release(releases, (1, 0, 0, 3, 0))
        self.assertIsNotNone(found)
        self.assertEqual((found.version, found.tag, found.size, found.sha256), ((1, 2, 0, 3, 0), "v1.2.0", 10, "ab" * 32))
        self.assertEqual(found.text, "1.2.0")
        self.assertIsNone(updater.pick_release(releases, (1, 2, 0, 3, 0)))
        self.assertIsNone(updater.pick_release([], (1, 0, 0, 3, 0)))

    def test_only_https_unless_a_local_test_server(self) -> None:
        self.assertTrue(updater.allowed_url("https://api.github.com/x"))
        with mock.patch.dict(os.environ, {"UNCHARTED_UPDATE_API": ""}):
            self.assertFalse(updater.allowed_url("http://127.0.0.1/x"))
        with mock.patch.dict(os.environ, {"UNCHARTED_UPDATE_API": "http://127.0.0.1:1/"}):
            self.assertTrue(updater.allowed_url("http://127.0.0.1/x"))
            self.assertFalse(updater.allowed_url("http://example.com/x"))


class TempRoot(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="updater-test-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def package(self, version: str = "1.2.0", prefix: str = "Uncharted-windows/", skip: str = "",
                extra: dict | None = None) -> Path:
        archive = self.root / "package.zip"
        with zipfile.ZipFile(archive, "w") as out:
            for name in updater.REQUIRED:
                if name != skip:
                    out.writestr(prefix + name, version + "\n" if name == "VERSION" else "x")
            for name, data in (extra or {}).items():
                out.writestr(name, data)
        return archive


class StageTests(TempRoot):
    def test_a_package_in_one_folder_is_staged(self) -> None:
        staged = updater.stage(self.package(), self.root, (1, 2, 0, 3, 0))
        self.assertEqual(staged, self.root / "update" / "staged")
        self.assertTrue((staged / "launcher" / "main.py").is_file())
        self.assertEqual(updater.installed_version(staged), (1, 2, 0, 3, 0))

    def test_a_package_without_a_top_folder_is_staged(self) -> None:
        staged = updater.stage(self.package(prefix=""), self.root, (1, 2, 0, 3, 0))
        self.assertTrue((staged / "Uncharted Launcher.exe").is_file())

    def test_the_new_entry_point_is_required(self) -> None:
        self.assertIn("launcher/main.py", updater.REQUIRED)
        self.assertNotIn("launcher/uncharted_launcher.pyw", updater.REQUIRED)
        with self.assertRaisesRegex(updater.UpdateError, "launcher/main.py"):
            updater.stage(self.package(skip="launcher/main.py"), self.root, (1, 2, 0, 3, 0))

    def test_a_wrong_version_is_refused(self) -> None:
        with self.assertRaisesRegex(updater.UpdateError, "VERSION"):
            updater.stage(self.package(version="1.1.0"), self.root, (1, 2, 0, 3, 0))

    def test_a_path_outside_the_folder_is_refused(self) -> None:
        with self.assertRaisesRegex(updater.UpdateError, "outside"):
            updater.stage(self.package(prefix="", extra={"../evil.txt": "x"}), self.root, (1, 2, 0, 3, 0))
        self.assertFalse((self.root.parent / "evil.txt").exists())

    def test_cleanup_removes_the_update_folder(self) -> None:
        updater.stage(self.package(), self.root, (1, 2, 0, 3, 0))
        (self.root / "update" / updater.ASSET).write_bytes(b"zip")
        self.assertEqual(updater.cleanup(self.root), [])
        self.assertFalse((self.root / "update").exists())
        self.assertEqual(updater.cleanup(self.root), [])


class Server(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # quiet tests
        return


class DownloadTests(TempRoot):
    def setUp(self) -> None:
        super().setUp()
        self.files = self.root / "served"
        self.files.mkdir()
        self.data = os.urandom(300_000)
        (self.files / "pkg.zip").write_bytes(self.data)
        handler = lambda *args: Server(*args, directory=str(self.files))  # noqa: E731
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        url = f"http://127.0.0.1:{self.server.server_port}"
        patch = mock.patch.dict(os.environ, {"UNCHARTED_UPDATE_API": url + "/releases"})
        patch.start()
        self.addCleanup(patch.stop)
        self.url = url + "/pkg.zip"

    def release(self, sha256: str) -> updater.Release:
        return updater.Release((1, 2, 0), "v1.2.0", "", "", self.url, len(self.data), sha256)

    def test_download_is_checked_and_reports_progress(self) -> None:
        seen = []
        target = updater.download(self.release(hashlib.sha256(self.data).hexdigest()), self.root,
                                  progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(target.read_bytes(), self.data)
        self.assertEqual(seen[-1], (len(self.data), len(self.data)))
        self.assertFalse((self.root / "update" / (updater.ASSET + ".part")).exists())

    def test_a_wrong_checksum_is_refused(self) -> None:
        with self.assertRaisesRegex(updater.UpdateError, "SHA-256"):
            updater.download(self.release("00" * 32), self.root)
        self.assertEqual(list((self.root / "update").iterdir()), [])

    def test_cancel(self) -> None:
        with self.assertRaises(updater.Cancelled):
            updater.download(self.release("00" * 32), self.root, cancelled=lambda: True)

    def test_releases_list_from_the_test_server(self) -> None:
        (self.files / "releases").write_text('[{"tag_name": "v9.0.0", "assets": []}]', encoding="utf-8")
        self.assertEqual(updater.fetch_releases()[0]["tag_name"], "v9.0.0")
        self.assertIsNone(updater.newest_release((1, 0, 0, 3, 0)))

    def test_a_server_that_is_not_there_is_an_update_error(self) -> None:
        with mock.patch.dict(os.environ, {"UNCHARTED_UPDATE_API": "http://127.0.0.1:1/releases"}):
            with self.assertRaises(updater.UpdateError):
                updater.fetch_releases(timeout=2)


if __name__ == "__main__":
    unittest.main()
