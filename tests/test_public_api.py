"""Public package surface: exports, alias, and version."""

from __future__ import annotations

import tomllib
from pathlib import Path

import doomgen
from doomgen.builder import ProceduralMapBuilder


def test_map_builder_alias():
    assert doomgen.MapBuilder is ProceduralMapBuilder


def test_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    expected = tomllib.load(pyproject.open("rb"))["project"]["version"]

    assert doomgen.__version__ == expected


def test_all_exports_importable():
    for name in doomgen.__all__:
        assert getattr(doomgen, name) is not None
