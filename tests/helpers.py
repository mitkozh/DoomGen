"""Shared fixtures for the DoomGen test suite: small fast builders and WAD readers."""

from __future__ import annotations

from pathlib import Path

from doomgen.builder import ProceduralMapBuilder
from doomgen.utils.paths import (
    CompilerUnavailable,
    can_run_compiler,
    resolve_compiler,
)


def compiler_runs(tool: str) -> bool:
    """Whether a usable compiler is available on this platform."""
    try:
        path = resolve_compiler(tool)
    except CompilerUnavailable:
        return False
    return can_run_compiler(tool, path)


def zdbsp_runs() -> bool:
    return compiler_runs("zdbsp")


def acc_runs() -> bool:
    return compiler_runs("acc")


def make_builder(num_seeds: int = 150, seed: int = 42) -> ProceduralMapBuilder:
    """Small-map builder. Keeps Voronoi relaxation and ZDBSP runs fast."""
    return ProceduralMapBuilder(bounds=(-512, -512, 512, 512), num_seeds=num_seeds, seed=seed)


def two_room_builder() -> ProceduralMapBuilder:
    """Two rooms sharing a mesh boundary along x=0."""
    builder = make_builder(num_seeds=300)
    builder.add_area("room_a", (-128, 0, 256, 256))
    builder.add_area("room_b", (128, 0, 256, 256))
    return builder


def build_wad(builder: ProceduralMapBuilder, path: str | Path) -> Path:
    """Build the builder's map to `path` and return it."""
    builder.build(str(path))
    return Path(path)


def map_lumps(wad_path: str | Path) -> list[str]:
    """Lump names of MAP01 in a built WAD."""
    from omg import WAD as OMGWAD

    return list(OMGWAD(str(wad_path)).maps["MAP01"])
