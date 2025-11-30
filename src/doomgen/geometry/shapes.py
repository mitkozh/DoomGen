"""
This module provides tools for creating base shapes (polygons) that can be
used to define rooms and other map elements. All operations are performed
in an abstract 2D coordinate system using Shapely.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from numpy.random import Generator
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union, nearest_points
from shapely.affinity import translate, rotate, scale
from shapely.validation import make_valid


class ShapeBuilder:
    """Creates geometric shapes for map rooms. All shapes centered at origin (0, 0) by default."""
    
    def __init__(self, seed: Optional[int] = None, rng: Optional[Generator] = None):
        """
        Args:
            seed: Random seed for deterministic generation.
            rng: Existing NumPy generator (takes precedence over seed).
        """
        if rng is not None:
            self.rng = rng
        elif seed is not None:
            self.rng = np.random.default_rng(seed)
        else:
            self.rng = np.random.default_rng()
    
    def create_polygon(
        self,
        sides: int,
        radius: float,
        center: tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0
    ) -> Polygon:
        """
        Create a regular N-sided polygon.
        
        Args:
            sides: Number of sides (minimum 3).
            radius: Distance from center to vertices.
            center: Center point (x, y).
            rotation: Rotation in degrees.
        
        Returns:
            Shapely Polygon.
        """
        if sides < 3:
            raise ValueError(f"Polygon must have at least 3 sides, got {sides}")
        if radius <= 0:
            raise ValueError(f"Radius must be positive, got {radius}")
        
        # Generate vertices
        angles = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        # Start from top (90 degrees) for consistent orientation
        angles = angles - np.pi / 2
        
        # For 4-sided polygons (squares), add 45 degrees to make axis-aligned
        # This ensures squares look like squares, not diamonds
        if sides == 4:
            angles = angles + np.pi / 4
        
        vertices = [
            (radius * np.cos(angle), radius * np.sin(angle))
            for angle in angles
        ]
        
        polygon = Polygon(vertices)
        
        # Apply rotation if specified
        if rotation != 0:
            polygon = rotate(polygon, rotation, origin=(0, 0))
        
        # Translate to center
        if center != (0.0, 0.0):
            polygon = translate(polygon, xoff=center[0], yoff=center[1])
        
        return polygon
    
    def create_rectangle(
        self,
        width: float,
        height: float,
        center: tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0
    ) -> Polygon:
        """
        Create a rectangle.
        
        Args:
            width: Width of the rectangle.
            height: Height of the rectangle.
            center: Center point (x, y).
            rotation: Rotation in degrees.
        
        Returns:
            Shapely Polygon.
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Dimensions must be positive, got {width}x{height}")
        
        half_w = width / 2
        half_h = height / 2
        
        vertices = [
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h),
        ]
        
        polygon = Polygon(vertices)
        
        if rotation != 0:
            polygon = rotate(polygon, rotation, origin=(0, 0))
        
        if center != (0.0, 0.0):
            polygon = translate(polygon, xoff=center[0], yoff=center[1])
        
        return polygon
    
    def create_connector(
        self,
        room_a: Polygon,
        room_b: Polygon,
        width: float,
        overlap: float = 16.0
    ) -> Polygon:
        """
        Create a corridor polygon connecting two rooms.
        
        Extends past room boundaries by `overlap` for proper CSG cutting.
        
        Args:
            room_a: First room polygon.
            room_b: Second room polygon.
            width: Corridor width.
            overlap: Extension into each room (default 16).
        
        Returns:
            Corridor polygon.
        """
        # Use centroid-to-centroid direction for a natural corridor path
        ca = room_a.centroid
        cb = room_b.centroid
        
        # Calculate direction vector
        dx = cb.x - ca.x
        dy = cb.y - ca.y
        length = np.sqrt(dx * dx + dy * dy)
        
        if length < 1e-6:
            # Rooms have same centroid, use default direction
            nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / length, dy / length
        
        # Create a line from centroid A to centroid B
        line_ab = LineString([(ca.x, ca.y), (cb.x, cb.y)])
        
        # Find where this line intersects each room's boundary
        # The intersection with the boundary gives us the exit/entry points
        boundary_a = room_a.exterior
        boundary_b = room_b.exterior
        
        intersection_a = line_ab.intersection(boundary_a)
        intersection_b = line_ab.intersection(boundary_b)
        
        # Get the intersection points (could be Point or MultiPoint)
        if intersection_a.is_empty:
            pt_a_x, pt_a_y = ca.x, ca.y
        elif intersection_a.geom_type == 'MultiPoint':
            # Find the point closest to room_b's centroid
            pts = list(intersection_a.geoms)
            pt_a = min(pts, key=lambda p: p.distance(cb))
            pt_a_x, pt_a_y = pt_a.x, pt_a.y
        elif intersection_a.geom_type == 'Point':
            pt_a_x, pt_a_y = intersection_a.x, intersection_a.y
        else:
            # LineString intersection (edge case) - use centroid of result
            c = intersection_a.centroid
            pt_a_x, pt_a_y = c.x, c.y
        
        if intersection_b.is_empty:
            pt_b_x, pt_b_y = cb.x, cb.y
        elif intersection_b.geom_type == 'MultiPoint':
            # Find the point closest to room_a's centroid
            pts = list(intersection_b.geoms)
            pt_b = min(pts, key=lambda p: p.distance(ca))
            pt_b_x, pt_b_y = pt_b.x, pt_b.y
        elif intersection_b.geom_type == 'Point':
            pt_b_x, pt_b_y = intersection_b.x, intersection_b.y
        else:
            c = intersection_b.centroid
            pt_b_x, pt_b_y = c.x, c.y
        
        # Extend points into rooms for proper overlap
        start_x = pt_a_x - nx * overlap
        start_y = pt_a_y - ny * overlap
        end_x = pt_b_x + nx * overlap
        end_y = pt_b_y + ny * overlap
        
        # Create corridor as buffered line with flat caps
        line = LineString([(start_x, start_y), (end_x, end_y)])
        corridor = line.buffer(width / 2, cap_style='flat')
        
        return corridor
    
    def create_circle(
        self,
        radius: float,
        center: tuple[float, float] = (0.0, 0.0),
        resolution: int = 32
    ) -> Polygon:
        """
        Create a circle (approximated by polygon).
        
        Args:
            radius: Circle radius.
            center: Center point (x, y).
            resolution: Number of vertices (higher = smoother).
        
        Returns:
            Shapely Polygon.
        """
        return self.create_polygon(sides=resolution, radius=radius, center=center)
    
    def create_corridor(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        width: float
    ) -> Polygon:
        """
        Create a straight corridor between two points.
        
        Args:
            start: Starting point (x, y).
            end: Ending point (x, y).
            width: Corridor width.
        
        Returns:
            Shapely Polygon.
        """
        if width <= 0:
            raise ValueError(f"Width must be positive, got {width}")
        
        line = LineString([start, end])
        corridor = line.buffer(width / 2, cap_style='flat')
        
        return corridor
    
    def create_corridor_from_path(
        self,
        path: list[tuple[float, float]],
        width: float,
        cap_style: str = 'round'
    ) -> Polygon:
        """
        Create a corridor following a path of waypoints.
        
        Args:
            path: List of (x, y) points.
            width: Corridor width.
            cap_style: 'round', 'flat', or 'square'.
        
        Returns:
            Shapely Polygon.
        """
        if len(path) < 2:
            raise ValueError("Path must have at least 2 points")
        if width <= 0:
            raise ValueError(f"Width must be positive, got {width}")
        
        cap_styles = {'round': 1, 'flat': 2, 'square': 3}
        cap = cap_styles.get(cap_style, 1)
        
        line = LineString(path)
        corridor = line.buffer(width / 2, cap_style=cap, join_style=1)
        
        return corridor
    
    def merge_shapes(self, *shapes: Polygon) -> Polygon:
        """
        Merge multiple shapes into one using union.
        
        Args:
            *shapes: Polygons to merge.
        
        Returns:
            Single merged Polygon (largest if disconnected).
        """
        if not shapes:
            raise ValueError("At least one shape must be provided")
        
        result = unary_union(shapes)
        
        # Ensure we return a Polygon (not MultiPolygon)
        if result.geom_type == 'MultiPolygon':
            # Return the largest polygon if they're disconnected
            result = max(result.geoms, key=lambda p: p.area)
        
        return result
    
    def subtract_polygon(self, base: Polygon, cutter: Polygon) -> Polygon:
        """
        Subtract cutter from base (CSG difference).
        
        Args:
            base: Polygon to cut from.
            cutter: Polygon to subtract.
        
        Returns:
            Resulting Polygon.
        """
        if not base.intersects(cutter):
            return base  # No intersection, return unchanged
        
        result = base.difference(cutter)
        
        # Handle invalid geometry
        if not result.is_valid:
            result = make_valid(result)
        
        # Handle MultiPolygon results
        if isinstance(result, MultiPolygon):
            # Keep the largest piece
            result = max(result.geoms, key=lambda p: p.area)
        
        return result
    
    def snap_to_grid(self, polygon: Polygon, grid_size: int = 8) -> Polygon:
        """
        Snap polygon vertices to grid. Important for Doom map compatibility.
        
        Args:
            polygon: Polygon to snap.
            grid_size: Grid spacing (default 8 for Doom).
        
        Returns:
            Polygon with snapped coordinates.
        """
        def snap_coord(val: float) -> float:
            return round(val / grid_size) * grid_size
        
        exterior_coords = [
            (snap_coord(x), snap_coord(y))
            for x, y in polygon.exterior.coords
        ]
        
        # Handle holes if any
        holes = []
        for interior in polygon.interiors:
            hole_coords = [
                (snap_coord(x), snap_coord(y))
                for x, y in interior.coords
            ]
            holes.append(hole_coords)
        
        return Polygon(exterior_coords, holes)
    
    def to_integer_coords(self, polygon: Polygon) -> Polygon:
        """
        Convert polygon coordinates to integers for WAD export. Important for Doom.
        
        Args:
            polygon: Polygon to convert.
        
        Returns:
            Polygon with integer coordinates.
        """
        exterior_coords = [
            (int(round(x)), int(round(y)))
            for x, y in polygon.exterior.coords
        ]
        
        holes = []
        for interior in polygon.interiors:
            hole_coords = [
                (int(round(x)), int(round(y)))
                for x, y in interior.coords
            ]
            holes.append(hole_coords)
        
        return Polygon(exterior_coords, holes)
    
    def validate_polygon(self, polygon: Polygon) -> tuple[bool, str]:
        """
        Check if polygon is valid for Doom maps.
        
        Args:
            polygon: Polygon to validate.
        
        Returns:
            Tuple of (is_valid, message).
        """
        if not polygon.is_valid:
            return False, f"Invalid geometry: {polygon.geom_type}"
        
        if polygon.is_empty:
            return False, "Polygon is empty"
        
        if polygon.area < 1:
            return False, "Polygon area too small"
        
        # Check for self-intersection
        if not polygon.is_simple:
            return False, "Polygon has self-intersections"
        
        return True, "Valid"
    
    def create_irregular_polygon(
        self,
        center: tuple[float, float],
        radius: float,
        sides: int = 6,
        irregularity: float = 0.3,
        grid_size: int = 8
    ) -> Polygon:
        """
        Create an irregular polygon with perturbed vertices.
        
        Args:
            center: Center point (x, y).
            radius: Base radius.
            sides: Number of sides (minimum 3).
            irregularity: Vertex variation (0.0-0.5).
            grid_size: Grid for snapping (default 8).
        
        Returns:
            Valid Polygon with integer coordinates.
        """
        if sides < 3:
            raise ValueError(f"Polygon must have at least 3 sides, got {sides}")
        if radius <= 0:
            raise ValueError(f"Radius must be positive, got {radius}")
        
        # Clamp irregularity to safe range
        irregularity = min(max(irregularity, 0.0), 0.45)
        
        # Generate evenly spaced angles
        base_angles = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        
        coords = []
        for i, angle in enumerate(base_angles):
            # Perturb radius
            r = radius * (1.0 + self.rng.uniform(-irregularity, irregularity))
            
            # Perturb angle (less than half the angular spacing to prevent crossings)
            angle_step = 2 * np.pi / sides
            max_angle_offset = angle_step * 0.3
            a = angle + self.rng.uniform(-max_angle_offset, max_angle_offset)
            
            # Calculate position
            x = center[0] + r * np.cos(a)
            y = center[1] + r * np.sin(a)
            
            # Snap to grid
            x = int(round(x / grid_size) * grid_size)
            y = int(round(y / grid_size) * grid_size)
            
            coords.append((x, y))
        
        # Close the polygon
        coords.append(coords[0])
        
        # Create polygon
        polygon = Polygon(coords)
        
        # Fix any issues with buffer(0)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        
        # If we got a MultiPolygon, take the largest
        if polygon.geom_type == 'MultiPolygon':
            polygon = max(polygon.geoms, key=lambda p: p.area)
        
        # Simplify to remove any duplicate points
        polygon = polygon.simplify(1.0, preserve_topology=True)
        
        return polygon
