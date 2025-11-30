"""
Geometry operations - Pure CSG and coordinate operations.

This module provides low-level geometry operations that are purely
mathematical with no Doom-specific knowledge.
"""

from __future__ import annotations

from typing import Union, Optional
import math

from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
from shapely.validation import make_valid


def snap_to_grid(value: float, grid_size: int = 8) -> int:
    """
    Snap a coordinate value to the nearest grid point.
    
    Doom coordinates should be integers, and aligning to a grid
    (typically 8 units) helps avoid rendering issues.
    
    Args:
        value: The coordinate value to snap.
        grid_size: Grid spacing (default 8).
    
    Returns:
        The snapped integer value.
    """
    return int(round(value / grid_size) * grid_size)


def snap_polygon_to_grid(polygon: Polygon, grid_size: int = 8) -> Polygon:
    """
    Snap all vertices of a polygon to grid coordinates.
    
    Args:
        polygon: The polygon to snap.
        grid_size: Grid spacing (default 8).
    
    Returns:
        A new polygon with snapped coordinates.
    """
    coords = list(polygon.exterior.coords)
    snapped = [(snap_to_grid(x, grid_size), snap_to_grid(y, grid_size)) for x, y in coords]
    return Polygon(snapped)


def to_integer_coords(polygon: Polygon) -> Polygon:
    """
    Convert polygon coordinates to integers.
    
    Args:
        polygon: The polygon to convert.
    
    Returns:
        A new polygon with integer coordinates.
    """
    coords = list(polygon.exterior.coords)
    int_coords = [(int(round(x)), int(round(y))) for x, y in coords]
    return Polygon(int_coords)


def ensure_polygon(geom: Union[Polygon, MultiPolygon, GeometryCollection]) -> Polygon:
    """
    Ensure geometry is a single Polygon.
    
    When CSG operations produce MultiPolygon or GeometryCollection,
    this extracts the largest polygon.
    
    Args:
        geom: Input geometry (Polygon, MultiPolygon, or GeometryCollection).
    
    Returns:
        A single Polygon (the largest if multiple).
    
    Raises:
        ValueError: If no polygon can be extracted.
    """
    if isinstance(geom, Polygon):
        return geom
    
    if isinstance(geom, MultiPolygon):
        if len(geom.geoms) == 0:
            raise ValueError("Empty MultiPolygon")
        return max(geom.geoms, key=lambda p: p.area)
    
    if isinstance(geom, GeometryCollection):
        polygons = [g for g in geom.geoms if isinstance(g, Polygon)]
        if not polygons:
            raise ValueError("GeometryCollection contains no polygons")
        return max(polygons, key=lambda p: p.area)
    
    raise ValueError(f"Cannot convert {type(geom).__name__} to Polygon")


def cut_polygon(
    polygon: Polygon,
    cutter: Polygon,
    grid_size: int = 8
) -> Polygon:
    """
    Cut (subtract) one polygon from another.
    
    This is the "global difference" operation used to create
    connections between rooms - the cut area becomes a separate
    sector (corridor, door, etc.).
    
    Args:
        polygon: The polygon to cut from.
        cutter: The polygon to subtract.
        grid_size: Grid size for snapping result.
    
    Returns:
        The resulting polygon after subtraction.
    """
    result = polygon.difference(cutter)
    
    if result.is_empty:
        raise ValueError("Cut operation resulted in empty polygon")
    
    result = ensure_polygon(result)
    result = make_valid(result)
    
    if grid_size > 0:
        result = snap_polygon_to_grid(result, grid_size)
    
    return result


def merge_polygons(
    *polygons: Polygon,
    grid_size: int = 8
) -> Polygon:
    """Merge multiple polygons into one ("local merge" for single sectors)."""
    if not polygons:
        raise ValueError("No polygons to merge")
    
    if len(polygons) == 1:
        return polygons[0]
    
    result = unary_union(polygons)
    
    if result.is_empty:
        raise ValueError("Merge operation resulted in empty polygon")
    
    result = ensure_polygon(result)
    result = make_valid(result)
    
    if grid_size > 0:
        result = snap_polygon_to_grid(result, grid_size)
    
    return result


