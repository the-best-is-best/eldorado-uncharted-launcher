# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Launcher updates from El Dorado's GitHub releases.

The package's VERSION file (tools/package_windows.sh copies tools/VERSION) names the installed version; a copy run
from the source tree has none and is never updated. An update goes:
  1. newest_release(): the newest release above the installed version whose Uncharted-windows.zip has a SHA-256
     published by GitHub (the asset's "digest"),
  2. download(): the zip into update\\, resumed after a broken connection, checked against size and SHA-256,
  3. stage(): unpacked into update\\staged and checked (REQUIRED, its VERSION),
  4. hand_off(): the new version's own Python runs its tools\\apply_update.py, which waits for this launcher to
     close, swaps the program folders (rolling back on any error) and starts the new launcher. analysis\\ (saves,
     settings, logs, shader cache) is never touched.
UNCHARTED_UPDATE_API points the check at another releases list (tests; plain http only on 127.0.0.1).
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY = "the-best-is-best/eldorado-uncharted-launcher"
RELEASES_PAGE = f"https://github.com/{REPOSITORY}/releases"
API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=20"
ASSET = "Uncharted-windows.zip"
USER_AGENT = "ElDorado-Launcher"
# What a package must hold to be installed over this one: the starter, the Python with Qt, the launcher's entry
# point and window, the updater pair and the game's start chain.
REQUIRED: tuple[str, ...] = (
    "Uncharted Launcher.exe", "VERSION", "python/pythonw.exe", "python/Lib/site-packages/PySide6/QtQuick.pyd",
    "launcher/main.py", "launcher/core/updater.py", "launcher/ui/qml/Main.qml", "tools/apply_update.py",
    "tools/probe_uncharted.py", "gow3_pc/run.py", "gow3_pc/scripts/prepare.py", "gow3_pc/out/bb-probe.exe",
)
CHUNK = 1 << 16
# A try that brought at least this much counts as progress: the failure count starts again.
PROGRESS_BYTES = 1 << 20

Version = tuple[int, int, int]


class UpdateError(Exception):
    """Why an update could not be checked or installed, worded for the player."""


class Cancelled(UpdateError):
    """The player stopped the download."""


@dataclass(frozen=True)
class Release:
    version: Version
    tag: str
    page: str
    notes: str
    url: str
    size: int
    sha256: str

    @property
    def text(self) -> str:
        return version_text(self.version)


def parse_version(text: str | None) -> Version | None:
    """'v1.2.3' or '1.2.3' -> (1, 2, 3); None for anything else."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    if not match:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def version_text(version: Version) -> str:
    return ".".join(str(part) for part in version)


def installed_version(root: Path) -> Version | None:
    """The package's version, or None for a copy run from the source tree (no VERSION file at its root)."""
    try:
        return parse_version((root / "VERSION").read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError):
        return None


# --- the check ---------------------------------------------------------------------------------------------------

def api_url() -> str:
    return os.environ.get("UNCHARTED_UPDATE_API") or API


def allowed_url(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "https":
        return True
    return parts.scheme == "http" and parts.hostname == "127.0.0.1" and bool(os.environ.get("UNCHARTED_UPDATE_API"))


def fetch_releases(timeout: float = 15) -> list[dict[str, Any]]:
    url = api_url()
    if not allowed_url(url):
        raise UpdateError(f"Refusing a non-HTTPS address: {url}")
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, http.client.HTTPException, ValueError) as error:  # offline, rate limit, a broken answer
        raise UpdateError(f"Could not reach GitHub's releases ({error or type(error).__name__}).") from error
    if not isinstance(data, list):
        raise UpdateError("GitHub's releases list looks wrong (not a list).")
    return data


def pick_release(releases: list[dict[str, Any]], current: Version) -> Release | None:
    """The newest release above `current` that carries an installable package. Pre-releases count."""
    best: Release | None = None
    for entry in releases:
        version = parse_version(entry.get("tag_name"))
        if entry.get("draft") or version is None or version <= current:
            continue
        if best is not None and version <= best.version:
            continue
        asset = next((item for item in entry.get("assets") or [] if item.get("name") == ASSET), None)
        digest = str((asset or {}).get("digest") or "")
        if asset is None or not digest.startswith("sha256:"):
            continue
        best = Release(version=version, tag=str(entry["tag_name"]), page=str(entry.get("html_url") or RELEASES_PAGE),
                       notes=str(entry.get("body") or ""), url=str(asset["browser_download_url"]),
                       size=int(asset.get("size") or 0), sha256=digest.split(":", 1)[1].lower())
    return best


def newest_release(current: Version, timeout: float = 15) -> Release | None:
    return pick_release(fetch_releases(timeout), current)


# --- download and staging ------------------------------------------------------------------------------------------

def update_dir(root: Path) -> Path:
    return root / "update"


Progress = Callable[[int, int], None]


def download(release: Release, root: Path, progress: Progress | None = None,
             cancelled: Callable[[], bool] | None = None, attempts: int = 8, timeout: float = 60,
             pause: float = 2.0) -> Path:
    """The release's zip in update\\, checked. A stalled or broken connection is opened again and the download
    goes on where it stopped (HTTP Range), up to `attempts` tries in a row without progress."""
    if not allowed_url(release.url):
        raise UpdateError(f"Refusing a non-HTTPS download: {release.url}")
    folder = update_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / (ASSET + ".part")
    target = folder / ASSET
    digest = hashlib.sha256()
    done = failures = 0
    with partial.open("wb") as out:
        while not release.size or done < release.size:
            start = done
            try:
                done, digest = _download_once(release, out, done, digest, progress, cancelled, timeout)
                if not release.size:
                    break
                if done < release.size:
                    raise ConnectionError(f"the connection closed after {done} of {release.size} bytes")
            except (OSError, http.client.HTTPException) as error:  # timeouts, resets, URLError, HTTPError
                failures = 0 if done - start >= PROGRESS_BYTES else failures + 1
                if failures >= attempts:
                    raise UpdateError(
                        f"The download from GitHub keeps stopping ({error or type(error).__name__}).\n\n"
                        f"Try again later, or download {ASSET} from the releases page and extract it over this "
                        "folder (saves and settings in analysis\\ are kept).") from error
                time.sleep(min(pause * max(failures, 1), 15.0))
    if release.size and done != release.size:
        partial.unlink(missing_ok=True)
        raise UpdateError(f"The download is incomplete ({done} of {release.size} bytes).")
    if digest.hexdigest() != release.sha256:
        partial.unlink(missing_ok=True)
        raise UpdateError("The download does not match the release's SHA-256: it was not installed.")
    partial.replace(target)
    return target


def _download_once(release: Release, out: Any, done: int, digest: Any, progress: Progress | None,
                   cancelled: Callable[[], bool] | None, timeout: float) -> tuple[int, Any]:
    """One connection: appends to `out` from byte `done`; returns the new count and digest."""
    headers = {"User-Agent": USER_AGENT}
    if done:
        headers["Range"] = f"bytes={done}-"
    # Each try asks github.com again: its redirect to the file host is signed and expires.
    with urllib.request.urlopen(urllib.request.Request(release.url, headers=headers), timeout=timeout) as response:
        if done and response.status != 206:  # the server ignored the range: from the start
            out.seek(0)
            out.truncate()
            done, digest = 0, hashlib.sha256()
        while chunk := response.read(CHUNK):
            if cancelled is not None and cancelled():
                raise Cancelled("Cancelled.")
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, release.size)
    return done, digest


