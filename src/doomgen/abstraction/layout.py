"""
Abstract layout representation for the Voronoi-first Doom map generator.
Defines Areas (abstract regions) and their relationships, independent of geometry.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import uuid

class SeedStrategy(Enum):
    """Strategy for generating seeds within an area."""
    GRID = "grid"           # Regular grid (Techbase style)
    POISSON = "poisson"     # Organic distribution (Cave style)
    RANDOM = "random"       # Chaotic
    SINGLE = "single"       # Single point (for small items/pillars)
    STENCIL = "stencil"     # Fixed pattern (for Prefabs)
    PATH = "path"           # Along a path (for Corridors)

@dataclass
class Transform:
    """Position and orientation of an area."""
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0  # Degrees

@dataclass
class AreaConfig:
    """Doom-specific configuration for an area (sector properties)."""
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = "FLOOR4_8"
    ceiling_texture: str = "CEIL3_5"
    wall_texture: str = "STARTAN3"
    lower_texture: Optional[str] = None # Explicit lower texture (overrides logic)
    upper_texture: Optional[str] = None # Explicit upper texture (overrides logic)
    light_level: int = 160
    special: int = 0
    tag: int = 0

class Area:
    """
    An abstract region in the map.
    It defines WHERE it is and HOW it should be filled with seeds.
    """
    def __init__(
        self, 
        name: str, 
        transform: Transform, 
        strategy: SeedStrategy = SeedStrategy.POISSON,
        config: Optional[AreaConfig] = None,
        shape_hint: str = "circle", # circle, rectangle, polygon
        dimensions: Tuple[float, float] = (256, 256), # width, height/radius
        seed_density: float = 1.0, # Multiplier for seed count
        stencil_name: Optional[str] = None, # If strategy is STENCIL
        path_points: Optional[List[Tuple[float, float]]] = None, # If strategy is PATH
        priority: int = 0, # Higher priority seeds displace lower priority seeds
        auto_boundary: bool = False # If True, automatically generates void seeds around the area
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.transform = transform
        self.strategy = strategy
        self.config = config or AreaConfig()
        self.shape_hint = shape_hint
        self.dimensions = dimensions
        self.seed_density = seed_density
        self.stencil_name = stencil_name
        self.path_points = path_points
        self.priority = priority
        self.auto_boundary = auto_boundary
        self.tags: Set[str] = set()

    def add_tag(self, tag: str):
        self.tags.add(tag)

class ConnectionType(Enum):
    OPEN = "open"       # Shared edge, passable (2-sided linedef)
    SOLID = "solid"     # Shared edge, impassable (1-sided linedef / mid-texture)
    DOOR = "door"       # Door mechanism (requires specific handling)
    WINDOW = "window"   # Window (mid-texture, passable or blocking)

@dataclass
class Connection:
    """A logical link between two areas."""
    area_a_id: str
    area_b_id: str
    type: ConnectionType = ConnectionType.OPEN
    properties: Dict[str, Any] = field(default_factory=dict)

class Prefab(Area):
    """
    A specialized Area that uses a fixed stencil.
    """
    def __init__(
        self,
        name: str,
        transform: Transform,
        stencil_name: str,
        dimensions: Tuple[float, float] = (64, 16),
        config: Optional[AreaConfig] = None,
        priority: int = 10 # Prefabs have high priority by default
    ):
        super().__init__(
            name=name,
            transform=transform,
            strategy=SeedStrategy.STENCIL,
            config=config,
            dimensions=dimensions,
            stencil_name=stencil_name,
            priority=priority
        )

class LayoutGraph:
    """
    The high-level graph of the map.
    Manages Areas and their Connections.
    """
    def __init__(self):
        self.areas: Dict[str, Area] = {}
        self.connections: List[Connection] = []

    def add_area(self, area: Area) -> str:
        self.areas[area.id] = area
        return area.id

    def connect(self, id_a: str, id_b: str, type: ConnectionType = ConnectionType.OPEN, **kwargs):
        if id_a not in self.areas or id_b not in self.areas:
            raise ValueError("Area ID not found")
        
        self.connections.append(Connection(id_a, id_b, type, properties=kwargs))

    def get_area(self, area_id: str) -> Optional[Area]:
        return self.areas.get(area_id)
