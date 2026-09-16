"""WAD layer: map data assembly, file output, and the ZDBSP hook."""

from __future__ import annotations

import pytest

from doomgen.doom.things import ThingType
from doomgen.doom.wad import DoomMapData, WADWriter, run_zdbsp
from doomgen.utils.validation import validate_wad

from .helpers import map_lumps


class TestDoomMapData:
    def test_vertices_deduplicate_after_rounding(self):
        data = DoomMapData("MAP01")

        assert data.add_vertex(100, 200) == 0
        assert data.add_vertex(100, 200) == 0
        assert data.add_vertex(100.4, 200.49) == 0
        assert data.add_vertex(300, 400) == 1

    def test_sectors_sidedefs_linedefs_index_in_order(self):
        data = DoomMapData("MAP01")

        assert data.add_sector(floor_height=64) == 0
        assert data.add_sector() == 1
        assert data.add_sidedef(sector=0) == 0
        v0 = data.add_vertex(0, 0)
        v1 = data.add_vertex(64, 0)
        assert data.add_linedef(v0, v1, front_sidedef=0) == 0

        assert data.sectors[0]["floor_height"] == 64
        assert data.linedefs[0]["back_sidedef"] == -1

    def test_linedef_args_truncate_to_five(self):
        data = DoomMapData("MAP01")
        data.add_linedef(0, 1, 0, args=[1, 2, 3, 4, 5, 6])

        line = data.linedefs[0]
        assert [line[f"arg{i}"] for i in range(5)] == [1, 2, 3, 4, 5]
        assert "arg5" not in line

    def test_things_round_coords_and_expand_args(self):
        data = DoomMapData("MAP01")
        data.add_thing(x=10.6, y=20.4, thing_type=1, angle=90)
        data.add_thing(x=0, y=0, thing_type=3001, args=[1, 2])

        assert (data.things[0]["x"], data.things[0]["y"]) == (11, 20)
        assert data.things[0]["angle"] == 90
        assert (data.things[1]["arg0"], data.things[1]["arg1"]) == (1, 2)

    def test_add_thing_accepts_thing_type_enum(self):
        data = DoomMapData("MAP01")
        data.add_thing(x=0, y=0, thing_type=ThingType.PLAYER1_START)

        assert data.things[0]["type"] == ThingType.PLAYER1_START == 1


class TestWADWriter:
    def test_create_duplicate_map_raises(self):
        writer = WADWriter()
        writer.create_map("MAP01")

        with pytest.raises(ValueError, match="already exists"):
            writer.create_map("MAP01")

    def test_get_missing_map_raises(self):
        with pytest.raises(KeyError, match="does not exist"):
            WADWriter().get_map("MAP01")

    def test_save_creates_parents_and_valid_wad(self, tmp_path):
        writer = WADWriter()
        data = writer.create_map("MAP01")
        data.add_sector()
        data.add_thing(x=0, y=0, thing_type=1)

        wad = tmp_path / "sub" / "dir" / "map.wad"
        writer.save(wad)

        assert wad.is_file()
        valid, issues = validate_wad(wad)
        assert valid, issues
        assert "THINGS" in map_lumps(wad)

    def test_hexen_behavior_embeds_behavior_lump(self, tmp_path):
        writer = WADWriter()
        writer.create_map("MAP01").behavior = b"BEHAV"

        wad = tmp_path / "hexen.wad"
        writer.save(wad)

        assert "BEHAVIOR" in map_lumps(wad)

    def test_add_lump_roundtrips(self, tmp_path):
        from omg import WAD as OMGWAD

        writer = WADWriter()
        writer.create_map("MAP01")
        writer.add_lump("MYLUMP", b"hello")

        wad = tmp_path / "lump.wad"
        writer.save(wad)

        assert "MYLUMP" in OMGWAD(str(wad)).data


class TestRunZdbsp:
    def test_missing_tool_returns_false(self):
        assert run_zdbsp("dummy.wad", zdbsp_path="/nonexistent/zdbsp") is False
