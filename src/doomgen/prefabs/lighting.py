"""
Lighting Effects Prefab System - Creates dynamic lighting sectors.

Doom supports various lighting effects through sector specials,
including blinking, flickering, and oscillating lights.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from shapely.geometry import Polygon, box

from doomgen.doom.specials import SectorSpecial, LightAction, LinedefFlags
from doomgen.prefabs.base import SectorModifierPrefab

if TYPE_CHECKING:
    from doomgen.doom.translator import MapEditor, SectorConfig


class LightEffect(Enum):
    """Types of lighting effects."""
    NONE = "none"                    # No special effect
    BLINK_RANDOM = "blink_random"    # Random blinking
    BLINK_HALF_SEC = "blink_half"    # Blink every 0.5 seconds
    BLINK_1_SEC = "blink_1sec"       # Blink every 1 second
    BLINK_SYNC_HALF = "sync_half"    # Synchronized 0.5s blink
    BLINK_SYNC_1SEC = "sync_1sec"    # Synchronized 1s blink
    OSCILLATE = "oscillate"          # Smooth oscillation
    FLICKER = "flicker"              # Random flickering


# Map light effects to sector specials
LIGHT_SPECIALS = {
    LightEffect.NONE: 0,
    LightEffect.BLINK_RANDOM: SectorSpecial.BLINK_RANDOM,
    LightEffect.BLINK_HALF_SEC: SectorSpecial.BLINK_HALF_SEC,
    LightEffect.BLINK_1_SEC: SectorSpecial.BLINK_1_SEC,
    LightEffect.BLINK_SYNC_HALF: SectorSpecial.BLINK_SYNC_HALF,
    LightEffect.BLINK_SYNC_1SEC: SectorSpecial.BLINK_SYNC_1_SEC,
    LightEffect.OSCILLATE: SectorSpecial.OSCILLATE_LIGHT,
    LightEffect.FLICKER: SectorSpecial.FLICKER,
}


@dataclass
class LightConfig:
    """Configuration for lighting effects.
    
    Attributes:
        width: Width of the lighting area.
        depth: Depth of the lighting area.
        effect: Type of lighting effect.
        light_level: Base light level.
        min_light: Minimum light level for blinking effects.
        floor_height: Floor height.
        ceiling_height: Ceiling height.
        floor_texture: Floor texture.
        ceiling_texture: Ceiling texture.
    """
    width: float = 128.0
    depth: float = 128.0
    effect: LightEffect = LightEffect.BLINK_RANDOM
    light_level: int = 192
    min_light: int = 128
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"


class LightingPrefab(SectorModifierPrefab):
    """
    Lighting effect prefab that creates dynamic lighting sectors.
    
    Properly inherits from SectorModifierPrefab and implements all required methods.
    
    Example:
        light = LightingPrefab(LightConfig(effect=LightEffect.FLICKER))
        poly = light.create_polygon((100, 0))
        sector_config = light.get_sector_config()
        idx = editor.add_sector_from_polygon(poly, sector_config)
        light.apply_to_map(editor, idx)
    """
    
    def __init__(self, config: Optional[LightConfig] = None):
        """
        Initialize lighting prefab.
        
        Args:
            config: Lighting configuration (uses defaults if None).
        """
        self.config = config or LightConfig()
    
    def create_polygon(
        self,
        position: Tuple[float, float],
        **kwargs
    ) -> Polygon:
        """
        Create a rectangular lighting area polygon at the specified position.
        
        Args:
            position: Center position (x, y) for the lighting area.
        
        Returns:
            A Polygon representing the lighting area geometry.
        """
        x, y = position
        return box(x - self.config.width/2, y - self.config.depth/2,
                   x + self.config.width/2, y + self.config.depth/2)
    
    def get_sector_config(self) -> 'SectorConfig':
        """
        Get sector configuration for the lighting area.
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
        """Get the sector special for this lighting effect."""
        special = LIGHT_SPECIALS.get(self.config.effect, 0)
        return int(special) if special else 0
    
    def apply_to_sector(
        self,
        editor: 'MapEditor',
        sector_index: int,
        **kwargs
    ) -> None:
        """
        Apply lighting effect to a sector.
        
        Args:
            editor: MapEditor with the sector.
            sector_index: Index of the sector.
        """
        md = editor.map_data
        
        special = self.get_sector_special()
        if special:
            md.sectors[sector_index]['special'] = special
        md.sectors[sector_index]['light_level'] = self.config.light_level
    
    # Legacy alias
    def apply_to_map(self, editor, sector_index, **kwargs) -> None:
        """Legacy alias for apply_to_sector."""
        self.apply_to_sector(editor, sector_index, **kwargs)


