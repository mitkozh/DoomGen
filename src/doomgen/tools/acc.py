"""Download and cache ACC 1.60 on demand."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from doomgen.utils.paths import can_run_compiler, get_platform

ACC_VERSION = "1.60"
ACC_RELEASE_URL = "https://github.com/ZDoom/acc/releases/download/1.60"

_ACC_ASSETS = {
    "windows-x86": (
        "acc-1.60-win32.zip",
        "d70c633fcf07da705562ce65104379e1c9ecaeaa159981acc5275840e606a15f",
    ),
    "windows-x86_64": (
        "acc-1.60-win32.zip",
        "d70c633fcf07da705562ce65104379e1c9ecaeaa159981acc5275840e606a15f",
    ),
    "windows-arm64": (
        "acc-1.60-win32.zip",
        "d70c633fcf07da705562ce65104379e1c9ecaeaa159981acc5275840e606a15f",
    ),
    "macos-x86_64": (
        "acc-1.60-mac.zip",
        "2acd2e72e96feb4d5f541db833901b13928548a3183906be4f02521c3aac4796",
    ),
    "macos-arm64": (
        "acc-1.60-mac.zip",
        "2acd2e72e96feb4d5f541db833901b13928548a3183906be4f02521c3aac4796",
    ),
    "linux-x86_64": (
        "acc-1.60-linux64.zip",
        "107f36708480205a4a8d699127f13f34e2255c0f57e632f06671d694279da292",
    ),
    "linux-arm64": (
        "acc-1.60-linuxarm64.zip",
        "58d520ffc2a5a9a47b524e366923b47bf6d50b94852bebc567bfea87f487eb4f",
    ),
}


def _binary_name() -> str:
    return "acc.exe" if sys.platform.startswith("win") else "acc"


def _cache_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "doomgen" / "tools" / "acc" / ACC_VERSION / get_platform()


def cached_acc_path() -> Path | None:
    """Return the cached ACC binary if it exists."""
    path = _cache_dir() / _binary_name()
    return path if path.is_file() else None


def _asset_for_platform() -> tuple[str, str]:
    try:
        return _ACC_ASSETS[get_platform()]
    except KeyError:
        raise RuntimeError(
            f"ACC {ACC_VERSION} is not available for {get_platform()}."
        ) from None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)


def _extract_archive(archive: Path, destination: Path) -> Path:
    binary_name = _binary_name()
    with zipfile.ZipFile(archive) as zip_file:
        for info in zip_file.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if Path(name).name != name:
                continue
            if name == binary_name or name.endswith(".acs"):
                with zip_file.open(info) as source:
                    with (destination / name).open("wb") as target:
                        shutil.copyfileobj(source, target)

    binary = destination / binary_name
    if not binary.is_file():
        raise RuntimeError(f"ACC archive did not contain {binary_name}.")
    return binary


def install_acc(force: bool = False) -> Path:
    """Download ACC 1.60 into the user cache and return the binary path."""
    cached = cached_acc_path()
    if cached is not None and not force and can_run_compiler("acc", cached):
        return cached

    asset, expected_hash = _asset_for_platform()
    url = f"{ACC_RELEASE_URL}/{asset}"
    cache_dir = _cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="doomgen-acc-") as temp_dir:
        archive = Path(temp_dir) / asset
        _download(url, archive)

        actual_hash = _sha256(archive)
        if actual_hash.lower() != expected_hash:
            raise RuntimeError(
                f"ACC archive checksum mismatch: expected {expected_hash}, "
                f"got {actual_hash}."
            )

        extracted = Path(temp_dir) / "extracted"
        extracted.mkdir()
        binary = _extract_archive(archive, extracted)

        target = cache_dir / binary.name
        shutil.copy2(binary, target)
        for include in extracted.glob("*.acs"):
            shutil.copy2(include, cache_dir / include.name)

        if not sys.platform.startswith("win"):
            target.chmod(target.stat().st_mode | 0o111)

        if not can_run_compiler("acc", target):
            raise RuntimeError(
                f"Downloaded ACC binary could not run on {get_platform()}."
            )

    return target
