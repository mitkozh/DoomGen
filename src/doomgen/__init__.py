"""
Doom map generation library.

High-level API::

Quick Start (DoomMapBuilder - High-level API)
----------------------------------------------
    from doomgen import DoomMapBuilder, ThingType
    
    builder = DoomMapBuilder()
    builder.add_room("spawn", width=256, height=256)
    builder.add_room("arena", width=512, height=512, center=(600, 0))
    builder.connect("spawn", "arena", corridor_width=64)
    builder.add_door_between("spawn", "arena")
    builder.add_lift("arena", position=(500, 0), upper_height=64)
    builder.add_crusher("arena", position=(550, 100))
    builder.add_damage_floor("arena", damage_type="lava")
    builder.add_lighting("arena", effect="flicker")
    builder.add_player_start("spawn")
    builder.add_enemies("arena", ThingType.IMP, count=4)
    builder.save("output/my_map.wad")

Mid-level API (MapBuilder)
--------------------------
    from doomgen import (
        WADWriter, MapEditor, MapBuilder, SectorConfig, ThingType, SlotType,
        create_rectangle
    )
    from doomgen.prefabs import DoorConfig, apply_door_to_sector
    
    # Build geometry
    builder = MapBuilder()
    builder.add_room("hub", create_rectangle(512, 512))
    builder.add_room("arena", create_rectangle(256, 256, center=(600, 0)))
    builder.add_corridor("hub", "arena", width=64)
    builder.add_slot("hub", (256, 0), width=64, slot_type=SlotType.DOOR)
    result = builder.build()
    
    # Create WAD
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    for name, poly in result.rooms.items():
        editor.add_sector_from_polygon(poly, SectorConfig())
    for corridor in result.corridors:
        editor.add_sector_from_polygon(corridor.polygon, SectorConfig())
    for slot in result.slots:
        if slot.slot_type == SlotType.DOOR:
            idx = editor.add_sector_from_polygon(slot.polygon, SectorConfig(ceiling_height=0))
            apply_door_to_sector(editor, idx, DoorConfig())
    
    editor.add_thing(0, 0, ThingType.PLAYER1_START)
    wad.save("output.wad")

Low-level API
-------------
For direct polygon manipulation without MapBuilder:

    from doomgen import (
        WADWriter, MapEditor, SectorConfig, ThingType,
        create_rectangle, cut_polygon
    )
    
    room = create_rectangle(512, 512)
    door = create_rectangle(64, 16, center=(256, 0))
    room_carved = cut_polygon(room, door)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    editor.add_sector_from_polygon(room_carved, SectorConfig())
    editor.add_sector_from_polygon(door, SectorConfig(ceiling_height=0))
    editor.add_thing(0, 0, ThingType.PLAYER1_START)
    wad.save("output.wad")
"""

__version__ = "0.1.0"

# =============================================================================
# Core WAD creation
# =============================================================================
from doomgen.doom.wad import WADWriter
from doomgen.doom.translator import MapEditor, SectorConfig, WallConfig
from doomgen.doom.things import ThingType

# =============================================================================
# Geometry - shape creation (pure geometry, no Doom knowledge)
# =============================================================================
from doomgen.geometry import (
    create_irregular_polygon,
    create_rectangle,
    create_polygon,
    create_corridor,
    ShapeBuilder,
)

# =============================================================================
# Geometry - CSG operations (pure geometry)
# =============================================================================
from doomgen.geometry import (
    cut_polygon,
    merge_polygons,
    snap_to_grid,
    ensure_polygon,
)

# =============================================================================
# Geometry - Procedural Modifiers (pure geometry)
# =============================================================================
from doomgen.geometry import (
    LSystemGenerator,
    GRAMMARS,
    create_lsystem_corridor,
    recursive_subdivision,
    subdivide_edge,
    add_noise_to_polygon,
)

# =============================================================================
# Geometry - MapBuilder (mid-level, CSG-based geometry orchestration)
# =============================================================================
from doomgen.geometry.builder import (
    MapBuilder,
    BuildResult,
    SlotInfo,
    SlotType,
    CorridorInfo,
    CorridorData,
    CorridorStyle,
    CorridorSlotRequest,
    create_corridor_between,
    create_cutout_polygon,
)

