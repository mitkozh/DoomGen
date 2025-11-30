"""
Stairs Prefab System - Creates staircases.

Doom stairs are built using the stair-building linedef action which
automatically creates a series of steps by raising floors in sequence.
Each sector in the stair sequence must have the same tag.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, box

from doomgen.doom.specials import StairAction, LinedefFlags
from doomgen.prefabs.base import TriggerPrefab

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class StairType(Enum):
    """Types of stair building."""
    SHORT = "short"    # 8-unit steps
    TALL = "tall"      # 16-unit steps
    FAST = "fast"      # 16-unit steps, fast build


# Map stair types to linedef actions
STAIR_ACTIONS = {
    StairType.SHORT: StairAction.W1_STAIRS_8,
    StairType.TALL: StairAction.S1_STAIRS_16,
    StairType.FAST: StairAction.W1_STAIRS_16_FAST,
}


@dataclass
class StairConfig:
    """Configuration for a stair prefab.
    
    Attributes:
        width: Width of each step in map units (perpendicular to travel).
        step_depth: Depth of each step in map units (along travel direction).
        step_height: Height increment per step.
        num_steps: Number of steps.
        stair_type: Type of stair building action.
        floor_texture: Floor texture for steps.
        wall_texture: Wall/riser texture for step fronts.
        ceiling_height: Ceiling height above stairs.
        light_level: Light level for stair sectors.
    """
    width: float = 128.0
    step_depth: float = 32.0
    step_height: int = 16
    num_steps: int = 8
    stair_type: StairType = StairType.TALL
    floor_texture: str = "STEP1"
    wall_texture: str = "STEP2"
    ceiling_height: int = 192
    light_level: int = 160


class StairPrefab(TriggerPrefab):
    """
    Stair prefab that creates staircases.
    
    Unlike other prefabs, stairs create MULTIPLE sectors (one per step).
    Use create_step_polygons() to get all step geometries.
    
    Example:
        stairs = StairPrefab(StairConfig(num_steps=8))
        steps = stairs.create_step_polygons((100, 0), direction="north")
        
        for i, step in enumerate(steps):
            config = stairs.get_sector_config(step_index=i)
            idx = editor.add_sector_from_polygon(step, config)
        
        stairs.apply_to_map(editor, first_step_idx, tag=1)
    """
    
    def __init__(self, config: Optional[StairConfig] = None):
        """
        Initialize stair prefab.
        
        Args:
            config: Stair configuration (uses defaults if None).
        """
        self.config = config or StairConfig()
        self._base_floor_height = 0
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create a single step polygon (the first step).
        
        For full staircases, use create_step_polygons() instead.
        
        Args:
            position: Starting position (x, y) of the step.
        
        Returns:
            A Polygon representing the first step.
        """
        steps = self.create_step_polygons(position, **kwargs)
        return steps[0] if steps else box(0, 0, 1, 1)
    
    def create_step_polygons(
        self,
        start_position: Tuple[float, float],
        direction: str = "north",
        base_floor_height: int = 0
    ) -> List[Polygon]:
        """
        Create a series of step polygons for a staircase.
        
        Args:
            start_position: Starting position (x, y) of the first step.
            direction: Direction stairs go: "north", "south", "east", "west".
            base_floor_height: Floor height of the first step.
        
        Returns:
            List of Polygons, one for each step.
        """
        self._base_floor_height = base_floor_height
        x, y = start_position
        steps = []
        
        for i in range(self.config.num_steps):
            if direction in ("north", "south"):
                # For north/south, width is along X, depth along Y
                if direction == "north":
                    step = box(
                        x - self.config.width/2,
                        y + i * self.config.step_depth,
                        x + self.config.width/2,
                        y + (i + 1) * self.config.step_depth
                    )
                else:  # south
                    step = box(
                        x - self.config.width/2,
                        y - (i + 1) * self.config.step_depth,
                        x + self.config.width/2,
                        y - i * self.config.step_depth
                    )
            else:
                # For east/west, width is along Y, depth along X
                if direction == "east":
                    step = box(
                        x + i * self.config.step_depth,
                        y - self.config.width/2,
                        x + (i + 1) * self.config.step_depth,
                        y + self.config.width/2
                    )
                else:  # west
                    step = box(
                        x - (i + 1) * self.config.step_depth,
                        y - self.config.width/2,
                        x - i * self.config.step_depth,
                        y + self.config.width/2
                    )
            steps.append(step)
        
        return steps
    
    def get_sector_config(self, step_index: int = 0) -> 'SectorConfig':
        """
        Get sector configuration for a specific step.
        
        Args:
            step_index: Index of the step (0 = first step).
        
        Returns:
            SectorConfig with appropriate floor height for this step.
        """
        from doomgen.doom.translator import SectorConfig
        return SectorConfig(
            floor_height=self._base_floor_height + step_index * self.config.step_height,
            ceiling_height=self.config.ceiling_height,
            floor_texture=self.config.floor_texture,
            ceiling_texture=self.config.floor_texture,  # Same as floor for steps
            light_level=self.config.light_level
        )
    
    def get_trigger_action(self) -> int:
        """Get the linedef action for this stair type."""
        return STAIR_ACTIONS.get(self.config.stair_type, StairAction.W1_STAIRS_8)
    
    def apply_to_map(
        self,
        editor: 'MapEditor',
        sector_index: int,
        tag: int = 0,
        trigger_linedef_idx: Optional[int] = None,
        **kwargs
    ) -> List[int]:
        """
        Apply stair building action to trigger linedef.
        
        The stair building action will raise floors of sectors with
        the same tag in sequence, creating a staircase.
        
        Args:
            editor: MapEditor with the stair sectors.
            sector_index: Index of the first step sector.
            tag: Tag for the stairs (all steps should have this tag).
            trigger_linedef_idx: Specific linedef to use as trigger.
        
        Returns:
            List containing the trigger linedef index.
        """
        md = editor.map_data
        
        # Tag the first step sector
        md.sectors[sector_index]['tag'] = tag
        
        action = self.get_trigger_action()
        
        # Find a linedef to use as trigger
        if trigger_linedef_idx is not None:
            md.linedefs[trigger_linedef_idx]['special'] = int(action)
            md.linedefs[trigger_linedef_idx]['tag'] = tag
            return [trigger_linedef_idx]
        
        # Find first linedef touching the first step sector
        for i, ld in enumerate(md.linedefs):
            front_sd = ld.get('front_sidedef', -1)
            back_sd = ld.get('back_sidedef', -1)
            
            if back_sd < 0:
                continue
            
            front_sec = md.sidedefs[front_sd].get('sector', -1) if front_sd >= 0 else -1
            back_sec = md.sidedefs[back_sd].get('sector', -1)
            
            if front_sec == sector_index or back_sec == sector_index:
                md.linedefs[i]['special'] = int(action)
                md.linedefs[i]['tag'] = tag
                return [i]
        
        return []


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

