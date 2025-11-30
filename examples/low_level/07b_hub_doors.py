"""
Example 07b: Hub with Doors
===========================

Hub room with 4 doors leading to 4 outer rooms.
Uses MapBuilder for clean room management with door tracking.

The "Local Merge, Global Difference" Pattern:
- Rooms are managed by MapBuilder
- Doors are added with add_slot_between which cuts through room geometry
- This creates proper sector boundaries for door mechanics
"""

from pathlib import Path

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType, DoorAction,
    MapBuilder, SlotType, create_rectangle
)
from doomgen.prefabs import DoorConfig, apply_door_to_sector


def main():
    """Hub room with 4 doors leading to 4 outer rooms."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create room shapes using create_rectangle helper
    hub = create_rectangle(512, 512, center=(0, 0))
    north_room = create_rectangle(256, 256, center=(0, 400))
    south_room = create_rectangle(256, 256, center=(0, -400))
    east_room = create_rectangle(256, 256, center=(400, 0))
    west_room = create_rectangle(256, 256, center=(-400, 0))
    
    # Use MapBuilder for geometry management
    mb = MapBuilder(grid_size=8)
    
    # Add rooms
    mb.add_room("hub", hub)
    mb.add_room("north", north_room)
    mb.add_room("south", south_room)
    mb.add_room("east", east_room)
    mb.add_room("west", west_room)
    
    # Add doors - cuts from both hub and adjacent rooms
    door_w, door_d = 96, 16
    mb.add_slot_between("hub", "north", (0, 264), door_w, door_d, "horizontal", slot_type=SlotType.DOOR)
    mb.add_slot_between("hub", "south", (0, -264), door_w, door_d, "horizontal", slot_type=SlotType.DOOR)
    mb.add_slot_between("hub", "east", (264, 0), door_w, door_d, "vertical", slot_type=SlotType.DOOR)
    mb.add_slot_between("hub", "west", (-264, 0), door_w, door_d, "vertical", slot_type=SlotType.DOOR)
    
    # Build resolved geometry
    result = mb.build()
    
    if not result.is_valid:
        print(f"MapBuilder errors: {result.errors}")
        return
    
    # Sector configs
    hub_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=200, floor_texture="FLAT14")
    door_cfg = SectorConfig(floor_height=0, ceiling_height=0, light_level=160)
    room_cfgs = {
        "north": SectorConfig(floor_height=0, ceiling_height=128, light_level=144, floor_texture="NUKAGE1"),
        "south": SectorConfig(floor_height=0, ceiling_height=128, light_level=176),
        "east": SectorConfig(floor_height=0, ceiling_height=128, light_level=192, floor_texture="FLAT5_1"),
        "west": SectorConfig(floor_height=0, ceiling_height=128, light_level=192),
    }
    
    # Add hub sector
    editor.add_sector_from_polygon(result.rooms["hub"], hub_cfg)
    
    # Add outer room sectors
    for room_name, cfg in room_cfgs.items():
        editor.add_sector_from_polygon(result.rooms[room_name], cfg)
    
    # Add door sectors
    door_sectors = []
    door_slots = [s for s in result.slots if s.slot_type == SlotType.DOOR]
    for door in door_slots:
        idx = editor.add_sector_from_polygon(door.polygon, door_cfg)
        door_sectors.append(idx)
    
    # Apply door properties
    total_linedefs = 0
    for door_idx in door_sectors:
        linedefs = apply_door_to_sector(editor, door_idx, DoorConfig(), DoorAction.DR_OPEN_WAIT_CLOSE)
        total_linedefs += len(linedefs)
    print(f"  Applied door properties to {total_linedefs} linedefs across {len(door_sectors)} doors")
    
    # Things
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(-80, 0, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(80, 0, ThingType.CHAINGUN, check_geometry=False)
    editor.add_thing(0, 400, ThingType.IMP, angle=180, check_geometry=False)
    editor.add_thing(0, -400, ThingType.DEMON, angle=0, check_geometry=False)
    editor.add_thing(400, 0, ThingType.ZOMBIEMAN, angle=270, check_geometry=False)
    editor.add_thing(-400, 0, ThingType.IMP, angle=90, check_geometry=False)
    
    wad.save(output_dir / "07b_hub_doors.wad")
    
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) != -1)
    print(f"Created output/07b_hub_doors.wad")
    print(f"  Sectors: {len(map_data.sectors)} (hub + 4 rooms + 4 doors)")
    print(f"  Two-sided linedefs: {two_sided}")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/07b_hub_doors.wad")


if __name__ == "__main__":
    main()
