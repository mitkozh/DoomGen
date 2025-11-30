"""
Example 07b: Hub with Doors (High-Level API)

Hub room with 4 doors leading to 4 outer rooms.
This is the high-level API equivalent of low_level/07b_hub_doors.py

Demonstrates using add_door_between() for connecting rooms with doors.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 07b: Hub with Doors (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Different configs for each room
    hub_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=200, floor_texture="FLAT14")
    north_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=144, floor_texture="NUKAGE1")
    south_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=176)
    east_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=192, floor_texture="FLAT5_1")
    west_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=192)
    
    # Add rooms
    builder.add_room("hub", width=512, height=512, center=(0, 0), config=hub_cfg)
    builder.add_room("north", width=256, height=256, center=(0, 400), config=north_cfg)
    builder.add_room("south", width=256, height=256, center=(0, -400), config=south_cfg)
    builder.add_room("east", width=256, height=256, center=(400, 0), config=east_cfg)
    builder.add_room("west", width=256, height=256, center=(-400, 0), config=west_cfg)
    
    # Add doors between hub and each room
    door_w, door_d = 96, 16
    builder.add_door_between("hub", "north", position=(0, 264), width=door_w, depth=door_d, direction="horizontal")
    builder.add_door_between("hub", "south", position=(0, -264), width=door_w, depth=door_d, direction="horizontal")
    builder.add_door_between("hub", "east", position=(264, 0), width=door_w, depth=door_d, direction="vertical")
    builder.add_door_between("hub", "west", position=(-264, 0), width=door_w, depth=door_d, direction="vertical")
    
    # Things
    builder.add_player_start("hub")
    builder.add_thing("hub", ThingType.SHOTGUN, position=(-80, 0))
    builder.add_thing("hub", ThingType.CHAINGUN, position=(80, 0))
    builder.add_thing("north", ThingType.IMP, position=(0, 400), angle=180)
    builder.add_thing("south", ThingType.DEMON, position=(0, -400), angle=0)
    builder.add_thing("east", ThingType.ZOMBIEMAN, position=(400, 0), angle=270)
    builder.add_thing("west", ThingType.IMP, position=(-400, 0), angle=90)
    
    # Save
    wad_path = builder.save(output_dir / "07b_hub_doors_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
