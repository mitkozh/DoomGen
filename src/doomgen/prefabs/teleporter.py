"""
Teleporter Prefab System - Creates teleportation pads.

Doom teleporters work by having a source sector trigger teleportation
to a destination sector containing a TELEPORT_LANDING thing.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, Point

from doomgen.doom.specials import TeleportAction
from doomgen.doom.things import ThingType
from doomgen.prefabs.base import TriggerPrefab, PrefabPlacement

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class TeleportType(Enum):
    """Types of teleporter activation."""
    WALK = "walk"      # Teleport on walkover
    SWITCH = "switch"  # Teleport by pressing use
    SILENT = "silent"  # Silent teleport (no fog/sound)


# Map teleport types to linedef actions
TELEPORT_ACTIONS = {
    TeleportType.WALK: TeleportAction.WR_TELEPORT,
    TeleportType.SWITCH: TeleportAction.SR_TELEPORT,
    TeleportType.SILENT: TeleportAction.WR_SILENT_TELEPORT,
}


@dataclass
class TeleporterConfig:
    """Configuration for a teleporter prefab.
    
    Attributes:
        radius: Radius of the teleporter pad.
        teleport_type: Type of teleporter activation.
        floor_height: Floor height of the teleporter pad.
        ceiling_height: Ceiling height.
        floor_texture: Floor texture for the teleporter pad.
        ceiling_texture: Ceiling texture.
        light_level: Light level for the teleporter sector.
    """
    radius: float = 32.0
    teleport_type: TeleportType = TeleportType.WALK
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = "GATE1"
    ceiling_texture: str = "CEIL3_5"
    light_level: int = 255


class TeleporterPrefab(TriggerPrefab):
    """
    Teleporter prefab that creates teleportation pads.
    
    Properly inherits from TriggerPrefab and implements all required methods.
    
    Example:
        teleporter = TeleporterPrefab(TeleporterConfig())
        poly = teleporter.create_polygon((100, 0))
        sector_config = teleporter.get_sector_config()
        idx = editor.add_sector_from_polygon(poly, sector_config)
        teleporter.apply_to_map(editor, idx, tag=1, dest_pos=(500, 0))
    """
    
    def __init__(self, config: Optional[TeleporterConfig] = None):
        """
        Initialize teleporter prefab.
        
        Args:
            config: Teleporter configuration (uses defaults if None).
        """
        self.config = config or TeleporterConfig()
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create a circular teleporter pad polygon at the specified position.
        
        Args:
            position: Center position (x, y) for the teleporter.
        
        Returns:
            A Polygon representing the teleporter geometry.
        """
        return Point(position).buffer(self.config.radius, resolution=8)
    
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get sector configuration for the teleporter.
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
        """Get the linedef action for this teleporter type."""
        return TELEPORT_ACTIONS.get(self.config.teleport_type, TeleportAction.WR_TELEPORT)
    
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        dest_sector_idx: Optional[int] = None,
        dest_pos: Optional[Tuple[float, float]] = None,
        **kwargs
    ) -> List[int]:
        """
        Apply teleporter properties to a sector.
        
        Sets up the teleporter by:
        1. Tagging the destination sector (if provided)
        2. Adding a TELEPORT_LANDING thing at the destination (if provided)
        3. Setting the linedef action on source sector borders
        
        Args:
            editor: MapEditor with the sectors.
            sector_index: Index of the source teleporter sector.
            tag: Sector tag linking source and destination.
            dest_sector_idx: Index of the destination sector.
            dest_pos: Position for the teleport landing thing.
        
        Returns:
            List of modified linedef indices.
        """
        md = editor.map_data
        
        # Tag the destination sector if provided
        if dest_sector_idx is not None:
            md.sectors[dest_sector_idx]['tag'] = tag
        
        # Add teleport landing thing at destination if provided
        if dest_pos is not None:
            md.add_thing(
                x=int(dest_pos[0]),
                y=int(dest_pos[1]),
                thing_type=ThingType.TELEPORT_LANDING.value
            )
        
        linedef_action = self.get_trigger_action()
        modified = []
        
        for i, ld in enumerate(md.linedefs):
            front_sd = ld.get('front_sidedef', -1)
            back_sd = ld.get('back_sidedef', -1)
            
            front_sec = md.sidedefs[front_sd].get('sector', -1) if front_sd >= 0 else -1
            back_sec = md.sidedefs[back_sd].get('sector', -1) if back_sd >= 0 else -1
            
            if front_sec != sector_index and back_sec != sector_index:
                continue
            
            md.linedefs[i]['special'] = int(linedef_action)
            md.linedefs[i]['tag'] = tag
            modified.append(i)
        
        return modified


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

