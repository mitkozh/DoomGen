"""Validation helpers: grid snapping, polygon checks, and WAD sanity."""

from __future__ import annotations

from shapely.geometry import LineString, MultiPolygon, box

from doomgen.utils.validation import (
    check_sector_closure,
    ensure_polygon,
    estimate_bsp_complexity,
    make_valid,
    snap_polygon_to_grid,
    snap_to_grid,
    to_integer_coords,
    validate_corridor_width,
    validate_polygon,
    validate_thing_placement,
    validate_wad,
)

from .helpers import build_wad, make_builder


class TestSnapping:
    def test_snap_to_grid(self):
        assert snap_to_grid(10, 8) == 8
        assert snap_to_grid(13, 8) == 16
        assert snap_to_grid(-10, 8) == -8

    def test_snap_polygon_to_grid(self):
        snapped = snap_polygon_to_grid(box(1, 1, 10, 10), grid_size=8)

        assert all(x % 8 == 0 and y % 8 == 0 for x, y in snapped.exterior.coords)

    def test_to_integer_coords(self):
        result = to_integer_coords(box(0.4, 0.6, 10.2, 10.8))

        assert all(float(x).is_integer() for x, y in result.exterior.coords for x in (x,))


class TestPolygons:
    def test_clean_box_is_valid(self):
        assert validate_polygon(box(0, 0, 100, 100)) == (True, [])

    def test_tiny_sector_rejected(self):
        valid, issues = validate_polygon(box(0, 0, 4, 4))

        assert not valid
        assert any("too small" in i for i in issues)

    def test_self_intersecting_rejected(self):
        from shapely.geometry import Polygon

        bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])

        assert not bowtie.is_valid
        assert validate_polygon(bowtie)[0] is False

    def test_make_valid_repairs_self_intersection(self):
        from shapely.geometry import Polygon

        bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])

        assert make_valid(bowtie).is_valid

    def test_out_of_bounds_rejected(self):
        valid, issues = validate_polygon(box(0, 0, 100_000, 100))

        assert not valid
        assert any("out of bounds" in i for i in issues)

    def test_empty_polygon_rejected(self):
        from shapely.geometry import Polygon

        assert validate_polygon(Polygon()) == (False, ["Polygon is empty"])

    def test_ensure_polygon_picks_largest(self):
        multi = MultiPolygon([box(0, 0, 10, 10), box(0, 0, 100, 100)])

        assert ensure_polygon(multi).area == 10_000

    def test_ensure_polygon_rejects_non_polygons(self):
        import pytest

        with pytest.raises(ValueError):
            ensure_polygon(LineString([(0, 0), (1, 1)]))


class TestThingPlacement:
    ROOM = box(0, 0, 200, 200)

    def test_center_is_valid(self):
        assert validate_thing_placement(100, 100, self.ROOM) == (True, "Valid")

    def test_outside_is_invalid(self):
        valid, reason = validate_thing_placement(500, 500, self.ROOM)

        assert not valid
        assert reason == "Position is outside sector"

    def test_near_wall_is_invalid(self):
        valid, reason = validate_thing_placement(10, 100, self.ROOM, radius=16.0)

        assert not valid
        assert reason == "Too close to walls"


class TestCorridorWidth:
    def test_wide_corridor_passes(self):
        assert validate_corridor_width(box(0, 0, 200, 200))[0] is True

    def test_narrow_corridor_reports_width(self):
        valid, width = validate_corridor_width(box(0, 0, 10, 200), min_width=64)

        assert valid is False
        assert 0 < width < 64


class TestSectorClosure:
    def test_closed_loop_passes(self):
        assert check_sector_closure([(0, 0), (10, 0), (10, 10), (0, 0)])[0] is True

    def test_open_loop_fails(self):
        assert check_sector_closure([(0, 0), (10, 0), (50, 50)])[0] is False

    def test_too_few_vertices_fails(self):
        assert check_sector_closure([(0, 0), (1, 1)])[0] is False


class TestEstimateComplexity:
    def test_box_metrics(self):
        metrics = estimate_bsp_complexity(box(0, 0, 100, 100))

        assert metrics["vertex_count"] == 4
        assert metrics["hole_count"] == 0
        assert metrics["convexity_ratio"] == 1.0


class TestValidateWad:
    def test_missing_file(self):
        valid, issues = validate_wad("/nonexistent/map.wad")

        assert (valid, issues) == (False, ["File does not exist"])

    def test_garbage_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.wad"
            bad.write_bytes(b"GARBAGE-DATA-HERE!!!")
            valid, issues = validate_wad(bad)

        assert not valid
        assert issues

    def test_built_map_is_valid(self, tmp_path):
        builder = make_builder()
        builder.add_area("hall", (0, 0, 256, 256))
        builder.add_thing("PLAYER1_START", 0, 0)
        wad = build_wad(builder, tmp_path / "map.wad")

        assert validate_wad(wad) == (True, [])
