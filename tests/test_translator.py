"""Map translation: mesh areas become sectors, shared edges become linedefs."""

from __future__ import annotations

from doomgen.abstraction.layout import ConnectionType
from doomgen.doom.specials import DoorAction, LinedefFlags

from .helpers import build_wad, two_room_builder


def blocking(lines: list[dict]) -> list[dict]:
    return [ld for ld in lines if ld["flags"] & LinedefFlags.BLOCKING]


def two_sided(lines: list[dict]) -> list[dict]:
    return [ld for ld in lines if ld["flags"] & LinedefFlags.TWO_SIDED]


class TestTranslation:
    def test_open_join_produces_two_sided_portals(self, tmp_path):
        builder = two_room_builder()
        builder.connect_adjacent("room_a", "room_b", ConnectionType.OPEN)
        build_wad(builder, tmp_path / "open.wad")

        portals = two_sided(builder.map_data.linedefs)
        assert portals, "no two-sided portal between joined rooms"
        assert all(ld["back_sidedef"] != -1 for ld in portals)

    def test_map_edge_produces_blocking_walls(self, tmp_path):
        builder = two_room_builder()
        build_wad(builder, tmp_path / "walls.wad")

        walls = blocking(builder.map_data.linedefs)
        assert walls, "no blocking walls around the map"
        assert all(ld["back_sidedef"] == -1 for ld in walls)

    def test_door_sector_gets_manual_door_action(self, tmp_path):
        builder = two_room_builder()
        builder.add_boundary(
            "room_a",
            "room_b",
            name="door",
            floor_height=0,
            ceiling_height=0,
            connection_type=ConnectionType.DOOR,
        )
        build_wad(builder, tmp_path / "door.wad")

        assert any(
            ld["special"] == DoorAction.DR_OPEN_WAIT_CLOSE
            for ld in builder.map_data.linedefs
        )

    def test_window_join_uses_grate_mid_texture(self, tmp_path):
        builder = two_room_builder()
        builder.connect_adjacent("room_a", "room_b", ConnectionType.WINDOW)
        build_wad(builder, tmp_path / "window.wad")

        assert any(
            sd.get("middle_texture") == "MIDGRATE" for sd in builder.map_data.sidedefs
        )

    def test_area_heights_land_in_sectors(self, tmp_path):
        builder = two_room_builder()
        builder.graph.get_area(builder.name_to_id["room_b"]).config.floor_height = 64
        build_wad(builder, tmp_path / "heights.wad")

        assert [s["floor_height"] for s in builder.map_data.sectors] == [0, 64]
