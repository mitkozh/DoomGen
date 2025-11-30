"""
Example 02: Two Rooms Connected

Demonstrates merging two room polygons with a connecting corridor.
Uses Shapely's unary_union for boolean geometry operations.
"""

from pathlib import Path
from shapely.geometry import box
from shapely.ops import unary_union

from doomgen import WADWriter, MapEditor, SectorConfig, ThingType


def main():
    print("=== Example 02: Two Rooms Connected ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create two rooms
    room1 = box(-300, -150, -50, 150)   # Left room
    room2 = box(50, -150, 300, 150)     # Right room
    
    # Create a connecting corridor
    corridor = box(-50, -50, 50, 50)
    
    # Merge into a single polygon
    merged = unary_union([room1, corridor, room2])
    
    # Add as a single sector
    config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture='FLOOR4_8',
        ceiling_texture='CEIL3_5',
        light_level=180
    )
    editor.add_sector_from_polygon(merged, config)
    
    # Add player in left room
    editor.add_thing(-175, 0, ThingType.PLAYER1_START, check_geometry=False)
    
    # Add weapons and ammo
    editor.add_thing(-200, 80, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(-200, -80, ThingType.BOX_OF_SHELLS, check_geometry=False)
    
    # Add enemies in right room
    editor.add_thing(175, 80, ThingType.IMP, angle=180, check_geometry=False)
    editor.add_thing(175, -80, ThingType.IMP, angle=180, check_geometry=False)
    editor.add_thing(200, 0, ThingType.DEMON, angle=180, check_geometry=False)
    
    # Add a key as the goal
    editor.add_thing(250, 0, ThingType.BLUE_KEYCARD, check_geometry=False)
    
    wad.save(output_dir / "02_two_rooms.wad")
    print(f"Saved: {output_dir / '02_two_rooms.wad'}")
    print(f"  Vertices: {len(map_data.vertices)}")
    print(f"  Linedefs: {len(map_data.linedefs)}")
    print(f"  Sectors:  {len(map_data.sectors)}")
    print(f"  Things:   {len(map_data.things)}")


if __name__ == "__main__":
    main()