def create_stair_shapes(
    start_position: Tuple[float, float],
    config: Optional[StairConfig] = None,
    direction: str = "north"
) -> List[Polygon]:
    """Create a series of step polygons for a staircase.
    
    Args:
        start_position: Starting position (x, y) of the first step.
        config: Stair configuration.
        direction: Direction stairs go: "north", "south", "east", "west".
    
    Returns:
        List of Polygons, one for each step.
    """
    if config is None:
        config = StairConfig()
    
    prefab = StairPrefab(config)
    return prefab.create_step_polygons(start_position, direction)


def apply_stair_trigger(
    editor: 'MapEditor',
    first_step_sector_idx: int,
    tag: int,
    config: Optional[StairConfig] = None,
    trigger_linedef_idx: Optional[int] = None
) -> int:
    """Apply stair building action to trigger linedef.
    
    The stair building action will raise floors of sectors with
    the same tag in sequence, creating a staircase.
    
    Args:
        editor: MapEditor with the stair sectors.
        first_step_sector_idx: Index of the first step sector.
        tag: Tag for the stairs (all steps should have this tag).
        config: Stair configuration.
        trigger_linedef_idx: Specific linedef to use as trigger.
    
    Returns:
        Index of the trigger linedef.
    """
    if config is None:
        config = StairConfig()
    
    prefab = StairPrefab(config)
    result = prefab.apply_to_map(
        editor, first_step_sector_idx, tag,
        trigger_linedef_idx=trigger_linedef_idx
    )
    return result[0] if result else -1


# Preset configurations
STAIR_PRESETS = {
    "short": StairConfig(stair_type=StairType.SHORT, step_height=8),
    "tall": StairConfig(stair_type=StairType.TALL, step_height=16),
    "wide": StairConfig(width=256),
    "long": StairConfig(num_steps=16),
}
