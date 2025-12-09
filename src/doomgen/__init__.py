"""
DoomGen - Voronoi-first procedural Doom map generation library.
"""

__version__ = "0.2.0"

# Abstract Layer
from doomgen.abstraction.layout import (
    LayoutGraph, 
    Area, 
    AreaConfig, 
    Transform, 
    SeedStrategy, 
    ConnectionType,
    Prefab
)

# Geometry Layer
from doomgen.geometry.seeds import SeedEngine, StencilLibrary
from doomgen.geometry.mesh import VoronoiMesh

# Doom Layer
from doomgen.doom.wad import WADWriter, DoomMapData
from doomgen.doom.translator import MapTranslator
from doomgen.doom.things import ThingType

# Builder Layer
from doomgen.builder import ProceduralMapBuilder as MapBuilder

__all__ = [
    "LayoutGraph", "Area", "AreaConfig", "Transform", "SeedStrategy", "ConnectionType",
    "SeedEngine", "StencilLibrary",
    "VoronoiMesh",
    "WADWriter", "DoomMapData", "MapTranslator", "ThingType",
    "MapBuilder"
]
