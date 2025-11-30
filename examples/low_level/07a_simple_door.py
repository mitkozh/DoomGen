"""
Example 07a: Simple Door
========================

Single room with a door in the middle using the cookie-cutter pattern.
A door is a sector with ceiling=floor (closed), which opens by raising ceiling.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType,
)
from doomgen.prefabs import (
    place_door, DoorConfig, DoorType, apply_door_to_sector
)


def main():
    """Single room with a door in the middle."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Full geometry spans entire playable area
    full_geometry = box(-320, -128, 208, 128)
    
    # Door config
    door_config = DoorConfig(width=256, depth=16, door_type=DoorType.MANUAL)
    
    # Cookie-cutter: place_door cuts the geometry
    door_placement = place_door(
        geometry=full_geometry,
        position=(-56, 0),
        direction="vertical",
        config=door_config
    )
    
    print(f"  Door polygon: {door_placement.polygon.bounds}")
    print(f"  Modified geometry: {door_placement.modified_geometry.geom_type}")
    
    # Sector configs
    room_config = SectorConfig(floor_height=0, ceiling_height=128, light_level=192)
    door_sector_config = SectorConfig(floor_height=0, ceiling_height=0, light_level=160)  # CLOSED
    
    # Add room sectors (door may split geometry into pieces)
    if door_placement.modified_geometry.geom_type == 'MultiPolygon':
        for poly in door_placement.modified_geometry.geoms:
            editor.add_sector_from_polygon(poly, room_config)
    else:
        editor.add_sector_from_polygon(door_placement.modified_geometry, room_config)
    
    # Add door sector
    door_idx = editor.add_sector_from_polygon(door_placement.polygon, door_sector_config)
    
    # Apply door properties (action type, textures, flags)
    door_linedefs = apply_door_to_sector(
        editor, door_idx, door_config, door_placement.linedef_action
    )
    print(f"  Applied door to {len(door_linedefs)} linedefs)")
    
    # Things
    editor.add_thing(-192, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(80, 0, ThingType.ZOMBIEMAN, angle=180, check_geometry=False)
    editor.add_thing(120, -60, ThingType.ZOMBIEMAN, angle=180, check_geometry=False)
    editor.add_thing(120, 60, ThingType.ZOMBIEMAN, angle=180, check_geometry=False)
    editor.add_thing(-160, 0, ThingType.SHOTGUN, check_geometry=False)
    
    wad.save(output_dir / "07a_simple_door.wad")
    print(f"Created output/07a_simple_door.wad ({len(map_data.sectors)} sectors, {len(map_data.linedefs)} linedefs)")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/07a_simple_door.wad")


if __name__ == "__main__":
    main()
