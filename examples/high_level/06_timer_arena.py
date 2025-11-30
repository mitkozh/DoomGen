"""
Example 06: Timer Arena (High-Level API)

Demonstrates a survival arena with timed wave announcements using ACS.
Shows how to use the add_survival_timer() helper method.

This is the high-level API equivalent of low_level/06_timer_arena.py
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 06: Timer Arena (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder with seed for reproducible octagon
    builder = DoomMapBuilder(seed=123)
    
    # Create octagonal arena using polygon room
    arena_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT5_4",
        ceiling_texture="CEIL3_5",
        light_level=192
    )
    builder.add_polygon_room("arena", sides=8, radius=400, center=(0, 0), config=arena_cfg)
    
    # Player and weapons in center
    builder.add_player_start("arena", position=(0, 0))
    builder.add_thing("arena", ThingType.SHOTGUN, position=(-64, 0))
    builder.add_thing("arena", ThingType.CHAINGUN, position=(64, 0))
    builder.add_thing("arena", ThingType.BOX_OF_BULLETS, position=(0, -64))
    builder.add_thing("arena", ThingType.BOX_OF_SHELLS, position=(0, 64))
    
    # Health around perimeter
    builder.add_thing("arena", ThingType.MEDIKIT, position=(-250, 0))
    builder.add_thing("arena", ThingType.MEDIKIT, position=(250, 0))
    builder.add_thing("arena", ThingType.MEDIKIT, position=(0, -250))
    builder.add_thing("arena", ThingType.MEDIKIT, position=(0, 250))
    
    # Enemies in corners
    builder.add_thing("arena", ThingType.IMP, position=(-200, 200))
    builder.add_thing("arena", ThingType.IMP, position=(200, 200))
    builder.add_thing("arena", ThingType.IMP, position=(-200, -200))
    builder.add_thing("arena", ThingType.IMP, position=(200, -200))
    
    # Add survival timer with wave announcements
    builder.add_survival_timer([
        ("Wave 1 - Zombies!", 350),  # 10 seconds
        ("Wave 2 - Imps!", 350),
        ("Wave 3 - Demons!", 350),
    ])
    
    # Save
    wad_path = builder.save(output_dir / "06_timer_arena_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
