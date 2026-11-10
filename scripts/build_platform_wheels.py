"""Build one DoomGen wheel per supported platform.

Each wheel contains only the compiler binaries for its target platform.
The sdist remains universal and is built separately with ``uv build --sdist``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "doomgen"
BIN = SRC / "bin"
DIST = ROOT / "dist"

TARGETS: dict[str, dict[str, tuple[str, ...]]] = {
    "win32": {
        "zdbsp": ("zdbsp-windows.exe", "zdbsp.html", "zdbsp-1.19-src.zip"),
    },
    "win_amd64": {
        "zdbsp": ("zdbsp-windows.exe", "zdbsp.html", "zdbsp-1.19-src.zip"),
    },
    "win_arm64": {
        "zdbsp": ("zdbsp-windows.exe", "zdbsp.html", "zdbsp-1.19-src.zip"),
    },
    "manylinux_2_28_x86_64": {
        "zdbsp": ("zdbsp-linux", "zdbsp.html", "zdbsp-1.19-src.zip"),
    },
    "manylinux_2_28_aarch64": {
        "zdbsp": ("zdbsp-linux-arm64", "zdbsp.html", "zdbsp-1.19-src.zip"),
    },
    "macosx_11_0_universal2": {
        "zdbsp": ("zdbsp-macos", "zdbsp.html", "zdbsp-1.19-src.zip"),
    },
}

_MACHO_CPUS = {
    7: "x86",
    12: "arm",
    0x01000007: "x86_64",
    0x0100000C: "arm64",
}


def _select_files(tool: str, patterns: tuple[str, ...]) -> list[Path]:
    selected: set[Path] = set()
    for pattern in patterns:
        matches = sorted((BIN / tool).glob(pattern))
        if not matches:
            raise SystemExit(f"no files match {tool}/{pattern}")
        selected.update(matches)
    return sorted(selected)


def _macho_arches(path: Path) -> set[str]:
    data = path.read_bytes()[:65536]
    thin = {
        b"\xcf\xfa\xed\xfe": "<",
        b"\xce\xfa\xed\xfe": "<",
        b"\xfe\xed\xfa\xcf": ">",
        b"\xfe\xed\xfa\xce": ">",
    }
    endian = thin.get(data[:4])
    if endian is not None and len(data) >= 8:
        cputype = struct.unpack_from(f"{endian}I", data, 4)[0]
        arch = _MACHO_CPUS.get(cputype)
        return {arch} if arch else set()

    fat = {
        b"\xca\xfe\xba\xbe": (">", 20),
        b"\xca\xfe\xba\xbf": (">", 32),
        b"\xbe\xba\xfe\xca": ("<", 20),
        b"\xbf\xba\xfe\xca": ("<", 32),
    }
    fat_info = fat.get(data[:4])
    if fat_info is None or len(data) < 8:
        return set()
    endian, entry_size = fat_info
    count = struct.unpack_from(f"{endian}I", data, 4)[0]
    arches: set[str] = set()
    for index in range(min(count, 32)):
        offset = 8 + index * entry_size
        if offset + 4 > len(data):
            break
        cputype = struct.unpack_from(f"{endian}I", data, offset)[0]
        arch = _MACHO_CPUS.get(cputype)
        if arch is not None:
            arches.add(arch)
    return arches


def _validate_target(platform_tag: str, target: dict[str, tuple[str, ...]]) -> None:
    if platform_tag != "macosx_11_0_universal2":
        return

    filename = next(
        name for name in target["zdbsp"] if name.startswith("zdbsp-macos")
    )
    arches = _macho_arches(BIN / "zdbsp" / filename)
    if arches != {"x86_64", "arm64"}:
        raise SystemExit(
            f"zdbsp/{filename} must be a universal2 binary, "
            f"found: {sorted(arches) or 'unknown'}"
        )


def _copy_project(project_dir: Path, platform_tag: str) -> None:
    for name in ("pyproject.toml", "setup.py", "README.md", "LICENSE"):
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, project_dir / name)

    shutil.copytree(
        SRC,
        project_dir / "src" / "doomgen",
        ignore=shutil.ignore_patterns("bin", "__pycache__"),
    )

    target = TARGETS[platform_tag]
    destination = project_dir / "src" / "doomgen" / "bin" / "zdbsp"
    destination.mkdir(parents=True, exist_ok=True)
    for source in _select_files("zdbsp", target["zdbsp"]):
        shutil.copy2(source, destination / source.name)


def _build_wheel(project_dir: Path, platform_tag: str) -> Path:
    DIST.mkdir(exist_ok=True)
    for stale in DIST.glob(f"doomgen-*-py3-none-{platform_tag}.whl"):
        stale.unlink()
    subprocess.run(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "--plat-name",
            platform_tag,
            "--dist-dir",
            str(DIST),
        ],
        cwd=project_dir,
        check=True,
        env={**os.environ, "DOOMGEN_PLATFORM_WHEEL": "1"},
    )
    wheels = sorted(DIST.glob(f"doomgen-*-py3-none-{platform_tag}.whl"))
    if not wheels:
        raise SystemExit(f"wheel for {platform_tag} was not created")
    return wheels[-1]


def _validate_wheel(wheel: Path, platform_tag: str) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        wheel_metadata = next(
            name for name in names if name.endswith(".dist-info/WHEEL")
        )
        metadata = archive.read(wheel_metadata).decode()
        if f"Tag: py3-none-{platform_tag}" not in metadata:
            raise SystemExit(f"{wheel.name} has the wrong wheel tag")

        expected = {
            f"doomgen/bin/zdbsp/{path.name}"
            for path in _select_files("zdbsp", TARGETS[platform_tag]["zdbsp"])
        }
        actual = {name for name in names if name.startswith("doomgen/bin/")}
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise SystemExit(f"{wheel.name} contents mismatch: {missing=} {extra=}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        choices=sorted(TARGETS),
        help="target platform tag; may be repeated (default: all)",
    )
    args = parser.parse_args()

    selected = args.target or sorted(TARGETS)
    for platform_tag in selected:
        _validate_target(platform_tag, TARGETS[platform_tag])
        with tempfile.TemporaryDirectory(prefix="doomgen-wheel-") as temp_dir:
            project_dir = Path(temp_dir)
            _copy_project(project_dir, platform_tag)
            wheel = _build_wheel(project_dir, platform_tag)
            _validate_wheel(wheel, platform_tag)
            print(wheel.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
