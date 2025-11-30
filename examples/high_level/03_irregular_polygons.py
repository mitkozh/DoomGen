"""
Example 03: Irregular Polygons (High-Level API)

Demonstrates using DoomMapBuilder to create organic, irregular room shapes.
This is the high-level API equivalent of low_level/03_irregular_polygons.py

Uses add_irregular_room() for varied, natural-looking rooms.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType


def main():
    print("=== Example 03: Irregular Polygons (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder with seed for reproducibility
    builder = DoomMapBuilder(seed=42)
    
    # Room config
    room_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT5_4",
        ceiling_texture="CEIL3_5",
        light_level=180
    )
    
    # Central hub - irregular octagon
    builder.add_irregular_room(
        "hub",
        radius=300,
        sides=8,
        irregularity=0.15,
        center=(0, 0),
        config=room_cfg
    )
    
    # North room - irregular hexagon
    builder.add_irregular_room(
        "north",
        radius=180,
        sides=6,
        irregularity=0.2,
        center=(0, 500),
        config=room_cfg
    )
    
    # East room - irregular pentagon
    builder.add_irregular_room(
        "east",
        radius=150,
        sides=5,
        irregularity=0.15,
        center=(450, 0),
        config=room_cfg
    )
    
    # Connect rooms with corridors
    builder.connect("hub", "north", corridor_width=80)
    builder.connect("hub", "east", corridor_width=80)
    
    # Add player in center hub
    builder.add_player_start("hub")
    
    # Add weapons in hub
    builder.add_thing("hub", ThingType.SHOTGUN, position=(-100, 0))
    builder.add_thing("hub", ThingType.CHAINGUN, position=(100, 0))
    
    # Add items in other rooms
    builder.add_thing("north", ThingType.SOULSPHERE, position=(0, 450))
    builder.add_thing("east", ThingType.BLUE_KEYCARD, position=(400, 0))
    
    # Add enemies
    builder.add_thing("hub", ThingType.IMP, position=(0, 200), angle=180)
    builder.add_thing("east", ThingType.DEMON, position=(300, 0), angle=270)
    
    # Save
    wad_path = builder.save(output_dir / "03_irregular_rooms_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
