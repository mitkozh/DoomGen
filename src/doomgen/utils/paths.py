"""Locate and resolve the ACC/ZDBSP compilers bundled with DoomGen."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path

__all__ = [
    "CompilerUnavailable",
    "can_run_compiler",
    "get_bundled_compiler",
    "get_platform",
    "resolve_compiler",
]


class CompilerUnavailable(RuntimeError):
    """No usable ACC or ZDBSP compiler was found for this platform."""


_TOOLS = ("acc", "zdbsp")

_BINARY_NAMES = {
    ("windows", "x86"): "zdbsp-windows.exe",
    ("windows", "x86_64"): "zdbsp-windows.exe",
    ("windows", "arm64"): "zdbsp-windows.exe",
    ("macos", "x86_64"): "zdbsp-macos",
    ("macos", "arm64"): "zdbsp-macos",
    ("linux", "x86_64"): "zdbsp-linux",
    ("linux", "arm64"): "zdbsp-linux-arm64",
}


def _os_name() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _arch_name() -> str:
    if sys.platform.startswith("win"):
        # platform.machine() reports the host CPU, which differs from the
        # interpreter under emulation. The wheel tag follows the interpreter.
        interpreter_arch = {
            "win32": "x86",
            "win-amd64": "x86_64",
            "win-arm64": "arm64",
        }.get(sysconfig.get_platform().lower())
        if interpreter_arch is not None:
            return interpreter_arch

    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "x86_64"
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86", "i386", "i686"):
        return "x86"
    return machine


def get_platform() -> str:
    """Return the current platform as ``<os>-<arch>``."""
    return f"{_os_name()}-{_arch_name()}"


def _bin_dir() -> Path:
    ref = files("doomgen") / "bin"
    with as_file(ref) as path:
        return Path(path)


def _bundled_path(tool: str) -> Path | None:
    if tool != "zdbsp":
        return None
    filename = _BINARY_NAMES.get((_os_name(), _arch_name()))
    if filename is None:
        return None
    return _bin_dir() / tool / filename


def _ensure_executable(path: Path) -> Path:
    if not sys.platform.startswith("win") and not os.access(path, os.X_OK):
        try:
            path.chmod(path.stat().st_mode | 0o111)
        except OSError:
            pass
    return path


def get_bundled_compiler(tool: str) -> str:
    """Return the path to the bundled ACC or ZDBSP binary for this platform."""
    if tool not in _TOOLS:
        raise ValueError(f"Unknown tool: {tool}")

    if tool == "acc":
        raise CompilerUnavailable(
            "ACC is not bundled. Run `python -m doomgen.tools install acc`."
        )

    bundled = _bundled_path(tool)
    if bundled is None:
        raise CompilerUnavailable(
            f"No bundled {tool} compiler is available for {get_platform()}."
        )
    if not bundled.is_file():
        raise CompilerUnavailable(f"Bundled {tool} compiler not found at '{bundled}'.")

    return str(_ensure_executable(bundled))


def _resolve_path(executable_path: str | os.PathLike[str]) -> Path | None:
    raw = os.fspath(executable_path)
    found = shutil.which(raw)
    path = Path(found) if found is not None else Path(raw)
    return path if path.is_file() else None


@lru_cache(maxsize=128)
def _can_run_cached(tool: str, path: str, mtime_ns: int, size: int) -> bool:
    if tool == "zdbsp":
        command = [path, "--version"]
        expected = b"ZDBSP"
        allowed_returncodes = {0}
    elif tool == "acc":
        command = [path]
        expected = b"Usage: ACC"
        allowed_returncodes = {0, 1}
    else:
        return False

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
            creationflags=creationflags,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return result.returncode in allowed_returncodes and expected in result.stdout


def can_run_compiler(tool: str, executable_path: str | os.PathLike[str]) -> bool:
    """Return whether the compiler starts and identifies itself correctly."""
    if tool not in _TOOLS:
        raise ValueError(f"Unknown tool: {tool}")

    path = _resolve_path(executable_path)
    if path is None:
        return False

    try:
        stat = path.stat()
    except OSError:
        return False

    return _can_run_cached(tool, str(path), stat.st_mtime_ns, stat.st_size)


def resolve_compiler(tool: str, explicit: str | None = None) -> str:
    """Resolve a usable compiler path.

    Resolution order: explicit path, bundled compiler, then ``PATH``.
    Raises :class:`CompilerUnavailable` when nothing can run.
    """
    if tool not in _TOOLS:
        raise ValueError(f"Unknown tool: {tool}")

    if explicit is not None:
        path = _resolve_path(explicit)
        if path is None or not can_run_compiler(tool, path):
            raise CompilerUnavailable(
                f"Explicit {tool} compiler is not usable on {get_platform()}: "
                f"'{explicit}'."
            )
        return str(path)

    if tool == "acc":
        from doomgen.tools.acc import cached_acc_path

        cached = cached_acc_path()
        if cached is not None and can_run_compiler("acc", str(cached)):
            return str(cached)

    bundled_error: CompilerUnavailable | None = None
    bundled_path: str | None = None
    try:
        bundled = get_bundled_compiler(tool)
    except CompilerUnavailable as exc:
        bundled_error = exc
    else:
        if can_run_compiler(tool, bundled):
            return bundled
        bundled_path = bundled

    system = shutil.which(tool)
    if system is not None and can_run_compiler(tool, system):
        return system

    message = f"No usable {tool} compiler was found for {get_platform()}."
    if bundled_error is not None:
        message += f" {bundled_error}"
    elif bundled_path is not None:
        message += f" Bundled compiler at '{bundled_path}' cannot run."
    if tool == "acc":
        message += " Install ACC 1.60 or pass an explicit acc_path."
    else:
        message += " Install ZDBSP or pass an explicit zdbsp_path."
    raise CompilerUnavailable(message)
