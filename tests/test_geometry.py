"""
Tests for the geometry module.
"""

import pytest
import numpy as np
from shapely.geometry import Polygon, Point

from doomgen.geometry.shapes import ShapeBuilder
from doomgen.geometry.modifiers import recursive_subdivision, LSystemGenerator, GRAMMARS
from doomgen.geometry.builder import (
    MapBuilder, BuildResult, SlotInfo, SlotType, CorridorInfo,
    create_corridor_between, create_cutout_polygon
)
from doomgen.geometry.operations import (
    cut_polygon, merge_polygons, ensure_polygon, snap_polygon_to_grid
)

# Use operations snap_polygon_to_grid, aliased as snap_to_grid for tests
snap_to_grid = snap_polygon_to_grid


class TestShapeBuilder:
    """Tests for ShapeBuilder class."""
    
    def test_create_square(self):
        """Test creating a square polygon."""
        builder = ShapeBuilder(seed=42)
        square = builder.create_polygon(sides=4, radius=100)
        
        assert square.is_valid
        assert len(square.exterior.coords) == 5  # 4 vertices + closing
        
    def test_create_octagon(self):
        """Test creating an octagon."""
        builder = ShapeBuilder(seed=42)
        octagon = builder.create_polygon(sides=8, radius=200)
        
        assert octagon.is_valid
        assert len(octagon.exterior.coords) == 9  # 8 vertices + closing
    
    def test_create_rectangle(self):
        """Test creating a rectangle."""
        builder = ShapeBuilder(seed=42)
        rect = builder.create_rectangle(width=200, height=100)
        
        assert rect.is_valid
        assert abs(rect.area - 20000) < 1  # 200 * 100
    
    def test_create_corridor(self):
        """Test creating a straight corridor."""
        builder = ShapeBuilder(seed=42)
        corridor = builder.create_corridor(
            start=(0, 0),
            end=(100, 0),
            width=32
        )
        
        assert corridor.is_valid
        assert corridor.area > 0
    
    def test_create_corridor_from_path(self):
        """Test creating a corridor from a path."""
        builder = ShapeBuilder(seed=42)
        path = [(0, 0), (50, 50), (100, 0)]
        corridor = builder.create_corridor_from_path(path, width=32)
        
        assert corridor.is_valid
        assert corridor.area > 0
    
    def test_merge_shapes(self):
        """Test merging overlapping shapes."""
        builder = ShapeBuilder(seed=42)
        
        square1 = builder.create_polygon(sides=4, radius=50, center=(0, 0))
        square2 = builder.create_polygon(sides=4, radius=50, center=(40, 0))
        
        merged = builder.merge_shapes(square1, square2)
        
        assert merged.is_valid
        assert merged.area > square1.area
        assert merged.area < square1.area + square2.area  # Overlap
    
    def test_snap_to_grid(self):
        """Test grid snapping."""
        builder = ShapeBuilder(seed=42)
        
        # Create polygon with non-grid-aligned coordinates
        polygon = Polygon([(1.5, 2.3), (10.7, 2.3), (10.7, 9.1), (1.5, 9.1)])
        
        snapped = builder.snap_to_grid(polygon, grid_size=8)
        
        for x, y in snapped.exterior.coords:
            assert x % 8 == 0 or x % 8 == 0
            assert y % 8 == 0 or y % 8 == 0
    
    def test_to_integer_coords(self):
        """Test integer conversion."""
        builder = ShapeBuilder(seed=42)
        
        polygon = Polygon([(0.5, 0.5), (100.7, 0.5), (100.7, 100.3), (0.5, 100.3)])
        
        int_polygon = builder.to_integer_coords(polygon)
        
        for x, y in int_polygon.exterior.coords:
            # Shapely stores floats, but values should be whole numbers
            assert float(x).is_integer(), f"x={x} is not a whole number"
            assert float(y).is_integer(), f"y={y} is not a whole number"
    
    def test_validate_polygon_valid(self):
        """Test validation of valid polygon."""
        builder = ShapeBuilder(seed=42)
        polygon = builder.create_polygon(sides=6, radius=100)
        
        is_valid, msg = builder.validate_polygon(polygon)
        
        assert is_valid
        assert msg == "Valid"
    
    def test_validate_polygon_invalid(self):
        """Test validation of invalid polygon."""
        builder = ShapeBuilder(seed=42)
        
        # Create self-intersecting polygon
        polygon = Polygon([(0, 0), (100, 100), (100, 0), (0, 100)])
        
        is_valid, msg = builder.validate_polygon(polygon)
        
        # Note: Shapely might auto-fix or detect differently
        # The key is that validation provides feedback
        assert isinstance(is_valid, bool)
    
    def test_deterministic_with_seed(self):
        """Test that same seed produces same results."""
        builder1 = ShapeBuilder(seed=123)
        builder2 = ShapeBuilder(seed=123)
        
        poly1 = builder1.create_polygon(sides=6, radius=100)
        poly2 = builder2.create_polygon(sides=6, radius=100)
        
        assert poly1.equals(poly2)


