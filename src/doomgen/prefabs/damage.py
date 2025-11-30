"""
Damaging Floor Prefab System - Creates nukage, lava, and slime pools.

Doom supports damaging floors through sector specials that apply
periodic damage to players standing on them.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, box, Point

from doomgen.doom.specials import SectorSpecial
from doomgen.prefabs.base import SectorModifierPrefab

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class DamageType(Enum):
    """Types of damaging floors."""
    LIGHT = "light"      # 5 damage (slime)
    MEDIUM = "medium"    # 10 damage (nukage)
    HEAVY = "heavy"      # 20 damage (lava)
    LETHAL = "lethal"    # 20 damage + end level on death


# Map damage types to sector specials
DAMAGE_SPECIALS = {
    DamageType.LIGHT: SectorSpecial.DAMAGE_5,
    DamageType.MEDIUM: SectorSpecial.DAMAGE_10,
    DamageType.HEAVY: SectorSpecial.DAMAGE_20,
    DamageType.LETHAL: SectorSpecial.DAMAGE_20_END,
}

# Default textures for each damage type
DAMAGE_TEXTURES = {
    DamageType.LIGHT: "SLIME01",
    DamageType.MEDIUM: "NUKAGE1",
    DamageType.HEAVY: "LAVA1",
    DamageType.LETHAL: "BLOOD1",
}


@dataclass
class DamageFloorConfig:
    """Configuration for a damaging floor.
    
    Attributes:
        width: Width of the damage pool.
        depth: Depth of the damage pool.
        damage_type: Type of damage.
        floor_texture: Floor texture (typically liquid).
        ceiling_texture: Ceiling texture.
        light_level: Light level for the sector.
        floor_height: Floor height (typically lower than surroundings).
        ceiling_height: Ceiling height.
    """
    width: float = 128.0
    depth: float = 128.0
    damage_type: DamageType = DamageType.MEDIUM
    floor_texture: str = "NUKAGE1"
    ceiling_texture: str = "CEIL3_5"
    light_level: int = 160
    floor_height: int = -8
    ceiling_height: int = 128


class DamageFloorPrefab(SectorModifierPrefab):
    """
    Damaging floor prefab that creates nukage/lava/slime pools.
    
    Properly inherits from SectorModifierPrefab and implements all required methods.
    
    Example:
        damage = DamageFloorPrefab(DamageFloorConfig(damage_type=DamageType.HEAVY))
        poly = damage.create_polygon((100, 0))
        sector_config = damage.get_sector_config()
        idx = editor.add_sector_from_polygon(poly, sector_config)
        damage.apply_to_map(editor, idx)
    """
    
    def __init__(self, config: Optional[DamageFloorConfig] = None):
        """
        Initialize damage floor prefab.
        
        Args:
            config: Damage floor configuration (uses defaults if None).
        """
        self.config = config or DamageFloorConfig()
        # Set floor texture based on damage type if not explicitly set
        if self.config.floor_texture == "NUKAGE1":
            self.config.floor_texture = DAMAGE_TEXTURES.get(
                self.config.damage_type, "NUKAGE1"
            )
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create a rectangular damage pool polygon at the specified position.
        
        Args:
            position: Center position (x, y) for the pool.
        
        Returns:
            A Polygon representing the pool geometry.
        """
        x, y = position
        return box(x - self.config.width/2, y - self.config.depth/2,
                   x + self.config.width/2, y + self.config.depth/2)
    
    def create_circular_polygon(
        self,
        position: Tuple[float, float],
        radius: float = 64.0,
        resolution: int = 16
    ) -> Polygon:
        """
        Create a circular damage pool polygon.
        
        Args:
            position: Center position (x, y) for the pool.
            radius: Radius of the pool.
            resolution: Number of segments in the circle.
        
        Returns:
            A Polygon representing the pool geometry.
        """
        return Point(position).buffer(radius, resolution=resolution)
    
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get sector configuration for the damage floor.
        """
        from doomgen.doom.translator import SectorConfig
        return SectorConfig(
            floor_height=self.config.floor_height,
            ceiling_height=self.config.ceiling_height,
            floor_texture=self.config.floor_texture,
            ceiling_texture=self.config.ceiling_texture,
            light_level=self.config.light_level
        )
    
    def get_sector_special(self) -> int:
        """Get the sector special for this damage type."""
        return int(DAMAGE_SPECIALS.get(self.config.damage_type, SectorSpecial.DAMAGE_10))
    
    def apply_to_sector(
        self,
        editor: 'MapEditor',
        sector_index: int,
        **kwargs
    ) -> None:
        """
        Apply damaging floor properties to a sector.
        
        Sets the sector special type to cause damage.
        
        Args:
            editor: MapEditor with the sector.
            sector_index: Index of the sector to make damaging.
        """
        md = editor.map_data
        md.sectors[sector_index]['special'] = self.get_sector_special()
    
    # Legacy alias
    def apply_to_map(self, editor, sector_index, **kwargs) -> None:
        """Legacy alias for apply_to_sector."""
        self.apply_to_sector(editor, sector_index, **kwargs)


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

def create_damage_pool_shape(
    position: Tuple[float, float],
    width: float = 128.0,
    depth: float = 128.0
) -> Polygon:
    """Create a rectangular damage pool polygon.
    
    Args:
        position: Center position (x, y) for the pool.
        width: Width of the pool.
        depth: Depth of the pool.
    
    Returns:
        A Polygon representing the pool geometry.
    """
    prefab = DamageFloorPrefab(DamageFloorConfig(width=width, depth=depth))
    return prefab.create_polygon(position)


def create_damage_pool_circular(
    position: Tuple[float, float],
    radius: float = 64.0,
    resolution: int = 16
) -> Polygon:
    """Create a circular damage pool polygon.
    
    Args:
        position: Center position (x, y) for the pool.
        radius: Radius of the pool.
        resolution: Number of segments in the circle.
    
    Returns:
        A Polygon representing the pool geometry.
    """
    prefab = DamageFloorPrefab()
    return prefab.create_circular_polygon(position, radius, resolution)


def apply_damage_to_sector(
    editor: 'MapEditor',
    sector_idx: int,
    config: Optional[DamageFloorConfig] = None
) -> None:
    """Apply damaging floor properties to a sector.
    
    Sets the sector special type to cause damage.
    
    Args:
        editor: MapEditor with the sector.
        sector_idx: Index of the sector to make damaging.
        config: Damage floor configuration.
    """
    if config is None:
        config = DamageFloorConfig()
    
    prefab = DamageFloorPrefab(config)
    prefab.apply_to_map(editor, sector_idx)


# Preset configurations
DAMAGE_FLOOR_PRESETS = {
    "slime": DamageFloorConfig(
        damage_type=DamageType.LIGHT,
        floor_texture="SLIME01",
        floor_height=-4
    ),
    "nukage": DamageFloorConfig(
        damage_type=DamageType.MEDIUM,
        floor_texture="NUKAGE1",
        floor_height=-8
    ),
    "lava": DamageFloorConfig(
        damage_type=DamageType.HEAVY,
        floor_texture="LAVA1",
        floor_height=-16
    ),
    "blood": DamageFloorConfig(
        damage_type=DamageType.LETHAL,
        floor_texture="BLOOD1",
        floor_height=-8
    ),
}
