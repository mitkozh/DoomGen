"""
Door Prefab System - Creates interactive doors in Doom maps.

Doors are sectors with ceiling=floor (closed state) that open by raising the ceiling.
Uses the cookie-cutter pattern to cut door geometry from room geometry.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, box
from shapely.validation import make_valid

from doomgen.doom.specials import DoorAction, LinedefFlags
from doomgen.prefabs.base import BasePrefab, PrefabPlacement

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class DoorType(Enum):
    """Types of doors available in Doom."""
    MANUAL = "manual"      # Player presses use to open
    REMOTE = "remote"      # Opened by switch elsewhere
    KEY_BLUE = "blue"      # Requires blue key
    KEY_RED = "red"        # Requires red key
    KEY_YELLOW = "yellow"  # Requires yellow key


# Map door types to linedef actions
DOOR_ACTIONS = {
    DoorType.MANUAL: DoorAction.DR_OPEN_WAIT_CLOSE,
    DoorType.REMOTE: DoorAction.SR_OPEN_WAIT_CLOSE,
    DoorType.KEY_BLUE: DoorAction.D1_BLUE_DOOR,
    DoorType.KEY_RED: DoorAction.D1_RED_DOOR,
    DoorType.KEY_YELLOW: DoorAction.D1_YELLOW_DOOR,
}


@dataclass
class DoorConfig:
    """Configuration for a door prefab.
    
    Attributes:
        width: Door opening width in map units.
        depth: Door thickness in map units.
        door_type: Type of door (manual, key-locked, etc.).
        texture: Door texture name.
        track_texture: Door track texture (sides).
        floor_height: Door floor height.
        open_height: Ceiling height when fully open.
        floor_texture: Floor texture.
        ceiling_texture: Ceiling texture.
        light_level: Light level for door sector.
    """
    width: float = 64.0
    depth: float = 16.0
    door_type: DoorType = DoorType.MANUAL
    texture: str = "BIGDOOR2"
    track_texture: str = "DOORTRAK"
    floor_height: int = 0
    open_height: int = 128
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"
    light_level: int = 160


class DoorPrefab(BasePrefab):
    """
    Door prefab that creates interactive doors.
    
    Properly inherits from BasePrefab and implements all required methods.
    
    Example:
        door = DoorPrefab(DoorConfig(width=64, door_type=DoorType.KEY_BLUE))
        poly = door.create_polygon((100, 0), direction="vertical")
        sector_config = door.get_sector_config()
        idx = editor.add_sector_from_polygon(poly, sector_config)
        door.apply_to_map(editor, idx)
    """
    
    def __init__(self, config: Optional[DoorConfig] = None):
        """
        Initialize door prefab.
        
        Args:
            config: Door configuration (uses defaults if None).
        """
        self.config = config or DoorConfig()
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        direction: str = "horizontal",
        **kwargs
    ) -> Polygon:
        """
        Create a door polygon at the specified position.
        
        Args:
            position: Center position (x, y) for the door.
            direction: "horizontal" (door spans left-right) or 
                       "vertical" (door spans up-down).
        
        Returns:
            A Polygon representing the door geometry.
        """
        x, y = position
        if direction == "horizontal":
            return box(x - self.config.width/2, y - self.config.depth/2, 
                       x + self.config.width/2, y + self.config.depth/2)
        else:
            return box(x - self.config.depth/2, y - self.config.width/2, 
                       x + self.config.depth/2, y + self.config.width/2)
    
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get sector configuration for the door.
        
        Door sectors have ceiling=floor (closed state).
        """
        from doomgen.doom.translator import SectorConfig
        return SectorConfig(
            floor_height=self.config.floor_height,
            ceiling_height=self.config.floor_height,  # Closed door
            floor_texture=self.config.floor_texture,
            ceiling_texture=self.config.ceiling_texture,
            light_level=self.config.light_level
        )
    
    def get_linedef_action(self) -> int:
        """Get the linedef action for this door type."""
        return DOOR_ACTIONS.get(self.config.door_type, DoorAction.DR_OPEN_WAIT_CLOSE)
    
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        **kwargs
    ) -> List[int]:
        """
        Apply door properties to a sector's linedefs.
        
        Sets the linedef action, flags, and textures for all linedefs
        that border the door sector. The special action is applied to
        ALL two-sided linedefs so the door can be triggered from both sides.
        
        Args:
            editor: MapEditor with the door sector.
            sector_index: Index of the door sector.
            tag: Sector tag (for remote doors).
        
        Returns:
            List of modified linedef indices.
        """
        modified = []
        md = editor.map_data
        linedef_action = self.get_linedef_action()
        
        for i, ld in enumerate(md.linedefs):
            front_sd = ld.get('front_sidedef', -1)
            back_sd = ld.get('back_sidedef', -1)
            
            if front_sd < 0:
                continue
            
            front_sec = md.sidedefs[front_sd].get('sector', -1)
            back_sec = md.sidedefs[back_sd].get('sector', -1) if back_sd >= 0 else -1
            
            # Check if this linedef touches the door sector
            if front_sec != sector_index and back_sec != sector_index:
                continue
            
            # Two-sided linedef (door borders another sector)
            if back_sd >= 0:
                # Set flags for two-sided door linedef
                md.linedefs[i]['flags'] = int(LinedefFlags.TWO_SIDED | LinedefFlags.UPPER_UNPEGGED)
                
                # Set special on ALL two-sided linedefs so door works from both sides
                if linedef_action:
                    md.linedefs[i]['special'] = int(linedef_action)
                    if tag:
                        md.linedefs[i]['tag'] = tag
                
                # Upper texture goes on BOTH sides for visibility from either direction
                md.sidedefs[front_sd]['upper_texture'] = self.config.texture
                md.sidedefs[back_sd]['upper_texture'] = self.config.texture
                
                # Track textures on the sides
                md.sidedefs[front_sd]['lower_texture'] = self.config.track_texture
                md.sidedefs[back_sd]['lower_texture'] = self.config.track_texture
            else:
                # One-sided linedef (shouldn't happen for doors, but handle it)
                md.sidedefs[front_sd]['upper_texture'] = self.config.texture
            
            modified.append(i)
        
        return modified


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

