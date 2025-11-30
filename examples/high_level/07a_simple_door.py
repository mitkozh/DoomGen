"""
Example 07a: Simple Door (High-Level API)

Single room with a door in the middle using DoomMapBuilder.
This is the high-level API equivalent of low_level/07a_simple_door.py

The door is created automatically with the cookie-cutter pattern.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 07a: Simple Door (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Room config
    room_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        light_level=192
    )
    
    # Add two rooms that will be separated by door
    builder.add_room("left", width=264, height=256, center=(-192, 0), config=room_cfg)
    builder.add_room("right", width=264, height=256, center=(80, 0), config=room_cfg)
    
    # Add door between rooms
    builder.add_door_between(
        "left", "right",
        position=(-56, 0),
        width=256,
        depth=16,
        direction="vertical"
    )
    
    # Add player in left room
    builder.add_player_start("left", position=(-192, 0))
    
    # Add enemies in right room
    builder.add_thing("right", ThingType.ZOMBIEMAN, position=(80, 0), angle=180)
    builder.add_thing("right", ThingType.ZOMBIEMAN, position=(120, -60), angle=180)
    builder.add_thing("right", ThingType.ZOMBIEMAN, position=(120, 60), angle=180)
    
    # Add weapon
    builder.add_thing("left", ThingType.SHOTGUN, position=(-160, 0))
    
    # Save
    wad_path = builder.save(output_dir / "07a_simple_door_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
