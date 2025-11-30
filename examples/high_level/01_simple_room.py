"""
Example 01: Simple Room (High-Level API)

The most basic possible Doom map - a single rectangular room with a player start.
This is the high-level API equivalent of low_level/01_simple_room.py

Uses DoomMapBuilder for a clean, declarative approach.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig


def main():
    print("=== Example 01: Simple Room (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Add a single room (512x384 centered at origin)
    builder.add_room(
        "spawn",
        width=512,
        height=384,
        center=(0, 0),
        config=RoomConfig(
            floor_height=0,
            ceiling_height=128,
            floor_texture="FLOOR4_8",
            ceiling_texture="CEIL3_5",
            light_level=192
        )
    )
    
    # Add player start in center
    builder.add_player_start("spawn")
    
    # Save the WAD
    wad_path = builder.save(output_dir / "01_simple_room_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
