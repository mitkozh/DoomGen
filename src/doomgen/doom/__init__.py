# Doom module
"""Doom-specific structures and WAD file manipulation."""

from doomgen.doom.wad import WADWriter
from doomgen.doom.translator import MapEditor, SectorConfig, WallConfig
from doomgen.doom.things import ThingType
from doomgen.doom.tags import TagRegistry
from doomgen.doom.specials import (
    LinedefFlags, DoorAction, LiftAction, TeleportAction,
    FloorAction, CeilingAction, CrusherAction, StairAction,
    ExitAction, LightAction,
)

__all__ = [
    "WADWriter", "MapEditor", "SectorConfig", "WallConfig",
    "ThingType", "TagRegistry", "LinedefFlags",
    "DoorAction", "LiftAction", "TeleportAction",
    "FloorAction", "CeilingAction", "CrusherAction", 
    "StairAction", "ExitAction", "LightAction",
]
