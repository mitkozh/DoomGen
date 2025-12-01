"""
CSG-based (Constructive Solid Geometry) map geometry builder.

Pattern: "Local Merge, Global Difference"
- Rooms built from merged shapes (local merge) = one sector
- Corridors/cutouts subtracted (global difference) = separate sectors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

import numpy as np
from numpy.random import Generator
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, nearest_points

from doomgen.geometry.operations import (
    ensure_polygon,
    cut_polygon,
    merge_polygons,
    snap_polygon_to_grid,
)
from doomgen.geometry.modifiers import (
    LSystemGenerator,
    GRAMMARS,
    recursive_subdivision,
    add_noise_to_polygon,
)


# =============================================================================
# Corridor & Cutout Creation (Pure Geometry Helpers)
# =============================================================================

def _calculate_entry_points(
    room_a: Polygon,
    room_b: Polygon,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """
    Calculate closest connection points between two polygons.
    
    Uses shapely.ops.nearest_points for robust handling of irregular shapes
    (U-shaped rooms, L-shaped rooms, etc.) where centroid-based raycasting fails.
    
    Returns:
        Tuple of (entry_a, entry_b, direction_vector) where:
        - entry_a: Point on room_a's boundary closest to room_b
        - entry_b: Point on room_b's boundary closest to room_a  
        - direction_vector: Normalized (nx, ny) from entry_a to entry_b
    """
    # Find the absolute closest points between the two geometries
    # This handles irregular shapes much better than centroid-based raycasting
    pt_a, pt_b = nearest_points(room_a, room_b)
    
    entry_a = (pt_a.x, pt_a.y)
    entry_b = (pt_b.x, pt_b.y)
    
    # Calculate direction vector
    dx = entry_b[0] - entry_a[0]
    dy = entry_b[1] - entry_a[1]
    length = np.sqrt(dx * dx + dy * dy)
    
    # Handle case where rooms are touching or overlapping
    if length < 1e-6:
        # Fallback to centroid logic if they are touching
        ca, cb = room_a.centroid, room_b.centroid
        dx, dy = cb.x - ca.x, cb.y - ca.y
        length = np.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / length, dy / length
    else:
        nx, ny = dx / length, dy / length
        
    return entry_a, entry_b, (nx, ny)


def create_corridor_between(
    room_a: Polygon,
    room_b: Polygon,
    width: float,
    overlap: Optional[float] = None
) -> Polygon:
    """
    Create a corridor polygon that connects two rooms.
    
    The corridor extends from room_a's boundary to room_b's boundary,
    with overlap into each room to ensure proper CSG cutting.
    
    Uses the "Cookie Cutter" approach: corridors penetrate into rooms
    and are then subtracted, guaranteeing clean shared edges.
    
    Args:
        room_a: First room polygon.
        room_b: Second room polygon.
        width: Width of the corridor.
        overlap: How far to extend into each room. If None, uses width
                 as the default for reliable CSG operations.
    
    Returns:
        A corridor polygon suitable for cutting from both rooms.
    """
    # Default overlap to corridor width for reliable CSG operations
    if overlap is None:
        overlap = width
    
    entry_a, entry_b, (nx, ny) = _calculate_entry_points(room_a, room_b)
    
    start = (entry_a[0] - nx * overlap, entry_a[1] - ny * overlap)
    end = (entry_b[0] + nx * overlap, entry_b[1] + ny * overlap)
    
    corridor = LineString([start, end]).buffer(width / 2, cap_style='flat')
    return ensure_polygon(corridor)


def create_cutout_polygon(
    position: tuple[float, float],
    width: float = 64,
    depth: float = 16,
    direction: Union[str, float] = "horizontal"
) -> Polygon:
    """
    Create a rectangular cutout polygon at the specified position.
    
    Useful for doors, lifts, and other rectangular prefab areas.
    
    Args:
        position: Center position (x, y) for the cutout.
        width: Width of the cutout.
        depth: Thickness of the cutout.
        direction: "horizontal", "vertical", or angle in radians.
                   Angle 0 = horizontal (width spans left-right),
                   Angle pi/2 = vertical (width spans up-down).
    
    Returns:
        A Polygon representing the cutout geometry.
    """
    from shapely.affinity import rotate, translate
    
    x, y = position
    
    # Handle string directions for backward compatibility
    if direction == "horizontal":
        angle_rad = 0.0
    elif direction == "vertical":
        angle_rad = np.pi / 2
    elif isinstance(direction, (int, float)):
        angle_rad = float(direction)
    else:
        angle_rad = 0.0
    
    # Create base rectangle (horizontal orientation)
    base_rect = box(-width/2, -depth/2, width/2, depth/2)
    
    # Rotate around origin, then translate to position
    if abs(angle_rad) > 1e-6:
        rotated = rotate(base_rect, np.degrees(angle_rad), origin=(0, 0))
    else:
        rotated = base_rect
    
    return translate(rotated, xoff=x, yoff=y)


# =============================================================================
# Enums for Type Safety
# =============================================================================

class CorridorStyle(Enum):
    """Types of corridors that can be created."""
    STRAIGHT = "straight"  # Direct straight-line corridor
    LSYSTEM = "lsystem"    # L-System procedural corridor
    CUSTOM = "custom"      # User-provided polygon


class SlotType(Enum):
    """Types of prefab slots."""
    GENERIC = "generic"
    DOOR = "door"
    LIFT = "lift"
    CRUSHER = "crusher"
    TELEPORTER = "teleporter"
    STAIRS = "stairs"


# =============================================================================
# Data Classes for Corridor Storage and Build Results
# =============================================================================

@dataclass
class CorridorData:
    """Internal data structure for storing corridor information.
    
    This unified structure replaces the mixed 3-tuple and 7-tuple formats.
    All corridor types (straight, L-system, custom) use this same structure.
    
    The "Cookie Cutter" approach is used: corridors always penetrate into
    rooms and are subtracted via CSG, guaranteeing clean shared edges.
    """
    name: str
    room_a: str
    room_b: str
    polygon: Polygon
    entry_a: tuple[float, float]  # Where corridor meets room_a
    entry_b: tuple[float, float]  # Where corridor meets room_b
    direction_a: float  # Door angle at entry_a (radians, perpendicular to corridor)
    direction_b: float  # Door angle at entry_b (radians, perpendicular to corridor)
    style: CorridorStyle = CorridorStyle.STRAIGHT
    width: float = 64.0
    metadata: dict = field(default_factory=dict)


@dataclass
class CorridorSlotRequest:
    """Request for a prefab slot at a corridor entrance.
    
    Stored during add_slot_at_corridor() and processed during build().
    The corridor will be shortened at this end to make room for the slot.
    """
    corridor_name: str
    end: str  # "a" or "b"
    width: float
    depth: float
    direction: float  # Angle in radians
    slot_type: SlotType = SlotType.GENERIC
    key_type: Optional[str] = None  # For keyed doors: "blue", "red", "yellow"
    metadata: dict = field(default_factory=dict)


@dataclass
class SlotInfo:
    """Information about a prefab slot (door, lift, crusher, etc.).
    
    Slots are rectangular areas cut from rooms where prefab sectors
    (doors, lifts, crushers, etc.) will be placed.
    """
    polygon: Polygon
    room_name: str
    position: tuple[float, float]
    width: float
    depth: float
    direction: Union[str, float]  # "horizontal", "vertical", or angle in radians
    slot_type: SlotType = SlotType.GENERIC
    key_type: Optional[str] = None  # For keyed doors: "blue", "red", "yellow"
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_key_door(self) -> bool:
        """Check if this is a keyed door."""
        return self.key_type is not None


@dataclass
class CorridorInfo:
    """Information about a corridor connecting two rooms (in BuildResult)."""
    polygon: Polygon
    room_a: str
    room_b: str
    name: str = ""
    # Entry/exit points for door placement (always populated now)
    entry_a: Optional[tuple[float, float]] = None  # Where corridor meets room_a
    entry_b: Optional[tuple[float, float]] = None  # Where corridor meets room_b
    # Direction of the corridor at each entry point (for door orientation)
    # These are angles in radians, perpendicular to corridor direction
    direction_a: Optional[float] = None
    direction_b: Optional[float] = None
    style: CorridorStyle = CorridorStyle.STRAIGHT
    width: float = 64.0


@dataclass
class BuildResult:
    """Result of building map geometry.
    
    Contains the final carved room polygons, corridors, and slots
    ready to be converted to Doom sectors.
    
    Attributes:
        rooms: Dictionary mapping room names to carved polygons.
        corridors: List of corridor information (all with entry points).
        slots: List of prefab slot information (doors, lifts, etc.).
        errors: List of any errors encountered during building.
    """
    rooms: dict[str, Polygon] = field(default_factory=dict)
    corridors: list[CorridorInfo] = field(default_factory=list)
    slots: list[SlotInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if the build completed without errors."""
        return len(self.errors) == 0
    
    def get_corridor(self, name: str) -> Optional[CorridorInfo]:
        """Get a corridor by name.
        
        Args:
            name: The corridor name.
            
        Returns:
            CorridorInfo if found, None otherwise.
        """
        for c in self.corridors:
            if c.name == name:
                return c
        return None
    
    def get_slots_by_type(self, slot_type: SlotType) -> list[SlotInfo]:
        """Get all slots of a specific type.
        
        Args:
            slot_type: Type of slots to get (SlotType.DOOR, SlotType.LIFT, etc.)
            
        Returns:
            List of matching SlotInfo objects.
        """
        return [s for s in self.slots if s.slot_type == slot_type]