# =============================================================================
# Standalone functions for backward compatibility
# =============================================================================

def apply_light_effect(
    editor: 'MapEditor',
    sector_idx: int,
    config: Optional[LightConfig] = None
) -> None:
    """Apply a lighting effect to a sector.
    
    Args:
        editor: MapEditor with the sector.
        sector_idx: Index of the sector.
        config: Lighting configuration.
    """
    if config is None:
        config = LightConfig()
    
    prefab = LightingPrefab(config)
    prefab.apply_to_map(editor, sector_idx)


def apply_light_trigger(
    editor: 'MapEditor',
    sector_idx: int,
    tag: int,
    action: int = LightAction.W1_LIGHT_TO_HIGHEST,
    trigger_linedef_idx: Optional[int] = None
) -> int:
    """Apply a triggered light change to a sector.
    
    Args:
        editor: MapEditor with the sector.
        sector_idx: Index of the target sector.
        tag: Tag for the sector.
        action: Light action type.
        trigger_linedef_idx: Specific linedef to use as trigger.
    
    Returns:
        Index of the trigger linedef.
    """
    md = editor.map_data
    md.sectors[sector_idx]['tag'] = tag
    
    if trigger_linedef_idx is not None:
        md.linedefs[trigger_linedef_idx]['special'] = int(action)
        md.linedefs[trigger_linedef_idx]['tag'] = tag
        return trigger_linedef_idx
    
    # Find first linedef touching the sector
    for i, ld in enumerate(md.linedefs):
        front_sd = ld.get('front_sidedef', -1)
        back_sd = ld.get('back_sidedef', -1)
        
        if back_sd < 0:
            continue
        
        front_sec = md.sidedefs[front_sd].get('sector', -1) if front_sd >= 0 else -1
        back_sec = md.sidedefs[back_sd].get('sector', -1)
        
        if front_sec == sector_idx or back_sec == sector_idx:
            md.linedefs[i]['special'] = int(action)
            md.linedefs[i]['tag'] = tag
            return i
    
    return -1


def create_light_gradient(
    editor: 'MapEditor',
    sector_indices: List[int],
    start_light: int = 255,
    end_light: int = 64
) -> None:
    """Apply a gradient of light levels across multiple sectors.
    
    Args:
        editor: MapEditor with the sectors.
        sector_indices: List of sector indices in order.
        start_light: Starting light level.
        end_light: Ending light level.
    """
    md = editor.map_data
    n = len(sector_indices)
    
    if n < 2:
        if n == 1:
            md.sectors[sector_indices[0]]['light_level'] = start_light
        return
    
    for i, sector_idx in enumerate(sector_indices):
        # Linear interpolation
        t = i / (n - 1)
        light = int(start_light + t * (end_light - start_light))
        md.sectors[sector_idx]['light_level'] = light


# Preset configurations
LIGHT_PRESETS = {
    "strobe_fast": LightConfig(effect=LightEffect.BLINK_HALF_SEC),
    "strobe_slow": LightConfig(effect=LightEffect.BLINK_1_SEC),
    "flicker": LightConfig(effect=LightEffect.FLICKER),
    "pulse": LightConfig(effect=LightEffect.OSCILLATE),
    "emergency": LightConfig(effect=LightEffect.BLINK_SYNC_HALF, light_level=255, min_light=64),
    "dark": LightConfig(effect=LightEffect.NONE, light_level=64),
    "bright": LightConfig(effect=LightEffect.NONE, light_level=255),
}
