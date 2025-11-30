"""
Lift Prefab System - Creates elevator platforms in Doom maps.

Doom lifts work by lowering the floor to the lowest adjacent floor height,
waiting, then raising back up. The lift sector needs a tag that matches
the trigger linedef.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, box
from shapely.validation import make_valid

from doomgen.doom.specials import LiftAction, LinedefFlags
from doomgen.prefabs.base import TriggerPrefab, PrefabPlacement

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class LiftType(Enum):
    """Types of lift behavior."""
    STANDARD = "standard"    # Normal lift speed
    FAST = "fast"            # Fast lift
    PERPETUAL = "perpetual"  # Continuously moving


# Map lift types to linedef actions
LIFT_ACTIONS = {
    LiftType.STANDARD: LiftAction.SR_LIFT,
    LiftType.FAST: LiftAction.SR_LIFT_FAST,
    LiftType.PERPETUAL: LiftAction.SR_PERPETUAL_RAISE,
}


@dataclass
class LiftConfig:
    """Configuration for a lift prefab.
    
    Attributes:
        width: Lift platform width in map units.
        depth: Lift platform depth in map units.
        lift_type: Type of lift behavior.
        floor_height: Upper floor height (lift starts here).
        lower_height: Lower floor height (lift travels to here).
        ceiling_height: Ceiling height above lift.
        floor_texture: Floor texture for the lift platform.
        ceiling_texture: Ceiling texture.
        lower_texture: Wall texture for the lift sides (lower).
        upper_texture: Wall texture for ceiling height differences.
        light_level: Light level for lift sector.
    """
    width: float = 128.0
    depth: float = 128.0
    lift_type: LiftType = LiftType.STANDARD
    floor_height: int = 64  # Upper position
    lower_height: int = 0   # Lower position (lift travels to lowest adjacent)
    ceiling_height: int = 192
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"
    lower_texture: str = "SUPPORT2"
    upper_texture: str = "SUPPORT2"
    light_level: int = 160


class LiftPrefab(TriggerPrefab):
    """
    Lift prefab that creates elevator platforms.
    
    Properly inherits from TriggerPrefab and implements all required methods.
    
    Example:
        lift = LiftPrefab(LiftConfig(floor_height=64))
        poly = lift.create_polygon((100, 0))
        sector_config = lift.get_sector_config()
        idx = editor.add_sector_from_polygon(poly, sector_config)
        lift.apply_to_map(editor, idx, tag=1)
    """
    
    def __init__(self, config: Optional[LiftConfig] = None):
        """
        Initialize lift prefab.
        
        Args:
            config: Lift configuration (uses defaults if None).
        """
        self.config = config or LiftConfig()
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create a rectangular lift polygon at the specified position.
        
        Args:
            position: Center position (x, y) for the lift.
        
        Returns:
            A Polygon representing the lift geometry.
        """
        x, y = position
        return box(x - self.config.width/2, y - self.config.depth/2,
                   x + self.config.width/2, y + self.config.depth/2)
    
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get sector configuration for the lift.
        
        Lift floor starts at upper position and lowers.
        """
        from doomgen.doom.translator import SectorConfig
        return SectorConfig(
            floor_height=self.config.floor_height,
            ceiling_height=self.config.ceiling_height,
            floor_texture=self.config.floor_texture,
            ceiling_texture=self.config.ceiling_texture,
            light_level=self.config.light_level
        )
    
    def get_trigger_action(self) -> int:
        """Get the linedef action for this lift type."""
        return LIFT_ACTIONS.get(self.config.lift_type, LiftAction.SR_LIFT)
    
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        **kwargs
    ) -> List[int]:
        """
        Apply lift properties to a sector.
        
        Sets the sector tag and applies linedef action, flags, and
        textures to all linedefs that border the lift sector.
        
        Args:
            editor: MapEditor with the lift sector.
            sector_index: Index of the lift sector.
            tag: Sector tag for triggering.
        
        Returns:
            List of modified linedef indices.
        """
        md = editor.map_data
        md.sectors[sector_index]['tag'] = tag
        
        modified = []
        linedef_action = self.get_trigger_action()
        
        for i, ld in enumerate(md.linedefs):
            front_sd = ld.get('front_sidedef', -1)
            back_sd = ld.get('back_sidedef', -1)
            
            if back_sd < 0:
                continue
            
            front_sec = md.sidedefs[front_sd].get('sector', -1) if front_sd >= 0 else -1
            back_sec = md.sidedefs[back_sd].get('sector', -1)
            
            if front_sec != sector_index and back_sec != sector_index:
                continue
            
            md.linedefs[i]['special'] = int(linedef_action)
            md.linedefs[i]['tag'] = tag
            
            # LOWER_UNPEGGED prevents floor texture from moving
            # UPPER_UNPEGGED prevents ceiling texture from moving
            current = ld.get('flags', 0)
            md.linedefs[i]['flags'] = current | int(LinedefFlags.LOWER_UNPEGGED) | int(LinedefFlags.UPPER_UNPEGGED)
            
            if front_sd >= 0:
                md.sidedefs[front_sd]['lower_texture'] = self.config.lower_texture
                md.sidedefs[front_sd]['upper_texture'] = self.config.upper_texture
            if back_sd >= 0:
                md.sidedefs[back_sd]['lower_texture'] = self.config.lower_texture
                md.sidedefs[back_sd]['upper_texture'] = self.config.upper_texture
            
            modified.append(i)
        
        return modified


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

def create_lift_shape(
    position: Tuple[float, float],
    width: float = 128.0,
    depth: float = 128.0
) -> Polygon:
    """Create a rectangular lift polygon at the specified position.
    
    Args:
        position: Center position (x, y) for the lift.
        width: Width of the lift platform.
        depth: Depth of the lift platform.
    
    Returns:
        A Polygon representing the lift geometry.
    """
    prefab = LiftPrefab(LiftConfig(width=width, depth=depth))
    return prefab.create_polygon(position)


def place_lift(
    geometry: Polygon,
    position: Tuple[float, float],
    config: Optional[LiftConfig] = None,
    tag: int = 1
) -> 'LiftPlacement':
    """Place a lift by cutting it from existing geometry.
    
    Uses the cookie-cutter pattern: creates the lift polygon,
    subtracts it from the room geometry, creating a hole where
    the lift sector will be placed.
    
    IMPORTANT: Doom lifts LOWER to the lowest adjacent floor height.
    If you want a lift to go UP to a higher room, set the lift's
    floor_height to the HIGHER level. The lift will lower down to
    reach the lower room.
    
    Args:
        geometry: Room geometry to cut the lift from.
        position: Center position (x, y) for the lift.
        config: Lift configuration (uses defaults if None).
        tag: Sector tag for the lift (must match trigger linedef).
    
    Returns:
        LiftPlacement with the lift and modified geometry.
    
    Raises:
        ValueError: If lift doesn't intersect the geometry.
    """
    if config is None:
        config = LiftConfig()
    
    prefab = LiftPrefab(config)
    placement = prefab.place(geometry, position)
    
    return LiftPlacement(
        lift=prefab,
        polygon=placement.polygon,
        modified_geometry=placement.modified_geometry,
        original_geometry=geometry,
        tag=tag
    )


def apply_lift_to_sector(
    editor: 'MapEditor',
    lift_sector_idx: int,
    tag: int,
    linedef_action: int = LiftAction.SR_LIFT,
    config: Optional[LiftConfig] = None
) -> List[int]:
    """Apply lift properties to a sector.
    
    Sets the sector tag and applies linedef action, flags, and
    textures to all linedefs that border the lift sector.
    
    Args:
        editor: MapEditor with the lift sector.
        lift_sector_idx: Index of the lift sector.
        tag: Sector tag for triggering.
        linedef_action: Doom linedef action type.
        config: Lift configuration for textures.
    
    Returns:
        List of modified linedef indices.
    """
    if config is None:
        config = LiftConfig()
    
    # Determine lift type from action
    lift_type = LiftType.STANDARD
    if linedef_action == LiftAction.SR_LIFT_FAST or linedef_action == LiftAction.WR_LIFT_FAST:
        lift_type = LiftType.FAST
    elif linedef_action == LiftAction.SR_PERPETUAL_RAISE:
        lift_type = LiftType.PERPETUAL
    
    config.lift_type = lift_type
    prefab = LiftPrefab(config)
    return prefab.apply_to_map(editor, lift_sector_idx, tag)


# =============================================================================
# Legacy dataclasses for backward compatibility
# =============================================================================

@dataclass
class LiftPlacement:
    """Result of placing a lift, containing the lift and modified geometry.
    
    Attributes:
        lift: The lift prefab.
        polygon: The lift polygon geometry.
        modified_geometry: Room geometry with lift cut out.
        original_geometry: Original room geometry before cutting.
        tag: Sector tag for the lift.
    """
    lift: LiftPrefab
    polygon: Polygon
    modified_geometry: Union[Polygon, list]
    original_geometry: Polygon
    tag: int = 1


# Preset configurations for common lift types
LIFT_PRESETS = {
    "standard": LiftConfig(),
    "small": LiftConfig(width=64, depth=64),
    "large": LiftConfig(width=192, depth=192),
    "fast": LiftConfig(lift_type=LiftType.FAST),
    "perpetual": LiftConfig(lift_type=LiftType.PERPETUAL),
}
