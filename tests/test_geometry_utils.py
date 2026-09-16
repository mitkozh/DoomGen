"""Geometry helpers: paths and void rings used to shape encounters."""

from __future__ import annotations

import pytest
from shapely.geometry import LineString, Point

from doomgen.geometry.seeds import Seed
from doomgen.utils.geometry_utils import add_void_ring, create_wavy_path


class TestWavyPath:
    def test_endpoints_and_point_count(self):
        points = create_wavy_path((0, 0), (100, 0), num_points=10, amplitude=20)

        assert len(points) == 11
        assert points[0] == pytest.approx((0, 0))
        assert points[-1] == pytest.approx((100, 0))

    def test_wave_offsets_perpendicular(self):
        points = create_wavy_path((0, 0), (100, 0), num_points=4, amplitude=40)

        assert any(y != 0 for _, y in points[1:-1])

    def test_zero_length_returns_ends(self):
        assert create_wavy_path((5, 5), (5, 5)) == [(5, 5), (5, 5)]


class TestVoidRing:
    def test_ring_seeds_are_void_boundary(self):
        seeds: list[Seed] = []
        add_void_ring(seeds, 0, 0, radius=128)

        assert seeds, "no ring seeds added"
        assert all(s.area_id == "VOID" and s.is_boundary for s in seeds)
        for s in seeds:
            assert abs(Point(s.x, s.y).distance(Point(0, 0)) - 128) < 32

    def test_path_exclusion_leaves_gap(self):
        line = [(0, -200), (0, 200)]
        full: list[Seed] = []
        add_void_ring(full, 0, 0, radius=128)
        gapped: list[Seed] = []
        add_void_ring(gapped, 0, 0, radius=128, exclude_paths=[(line, 64)])

        assert 0 < len(gapped) < len(full)
        path = LineString(line)
        assert all(path.distance(Point(s.x, s.y)) >= 32 + 16 for s in gapped)
