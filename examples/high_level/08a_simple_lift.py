"""
Example 08a: Simple Lift (High-Level API)

Demonstrates a basic lift between two floor levels.
This is the high-level API equivalent of low_level/08a_simple_lift.py

Uses add_lift_between() for automatic height configuration.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 08a: Simple Lift (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Room configs at different heights (same ceiling to avoid texture issues)
    CEILING = 192
    lower_cfg = RoomConfig(floor_height=0, ceiling_height=CEILING, light_level=176)
    upper_cfg = RoomConfig(floor_height=64, ceiling_height=CEILING, light_level=200)
    
    # Add rooms at different heights
    builder.add_room("lower", width=256, height=384, center=(-192, 0), config=lower_cfg)
    builder.add_room("upper", width=256, height=384, center=(192, 0), config=upper_cfg)
    
    # Add lift between rooms - heights are auto-calculated from room floor heights
    builder.add_lift_between(
        "lower", "upper",
        position=(0, 0),
        width=128,
        depth=128
    )
    
    # Things
    builder.add_player_start("lower", position=(-192, 0))
    builder.add_thing("upper", ThingType.SHOTGUN, position=(192, 0))
    
    # Save
    wad_path = builder.save(output_dir / "08a_simple_lift_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
