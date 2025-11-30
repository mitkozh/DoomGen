"""
Example 07c: Key Doors
======================

Map with blue, red, and yellow keyed doors.
Uses MapBuilder for clean room management with integrated key door tracking.

The "Local Merge, Global Difference" Pattern:
- Rooms are managed by MapBuilder
- Key doors are added with add_slot_between which cuts from both rooms
- Each door requires a matching colored key to open
"""

from pathlib import Path

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType, DoorAction,
    MapBuilder, SlotType, create_rectangle
)
from doomgen.prefabs import (
    DoorConfig, DoorType, apply_door_to_sector, apply_door_from_info, get_door_action
)


def main():
    """Map with blue, red, and yellow keyed doors."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create room shapes
    main_room = create_rectangle(512, 512, center=(0, 0))
    blue_room = create_rectangle(144, 160, center=(328, 0))
    red_room = create_rectangle(144, 160, center=(-328, 0))
    yellow_room = create_rectangle(160, 144, center=(0, 328))
    
    # Use MapBuilder for geometry management
    mb = MapBuilder(grid_size=8)
    
    # Add rooms
    mb.add_room("main", main_room)
    mb.add_room("blue", blue_room)
    mb.add_room("red", red_room)
    mb.add_room("yellow", yellow_room)
    
    # Add key doors between main and side rooms
    mb.add_slot_between("main", "blue", (264, 0), width=128, depth=16, direction="vertical", slot_type=SlotType.DOOR, key_type="blue")
    mb.add_slot_between("main", "red", (-264, 0), width=128, depth=16, direction="vertical", slot_type=SlotType.DOOR, key_type="red")
    mb.add_slot_between("main", "yellow", (0, 264), width=128, depth=16, direction="horizontal", slot_type=SlotType.DOOR, key_type="yellow")
    
    # Build resolved geometry
    result = mb.build()
    
    if not result.is_valid:
        print(f"MapBuilder errors: {result.errors}")
        return
    
    # Sector configs
    main_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=200)
    door_cfg = SectorConfig(floor_height=0, ceiling_height=0, light_level=160)
    alcove_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=144)
    
    # Add main room
    editor.add_sector_from_polygon(result.rooms["main"], main_cfg)
    
    # Add doors and apply properties in one clean pass
    door_slots = [s for s in result.slots if s.slot_type == SlotType.DOOR]
    for door in door_slots:
        idx = editor.add_sector_from_polygon(door.polygon, door_cfg)
        # Use the new helper that gets the correct action based on key_type
        door_action = get_door_action(door.key_type)
        door_config = DoorConfig(width=door.width, depth=door.depth)
        apply_door_to_sector(editor, idx, door_config, door_action)
    
    # Add alcoves
    editor.add_sector_from_polygon(result.rooms["blue"], alcove_cfg)
    editor.add_sector_from_polygon(result.rooms["red"], alcove_cfg)
    editor.add_sector_from_polygon(result.rooms["yellow"], alcove_cfg)
    
    # Things
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(328, 0, ThingType.BLUE_KEYCARD, check_geometry=False)
    editor.add_thing(-328, 0, ThingType.RED_KEYCARD, check_geometry=False)
    editor.add_thing(0, 328, ThingType.YELLOW_KEYCARD, check_geometry=False)
    
    wad.save(output_dir / "07c_key_doors.wad")
    
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) != -1)
    print(f"Created output/07c_key_doors.wad")
    print(f"  Sectors: {len(map_data.sectors)} (main + 3 alcoves + 3 doors)")
    print(f"  Two-sided linedefs: {two_sided}")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/07c_key_doors.wad")


if __name__ == "__main__":
    main()