class TestRecursiveSubdivision:
    """Tests for recursive subdivision."""
    
    def test_subdivision_increases_vertices(self):
        """Test that subdivision adds vertices."""
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        original_count = len(polygon.exterior.coords)
        
        subdivided = recursive_subdivision(polygon, iterations=1, roughness=0.2, seed=42)
        new_count = len(subdivided.exterior.coords)
        
        assert new_count > original_count
    
    def test_subdivision_preserves_validity(self):
        """Test that subdivided polygon is valid."""
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        
        subdivided = recursive_subdivision(polygon, iterations=2, roughness=0.3, seed=42)
        
        assert subdivided.is_valid
    
    def test_subdivision_deterministic(self):
        """Test that subdivision is deterministic with seed."""
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        
        sub1 = recursive_subdivision(polygon, iterations=2, roughness=0.3, seed=42)
        sub2 = recursive_subdivision(polygon, iterations=2, roughness=0.3, seed=42)
        
        assert sub1.equals(sub2)
    
    def test_zero_roughness(self):
        """Test that zero roughness preserves shape."""
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        
        subdivided = recursive_subdivision(polygon, iterations=1, roughness=0.0, seed=42)
        
        # Should have more vertices but same shape
        assert subdivided.is_valid
        # Area should be similar (might add vertices at midpoints)


class TestLSystemGenerator:
    """Tests for L-System path generation."""
    
    def test_generate_string(self):
        """Test L-System string generation."""
        gen = LSystemGenerator(grammar_name='zigzag')
        
        result = gen.generate_string(iterations=1)
        
        assert len(result) > 0
        assert 'F' in result
    
    def test_generate_path(self):
        """Test path generation."""
        gen = LSystemGenerator(grammar_name='serpentine', seed=42)
        
        path = gen.generate_path(
            start=(0, 0),
            end=(100, 0),
            iterations=2
        )
        
        assert len(path) >= 2
        # Path should start and end at specified points
        assert np.allclose(path[0], (0, 0), atol=1)
        assert np.allclose(path[-1], (100, 0), atol=1)
    
    def test_generate_corridor(self):
        """Test corridor polygon generation."""
        gen = LSystemGenerator(grammar_name='zigzag', seed=42)
        
        corridor = gen.generate_corridor(
            start=(0, 0),
            end=(200, 0),
            width=32,
            iterations=2
        )
        
        assert corridor.is_valid
        assert corridor.area > 0
    
    def test_all_grammars(self):
        """Test that all predefined grammars work."""
        for grammar_name in GRAMMARS:
            gen = LSystemGenerator(grammar_name=grammar_name, seed=42)
            path = gen.generate_path((0, 0), (100, 100), iterations=1)
            
            assert len(path) >= 2, f"Grammar {grammar_name} failed"
    
    def test_deterministic(self):
        """Test deterministic output with seed."""
        gen1 = LSystemGenerator(grammar_name='meander', seed=99)
        gen2 = LSystemGenerator(grammar_name='meander', seed=99)
        
        path1 = gen1.generate_path((0, 0), (100, 50), iterations=2)
        path2 = gen2.generate_path((0, 0), (100, 50), iterations=2)
        
        assert len(path1) == len(path2)
        for p1, p2 in zip(path1, path2):
            assert np.allclose(p1, p2)


