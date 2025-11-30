"""
Prefabs - Interactive gameplay elements for Doom maps.

Provides cookie-cutter style prefabs for doors, lifts, teleporters, crushers,
stairs, damaging floors, and lighting effects.

Architecture
------------
All prefabs inherit from BasePrefab which provides:
- create_polygon(): Create the prefab's geometry
- apply_to_map(): Configure the sector and linedefs
- place(): Convenience method for cookie-cutter pattern

Specialized base classes:
- SectorModifierPrefab: For effects that modify existing sectors (damage, lighting)
- TriggerPrefab: For prefabs activated by triggers (lifts, crushers)

Quick Reference
---------------
Each prefab follows the pattern: Type (enum) + Config (dataclass) + apply function.

    from doomgen.prefabs import (
        DoorType, DoorConfig, apply_door_to_sector,      # Doors
        LiftType, LiftConfig, apply_lift_to_sector,      # Lifts
        CrusherType, CrusherConfig, apply_crusher_to_sector,  # Crushers
        StairConfig, create_stair_shapes,                # Stairs
        DamageType, DamageFloorConfig, apply_damage_to_sector,  # Damage
        LightEffect, LightConfig, apply_light_effect,    # Lighting
        TeleportType, TeleporterConfig, apply_teleporter_to_sector,  # Teleporters
    )

Cookie-Cutter Pattern
---------------------
1. Create element geometry at desired position
2. Cut it from static geometry using Shapely difference()
3. Add both as sectors - shared edges become two-sided linedefs
4. Apply special properties to the relevant linedefs
"""

# =============================================================================
# Base prefab classes
# =============================================================================
from doomgen.prefabs.base import (
    BasePrefab,
    BasePrefabConfig,
    PrefabPlacement,
    SectorModifierPrefab,
    TriggerPrefab,
)

# =============================================================================
# Door prefabs
# =============================================================================
from doomgen.prefabs.door import (
    DoorType,
    DoorConfig,
    apply_door_to_sector,
    apply_door_from_info,
    get_door_action,
    DOOR_PRESETS,
    # Geometry helpers
    create_door_shape,
    place_door,
    place_door_between,
    # Internal types (for advanced use)
    DoorPrefab,
    DoorPlacement,
)

# =============================================================================
# Lift prefabs
# =============================================================================
from doomgen.prefabs.lift import (
    LiftType,
    LiftConfig,
    apply_lift_to_sector,
    LIFT_PRESETS,
    # Geometry helpers
    create_lift_shape,
    place_lift,
    # Internal types
    LiftPrefab,
    LiftPlacement,
)

# =============================================================================
# Teleporter prefabs
# =============================================================================
from doomgen.prefabs.teleporter import (
    TeleportType,
    TeleporterConfig,
    apply_teleporter_to_sector,
    TELEPORTER_PRESETS,
    create_teleporter_pair,
    TeleporterPrefab,
)

# =============================================================================
# Crusher prefabs
# =============================================================================
from doomgen.prefabs.crusher import (
    CrusherType,
    CrusherConfig,
    apply_crusher_to_sector,
    CRUSHER_PRESETS,
    create_crusher_shape,
    CrusherPrefab,
)

# =============================================================================
# Stairs prefabs
# =============================================================================
from doomgen.prefabs.stairs import (
    StairType,
    StairConfig,
    create_stair_shapes,
    apply_stair_trigger,
    STAIR_PRESETS,
    StairPrefab,
)

# =============================================================================
# Damage floor prefabs
# =============================================================================
from doomgen.prefabs.damage import (
    DamageType,
    DamageFloorConfig,
    apply_damage_to_sector,
    DAMAGE_FLOOR_PRESETS,
    # Geometry helpers
    create_damage_pool_shape,
    create_damage_pool_circular,
    DamageFloorPrefab,
)

# =============================================================================
# Lighting prefabs
# =============================================================================
from doomgen.prefabs.lighting import (
    LightEffect,
    LightConfig,
    apply_light_effect,
    LIGHT_PRESETS,
    # Advanced
    apply_light_trigger,
    create_light_gradient,
    LightingPrefab,
)

# =============================================================================
# Public API - organized by usage frequency
# =============================================================================
__all__ = [
    # === Base classes ===
    "BasePrefab", "BasePrefabConfig", "PrefabPlacement",
    "SectorModifierPrefab", "TriggerPrefab",
    
    # === Primary API (Config + apply function) ===
    # Doors
    "DoorType", "DoorConfig", "apply_door_to_sector", "apply_door_from_info",
    "get_door_action", "DOOR_PRESETS",
    # Lifts
    "LiftType", "LiftConfig", "apply_lift_to_sector", "LIFT_PRESETS",
    # Crushers
    "CrusherType", "CrusherConfig", "apply_crusher_to_sector", "CRUSHER_PRESETS",
    # Stairs
    "StairType", "StairConfig", "create_stair_shapes", "STAIR_PRESETS",
    # Damage floors
    "DamageType", "DamageFloorConfig", "apply_damage_to_sector", "DAMAGE_FLOOR_PRESETS",
    # Lighting
    "LightEffect", "LightConfig", "apply_light_effect", "LIGHT_PRESETS",
    # Teleporters
    "TeleportType", "TeleporterConfig", "apply_teleporter_to_sector", "TELEPORTER_PRESETS",
    
    # === Geometry helpers (for cookie-cutter pattern) ===
    "create_door_shape", "place_door", "place_door_between",
    "create_lift_shape", "place_lift",
    "create_crusher_shape",
    "create_damage_pool_shape", "create_damage_pool_circular",
    "create_teleporter_pair",
    "apply_stair_trigger", "apply_light_trigger", "create_light_gradient",
    
    # === Internal types (for type annotations) ===
    "DoorPrefab", "DoorPlacement", "LiftPrefab", "LiftPlacement", "TeleporterPrefab",
    "CrusherPrefab", "StairPrefab", "DamageFloorPrefab", "LightingPrefab",
]
