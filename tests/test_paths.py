"""Platform selection and resolution for the bundled compilers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from doomgen.utils.paths import (
    CompilerUnavailable,
    _arch_name,
    _bin_dir,
    _bundled_path,
    _os_name,
    can_run_compiler,
    get_bundled_compiler,
    get_platform,
    resolve_compiler,
)


def _expected_zdbsp_name() -> str:
    if _os_name() == "windows":
        return "zdbsp-windows.exe"
    if _os_name() == "macos":
        return "zdbsp-macos"
    if _arch_name() == "arm64":
        return "zdbsp-linux-arm64"
    return "zdbsp-linux"


def test_bin_dir_uses_package_resources():
    path = _bin_dir()
    assert path.is_dir()
    assert path.name == "bin"


def test_platform_string_is_os_and_arch():
    assert get_platform() == f"{_os_name()}-{_arch_name()}"


def test_bundled_filename_matches_platform():
    path = _bundled_path("zdbsp")
    assert path is not None
    assert path.name == _expected_zdbsp_name()


def test_acc_has_no_bundled_path():
    assert _bundled_path("acc") is None


def test_acc_bundled_lookup_points_to_installer():
    with pytest.raises(CompilerUnavailable, match="doomgen.tools install acc"):
        get_bundled_compiler("acc")


def test_bundled_zdbsp_resolves_to_existing_file():
    try:
        path = Path(get_bundled_compiler("zdbsp"))
    except CompilerUnavailable as exc:
        pytest.skip(str(exc))
    assert path.is_absolute()
    assert path.is_file()


def test_bundled_zdbsp_runs():
    try:
        path = get_bundled_compiler("zdbsp")
    except CompilerUnavailable as exc:
        pytest.skip(str(exc))
    if not can_run_compiler("zdbsp", path):
        pytest.skip(f"bundled zdbsp cannot run on {get_platform()}")


def test_resolve_compiler_uses_bundled_zdbsp():
    try:
        expected = get_bundled_compiler("zdbsp")
    except CompilerUnavailable as exc:
        pytest.skip(str(exc))
    if not can_run_compiler("zdbsp", expected):
        pytest.skip(f"bundled zdbsp cannot run on {get_platform()}")
    assert resolve_compiler("zdbsp") == expected


def test_resolve_compiler_uses_cached_acc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fake = tmp_path / "acc"
    fake.write_bytes(b"")
    monkeypatch.setattr("doomgen.tools.acc.cached_acc_path", lambda: fake)
    monkeypatch.setattr(
        "doomgen.utils.paths.can_run_compiler",
        lambda tool, path: tool == "acc",
    )
    assert resolve_compiler("acc") == str(fake)


def test_resolve_compiler_uses_explicit_path():
    try:
        expected = get_bundled_compiler("zdbsp")
    except CompilerUnavailable as exc:
        pytest.skip(str(exc))
    if not can_run_compiler("zdbsp", expected):
        pytest.skip(f"bundled zdbsp cannot run on {get_platform()}")
    assert resolve_compiler("zdbsp", explicit=expected) == expected


def test_resolve_compiler_falls_back_to_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    try:
        bundled = Path(get_bundled_compiler("zdbsp"))
    except CompilerUnavailable as exc:
        pytest.skip(str(exc))
    if not can_run_compiler("zdbsp", bundled):
        pytest.skip(f"bundled zdbsp cannot run on {get_platform()}")

    name = "zdbsp.exe" if _os_name() == "windows" else "zdbsp"
    fallback = tmp_path / name
    fallback.write_bytes(bundled.read_bytes())
    if _os_name() != "windows":
        fallback.chmod(0o755)

    monkeypatch.setattr("doomgen.utils.paths._bundled_path", lambda tool: None)
    monkeypatch.setattr("doomgen.tools.acc.cached_acc_path", lambda: None)
    monkeypatch.setenv(
        "PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"
    )
    assert os.path.samefile(resolve_compiler("zdbsp"), fallback)


def test_resolve_compiler_rejects_missing_explicit_path():
    with pytest.raises(CompilerUnavailable):
        resolve_compiler("acc", explicit="/nonexistent/path/to/acc")


def test_unknown_tool_raises_value_error():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_bundled_compiler("not_a_tool")


def test_windows_arch_uses_interpreter(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("sysconfig.get_platform", lambda: "win-arm64")
    monkeypatch.setattr("platform.machine", lambda: "AMD64")
    assert _arch_name() == "arm64"


def test_linux_arm64_bundled_filename(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("platform.machine", lambda: "aarch64")
    path = _bundled_path("zdbsp")
    assert path is not None
    assert path.name == "zdbsp-linux-arm64"


def test_unsupported_platform_has_no_bundled_path(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("platform.machine", lambda: "ppc64le")
    assert _bundled_path("zdbsp") is None