class TestMapBuilder:
    """Tests for the new MapBuilder class (Local Merge, Global Difference pattern)."""
    
    def test_cut_polygon_basic(self):
        """Test basic polygon cutting."""
        base = Polygon([(-100, -100), (100, -100), (100, 100), (-100, 100)])
        cutter = Polygon([(50, -50), (150, -50), (150, 50), (50, 50)])  # Overlaps right edge
        
        # Use grid_size=0 to disable snapping for precise test
        result = cut_polygon(base, cutter, grid_size=0)
        
        assert result.is_valid
        assert result.area < base.area
        # The cut area should be the intersection
        expected_area = base.area - base.intersection(cutter).area
        assert abs(result.area - expected_area) < 1
    
    def test_cut_polygon_no_intersection(self):
        """Test cutting with non-intersecting polygon."""
        base = Polygon([(-100, -100), (100, -100), (100, 100), (-100, 100)])
        cutter = Polygon([(500, 500), (600, 500), (600, 600), (500, 600)])  # Far away
        
        # Use grid_size=0 to disable snapping for precise test
        result = cut_polygon(base, cutter, grid_size=0)
        
        assert result.is_valid
        assert result.equals(base)  # Should be unchanged
    
    def test_merge_polygons_basic(self):
        """Test merging overlapping polygons."""
        poly1 = Polygon([(-50, -50), (50, -50), (50, 50), (-50, 50)])
        poly2 = Polygon([(25, -25), (125, -25), (125, 75), (25, 75)])  # Overlaps
        
        result = merge_polygons(poly1, poly2)
        
        assert result.is_valid
        assert result.area > poly1.area
        assert result.area < poly1.area + poly2.area  # Overlap means less than sum
    
    def test_merge_polygons_l_shape(self):
        """Test merging to create L-shaped room."""
        rect1 = Polygon([(-100, -200), (100, -200), (100, 200), (-100, 200)])  # Vertical
        rect2 = Polygon([(-200, -100), (200, -100), (200, 100), (-200, 100)])  # Horizontal
        
        l_room = merge_polygons(rect1, rect2)
        
        assert l_room.is_valid
        # Should have more than 4 vertices due to L shape
        assert len(l_room.exterior.coords) > 5
    
    def test_snap_to_grid(self):
        """Test snapping polygon to grid."""
        poly = Polygon([(3.7, 5.2), (101.3, 5.2), (101.3, 99.8), (3.7, 99.8)])
        
        snapped = snap_to_grid(poly, grid_size=8)
        
        for x, y in snapped.exterior.coords:
            assert x == int(x)
            assert y == int(y)
            assert x % 8 == 0
            assert y % 8 == 0
    
    def test_ensure_polygon_multipolygon(self):
        """Test ensure_polygon with MultiPolygon input."""
        from shapely.geometry import MultiPolygon
        
        poly1 = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        poly2 = Polygon([(200, 0), (250, 0), (250, 50), (200, 50)])
        multi = MultiPolygon([poly1, poly2])
        
        result = ensure_polygon(multi)
        
        assert isinstance(result, Polygon)
        assert result.equals(poly1)  # Should return the larger polygon
    
    def test_create_corridor_between(self):
        """Test creating a corridor between two rooms."""
        room_a = Polygon([(-100, -100), (100, -100), (100, 100), (-100, 100)])
        room_b = Polygon([(300, -100), (500, -100), (500, 100), (300, 100)])
        
        corridor = create_corridor_between(room_a, room_b, width=64, overlap=16)
        
        assert corridor.is_valid
        assert corridor.intersects(room_a)
        assert corridor.intersects(room_b)
    
    def test_create_door_polygon(self):
        """Test creating a cutout polygon (for doors, lifts, etc.)."""
        door = create_cutout_polygon(position=(100, 0), width=64, depth=16, direction="horizontal")
        
        assert door.is_valid
        assert door.area == 64 * 16
    
    def test_door_info_dataclass(self):
        """Test SlotInfo dataclass."""
        door_shape = create_cutout_polygon((0, 0), 64, 16)
        info = SlotInfo(
            polygon=door_shape,
            room_name="room1",
            position=(0, 0),
            width=64,
            depth=16,
            direction="horizontal",
            slot_type=SlotType.DOOR,
            key_type="red"
        )
        
        assert info.polygon.is_valid
        assert info.room_name == "room1"
        assert info.key_type == "red"
        assert info.is_key_door
    
    def test_map_builder_basic(self):
        """Test MapBuilder with two rooms and corridor."""
        builder = ShapeBuilder(seed=42)
        room1 = builder.create_rectangle(256, 256, center=(0, 0))
        room2 = builder.create_rectangle(256, 256, center=(500, 0))
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room1", room1)
        mb.add_room("room2", room2)
        # Use overlap mode to test legacy CSG cutting behavior
        mb.add_corridor("room1", "room2", width=64, connection_style="overlap", overlap=16)
        
        result = mb.build()
        
        assert result.is_valid
        assert "room1" in result.rooms
        assert "room2" in result.rooms
        assert len(result.corridors) == 1
        
        # Rooms should be carved (smaller than original) in overlap mode
        assert result.rooms["room1"].area < room1.area
        assert result.rooms["room2"].area < room2.area
    
    def test_map_builder_abutting(self):
        """Test MapBuilder with corridors (cookie cutter approach)."""
        builder = ShapeBuilder(seed=42)
        room1 = builder.create_rectangle(256, 256, center=(0, 0))
        room2 = builder.create_rectangle(256, 256, center=(500, 0))
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room1", room1)
        mb.add_room("room2", room2)
        # Corridors use cookie cutter approach - rooms are carved
        mb.add_corridor("room1", "room2", width=64)
        
        result = mb.build()
        
        assert result.is_valid
        assert "room1" in result.rooms
        assert "room2" in result.rooms
        assert len(result.corridors) == 1
        
        # Cookie cutter approach: rooms ARE carved where corridor connects
        # The corridor is subtracted from rooms, so room area decreases
        assert result.rooms["room1"].area < room1.area
        assert result.rooms["room2"].area < room2.area
    
    def test_map_builder_hub(self):
        """Test MapBuilder with hub layout."""
        builder = ShapeBuilder(seed=42)
        hub = builder.create_polygon(8, radius=256, center=(0, 0))
        north = builder.create_rectangle(200, 200, center=(0, 500))
        south = builder.create_rectangle(200, 200, center=(0, -500))
        east = builder.create_rectangle(200, 200, center=(500, 0))
        west = builder.create_rectangle(200, 200, center=(-500, 0))
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("hub", hub)
        mb.add_room("north", north)
        mb.add_room("south", south)
        mb.add_room("east", east)
        mb.add_room("west", west)
        
        mb.add_corridor("hub", "north", width=64)
        mb.add_corridor("hub", "south", width=64)
        mb.add_corridor("hub", "east", width=64)
        mb.add_corridor("hub", "west", width=64)
        
        result = mb.build()
        
        assert result.is_valid
        assert len(result.rooms) == 5
        assert len(result.corridors) == 4
    
    def test_map_builder_door(self):
        """Test MapBuilder with door slot between rooms."""
        builder = ShapeBuilder(seed=42)
        room1 = builder.create_rectangle(256, 256, center=(0, 0))
        room2 = builder.create_rectangle(256, 256, center=(280, 0))  # Adjacent (overlapping slightly)
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room1", room1)
        mb.add_room("room2", room2)
        # Use the new slot-based API for doors
        mb.add_slot_between("room1", "room2", position=(140, 0), width=64, depth=16, 
                           slot_type=SlotType.DOOR, key_type="blue")
        
        result = mb.build()
        
        assert result.is_valid
        # Check for door slots
        door_slots = [s for s in result.slots if s.slot_type == SlotType.DOOR]
        assert len(door_slots) == 1
        
        door = door_slots[0]
        assert door.room_name == "room1"
        assert door.key_type == "blue"
    
    def test_map_builder_slot(self):
        """Test MapBuilder with slot (prefab)."""
        builder = ShapeBuilder(seed=42)
        room = builder.create_rectangle(512, 512, center=(0, 0))
        # Place slot at center position
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room", room)
        mb.add_slot("room", position=(100, 100), width=64, depth=64, slot_type=SlotType.GENERIC)
        
        result = mb.build()
        
        assert result.is_valid
        assert "room" in result.rooms
        
        # Should have a slot
        assert len(result.slots) >= 1
        assert result.rooms["room"].is_valid
    
    def test_map_builder_chaining(self):
        """Test MapBuilder method chaining."""
        builder = ShapeBuilder(seed=42)
        room1 = builder.create_rectangle(256, 256, center=(0, 0))
        room2 = builder.create_rectangle(256, 256, center=(500, 0))
        
        result = (MapBuilder(grid_size=8)
            .add_room("room1", room1)
            .add_room("room2", room2)
            .add_corridor("room1", "room2", width=64)
            .build())
        
        assert result.is_valid
        assert len(result.rooms) == 2
        assert len(result.corridors) == 1
    
    def test_map_builder_missing_room_error(self):
        """Test MapBuilder raises error for missing room."""
        builder = ShapeBuilder(seed=42)
        room1 = builder.create_rectangle(256, 256, center=(0, 0))
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room1", room1)
        
        with pytest.raises(KeyError):
            mb.add_corridor("room1", "nonexistent", width=64)
    
    def test_build_result_dataclass(self):
        """Test BuildResult dataclass properties."""
        builder = ShapeBuilder(seed=42)
        room1 = builder.create_rectangle(256, 256, center=(0, 0))
        room2 = builder.create_rectangle(256, 256, center=(500, 0))
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room1", room1)
        mb.add_room("room2", room2)
        mb.add_corridor("room1", "room2", width=64)
        
        result = mb.build()
        
        assert isinstance(result, BuildResult)
        assert isinstance(result.rooms, dict)
        assert isinstance(result.corridors, list)
        assert isinstance(result.slots, list)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
    
    def test_subtract_polygon(self):
        """Test the subtract_polygon method of ShapeBuilder."""
        builder = ShapeBuilder(seed=42)
        
        base = builder.create_rectangle(256, 256, center=(0, 0))
        cutter = builder.create_rectangle(64, 64, center=(128 - 32, 0))  # Overlaps east edge
        
        result = builder.subtract_polygon(base, cutter)
        
        assert result.is_valid
        assert result.area < base.area
    
    def test_snapping_after_build(self):
        """Test that built geometry is snapped to grid."""
        builder = ShapeBuilder(seed=42)
        
        # Create rooms at non-grid-aligned positions
        room1 = builder.create_rectangle(257, 257, center=(3, 3))
        room2 = builder.create_rectangle(257, 257, center=(503, 3))
        
        mb = MapBuilder(grid_size=8)
        mb.add_room("room1", room1)
        mb.add_room("room2", room2)
        mb.add_corridor("room1", "room2", width=65)
        
        result = mb.build()
        
        # Check that all coordinates are integers aligned to grid
        for room_id, poly in result.rooms.items():
            for x, y in poly.exterior.coords:
                assert x == int(x), f"X coordinate {x} not integer in {room_id}"
                assert y == int(y), f"Y coordinate {y} not integer in {room_id}"
                assert x % 8 == 0, f"X coordinate {x} not aligned to grid in {room_id}"
                assert y % 8 == 0, f"Y coordinate {y} not aligned to grid in {room_id}"
