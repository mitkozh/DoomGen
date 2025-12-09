"""
Hybrid Voronoi generation - Fixed shapes + organic fill.

This module implements the core Voronoi tessellation system that combines:
1. Fixed Pass: User-defined exact shapes (squares, hexagons, custom polygons)
2. Fill Pass: Organic Voronoi cells that fill the remaining space

The result is a cellular partition with guaranteed shared edges between adjacent cells.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set
from enum import Enum

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid


class CellType(Enum):
    """Type of Voronoi cell."""
    FIXED = "fixed"  # User-defined exact shape
    FILL = "fill"    # Generated organic cell
    VOID = "void"    # Empty space (outside map bounds)


@dataclass
class VoronoiCell:
    """A cell in the Voronoi diagram."""
    id: int
    polygon: Polygon
    cell_type: CellType
    center: Tuple[float, float]
    neighbors: Set[int] = field(default_factory=set)
    ridges: Dict[int, LineString] = field(default_factory=dict)  # neighbor_id -> shared edge


@dataclass
class VoronoiResult:
    """Result of Voronoi generation."""
    cells: Dict[int, VoronoiCell]
    fixed_cell_ids: Set[int]
    fill_cell_ids: Set[int]
    bounds: Polygon
    errors: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if generation was successful."""
        return len(self.errors) == 0


