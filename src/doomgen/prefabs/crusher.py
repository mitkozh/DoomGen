"""
Crusher Prefab System - Creates crushing ceiling traps.

Crushers are ceilings that lower to the floor and raise back up continuously,
damaging anything caught between them.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, box

from doomgen.doom.specials import CrusherAction, LinedefFlags
from doomgen.prefabs.base import TriggerPrefab

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class CrusherType(Enum):
    """Types of crusher behavior."""
    SLOW = "slow"          # Slow crushing speed
    FAST = "fast"          # Fast crushing speed
    SILENT = "silent"      # Silent crusher


# Map crusher types to linedef actions
CRUSHER_ACTIONS = {
    CrusherType.SLOW: CrusherAction.WR_CRUSHER_SLOW,
    CrusherType.FAST: CrusherAction.WR_CRUSHER_FAST,
    CrusherType.SILENT: CrusherAction.W1_CRUSHER_SILENT,
}


@dataclass
class CrusherConfig:
    """Configuration for a crusher prefab.
    
    Attributes:
        width: Crusher area width in map units.
        depth: Crusher area depth in map units.
        crusher_type: Type of crusher behavior.
        floor_height: Floor height of the crusher sector.
        ceiling_height: Ceiling height (starting position).
        floor_texture: Floor texture.
        ceiling_texture: Ceiling texture (the crusher surface).
        light_level: Light level for the crusher sector.
    """
    width: float = 128.0
    depth: float = 128.0
    crusher_type: CrusherType = CrusherType.SLOW
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL5_2"
    light_level: int = 160


class CrusherPrefab(TriggerPrefab):
    """
    Crusher prefab that creates crushing ceiling traps.
    
    Properly inherits from TriggerPrefab and implements all required methods.
    
    Example:
        crusher = CrusherPrefab(CrusherConfig(crusher_type=CrusherType.FAST))
        poly = crusher.create_polygon((100, 0))
        sector_config = crusher.get_sector_config()
        idx = editor.add_sector_from_polygon(poly, sector_config)
        crusher.apply_to_map(editor, idx, tag=1)
    """
    
    def __init__(self, config: Optional[CrusherConfig] = None):
        """
        Initialize crusher prefab.
        
        Args:
            config: Crusher configuration (uses defaults if None).
        """
        self.config = config or CrusherConfig()
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create a rectangular crusher polygon at the specified position.
        
        Args:
            position: Center position (x, y) for the crusher.
        
        Returns:
            A Polygon representing the crusher geometry.
        """
        x, y = position
        return box(x - self.config.width/2, y - self.config.depth/2,
                   x + self.config.width/2, y + self.config.depth/2)
    
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get sector configuration for the crusher.
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
        """Get the linedef action for this crusher type."""
        return CRUSHER_ACTIONS.get(self.config.crusher_type, CrusherAction.WR_CRUSHER_SLOW)
    
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        **kwargs
    ) -> List[int]:
        """
        Apply crusher properties to a sector.
        
        Sets the sector tag and applies crusher linedef action to all
        linedefs that border the crusher sector.
        
        Args:
            editor: MapEditor with the crusher sector.
            sector_index: Index of the crusher sector.
            tag: Sector tag for triggering.
        
        Returns:
            List of modified linedef indices.
        """
        md = editor.map_data
        md.sectors[sector_index]['tag'] = tag
        
        linedef_action = self.get_trigger_action()
        modified = []
        
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
            modified.append(i)
        
        return modified


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

def create_crusher_shape(
    position: Tuple[float, float],
    width: float = 128.0,
    depth: float = 128.0
) -> Polygon:
    """Create a rectangular crusher polygon at the specified position.
    
    Args:
        position: Center position (x, y) for the crusher.
        width: Width of the crusher area.
        depth: Depth of the crusher area.
    
    Returns:
        A Polygon representing the crusher geometry.
    """
    prefab = CrusherPrefab(CrusherConfig(width=width, depth=depth))
    return prefab.create_polygon(position)


def apply_crusher_to_sector(
    editor: 'MapEditor',
    crusher_sector_idx: int,
    tag: int,
    config: Optional[CrusherConfig] = None,
    trigger_action: Optional[int] = None
) -> List[int]:
    """Apply crusher properties to a sector.
    
    Sets the sector tag and applies crusher linedef action to all
    linedefs that border the crusher sector.
    
    Args:
        editor: MapEditor with the crusher sector.
        crusher_sector_idx: Index of the crusher sector.
        tag: Sector tag for triggering.
        config: Crusher configuration.
        trigger_action: Override linedef action type.
    
    Returns:
        List of modified linedef indices.
    """
    if config is None:
        config = CrusherConfig()
    
    # Override action if provided
    if trigger_action is not None:
        for ctype, action in CRUSHER_ACTIONS.items():
            if action == trigger_action:
                config.crusher_type = ctype
                break
    
    prefab = CrusherPrefab(config)
    return prefab.apply_to_map(editor, crusher_sector_idx, tag)


# Preset configurations
CRUSHER_PRESETS = {
    "slow": CrusherConfig(crusher_type=CrusherType.SLOW),
    "fast": CrusherConfig(crusher_type=CrusherType.FAST),
    "silent": CrusherConfig(crusher_type=CrusherType.SILENT),
    "large": CrusherConfig(width=256, depth=256),
}
