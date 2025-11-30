"""
Example 03: Irregular Polygons

Demonstrates using ShapeBuilder to create organic, irregular room shapes.
The create_irregular_polygon method creates non-rectangular rooms
that look more natural.
"""

from pathlib import Path
from shapely.ops import unary_union
from shapely.geometry import box

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType,
    ShapeBuilder, create_irregular_polygon
)


def main():
    print("=== Example 03: Irregular Polygons ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Method 1: Use ShapeBuilder for multiple shapes with same RNG
    builder = ShapeBuilder(seed=42)
    
    # Create irregular rooms
    hub = builder.create_irregular_polygon(
        center=(0, 0),
        radius=300,
        sides=8,
        irregularity=0.15
    )
    
    north_room = builder.create_irregular_polygon(
        center=(0, 500),
        radius=180,
        sides=6,
        irregularity=0.2
    )
    
    # Method 2: Use convenience function (creates new RNG each call)
    east_room = create_irregular_polygon(
        center=(450, 0),
        radius=150,
        sides=5,
        seed=100
    )
    
    # Create connecting corridors
    north_corridor = box(-40, 250, 40, 370)
    east_corridor = box(250, -40, 350, 40)
    
    # Merge all geometry
    all_shapes = [hub, north_room, east_room, north_corridor, east_corridor]
    merged = unary_union(all_shapes)
    
    # Handle potential MultiPolygon result
    if merged.geom_type == 'MultiPolygon':
        merged = max(merged.geoms, key=lambda p: p.area)
    
    # Add as sector
    config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture='FLAT5_4',
        ceiling_texture='CEIL3_5',
        light_level=180
    )
    editor.add_sector_from_polygon(merged, config)
    
    # Add player in center hub
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    
    # Add weapons
    editor.add_thing(-100, 0, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(100, 0, ThingType.CHAINGUN, check_geometry=False)
    
    # Add items in other rooms
    editor.add_thing(0, 450, ThingType.SOULSPHERE, check_geometry=False)
    editor.add_thing(400, 0, ThingType.BLUE_KEYCARD, check_geometry=False)
    
    # Add enemies
    editor.add_thing(0, 300, ThingType.IMP, check_geometry=False)
    editor.add_thing(300, 0, ThingType.DEMON, check_geometry=False)
    
    wad.save(output_dir / "03_irregular_rooms.wad")
    print(f"Saved: {output_dir / '03_irregular_rooms.wad'}")
    print(f"  Vertices: {len(map_data.vertices)}")
    print(f"  Linedefs: {len(map_data.linedefs)}")
    print(f"  Sectors:  {len(map_data.sectors)}")
    print(f"  Things:   {len(map_data.things)}")


if __name__ == "__main__":
    main()
