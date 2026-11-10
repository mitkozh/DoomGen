"""Polyobjects: moving doors, lifts, and crushers for platform scenarios."""

from __future__ import annotations

from doomgen.doom.polyobjects import (
    POLYOBJ_ANCHOR_THING,
    PolyobjectBuilder,
    PolyobjectConfig,
)
from doomgen.doom.specials import LinedefFlags, PolyobjAction
from doomgen.doom.wad import DoomMapData


def builder() -> tuple[DoomMapData, PolyobjectBuilder]:
    data = DoomMapData("MAP01")
    return data, PolyobjectBuilder(data)


class TestPolyobjectRect:
    def test_rect_builds_closed_shell_with_start_line(self):
        data, poly = builder()
        poly.add_rect(PolyobjectConfig(number=1, center=(0, 0), width=128, height=64))

        start_lines = [
            ld for ld in data.linedefs if ld["special"] == PolyobjAction.START_LINE
        ]
        assert len(start_lines) == 1
        assert len(data.linedefs) == 4
        assert all(ld["flags"] & LinedefFlags.BLOCKING for ld in data.linedefs)

    def test_rect_places_anchor_and_start_spot(self):
        data, poly = builder()
        poly.add_rect(
            PolyobjectConfig(number=3, center=(100, 200), width=64, height=64)
        )

        things = {t["type"]: t for t in data.things}
        assert things[POLYOBJ_ANCHOR_THING]["tid"] == 3
        assert things[POLYOBJ_ANCHOR_THING]["angle"] == 3
        assert (
            things[POLYOBJ_ANCHOR_THING]["x"],
            things[POLYOBJ_ANCHOR_THING]["y"],
        ) == (100, 200)

    def test_rect_sector_uses_config(self):
        data, poly = builder()
        sector = poly.add_rect(
            PolyobjectConfig(
                number=1,
                center=(0, 0),
                width=64,
                height=64,
                floor_height=16,
                texture="BROWN1",
            )
        )

        assert data.sectors[sector]["floor_height"] == 16
        assert data.sectors[sector]["floor_texture"] == "BROWN1"


class TestPolyobjectTriggers:
    def test_move_trigger_carries_action_and_args(self):
        data, poly = builder()
        poly.add_move_trigger(
            number=2, speed=32, angle=0, distance=256, x=-4096, y=-4096
        )

        line = data.linedefs[0]
        assert line["special"] == PolyobjAction.OR_MOVE
        assert [line[f"arg{i}"] for i in range(4)] == [2, 32, 0, 256]
        assert line["flags"] & LinedefFlags.NOT_ON_MAP

    def test_rotate_direction_selects_action(self):
        for clockwise, expected in (
            (True, PolyobjAction.OR_ROTATE_RIGHT),
            (False, PolyobjAction.OR_ROTATE_LEFT),
        ):
            data, poly = builder()
            poly.add_rotate_trigger(
                number=1, speed=16, angle=90, clockwise=clockwise, x=-4096, y=-4096
            )

            assert data.linedefs[0]["special"] == expected
