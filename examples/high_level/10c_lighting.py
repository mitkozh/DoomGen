"""
Example 10c: Lighting Effects (High-Level API)

Arena demonstrating various sector lighting effects.
This is the high-level API equivalent of low_level/10c_lighting.py

Demonstrates using add_lighting() for dynamic lighting sectors.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType
from doomgen.prefabs import LightEffect


def main():
    print("=== Example 10c: Lighting Effects (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Dimensions
    central_size = 384
    effect_room_size = 256
    effect_room_offset = 416  # Central half + gap + effect half
    
    # Configs
    bright_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=255, floor_texture="CEIL5_1")
    dim_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=128, floor_texture="CEIL5_2")
    
    # Add central hub (bright)
    builder.add_room("central", width=central_size, height=central_size, center=(0, 0), config=bright_cfg)
    
    # Add effect rooms in each direction
    builder.add_room("blink_random", width=effect_room_size, height=effect_room_size,
                     center=(0, effect_room_offset), config=dim_cfg)
    builder.add_room("blink_half", width=effect_room_size, height=effect_room_size,
                     center=(0, -effect_room_offset), config=dim_cfg)
    builder.add_room("blink_1sec", width=effect_room_size, height=effect_room_size,
                     center=(effect_room_offset, 0), config=dim_cfg)
    builder.add_room("oscillate", width=effect_room_size, height=effect_room_size,
                     center=(-effect_room_offset, 0), config=dim_cfg)
    
    # Connect rooms with corridors
    builder.connect("central", "blink_random", corridor_width=64)
    builder.connect("central", "blink_half", corridor_width=64)
    builder.connect("central", "blink_1sec", corridor_width=64)
    builder.connect("central", "oscillate", corridor_width=64)
    
    # Apply lighting effects to rooms
    builder.add_lighting("blink_random", effect=LightEffect.BLINK_RANDOM)
    builder.add_lighting("blink_half", effect=LightEffect.BLINK_HALF_SEC)
    builder.add_lighting("blink_1sec", effect=LightEffect.BLINK_1_SEC)
    builder.add_lighting("oscillate", effect=LightEffect.OSCILLATE)
    
    # Player start in center
    builder.add_player_start("central")
    
    # Decorative pillars in each room
    builder.add_thing("blink_random", ThingType.TALL_GREEN_PILLAR, position=(0, effect_room_offset))
    builder.add_thing("blink_half", ThingType.TALL_RED_PILLAR, position=(0, -effect_room_offset))
    builder.add_thing("blink_1sec", ThingType.TALL_GREEN_PILLAR, position=(effect_room_offset, 0))
    builder.add_thing("oscillate", ThingType.TALL_RED_PILLAR, position=(-effect_room_offset, 0))
    
    # Save
    wad_path = builder.save(output_dir / "10c_lighting_hl.wad")
    print("\nLighting effects: random blink (N), 0.5s blink (S), 1s blink (E), oscillate (W)")
    print(f"Load with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