# =============================================================================
# Prefabs - Interactive gameplay elements
# =============================================================================
from doomgen.prefabs import (
    # Base classes
    BasePrefab,
    SectorModifierPrefab,
    TriggerPrefab,
    # Door
    DoorPrefab,
    DoorConfig,
    DoorType,
    apply_door_to_sector,
    create_door_shape,
    DOOR_PRESETS,
    # Lift
    LiftPrefab,
    LiftConfig,
    LiftType,
    apply_lift_to_sector,
    create_lift_shape,
    LIFT_PRESETS,
    # Crusher
    CrusherPrefab,
    CrusherConfig,
    CrusherType,
    apply_crusher_to_sector,
    create_crusher_shape,
    CRUSHER_PRESETS,
    # Teleporter
    TeleporterPrefab,
    TeleporterConfig,
    TeleportType,
    apply_teleporter_to_sector,
    TELEPORTER_PRESETS,
    # Damage floors
    DamageFloorPrefab,
    DamageFloorConfig,
    DamageType,
    apply_damage_to_sector,
    DAMAGE_FLOOR_PRESETS,
    # Lighting
    LightingPrefab,
    LightConfig,
    LightEffect,
    apply_light_effect,
    LIGHT_PRESETS,
    # Stairs
    StairPrefab,
    StairConfig,
    StairType,
    create_stair_shapes,
    STAIR_PRESETS,
)

# =============================================================================
# API - DoomMapBuilder (high-level, declarative)
# =============================================================================
from doomgen.api import (
    DoomMapBuilder,
    RoomConfig,
    CorridorConfig,
    DoomDoorConfig,
    DoomLiftConfig,
    DoomCrusherConfig,
    DoomDamageConfig,
    DoomLightConfig,
    DoomStairConfig,
    create_simple_map,
)

# =============================================================================
# Linedef special actions
# =============================================================================
from doomgen.doom.specials import (
    LinedefFlags,
    DoorAction,
    LiftAction,
    TeleportAction,
    FloorAction,
    CeilingAction,
    CrusherAction,
    StairAction,
    ExitAction,
    LightAction,
    SectorSpecial,
)

# =============================================================================
# ACS Scripting
# =============================================================================
from doomgen.logic.acs_builder import ACSBuilder, ScriptType

# =============================================================================
# Public API
# =============================================================================
__all__ = [
    # Core WAD creation
    "WADWriter",
    "MapEditor",
    "SectorConfig",
    "WallConfig",
    "ThingType",
    
    # Shape creation functions (pure geometry)
    "create_irregular_polygon",
    "create_rectangle",
    "create_polygon",
    "create_corridor",
    "ShapeBuilder",
    
    # CSG operations (pure geometry)
    "cut_polygon",
    "merge_polygons",
    "snap_to_grid",
    "ensure_polygon",
    
    # Procedural modifiers (pure geometry)
    "LSystemGenerator",
    "GRAMMARS",
    "create_lsystem_corridor",
    "recursive_subdivision",
    "subdivide_edge",
    "add_noise_to_polygon",
    
    # MapBuilder (mid-level API) - from geometry.builder
    "MapBuilder",
    "BuildResult",
    "SlotInfo",
    "SlotType",
    "CorridorInfo",
    "CorridorData",
    "CorridorStyle",
    "CorridorSlotRequest",
    "create_corridor_between",
    "create_cutout_polygon",
    
    # Prefab base classes
    "BasePrefab",
    "SectorModifierPrefab",
    "TriggerPrefab",
    
    # Prefab classes and configs
    "DoorPrefab", "DoorConfig", "DoorType", "apply_door_to_sector", "create_door_shape", "DOOR_PRESETS",
    "LiftPrefab", "LiftConfig", "LiftType", "apply_lift_to_sector", "create_lift_shape", "LIFT_PRESETS",
    "CrusherPrefab", "CrusherConfig", "CrusherType", "apply_crusher_to_sector", "create_crusher_shape", "CRUSHER_PRESETS",
    "TeleporterPrefab", "TeleporterConfig", "TeleportType", "apply_teleporter_to_sector", "TELEPORTER_PRESETS",
    "DamageFloorPrefab", "DamageFloorConfig", "DamageType", "apply_damage_to_sector", "DAMAGE_FLOOR_PRESETS",
    "LightingPrefab", "LightConfig", "LightEffect", "apply_light_effect", "LIGHT_PRESETS",
    "StairPrefab", "StairConfig", "StairType", "create_stair_shapes", "STAIR_PRESETS",
    
    # DoomMapBuilder (high-level API)
    "DoomMapBuilder",
    "RoomConfig",
    "CorridorConfig",
    "DoomDoorConfig",
    "DoomLiftConfig",
    "DoomCrusherConfig",
    "DoomDamageConfig",
    "DoomLightConfig",
    "DoomStairConfig",
    "create_simple_map",
    
    # Linedef specials
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
    
    # ACS Scripting
    "ACSBuilder",
    "ScriptType",
]
