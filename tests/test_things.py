"""Thing catalog: IDs and groupings the generators place on maps."""

from __future__ import annotations

from doomgen.doom.things import (
    ALL_KEYS,
    ALL_WEAPONS,
    ARMOR_ITEMS,
    BOSS_ENEMIES,
    EASY_ENEMIES,
    HARD_ENEMIES,
    HEALTH_ITEMS,
    MEDIUM_ENEMIES,
    PLAYER_STARTS,
    ThingType,
    get_thing_radius,
)


class TestThingIds:
    def test_player_starts_are_1_to_4(self):
        assert [t.value for t in PLAYER_STARTS[:4]] == [1, 2, 3, 4]

    def test_translator_player_start_matches_catalog(self):
        from doomgen.doom.wad import DoomMapData
        from doomgen.doom.translator import MapTranslator

        data = DoomMapData("MAP01")
        MapTranslator(data).add_player_start("area", 10, 20)

        assert data.things[0]["type"] == ThingType.PLAYER1_START == 1

    def test_builder_fallback_matches_shotgun(self):
        assert ThingType.SHOTGUN.value == 2001

    def test_map_spot_for_acs_spawns(self):
        assert ThingType.MAP_SPOT.value == 9001


class TestRadiusTiers:
    def test_large_bosses_need_wide_rooms(self):
        assert get_thing_radius(ThingType.CYBERDEMON) == 48

    def test_medium_enemies_share_tier(self):
        assert get_thing_radius(ThingType.CACODEMON) == 31
        assert get_thing_radius(ThingType.BARON_OF_HELL) == 31

    def test_small_actors_default(self):
        assert get_thing_radius(ThingType.IMP) == 16
        assert get_thing_radius(ThingType.PLAYER1_START) == 16


class TestGroupings:
    def test_difficulty_ladder_covers_distinct_sets(self):
        assert ThingType.IMP in EASY_ENEMIES
        assert ThingType.DEMON in MEDIUM_ENEMIES
        assert ThingType.REVENANT in HARD_ENEMIES
        assert ThingType.CYBERDEMON in BOSS_ENEMIES
        assert not (set(EASY_ENEMIES) & set(BOSS_ENEMIES))

    def test_pickup_groups(self):
        assert ThingType.SHOTGUN in ALL_WEAPONS
        assert ThingType.MEDIKIT in HEALTH_ITEMS
        assert ThingType.GREEN_ARMOR in ARMOR_ITEMS
        assert ThingType.BLUE_KEYCARD in ALL_KEYS
