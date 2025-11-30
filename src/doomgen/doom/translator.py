"""
MapEditor - Doom geometry translator.

Converts abstract Shapely geometry into Doom-specific structures
(vertices, linedefs, sidedefs, sectors).
"""

from __future__ import annotations

from typing import Optional, Tuple, List
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from shapely.validation import make_valid

from doomgen.doom.wad import DoomMapData
from doomgen.doom.tags import TagRegistry
from doomgen.doom.things import ThingType
from doomgen.doom.specials import LinedefFlags


COORD_TOLERANCE = 1.0


def snap_polygon_to_grid(polygon: Polygon, grid_size: int = 1) -> Polygon:
    """
    Snap all polygon coordinates to an integer grid.
    
    This is critical for ensuring that adjacent polygons share exactly
    the same edge coordinates, which is required for proper two-sided
    linedef creation in Doom.
    
    Args:
        polygon: The polygon to snap.
        grid_size: Grid size for snapping (default 1 = integer coordinates).
    
    Returns:
        A new polygon with all coordinates snapped to the grid.
    """
    def snap_coords(coords):
        return [(int(round(x / grid_size) * grid_size), 
                 int(round(y / grid_size) * grid_size)) for x, y in coords]
    
    # Snap exterior ring
    exterior_snapped = snap_coords(polygon.exterior.coords)
    
    # Snap interior rings (holes)
    interiors_snapped = [snap_coords(interior.coords) for interior in polygon.interiors]
    
    return Polygon(exterior_snapped, interiors_snapped)


@dataclass
class SectorConfig:
    """Sector properties: heights, textures, lighting."""
    floor_height: int = 0
    ceiling_height: int = 128
    floor_texture: str = 'FLOOR4_8'
    ceiling_texture: str = 'CEIL3_5'
    light_level: int = 160
    special: int = 0
    tag: int = 0


@dataclass
class WallConfig:
    """Wall texture configuration."""
    upper_texture: str = '-'
    middle_texture: str = 'STARTAN2'
    lower_texture: str = '-'
    x_offset: int = 0
    y_offset: int = 0