def create_door_shape(
    position: Tuple[float, float],
    width: float = 64.0,
    depth: float = 16.0,
    direction: str = "horizontal"
) -> Polygon:
    """Create a door polygon at the specified position.
    
    Args:
        position: Center position (x, y) for the door.
        width: Width of the door opening.
        depth: Thickness of the door.
        direction: "horizontal" (door spans left-right) or 
                   "vertical" (door spans up-down).
    
    Returns:
        A Polygon representing the door geometry.
    """
    prefab = DoorPrefab(DoorConfig(width=width, depth=depth))
    return prefab.create_polygon(position, direction=direction)


def place_door(
    geometry: Polygon,
    position: Tuple[float, float],
    direction: str = "horizontal",
    config: Optional[DoorConfig] = None
) -> 'DoorPlacement':
    """Place a door by cutting it from existing geometry.
    
    Uses the cookie-cutter pattern: creates the door polygon,
    subtracts it from the room geometry, creating a hole where
    the door sector will be placed.
    
    Args:
        geometry: Room geometry to cut the door from.
        position: Center position (x, y) for the door.
        direction: "horizontal" or "vertical".
        config: Door configuration (uses defaults if None).
    
    Returns:
        DoorPlacement with the door and modified geometry.
    
    Raises:
        ValueError: If door doesn't intersect the geometry.
    """
    if config is None:
        config = DoorConfig()
    
    prefab = DoorPrefab(config)
    placement = prefab.place(geometry, position, direction=direction)
    
    return DoorPlacement(
        door=prefab,
        polygon=placement.polygon,
        modified_geometry=placement.modified_geometry,
        original_geometry=geometry,
        linedef_action=prefab.get_linedef_action()
    )


def place_door_between(
    geom1: Polygon,
    geom2: Polygon,
    config: Optional[DoorConfig] = None
) -> Tuple['DoorPrefab', Polygon, Polygon]:
    """Place a door at the boundary between two geometries.
    
    Automatically detects the shared edge and places the door there.
    
    Args:
        geom1: First room geometry.
        geom2: Second room geometry.
        config: Door configuration (uses defaults if None).
    
    Returns:
        Tuple of (door prefab, modified geom1, modified geom2).
    
    Raises:
        ValueError: If geometries don't share an edge.
    """
    if config is None:
        config = DoorConfig()
    
    shared = geom1.boundary.intersection(geom2.boundary)
    if shared.is_empty:
        raise ValueError("Geometries don't share an edge")
    
    if shared.geom_type == 'MultiLineString':
        shared = max(shared.geoms, key=lambda l: l.length)
    
    center = shared.centroid
    coords = list(shared.coords) if hasattr(shared, 'coords') else [(center.x, center.y)]
    
    if len(coords) >= 2:
        dx = abs(coords[1][0] - coords[0][0])
        dy = abs(coords[1][1] - coords[0][1])
        direction = "vertical" if dx > dy else "horizontal"
    else:
        direction = "horizontal"
    
    prefab = DoorPrefab(config)
    door_poly = prefab.create_polygon((center.x, center.y), direction=direction)
    
    cut1 = geom1.difference(door_poly)
    cut2 = geom2.difference(door_poly)
    if not cut1.is_valid:
        cut1 = make_valid(cut1)
    if not cut2.is_valid:
        cut2 = make_valid(cut2)
    
    return prefab, cut1, cut2


