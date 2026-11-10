"""Builder pipeline: areas, connections, things, placement, and WAD output."""

from __future__ import annotations

import warnings

import pytest
from shapely.geometry import Point, box

from doomgen.abstraction.layout import ConnectionType
from doomgen.builder import ProceduralMapBuilder
from doomgen.utils.validation import validate_wad

from .helpers import build_wad, make_builder, map_lumps, two_room_builder, zdbsp_runs


def claimed(builder: ProceduralMapBuilder, area_id: str) -> list:
    return [s for s in builder.seeds if s.area_id == area_id]


class TestAreas:
    def test_add_area_claims_cells_inside_shape(self):
        builder = make_builder()
        area_id = builder.add_area("hall", (0, 0, 256, 256))

        assert area_id == builder.name_to_id["hall"]
        cells = claimed(builder, area_id)
        assert cells, "area claimed no cells"
        poly = box(-128, -128, 128, 128)
        assert all(poly.contains(Point(s.x, s.y)) for s in cells)

    def test_add_area_outside_bounds_warns(self):
        builder = make_builder()
        with pytest.warns(UserWarning, match="claimed 0 seeds"):
            area_id = builder.add_area("void", (5000, 5000, 10, 10))

        assert claimed(builder, area_id) == []

    def test_claim_void_does_not_steal_cells(self):
        builder = make_builder()
        first = builder.add_area("a", (0, 0, 256, 256))
        before = len(claimed(builder, first))

        with pytest.warns(UserWarning, match="claimed 0 seeds"):
            builder.add_area("b", (0, 0, 256, 256))

        assert len(claimed(builder, first)) == before

    def test_overwrite_reclaims_cells(self):
        builder = make_builder()
        builder.add_area("a", (0, 0, 256, 256))
        second = builder.add_area("b", (0, 0, 256, 256), mode="overwrite")

        assert claimed(builder, second), "overwrite claimed no cells"

    def test_set_void_releases_cells(self):
        builder = make_builder()
        area_id = builder.add_area("hall", (0, 0, 256, 256))
        builder.set_void((0, 0, 256, 256))

        assert claimed(builder, area_id) == []
        assert builder.get_random_point_in_area("hall") is None


class TestConnections:
    def test_corridor_links_distant_rooms(self):
        builder = make_builder(num_seeds=200)
        id_a = builder.add_area("a", (-300, 0, 128, 128))
        id_b = builder.add_area("b", (300, 0, 128, 128))

        corridor_id = builder.add_corridor("a", "b")

        assert corridor_id
        assert claimed(builder, corridor_id), "corridor claimed no cells"
        links = {(c.area_a_id, c.area_b_id) for c in builder.graph.connections}
        assert (id_a, corridor_id) in links
        assert (corridor_id, id_b) in links

    def test_corridor_missing_room_warns(self):
        builder = make_builder()
        with pytest.warns(UserWarning, match="no seeds"):
            assert builder.add_corridor("nope", "also-nope") == ""

    def test_boundary_needs_shared_edge(self):
        builder = make_builder(num_seeds=200)
        builder.add_area("a", (-300, 0, 128, 128))
        builder.add_area("b", (300, 0, 128, 128))

        with pytest.warns(UserWarning, match="No boundary"):
            assert builder.add_boundary("a", "b") == ""

    def test_boundary_creates_door_area(self):
        builder = two_room_builder()
        door_id = builder.add_boundary(
            "room_a", "room_b", name="door", connection_type=ConnectionType.DOOR
        )

        assert door_id == builder.name_to_id["door"]
        assert claimed(builder, door_id), "door claimed no cells"
        types = [c.type for c in builder.graph.connections]
        assert ConnectionType.DOOR in types

    def test_connect_adjacent_warns_when_separate(self):
        builder = make_builder(num_seeds=200)
        builder.add_area("a", (-300, 0, 128, 128))
        builder.add_area("b", (300, 0, 128, 128))

        with pytest.warns(UserWarning, match="not adjacent"):
            builder.connect_adjacent("a", "b")

    def test_connect_adjacent_silent(self):
        builder = make_builder(num_seeds=200)
        builder.add_area("a", (-300, 0, 128, 128))
        builder.add_area("b", (300, 0, 128, 128))

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            builder.connect_adjacent("a", "b", silent=True)


