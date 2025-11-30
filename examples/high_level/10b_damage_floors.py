"""
Example 10b: Damaging Floors (High-Level API)

Arena with connected rooms featuring different damage types.
This is the high-level API equivalent of low_level/10b_damage_floors.py

Demonstrates using add_damage_floor() for hazardous floor sectors.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType
from doomgen.prefabs import DamageType


def main():
    print("=== Example 10b: Damaging Floors (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Dimensions
    central_size = 512
    damage_room_size = 256
    damage_room_offset = 512  # Central half + gap + damage half
    
    # Configs
    safe_cfg = RoomConfig(floor_height=0, ceiling_height=128, light_level=192, floor_texture="FLOOR4_8")
    
    # Add central safe room
    builder.add_room("central", width=central_size, height=central_size, center=(0, 0), config=safe_cfg)
    
    # Add damage rooms in each direction
    builder.add_room("north", width=damage_room_size, height=damage_room_size,
                     center=(0, damage_room_offset), config=safe_cfg)
    builder.add_room("south", width=damage_room_size, height=damage_room_size,
                     center=(0, -damage_room_offset), config=safe_cfg)
    builder.add_room("east", width=damage_room_size, height=damage_room_size,
                     center=(damage_room_offset, 0), config=safe_cfg)
    builder.add_room("west", width=damage_room_size, height=damage_room_size,
                     center=(-damage_room_offset, 0), config=safe_cfg)
    
    # Connect rooms with corridors
    builder.connect("central", "north", corridor_width=64)
    builder.connect("central", "south", corridor_width=64)
    builder.connect("central", "east", corridor_width=64)
    builder.connect("central", "west", corridor_width=64)
    
    # Apply damage floors to outer rooms
    builder.add_damage_floor("north", damage_type=DamageType.MEDIUM, floor_texture="NUKAGE1")
    builder.add_damage_floor("south", damage_type=DamageType.LIGHT, floor_texture="SLIME01")
    builder.add_damage_floor("east", damage_type=DamageType.HEAVY, floor_texture="LAVA1")
    builder.add_damage_floor("west", damage_type=DamageType.LETHAL, floor_texture="BLOOD1")
    
    # Player start in center
    builder.add_player_start("central")
    
    # Health items in central room
    builder.add_thing("central", ThingType.STIMPACK, position=(-128, 128))
    builder.add_thing("central", ThingType.STIMPACK, position=(128, 128))
    builder.add_thing("central", ThingType.MEDIKIT, position=(-128, -128))
    builder.add_thing("central", ThingType.MEDIKIT, position=(128, -128))
    
    # Rewards in damage rooms
    builder.add_thing("north", ThingType.ARMOR_BONUS, position=(0, damage_room_offset))
    builder.add_thing("south", ThingType.HEALTH_BONUS, position=(0, -damage_room_offset))
    builder.add_thing("east", ThingType.RADIATION_SUIT, position=(damage_room_offset, 0))
    builder.add_thing("west", ThingType.RADIATION_SUIT, position=(-damage_room_offset, 0))
    
    # Save
    wad_path = builder.save(output_dir / "10b_damage_floors_hl.wad")
    print("\nDamage types: LIGHT (south/slime), MEDIUM (north/nukage), HEAVY (east/lava), LETHAL (west/blood)")
    print(f"Load with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
