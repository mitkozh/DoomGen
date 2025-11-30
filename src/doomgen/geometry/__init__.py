# Geometry module
"""
Pure geometry operations for Doom map generation.

This module provides tools for creating and manipulating 2D shapes
that represent Doom map elements (rooms, corridors, doors, etc.).
This module contains NO Doom-specific knowledge - it's pure geometry.

Module Structure
----------------
- **shapes.py**: Shape primitives (ShapeBuilder class)
- **operations.py**: Pure CSG operations (cut, merge, snap)
- **modifiers.py**: Procedural shape modification (L-system, subdivision)
- **builder.py**: MapBuilder for CSG-based map construction

For map building with CSG patterns:

    from doomgen.geometry import MapBuilder, create_rectangle
    
    builder = MapBuilder(seed=42)
    builder.add_room("hub", create_rectangle(512, 512))
    builder.add_room("arena", create_rectangle(256, 256, center=(600, 0)))
    
    # Straight corridor
    builder.add_corridor("hub", "arena", width=64)
    
    # L-system corridor with door support
    builder.add_corridor("hub", "arena", width=64, style="lsystem:serpentine", name="main")
    builder.add_corridor_door("main", end="a")  # Add door at hub entrance
    
    # Apply procedural modifiers
    builder.subdivide_room("hub", iterations=2, roughness=0.2)
    
    result = builder.build()

Shape Creation Functions
------------------------
    create_rectangle(width, height, center=(0,0))
    create_polygon(sides, radius, center=(0,0))
    create_corridor(start, end, width)
    create_irregular_polygon(center, radius, sides=6, irregularity=0.3)

CSG Operations
--------------
    merge_polygons(*polygons)  - Combine shapes into one
    cut_polygon(base, cutter)  - Subtract one shape from another
    snap_to_grid(value, grid_size) - Snap coordinate to grid

Procedural Modifiers (Standalone Functions)
-------------------------------------------
    recursive_subdivision(polygon, iterations, roughness) - Fractal edges
    LSystemGenerator - L-system based path generation
    add_noise_to_polygon(polygon, noise_scale) - Random vertex displacement

Corridor API (MapBuilder)
-------------------------
    builder.add_corridor(room_a, room_b, width, style="straight")
    builder.add_corridor(room_a, room_b, width, style="lsystem:organic", name="main")
    builder.add_corridor(room_a, room_b, style="custom", polygon=my_polygon)
    builder.add_corridor_door(corridor_name, end="a")
    builder.get_corridor(name) - Query corridor data
    builder.list_corridors() - List all corridor names

Procedural Modifiers (MapBuilder Methods)
-----------------------------------------
    builder.subdivide_room(room, iterations, roughness) - Fractal room edges
    builder.add_noise_to_room(room, noise_scale) - Random vertex noise
    builder.apply_modifier(room, fn, *args, **kwargs) - Custom modifier function
"""

from shapely.geometry import Polygon

# Shape primitives
from doomgen.geometry.shapes import ShapeBuilder

# Pure geometry operations
from doomgen.geometry.operations import (
    # Grid snapping
    snap_to_grid,
    snap_polygon_to_grid,
    to_integer_coords,
    # CSG operations
    ensure_polygon,
    cut_polygon,
    merge_polygons,
    buffer_polygon,
    # Shape creation (low-level)
    create_rectangle as _ops_create_rectangle,
    create_corridor_polygon,
    # Utilities
    get_edge_midpoint,
    find_closest_edge,
    polygon_contains_point,
    get_polygon_center,
)

# Procedural modifiers
from doomgen.geometry.modifiers import (
    # L-System
    LSystemGenerator,
    GRAMMARS,
    create_lsystem_corridor,
    # Subdivision
    recursive_subdivision,
    subdivide_edge,
    add_noise_to_polygon,
)

# Map builder (CSG-based geometry orchestration)
from doomgen.geometry.builder import (
    MapBuilder,
    BuildResult,
    SlotInfo,
    SlotType,
    CorridorInfo,
    CorridorData,
    CorridorSlotRequest,
    CorridorStyle,
    create_corridor_between,
    create_cutout_polygon,
)


# =============================================================================
# Standalone shape creation functions
# =============================================================================

def create_irregular_polygon(
    center: tuple[float, float],
    radius: float,
    sides: int = 6,
    irregularity: float = 0.3,
    seed: int | None = None
) -> Polygon:
    """
    Create an irregular polygon suitable for Doom map rooms.
    
    Args:
        center: Center point (x, y) of the polygon.
        radius: Base radius from center to vertices.
        sides: Number of sides (minimum 3, default 6).
        irregularity: How much to vary vertex positions (0.0-0.5).
        seed: Random seed for reproducibility.
    
    Returns:
        A valid Shapely Polygon with integer coordinates.
    """
    builder = ShapeBuilder(seed=seed)
    return builder.create_irregular_polygon(center, radius, sides, irregularity)


def create_rectangle(
    width: float,
    height: float,
    center: tuple[float, float] = (0.0, 0.0),
    rotation: float = 0.0
) -> Polygon:
    """
    Create a rectangle with the specified dimensions.
    
    Args:
        width: Width of the rectangle.
        height: Height of the rectangle.
        center: Center point of the rectangle (x, y).
        rotation: Rotation angle in degrees.
    
    Returns:
        A Shapely Polygon representing the rectangle.
    """
    builder = ShapeBuilder()
    return builder.create_rectangle(width, height, center, rotation)


def create_polygon(
    sides: int,
    radius: float,
    center: tuple[float, float] = (0.0, 0.0),
    rotation: float = 0.0
) -> Polygon:
    """
    Create a regular polygon with the specified number of sides.
    
    Args:
        sides: Number of sides (minimum 3).
        radius: Distance from center to each vertex.
        center: Center point of the polygon (x, y).
        rotation: Rotation angle in degrees.
    
    Returns:
        A Shapely Polygon representing the shape.
    """
    builder = ShapeBuilder()
    return builder.create_polygon(sides, radius, center, rotation)


def create_corridor(
    start: tuple[float, float],
    end: tuple[float, float],
    width: float
) -> Polygon:
    """
    Create a straight corridor between two points.
    
    Args:
        start: Starting point (x, y).
        end: Ending point (x, y).
        width: Width of the corridor.
    
    Returns:
        A Shapely Polygon representing the corridor.
    """
    builder = ShapeBuilder()
    return builder.create_corridor(start, end, width)


__all__ = [
    # Shape creation
    "ShapeBuilder",
    "create_irregular_polygon",
    "create_rectangle",
    "create_polygon",
    "create_corridor",
    
    # Pure operations
    "snap_to_grid",
    "snap_polygon_to_grid",
    "to_integer_coords",
    "ensure_polygon",
    "cut_polygon",
    "merge_polygons",
    "buffer_polygon",
    "create_corridor_polygon",
    "get_edge_midpoint",
    "find_closest_edge",
    "polygon_contains_point",
    "get_polygon_center",
    
    # Procedural modifiers
    "LSystemGenerator",
    "GRAMMARS",
    "create_lsystem_corridor",
    "recursive_subdivision",
    "subdivide_edge",
    "add_noise_to_polygon",
    
    # MapBuilder (CSG-based geometry construction)
    "MapBuilder",
    "BuildResult",
    "SlotInfo",
    "SlotType",
    "CorridorInfo",
    "CorridorData",
    "CorridorSlotRequest",
    "CorridorStyle",
    "create_corridor_between",
    "create_cutout_polygon",
]
