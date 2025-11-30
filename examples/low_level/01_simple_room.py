"""
Example 01: Simple Room

The most basic possible Doom map - a single rectangular room with a player start.
This demonstrates the core workflow:
1. Create a WADWriter
2. Create a map
3. Use MapEditor to add a sector from a polygon
4. Add a player start
5. Save the WAD
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import WADWriter, MapEditor, SectorConfig, ThingType


def main():
    print("=== Example 01: Simple Room ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create WAD and map
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create a simple rectangular room using Shapely box
    # box(minx, miny, maxx, maxy)
    room = box(-256, -192, 256, 192)
    
    # Add the room as a sector
    config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture='FLOOR4_8',
        ceiling_texture='CEIL3_5',
        light_level=192
    )
    editor.add_sector_from_polygon(room, config)
    
    # Add player 1 start in the center
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    
    # Save the WAD
    wad.save(output_dir / "01_simple_room.wad")
    print(f"Saved: {output_dir / '01_simple_room.wad'}")
    print(f"  Vertices: {len(map_data.vertices)}")
    print(f"  Linedefs: {len(map_data.linedefs)}")
    print(f"  Sectors:  {len(map_data.sectors)}")
    print(f"  Things:   {len(map_data.things)}")


if __name__ == "__main__":
    main()
