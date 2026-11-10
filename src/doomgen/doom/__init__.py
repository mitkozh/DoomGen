"""Doom-specific structures and WAD helpers."""

from doomgen.doom.config import (
    PrefabDoomConfig,
    SectorConfig,
    WallConfig,
)
from doomgen.doom.polyobjects import (
    PolyobjectBuilder,
    PolyobjectConfig,
)
from doomgen.doom.specials import (
    CeilingAction,
    CrusherAction,
    DoorAction,
    ExitAction,
    FloorAction,
    LiftAction,
    LightAction,
    LinedefFlags,
    PolyobjAction,
    SectorSpecial,
    StairAction,
    TeleportAction,
)
from doomgen.doom.tags import TagRegistry
from doomgen.doom.things import ThingType
from doomgen.doom.translator import MapTranslator
from doomgen.doom.wad import WADWriter, run_zdbsp

__all__ = [
    "SectorConfig",
    "WallConfig",
    "PrefabDoomConfig",
    "WADWriter",
    "run_zdbsp",
    "MapTranslator",
    "ThingType",
    "TagRegistry",
    "LinedefFlags",
    "DoorAction",
    "LiftAction",
    "TeleportAction",
    "FloorAction",
    "CeilingAction",
    "CrusherAction",
    "StairAction",
    "ExitAction",
    "LightAction",
    "SectorSpecial",
    "PolyobjAction",
    "PolyobjectBuilder",
    "PolyobjectConfig",
]