class VoronoiDiagram:
    """
    Hybrid Voronoi diagram generator.
    
    Supports two-pass generation:
    1. Fixed Pass: Lock user-defined shapes
    2. Fill Pass: Generate organic cells in remaining space
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize Voronoi diagram generator.
        
        Args:
            seed: Random seed for reproducibility.
        """
        self.seed = seed
        self.rng = np.random.default_rng(seed)
    
    def generate_hybrid(
        self,
        bounds: Polygon,
        fixed_shapes: Optional[Dict[str, Polygon]] = None,
        num_fill_cells: int = 50,
        relaxation_iterations: int = 3,
        min_distance: float = 32.0,
        seed: Optional[int] = None
    ) -> VoronoiResult:
        """
        Generate hybrid Voronoi diagram with fixed shapes + organic fill.
        
        Args:
            bounds: Map boundary polygon.
            fixed_shapes: Dict of {name: polygon} for locked regions.
            num_fill_cells: Ignored in new algorithm (uses grid spacing).
            relaxation_iterations: Lloyd's relaxation iterations.
            min_distance: Spacing for boundary points (fill uses 2x).
            seed: Override random seed.
        
        Returns:
            VoronoiResult with cells and adjacency data.
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        
        errors = []
        
        # Validate bounds
        if not bounds.is_valid:
            bounds = make_valid(bounds)
        
        fixed_shapes = fixed_shapes or {}
        
        # Step 1: BOUNDARY INJECTION - Seed points along fixed shape perimeters
        # Use min_distance for boundary spacing (e.g. 32)
        boundary_points = self._generate_boundary_points(fixed_shapes, spacing=min_distance)
        
        # Step 2: VOID FILLING - Generate points using Jittered Grid
        # Use min_distance * 2 for fill spacing (e.g. 64)
        fill_points = self._generate_fill_points(
            bounds, fixed_shapes, spacing=min_distance * 2.0
        )
        
        # Step 3: Lloyd's relaxation ONLY on fill points (keep boundary points fixed)
        if len(fill_points) > 0 and relaxation_iterations > 0:
            fill_points = self._lloyds_relaxation(
                fill_points, bounds, iterations=relaxation_iterations
            )
            
        # Step 4: Combine boundary barrier points with fill points
        if len(boundary_points) > 0 and len(fill_points) > 0:
            all_points = np.vstack([boundary_points, fill_points])
        elif len(boundary_points) > 0:
            all_points = boundary_points
        elif len(fill_points) > 0:
            all_points = fill_points
        else:
            all_points = np.empty((0, 2))
        
        points = all_points
        
        if len(points) < 3:
            errors.append(f"Not enough points ({len(points)}) for Voronoi diagram (need >= 3)")
            return self._create_fallback_result(fixed_shapes, bounds, errors)
        
        # Step 5: Compute Voronoi diagram
        try:
            vor = Voronoi(points)
        except Exception as e:
            errors.append(f"Voronoi generation failed: {str(e)}")
            return self._create_fallback_result(fixed_shapes, bounds, errors)
        
        # Step 6: TESSELLATION - Convert Voronoi regions to polygons (clipped to bounds)
        all_voronoi_cells = self._voronoi_to_polygons(vor, bounds)
        
        # Step 7: STITCHING - Identify and replace internal cells with original fixed polygons
        fill_cells = self._classify_and_filter_cells(all_voronoi_cells, fixed_shapes)
        
        # Step 8: Extract vertices from Voronoi cell boundaries and merge into fixed shapes
        modified_fixed_shapes = self._merge_vertices_into_fixed_shapes(fixed_shapes, fill_cells)
        
        # Step 9: Build cell dictionary (fixed + fill)
        cells, fixed_cell_ids, fill_cell_ids = self._build_cell_dictionary(
            modified_fixed_shapes, fill_cells
        )
        
        # Step 10: Build adjacency graph (detect shared edges)
        self._build_adjacency_graph(cells)
        
        return VoronoiResult(
            cells=cells,
            fixed_cell_ids=fixed_cell_ids,
            fill_cell_ids=fill_cell_ids,
            bounds=bounds,
            errors=errors
        )

    def _generate_boundary_points(
        self, 
        fixed_shapes: Dict[str, Polygon], 
        spacing: float = 32.0
    ) -> np.ndarray:
        """Generate seed points along the perimeter of fixed shapes."""
        boundary_points = []
        
        for shape in fixed_shapes.values():
            # Walk along the exterior of the polygon
            perimeter = shape.exterior.length
            # Place a point every 'spacing' units
            for distance in np.arange(0, perimeter, spacing):
                point = shape.exterior.interpolate(distance)
                boundary_points.append((point.x, point.y))
            
        return np.array(boundary_points) if boundary_points else np.empty((0, 2))

    def _generate_fill_points(
        self,
        bounds: Polygon,
        fixed_shapes: Dict[str, Polygon],
        spacing: float = 64.0
    ) -> np.ndarray:
        """
        Generates points using a Jittered Grid to ensure uniform coverage.
        """
        minx, miny, maxx, maxy = bounds.bounds
        points = []
        
        # Create a union of fixed shapes for fast checking
        fixed_union = unary_union(list(fixed_shapes.values())) if fixed_shapes else None
        
        # Iterate over the grid
        for x in np.arange(minx, maxx, spacing):
            for y in np.arange(miny, maxy, spacing):
                
                # Add random jitter (offset) to make it organic, not square
                jitter_x = self.rng.uniform(-spacing/2.5, spacing/2.5)
                jitter_y = self.rng.uniform(-spacing/2.5, spacing/2.5)
                
                pt = Point(x + jitter_x, y + jitter_y)
                
                # 1. Check if inside map bounds
                if not bounds.contains(pt):
                    continue
                    
                # 2. Check if inside a Fixed Room (Blue Square)
                if fixed_union and fixed_union.contains(pt):
                    continue # Don't put fill points inside fixed rooms
                    
                points.append((pt.x, pt.y))
                
        return np.array(points) if points else np.empty((0, 2))

    def _classify_and_filter_cells(
        self,
        all_voronoi_cells: List[Polygon],
        fixed_shapes: Dict[str, Polygon]
    ) -> List[Polygon]:
        """Filter out internal cells and clip boundary cells."""
        fixed_union = unary_union(list(fixed_shapes.values())) if fixed_shapes else None
        fill_cells = []
        
        for poly in all_voronoi_cells:
            if poly.is_empty or poly.area < 1.0:
                continue
            
            center = poly.centroid
            
            # Check if cell center is inside any fixed shape
            if fixed_union and fixed_union.contains(center):
                # This cell is INSIDE a fixed shape - discard
                continue
            else:
                # External or boundary cell - keep it
                # If it overlaps fixed shapes, clip it
                if fixed_union and poly.intersects(fixed_union):
                    try:
                        clipped = poly.difference(fixed_union)
                        if clipped.is_empty or clipped.area < 1.0:
                            continue
                        
                        # Handle MultiPolygon result
                        if isinstance(clipped, MultiPolygon):
                            clipped = max(clipped.geoms, key=lambda p: p.area)
                        
                        if isinstance(clipped, Polygon) and clipped.area >= 1.0:
                            fill_cells.append(clipped)
                    except Exception:
                        continue
                else:
                    # Pure fill cell - no overlap with fixed shapes
                    fill_cells.append(poly)
                    
        return fill_cells

    def _merge_vertices_into_fixed_shapes(
        self,
        fixed_shapes: Dict[str, Polygon],
        fill_cells: List[Polygon]
    ) -> Dict[str, Polygon]:
        """
        Subdivide fixed shape edges to include vertices from adjacent Voronoi cells.
        This ensures proper shared edges (linedefs) in the final map.
        """
        modified_fixed_shapes = {}
        
        for name, original_shape in fixed_shapes.items():
            # Collect all vertices where Voronoi cells touch this fixed shape
            boundary_vertices = set()
            
            # Get original corner vertices
            original_coords = list(original_shape.exterior.coords[:-1])
            for coord in original_coords:
                boundary_vertices.add((round(coord[0], 3), round(coord[1], 3)))
            
            # Extract vertices from clipped Voronoi cells that share edges with this shape
            for fill_cell in fill_cells:
                shared_edge = fill_cell.intersection(original_shape.boundary)
                
                if not shared_edge.is_empty and hasattr(shared_edge, 'length') and shared_edge.length > 0.1:
                    if shared_edge.geom_type == 'LineString':
                        for coord in shared_edge.coords:
                            boundary_vertices.add((round(coord[0], 3), round(coord[1], 3)))
                    elif shared_edge.geom_type == 'MultiLineString':
                        for line in shared_edge.geoms:
                            for coord in line.coords:
                                boundary_vertices.add((round(coord[0], 3), round(coord[1], 3)))
            
            # Rebuild polygon if we found new vertices
            if len(boundary_vertices) > len(original_coords):
                new_coords = self._insert_vertices_into_polygon(original_coords, boundary_vertices)
                refined_shape = Polygon(new_coords)
                
                if refined_shape.is_valid and not refined_shape.is_empty:
                    modified_fixed_shapes[name] = refined_shape
                else:
                    modified_fixed_shapes[name] = original_shape
            else:
                modified_fixed_shapes[name] = original_shape
                
        return modified_fixed_shapes

    def _insert_vertices_into_polygon(
        self,
        original_coords: List[Tuple[float, float]],
        boundary_vertices: Set[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """Helper to insert vertices into polygon edges in correct order."""
        new_coords = []
        
        for i in range(len(original_coords)):
            p1 = original_coords[i]
            p2 = original_coords[(i + 1) % len(original_coords)]
            
            # Add corner vertex
            new_coords.append(p1)
            
            # Find vertices that lie on this edge
            edge_vertices = []
            for v in boundary_vertices:
                # Check if vertex lies on line segment p1-p2
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                edge_length = (dx*dx + dy*dy) ** 0.5
                
                if edge_length > 0.01:
                    vx = v[0] - p1[0]
                    vy = v[1] - p1[1]
                    
                    # Cross product (should be ~0 if collinear)
                    cross = abs(dx * vy - dy * vx)
                    # Dot product to check if between p1 and p2
                    dot = (vx * dx + vy * dy) / edge_length
                    
                    if cross < 0.1 and 0.01 < dot < edge_length - 0.01:
                        edge_vertices.append((dot, v))
            
            # Sort vertices by distance from p1 and add them
            edge_vertices.sort(key=lambda x: x[0])
            for _, v in edge_vertices:
                new_coords.append(v)
                
        return new_coords

    def _build_cell_dictionary(
        self,
        fixed_shapes: Dict[str, Polygon],
        fill_cells: List[Polygon]
    ) -> Tuple[Dict[int, VoronoiCell], Set[int], Set[int]]:
        """Construct the final dictionary of VoronoiCells."""
        cells = {}
        fixed_cell_ids = set()
        fill_cell_ids = set()
        
        cell_id = 0
        
        # Add fixed cells
        for name, shape in fixed_shapes.items():
            center = shape.centroid
            cells[cell_id] = VoronoiCell(
                id=cell_id,
                polygon=shape,
                cell_type=CellType.FIXED,
                center=(center.x, center.y)
            )
            fixed_cell_ids.add(cell_id)
            cell_id += 1
        
        # Add fill cells
        for poly in fill_cells:
            if poly.is_empty or poly.area < 1.0:
                continue
            center = poly.centroid
            cells[cell_id] = VoronoiCell(
                id=cell_id,
                polygon=poly,
                cell_type=CellType.FILL,
                center=(center.x, center.y)
            )
            fill_cell_ids.add(cell_id)
            cell_id += 1
            
        return cells, fixed_cell_ids, fill_cell_ids

    def _create_fallback_result(
        self,
        fixed_shapes: Dict[str, Polygon],
        bounds: Polygon,
        errors: List[str]
    ) -> VoronoiResult:
        """Create a result containing only fixed shapes when generation fails."""
        cells = {}
        for i, (name, shape) in enumerate(fixed_shapes.items()):
            center = shape.centroid
            cells[i] = VoronoiCell(
                id=i,
                polygon=shape,
                cell_type=CellType.FIXED,
                center=(center.x, center.y)
            )
        return VoronoiResult(
            cells=cells,
            fixed_cell_ids=set(cells.keys()),
            fill_cell_ids=set(),
            bounds=bounds,
            errors=errors
        )

    def _poisson_disc_sampling(
        self,
        region: Polygon,
        min_distance: float,
        num_attempts: int = 1000
    ) -> np.ndarray:
        """
        Generate Poisson disc samples within a polygon region.
        Uses rejection sampling with spatial grid acceleration.
        """
        minx, miny, maxx, maxy = region.bounds
        
        # Grid cell size
        cell_size = min_distance / np.sqrt(2)
        
        # Grid for fast neighbor lookup
        grid = {}
        points = []
        
        # Start with random point in region
        for _ in range(num_attempts):
            x = self.rng.uniform(minx, maxx)
            y = self.rng.uniform(miny, maxy)
            pt = Point(x, y)
            if region.contains(pt):
                points.append(np.array([x, y]))
                gx = int((x - minx) / cell_size)
                gy = int((y - miny) / cell_size)
                grid[(gx, gy)] = len(points) - 1
                break
        
        if not points:
            return np.array([])
        
        # Active list for generating new points
        active = [0]
        
        while active and len(points) < num_attempts:
            idx = self.rng.choice(len(active))
            active_idx = active[idx]
            px, py = points[active_idx]
            
            found = False
            for _ in range(30):
                angle = self.rng.uniform(0, 2 * np.pi)
                radius = self.rng.uniform(min_distance, 2 * min_distance)
                x = px + radius * np.cos(angle)
                y = py + radius * np.sin(angle)
                
                if not (minx <= x < maxx and miny <= y < maxy):
                    continue
                
                pt = Point(x, y)
                if not region.contains(pt):
                    continue
                
                gx = int((x - minx) / cell_size)
                gy = int((y - miny) / cell_size)
                
                too_close = False
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        ngx, ngy = gx + dx, gy + dy
                        if (ngx, ngy) in grid:
                            neighbor_idx = grid[(ngx, ngy)]
                            nx, ny = points[neighbor_idx]
                            dist = np.sqrt((x - nx)**2 + (y - ny)**2)
                            if dist < min_distance:
                                too_close = True
                                break
                    if too_close:
                        break
                
                if not too_close:
                    points.append(np.array([x, y]))
                    grid[(gx, gy)] = len(points) - 1
                    active.append(len(points) - 1)
                    found = True
                    break
            
            if not found:
                active.pop(idx)
        
        return np.array(points) if points else np.array([])
    
    def _lloyds_relaxation(
        self,
        points: np.ndarray,
        region: Polygon,
        iterations: int = 3
    ) -> np.ndarray:
        """Apply Lloyd's relaxation to make cells more uniform."""
        if len(points) < 3:
            return points
        
        for _ in range(iterations):
            try:
                vor = Voronoi(points)
            except Exception:
                break
            
            new_points = []
            for i, point_idx in enumerate(vor.point_region):
                region_idx = point_idx
                vertex_indices = vor.regions[region_idx]
                
                if -1 in vertex_indices or len(vertex_indices) == 0:
                    new_points.append(points[i])
                    continue
                
                vertices = [vor.vertices[vi] for vi in vertex_indices]
                cell_poly = Polygon(vertices)
                
                try:
                    clipped = cell_poly.intersection(region)
                    if clipped.is_empty:
                        new_points.append(points[i])
                        continue
                    
                    if isinstance(clipped, MultiPolygon):
                        clipped = max(clipped.geoms, key=lambda p: p.area)
                    
                    centroid = clipped.centroid
                    if region.contains(centroid):
                        new_points.append(np.array([centroid.x, centroid.y]))
                    else:
                        new_points.append(points[i])
                except Exception:
                    new_points.append(points[i])
            
            points = np.array(new_points)
        
        return points
    
    def _voronoi_to_polygons(
        self,
        vor: Voronoi,
        clip_region: Polygon
    ) -> List[Polygon]:
        """Convert scipy Voronoi diagram to clipped polygons."""
        polygons = []
        
        minx, miny, maxx, maxy = clip_region.bounds
        buffer = max(maxx - minx, maxy - miny) * 2
        far_box = box(minx - buffer, miny - buffer, maxx + buffer, maxy + buffer)
        
        for point_idx in range(len(vor.points)):
            region_idx = vor.point_region[point_idx]
            vertex_indices = vor.regions[region_idx]
            
            if len(vertex_indices) == 0:
                continue
            
            if -1 in vertex_indices:
                poly = self._infinite_voronoi_region(vor, point_idx, far_box)
            else:
                vertices = [vor.vertices[vi] for vi in vertex_indices]
                poly = Polygon(vertices)
            
            if poly is None or poly.is_empty:
                continue
            
            try:
                clipped = poly.intersection(clip_region)
                if clipped.is_empty:
                    continue
                
                if isinstance(clipped, MultiPolygon):
                    clipped = max(clipped.geoms, key=lambda p: p.area)
                
                if clipped.area > 1.0:
                    polygons.append(make_valid(clipped))
            except Exception:
                continue
        
        return polygons
    
    def _infinite_voronoi_region(
        self,
        vor: Voronoi,
        point_idx: int,
        far_box: Polygon
    ) -> Optional[Polygon]:
        """Construct polygon for infinite Voronoi region."""
        region_idx = vor.point_region[point_idx]
        vertex_indices = vor.regions[region_idx]
        
        if len(vertex_indices) == 0:
            return None
        
        finite_vertices = []
        for vi in vertex_indices:
            if vi != -1:
                finite_vertices.append(vor.vertices[vi])
        
        if len(finite_vertices) < 2:
            return None
        
        if len(finite_vertices) >= 3:
            try:
                poly = Polygon(finite_vertices)
                return poly.intersection(far_box)
            except Exception:
                return None
        
        return None
    
    def _build_adjacency_graph(self, cells: Dict[int, VoronoiCell]) -> None:
        """Build adjacency graph by detecting shared edges between cells."""
        cell_list = list(cells.values())
        
        for i, cell_a in enumerate(cell_list):
            for cell_b in cell_list[i + 1:]:
                try:
                    intersection = cell_a.polygon.intersection(cell_b.polygon)
                    
                    if not intersection.is_empty:
                        if intersection.geom_type == 'LineString':
                            cell_a.neighbors.add(cell_b.id)
                            cell_b.neighbors.add(cell_a.id)
                            cell_a.ridges[cell_b.id] = intersection
                            cell_b.ridges[cell_a.id] = intersection
                            continue
                        elif intersection.geom_type == 'MultiLineString':
                            longest = max(intersection.geoms, key=lambda ls: ls.length)
                            if longest.length > 1.0:
                                cell_a.neighbors.add(cell_b.id)
                                cell_b.neighbors.add(cell_a.id)
                                cell_a.ridges[cell_b.id] = longest
                                cell_b.ridges[cell_a.id] = longest
                                continue
                    
                    # Proximity check for fixed-fill adjacency gaps
                    distance = cell_a.polygon.distance(cell_b.polygon)
                    if distance < 0.1:
                        cell_a.neighbors.add(cell_b.id)
                        cell_b.neighbors.add(cell_a.id)
                        
                except Exception:
                    continue