class MapEditor:
    """
    Converts Shapely polygons to Doom map structures.
    
    Handles vertex deduplication, linedef orientation, and shared edge
    detection for connected sectors.
    """
    
    def __init__(self, map_data: DoomMapData):
        """Initialize with a DoomMapData container to populate."""
        self.map_data = map_data
        self.tag_registry = TagRegistry()
        # (polygon, sector_index)
        self.sectors: list[tuple[Polygon, int]] = []
        # Edge registry maps edge -> (linedef_index, front_sector)
        self._edge_registry: dict[tuple[tuple[int, int], tuple[int, int]], tuple[int, int]] = {}
        # Store all edges with their geometric representation for shared edge detection
        self._geometric_edges: list[tuple[LineString, int, tuple[int, int], tuple[int, int]]] = []
    
    def _find_shared_edge(
        self,
        p1: tuple[int, int],
        p2: tuple[int, int]
    ) -> Optional[tuple[int, int, int]]:
        """
        Find if an edge shares geometry with an existing edge.
        
        Uses geometric comparison to handle floating point issues and
        the case where edges overlap but aren't exact coordinate matches.
        
        Args:
            p1: Start point of edge.
            p2: End point of edge.
        
        Returns:
            (linedef_index, original_sector, edge_direction) or None.
            edge_direction: 1 if same direction, -1 if reversed.
        """
        edge_line = LineString([p1, p2])
        
        for existing_line, linedef_idx, existing_p1, existing_p2 in self._geometric_edges:
            # Check if lines are collinear and overlapping
            if edge_line.distance(existing_line) < COORD_TOLERANCE:
                # Check if it's the same edge (possibly reversed)
                if (self._points_equal(p1, existing_p2) and 
                    self._points_equal(p2, existing_p1)):
                    # Reversed edge - this is the case for shared walls
                    front_sd = self.map_data.linedefs[linedef_idx].get('front_sidedef', -1)
                    original_sector = self.map_data.sidedefs[front_sd]['sector'] if front_sd >= 0 else -1
                    return (linedef_idx, original_sector, -1)
                elif (self._points_equal(p1, existing_p1) and 
                      self._points_equal(p2, existing_p2)):
                    # Same direction edge
                    front_sd = self.map_data.linedefs[linedef_idx].get('front_sidedef', -1)
                    original_sector = self.map_data.sidedefs[front_sd]['sector'] if front_sd >= 0 else -1
                    return (linedef_idx, original_sector, 1)
        
        return None
    
    def _points_equal(self, p1: tuple[int, int], p2: tuple[int, int]) -> bool:
        """Check if two points are equal within tolerance."""
        return abs(p1[0] - p2[0]) <= COORD_TOLERANCE and abs(p1[1] - p2[1]) <= COORD_TOLERANCE
    
    def add_sector_from_polygon(
        self,
        polygon: Polygon,
        config: Optional[SectorConfig] = None,
        wall_config: Optional[WallConfig] = None
    ) -> int:
        """
        Add a sector from a Shapely Polygon.
        
        This is the main method for converting abstract geometry to Doom.
        Automatically detects shared edges with existing sectors and creates
        two-sided linedefs for connections.
        
        Args:
            polygon: The sector geometry.
            config: Sector configuration (heights, textures, etc.).
            wall_config: Wall texture configuration.
        
        Returns:
            Index of the created sector.
        """
        if config is None:
            config = SectorConfig()
        if wall_config is None:
            wall_config = WallConfig()
        
        # CRITICAL: Snap polygon to integer grid FIRST
        # This ensures adjacent polygons share exactly the same edge coordinates
        polygon = snap_polygon_to_grid(polygon, grid_size=1)
        
        # Validate polygon
        if not polygon.is_valid:
            polygon = make_valid(polygon)
            # Re-snap after make_valid as it may introduce float coords
            if polygon.geom_type == 'Polygon':
                polygon = snap_polygon_to_grid(polygon, grid_size=1)
        
        if polygon.is_empty:
            raise ValueError("Cannot create sector from empty polygon")
        
        # Ensure we have a single polygon
        if polygon.geom_type == 'MultiPolygon':
            polygon = max(polygon.geoms, key=lambda p: p.area)
            polygon = snap_polygon_to_grid(polygon, grid_size=1)
        elif polygon.geom_type == 'GeometryCollection':
            # Extract the largest polygon from collection
            polys = [g for g in polygon.geoms if g.geom_type == 'Polygon']
            if not polys:
                raise ValueError("No valid polygon in geometry collection")
            polygon = max(polys, key=lambda p: p.area)
            polygon = snap_polygon_to_grid(polygon, grid_size=1)
        
        # Create the sector
        sector_index = self.map_data.add_sector(
            floor_height=config.floor_height,
            ceiling_height=config.ceiling_height,
            floor_texture=config.floor_texture,
            ceiling_texture=config.ceiling_texture,
            light_level=config.light_level,
            special=config.special,
            tag=config.tag
        )
        
        # Get coordinates and ensure clockwise winding for exterior
        coords = list(polygon.exterior.coords)
        
        # Shapely uses counter-clockwise for exterior, Doom expects clockwise
        # for sectors that face inward (player inside)
        if self._is_counter_clockwise(coords):
            coords = coords[::-1]
        
        # Add vertices and linedefs for exterior ring
        self._add_polygon_linedefs(coords, sector_index, wall_config)
        
        # Process interior rings (holes) - these are edges that face INTO the hole
        # Shapely interior rings are counter-clockwise, but we need them clockwise
        # so they face into the hole (and can be shared with sectors inside the hole)
        for interior in polygon.interiors:
            interior_coords = list(interior.coords)
            # Interior rings are already wound correctly in Shapely (opposite to exterior)
            # We want them clockwise so the linedef faces into the hole
            if not self._is_counter_clockwise(interior_coords):
                interior_coords = interior_coords[::-1]
            self._add_polygon_linedefs(interior_coords, sector_index, wall_config)
        
        # Track the sector
        self.sectors.append((polygon, sector_index))
        
        return sector_index
    
    def _add_polygon_linedefs(
        self,
        coords: list[tuple[float, float]],
        sector_index: int,
        wall_config: WallConfig
    ) -> None:
        """
        Add linedefs for a polygon's edges.
        
        Args:
            coords: List of (x, y) coordinates (closed polygon).
            sector_index: Index of the sector these lines belong to.
            wall_config: Wall texture configuration.
        """
        # Remove duplicate closing vertex if present
        if coords[0] == coords[-1]:
            coords = coords[:-1]
        
        num_vertices = len(coords)
        
        for i in range(num_vertices):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % num_vertices]
            
            # Snap to grid and convert to int
            x1, y1 = int(round(x1)), int(round(y1))
            x2, y2 = int(round(x2)), int(round(y2))
            
            # Skip degenerate edges
            if (x1, y1) == (x2, y2):
                continue
            
            # Add vertices
            v1 = self.map_data.add_vertex(x1, y1)
            v2 = self.map_data.add_vertex(x2, y2)
            
            # Check for shared edge using both exact match and geometric comparison
            edge_key = self._make_edge_key((x1, y1), (x2, y2))
            reverse_key = self._make_edge_key((x2, y2), (x1, y1))
            
            # First check exact match in registry
            shared_info = None
            if reverse_key in self._edge_registry:
                linedef_idx, orig_sector = self._edge_registry[reverse_key]
                shared_info = (linedef_idx, orig_sector, -1)
            else:
                # Try geometric comparison for near-matches
                shared_info = self._find_shared_edge((x1, y1), (x2, y2))
            
            if shared_info is not None:
                linedef_index, original_sector, direction = shared_info
                
                # Create new sidedef for this sector
                new_sidedef = self.map_data.add_sidedef(
                    sector=sector_index,
                    upper_texture=wall_config.upper_texture,
                    middle_texture='-',  # No middle texture for two-sided lines
                    lower_texture=wall_config.lower_texture,
                    x_offset=wall_config.x_offset,
                    y_offset=wall_config.y_offset
                )
                
                if direction == -1:
                    # Reversed edge - new sector becomes the back sidedef
                    # This is the normal case for properly wound adjacent polygons
                    self.map_data.linedefs[linedef_index]['back_sidedef'] = new_sidedef
                else:
                    # Same direction edge - need to flip the linedef
                    # The new sector should be the front (facing into its own sector)
                    # and the original sector becomes the back
                    existing_front_sd = self.map_data.linedefs[linedef_index]['front_sidedef']
                    
                    # Flip the linedef vertices
                    start_v = self.map_data.linedefs[linedef_index]['start_vertex']
                    end_v = self.map_data.linedefs[linedef_index]['end_vertex']
                    self.map_data.linedefs[linedef_index]['start_vertex'] = end_v
                    self.map_data.linedefs[linedef_index]['end_vertex'] = start_v
                    
                    # Now the original front becomes back, and new becomes front
                    self.map_data.linedefs[linedef_index]['front_sidedef'] = new_sidedef
                    self.map_data.linedefs[linedef_index]['back_sidedef'] = existing_front_sd
                
                # Set two-sided flag and remove middle texture from both sides
                self.map_data.linedefs[linedef_index]['flags'] = int(LinedefFlags.TWO_SIDED)
                
                front_sd = self.map_data.linedefs[linedef_index]['front_sidedef']
                back_sd = self.map_data.linedefs[linedef_index]['back_sidedef']
                self.map_data.sidedefs[front_sd]['middle_texture'] = '-'
                self.map_data.sidedefs[back_sd]['middle_texture'] = '-'
            else:
                # New edge - create linedef with front sidedef only
                front_sidedef = self.map_data.add_sidedef(
                    sector=sector_index,
                    upper_texture=wall_config.upper_texture,
                    middle_texture=wall_config.middle_texture,
                    lower_texture=wall_config.lower_texture,
                    x_offset=wall_config.x_offset,
                    y_offset=wall_config.y_offset
                )
                
                linedef_index = self.map_data.add_linedef(
                    start_vertex=v1,
                    end_vertex=v2,
                    front_sidedef=front_sidedef,
                    back_sidedef=-1,
                    flags=int(LinedefFlags.BLOCKING)
                )
                
                # Register this edge for future matching
                self._edge_registry[edge_key] = (linedef_index, sector_index)
                
                # Store geometric representation for near-match detection
                edge_line = LineString([(x1, y1), (x2, y2)])
                self._geometric_edges.append((edge_line, linedef_index, (x1, y1), (x2, y2)))
    
    def _make_edge_key(
        self,
        p1: tuple[int, int],
        p2: tuple[int, int]
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """Create a consistent key for an edge."""
        return (p1, p2)
    
    def _is_counter_clockwise(self, coords: list[tuple[float, float]]) -> bool:
        """
        Check if polygon coordinates are counter-clockwise.
        
        Uses the shoelace formula to calculate signed area.
        """
        if coords[0] == coords[-1]:
            coords = coords[:-1]
        
        total = 0.0
        n = len(coords)
        for i in range(n):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % n]
            total += (x2 - x1) * (y2 + y1)
        
        return total < 0
    
    def get_linedefs_for_sector(self, sector_index: int) -> List[int]:
        """
        Get all linedef indices that reference a sector.
        
        Args:
            sector_index: The sector to find linedefs for.
        
        Returns:
            List of linedef indices.
        """
        result = []
        for i, ld in enumerate(self.map_data.linedefs):
            front_sd = ld.get('front_sidedef', -1)
            back_sd = ld.get('back_sidedef', -1)
            
            if front_sd >= 0:
                if self.map_data.sidedefs[front_sd].get('sector', -1) == sector_index:
                    result.append(i)
                    continue
            if back_sd >= 0:
                if self.map_data.sidedefs[back_sd].get('sector', -1) == sector_index:
                    result.append(i)
        
        return result
    
    def get_two_sided_linedefs_for_sector(self, sector_index: int) -> List[int]:
        """
        Get two-sided linedef indices that connect a sector to other sectors.
        
        Args:
            sector_index: The sector to find connections for.
        
        Returns:
            List of two-sided linedef indices.
        """
        result = []
        for i, ld in enumerate(self.map_data.linedefs):
            front_sd = ld.get('front_sidedef', -1)
            back_sd = ld.get('back_sidedef', -1)
            
            # Must be two-sided
            if back_sd < 0:
                continue
            
            front_sector = self.map_data.sidedefs[front_sd].get('sector', -1) if front_sd >= 0 else -1
            back_sector = self.map_data.sidedefs[back_sd].get('sector', -1)
            
            if front_sector == sector_index or back_sector == sector_index:
                result.append(i)
        
        return result
    
    def modify_linedef(
        self,
        linedef_index: int,
        flags: Optional[int] = None,
        special: Optional[int] = None,
        tag: Optional[int] = None,
        add_flags: Optional[int] = None,
        remove_flags: Optional[int] = None
    ) -> None:
        """
        Modify properties of an existing linedef.
        
        Args:
            linedef_index: Index of the linedef to modify.
            flags: New flags value (replaces existing).
            special: New special/action value.
            tag: New tag value.
            add_flags: Flags to add (OR with existing).
            remove_flags: Flags to remove (AND NOT with existing).
        """
        if linedef_index < 0 or linedef_index >= len(self.map_data.linedefs):
            raise IndexError(f"Linedef {linedef_index} does not exist")
        
        ld = self.map_data.linedefs[linedef_index]
        
        if flags is not None:
            ld['flags'] = flags
        elif add_flags is not None or remove_flags is not None:
            current = ld.get('flags', 0)
            if add_flags:
                current |= add_flags
            if remove_flags:
                current &= ~remove_flags
            ld['flags'] = current
        
        if special is not None:
            ld['special'] = special
        
        if tag is not None:
            ld['tag'] = tag
    
    def modify_sidedef(
        self,
        sidedef_index: int,
        upper_texture: Optional[str] = None,
        middle_texture: Optional[str] = None,
        lower_texture: Optional[str] = None,
        x_offset: Optional[int] = None,
        y_offset: Optional[int] = None
    ) -> None:
        """
        Modify properties of an existing sidedef.
        
        Args:
            sidedef_index: Index of the sidedef to modify.
            upper_texture: New upper texture.
            middle_texture: New middle texture.
            lower_texture: New lower texture.
            x_offset: New X offset.
            y_offset: New Y offset.
        """
        if sidedef_index < 0 or sidedef_index >= len(self.map_data.sidedefs):
            raise IndexError(f"Sidedef {sidedef_index} does not exist")
        
        sd = self.map_data.sidedefs[sidedef_index]
        
        if upper_texture is not None:
            sd['upper_texture'] = upper_texture
        if middle_texture is not None:
            sd['middle_texture'] = middle_texture
        if lower_texture is not None:
            sd['lower_texture'] = lower_texture
        if x_offset is not None:
            sd['x_offset'] = x_offset
        if y_offset is not None:
            sd['y_offset'] = y_offset
    
    def add_thing(
        self,
        x: float,
        y: float,
        thing_type: int | ThingType,
        angle: int = 0,
        check_geometry: bool = True,
        check_collision: bool = False,
        tid: int = 0
    ) -> int:
        """
        Add a thing (entity) to the map.
        
        Args:
            x: X coordinate.
            y: Y coordinate.
            thing_type: Doom thing type ID or ThingType enum.
            angle: Facing angle in degrees.
            check_geometry: If True, verify thing is inside a sector.
            check_collision: If True, verify thing has clearance from walls.
            tid: Thing ID for ACS scripts (ZDoom/Hexen format).
        
        Returns:
            Index of the created thing.
        
        Raises:
            ValueError: If check_geometry is True and thing is outside all sectors.
        """
        from doomgen.doom.things import get_thing_radius
        
        thing_type_enum = thing_type if isinstance(thing_type, ThingType) else ThingType(thing_type)
        if isinstance(thing_type, ThingType):
            thing_type = thing_type.value
        
        if check_geometry or check_collision:
            point = Point(x, y)
            
            if check_collision:
                # Check that the thing's collision circle fits inside a sector
                radius = get_thing_radius(thing_type_enum)
                collision_circle = point.buffer(radius)
                inside_any = any(poly.contains(collision_circle) for poly, _ in self.sectors)
            else:
                inside_any = any(poly.contains(point) for poly, _ in self.sectors)
            
            if not inside_any:
                raise ValueError(f"Thing at ({x}, {y}) is outside all sectors or too close to walls")
        
        return self.map_data.add_thing(
            x=int(round(x)),
            y=int(round(y)),
            thing_type=thing_type,
            angle=angle,
            tid=tid
        )
    
    def add_player_start(
        self,
        x: float,
        y: float,
        angle: int = 0,
        player_num: int = 1
    ) -> int:
        """
        Add a player start position.
        
        Args:
            x: X coordinate.
            y: Y coordinate.
            angle: Facing angle in degrees.
            player_num: Player number (1-4 for coop).
        
        Returns:
            Index of the created thing.
        """
        thing_types = {
            1: ThingType.PLAYER1_START,
            2: ThingType.PLAYER2_START,
            3: ThingType.PLAYER3_START,
            4: ThingType.PLAYER4_START,
        }
        
        thing_type = thing_types.get(player_num, ThingType.PLAYER1_START)
        return self.add_thing(x, y, thing_type, angle)
    
    def merge_sectors(
        self,
        polygon1: Polygon,
        polygon2: Polygon,
        config: Optional[SectorConfig] = None,
        wall_config: Optional[WallConfig] = None
    ) -> int:
        """
        Merge two polygons and create a single sector.
        
        Uses Shapely's unary_union for boolean merge.
        
        Args:
            polygon1: First polygon.
            polygon2: Second polygon.
            config: Sector configuration.
            wall_config: Wall texture configuration.
        
        Returns:
            Index of the merged sector.
        """
        merged = unary_union([polygon1, polygon2])
        return self.add_sector_from_polygon(merged, config, wall_config)
    
    def get_sector_center(self, sector_index: int) -> tuple[float, float]:
        """
        Get the center point of a sector.
        
        Args:
            sector_index: Index of the sector.
        
        Returns:
            (x, y) coordinates of the sector centroid.
        """
        for polygon, idx in self.sectors:
            if idx == sector_index:
                centroid = polygon.centroid
                return (centroid.x, centroid.y)
        
        raise KeyError(f"Sector {sector_index} not found")
    
    def get_sector_polygon(self, sector_index: int) -> Polygon:
        """
        Get the polygon for a sector.
        
        Args:
            sector_index: Index of the sector.
        
        Returns:
            The Shapely Polygon for the sector.
        """
        for polygon, idx in self.sectors:
            if idx == sector_index:
                return polygon
        
        raise KeyError(f"Sector {sector_index} not found")