class TestStairs:
    def test_stairs_interpolate_floor_heights(self):
        builder = make_builder(num_seeds=200)
        builder.add_area("low", (-300, 0, 128, 128), floor_height=0)
        builder.add_area("high", (300, 0, 128, 128), floor_height=128)

        step_ids = builder.add_stairs("low", "high", num_steps=4)

        assert len(step_ids) == 4
        heights = [builder.graph.get_area(s).config.floor_height for s in step_ids]
        assert heights == [32, 64, 96, 128]
        assert all(claimed(builder, s) for s in step_ids)

    def test_stairs_more_steps_than_cells_warns(self):
        builder = make_builder(num_seeds=200)
        builder.add_area("low", (-300, 0, 128, 128), floor_height=0)
        builder.add_area("high", (300, 0, 128, 128), floor_height=128)

        with pytest.warns(UserWarning, match="Reducing steps"):
            step_ids = builder.add_stairs("low", "high", num_steps=10_000)

        assert 0 < len(step_ids) < 10_000

    def test_stairs_missing_room_returns_empty(self):
        builder = make_builder()
        builder.add_area("low", (-300, 0, 128, 128))
        with pytest.warns(UserWarning, match="with stairs"):
            assert builder.add_stairs("low", "ghost") == []


class TestThings:
    def test_add_thing_defaults(self):
        builder = make_builder()
        builder.add_thing("PLAYER1_START", 10, 20)

        (thing,) = builder.things_to_add
        assert (thing["type"], thing["x"], thing["y"]) == ("PLAYER1_START", 10, 20)
        assert thing.get("angle", 0) == 0
        assert thing.get("flags", 7) == 7

    def test_build_resolves_thing_names(self, tmp_path):
        builder = make_builder()
        builder.add_area("hall", (0, 0, 256, 256))
        builder.add_thing("PLAYER1_START", 0, 0)
        builder.add_thing(2001, 10, 10)
        builder.add_thing("2001", 20, 20)
        build_wad(builder, tmp_path / "things.wad")

        assert [t["type"] for t in builder.map_data.things] == [1, 2001, 2001]

    def test_unknown_thing_warns_and_defaults(self, tmp_path):
        builder = make_builder()
        builder.add_area("hall", (0, 0, 256, 256))
        builder.add_thing("NOT_A_THING", 0, 0)

        with pytest.warns(UserWarning, match="Unknown thing type"):
            build_wad(builder, tmp_path / "thing.wad")

        assert builder.map_data.things[0]["type"] == 2001


class TestPlacement:
    def test_random_point_lies_inside_area(self):
        builder = two_room_builder()
        point = builder.get_random_point_in_area("room_a")

        assert point is not None
        assert box(-256, -128, 0, 128).contains(Point(*point))

    def test_random_point_unknown_area_is_none(self):
        assert make_builder().get_random_point_in_area("ghost") is None

    def test_random_points_avoid_immediate_reuse(self):
        builder = make_builder(num_seeds=300)
        builder.add_area("hall", (0, 0, 512, 512))

        first = builder.get_random_point_in_area("hall")
        second = builder.get_random_point_in_area("hall")

        assert first is not None and second is not None
        assert first != second

    def test_centroid_near_room_center(self):
        builder = two_room_builder()
        x, y = builder.get_area_centroid("room_a")

        assert abs(x - -128) < 60
        assert abs(y - 0) < 60

    def test_centroid_unknown_area_is_none(self):
        assert make_builder().get_area_centroid("ghost") is None


class TestBuild:
    @pytest.mark.skipif(not zdbsp_runs(), reason="bundled ZDBSP cannot run here")
    def test_build_writes_valid_wad_with_nodes(self, tmp_path):
        builder = two_room_builder()
        builder.connect_adjacent("room_a", "room_b")
        builder.add_thing("PLAYER1_START", -128, 0)
        wad = build_wad(builder, tmp_path / "map.wad")

        assert wad.is_file()
        valid, issues = validate_wad(wad)
        assert valid, issues
        for lump in ("VERTEXES", "LINEDEFS", "SIDEDEFS", "SECTORS", "THINGS", "NODES"):
            assert lump in map_lumps(wad)

    def test_sector_count_matches_areas(self, tmp_path):
        builder = two_room_builder()
        build_wad(builder, tmp_path / "map.wad")

        assert len(builder.map_data.sectors) == len(builder.graph.areas) == 2

    def test_build_is_deterministic(self, tmp_path):
        def build(seed: int) -> bytes:
            builder = make_builder(seed=seed)
            builder.add_area("hall", (0, 0, 256, 256))
            builder.add_thing("PLAYER1_START", 0, 0)
            return build_wad(builder, tmp_path / f"map_{seed}.wad").read_bytes()

        assert build(7) == build(7)
        assert build(7) != build(8)

    def test_build_without_zdbsp_warns_but_writes(self, tmp_path):
        builder = make_builder()
        builder.add_area("hall", (0, 0, 256, 256))

        with pytest.warns(UserWarning, match="ZDBSP at '/nonexistent/zdbsp' failed"):
            builder.build(
                str(tmp_path / "nonodes.wad"), zdbsp_path="/nonexistent/zdbsp"
            )

        assert (tmp_path / "nonodes.wad").is_file()
