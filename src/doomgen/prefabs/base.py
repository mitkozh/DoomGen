"""
Abstract base classes for prefabs.

All prefabs follow a common pattern:
1. create_polygon(position, **kwargs) - Create the prefab's geometry
2. apply_to_map(editor, sector_index, tag, **kwargs) - Configure sector/linedefs
3. get_sector_config() - Get sector configuration for this prefab
4. place(geometry, position, **kwargs) - Cookie-cutter convenience method

Specialized base classes:
- SectorModifierPrefab: For effects that modify existing sectors (damage, lighting)
- TriggerPrefab: For prefabs activated by triggers (lifts, crushers)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Any, TYPE_CHECKING, Tuple

from shapely.geometry import Polygon, box

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


@dataclass
class PrefabPlacement:
    """
    Result of placing a prefab in a map.
    
    Contains the prefab polygon and any modified geometry resulting
    from cutting the prefab from surrounding areas.
    
    Attributes:
        polygon: The prefab's geometry.
        modified_geometry: Geometry with prefab cut out (may be MultiPolygon).
        sector_index: Index of the sector after adding to map (set after apply).
        tag: Sector/linedef tag (set after apply).
        metadata: Additional prefab-specific data.
    """
    polygon: Polygon
    modified_geometry: Optional[Polygon] = None
    sector_index: int = -1
    tag: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class BasePrefabConfig:
    """
    Base configuration for all prefabs.
    
    Subclasses add prefab-specific attributes.
    
    Attributes:
        width: Prefab width in map units.
        depth: Prefab depth in map units.
        floor_texture: Floor texture name.
        ceiling_texture: Ceiling texture name.
        wall_texture: Wall texture name.
        light_level: Sector light level.
    """
    width: float = 128.0
    depth: float = 128.0
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"
    wall_texture: str = "STARTAN2"
    light_level: int = 160


class BasePrefab(ABC):
    """
    Abstract base class for all map prefabs.
    
    Prefabs are reusable interactive elements that can be placed in a map.
    Each prefab type knows how to:
    - Create its own geometry
    - Apply its properties to the map
    - Handle sector/linedef configuration
    
    Subclasses must implement:
    - create_polygon(): Create the prefab's geometry
    - apply_to_map(): Configure the sector and linedefs
    
    Example usage:
        # Create prefab
        door_prefab = DoorPrefab(config=DoorConfig(width=64))
        
        # Get geometry
        door_poly = door_prefab.create_polygon((128, 0))
        
        # Cut from room
        room_carved = cut_polygon(room, door_poly)
        
        # Add to map
        editor.add_sector_from_polygon(room_carved, room_config)
        door_idx = editor.add_sector_from_polygon(door_poly, door_config)
        
        # Apply prefab properties
        door_prefab.apply_to_map(editor, door_idx, tag=1)
    """
    
    @abstractmethod
    def create_polygon(
        self,
        position: tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create the prefab's geometry at the given position.
        
        Args:
            position: Center position (x, y) for the prefab.
            **kwargs: Prefab-specific options (direction, etc.)
        
        Returns:
            A Polygon representing the prefab geometry.
        """
        pass
    
    @abstractmethod
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        **kwargs
    ) -> List[int]:
        """
        Apply prefab properties to a sector in the map.
        
        Sets up linedef actions, flags, textures, and tags as needed.
        
        Args:
            editor: MapEditor with the prefab sector already added.
            sector_index: Index of the prefab's sector.
            tag: Sector tag for triggering (if applicable).
            **kwargs: Prefab-specific options.
        
        Returns:
            List of modified linedef indices.
        """
        pass
    
    @abstractmethod
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get the SectorConfig for creating this prefab's sector.
        
        Returns:
            SectorConfig with appropriate heights, textures, lighting.
        """
        pass
    
    def place(
        self,
        geometry: Polygon,
        position: tuple[float, float],
        **kwargs
    ) -> PrefabPlacement:
        """
        Create prefab geometry and cut it from surrounding geometry.
        
        This is a convenience method that combines polygon creation
        with the cookie-cutter cut operation.
        
        Args:
            geometry: Room or area geometry to cut from.
            position: Center position for the prefab.
            **kwargs: Passed to create_polygon.
        
        Returns:
            PrefabPlacement with prefab polygon and modified geometry.
        """
        from shapely.validation import make_valid
        
        prefab_poly = self.create_polygon(position, **kwargs)
        
        if not geometry.intersects(prefab_poly):
            raise ValueError(f"Prefab at {position} doesn't intersect geometry")
        
        modified = geometry.difference(prefab_poly)
        if not modified.is_valid:
            modified = make_valid(modified)
        
        return PrefabPlacement(
            polygon=prefab_poly,
            modified_geometry=modified
        )
    
    @classmethod
    def get_default_config(cls) -> BasePrefabConfig:
        """Get the default configuration for this prefab type."""
        return BasePrefabConfig()


class SectorModifierPrefab(BasePrefab):
    """
    Base class for prefabs that modify existing sectors rather than
    creating new geometry.
    
    Examples: damage floors, lighting effects.
    
    These prefabs don't need their own geometry - they apply properties
    to existing sectors.
    """
    
    def create_polygon(
        self,
        position: tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create geometry for a sector modifier.
        
        Override in subclasses if custom geometry is needed.
        Default creates a rectangular area.
        """
        width = kwargs.get('width', 128)
        depth = kwargs.get('depth', 128)
        x, y = position
        return box(x - width/2, y - depth/2, x + width/2, y + depth/2)
    
    def get_sector_config(self) -> 'SectorConfig':
        """Sector modifiers typically don't create new sectors."""
        from doomgen.doom.translator import SectorConfig
        return SectorConfig()
    
    @abstractmethod
    def apply_to_sector(
        self,
        editor: 'MapEditor',
        sector_index: int,
        **kwargs
    ) -> None:
        """
        Apply modifier properties to an existing sector.
        
        Args:
            editor: MapEditor with the sector.
            sector_index: Index of the sector to modify.
            **kwargs: Modifier-specific options.
        """
        pass
    
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        **kwargs
    ) -> List[int]:
        """Apply modifier - delegates to apply_to_sector."""
        self.apply_to_sector(editor, sector_index, **kwargs)
        return []  # Sector modifiers don't modify linedefs


class TriggerPrefab(BasePrefab):
    """
    Base class for prefabs that require trigger activation.
    
    Examples: lifts, crushers, triggered lights.
    
    These prefabs need:
    - A sector tag
    - Linedef action on bordering linedefs
    """
    
    @abstractmethod
    def get_trigger_action(self) -> int:
        """Get the linedef action type for this trigger."""
        pass
    
    def apply_trigger_to_linedefs(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int,
        action: Optional[int] = None
    ) -> List[int]:
        """
        Apply trigger action to all linedefs bordering a sector.
        
        Args:
            editor: MapEditor with the sector.
            sector_index: Index of the triggered sector.
            tag: Sector tag.
            action: Override linedef action (uses get_trigger_action if None).
        
        Returns:
            List of modified linedef indices.
        """
        if action is None:
            action = self.get_trigger_action()
        
        md = editor.map_data
        md.sectors[sector_index]['tag'] = tag
        
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
            
            md.linedefs[i]['special'] = int(action)
            md.linedefs[i]['tag'] = tag
            modified.append(i)
        
        return modified
