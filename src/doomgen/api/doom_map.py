"""
High-level fluent API for Doom map creation.

DoomMapBuilder
-------------------------------------------
    from doomgen import DoomMapBuilder, ThingType
    
    builder = DoomMapBuilder()
    
    # Define rooms
    builder.add_room("spawn", width=256, height=256)
    builder.add_room("arena", width=512, height=512, center=(600, 0))
    
    # Connect rooms
    builder.connect("spawn", "arena", corridor_width=64)
    
    # Add prefabs
    builder.add_door_between("spawn", "arena")
    builder.add_lift("arena", position=(500, 0), lower_height=0, upper_height=64)
    builder.add_crusher("arena", position=(600, 100))
    builder.add_damage_floor("arena", damage_type="lava")
    builder.add_lighting("arena", effect="flicker")
    
    # Add entities
    builder.add_player_start("spawn")
    builder.add_enemies("arena", count=4)
    
    # Save
    builder.save("output/my_map.wad")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, List, Any

import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from doomgen.doom.wad import WADWriter
from doomgen.doom.translator import MapEditor, SectorConfig, WallConfig
from doomgen.doom.things import ThingType
from doomgen.doom.specials import DoorAction, LiftAction, SectorSpecial

from doomgen.geometry.shapes import ShapeBuilder
from doomgen.geometry.builder import (
    MapBuilder,
    BuildResult,
    SlotInfo,
    SlotType,
    CorridorInfo,
    create_corridor_between,
    create_cutout_polygon,
)

from doomgen.prefabs import (
    # Doors
    DoorConfig,
    DoorType,
    apply_door_to_sector,
    create_door_shape,
    # Lifts
    LiftConfig,
    LiftType,
    apply_lift_to_sector,
    create_lift_shape,
    # Crushers
    CrusherConfig,
    CrusherType,
    apply_crusher_to_sector,
    create_crusher_shape,
    # Damage floors
    DamageType,
    DamageFloorConfig,
    apply_damage_to_sector,
    DAMAGE_FLOOR_PRESETS,
    # Lighting
    LightEffect,
    LightConfig,
    apply_light_effect,
    LIGHT_PRESETS,
    # Stairs
    StairConfig,
    StairType,
    create_stair_shapes,
    apply_stair_trigger,
    # Teleporters
    TeleporterConfig,
    TeleportType,
    apply_teleporter_to_sector,
)

from doomgen.logic.acs_builder import ACSBuilder, ScriptType


# =============================================================================
# DoomMapBuilder Config Classes
# =============================================================================

@dataclass
class RoomConfig:
    """Configuration for a room."""
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"
    wall_texture: str = "STARTAN3"
    lower_texture: Optional[str] = None  # For stair risers, etc.
    upper_texture: Optional[str] = None  # For ceiling height differences
    light_level: int = 192


@dataclass
class CorridorConfig:
    """Configuration for a corridor."""
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"
    wall_texture: str = "STARTAN3"
    light_level: int = 160


@dataclass
class DoomDoorConfig:
    """Configuration for a door."""
    width: int = 64
    depth: int = 16
    key_type: Optional[str] = None  # None, "blue", "red", "yellow"
    door_type: DoorType = DoorType.MANUAL
    wall_texture: str = "BIGDOOR2"


@dataclass
class DoomLiftConfig:
    """Configuration for a lift."""
    width: int = 128
    depth: int = 128
    lift_type: LiftType = LiftType.STANDARD
    lower_height: int = 0
    upper_height: int = 64
    floor_texture: str = "FLOOR4_8"
    wall_texture: str = "SUPPORT2"


@dataclass
class DoomCrusherConfig:
    """Configuration for a crusher."""
    width: int = 128
    depth: int = 128
    crusher_type: CrusherType = CrusherType.SLOW
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"


@dataclass
class DoomDamageConfig:
    """Configuration for a damage floor."""
    damage_type: DamageType = DamageType.MEDIUM
    floor_texture: str = "NUKAGE1"
    floor_height: int = -8


@dataclass
class DoomLightConfig:
    """Configuration for lighting effects."""
    effect: LightEffect = LightEffect.BLINK_RANDOM
    light_level: int = 192


@dataclass
class DoomStairConfig:
    """Configuration for stairs."""
    width: float = 128
    step_depth: float = 32
    step_height: int = 16
    num_steps: int = 8
    direction: str = "north"
    floor_texture: str = "STEP1"


@dataclass
class RoomInfo:
    """Internal info about a room."""
    name: str
    polygon: Polygon
    config: RoomConfig
    sector_index: Optional[int] = None
    things: list = field(default_factory=list)
    
    # Optional modifiers applied to the room's sector
    damage_config: Optional[DoomDamageConfig] = None
    light_config: Optional[DoomLightConfig] = None


@dataclass
class PrefabInfo:
    """Information about a prefab to be added."""
    prefab_type: str  # "door", "lift", "crusher", "stairs"
    room_name: str
    room_b_name: Optional[str]  # For between-room prefabs
    position: tuple
    config: Any  # Type-specific config
    tag: int = 0
    polygon: Optional[Polygon] = None
    direction: str = "horizontal"


# =============================================================================
# DoomMapBuilder - High-Level API
# =============================================================================

class DoomMapBuilder:
    """
    High-level fluent API for building Doom maps.
    
    This class orchestrates:
    - Geometry creation (via MapBuilder from geometry module)
    - Prefab placement (doors, lifts, crushers, etc.)
    - Thing placement (enemies, items, players)
    - WAD output
    
    Example:
        builder = DoomMapBuilder()
        
        # Define rooms
        builder.add_room("spawn", width=256, height=256)
        builder.add_room("arena", width=512, height=512, center=(500, 0))
        
        # Connect rooms
        builder.connect("spawn", "arena", corridor_width=64)
        
        # Add prefabs
        builder.add_door_between("spawn", "arena")
        builder.add_lift("arena", position=(400, 0), upper_height=64)
        builder.add_crusher("arena", position=(500, 100))
        
        # Add entities
        builder.add_player_start("spawn")
        builder.add_enemies("arena", ThingType.IMP, count=4)
        
        # Save
        builder.save("output/my_map.wad")
    """
    
    def __init__(
        self,
        map_name: str = "MAP01",
        grid_size: int = 8,
        seed: Optional[int] = None
    ):
        """
        Initialize the DoomMapBuilder.
        
        Args:
            map_name: Name of the map (e.g., "MAP01").
            grid_size: Grid size for snapping (default 8).
            seed: Random seed for reproducibility.
        """
        self.map_name = map_name
        self.grid_size = grid_size
        self.seed = seed
        
        self._shape_builder = ShapeBuilder(seed=seed)
        self._map_builder = MapBuilder(grid_size=grid_size, seed=seed)
        
        self._rooms: dict[str, RoomInfo] = {}
        self._default_room_config = RoomConfig()
        self._default_corridor_config = CorridorConfig()
        
        # Track prefabs
        self._prefabs: list[PrefabInfo] = []
        self._connections: list[tuple[str, str, int]] = []
        
        # Corridor configs by connection
        self._corridor_configs: dict[tuple[str, str], CorridorConfig] = {}
        
        # Tag counter for triggers
        self._next_tag = 1
        
        # ACS support
        self._acs_builder: Optional[ACSBuilder] = None
        self._acs_source_path: Optional[Path] = None
    
    def _get_next_tag(self) -> int:
        """Get the next available tag number."""
        tag = self._next_tag
        self._next_tag += 1
        return tag
    
    # =========================================================================
    # Room Creation
    # =========================================================================
    
    def add_room(
        self,
        name: str,
        width: float = 256,
        height: float = 256,
        center: tuple[float, float] = (0, 0),
        config: Optional[RoomConfig] = None,
        polygon: Optional[Polygon] = None
    ) -> "DoomMapBuilder":
        """
        Add a rectangular room.
        
        Args:
            name: Unique room identifier.
            width: Room width.
            height: Room height.
            center: Center position (x, y).
            config: Optional room configuration.
            polygon: Optional custom polygon (overrides width/height).
        
        Returns:
            Self for chaining.
        """
        if polygon is None:
            polygon = self._shape_builder.create_rectangle(width, height, center)
        
        self._map_builder.add_room(name, polygon)
        self._rooms[name] = RoomInfo(
            name=name,
            polygon=polygon,
            config=config or RoomConfig()
        )
        
        return self
    
    def add_irregular_room(
        self,
        name: str,
        radius: float = 256,
        sides: int = 6,
        irregularity: float = 0.3,
        center: tuple[float, float] = (0, 0),
        config: Optional[RoomConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add an irregular polygon room.
        
        Args:
            name: Unique room identifier.
            radius: Approximate room radius.
            sides: Number of sides.
            irregularity: How much to vary vertex positions (0.0-0.5).
            center: Center position (x, y).
            config: Optional room configuration.
        
        Returns:
            Self for chaining.
        """
        polygon = self._shape_builder.create_irregular_polygon(
            center, radius, sides, irregularity
        )
        
        self._map_builder.add_room(name, polygon)
        self._rooms[name] = RoomInfo(
            name=name,
            polygon=polygon,
            config=config or RoomConfig()
        )
        
        return self
    
    def add_polygon_room(
        self,
        name: str,
        sides: int = 8,
        radius: float = 256,
        center: tuple[float, float] = (0, 0),
        config: Optional[RoomConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a regular polygon room (octagon, hexagon, etc.).
        
        Args:
            name: Unique room identifier.
            sides: Number of sides.
            radius: Distance from center to vertices.
            center: Center position (x, y).
            config: Optional room configuration.
        
        Returns:
            Self for chaining.
        """
        polygon = self._shape_builder.create_polygon(sides, radius, center)
        
        self._map_builder.add_room(name, polygon)
        self._rooms[name] = RoomInfo(
            name=name,
            polygon=polygon,
            config=config or RoomConfig()
        )
        
        return self
    
    def add_merged_room(
        self,
        name: str,
        *polygons: Polygon,
        config: Optional[RoomConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a room from merged polygons (e.g., L-shaped rooms).
        
        Args:
            name: Unique room identifier.
            *polygons: Polygons to merge.
            config: Optional room configuration.
        
        Returns:
            Self for chaining.
        """
        merged = unary_union(polygons)
        if merged.geom_type == 'MultiPolygon':
            merged = max(merged.geoms, key=lambda p: p.area)
        
        self._map_builder.add_room(name, merged)
        self._rooms[name] = RoomInfo(
            name=name,
            polygon=merged,
            config=config or RoomConfig()
        )
        
        return self
    
    # =========================================================================
    # Connections
    # =========================================================================
    
    def connect(
        self,
        room_a: str,
        room_b: str,
        corridor_width: int = 64,
        corridor_config: Optional[CorridorConfig] = None,
        name: Optional[str] = None,
        style: str = "straight",
        # L-system specific options
        grammar_name: str = "organic",
        iterations: int = 2,
        max_deviation: Optional[float] = 0.25,
        seed: Optional[int] = None
    ) -> "DoomMapBuilder":
        """
        Connect two rooms with a corridor.
        
        Supports multiple corridor styles:
        - "straight": Direct straight-line corridor (default)
        - "lsystem" or "lsystem:<grammar>": Procedural winding corridor
        
        Available L-system grammars:
            Organic/Straight:
            - 'direct': Almost straight, minimal deviation (5°)
            - 'wavy': Gentle wave pattern (8°)
            - 'wobble': Nearly straight with tiny deviations (10°)
            - 'organic': Natural looking slight curves (12°)
            - 'gentle': Mostly straight with slight bends (15°)
            - 'kinked': Mostly straight with occasional turns (20°)
            
            Complex/Winding:
            - 'serpentine': Serpentine path (45° turns)
            - 'koch': Koch-like curve (60° turns)
            - 'zigzag': Sharp zigzag pattern (90° turns)
            - 'meander': Meandering path (90° turns)
        
        Args:
            room_a: First room name.
            room_b: Second room name.
            corridor_width: Width of the corridor.
            corridor_config: Optional corridor configuration (textures, heights).
            name: Optional corridor name (for door placement via add_corridor_door).
            style: Corridor style - "straight" or "lsystem:<grammar>".
            grammar_name: L-System grammar (when style="lsystem").
            iterations: L-System iterations (when style="lsystem").
            max_deviation: Max deviation for L-System (fraction of distance).
            seed: Random seed for L-System generation.
        
        Returns:
            Self for chaining.
        
        Example:
            # Straight corridor
            builder.connect("hub", "arena", corridor_width=64)
            
            # L-system corridor
            builder.connect("hub", "arena", style="lsystem:serpentine", name="main")
            builder.add_corridor_door("main", end="a")
        """
        self._map_builder.add_corridor(
            room_a, room_b, corridor_width,
            name=name,
            style=style,
            grammar_name=grammar_name,
            iterations=iterations,
            max_deviation=max_deviation,
            seed=seed
        )
        self._connections.append((room_a, room_b, corridor_width))
        if corridor_config:
            self._corridor_configs[(room_a, room_b)] = corridor_config
        return self
    
    def add_custom_corridor(
        self,
        room_a: str,
        room_b: str,
        polygon: Polygon,
        corridor_config: Optional[CorridorConfig] = None,
        name: Optional[str] = None
    ) -> "DoomMapBuilder":
        """
        Add a custom polygon corridor between two rooms.
        
        Use this when you need full control over the corridor shape.
        The polygon will be used as-is, and rooms will be carved to connect.
        
        Args:
            room_a: First room name.
            room_b: Second room name.
            polygon: Custom corridor polygon.
            corridor_config: Optional corridor configuration.
            name: Optional corridor name (for door placement via add_corridor_door).
        
        Returns:
            Self for chaining.
        
        Example:
            from shapely.geometry import Polygon
            corridor_poly = Polygon([...])  # Your custom shape
            builder.add_custom_corridor("hub", "arena", corridor_poly, name="main_hall")
        """
        if room_a not in self._rooms:
            raise KeyError(f"Room '{room_a}' not found")
        if room_b not in self._rooms:
            raise KeyError(f"Room '{room_b}' not found")
        
        self._map_builder.add_corridor(
            room_a, room_b, 0,  # width ignored for custom
            style="custom",
            polygon=polygon,
            name=name
        )
        self._connections.append((room_a, room_b, 0))
        if corridor_config:
            self._corridor_configs[(room_a, room_b)] = corridor_config
        return self
    
    def get_corridor(self, name: str):
        """
        Get corridor data by name.
        
        Args:
            name: Corridor name.
        
        Returns:
            CorridorData for the named corridor, or None if not found.
        
        Example:
            builder.connect("hub", "arena", name="main_corridor")
            corridor = builder.get_corridor("main_corridor")
            if corridor:
                print(f"Corridor connects {corridor.room_a} to {corridor.room_b}")
        """
        return self._map_builder.get_corridor(name)
    
    def list_corridors(self) -> list[str]:
        """
        List all named corridors.
        
        Returns:
            List of corridor names.
        """
        return self._map_builder.list_corridors()
    
    # =========================================================================
    # Procedural Modifiers
    # =========================================================================
    
    def subdivide_room(
        self,
        room_name: str,
        iterations: int = 2,
        roughness: float = 0.3,
        seed: Optional[int] = None
    ) -> "DoomMapBuilder":
        """
        Apply recursive subdivision to a room's edges.
        
        This creates a fractal-like perturbation of edges, useful for
        creating organic or ruined-looking room shapes (caves, ruins, etc.).
        
        Args:
            room_name: Name of the room to modify.
            iterations: Number of subdivision iterations (each doubles vertex count).
            roughness: Displacement magnitude as fraction of edge length (0.0 to 1.0).
            seed: Random seed for reproducibility.
        
        Returns:
            Self for chaining.
        
        Example:
            builder.add_room("cave", width=256, height=256)
            builder.subdivide_room("cave", iterations=2, roughness=0.2)
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        self._map_builder.subdivide_room(room_name, iterations, roughness, seed)
        # Update stored polygon
        self._rooms[room_name].polygon = self._map_builder._rooms[room_name]
        return self
    
    def add_noise_to_room(
        self,
        room_name: str,
        noise_scale: float = 10.0,
        seed: Optional[int] = None
    ) -> "DoomMapBuilder":
        """
        Add random noise to a room's vertices.
        
        Unlike subdivide_room, this doesn't add new vertices,
        just displaces existing ones. Good for subtle irregularities.
        
        Args:
            room_name: Name of the room to modify.
            noise_scale: Maximum displacement in map units.
            seed: Random seed for reproducibility.
        
        Returns:
            Self for chaining.
        
        Example:
            builder.add_room("ruins", width=256, height=256)
            builder.add_noise_to_room("ruins", noise_scale=8)
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        self._map_builder.add_noise_to_room(room_name, noise_scale, seed)
        # Update stored polygon
        self._rooms[room_name].polygon = self._map_builder._rooms[room_name]
        return self
    
    def add_corridor_door(
        self,
        corridor_name: str,
        end: str = "a",
        width: Optional[float] = None,
        depth: float = 16,
        tag: Optional[int] = None,
        key_type: Optional[str] = None,
        **metadata
    ) -> "DoomMapBuilder":
        """
        Add a door at a corridor entrance.
        
        Places a door at the specified end of a named corridor (any type).
        The door is automatically positioned inside the room and aligned
        perpendicular to the corridor direction.
        
        Args:
            corridor_name: Name of the corridor (from connect() or add_custom_corridor()).
            end: Which end of corridor: "a" (first room) or "b" (second room).
            width: Door width (defaults to corridor width if not specified).
            depth: Door depth/thickness.
            tag: Sector tag for ACS control.
            key_type: Key type for keyed doors ("blue", "red", "yellow").
            **metadata: Additional metadata stored with the door.
        
        Returns:
            Self for chaining.
        
        Example:
            builder.connect("hub", "arena", name="corridor1", style="lsystem:serpentine")
            builder.add_corridor_door("corridor1", end="b", tag=1)  # Door at arena
        """
        # Get corridor data to determine actual width and position
        corridor = self._map_builder._corridors.get(corridor_name)
        if corridor is None:
            raise KeyError(f"Corridor '{corridor_name}' not found")
        
        actual_width = width if width is not None else corridor.width
        
        # Register the slot with the geometry builder
        self._map_builder.add_corridor_door(
            corridor_name, end=end, width=actual_width, depth=depth,
            tag=tag, key_type=key_type, **metadata
        )
        
        # Register a prefab for door creation during save()
        # room_name stores corridor name, room_b_name stores which end
        cfg = DoomDoorConfig(width=int(actual_width), depth=int(depth), key_type=key_type)
        
        self._prefabs.append(PrefabInfo(
            prefab_type="corridor_door",
            room_name=corridor_name,  # Store corridor name
            room_b_name=end,  # Store which end ("a" or "b")
            position=(0, 0),  # Position determined from slot during build
            config=cfg,
            tag=tag if tag is not None else self._get_next_tag()
        ))
        
        return self
    
    def apply_modifier(
        self,
        room_name: str,
        modifier_fn,
        *args,
        **kwargs
    ) -> "DoomMapBuilder":
        """
        Apply a custom modifier function to a room.
        
        This allows using any function that takes a Polygon and returns
        a Polygon as a room modifier.
        
        Args:
            room_name: Name of the room to modify.
            modifier_fn: Function that takes (Polygon, *args, **kwargs) -> Polygon.
            *args: Additional positional arguments to pass to the modifier.
            **kwargs: Additional keyword arguments to pass to the modifier.
        
        Returns:
            Self for chaining.
        
        Example:
            from shapely.affinity import scale
            builder.add_room("arena", width=256, height=256)
            builder.apply_modifier("arena", scale, xfact=1.5, yfact=1.0)
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        self._map_builder.apply_modifier(room_name, modifier_fn, *args, **kwargs)
        # Update stored polygon
        self._rooms[room_name].polygon = self._map_builder._rooms[room_name]
        return self
    
    # =========================================================================
    # Doors
    # =========================================================================
    
    def add_door(
        self,
        room_name: str,
        position: tuple[float, float],
        width: int = 64,
        depth: int = 16,
        direction: str = "horizontal",
        key_type: Optional[str] = None,
        config: Optional[DoomDoorConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a door to a room at a specific position.
        
        Args:
            room_name: Room to add door to.
            position: Door position (x, y).
            width: Door width.
            depth: Door depth.
            direction: "horizontal" or "vertical".
            key_type: Key required (None, "blue", "red", "yellow").
            config: Optional door configuration.
        
        Returns:
            Self for chaining.
        """
        cfg = config or DoomDoorConfig(width=width, depth=depth, key_type=key_type)
        poly = create_door_shape(position, cfg.width, cfg.depth, direction)
        
        self._map_builder.add_slot(
            room_name, position, cfg.width, cfg.depth, direction,
            slot_type="door", key_type=key_type
        )
        
        self._prefabs.append(PrefabInfo(
            prefab_type="door",
            room_name=room_name,
            room_b_name=None,
            position=position,
            config=cfg,
            polygon=poly,
            direction=direction
        ))
        
        return self
    
    def add_door_between(
        self,
        room_a: str,
        room_b: str,
        position: Optional[tuple[float, float]] = None,
        width: int = 64,
        depth: int = 16,
        direction: str = "auto",
        key_type: Optional[str] = None,
        config: Optional[DoomDoorConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a door between two adjacent rooms.
        
        Args:
            room_a: First room.
            room_b: Second room.
            position: Door position (auto-calculated if None).
            width: Door width.
            depth: Door depth.
            direction: "horizontal", "vertical", or "auto".
            key_type: Key required (None, "blue", "red", "yellow").
            config: Optional door configuration.
        
        Returns:
            Self for chaining.
        """
        cfg = config or DoomDoorConfig(width=width, depth=depth, key_type=key_type)
        
        # Auto-calculate position if not provided
        if position is None:
            poly_a = self._rooms[room_a].polygon
            poly_b = self._rooms[room_b].polygon
            ca, cb = poly_a.centroid, poly_b.centroid
            position = ((ca.x + cb.x) / 2, (ca.y + cb.y) / 2)
        
        # Auto-detect direction
        if direction == "auto":
            poly_a = self._rooms[room_a].polygon
            poly_b = self._rooms[room_b].polygon
            ca, cb = poly_a.centroid, poly_b.centroid
            if abs(cb.x - ca.x) > abs(cb.y - ca.y):
                direction = "vertical"  # Rooms are horizontal, door is vertical
            else:
                direction = "horizontal"  # Rooms are vertical, door is horizontal
        
        poly = create_door_shape(position, cfg.width, cfg.depth, direction)
        
        self._map_builder.add_slot_between(
            room_a, room_b, position, cfg.width, cfg.depth, direction,
            slot_type="door", key_type=key_type
        )
        
        self._prefabs.append(PrefabInfo(
            prefab_type="door",
            room_name=room_a,
            room_b_name=room_b,
            position=position,
            config=cfg,
            polygon=poly,
            direction=direction
        ))
        
        return self
    
    # =========================================================================
    # Lifts
    # =========================================================================
    
    def add_lift(
        self,
        room_name: str,
        position: tuple[float, float],
        width: int = 128,
        depth: int = 128,
        lower_height: int = 0,
        upper_height: int = 64,
        lift_type: LiftType = LiftType.STANDARD,
        config: Optional[DoomLiftConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a lift to a room.
        
        Args:
            room_name: Room to add lift to.
            position: Lift position (x, y).
            width: Lift width.
            depth: Lift depth.
            lower_height: Floor height when lowered.
            upper_height: Floor height when raised.
            lift_type: Type of lift behavior.
            config: Optional lift configuration.
        
        Returns:
            Self for chaining.
        """
        cfg = config or DoomLiftConfig(
            width=width, depth=depth, 
            lower_height=lower_height, upper_height=upper_height,
            lift_type=lift_type
        )
        
        poly = create_lift_shape(position, cfg.width, cfg.depth)
        tag = self._get_next_tag()
        
        self._map_builder.add_slot(
            room_name, position, cfg.width, cfg.depth, "horizontal",
            slot_type="lift", polygon=poly
        )
        
        self._prefabs.append(PrefabInfo(
            prefab_type="lift",
            room_name=room_name,
            room_b_name=None,
            position=position,
            config=cfg,
            tag=tag,
            polygon=poly
        ))
        
        return self
    
    def add_lift_between(
        self,
        room_a: str,
        room_b: str,
        position: tuple[float, float],
        width: int = 128,
        depth: int = 128,
        config: Optional[DoomLiftConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a lift between two rooms at different heights.
        
        The lift's heights are auto-calculated from the room floor heights.
        
        Args:
            room_a: First room.
            room_b: Second room.
            position: Lift position.
            width: Lift width.
            depth: Lift depth.
            config: Optional lift configuration.
        
        Returns:
            Self for chaining.
        """
        # Get floor heights from room configs
        h_a = self._rooms[room_a].config.floor_height
        h_b = self._rooms[room_b].config.floor_height
        lower_h = min(h_a, h_b)
        upper_h = max(h_a, h_b)
        
        cfg = config or DoomLiftConfig(
            width=width, depth=depth,
            lower_height=lower_h, upper_height=upper_h
        )
        
        poly = create_lift_shape(position, cfg.width, cfg.depth)
        tag = self._get_next_tag()
        
        self._map_builder.add_slot_between(
            room_a, room_b, position, cfg.width, cfg.depth, "horizontal",
            slot_type="lift", polygon=poly
        )
        
        self._prefabs.append(PrefabInfo(
            prefab_type="lift",
            room_name=room_a,
            room_b_name=room_b,
            position=position,
            config=cfg,
            tag=tag,
            polygon=poly
        ))
        
        return self
    
    # =========================================================================
    # Crushers
    # =========================================================================
    
    def add_crusher(
        self,
        room_name: str,
        position: tuple[float, float],
        width: int = 128,
        depth: int = 128,
        crusher_type: CrusherType = CrusherType.SLOW,
        config: Optional[DoomCrusherConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add a crusher trap to a room.
        
        Args:
            room_name: Room to add crusher to.
            position: Crusher position (x, y).
            width: Crusher area width.
            depth: Crusher area depth.
            crusher_type: Type of crusher behavior.
            config: Optional crusher configuration.
        
        Returns:
            Self for chaining.
        """
        cfg = config or DoomCrusherConfig(
            width=width, depth=depth, crusher_type=crusher_type
        )
        
        poly = create_crusher_shape(position, cfg.width, cfg.depth)
        tag = self._get_next_tag()
        
        self._map_builder.add_slot(
            room_name, position, cfg.width, cfg.depth, "horizontal",
            slot_type="crusher", polygon=poly
        )
        
        self._prefabs.append(PrefabInfo(
            prefab_type="crusher",
            room_name=room_name,
            room_b_name=None,
            position=position,
            config=cfg,
            tag=tag,
            polygon=poly
        ))
        
        return self
    
    # =========================================================================
    # Damage Floors
    # =========================================================================
    
    def add_damage_floor(
        self,
        room_name: str,
        damage_type: Union[str, DamageType] = DamageType.MEDIUM,
        floor_texture: Optional[str] = None,
        floor_height: int = -8
    ) -> "DoomMapBuilder":
        """
        Make a room's floor damaging.
        
        Args:
            room_name: Room to modify.
            damage_type: Type of damage ("light", "medium", "heavy", "lethal").
            floor_texture: Floor texture (auto-selected if None).
            floor_height: Floor height offset.
        
        Returns:
            Self for chaining.
        """
        if isinstance(damage_type, str):
            damage_type = DamageType(damage_type)
        
        # Auto-select texture based on damage type
        texture_map = {
            DamageType.LIGHT: "SLIME01",
            DamageType.MEDIUM: "NUKAGE1",
            DamageType.HEAVY: "LAVA1",
            DamageType.LETHAL: "BLOOD1",
        }
        if floor_texture is None:
            floor_texture = texture_map.get(damage_type, "NUKAGE1")
        
        self._rooms[room_name].damage_config = DoomDamageConfig(
            damage_type=damage_type,
            floor_texture=floor_texture,
            floor_height=floor_height
        )
        
        return self
    
    # =========================================================================
    # Lighting Effects
    # =========================================================================
    
    def add_lighting(
        self,
        room_name: str,
        effect: Union[str, LightEffect] = LightEffect.BLINK_RANDOM,
        light_level: int = 192
    ) -> "DoomMapBuilder":
        """
        Add a lighting effect to a room.
        
        Args:
            room_name: Room to modify.
            effect: Lighting effect type.
            light_level: Base light level.
        
        Returns:
            Self for chaining.
        """
        if isinstance(effect, str):
            # Map string names to enum values
            effect_map = {
                "blink_random": LightEffect.BLINK_RANDOM,
                "blink_half": LightEffect.BLINK_HALF_SEC,
                "blink_1sec": LightEffect.BLINK_1_SEC,
                "sync_half": LightEffect.BLINK_SYNC_HALF,
                "sync_1sec": LightEffect.BLINK_SYNC_1SEC,
                "oscillate": LightEffect.OSCILLATE,
                "flicker": LightEffect.FLICKER,
            }
            effect = effect_map.get(effect, LightEffect.BLINK_RANDOM)
        
        self._rooms[room_name].light_config = DoomLightConfig(
            effect=effect,
            light_level=light_level
        )
        
        return self
    
    # =========================================================================
    # Stairs
    # =========================================================================
    
    def add_stairs(
        self,
        room_name: str,
        position: tuple[float, float],
        direction: str = "north",
        num_steps: int = 8,
        step_height: int = 16,
        step_depth: float = 32,
        width: float = 128,
        config: Optional[DoomStairConfig] = None
    ) -> "DoomMapBuilder":
        """
        Add stairs to a room.
        
        Args:
            room_name: Room to add stairs to.
            position: Starting position.
            direction: Direction ("north", "south", "east", "west").
            num_steps: Number of steps.
            step_height: Height per step.
            step_depth: Depth per step.
            width: Stair width.
            config: Optional stair configuration.
        
        Returns:
            Self for chaining.
        """
        cfg = config or DoomStairConfig(
            width=width,
            step_depth=step_depth,
            step_height=step_height,
            num_steps=num_steps,
            direction=direction
        )
        
        tag = self._get_next_tag()
        
        self._prefabs.append(PrefabInfo(
            prefab_type="stairs",
            room_name=room_name,
            room_b_name=None,
            position=position,
            config=cfg,
            tag=tag
        ))
        
        return self
    
    # =========================================================================
    # ACS Scripting
    # =========================================================================
    
    def _ensure_acs_builder(self) -> ACSBuilder:
        """Ensure ACS builder is initialized."""
        if self._acs_builder is None:
            self._acs_builder = ACSBuilder()
            self._acs_builder.add_include("zcommon.acs")
        return self._acs_builder
    
    def add_acs_script(
        self,
        script_type: ScriptType,
        body: str,
        number: Optional[int] = None
    ) -> "DoomMapBuilder":
        """
        Add an ACS script to the map.
        
        Args:
            script_type: Type of script (OPEN, ENTER, etc.)
            body: Script body code (C-style ACS).
            number: Optional script number.
        
        Returns:
            Self for chaining.
        
        Example:
            builder.add_acs_script(
                ScriptType.OPEN,
                '''
                Delay(35);
                Print(s:"Welcome to the map!");
                '''
            )
        """
        acs = self._ensure_acs_builder()
        acs.add_script(script_type, body, number)
        return self
    
    def add_acs_global_var(
        self,
        name: str,
        var_type: str = "int",
        initial: Optional[int] = None
    ) -> "DoomMapBuilder":
        """
        Add a global variable to the ACS scripts.
        
        Args:
            name: Variable name.
            var_type: Variable type ("int", "str").
            initial: Initial value.
        
        Returns:
            Self for chaining.
        """
        acs = self._ensure_acs_builder()
        acs.add_global_var(name, var_type, initial)
        return self
    
    def add_acs_define(self, name: str, value: Any) -> "DoomMapBuilder":
        """
        Add a #define macro to the ACS scripts.
        
        Args:
            name: Macro name.
            value: Macro value.
        
        Returns:
            Self for chaining.
        """
        acs = self._ensure_acs_builder()
        acs.add_define(name, value)
        return self
    
    def add_welcome_message(self, message: str, delay: int = 35) -> "DoomMapBuilder":
        """
        Add a welcome message that displays when the map opens.
        
        Args:
            message: Message to display.
            delay: Delay before showing (tics, 35 = 1 second).
        
        Returns:
            Self for chaining.
        """
        escaped = message.replace('"', '\\"')
        body = f'Delay({delay});\nPrint(s:"{escaped}");'
        return self.add_acs_script(ScriptType.OPEN, body)
    
    def add_survival_timer(
        self,
        waves: list[tuple[str, int]],
        intro_message: str = "SURVIVAL CHALLENGE"
    ) -> "DoomMapBuilder":
        """
        Add a timed survival challenge with wave announcements.
        
        Args:
            waves: List of (wave_name, duration_tics) tuples.
            intro_message: Initial message.
        
        Returns:
            Self for chaining.
        
        Example:
            builder.add_survival_timer([
                ("Wave 1 - Zombies!", 350),
                ("Wave 2 - Imps!", 350),
                ("Wave 3 - Demons!", 350),
            ])
        """
        acs = self._ensure_acs_builder()
        acs.add_global_var("currentWave", "int", 0)
        
        lines = [
            'Delay(35);',
            f'Print(s:"{intro_message}");',
            'Delay(70);',
            'Print(s:"Survive the waves!");',
            'Delay(105);',
            ''
        ]
        
        for i, (wave_name, duration) in enumerate(waves, 1):
            escaped = wave_name.replace('"', '\\"')
            lines.append(f'currentWave = {i};')
            lines.append(f'Print(s:"{escaped}");')
            lines.append(f'Delay({duration});')
            lines.append('')
        
        lines.append('Print(s:"CHALLENGE COMPLETE!");')
        
        body = '\n'.join(lines)
        return self.add_acs_script(ScriptType.OPEN, body)
    
    def get_acs_source(self) -> Optional[str]:
        """
        Get the ACS source code.
        
        Returns:
            ACS source code string, or None if no scripts added.
        """
        if self._acs_builder is None:
            return None
        return self._acs_builder.to_code()
    
    def set_acs_source_save_path(self, path: Union[str, Path]) -> "DoomMapBuilder":
        """
        Set the path to save ACS source file alongside the WAD.
        
        Args:
            path: Path for the .acs source file.
        
        Returns:
            Self for chaining.
        """
        self._acs_source_path = Path(path)
        return self
    
    # =========================================================================
    # Things
    # =========================================================================
    
    def add_player_start(
        self,
        room_name: str,
        position: Optional[tuple[float, float]] = None,
        angle: int = 0
    ) -> "DoomMapBuilder":
        """
        Add player 1 start to a room.
        
        Args:
            room_name: Room to place player in.
            position: Position (uses room center if None).
            angle: Facing angle in degrees.
        
        Returns:
            Self for chaining.
        """
        if position is None:
            centroid = self._rooms[room_name].polygon.centroid
            position = (centroid.x, centroid.y)
        
        self._rooms[room_name].things.append({
            "type": ThingType.PLAYER1_START,
            "x": position[0],
            "y": position[1],
            "angle": angle
        })
        return self
    
    def add_thing(
        self,
        room_name: str,
        thing_type: ThingType,
        position: Optional[tuple[float, float]] = None,
        angle: int = 0
    ) -> "DoomMapBuilder":
        """
        Add a thing to a room.
        
        Args:
            room_name: Room to place thing in.
            thing_type: Type of thing.
            position: Position (uses room center if None).
            angle: Facing angle in degrees.
        
        Returns:
            Self for chaining.
        """
        if position is None:
            centroid = self._rooms[room_name].polygon.centroid
            position = (centroid.x, centroid.y)
        
        self._rooms[room_name].things.append({
            "type": thing_type,
            "x": position[0],
            "y": position[1],
            "angle": angle
        })
        return self
    
    def add_enemies(
        self,
        room_name: str,
        enemy_type: ThingType = ThingType.IMP,
        count: int = 4,
        positions: Optional[list[tuple[float, float]]] = None
    ) -> "DoomMapBuilder":
        """
        Add enemies to a room.
        
        Args:
            room_name: Room to place enemies in.
            enemy_type: Type of enemy.
            count: Number of enemies (if positions not specified).
            positions: Specific positions (overrides count).
        
        Returns:
            Self for chaining.
        """
        polygon = self._rooms[room_name].polygon
        
        if positions is None:
            # Distribute enemies around room perimeter
            inner = polygon.buffer(-32)
            if inner.is_empty:
                inner = polygon
            
            perimeter = inner.exterior
            length = perimeter.length
            
            positions = []
            for i in range(count):
                distance = (i / count) * length
                point = perimeter.interpolate(distance)
                positions.append((point.x, point.y))
        
        for x, y in positions:
            centroid = polygon.centroid
            dx, dy = centroid.x - x, centroid.y - y
            angle = int(np.degrees(np.arctan2(dy, dx))) % 360
            
            self._rooms[room_name].things.append({
                "type": enemy_type,
                "x": x,
                "y": y,
                "angle": angle
            })
        
        return self
    
    # =========================================================================
    # Building & Saving
    # =========================================================================
    
    def build(self) -> BuildResult:
        """
        Build the map geometry.
        
        Returns:
            BuildResult with all carved rooms and elements.
        """
        return self._map_builder.build()
    
    def save(self, path: Union[str, Path]) -> Path:
        """
        Build and save the map to a WAD file.
        
        Args:
            path: Output path for the WAD file.
        
        Returns:
            Path to the saved WAD file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build geometry
        result = self.build()
        
        if not result.is_valid:
            print(f"Warning: Build had errors: {result.errors}")
        
        # Create WAD
        wad = WADWriter()
        map_data = wad.create_map(self.map_name)
        editor = MapEditor(map_data)
        
        # Track sector indices
        room_sectors: dict[str, int] = {}
        
        # Add rooms
        for name, room_info in self._rooms.items():
            polygon = result.rooms.get(name, room_info.polygon)
            cfg = room_info.config
            
            # Apply damage floor height if set
            floor_height = cfg.floor_height
            floor_texture = cfg.floor_texture
            if room_info.damage_config:
                floor_height = room_info.damage_config.floor_height
                floor_texture = room_info.damage_config.floor_texture
            
            # Apply light level from light config if set
            light_level = cfg.light_level
            if room_info.light_config:
                light_level = room_info.light_config.light_level
            
            sector_config = SectorConfig(
                floor_height=floor_height,
                ceiling_height=cfg.ceiling_height,
                floor_texture=floor_texture,
                ceiling_texture=cfg.ceiling_texture,
                light_level=light_level
            )
            wall_config = WallConfig(
                middle_texture=cfg.wall_texture,
                lower_texture=cfg.lower_texture or cfg.wall_texture,
                upper_texture=cfg.upper_texture or cfg.wall_texture
            )
            
            idx = editor.add_sector_from_polygon(polygon, sector_config, wall_config)
            room_sectors[name] = idx
            
            # Apply damage floor special
            if room_info.damage_config:
                apply_damage_to_sector(editor, idx, DamageFloorConfig(
                    damage_type=room_info.damage_config.damage_type
                ))
            
            # Apply lighting effect
            if room_info.light_config:
                apply_light_effect(editor, idx, LightConfig(
                    effect=room_info.light_config.effect,
                    light_level=room_info.light_config.light_level
                ))
        
        # Add corridors
        for corridor in result.corridors:
            key = (corridor.room_a, corridor.room_b)
            cfg = self._corridor_configs.get(key, self._default_corridor_config)
            sector_config = SectorConfig(
                floor_height=cfg.floor_height,
                ceiling_height=cfg.ceiling_height,
                floor_texture=cfg.floor_texture,
                ceiling_texture=cfg.ceiling_texture,
                light_level=cfg.light_level
            )
            wall_config = WallConfig(middle_texture=cfg.wall_texture)
            editor.add_sector_from_polygon(corridor.polygon, sector_config, wall_config)
        
        # Process prefabs
        for prefab in self._prefabs:
            if prefab.prefab_type == "door":
                self._apply_door_prefab(editor, prefab, result)
            elif prefab.prefab_type == "corridor_door":
                self._apply_corridor_door_prefab(editor, prefab, result)
            elif prefab.prefab_type == "lift":
                self._apply_lift_prefab(editor, prefab, result)
            elif prefab.prefab_type == "crusher":
                self._apply_crusher_prefab(editor, prefab, result)
            elif prefab.prefab_type == "stairs":
                self._apply_stairs_prefab(editor, prefab, room_sectors)
        
        # Add things
        for room_info in self._rooms.values():
            for thing in room_info.things:
                editor.add_thing(
                    x=thing["x"],
                    y=thing["y"],
                    thing_type=thing["type"],
                    angle=thing["angle"],
                    check_geometry=False
                )
        
        # Compile and embed ACS scripts if any
        has_acs = False
        if self._acs_builder is not None:
            try:
                behavior = self._acs_builder.compile()
                if behavior:
                    map_data.behavior = behavior
                    map_data.scripts = self._acs_builder.to_code()
                    has_acs = True
                    print("ACS compiled and embedded successfully!")
            except FileNotFoundError:
                print("ACC compiler not found. ACS scripts not embedded.")
            
            # Save source file if path specified or alongside WAD
            if self._acs_source_path:
                acs_path = self._acs_source_path
            else:
                acs_path = path.with_suffix('.acs')
            self._acs_builder.save_source(acs_path)
            print(f"ACS source saved to: {acs_path}")
        
        # Save
        wad.save(str(path))
        
        print(f"Created {path}")
        print(f"  Rooms: {len(result.rooms)}")
        print(f"  Corridors: {len(result.corridors)}")
        print(f"  Prefabs: {len(self._prefabs)}")
        if has_acs:
            print(f"  Has ACS: Yes")
        
        return path
    
    def _apply_door_prefab(self, editor: MapEditor, prefab: PrefabInfo, result: BuildResult) -> None:
        """Apply a door prefab to the map."""
        cfg: DoomDoorConfig = prefab.config
        
        # Find the matching slot
        for slot in result.slots:
            if slot.slot_type == SlotType.DOOR and self._positions_match(slot.position, prefab.position):
                door_sector_config = SectorConfig(
                    floor_height=0,
                    ceiling_height=0,  # Closed door
                    floor_texture="FLOOR4_8",
                    ceiling_texture="CEIL3_5",
                    light_level=160
                )
                
                idx = editor.add_sector_from_polygon(
                    slot.polygon,
                    door_sector_config,
                    WallConfig(middle_texture=cfg.wall_texture)
                )
                
                # Determine door type from key_type
                door_type = cfg.door_type
                if cfg.key_type == "blue":
                    door_type = DoorType.KEY_BLUE
                elif cfg.key_type == "red":
                    door_type = DoorType.KEY_RED
                elif cfg.key_type == "yellow":
                    door_type = DoorType.KEY_YELLOW
                
                apply_door_to_sector(editor, idx, DoorConfig(door_type=door_type))
                break
    
    def _apply_corridor_door_prefab(self, editor: MapEditor, prefab: PrefabInfo, result: BuildResult) -> None:
        """Apply a corridor door prefab to the map."""
        cfg: DoomDoorConfig = prefab.config
        corridor_name = prefab.room_name  # Stored corridor name
        end = prefab.room_b_name  # Stored which end ("a" or "b")
        
        # Find the matching corridor slot
        for slot in result.slots:
            if (slot.slot_type == SlotType.DOOR and 
                slot.metadata.get("corridor_slot") and
                slot.metadata.get("corridor") == corridor_name and
                slot.metadata.get("end") == end):
                
                door_sector_config = SectorConfig(
                    floor_height=0,
                    ceiling_height=0,  # Closed door
                    floor_texture="FLOOR4_8",
                    ceiling_texture="CEIL3_5",
                    light_level=160
                )
                
                idx = editor.add_sector_from_polygon(
                    slot.polygon,
                    door_sector_config,
                    WallConfig(middle_texture=cfg.wall_texture)
                )
                
                # Determine door type from key_type
                door_type = cfg.door_type
                if cfg.key_type == "blue":
                    door_type = DoorType.KEY_BLUE
                elif cfg.key_type == "red":
                    door_type = DoorType.KEY_RED
                elif cfg.key_type == "yellow":
                    door_type = DoorType.KEY_YELLOW
                
                # Apply door with tag for ACS control
                from doomgen.prefabs.door import DoorPrefab
                door_prefab = DoorPrefab(DoorConfig(door_type=door_type))
                door_prefab.apply_to_map(editor, idx, tag=prefab.tag or 0)
                break
    
    def _apply_lift_prefab(self, editor: MapEditor, prefab: PrefabInfo, result: BuildResult) -> None:
        """Apply a lift prefab to the map."""
        cfg: DoomLiftConfig = prefab.config
        
        # Find the matching slot
        for slot in result.slots:
            if slot.slot_type == SlotType.LIFT and self._positions_match(slot.position, prefab.position):
                # Lift floor starts at upper height and lowers to lower height
                lift_sector_config = SectorConfig(
                    floor_height=cfg.upper_height,
                    ceiling_height=cfg.upper_height + 128,
                    floor_texture=cfg.floor_texture,
                    ceiling_texture="CEIL3_5",
                    light_level=160
                )
                
                idx = editor.add_sector_from_polygon(
                    slot.polygon,
                    lift_sector_config,
                    WallConfig(
                        middle_texture=cfg.wall_texture,
                        lower_texture=cfg.wall_texture
                    )
                )
                
                # Get lift action based on type
                action_map = {
                    LiftType.STANDARD: LiftAction.WR_LIFT,
                    LiftType.FAST: LiftAction.WR_LIFT_FAST,
                    LiftType.PERPETUAL: LiftAction.SR_PERPETUAL_RAISE,
                }
                action = action_map.get(cfg.lift_type, LiftAction.WR_LIFT)
                
                apply_lift_to_sector(editor, idx, prefab.tag, action)
                break
    
    def _apply_crusher_prefab(self, editor: MapEditor, prefab: PrefabInfo, result: BuildResult) -> None:
        """Apply a crusher prefab to the map."""
        cfg: DoomCrusherConfig = prefab.config
        
        # Find the matching slot
        for slot in result.slots:
            if slot.slot_type == SlotType.CRUSHER and self._positions_match(slot.position, prefab.position):
                crusher_sector_config = SectorConfig(
                    floor_height=0,
                    ceiling_height=128,
                    floor_texture=cfg.floor_texture,
                    ceiling_texture=cfg.ceiling_texture,
                    light_level=144
                )
                
                idx = editor.add_sector_from_polygon(
                    slot.polygon,
                    crusher_sector_config,
                    WallConfig(middle_texture="STARTAN2")
                )
                
                apply_crusher_to_sector(
                    editor, idx, prefab.tag,
                    CrusherConfig(crusher_type=cfg.crusher_type)
                )
                break
    
    def _apply_stairs_prefab(self, editor: MapEditor, prefab: PrefabInfo, room_sectors: dict[str, int]) -> None:
        """Apply a stairs prefab to the map."""
        cfg: DoomStairConfig = prefab.config
        
        stair_config = StairConfig(
            width=cfg.width,
            step_depth=cfg.step_depth,
            step_height=cfg.step_height,
            num_steps=cfg.num_steps
        )
        
        stair_polys = create_stair_shapes(prefab.position, stair_config, cfg.direction)
        
        base_height = self._rooms[prefab.room_name].config.floor_height
        
        for i, step_poly in enumerate(stair_polys):
            step_height = base_height + (i + 1) * cfg.step_height
            step_config = SectorConfig(
                floor_height=step_height,
                ceiling_height=128 + step_height,
                floor_texture=cfg.floor_texture,
                ceiling_texture="CEIL3_5",
                light_level=192
            )
            editor.add_sector_from_polygon(step_poly, step_config)
    
    def _positions_match(self, pos1: tuple, pos2: tuple) -> bool:
        """Check if two positions are approximately equal."""
        return abs(pos1[0] - pos2[0]) < 1 and abs(pos1[1] - pos2[1]) < 1


# =============================================================================
# Convenience Functions
# =============================================================================

def create_simple_map(
    rooms: list[dict],
    connections: list[tuple[str, str]],
    output_path: str,
    seed: Optional[int] = None
) -> Path:
    """
    Create a simple map from room definitions.
    
    Args:
        rooms: List of room dicts with 'name', 'width', 'height', 'center'.
        connections: List of (room_a, room_b) tuples to connect.
        output_path: Output WAD path.
        seed: Random seed.
    
    Returns:
        Path to the saved WAD file.
    
    Example:
        create_simple_map(
            rooms=[
                {"name": "spawn", "width": 256, "height": 256, "center": (0, 0)},
                {"name": "arena", "width": 512, "height": 512, "center": (500, 0)},
            ],
            connections=[("spawn", "arena")],
            output_path="output/simple.wad"
        )
    """
    builder = DoomMapBuilder(seed=seed)
    
    for room in rooms:
        builder.add_room(**room)
    
    for room_a, room_b in connections:
        builder.connect(room_a, room_b)
    
    if rooms:
        builder.add_player_start(rooms[0]["name"])
    
    return builder.save(output_path)
