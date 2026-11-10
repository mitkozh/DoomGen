"""Linedef actions and flags: values the translator emits into the WAD."""

from __future__ import annotations

from doomgen.doom.specials import DoorAction, LiftAction, LinedefFlags, SectorSpecial


class TestLinedefFlags:
    def test_core_bits(self):
        assert LinedefFlags.BLOCKING == 1
        assert LinedefFlags.TWO_SIDED == 4

    def test_flags_combine(self):
        combo = LinedefFlags.BLOCKING | LinedefFlags.TWO_SIDED

        assert combo & LinedefFlags.BLOCKING
        assert combo & LinedefFlags.TWO_SIDED
        assert not (combo & LinedefFlags.SECRET)


class TestActions:
    def test_manual_door_action_matches_translator_output(self):
        assert DoorAction.DR_OPEN_WAIT_CLOSE == 1

    def test_keyed_doors_are_distinct(self):
        assert (
            len(
                {
                    DoorAction.D1_BLUE_DOOR,
                    DoorAction.D1_RED_DOOR,
                    DoorAction.D1_YELLOW_DOOR,
                }
            )
            == 3
        )

    def test_lift_and_sector_specials_defined(self):
        assert LiftAction.SR_LIFT == 62
        assert SectorSpecial.BLINK_HALF_SEC == 2