@dataclass
class TeleporterPair:
    """Result of creating a teleporter pair (legacy compatibility).
    
    Attributes:
        source_polygon: The teleporter pad geometry.
        dest_position: Destination coordinates.
        linedef_action: Doom linedef action type.
        tag: Sector tag linking source and destination.
    """
    source_polygon: Polygon
    dest_position: Tuple[float, float]
    linedef_action: int
    tag: int


def create_teleporter_pair(
    source_pos: Tuple[float, float],
    dest_pos: Tuple[float, float],
    config: Optional[TeleporterConfig] = None,
    tag: int = 1
) -> TeleporterPair:
    """Create a teleporter prefab linking source and destination.
    
    The source is a circular pad that triggers teleportation.
    The destination needs a TELEPORT_LANDING thing placed in a
    tagged sector.
    
    Args:
        source_pos: Center position (x, y) of the teleporter pad.
        dest_pos: Destination position (x, y).
        config: Teleporter configuration (uses defaults if None).
        tag: Sector tag linking source and destination.
    
    Returns:
        TeleporterPair with source geometry and destination info.
    """
    if config is None:
        config = TeleporterConfig()
    
    prefab = TeleporterPrefab(config)
    source_poly = prefab.create_polygon(source_pos)
    
    return TeleporterPair(
        source_polygon=source_poly,
        dest_position=dest_pos,
        linedef_action=prefab.get_trigger_action(),
        tag=tag
    )


def apply_teleporter_to_sector(
    editor: 'MapEditor',
    source_sector_idx: int,
    dest_sector_idx: int,
    dest_pos: Tuple[float, float],
    tag: int,
    linedef_action: int = TeleportAction.WR_TELEPORT
) -> List[int]:
    """Apply teleporter properties to source and destination sectors.
    
    Sets up the teleporter by:
    1. Tagging the destination sector
    2. Adding a TELEPORT_LANDING thing at the destination
    3. Setting the linedef action on source sector borders
    
    Args:
        editor: MapEditor with the sectors.
        source_sector_idx: Index of the source teleporter sector.
        dest_sector_idx: Index of the destination sector.
        dest_pos: Position for the teleport landing thing.
        tag: Sector tag linking source and destination.
        linedef_action: Doom linedef action type.
    
    Returns:
        List of modified linedef indices.
    """
    # Determine teleport type from action
    teleport_type = TeleportType.WALK
    if linedef_action == TeleportAction.SR_TELEPORT:
        teleport_type = TeleportType.SWITCH
    elif linedef_action == TeleportAction.WR_SILENT_TELEPORT:
        teleport_type = TeleportType.SILENT
    
    config = TeleporterConfig(teleport_type=teleport_type)
    prefab = TeleporterPrefab(config)
    
    return prefab.apply_to_map(
        editor, source_sector_idx, tag,
        dest_sector_idx=dest_sector_idx,
        dest_pos=dest_pos
    )


# Preset configurations for common teleporter types
TELEPORTER_PRESETS = {
    "standard": TeleporterConfig(),
    "large": TeleporterConfig(radius=64),
    "silent": TeleporterConfig(teleport_type=TeleportType.SILENT),
    "switch": TeleporterConfig(teleport_type=TeleportType.SWITCH),
}