def apply_door_to_sector(
    editor: 'MapEditor',
    door_sector_idx: int,
    config: Optional[DoorConfig] = None,
    linedef_action: int = DoorAction.DR_OPEN_WAIT_CLOSE
) -> List[int]:
    """Apply door properties to a sector's linedefs.
    
    Sets the linedef action, flags, and textures for all linedefs
    that border the door sector.
    
    Args:
        editor: MapEditor with the door sector.
        door_sector_idx: Index of the door sector.
        config: Door configuration for textures.
        linedef_action: Doom linedef action type.
    
    Returns:
        List of modified linedef indices.
    """
    if config is None:
        config = DoorConfig()
    
    # Create prefab with matching door type
    door_type = DoorType.MANUAL
    if linedef_action == DoorAction.D1_BLUE_DOOR:
        door_type = DoorType.KEY_BLUE
    elif linedef_action == DoorAction.D1_RED_DOOR:
        door_type = DoorType.KEY_RED
    elif linedef_action == DoorAction.D1_YELLOW_DOOR:
        door_type = DoorType.KEY_YELLOW
    elif linedef_action == DoorAction.SR_OPEN_WAIT_CLOSE:
        door_type = DoorType.REMOTE
    
    config.door_type = door_type
    prefab = DoorPrefab(config)
    return prefab.apply_to_map(editor, door_sector_idx)


def get_door_action(key_type: Optional[str] = None) -> int:
    """Get the appropriate door action for a key type.
    
    Args:
        key_type: None for manual door, or "blue"/"red"/"yellow" for key doors.
    
    Returns:
        The DoorAction value for the door type.
    """
    if key_type == "blue":
        return DoorAction.D1_BLUE_DOOR
    elif key_type == "red":
        return DoorAction.D1_RED_DOOR
    elif key_type == "yellow":
        return DoorAction.D1_YELLOW_DOOR
    else:
        return DoorAction.DR_OPEN_WAIT_CLOSE


def apply_door_from_info(
    editor: 'MapEditor',
    door_sector_idx: int,
    door_info,  # SlotInfo from geometry.builder
    config: Optional[DoorConfig] = None
) -> List[int]:
    """Apply door properties using SlotInfo from MapBuilder.
    
    This is the preferred way to apply doors when using MapBuilder.
    
    Args:
        editor: MapEditor with the door sector.
        door_sector_idx: Index of the door sector.
        door_info: SlotInfo from MapBuilder.build() result.
        config: Optional DoorConfig for texture overrides.
    
    Returns:
        List of modified linedef indices.
    """
    if config is None:
        config = DoorConfig()
    
    # Get key_type from metadata if present
    key_type = door_info.metadata.get('key_type') if hasattr(door_info, 'metadata') else None
    linedef_action = get_door_action(key_type)
    return apply_door_to_sector(editor, door_sector_idx, config, linedef_action)


# =============================================================================
# Legacy dataclasses for backward compatibility
# =============================================================================

@dataclass
class DoorPlacement:
    """Result of placing a door, containing the door and modified geometry.
    
    Attributes:
        door: The door prefab.
        polygon: The door polygon geometry.
        modified_geometry: Room geometry with door cut out.
        original_geometry: Original room geometry before cutting.
        linedef_action: Recommended linedef action for the door.
    """
    door: DoorPrefab
    polygon: Polygon
    modified_geometry: Union[Polygon, list]
    original_geometry: Polygon
    linedef_action: int = DoorAction.DR_OPEN_WAIT_CLOSE


# Preset configurations for common door types
DOOR_PRESETS = {
    "standard": DoorConfig(),
    "wide": DoorConfig(width=128),
    "narrow": DoorConfig(width=48),
    "key_blue": DoorConfig(door_type=DoorType.KEY_BLUE),
    "key_red": DoorConfig(door_type=DoorType.KEY_RED),
    "key_yellow": DoorConfig(door_type=DoorType.KEY_YELLOW),
}