def stage(archive: Path, root: Path, version: Version) -> Path:
    """The package unpacked into update\\staged and checked; returns that folder."""
    staged = update_dir(root) / "staged"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True)
    with zipfile.ZipFile(archive) as package:
        prefix = _common_folder([info.filename for info in package.infolist() if not info.is_dir()])
        base = staged.resolve()
        for info in package.infolist():
            name = info.filename.replace("\\", "/")
            if info.is_dir() or not name.startswith(prefix):
                continue
            target = (staged / name[len(prefix):]).resolve()
            if base not in target.parents:
                raise UpdateError(f"The package holds a path outside its folder: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.open(info) as source, target.open("wb") as out:
                shutil.copyfileobj(source, out, 1 << 20)
    missing = [path for path in REQUIRED if not (staged / path).is_file()]
    if missing:
        raise UpdateError("The package is incomplete: " + ", ".join(missing))
    if installed_version(staged) != version:
        raise UpdateError("The package's VERSION does not match the release.")
    return staged


def _common_folder(names: list[str]) -> str:
    """"Uncharted-windows/" when every file sits in that one folder (python -m zipfile -c packs it so)."""
    parts = [name.replace("\\", "/").split("/", 1) for name in names]
    tops = {part[0] for part in parts}
    if len(tops) == 1 and all(len(part) == 2 for part in parts):
        return tops.pop() + "/"
    return ""


def hand_off(root: Path, staged: Path) -> None:
    """Starts the new version's installer; it waits for this process to end, then restarts the launcher."""
    python = staged / "python" / "pythonw.exe"
    script = staged / "tools" / "apply_update.py"
    if not python.is_file() or not script.is_file():
        raise UpdateError("The staged update has no python\\pythonw.exe or tools\\apply_update.py.")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        subprocess.Popen([str(python), "-I", str(script), "--root", str(root), "--wait-pid", str(os.getpid())],
                         cwd=str(staged), creationflags=flags, close_fds=True)
    except OSError as error:
        raise UpdateError(f"The update installer could not start:\n{error}") from error


def cleanup(root: Path) -> list[Path]:
    """Removes what an applied or abandoned update left in update\\. Returns what could not be removed yet (files
    still held by the installer that just ended); the next start tries again."""
    folder = update_dir(root)
    if not folder.exists():
        return []
    left: list[Path] = []
    for name in ("old", "staged", ASSET, ASSET + ".part"):
        path = folder / name
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except OSError:
            left.append(path)
    try:
        folder.rmdir()
    except OSError:
        left.append(folder)
    return left