def buffer_polygon(
    polygon: Polygon,
    distance: float,
    grid_size: int = 8
) -> Polygon:
    """
    Expand or shrink a polygon by a distance.
    
    Positive distance expands, negative shrinks.
    
    Args:
        polygon: The polygon to buffer.
        distance: Buffer distance (positive=expand, negative=shrink).
        grid_size: Grid size for snapping result.
    
    Returns:
        The buffered polygon.
    """
    result = polygon.buffer(distance, join_style=2)  # mitre join
    
    if result.is_empty:
        raise ValueError("Buffer operation resulted in empty polygon")
    
    result = ensure_polygon(result)
    
    if grid_size > 0:
        result = snap_polygon_to_grid(result, grid_size)
    
    return result


def create_rectangle(
    width: float,
    height: float,
    center: tuple[float, float] = (0, 0),
    grid_size: int = 8
) -> Polygon:
    """
    Create a rectangle polygon.
    
    Args:
        width: Rectangle width.
        height: Rectangle height.
        center: Center point (x, y).
        grid_size: Grid size for snapping.
    
    Returns:
        A rectangular polygon.
    """
    cx, cy = center
    half_w = width / 2
    half_h = height / 2
    
    coords = [
        (cx - half_w, cy - half_h),
        (cx + half_w, cy - half_h),
        (cx + half_w, cy + half_h),
        (cx - half_w, cy + half_h),
    ]
    
    polygon = Polygon(coords)
    
    if grid_size > 0:
        polygon = snap_polygon_to_grid(polygon, grid_size)
    
    return polygon


def create_corridor_polygon(
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    grid_size: int = 8
) -> Polygon:
    """
    Create a corridor polygon between two points.
    
    Args:
        start: Starting point (x, y).
        end: Ending point (x, y).
        width: Corridor width.
        grid_size: Grid size for snapping.
    
    Returns:
        A corridor-shaped polygon.
    """
    from shapely.geometry import LineString
    
    line = LineString([start, end])
    corridor = line.buffer(width / 2, cap_style=3)  # flat caps
    
    result = ensure_polygon(corridor)
    
    if grid_size > 0:
        result = snap_polygon_to_grid(result, grid_size)
    
    return result


def get_edge_midpoint(
    polygon: Polygon,
    edge_index: int
) -> tuple[float, float]:
    """
    Get the midpoint of a polygon edge.
    
    Args:
        polygon: The polygon.
        edge_index: Index of the edge (0 = first edge).
    
    Returns:
        Midpoint (x, y) of the edge.
    """
    coords = list(polygon.exterior.coords)
    n_edges = len(coords) - 1
    
    if edge_index < 0 or edge_index >= n_edges:
        raise ValueError(f"Edge index {edge_index} out of range (0-{n_edges-1})")
    
    p1 = coords[edge_index]
    p2 = coords[(edge_index + 1) % len(coords)]
    
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def find_closest_edge(
    polygon: Polygon,
    point: tuple[float, float]
) -> int:
    """
    Find the edge of a polygon closest to a point.
    
    Args:
        polygon: The polygon.
        point: The reference point (x, y).
    
    Returns:
        Index of the closest edge.
    """
    from shapely.geometry import Point, LineString
    
    coords = list(polygon.exterior.coords)
    pt = Point(point)
    
    min_dist = float('inf')
    closest_edge = 0
    
    for i in range(len(coords) - 1):
        edge = LineString([coords[i], coords[i + 1]])
        dist = pt.distance(edge)
        if dist < min_dist:
            min_dist = dist
            closest_edge = i
    
    return closest_edge


def polygon_contains_point(
    polygon: Polygon,
    point: tuple[float, float]
) -> bool:
    """
    Check if a polygon contains a point.
    
    Args:
        polygon: The polygon.
        point: The point (x, y).
    
    Returns:
        True if the point is inside the polygon.
    """
    from shapely.geometry import Point
    return polygon.contains(Point(point))


def get_polygon_center(polygon: Polygon) -> tuple[float, float]:
    """
    Get the centroid of a polygon.
    
    Args:
        polygon: The polygon.
    
    Returns:
        Centroid (x, y).
    """
    centroid = polygon.centroid
    return (centroid.x, centroid.y)
