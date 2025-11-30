"""
Example 02: Two Rooms Connected (High-Level API)

Demonstrates connecting two rooms with a corridor using DoomMapBuilder.
This is the high-level API equivalent of low_level/02_two_rooms.py

The corridor is automatically generated and merged into a single sector.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 02: Two Rooms Connected (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Configure room settings
    room_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLOOR4_8",
        ceiling_texture="CEIL3_5",
        light_level=180
    )
    
    # Add two rooms
    builder.add_room("left", width=250, height=300, center=(-175, 0), config=room_cfg)
    builder.add_room("right", width=250, height=300, center=(175, 0), config=room_cfg)
    
    # Connect rooms with corridor
    builder.connect("left", "right", corridor_width=100)
    
    # Add player in left room
    builder.add_player_start("left", position=(-175, 0))
    
    # Add weapons and ammo in left room
    builder.add_thing("left", ThingType.SHOTGUN, position=(-200, 80))
    builder.add_thing("left", ThingType.BOX_OF_SHELLS, position=(-200, -80))
    
    # Add enemies in right room
    builder.add_thing("right", ThingType.IMP, position=(175, 80), angle=180)
    builder.add_thing("right", ThingType.IMP, position=(175, -80), angle=180)
    builder.add_thing("right", ThingType.DEMON, position=(200, 0), angle=180)
    
    # Add a key as the goal
    builder.add_thing("right", ThingType.BLUE_KEYCARD, position=(250, 0))
    
    # Save
    wad_path = builder.save(output_dir / "02_two_rooms_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
