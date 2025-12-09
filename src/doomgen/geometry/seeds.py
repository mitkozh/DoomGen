"""
Seed generation engine for Voronoi-first map generation.
Converts abstract Areas into concrete Seed points.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import numpy as np
from shapely.geometry import Point, Polygon, box, LineString, MultiLineString
from shapely.affinity import translate, rotate, scale
import math

from doomgen.abstraction.layout import LayoutGraph, Area, SeedStrategy

@dataclass
class Seed:
    """A single Voronoi seed."""
    x: float
    y: float
    area_id: str
    is_boundary: bool = False # If true, this seed helps define the boundary but isn't part of the area

class StencilLibrary:
    """
    Library of fixed seed patterns (Stencils).
    Used for prefabs like doors, lifts, pillars.
    """
    @staticmethod
    def get_stencil(name: str, width: float, height: float) -> List[Tuple[float, float]]:
        """Returns a list of (x, y) offsets centered at (0,0)."""
        seeds = []
        
        if name == "door_linear":
            # A line of seeds to create a thin rectangular-ish region
            # Good for doors
            # Use a grid instead of a line to ensure solidity
            steps_x = max(3, int(width / 16))
            steps_y = max(1, int(height / 16))
            
            # Grid
            for i in range(steps_x):
                x = -width/2 + (width * i / (steps_x - 1))
                if steps_y > 1:
                    for j in range(steps_y):
                        y = -height/2 + (height * j / (steps_y - 1))
                        seeds.append((x, y))
                else:
                    seeds.append((x, 0))
                
        elif name == "rectangle_grid":
            # Regular grid for lifts/platforms
            step_size = 32
            cols = max(2, int(width / step_size))
            rows = max(2, int(height / step_size))
            
            for r in range(rows):
                y = -height/2 + (height * r / (rows - 1))
                for c in range(cols):
                    x = -width/2 + (width * c / (cols - 1))
                    seeds.append((x, y))
                    
        elif name == "circle_ring":
            # Ring of seeds
            count = max(6, int(width / 16))
            radius = width / 2
            for i in range(count):
                angle = 2 * np.pi * i / count
                seeds.append((np.cos(angle) * radius, np.sin(angle) * radius))
            # Add center seed to make it solid
            seeds.append((0, 0))
                
        elif name == "circle_filled":
            # Filled circle (Ring + Center)
            count = max(6, int(width / 16))
            radius = width / 2
            for i in range(count):
                angle = 2 * np.pi * i / count
                seeds.append((np.cos(angle) * radius, np.sin(angle) * radius))
            seeds.append((0, 0))
            
        return seeds

class SeedEngine:
    """
    Generates seeds for the entire map based on the LayoutGraph.
    """
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def generate(self, graph: LayoutGraph) -> List[Seed]:
        all_seeds: List[Seed] = []
        area_seeds_map: Dict[str, List[Seed]] = {}

        # 1. Generate Area Seeds
        for area_id, area in graph.areas.items():
            seeds = self._generate_area_seeds(area)
            area_seeds_map[area_id] = seeds
            
            # Handle Auto Boundary
            if area.auto_boundary:
                boundary_seeds = self._generate_auto_boundary(area, graph)
                area_seeds_map[area_id].extend(boundary_seeds)
            
        # 2. Apply Priority Filtering (Cookie Cutter)
        # If Area A has higher priority than Area B, remove B's seeds that are "inside" A.
        # "Inside" is approximated by checking distance to A's seeds or A's bounding box.
        # Using bounding box is safer for Prefabs.
        
        sorted_areas = sorted(graph.areas.values(), key=lambda a: a.priority, reverse=True)
        
        for i, high_area in enumerate(sorted_areas):
            if high_area.priority == 0: continue # Skip low priority areas acting as cutters
            
            # Define cutter shape (bounding box in world space)
            w, h = high_area.dimensions
            cx, cy = high_area.transform.x, high_area.transform.y
            # Simple radius check for now, or box check
            # Let's use a box check rotated by transform
            
            # Create Shapely polygon for the high priority area
            # This requires importing shapely geometry
            poly = box(-w/2, -h/2, w/2, h/2)
            poly = rotate(poly, high_area.transform.rotation, origin=(0,0))
            poly = translate(poly, cx, cy)
            
            # Check against all lower priority areas
            for low_area in sorted_areas[i+1:]:
                if low_area.priority >= high_area.priority: continue
                
                low_seeds = area_seeds_map[low_area.id]
                kept_seeds = []
                for s in low_seeds:
                    p = Point(s.x, s.y)
                    if not poly.contains(p):
                        kept_seeds.append(s)
                
                area_seeds_map[low_area.id] = kept_seeds

        # 3. Collect all seeds
        for seeds in area_seeds_map.values():
            all_seeds.extend(seeds)

        # 4. Generate Void Seeds (Bounding Box)
        # This constrains the Voronoi diagram so outer cells are finite.
        if all_seeds:
            xs = [s.x for s in all_seeds]
            ys = [s.y for s in all_seeds]
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
            
            # Add margin
            margin = 256
            minx -= margin
            maxx += margin
            miny -= margin
            maxy += margin
            
            # Create a ring of void seeds
            step = 64
            void_seeds = []
            
            # Top/Bottom
            for x in np.arange(minx, maxx + step, step):
                void_seeds.append(Seed(x, miny, "VOID", is_boundary=True))
                void_seeds.append(Seed(x, maxy, "VOID", is_boundary=True))
                
            # Left/Right
            for y in np.arange(miny + step, maxy, step):
                void_seeds.append(Seed(minx, y, "VOID", is_boundary=True))
                void_seeds.append(Seed(maxx, y, "VOID", is_boundary=True))
                
            all_seeds.extend(void_seeds)
        
        # 5. Deduplicate seeds
        all_seeds = self._remove_close_seeds(all_seeds)

        return all_seeds

    def _remove_close_seeds(self, seeds: List[Seed], min_dist: float = 2.0) -> List[Seed]:
        """Removes seeds that are too close to each other to prevent numerical instability."""
        kept_seeds = []
        for s in seeds:
            too_close = False
            for k in kept_seeds:
                dist = math.sqrt((s.x - k.x)**2 + (s.y - k.y)**2)
                if dist < min_dist:
                    too_close = True
                    break
            if not too_close:
                kept_seeds.append(s)
        return kept_seeds

    def _generate_auto_boundary(self, area: Area, graph: LayoutGraph) -> List[Seed]:
        """Generates boundary seeds for an area, respecting connections."""
        seeds = []
        w, h = area.dimensions
        cx, cy = area.transform.x, area.transform.y
        rot = area.transform.rotation
        
        # Find connections to this area
        connections = []
        for conn in graph.connections:
            other_id = None
            if conn.area_a_id == area.id:
                other_id = conn.area_b_id
            elif conn.area_b_id == area.id:
                other_id = conn.area_a_id
            
            if other_id:
                other_area = graph.get_area(other_id)
                if other_area:
                    # Calculate direction to other area
                    dx = other_area.transform.x - cx
                    dy = other_area.transform.y - cy
                    angle = math.atan2(dy, dx)
                    connections.append(angle)

        # Generate boundary points
        margin = 16
        step = 32
        
        if area.shape_hint == "circle":
            radius = w / 2 + margin
            circumference = 2 * np.pi * radius
            count = int(circumference / step)
            
            for i in range(count):
                angle = 2 * np.pi * i / count
                
                # Check if this angle is close to a connection
                is_connected = False
                for conn_angle in connections:
                    # Normalize angles
                    diff = abs(math.atan2(math.sin(angle - conn_angle), math.cos(angle - conn_angle)))
                    # Connection width threshold (approx 45 degrees / 0.78 rad)
                    if diff < 0.4: # ~22 degrees half-width
                        is_connected = True
                        break
                
                if not is_connected:
                    seeds.append(Seed(
                        cx + radius * np.cos(angle),
                        cy + radius * np.sin(angle),
                        "VOID",
                        is_boundary=True
                    ))
                    
        elif area.shape_hint == "rectangle":
            # TODO: Implement rectangle boundary with connection checking
            # For now, just simple box
            pass
            
        return seeds

    def _generate_area_seeds(self, area: Area) -> List[Seed]:
        seeds: List[Seed] = []
        
        # 1. Determine bounding shape for generation
        w, h = area.dimensions
        cx, cy = area.transform.x, area.transform.y
        rot = area.transform.rotation
        
        # 2. Generate local points based on strategy
        points: List[Tuple[float, float]] = []
        void_points: List[Tuple[float, float]] = []
        
        if area.strategy == SeedStrategy.GRID:
            step = 32 / area.seed_density
            cols = int(w / step)
            rows = int(h / step)
            for r in range(rows):
                y = -h/2 + r * step
                for c in range(cols):
                    x = -w/2 + c * step
                    points.append((x, y))
                    
        elif area.strategy == SeedStrategy.POISSON:
            # Simple rejection sampling for now
            # Target count based on area
            area_sq = w * h if area.shape_hint == "rectangle" else np.pi * (w/2)**2
            count = int((area_sq / 1024) * area.seed_density) # ~1 seed per 32x32 unit
            
            for _ in range(count):
                if area.shape_hint == "circle":
                    # Random point in circle
                    r = (w/2) * np.sqrt(self.rng.random())
                    theta = self.rng.random() * 2 * np.pi
                    points.append((r * np.cos(theta), r * np.sin(theta)))
                else:
                    # Random point in rectangle
                    points.append((
                        self.rng.uniform(-w/2, w/2),
                        self.rng.uniform(-h/2, h/2)
                    ))
                    
        elif area.strategy == SeedStrategy.STENCIL:
            if area.stencil_name:
                points = StencilLibrary.get_stencil(area.stencil_name, w, h)
            else:
                # Fallback
                points = [(0,0)]

        elif area.strategy == SeedStrategy.SINGLE:
            points = [(0,0)]

        elif area.strategy == SeedStrategy.PATH:
            if area.path_points and len(area.path_points) > 1:
                path = LineString(area.path_points)
                length = path.length
                step = 32 / area.seed_density
                
                # Center seeds
                num_points = max(2, int(length / step))
                for i in range(num_points + 1):
                    dist = (i / num_points) * length
                    p = path.interpolate(dist)
                    points.append((p.x, p.y))
                
                # Boundary seeds (VOID)
                width = w # Use width from dimensions
                if width > 0:
                    try:
                        # Offset by width/2 + margin (e.g. 16 units)
                        # This ensures the Voronoi boundary is roughly at width/2
                        offset_dist = width / 2 + 16
                        left = path.parallel_offset(offset_dist, 'left')
                        right = path.parallel_offset(offset_dist, 'right')
                        
                        for boundary_line in [left, right]:
                            if boundary_line.is_empty: continue
                            if isinstance(boundary_line, MultiLineString):
                                lines = boundary_line.geoms
                            else:
                                lines = [boundary_line]
                                
                            for line in lines:
                                b_len = line.length
                                b_steps = max(2, int(b_len / step))
                                for i in range(b_steps + 1):
                                    dist = (i / b_steps) * b_len
                                    p = line.interpolate(dist)
                                    void_points.append((p.x, p.y))
                    except Exception:
                        pass

        # 3. Transform points to world space
        # Rotate then Translate
        rad = np.radians(rot)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)
        
        def transform_and_add(pts, aid, is_boundary=False):
            for px, py in pts:
                # Rotate
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                # Translate
                wx = rx + cx
                wy = ry + cy
                
                # Add Jitter to prevent degenerate Voronoi cases (missing cells)
                # Epsilon jitter (0.05 units) - Increased to handle grid alignments better
                jitter_x = (self.rng.random() - 0.5) * 0.05
                jitter_y = (self.rng.random() - 0.5) * 0.05
                
                seeds.append(Seed(wx + jitter_x, wy + jitter_y, aid, is_boundary=is_boundary))

        transform_and_add(points, area.id)
        transform_and_add(void_points, "VOID", is_boundary=True)
        
        # 4. Auto Boundary Generation
        if area.auto_boundary:
            # We need to access the graph to check connections
            # But _generate_area_seeds doesn't have access to graph currently
            # We'll need to pass it or handle it in generate()
            # For now, let's assume we can't access graph here easily without refactoring
            # Let's return the seeds and handle auto-boundary in generate()
            pass
            
        return seeds
