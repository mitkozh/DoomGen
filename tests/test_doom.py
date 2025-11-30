"""
Tests for the Doom translator module.
"""

import pytest

from doomgen.doom.wad import DoomMapData
from doomgen.doom.translator import MapEditor, SectorConfig, WallConfig
from doomgen.doom.things import ThingType, get_thing_radius, EASY_ENEMIES
from doomgen.doom.tags import TagRegistry


class TestDoomMapData:
    """Tests for DoomMapData class."""
    
    def test_add_vertex(self):
        """Test adding vertices."""
        map_data = DoomMapData("MAP01")
        
        idx1 = map_data.add_vertex(100, 200)
        idx2 = map_data.add_vertex(300, 400)
        
        assert idx1 == 0
        assert idx2 == 1
        assert len(map_data.vertices) == 2
    
    def test_vertex_deduplication(self):
        """Test that duplicate vertices are reused."""
        map_data = DoomMapData("MAP01")
        
        idx1 = map_data.add_vertex(100, 200)
        idx2 = map_data.add_vertex(100, 200)  # Same coordinates
        
        assert idx1 == idx2
        assert len(map_data.vertices) == 1
    
    def test_add_sector(self):
        """Test adding a sector."""
        map_data = DoomMapData("MAP01")
        
        idx = map_data.add_sector(
            floor_height=0,
            ceiling_height=128,
            floor_texture='FLOOR4_8',
            light_level=160
        )
        
        assert idx == 0
        assert len(map_data.sectors) == 1
        assert map_data.sectors[0]['floor_height'] == 0
    
    def test_add_thing(self):
        """Test adding a thing."""
        map_data = DoomMapData("MAP01")
        
        idx = map_data.add_thing(
            x=256,
            y=512,
            thing_type=ThingType.PLAYER1_START,
            angle=90
        )
        
        assert idx == 0
        assert len(map_data.things) == 1
        assert map_data.things[0]['type'] == ThingType.PLAYER1_START


class TestMapEditor:
    """Tests for MapEditor class."""
    
    def test_create_from_polygon(self):
        """Test creating a sector from a polygon."""
        from shapely.geometry import Polygon
        
        map_data = DoomMapData("MAP01")
        editor = MapEditor(map_data)
        
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        sector_idx = editor.add_sector_from_polygon(polygon)
        
        assert sector_idx == 0
        assert len(map_data.sectors) == 1
        assert len(map_data.vertices) == 4
        assert len(map_data.linedefs) == 4
    
    def test_sector_config(self):
        """Test sector configuration."""
        from shapely.geometry import Polygon
        
        map_data = DoomMapData("MAP01")
        editor = MapEditor(map_data)
        
        config = SectorConfig(
            floor_height=24,
            ceiling_height=256,
            light_level=200
        )
        
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        editor.add_sector_from_polygon(polygon, config=config)
        
        assert map_data.sectors[0]['floor_height'] == 24
        assert map_data.sectors[0]['ceiling_height'] == 256
        assert map_data.sectors[0]['light_level'] == 200
    
    def test_add_thing_with_check(self):
        """Test thing placement with geometry check."""
        from shapely.geometry import Polygon
        
        map_data = DoomMapData("MAP01")
        editor = MapEditor(map_data)
        
        polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        editor.add_sector_from_polygon(polygon)
        
        # Thing inside polygon - should work
        idx = editor.add_thing(50, 50, ThingType.PLAYER1_START)
        assert idx == 0
        
        # Thing outside polygon - should raise
        with pytest.raises(ValueError):
            editor.add_thing(200, 200, ThingType.IMP)
    
    def test_add_player_start(self):
        """Test player start convenience method."""
        from shapely.geometry import Polygon
        
        map_data = DoomMapData("MAP01")
        editor = MapEditor(map_data)
        
        polygon = Polygon([(0, 0), (200, 0), (200, 200), (0, 200)])
        editor.add_sector_from_polygon(polygon)
        
        editor.add_player_start(100, 100, angle=90, player_num=1)
        
        assert len(map_data.things) == 1
        assert map_data.things[0]['type'] == ThingType.PLAYER1_START
        assert map_data.things[0]['angle'] == 90


class TestThingType:
    """Tests for ThingType enum."""
    
    def test_player_starts(self):
        """Test player start thing types."""
        assert ThingType.PLAYER1_START.value == 1
        assert ThingType.PLAYER2_START.value == 2
        assert ThingType.PLAYER3_START.value == 3
        assert ThingType.PLAYER4_START.value == 4
    
    def test_enemies(self):
        """Test enemy thing types."""
        assert ThingType.ZOMBIEMAN.value == 3004
        assert ThingType.IMP.value == 3001
        assert ThingType.CYBERDEMON.value == 16
    
    def test_get_thing_radius(self):
        """Test thing radius lookup."""
        assert get_thing_radius(ThingType.PLAYER1_START) == 16
        assert get_thing_radius(ThingType.CYBERDEMON) == 48
        assert get_thing_radius(ThingType.CACODEMON) == 31
    
    def test_enemy_groups(self):
        """Test enemy groupings."""
        assert ThingType.IMP in EASY_ENEMIES
        assert ThingType.ZOMBIEMAN in EASY_ENEMIES


class TestTagRegistry:
    """Tests for TagRegistry class."""
    
    def test_allocate(self):
        """Test tag allocation."""
        registry = TagRegistry()
        
        tag1 = registry.allocate()
        tag2 = registry.allocate()
        
        assert tag1 == 1
        assert tag2 == 2
    
    def test_allocate_named(self):
        """Test named tag allocation."""
        registry = TagRegistry()
        
        tag = registry.allocate(name="door1")
        
        assert tag == 1
        assert registry.get("door1") == 1
    
    def test_reserve(self):
        """Test tag reservation."""
        registry = TagRegistry()
        
        registry.reserve(10, name="special")
        
        assert registry.is_used(10)
        assert registry.get("special") == 10
    
    def test_reserve_conflict(self):
        """Test that reserving used tag raises error."""
        registry = TagRegistry()
        
        registry.allocate()  # Uses tag 1
        
        with pytest.raises(ValueError):
            registry.reserve(1)
    
    def test_get_or_allocate(self):
        """Test get or allocate."""
        registry = TagRegistry()
        
        tag1 = registry.get_or_allocate("door")
        tag2 = registry.get_or_allocate("door")  # Same name
        
        assert tag1 == tag2
    
    def test_reset(self):
        """Test registry reset."""
        registry = TagRegistry()
        
        registry.allocate()
        registry.allocate()
        registry.reset()
        
        tag = registry.allocate()
        assert tag == 1
