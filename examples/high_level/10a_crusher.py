"""
Example 10a: Crusher Arena (High-Level API)

Arena with crushing ceiling traps in the corners.
This is the high-level API equivalent of low_level/10a_crusher.py

Demonstrates using add_crusher() for hazardous trap sectors.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType
from doomgen.prefabs import CrusherType


def main():
    print("=== Example 10a: Crusher Arena (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Room config
    arena_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        light_level=192,
        wall_texture="STARTAN2"
    )
    
    # Add main arena
    builder.add_room("arena", width=768, height=768, center=(0, 0), config=arena_cfg)
    
    # Add crushers in four corners
    crusher_positions = [
        (-256, -256),  # SW
        (256, -256),   # SE
        (-256, 256),   # NW
        (256, 256),    # NE
    ]
    
    for pos in crusher_positions:
        builder.add_crusher(
            "arena",
            position=pos,
            width=96,
            depth=96,
            crusher_type=CrusherType.SLOW
        )
    
    # Player and items in center
    builder.add_player_start("arena")
    builder.add_thing("arena", ThingType.SHOTGUN, position=(-100, 0))
    builder.add_thing("arena", ThingType.MEDIKIT, position=(100, 0))
    
    # Enemies in crusher zones
    for pos in crusher_positions:
        builder.add_thing("arena", ThingType.ZOMBIEMAN, position=pos)
    
    # Save
    wad_path = builder.save(output_dir / "10a_crusher_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
