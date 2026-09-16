"""Resolve bundled ACC/ZDBSP binaries (installed package first, source checkout fallback)."""

import shutil
import sys
from functools import lru_cache
from pathlib import Path


def _package_dir() -> Path:
    """Directory of the installed ``doomgen`` package."""
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    current = Path(__file__).resolve().parent
    # Traverse upward to find project root
    # The structure is: DoomGen/src/doomgen/utils/paths.py
    # So we need to go up 3 levels to reach DoomGen/
    while current != current.parent:
        # Check if this is the project root (has 'src' directory)
        if (current / "src").is_dir() and (current / "pyproject.toml").is_file():
            return current
        current = current.parent
    raise RuntimeError("Cannot determine project root. Expected to find 'src' directory and 'pyproject.toml' at the project root.")


def get_bundled_compiler(tool_name: str) -> str:
    if tool_name not in ["acc", "zdbsp"]:
        raise ValueError(f"Unknown tool: {tool_name}")

    is_windows = sys.platform == "win32" or sys.platform == "cygwin"
    exe_ext = ".exe" if is_windows else ""

    # Installed-package layout first: <site-packages>/doomgen/bin/<tool>/<exe>
    packaged = _package_dir() / "bin" / tool_name / f"{tool_name}{exe_ext}"
    if packaged.is_file():
        return str(packaged.resolve())

    # Source-checkout layout: <project-root>/<tool>/<exe>
    project_root = get_project_root()
    tool_path = project_root / tool_name / f"{tool_name}{exe_ext}"
    return str(tool_path.resolve())


def validate_executable(executable_path: str) -> bool:
    resolved = shutil.which(executable_path)
    if resolved is not None:
        return True
    executable_path_obj = Path(executable_path)
    return executable_path_obj.exists() and executable_path_obj.is_file()
