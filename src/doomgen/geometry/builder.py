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
from shapely.ops import unary_union

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
    Calculate entry points where a corridor would connect two rooms.
    
    Returns:
        Tuple of (entry_a, entry_b, direction_vector) where:
        - entry_a: Point on room_a's boundary closest to room_b
        - entry_b: Point on room_b's boundary closest to room_a  
        - direction_vector: Normalized (nx, ny) from entry_a to entry_b
    """
    ca, cb = room_a.centroid, room_b.centroid
    dx, dy = cb.x - ca.x, cb.y - ca.y
    length = np.sqrt(dx * dx + dy * dy)
    
    if length < 1e-6:
        nx, ny = 1.0, 0.0
    else:
        nx, ny = dx / length, dy / length
    
    line_ab = LineString([(ca.x, ca.y), (cb.x, cb.y)])
    
    def get_exit_point(room: Polygon, line: LineString, target: Point) -> tuple[float, float]:
        intersection = line.intersection(room.exterior)
        if intersection.is_empty:
            return room.centroid.x, room.centroid.y
        elif intersection.geom_type == 'MultiPoint':
            closest = min(intersection.geoms, key=lambda p: p.distance(target))
            return closest.x, closest.y
        elif intersection.geom_type == 'Point':
            return intersection.x, intersection.y
        else:
            c = intersection.centroid
            return c.x, c.y
    
    entry_a = get_exit_point(room_a, line_ab, cb)
    entry_b = get_exit_point(room_b, line_ab, ca)
    
    return entry_a, entry_b, (nx, ny)


def create_corridor_between(
    room_a: Polygon,
    room_b: Polygon,
    width: float,
    overlap: float = 16
) -> Polygon:
    """
    Create a corridor polygon that connects two rooms.
    
    The corridor extends from room_a's boundary to room_b's boundary,
    with overlap into each room to ensure proper CSG cutting.
    
    Args:
        room_a: First room polygon.
        room_b: Second room polygon.
        width: Width of the corridor.
        overlap: How far to extend into each room.
    
    Returns:
        A corridor polygon suitable for cutting from both rooms.
    """
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
    overlap: float = 16.0  # How far corridor extends into rooms
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
        overlap: float = 16,
        name: Optional[str] = None,
        style: str = "straight",
        connection_style: str = "abutting",
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
        
        Connection Styles (how corridors connect to rooms):
        - "abutting" (default): Corridor edges align exactly with room boundaries.
          This matches Doom's sector model where adjacent sectors share linedefs.
          Rooms and corridors touch at their edges without overlapping.
        - "overlap": Corridor extends INTO rooms by 'overlap' amount (legacy).
          Use when you need CSG cutting behavior for complex geometry.
        
        All corridor types calculate and store entry points, enabling
        door placement with add_corridor_door().
        
        Args:
            room_a: Name of first room.
            room_b: Name of second room.
            width: Width of the corridor.
            overlap: How far corridor extends into rooms (only used with connection_style="overlap").
            name: Optional name for the corridor (auto-generated if None).
            style: Corridor style - "straight", "lsystem", "lsystem:<grammar>", or "custom".
            connection_style: How corridor connects to rooms - "abutting" (default) or "overlap".
            grammar_name: L-System grammar (used when style starts with "lsystem").
            iterations: L-System iterations (used when style starts with "lsystem").
            max_deviation: Max deviation for L-System (fraction of distance, 0.0-1.0).
            seed: Random seed for L-System generation.
            polygon: Custom corridor polygon (required when style="custom").
            **metadata: Additional data to store with the corridor.
        
        Returns:
            Self for chaining.
        
        Example:
            # Straight corridor with abutting edges (default, Doom-accurate)
            builder.add_corridor("hub", "arena", width=64)
            
            # L-System corridor with specific grammar
            builder.add_corridor("hub", "arena", style="lsystem:serpentine", width=64)
            
            # Legacy overlap mode for complex CSG operations
            builder.add_corridor("hub", "arena", width=64, connection_style="overlap", overlap=16)
            
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
        
        # Validate connection_style
        connection_style_lower = connection_style.lower()
        if connection_style_lower not in ("abutting", "overlap"):
            raise ValueError(f"Unknown connection_style: {connection_style}. Use 'abutting' or 'overlap'.")
        
        # For abutting mode, effective overlap is 0
        effective_overlap = overlap if connection_style_lower == "overlap" else 0.0
        
        # Calculate entry points (used by ALL corridor types)
        entry_a, entry_b, (nx, ny) = _calculate_entry_points(poly_a, poly_b)
        
        # Calculate door angles (perpendicular to corridor direction)
        corridor_angle = np.arctan2(ny, nx)
        door_angle = corridor_angle + np.pi / 2
        
        # Parse style
        style_lower = style.lower()
        if style_lower == "straight":
            corridor_style = CorridorStyle.STRAIGHT
            corridor_poly = self._create_straight_corridor(
                entry_a, entry_b, (nx, ny), width, effective_overlap
            )
        elif style_lower.startswith("lsystem"):
            corridor_style = CorridorStyle.LSYSTEM
            # Parse grammar from style string (e.g., "lsystem:serpentine")
            if ":" in style_lower:
                grammar_name = style_lower.split(":", 1)[1]
            corridor_poly = self._create_lsystem_corridor(
                entry_a, entry_b, (nx, ny), width, effective_overlap,
                grammar_name, iterations, max_deviation, seed
            )
        elif style_lower == "custom":
            corridor_style = CorridorStyle.CUSTOM
            if polygon is None:
                raise ValueError("Custom corridor style requires 'polygon' parameter")
            corridor_poly = ensure_polygon(polygon)
        else:
            raise ValueError(f"Unknown corridor style: {style}. Use 'straight', 'lsystem', or 'custom'.")
        
        # Store corridor data (store original overlap for reference, but effective_overlap was used)
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
            overlap=effective_overlap,  # Store the actual overlap used
            metadata={**metadata, "connection_style": connection_style_lower}
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
        overlap: float
    ) -> Polygon:
        """Create a straight corridor polygon."""
        nx, ny = direction
        start = (entry_a[0] - nx * overlap, entry_a[1] - ny * overlap)
        end = (entry_b[0] + nx * overlap, entry_b[1] + ny * overlap)
        corridor = LineString([start, end]).buffer(width / 2, cap_style='flat')
        return ensure_polygon(corridor)
    
    def _create_lsystem_corridor(
        self,
        entry_a: tuple[float, float],
        entry_b: tuple[float, float],
        direction: tuple[float, float],
        width: float,
        overlap: float,
        grammar_name: str,
        iterations: int,
        max_deviation: Optional[float],
        seed: Optional[int]
    ) -> Polygon:
        """Create an L-System corridor polygon."""
        nx, ny = direction
        start = (entry_a[0] - nx * overlap, entry_a[1] - ny * overlap)
        end = (entry_b[0] + nx * overlap, entry_b[1] + ny * overlap)
        
        rng = self._rng if seed is None else np.random.default_rng(seed)
        generator = LSystemGenerator(grammar_name=grammar_name, rng=rng)
        corridor = generator.generate_corridor(
            start, end, width, iterations, max_deviation=max_deviation
        )
        return ensure_polygon(corridor)
    
    def _create_portal_cut(
        self,
        entry_point: tuple[float, float],
        width: float,
        depth: float,
        direction: tuple[float, float]
    ) -> Polygon:
        """
        Create a portal cut polygon for abutting corridors.
        
        Portal cuts are thin rectangles that extend slightly into a room
        at the corridor entry point. When subtracted from the room, they
        add vertices to the room's boundary that exactly match the
        corridor's edge vertices.
        
        This is essential for Doom's edge-sharing: the MapEditor detects
        shared edges by exact vertex matching. Without portal cuts, room
        edges are long continuous lines that don't match the shorter
        corridor edges.
        
        Args:
            entry_point: Center of the portal on the room boundary.
            width: Width of the corridor (perpendicular to direction).
            depth: How far into the room to cut (typically 1 unit).
            direction: Unit vector pointing INTO the room.
        
        Returns:
            A small rectangular polygon for cutting.
        """
        nx, ny = direction
        # Perpendicular direction for width
        px, py = -ny, nx
        
        # Create rectangle: starts at entry point, extends into room by depth
        # Width spans perpendicular to corridor direction
        half_width = width / 2
        
        # Four corners of the portal cut
        # p1, p2 at entry point (on room boundary)
        # p3, p4 inside room
        p1 = (entry_point[0] + px * half_width, entry_point[1] + py * half_width)
        p2 = (entry_point[0] - px * half_width, entry_point[1] - py * half_width)
        p3 = (entry_point[0] - px * half_width + nx * depth,
              entry_point[1] - py * half_width + ny * depth)
        p4 = (entry_point[0] + px * half_width + nx * depth,
              entry_point[1] + py * half_width + ny * depth)
        
        return Polygon([p1, p2, p3, p4])
    

    
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
        Build the final geometry.
        
        Performs all CSG operations:
        1. Process corridor slot requests (shorten corridors, create slot polygons)
        2. Cut corridors from rooms
        3. Cut prefab slot areas from rooms and corridors
        4. Snap everything to grid
        
        Returns:
            BuildResult with carved rooms, corridors (with entry points), and slots.
        """
        result = BuildResult()
        carved = {name: poly for name, poly in self._rooms.items()}
        corridors = []
        generated_slots: list[SlotInfo] = []
        
        # Group corridor slot requests by corridor
        slots_by_corridor: dict[str, dict[str, CorridorSlotRequest]] = {}
        for slot_req in self._corridor_slots:
            if slot_req.corridor_name not in slots_by_corridor:
                slots_by_corridor[slot_req.corridor_name] = {}
            slots_by_corridor[slot_req.corridor_name][slot_req.end] = slot_req
        
        # Process all corridors (using unified CorridorData)
        for corridor_name in self._corridor_order:
            corridor = self._corridors[corridor_name]
            slot_requests = slots_by_corridor.get(corridor_name, {})
            
            try:
                # Calculate corridor direction
                dx = corridor.entry_b[0] - corridor.entry_a[0]
                dy = corridor.entry_b[1] - corridor.entry_a[1]
                length = np.sqrt(dx * dx + dy * dy)
                if length > 0:
                    nx, ny = dx / length, dy / length
                else:
                    nx, ny = 1.0, 0.0
                
                # Get connection style for this corridor
                connection_style = corridor.metadata.get("connection_style", "abutting")
                
                # Determine how much to shorten each end
                shorten_a = slot_requests["a"].depth if "a" in slot_requests else 0
                shorten_b = slot_requests["b"].depth if "b" in slot_requests else 0
                
                # Create the (possibly shortened) corridor polygon
                if shorten_a > 0 or shorten_b > 0:
                    if corridor.style == CorridorStyle.STRAIGHT:
                        # For straight corridors: recreate with adjusted endpoints
                        # For abutting mode, corridor starts at entry points (not overlapped)
                        # For overlap mode, corridor starts at entry - overlap (overlapped)
                        base_start = (
                            corridor.entry_a[0] - nx * corridor.overlap,
                            corridor.entry_a[1] - ny * corridor.overlap
                        )
                        base_end = (
                            corridor.entry_b[0] + nx * corridor.overlap,
                            corridor.entry_b[1] + ny * corridor.overlap
                        )
                        
                        # Adjust for slot shortening (shorten pulls back from room)
                        new_start = (
                            base_start[0] + nx * shorten_a,
                            base_start[1] + ny * shorten_a
                        )
                        new_end = (
                            base_end[0] - nx * shorten_b,
                            base_end[1] - ny * shorten_b
                        )
                        
                        corridor_poly = LineString([new_start, new_end]).buffer(
                            corridor.width / 2, cap_style='flat'
                        )
                        corridor_poly = ensure_polygon(corridor_poly)
                    else:
                        # For L-system/custom: we can't easily shorten complex paths
                        # Instead, keep the full corridor and place slot inside the overlap region
                        # The slot will be cut from both room AND corridor
                        corridor_poly = corridor.polygon
                else:
                    corridor_poly = corridor.polygon
                
                # Create slot polygons at each end where requested
                # For L-system corridors, slots are cut from corridor too
                cut_slots_from_corridor = corridor.style != CorridorStyle.STRAIGHT
                
                for end, slot_req in slot_requests.items():
                    if end == "a":
                        entry_point = corridor.entry_a
                        target_room = corridor.room_a
                    else:
                        entry_point = corridor.entry_b
                        target_room = corridor.room_b
                    
                    # Calculate slot center position based on corridor style and connection style
                    if corridor.style == CorridorStyle.STRAIGHT:
                        # For abutting mode: slot is between room boundary and shortened corridor
                        # Slot center is half slot depth from entry point toward the corridor
                        if connection_style == "abutting":
                            # Slot is at the entry point, spanning into the gap
                            slot_center = (
                                entry_point[0] + nx * (slot_req.depth / 2) if end == "a" else
                                entry_point[0] - nx * (slot_req.depth / 2),
                                entry_point[1] + ny * (slot_req.depth / 2) if end == "a" else
                                entry_point[1] - ny * (slot_req.depth / 2)
                            )
                        else:
                            # For overlap mode: slot fills gap in overlap region
                            slot_center = (
                                entry_point[0] - nx * (corridor.overlap - slot_req.depth / 2) if end == "a" else
                                entry_point[0] + nx * (corridor.overlap - slot_req.depth / 2),
                                entry_point[1] - ny * (corridor.overlap - slot_req.depth / 2) if end == "a" else
                                entry_point[1] + ny * (corridor.overlap - slot_req.depth / 2)
                            )
                    else:
                        # For L-system: place slot at entry point, slightly inside room
                        inward_offset = slot_req.depth / 2 + 4
                        slot_center = (
                            entry_point[0] - nx * inward_offset if end == "a" else
                            entry_point[0] + nx * inward_offset,
                            entry_point[1] - ny * inward_offset if end == "a" else
                            entry_point[1] + ny * inward_offset
                        )
                    
                    slot_poly = create_cutout_polygon(
                        slot_center, slot_req.width, slot_req.depth, slot_req.direction
                    )
                    
                    # For L-system corridors, also cut slot from the corridor itself
                    if cut_slots_from_corridor:
                        corridor_poly = cut_polygon(corridor_poly, slot_poly, grid_size=0)
                    
                    generated_slots.append(SlotInfo(
                        polygon=slot_poly,
                        room_name=target_room,
                        position=slot_center,
                        width=slot_req.width,
                        depth=slot_req.depth,
                        direction=slot_req.direction,
                        slot_type=slot_req.slot_type,
                        key_type=slot_req.key_type,
                        metadata={
                            **slot_req.metadata,
                            "connection_style": connection_style,
                            "corridor_slot": True
                        }
                    ))
                
                # Determine if we need to cut corridor from rooms
                connection_style = corridor.metadata.get("connection_style", "abutting")
                
                if connection_style == "overlap" and corridor.overlap > 0:
                    # Overlap mode: Cut full corridor from both rooms
                    carved[corridor.room_a] = cut_polygon(carved[corridor.room_a], corridor_poly, grid_size=0)
                    carved[corridor.room_b] = cut_polygon(carved[corridor.room_b], corridor_poly, grid_size=0)
                elif connection_style == "abutting":
                    # Abutting mode: Create "portal cuts" at room boundaries
                    # This adds vertices to room edges so they exactly match corridor edges
                    # Without these cuts, room edges are continuous lines that don't match
                    # the shorter corridor edges, preventing proper linedef sharing.
                    #
                    # Portal cuts are thin slivers (1 unit deep) centered at entry points,
                    # spanning the corridor width. They split room edges into segments.
                    portal_depth = 1  # Minimal depth to split the edge
                    
                    # Portal at room_a (entry_a is on room_a's boundary)
                    portal_a = self._create_portal_cut(
                        corridor.entry_a, corridor.width, portal_depth, (nx, ny)
                    )
                    carved[corridor.room_a] = cut_polygon(carved[corridor.room_a], portal_a, grid_size=0)
                    
                    # Portal at room_b (entry_b is on room_b's boundary)
                    portal_b = self._create_portal_cut(
                        corridor.entry_b, corridor.width, portal_depth, (-nx, -ny)
                    )
                    carved[corridor.room_b] = cut_polygon(carved[corridor.room_b], portal_b, grid_size=0)
                
                corridors.append(CorridorInfo(
                    polygon=corridor_poly,
                    room_a=corridor.room_a,
                    room_b=corridor.room_b,
                    name=corridor.name,
                    entry_a=corridor.entry_a,
                    entry_b=corridor.entry_b,
                    direction_a=corridor.direction_a,
                    direction_b=corridor.direction_b,
                    style=corridor.style,
                    width=corridor.width
                ))
            except Exception as e:
                result.errors.append(f"Corridor {corridor_name} ({corridor.room_a}-{corridor.room_b}): {e}")
        
        # Cut generated slots from rooms (only for overlap mode)
        # In abutting mode, corridor slots sit between room and corridor, not overlapping either
        for slot in generated_slots:
            # Skip cutting for abutting corridor slots - they don't overlap rooms
            if slot.metadata.get("corridor_slot") and slot.metadata.get("connection_style") == "abutting":
                continue
            try:
                carved[slot.room_name] = cut_polygon(
                    carved[slot.room_name], slot.polygon, grid_size=0
                )
            except Exception as e:
                result.errors.append(f"Slot in {slot.room_name}: {e}")
        
        # Process regular slots (not corridor slots)
        for slot in self._slots:
            try:
                carved[slot.room_name] = cut_polygon(
                    carved[slot.room_name], slot.polygon, grid_size=0
                )
            except Exception as e:
                result.errors.append(f"Slot in {slot.room_name}: {e}")
        
        # Process raw slots (from add_slot_between's second room)
        for room_name, slot in self._raw_slots:
            try:
                carved[room_name] = cut_polygon(carved[room_name], slot, grid_size=0)
            except Exception as e:
                result.errors.append(f"Slot in {room_name}: {e}")
        
        # Snap everything to grid
        for name, poly in carved.items():
            result.rooms[name] = snap_polygon_to_grid(poly, self.grid_size)
        
        result.corridors = [
            CorridorInfo(
                polygon=snap_polygon_to_grid(c.polygon, self.grid_size),
                room_a=c.room_a,
                room_b=c.room_b,
                name=c.name,
                entry_a=c.entry_a,
                entry_b=c.entry_b,
                direction_a=c.direction_a,
                direction_b=c.direction_b,
                style=c.style,
                width=c.width
            )
            for c in corridors
        ]
        
        # Combine generated slots with regular slots
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
