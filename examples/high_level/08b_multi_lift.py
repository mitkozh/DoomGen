"""
Example 08b: Multi-Lift Hub (High-Level API)

Hub room with 3 lifts going to rooms at different heights.
This is the high-level API equivalent of low_level/08b_multi_lift.py

Demonstrates multiple lifts with different floor level configurations.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 08b: Multi-Lift Hub (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Use same ceiling height everywhere to prevent texture issues
    CEILING = 128
    
    # Room configs at different heights
    hub_cfg = RoomConfig(floor_height=0, ceiling_height=CEILING, light_level=192)
    west_cfg = RoomConfig(floor_height=-32, ceiling_height=CEILING, light_level=160)
    east_cfg = RoomConfig(floor_height=48, ceiling_height=CEILING, light_level=208)
    north_cfg = RoomConfig(floor_height=32, ceiling_height=CEILING, light_level=176)
    
    # Add rooms
    builder.add_room("hub", width=384, height=384, center=(0, 0), config=hub_cfg)
    builder.add_room("west", width=192, height=256, center=(-288, 0), config=west_cfg)
    builder.add_room("east", width=192, height=256, center=(288, 0), config=east_cfg)
    builder.add_room("north", width=256, height=192, center=(0, 288), config=north_cfg)
    
    # Add lifts between hub and each room
    # Heights are auto-calculated from room floor heights
    builder.add_lift_between("hub", "west", position=(-160, 0), width=64, depth=96)
    builder.add_lift_between("hub", "east", position=(160, 0), width=64, depth=96)
    builder.add_lift_between("hub", "north", position=(0, 160), width=96, depth=64)
    
    # Things
    builder.add_player_start("hub")
    builder.add_thing("west", ThingType.MEDIKIT, position=(-288, 0))
    builder.add_thing("east", ThingType.SHOTGUN, position=(288, 0))
    builder.add_thing("north", ThingType.CHAINGUN, position=(0, 288))
    
    # Save
    wad_path = builder.save(output_dir / "08b_multi_lift_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
