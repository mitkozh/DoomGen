# API module
"""
High-level API for map construction.

This module provides the user-facing API for building Doom maps.

Two API Levels
--------------
1. **MapBuilder** (Mid-level): CSG-based geometry construction
   Located in geometry.builder - pure geometry, no Doom knowledge
   
       from doomgen import MapBuilder, create_rectangle
       
       builder = MapBuilder()
       builder.add_room("hub", create_rectangle(512, 512))
       builder.add_corridor("hub", "arena", width=64)
       result = builder.build()
       
       # Use with MapEditor manually...

2. **DoomMapBuilder** (High-level): Full declarative API

       from doomgen import DoomMapBuilder
       
       builder = DoomMapBuilder()
       builder.add_room("spawn", width=256, height=256)
       builder.connect("spawn", "arena")
       builder.add_door_between("spawn", "arena")
       builder.add_lift("arena", position=(100, 0))
       builder.add_crusher("arena", position=(200, 0))
       builder.add_damage_floor("arena", damage_type="lava")
       builder.add_lighting("arena", effect="flicker")
       builder.add_player_start("spawn")
       builder.save("output/my_map.wad")
"""

# Import from geometry.builder (pure geometry)
from doomgen.geometry.builder import (
    # MapBuilder (mid-level API)
    MapBuilder,
    BuildResult,
    SlotInfo,
    SlotType,
    CorridorInfo,
    
    # Geometry helpers
    create_corridor_between,
    create_cutout_polygon,
)

# Import from doom_map (high-level API)
from doomgen.api.doom_map import (
    # DoomMapBuilder (high-level API)
    DoomMapBuilder,
    RoomConfig,
    CorridorConfig,
    DoomDoorConfig,
    DoomLiftConfig,
    DoomCrusherConfig,
    DoomDamageConfig,
    DoomLightConfig,
    DoomStairConfig,
    RoomInfo,
    PrefabInfo,
    create_simple_map,
)

__all__ = [
    # MapBuilder (mid-level) - from geometry.builder
    "MapBuilder",
    "BuildResult",
    "SlotInfo",
    "SlotType",
    "CorridorInfo",
    
    # Geometry helpers
    "create_corridor_between",
    "create_cutout_polygon",
    
    # DoomMapBuilder (high-level) - from doom_map
    "DoomMapBuilder",
    "RoomConfig",
    "CorridorConfig", 
    "DoomDoorConfig",
    "DoomLiftConfig",
    "DoomCrusherConfig",
    "DoomDamageConfig",
    "DoomLightConfig",
    "DoomStairConfig",
    "RoomInfo",
    "PrefabInfo",
    "create_simple_map",
]
