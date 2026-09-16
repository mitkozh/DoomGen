"""Check bundled ACC/ZDBSP binaries resolve to real files."""

from pathlib import Path

import pytest

from doomgen.utils.paths import get_bundled_compiler, validate_executable


@pytest.mark.parametrize("tool", ["acc", "zdbsp"])
def test_bundled_tool_resolves_to_existing_absolute_file(tool: str) -> None:
    path = Path(get_bundled_compiler(tool))
    assert path.is_absolute()
    assert path.is_file(), f"bundled {tool} not found at {path}"


@pytest.mark.parametrize("tool", ["acc", "zdbsp"])
def test_bundled_tool_passes_executable_validation(tool: str) -> None:
    assert validate_executable(get_bundled_compiler(tool)) is True


def test_resolved_filename_matches_requested_tool() -> None:
    assert Path(get_bundled_compiler("acc")).stem == "acc"
    assert Path(get_bundled_compiler("zdbsp")).stem == "zdbsp"


def test_unknown_tool_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        get_bundled_compiler("not_a_tool")


def test_validate_executable_accepts_real_file(tmp_path: Path) -> None:
    marker = tmp_path / "tool"
    marker.write_bytes(b"")
    assert validate_executable(str(marker)) is True


def test_validate_executable_rejects_missing_path() -> None:
    assert validate_executable("/nonexistent/path/to/tool") is False