# =============================================================================
# MapBuilder - Pure Geometry CSG Builder
# =============================================================================

class MapBuilder:
    """
    CSG-based map geometry builder.
    
    Manages rooms, corridors, and cutouts. Pure geometry - no Doom knowledge.
    Use with MapEditor to convert to Doom structures.
    
    Example:
        builder = MapBuilder()
        
        # Add rooms
        builder.add_room("hub", create_rectangle(512, 512))
        builder.add_room("arena", create_rectangle(256, 256, center=(600, 0)))
        
        # Add corridor connection (now supports doors on any corridor type)
        builder.add_corridor("hub", "arena", width=64, name="main_corridor")
        
        # Add door at corridor entrance (works for ALL corridor types now)
        builder.add_corridor_door("main_corridor", end="a")
        
        # Or use L-system corridor for procedural paths
        builder.add_corridor("hub", "arena", width=64, style="lsystem:organic")
        
        # Build final geometry
        result = builder.build()
        
        # Query corridor info
        corridor = result.get_corridor("main_corridor")
        print(f"Entry points: {corridor.entry_a} -> {corridor.entry_b}")
    """
    
    def __init__(self, grid_size: int = 8, seed: Optional[int] = None, rng: Optional[Generator] = None):
        """
        Initialize the map builder.
        
        Args:
            grid_size: Grid size for snapping (default 8).
            seed: Random seed for procedural modifiers.
            rng: Existing NumPy generator (takes precedence over seed).
        """
        self.grid_size = grid_size
        self._rooms: dict[str, Polygon] = {}
        
        # Unified corridor storage - all corridor types use CorridorData
        self._corridors: dict[str, CorridorData] = {}
        self._corridor_order: list[str] = []  # Preserve insertion order
        
        # Corridor slot requests - processed during build() to shorten corridors
        self._corridor_slots: list[CorridorSlotRequest] = []
        
        self._slots: list[SlotInfo] = []
        self._raw_slots: list[tuple[str, Polygon]] = []  # For add_slot_between's second room
        
        # Counter for auto-generating corridor names
        self._corridor_counter = 0
        
        # Random generator for procedural modifiers
        if rng is not None:
            self._rng = rng
        elif seed is not None:
            self._rng = np.random.default_rng(seed)
        else:
            self._rng = np.random.default_rng()
    
    def _generate_corridor_name(self, room_a: str, room_b: str) -> str:
        """Generate a unique corridor name."""
        self._corridor_counter += 1
        return f"corridor_{room_a}_{room_b}_{self._corridor_counter}"
    
    # =========================================================================
    # Room Management
    # =========================================================================
    
    def add_room(self, name: str, polygon: Polygon) -> "MapBuilder":
        """
        Add a room to the map.
        
        Args:
            name: Unique identifier for the room.
            polygon: The room polygon.
        
        Returns:
            Self for chaining.
        """
        self._rooms[name] = ensure_polygon(polygon)
        return self
    
    def add_merged_room(self, name: str, *polygons: Polygon) -> "MapBuilder":
        """
        Add a room created by merging multiple polygons.
        
        Use for complex room shapes like L-shaped rooms.
        
        Args:
            name: Unique identifier for the room.
            *polygons: Polygons to merge into the room.
        
        Returns:
            Self for chaining.
        """
        self._rooms[name] = merge_polygons(*polygons, grid_size=0)
        return self
    
    # =========================================================================
    # Unified Corridor API
    # =========================================================================
    
    def add_corridor(
        self,
        room_a: str,
        room_b: str,
        width: float = 64,
        name: Optional[str] = None,
        style: str = "straight",
        # L-system specific options
        grammar_name: str = "organic",
        iterations: int = 2,
        max_deviation: Optional[float] = 0.25,
        seed: Optional[int] = None,
        # Custom polygon option
        polygon: Optional[Polygon] = None,
        **metadata
    ) -> "MapBuilder":
        """
        Add a corridor connecting two rooms.
        
        This unified method supports all corridor types:
        - "straight": Direct straight-line corridor (default)
        - "lsystem" or "lsystem:<grammar>": L-System procedural corridor
        - "custom": User-provided polygon (requires polygon parameter)
        
        Uses the "Cookie Cutter" approach: corridors penetrate into rooms
        and are subtracted via CSG difference. This guarantees clean shared
        edges regardless of room shape (handles irregular polygons, U-shapes,
        L-system curves, etc.).
        
        All corridor types calculate and store entry points, enabling
        door placement with add_corridor_door().
        
        Args:
            room_a: Name of first room.
            room_b: Name of second room.
            width: Width of the corridor.
            name: Optional name for the corridor (auto-generated if None).
            style: Corridor style - "straight", "lsystem", "lsystem:<grammar>", or "custom".
            grammar_name: L-System grammar (used when style starts with "lsystem").
            iterations: L-System iterations (used when style starts with "lsystem").
            max_deviation: Max deviation for L-System (fraction of distance, 0.0-1.0).
            seed: Random seed for L-System generation.
            polygon: Custom corridor polygon (required when style="custom").
            **metadata: Additional data to store with the corridor.
        
        Returns:
            Self for chaining.
        
        Example:
            # Straight corridor
            builder.add_corridor("hub", "arena", width=64)
            
            # L-System corridor with specific grammar
            builder.add_corridor("hub", "arena", style="lsystem:serpentine", width=64)
            
            # Named corridor for door placement
            builder.add_corridor("hub", "arena", name="main", width=64)
            builder.add_corridor_door("main", end="a")
        """
        if room_a not in self._rooms:
            raise KeyError(f"Room '{room_a}' not found")
        if room_b not in self._rooms:
            raise KeyError(f"Room '{room_b}' not found")
        
        poly_a = self._rooms[room_a]
        poly_b = self._rooms[room_b]
        
        # Generate name if not provided
        corridor_name = name if name else self._generate_corridor_name(room_a, room_b)
        
        # Check for duplicate names
        if corridor_name in self._corridors:
            raise ValueError(f"Corridor '{corridor_name}' already exists")
        
        # Calculate entry points using robust nearest_points algorithm
        entry_a, entry_b, (nx, ny) = _calculate_entry_points(poly_a, poly_b)
        
        # Calculate door angles (perpendicular to corridor direction)
        corridor_angle = np.arctan2(ny, nx)
        door_angle = corridor_angle + np.pi / 2
        
        # Calculate extension depth for cookie cutter approach
        # Extend by at least corridor width to ensure clean CSG cuts
        extension_depth = max(width, 32.0)
        
        # Parse style and create corridor polygon
        style_lower = style.lower()
        if style_lower == "straight":
            corridor_style = CorridorStyle.STRAIGHT
            corridor_poly = self._create_straight_corridor(
                entry_a, entry_b, (nx, ny), width, extension_depth
            )
        elif style_lower.startswith("lsystem"):
            corridor_style = CorridorStyle.LSYSTEM
            # Parse grammar from style string (e.g., "lsystem:serpentine")
            if ":" in style_lower:
                grammar_name = style_lower.split(":", 1)[1]
            corridor_poly = self._create_lsystem_corridor(
                entry_a, entry_b, (nx, ny), width, extension_depth,
                grammar_name, iterations, max_deviation, seed
            )
        elif style_lower == "custom":
            corridor_style = CorridorStyle.CUSTOM
            if polygon is None:
                raise ValueError("Custom corridor style requires 'polygon' parameter")
            corridor_poly = ensure_polygon(polygon)
        else:
            raise ValueError(f"Unknown corridor style: {style}. Use 'straight', 'lsystem', or 'custom'.")
        
        # Store corridor data
        corridor_data = CorridorData(
            name=corridor_name,
            room_a=room_a,
            room_b=room_b,
            polygon=corridor_poly,
            entry_a=entry_a,
            entry_b=entry_b,
            direction_a=door_angle,
            direction_b=door_angle,
            style=corridor_style,
            width=width,
            metadata=metadata
        )
        
        self._corridors[corridor_name] = corridor_data
        self._corridor_order.append(corridor_name)
        
        return self
    
    def _create_straight_corridor(
        self,
        entry_a: tuple[float, float],
        entry_b: tuple[float, float],
        direction: tuple[float, float],
        width: float,
        extension_depth: float
    ) -> Polygon:
        """Create a straight corridor polygon with cookie cutter extensions."""
        nx, ny = direction
        # Extend into both rooms by extension_depth
        start = (entry_a[0] - nx * extension_depth, entry_a[1] - ny * extension_depth)
        end = (entry_b[0] + nx * extension_depth, entry_b[1] + ny * extension_depth)
        corridor = LineString([start, end]).buffer(width / 2, cap_style='flat')
        return ensure_polygon(corridor)
    
    def _create_lsystem_corridor(
        self,
        entry_a: tuple[float, float],
        entry_b: tuple[float, float],
        direction: tuple[float, float],
        width: float,
        extension_depth: float,
        grammar_name: str,
        iterations: int,
        max_deviation: Optional[float],
        seed: Optional[int]
    ) -> Polygon:
        """Create an L-System corridor polygon with cookie cutter extensions."""
        nx, ny = direction
        # Extend into both rooms by extension_depth for reliable CSG cuts
        start = (entry_a[0] - nx * extension_depth, entry_a[1] - ny * extension_depth)
        end = (entry_b[0] + nx * extension_depth, entry_b[1] + ny * extension_depth)
        
        rng = self._rng if seed is None else np.random.default_rng(seed)
        generator = LSystemGenerator(grammar_name=grammar_name, rng=rng)
        corridor = generator.generate_corridor(
            start, end, width, iterations, max_deviation=max_deviation
        )
        return ensure_polygon(corridor)
    
    

    
    def get_corridor(self, name: str) -> Optional[CorridorData]:
        """
        Get corridor data by name (before building).
        
        Args:
            name: The corridor name.
            
        Returns:
            CorridorData if found, None otherwise.
        """
        return self._corridors.get(name)
    
    def list_corridors(self) -> list[str]:
        """
        Get list of all corridor names.
        
        Returns:
            List of corridor names in creation order.
        """
        return list(self._corridor_order)
    
    # =========================================================================
    # Slot Management (Doors, Lifts, Crushers, etc.)
    # =========================================================================
    
    def add_slot(
        self,
        room_name: str,
        position: Optional[Union[tuple[float, float], Polygon]] = None,
        width: float = 64,
        depth: float = 16,
        direction: Union[str, float] = "horizontal",
        slot_type: Union[SlotType, str] = SlotType.GENERIC,
        polygon: Optional[Polygon] = None,
        key_type: Optional[str] = None,
        **metadata
    ) -> "MapBuilder":
        """
        Add a slot (door, lift, crusher, etc.) to a room.
        
        The slot will be subtracted from the room, creating a hole
        where a separate sector (for the prefab) will be placed.
        
        Args:
            room_name: Room to cut from.
            position: Center position (x, y) for the slot, or a Polygon.
            width: Width of the slot.
            depth: Thickness of the slot.
            direction: "horizontal", "vertical", or angle in radians.
            slot_type: Type identifier (SlotType.DOOR, SlotType.LIFT, etc.)
            polygon: Optional pre-made polygon (overrides position/width/depth).
            key_type: Key type for keyed doors ("blue", "red", "yellow").
            **metadata: Additional data to store with the slot.
        
        Returns:
            Self for chaining.
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        # Convert string to SlotType enum
        if isinstance(slot_type, str):
            slot_type = SlotType(slot_type) if slot_type in [e.value for e in SlotType] else SlotType.GENERIC
        
        # Handle position being a Polygon (legacy API support)
        if isinstance(position, Polygon):
            polygon = position
            position = None
        
        if polygon is not None:
            poly = ensure_polygon(polygon)
            centroid = poly.centroid
            position = (centroid.x, centroid.y)
            bounds = poly.bounds
            width = bounds[2] - bounds[0]
            depth = bounds[3] - bounds[1]
        else:
            if position is None:
                raise ValueError("Either position or polygon must be provided")
            poly = create_cutout_polygon(position, width, depth, direction)
        
        self._slots.append(SlotInfo(
            polygon=poly,
            room_name=room_name,
            position=position,
            width=width,
            depth=depth,
            direction=direction,
            slot_type=slot_type,
            key_type=key_type,
            metadata=metadata
        ))
        return self
    
    def add_slot_between(
        self,
        room_a: str,
        room_b: str,
        position: Optional[tuple[float, float]] = None,
        width: float = 64,
        depth: float = 16,
        direction: Union[str, float] = "horizontal",
        slot_type: Union[SlotType, str] = SlotType.GENERIC,
        polygon: Optional[Polygon] = None,
        key_type: Optional[str] = None,
        auto_position: bool = True,
        **metadata
    ) -> "MapBuilder":
        """
        Add a slot between two adjacent rooms.
        
        The slot will be cut from both rooms.
        
        Args:
            room_a: First room.
            room_b: Second room.
            position: Center position for the slot (auto-calculated if None).
            width: Width of the slot.
            depth: Thickness of the slot.
            direction: "horizontal", "vertical", "auto", or angle in radians.
            slot_type: Type identifier (SlotType.DOOR, SlotType.LIFT, etc.)
            polygon: Optional pre-made polygon (overrides position/width/depth).
            key_type: Key type for keyed doors ("blue", "red", "yellow").
            auto_position: If True and position is None, auto-calculate midpoint.
            **metadata: Additional data.
        
        Returns:
            Self for chaining.
        """
        if room_a not in self._rooms:
            raise KeyError(f"Room '{room_a}' not found")
        if room_b not in self._rooms:
            raise KeyError(f"Room '{room_b}' not found")
        
        # Convert string to SlotType enum
        if isinstance(slot_type, str):
            slot_type = SlotType(slot_type) if slot_type in [e.value for e in SlotType] else SlotType.GENERIC
        
        poly_a = self._rooms[room_a]
        poly_b = self._rooms[room_b]
        
        # Auto-calculate position if not provided
        if position is None and polygon is None and auto_position:
            entry_a, entry_b, (nx, ny) = _calculate_entry_points(poly_a, poly_b)
            position = ((entry_a[0] + entry_b[0]) / 2, (entry_a[1] + entry_b[1]) / 2)
            
            # Auto-detect direction
            if direction == "auto":
                if abs(nx) > abs(ny):
                    direction = "vertical"  # Corridor is mostly horizontal, door is vertical
                else:
                    direction = "horizontal"  # Corridor is mostly vertical, door is horizontal
        
        if direction == "auto":
            direction = "horizontal"
        
        if polygon is not None:
            poly = ensure_polygon(polygon)
            centroid = poly.centroid
            position = (centroid.x, centroid.y)
            bounds = poly.bounds
            width = bounds[2] - bounds[0]
            depth = bounds[3] - bounds[1]
        else:
            if position is None:
                raise ValueError("Either position or polygon must be provided")
            poly = create_cutout_polygon(position, width, depth, direction)
        
        # Add as slot from first room
        self._slots.append(SlotInfo(
            polygon=poly,
            room_name=room_a,
            position=position,
            width=width,
            depth=depth,
            direction=direction,
            slot_type=slot_type,
            key_type=key_type,
            metadata=metadata
        ))
        
        # Also cut from second room
        self._raw_slots.append((room_b, poly))
        
        return self
    
    # =========================================================================
    # Corridor Door Placement (Now works for ALL corridor types)
    # =========================================================================
    
    def add_slot_at_corridor(
        self,
        corridor_name: str,
        end: str = "a",
        width: Optional[float] = None,
        depth: float = 16,
        slot_type: Union[str, SlotType] = SlotType.GENERIC,
        key_type: Optional[str] = None,
        **metadata
    ) -> "MapBuilder":
        """
        Add a prefab slot at the entrance of a corridor.
        
        Works for ALL corridor types (straight, L-system, custom).
        The corridor will be shortened at this end during build() to make
        room for the slot. This creates clean geometry where:
        - The room connects to the slot
        - The slot connects to the (shortened) corridor
        - No overlapping geometry
        
        Args:
            corridor_name: Name of the corridor.
            end: Which end to place the slot - "a" for room_a entrance, "b" for room_b.
            width: Width of the slot (defaults to corridor width if not specified).
            depth: Thickness of the slot.
            slot_type: Type identifier ("door", "lift", "crusher", etc.).
            key_type: Key type for keyed doors ("blue", "red", "yellow").
            **metadata: Additional data to store with the slot (e.g., tag for ACS).
        
        Returns:
            Self for chaining.
        
        Example:
            # Add a door at corridor entrance
            builder.add_slot_at_corridor("main", end="a", slot_type="door")
            
            # Add a lift at corridor entrance  
            builder.add_slot_at_corridor("main", end="b", slot_type="lift", depth=64)
            
            # Works with L-system corridors too
            builder.add_slot_at_corridor("winding", end="a", slot_type="door")
        """
        if corridor_name not in self._corridors:
            raise KeyError(f"Corridor '{corridor_name}' not found. Available: {self.list_corridors()}")
        
        corridor = self._corridors[corridor_name]
        
        if end not in ("a", "b"):
            raise ValueError(f"end must be 'a' or 'b', got '{end}'")
        
        # Default width to corridor width
        if width is None:
            width = corridor.width
        
        # Get slot direction (perpendicular to corridor)
        direction = corridor.direction_a if end == "a" else corridor.direction_b
        
        # Convert string slot_type to SlotType enum
        if isinstance(slot_type, str):
            slot_type_enum = SlotType(slot_type) if slot_type in [e.value for e in SlotType] else SlotType.GENERIC
        else:
            slot_type_enum = slot_type
        
        # Store the slot request - will be processed during build()
        self._corridor_slots.append(CorridorSlotRequest(
            corridor_name=corridor_name,
            end=end,
            width=width,
            depth=depth,
            direction=direction,
            slot_type=slot_type_enum,
            key_type=key_type,
            metadata={**metadata, "corridor": corridor_name, "end": end}
        ))
        
        return self
    
    def add_corridor_door(
        self,
        corridor_name: str,
        end: str = "a",
        width: Optional[float] = None,
        depth: float = 16,
        key_type: Optional[str] = None,
        **metadata
    ) -> "MapBuilder":
        """
        Add a door at the entrance of a corridor.
        
        This is a convenience wrapper for add_slot_at_corridor with slot_type="door".
        Works for ALL corridor types (straight, L-system, custom).
        
        Args:
            corridor_name: Name of the corridor.
            end: Which end to place the door - "a" for room_a entrance, "b" for room_b.
            width: Width of the door (defaults to corridor width if not specified).
            depth: Thickness of the door.
            key_type: Key type for keyed doors ("blue", "red", "yellow").
            **metadata: Additional data to store with the slot (e.g., tag for ACS).
        
        Returns:
            Self for chaining.
        
        Example:
            # Works with any corridor type
            builder.add_corridor("hub", "arena", name="main", width=64)
            builder.add_corridor_door("main", end="a")  # Door at hub entrance
            builder.add_corridor_door("main", end="b")  # Door at arena entrance
            
            # Also works with L-system corridors
            builder.add_corridor("hub", "arena", name="winding", style="lsystem:serpentine")
            builder.add_corridor_door("winding", end="a")
        """
        return self.add_slot_at_corridor(
            corridor_name=corridor_name,
            end=end,
            width=width,
            depth=depth,
            slot_type=SlotType.DOOR,
            key_type=key_type,
            **metadata
        )
    
    def add_corridor_doors(
        self,
        corridor_name: str,
        width: Optional[float] = None,
        depth: float = 16,
        key_type_a: Optional[str] = None,
        key_type_b: Optional[str] = None,
        **metadata
    ) -> "MapBuilder":
        """
        Add doors at both entrances of a corridor.
        
        Convenience method that calls add_corridor_door for both ends.
        Works for ALL corridor types.
        
        Args:
            corridor_name: Name of the corridor.
            width: Width of both doors (defaults to corridor width).
            depth: Thickness of both doors.
            key_type_a: Key type for door at room_a entrance.
            key_type_b: Key type for door at room_b entrance.
            **metadata: Additional data (e.g., tag_a, tag_b for ACS control).
        
        Returns:
            Self for chaining.
        
        Example:
            builder.add_corridor("hub", "arena", name="main", width=64)
            builder.add_corridor_doors("main", key_type_a="blue")
        """
        # Extract per-door metadata
        meta_a = {k[:-2]: v for k, v in metadata.items() if k.endswith('_a')}
        meta_b = {k[:-2]: v for k, v in metadata.items() if k.endswith('_b')}
        # Also include common metadata
        common = {k: v for k, v in metadata.items() if not k.endswith('_a') and not k.endswith('_b')}
        
        self.add_corridor_door(corridor_name, end="a", width=width, depth=depth, 
                               key_type=key_type_a, **{**common, **meta_a})
        self.add_corridor_door(corridor_name, end="b", width=width, depth=depth,
                               key_type=key_type_b, **{**common, **meta_b})
        return self
    
    # =========================================================================
    # Procedural Modifiers
    # =========================================================================
    
    def subdivide_room(
        self,
        room_name: str,
        iterations: int = 2,
        roughness: float = 0.3,
        seed: Optional[int] = None
    ) -> "MapBuilder":
        """
        Apply recursive subdivision to a room's edges.
        
        This creates a fractal-like perturbation of edges, useful for
        creating organic or ruined-looking room shapes.
        
        Args:
            room_name: Name of the room to modify.
            iterations: Number of subdivision iterations (each doubles vertex count).
            roughness: Displacement magnitude as fraction of edge length (0.0 to 1.0).
            seed: Random seed for reproducibility.
        
        Returns:
            Self for chaining.
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        rng = self._rng if seed is None else np.random.default_rng(seed)
        self._rooms[room_name] = recursive_subdivision(
            self._rooms[room_name],
            iterations=iterations,
            roughness=roughness,
            rng=rng
        )
        return self
    
    def add_noise_to_room(
        self,
        room_name: str,
        noise_scale: float = 10.0,
        seed: Optional[int] = None
    ) -> "MapBuilder":
        """
        Add random noise to a room's vertices.
        
        Unlike subdivide_room, this doesn't add new vertices,
        just displaces existing ones.
        
        Args:
            room_name: Name of the room to modify.
            noise_scale: Maximum displacement in map units.
            seed: Random seed for reproducibility.
        
        Returns:
            Self for chaining.
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        rng = self._rng if seed is None else np.random.default_rng(seed)
        self._rooms[room_name] = add_noise_to_polygon(
            self._rooms[room_name],
            noise_scale=noise_scale,
            rng=rng
        )
        return self
    
    def apply_modifier(
        self,
        room_name: str,
        modifier_fn,
        *args,
        **kwargs
    ) -> "MapBuilder":
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
        """
        if room_name not in self._rooms:
            raise KeyError(f"Room '{room_name}' not found")
        
        self._rooms[room_name] = ensure_polygon(
            modifier_fn(self._rooms[room_name], *args, **kwargs)
        )
        return self
    
    # =========================================================================
    # Build
    # =========================================================================
    
    def build(self) -> BuildResult:
        """
        Build the final geometry using the Cookie Cutter approach.
        
        Performs CSG operations using "Penetration and Subtraction":
        1. Corridors are generated to penetrate into rooms
        2. Corridors are subtracted from rooms via CSG difference
        3. This guarantees clean shared edges regardless of room shape
        4. Slots (doors, lifts) are cut from rooms and/or corridors
        5. Everything is snapped to grid
        
        This approach handles irregular polygons, U-shaped rooms, and
        L-system corridors reliably without fragile edge-alignment logic.
        
        Returns:
            BuildResult with carved rooms, corridors (with entry points), and slots.
        """
        result = BuildResult()
        carved = {name: poly for name, poly in self._rooms.items()}
        final_corridors: list[CorridorInfo] = []
        generated_slots: list[SlotInfo] = []
        
        # Group corridor slot requests by corridor
        slots_by_corridor: dict[str, dict[str, CorridorSlotRequest]] = {}
        for slot_req in self._corridor_slots:
            if slot_req.corridor_name not in slots_by_corridor:
                slots_by_corridor[slot_req.corridor_name] = {}
            slots_by_corridor[slot_req.corridor_name][slot_req.end] = slot_req
        
        # Process all corridors using Cookie Cutter approach
        for corridor_name in self._corridor_order:
            data = self._corridors[corridor_name]
            slot_requests = slots_by_corridor.get(corridor_name, {})
            
            try:
                # Calculate corridor direction vector
                dx = data.entry_b[0] - data.entry_a[0]
                dy = data.entry_b[1] - data.entry_a[1]
                dist = np.sqrt(dx * dx + dy * dy)
                
                if dist > 0:
                    nx, ny = dx / dist, dy / dist
                else:
                    nx, ny = 1.0, 0.0
                
                # Use the pre-generated corridor polygon (already has extension)
                corridor_poly = data.polygon
                
                # Handle doors/slots at corridor entrances
                shorten_a = slot_requests["a"].depth if "a" in slot_requests else 0
                shorten_b = slot_requests["b"].depth if "b" in slot_requests else 0
                
                # For straight corridors with slots, recreate shortened corridor
                if (shorten_a > 0 or shorten_b > 0) and data.style == CorridorStyle.STRAIGHT:
                    extension_depth = max(data.width, 32.0)
                    new_start = (
                        data.entry_a[0] - nx * extension_depth + nx * shorten_a,
                        data.entry_a[1] - ny * extension_depth + ny * shorten_a
                    )
                    new_end = (
                        data.entry_b[0] + nx * extension_depth - nx * shorten_b,
                        data.entry_b[1] + ny * extension_depth - ny * shorten_b
                    )
                    corridor_poly = LineString([new_start, new_end]).buffer(
                        data.width / 2, cap_style='flat'
                    )
                    corridor_poly = ensure_polygon(corridor_poly)
                
                # Create slot polygons at each end where requested
                # NOTE: Slots are NOT cut from the corridor - only from rooms.
                # The door fills the gap between corridor and room.
                for end, slot_req in slot_requests.items():
                    if end == "a":
                        entry_point = data.entry_a
                        target_room = data.room_a
                        # Slot is placed at entry point, extending into the corridor direction
                        slot_center = (
                            entry_point[0] + nx * (slot_req.depth / 2),
                            entry_point[1] + ny * (slot_req.depth / 2)
                        )
                    else:
                        entry_point = data.entry_b
                        target_room = data.room_b
                        slot_center = (
                            entry_point[0] - nx * (slot_req.depth / 2),
                            entry_point[1] - ny * (slot_req.depth / 2)
                        )
                    
                    slot_poly = create_cutout_polygon(
                        slot_center, slot_req.width, slot_req.depth, slot_req.direction
                    )
                    
                    generated_slots.append(SlotInfo(
                        polygon=slot_poly,
                        room_name=target_room,
                        position=slot_center,
                        width=slot_req.width,
                        depth=slot_req.depth,
                        direction=slot_req.direction,
                        slot_type=slot_req.slot_type,
                        key_type=slot_req.key_type,
                        metadata={**slot_req.metadata, "corridor_slot": True}
                    ))
                
                # CRITICAL STEP: The Cookie Cut
                # 1. Trim the corridor by subtracting ORIGINAL room polygons.
                #    The corridor should only occupy the "void" between rooms.
                # 2. Use convex hull to fill concave boundaries (V-shapes).
                # 3. Carve the rooms by subtracting the TRIMMED corridor.
                #    This ensures room boundaries exactly match corridor edges.
                
                # Get original room polygons for trimming
                original_room_a = self._rooms[data.room_a]
                original_room_b = self._rooms[data.room_b]
                
                try:
                    # Step 1: Trim the corridor to remove overlap with rooms
                    trimmed_corridor = corridor_poly
                    if trimmed_corridor.intersects(original_room_a):
                        trimmed_corridor = trimmed_corridor.difference(original_room_a)
                    if trimmed_corridor.intersects(original_room_b):
                        trimmed_corridor = trimmed_corridor.difference(original_room_b)
                    
                    # Handle MultiPolygon result (take largest piece)
                    trimmed_corridor = ensure_polygon(trimmed_corridor)
                    
                    # Step 2: Use convex hull to properly fill V-shaped connections
                    # When a room has a concave boundary (V-shape) at the corridor
                    # junction, the trimmed corridor may have a weird shape. The
                    # convex hull ensures we fill the entire connection area.
                    trimmed_corridor = trimmed_corridor.convex_hull
                    trimmed_corridor = ensure_polygon(trimmed_corridor)
                    
                    corridor_poly = trimmed_corridor
                    
                    # Step 3: Carve rooms by subtracting the TRIMMED corridor
                    # This creates clean shared edges at the corridor boundaries
                    if carved[data.room_a].intersects(corridor_poly):
                        carved[data.room_a] = cut_polygon(
                            carved[data.room_a], corridor_poly, grid_size=0
                        )
                    
                    if carved[data.room_b].intersects(corridor_poly):
                        carved[data.room_b] = cut_polygon(
                            carved[data.room_b], corridor_poly, grid_size=0
                        )
                    
                except Exception as cut_error:
                    # Fallback: buffer corridor slightly to fix vertex precision issues
                    try:
                        safe_cutter = corridor_poly.buffer(-0.01)
                        if not safe_cutter.is_empty:
                            carved[data.room_a] = cut_polygon(
                                carved[data.room_a], safe_cutter, grid_size=0
                            )
                            carved[data.room_b] = cut_polygon(
                                carved[data.room_b], safe_cutter, grid_size=0
                            )
                    except Exception:
                        result.errors.append(
                            f"Corridor {corridor_name}: CSG cut failed: {cut_error}"
                        )
                
                # Store corridor result (now trimmed)
                final_corridors.append(CorridorInfo(
                    polygon=corridor_poly,
                    room_a=data.room_a,
                    room_b=data.room_b,
                    name=data.name,
                    entry_a=data.entry_a,
                    entry_b=data.entry_b,
                    direction_a=data.direction_a,
                    direction_b=data.direction_b,
                    style=data.style,
                    width=data.width
                ))
                
            except Exception as e:
                result.errors.append(
                    f"Corridor {corridor_name} ({data.room_a}-{data.room_b}): {e}"
                )
        
        # Cut generated corridor slots from rooms
        for slot in generated_slots:
            try:
                if carved[slot.room_name].intersects(slot.polygon):
                    carved[slot.room_name] = cut_polygon(
                        carved[slot.room_name], slot.polygon, grid_size=0
                    )
            except Exception as e:
                result.errors.append(f"Corridor slot in {slot.room_name}: {e}")
        
        # Process regular slots (not corridor slots)
        for slot in self._slots:
            try:
                carved[slot.room_name] = cut_polygon(
                    carved[slot.room_name], slot.polygon, grid_size=0
                )
            except Exception as e:
                result.errors.append(f"Slot in {slot.room_name}: {e}")
        
        # Process raw slots (from add_slot_between's second room)
        for room_name, slot_poly in self._raw_slots:
            try:
                carved[room_name] = cut_polygon(carved[room_name], slot_poly, grid_size=0)
            except Exception as e:
                result.errors.append(f"Slot in {room_name}: {e}")
        
        # Final validity check and snap to grid
        for name, poly in carved.items():
            if not poly.is_valid:
                poly = poly.buffer(0)  # Fix validity issues
            result.rooms[name] = snap_polygon_to_grid(poly, self.grid_size)
        
        # Snap corridors to grid
        for c in final_corridors:
            c.polygon = snap_polygon_to_grid(c.polygon, self.grid_size)
        result.corridors = final_corridors
        
        # Combine and snap all slots
        all_slots = generated_slots + list(self._slots)
        result.slots = [
            SlotInfo(
                polygon=snap_polygon_to_grid(s.polygon, self.grid_size),
                room_name=s.room_name,
                position=s.position,
                width=s.width,
                depth=s.depth,
                direction=s.direction,
                slot_type=s.slot_type,
                key_type=s.key_type,
                metadata=s.metadata
            )
            for s in all_slots
        ]
        
        return result
