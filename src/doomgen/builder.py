"""
High-level builder for creating Doom maps procedurally.
Simplifies the creation of rooms, corridors, and connections.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, Dict, Any
import math
import random
import numpy as np

from doomgen.abstraction.layout import LayoutGraph, Area, AreaConfig, Transform, SeedStrategy, ConnectionType, Prefab
from doomgen.geometry.seeds import SeedEngine
from doomgen.geometry.mesh import VoronoiMesh
from doomgen.doom.wad import WADWriter, DoomMapData
from doomgen.doom.translator import MapTranslator
from doomgen.utils.geometry_utils import create_wavy_path

class ProceduralMapBuilder:
    """
    A builder class that provides a simplified API for generating Doom maps.
    Wraps LayoutGraph and SeedEngine.
    """
    def __init__(self, seed: int = 42):
        self.graph = LayoutGraph()
        self.seed = seed
        self.engine = SeedEngine(seed=seed)
        self.wad_writer = WADWriter()
        self.mesh: Optional[VoronoiMesh] = None
        self.map_data: Optional[DoomMapData] = None
        self.things_to_add: List[Dict[str, Any]] = []
        self.name_to_id: Dict[str, str] = {}
        
    def add_room(
        self,
        name: str,
        x: float,
        y: float,
        shape: str = "circle",
        width: float = 256,
        height: float = 256,
        floor_height: int = 0,
        ceiling_height: int = 128,
        floor_texture: str = "FLOOR4_8",
        ceiling_texture: str = "CEIL3_5",
        wall_texture: str = "STARTAN3",
        special: int = 0,
        auto_boundary: bool = True
    ) -> str:
        """
        Adds a room to the map.
        
        Args:
            name: Room name.
            x, y: Center coordinates.
            shape: "circle" or "rectangle".
            width, height: Dimensions (for circle, width is diameter).
            auto_boundary: If True, automatically generates void seeds around the room.
        """
        strategy = SeedStrategy.POISSON if shape == "circle" else SeedStrategy.GRID
        
        config = AreaConfig(
            floor_height=floor_height,
            ceiling_height=ceiling_height,
            floor_texture=floor_texture,
            ceiling_texture=ceiling_texture,
            wall_texture=wall_texture,
            special=special
        )
        
        area = Area(
            name=name,
            transform=Transform(x, y),
            strategy=strategy,
            shape_hint=shape,
            dimensions=(width, height),
            seed_density=1.5 if shape == "circle" else 1.0,
            config=config,
            auto_boundary=auto_boundary
        )
        
        area_id = self.graph.add_area(area)
        self.name_to_id[name] = area_id
        return area_id

    def _resolve_id(self, id_or_name: str) -> str:
        """Helper to resolve name to ID if possible."""
        if id_or_name in self.name_to_id:
            return self.name_to_id[id_or_name]
        return id_or_name

    def add_corridor(
        self,
        room_a_id: str,
        room_b_id: str,
        width: float = 96,
        style: str = "straight", # "straight", "wavy"
        door_a: bool = False,
        door_b: bool = False
    ) -> str:
        """
        Adds a corridor connecting two rooms.
        Automatically calculates start/end points to avoid overlapping room centers.
        """
        room_a_id = self._resolve_id(room_a_id)
        room_b_id = self._resolve_id(room_b_id)
        
        room_a = self.graph.get_area(room_a_id)
        room_b = self.graph.get_area(room_b_id)
        
        if not room_a or not room_b:
            raise ValueError(f"Room IDs not found: {room_a_id}, {room_b_id}")
            
        # Calculate geometry
        x1, y1 = room_a.transform.x, room_a.transform.y
        x2, y2 = room_b.transform.x, room_b.transform.y
        
        dx = x2 - x1
        dy = y2 - y1
        dist = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        
        # Determine start/end offsets based on room size
        # Assume circular approximation for simplicity
        r_a = room_a.dimensions[0] / 2
        r_b = room_b.dimensions[0] / 2
        
        # Start/End points (slightly inside rooms for connection)
        start_dist = r_a - 16
        end_dist = dist - r_b + 16
        
        sx = x1 + start_dist * math.cos(angle)
        sy = y1 + start_dist * math.sin(angle)
        ex = x1 + end_dist * math.cos(angle)
        ey = y1 + end_dist * math.sin(angle)
        
        # Generate path points
        if style == "wavy":
            path_points = create_wavy_path((sx, sy), (ex, ey), amplitude=30)
        else:
            path_points = [(sx, sy), (ex, ey)]
            
        # Filter points inside rooms (prevent mixed cells)
        filtered_points = []
        for px, py in path_points:
            d_a = math.sqrt((px-x1)**2 + (py-y1)**2)
            d_b = math.sqrt((px-x2)**2 + (py-y2)**2)
            
            # Keep if outside rooms (with buffer)
            if d_a > (r_a - 8) and d_b > (r_b - 8):
                filtered_points.append((px, py))
                
        if not filtered_points:
            filtered_points = [(sx, sy), (ex, ey)]
            
        # Create Corridor Area
        corridor = Area(
            name=f"Corridor {room_a.name}-{room_b.name}",
            transform=Transform(0, 0),
            strategy=SeedStrategy.PATH,
            path_points=filtered_points,
            dimensions=(width, 0),
            seed_density=1.0,
            config=AreaConfig(
                floor_height=min(room_a.config.floor_height, room_b.config.floor_height),
                ceiling_height=min(room_a.config.ceiling_height, room_b.config.ceiling_height) - 16,
                floor_texture="CEIL3_5"
            )
        )
        corr_id = self.graph.add_area(corridor)
        
        # Handle Doors
        # For simplicity in this version, we'll just add the door prefab if requested
        # and rewire the connections.
        
        current_start_id = room_a_id
        
        if door_a:
            # Add door at start
            door_dist = r_a + 16 # Just outside room
            dx = door_dist * math.cos(angle)
            dy = door_dist * math.sin(angle)
            
            door_id = self._create_door_prefab(
                f"Door {room_a.name}", 
                x1 + dx, y1 + dy, 
                math.degrees(angle) + 90
            )
            
            self.graph.connect(current_start_id, door_id, ConnectionType.DOOR)
            current_start_id = door_id
            
        self.graph.connect(current_start_id, corr_id, ConnectionType.OPEN)
        
        current_end_id = room_b_id
        
        if door_b:
            # Add door at end
            door_dist = r_b + 16
            dx = door_dist * math.cos(angle + math.pi) # Opposite direction
            dy = door_dist * math.sin(angle + math.pi)
            
            door_id = self._create_door_prefab(
                f"Door {room_b.name}", 
                x2 + dx, y2 + dy, 
                math.degrees(angle) + 90
            )
            
            self.graph.connect(corr_id, door_id, ConnectionType.OPEN)
            self.graph.connect(door_id, room_b_id, ConnectionType.DOOR)
        else:
            self.graph.connect(corr_id, room_b_id, ConnectionType.OPEN)
            
        return corr_id

    def add_thing(
        self, 
        room_id: str, 
        thing_type: int, 
        count: int = 1, 
        **kwargs
    ):
        """
        Schedules things to be added to a room.
        
        Args:
            room_id: The ID/Name of the room to place things in.
            thing_type: The Doom Thing Type ID (e.g., from ThingType enum).
            count: Number of things to spawn.
            **kwargs: Additional arguments passed to map_data.add_thing (e.g., angle, flags).
        """
        room_id = self._resolve_id(room_id)
        
        if not self.graph.get_area(room_id):
             raise ValueError(f"Room {room_id} not found")
        
        self.things_to_add.append({
            "room_id": room_id,
            "type": thing_type,
            "count": count,
            "kwargs": kwargs
        })

    def _create_door_prefab(self, name: str, x: float, y: float, rotation: float) -> str:
        door = Prefab(
            name=name,
            transform=Transform(x, y, rotation=rotation),
            stencil_name="door_linear",
            dimensions=(64, 16),
            config=AreaConfig(
                floor_height=0, ceiling_height=0,
                floor_texture="FLOOR4_8", ceiling_texture="CEIL3_5",
                wall_texture="BIGDOOR2", upper_texture="BIGDOOR2", lower_texture="BIGDOOR2"
            )
        )
        return self.graph.add_area(door)

    def generate_geometry(self) -> VoronoiMesh:
        """Generates seeds and builds the Voronoi mesh."""
        print("Generating seeds...")
        seeds = self.engine.generate(self.graph)
        print(f"Generated {len(seeds)} seeds.")
        
        print("Building mesh...")
        self.mesh = VoronoiMesh(seeds, self.graph)
        self.mesh.build()
        return self.mesh

    def translate(self, map_name: str = "MAP01") -> DoomMapData:
        """Translates the mesh to Doom format and places things."""
        if not self.mesh:
            raise RuntimeError("Mesh not built. Call generate_geometry() first.")
            
        print("Translating to Doom format...")
        self.map_data = self.wad_writer.create_map(map_name)
        translator = MapTranslator(self.map_data)
        translator.translate(self.mesh, self.graph)
        
        # Add scheduled things
        self._place_things()
        
        return self.map_data

    def _place_things(self):
        """Places scheduled things into the map data."""
        if not self.map_data:
            return

        rng = random.Random(self.seed)
        
        for item in self.things_to_add:
            room = self.graph.get_area(item["room_id"])
            if not room: continue

            # Determine spawn area bounds
            cx, cy = room.transform.x, room.transform.y
            w, h = room.dimensions
            
            # Safe margin to avoid spawning in walls
            margin = 32
            
            for _ in range(item["count"]):
                if room.shape_hint == "circle":
                    # Random point in circle
                    radius = (w / 2) - margin
                    if radius < 0: radius = 0
                    
                    angle = rng.uniform(0, 2 * math.pi)
                    r = rng.uniform(0, radius) # Uniform distribution (not area-correct but fine for spawning)
                    # For area-correct: r = radius * math.sqrt(rng.random())
                    
                    x = cx + r * math.cos(angle)
                    y = cy + r * math.sin(angle)
                else:
                    # Random point in rectangle
                    half_w = (w / 2) - margin
                    half_h = (h / 2) - margin
                    if half_w < 0: half_w = 0
                    if half_h < 0: half_h = 0
                    
                    x = cx + rng.uniform(-half_w, half_w)
                    y = cy + rng.uniform(-half_h, half_h)
                
                # Add to map data
                self.map_data.add_thing(
                    x=int(x),
                    y=int(y),
                    thing_type=item["type"],
                    **item["kwargs"]
                )

    def save(self, output_path: str):
        """Saves the WAD to disk."""
        print(f"Saving to {output_path}...")
        self.wad_writer.save(output_path)

    def build(self, output_path: str, map_name: str = "MAP01"):
        """Runs the full pipeline: Generate -> Translate -> Save."""
        self.generate_geometry()
        self.translate(map_name)
        self.save(output_path)

