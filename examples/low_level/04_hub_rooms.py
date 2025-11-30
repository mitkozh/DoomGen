"""
Example 04: Hub With Multiple Rooms

Demonstrates a more complex layout with a central hub
connected to multiple surrounding rooms.
"""

from pathlib import Path
from shapely.geometry import box
from shapely.ops import unary_union

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType, ShapeBuilder
)


def main():
    print("=== Example 04: Hub With Multiple Rooms ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    builder = ShapeBuilder(seed=42)
    
    # Central hub - octagonal
    hub = builder.create_polygon(sides=8, radius=300, center=(0, 0))
    hub = builder.snap_to_grid(hub)
    
    # Four surrounding rooms
    north = builder.create_irregular_polygon((0, 500), 150, sides=6, irregularity=0.15)
    south = builder.create_irregular_polygon((0, -500), 150, sides=6, irregularity=0.15)
    east = builder.create_irregular_polygon((500, 0), 150, sides=5, irregularity=0.15)
    west = builder.create_irregular_polygon((-500, 0), 150, sides=5, irregularity=0.15)
    
    # Corridors connecting hub to rooms
    corridors = [
        box(-40, 250, 40, 400),   # North
        box(-40, -400, 40, -250), # South
        box(250, -40, 400, 40),   # East
        box(-400, -40, -250, 40), # West
    ]
    
    # Merge everything
    all_shapes = [hub, north, south, east, west] + corridors
    merged = unary_union(all_shapes)
    
    if merged.geom_type == 'MultiPolygon':
        merged = max(merged.geoms, key=lambda p: p.area)
    
    config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture='FLAT5_4',
        ceiling_texture='CEIL3_5',
        light_level=180
    )
    editor.add_sector_from_polygon(merged, config)
    
    # Player in center
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    
    # Weapons in hub
    editor.add_thing(-80, 80, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(80, 80, ThingType.CHAINGUN, check_geometry=False)
    editor.add_thing(-80, -80, ThingType.BOX_OF_SHELLS, check_geometry=False)
    editor.add_thing(80, -80, ThingType.BOX_OF_BULLETS, check_geometry=False)
    
    # Items in rooms
    editor.add_thing(0, 480, ThingType.SOULSPHERE, check_geometry=False)
    editor.add_thing(0, -480, ThingType.BLUE_KEYCARD, check_geometry=False)
    editor.add_thing(480, 0, ThingType.ROCKET_LAUNCHER, check_geometry=False)
    editor.add_thing(-480, 0, ThingType.MEDIKIT, check_geometry=False)
    
    # Enemies guarding corridors
    editor.add_thing(0, 300, ThingType.IMP, check_geometry=False)
    editor.add_thing(0, -300, ThingType.IMP, check_geometry=False)
    editor.add_thing(300, 0, ThingType.DEMON, check_geometry=False)
    editor.add_thing(-300, 0, ThingType.SHOTGUN_GUY, check_geometry=False)
    
    wad.save(output_dir / "04_hub_rooms.wad")
    print(f"Saved: {output_dir / '04_hub_rooms.wad'}")
    print(f"  Vertices: {len(map_data.vertices)}")
    print(f"  Linedefs: {len(map_data.linedefs)}")
    print(f"  Sectors:  {len(map_data.sectors)}")
    print(f"  Things:   {len(map_data.things)}")


if __name__ == "__main__":
    main()
