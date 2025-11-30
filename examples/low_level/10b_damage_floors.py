"""
Example 10b: Damaging Floors
============================

Arena with connected rooms featuring different damage types.
All rooms are connected via corridors so the player can walk between them.

Uses the CSG (Constructive Solid Geometry) pattern with MapBuilder:
1. Create rooms as solid polygons
2. Use MapBuilder to automatically "drill" corridors out of rooms
3. The shared edges become proper two-sided linedefs (passable walls)

This is much simpler than manually calculating opening positions!
"""

from pathlib import Path

from doomgen import (
    WADWriter, MapEditor, SectorConfig, WallConfig, ThingType,
    create_rectangle, MapBuilder,
)
from doomgen.prefabs import DamageType, DamageFloorConfig, apply_damage_to_sector


def main():
    """Arena with various damaging floor areas."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Dimensions
    central_size = 512  # 512x512 central room
    corridor_width = 64  # 64-unit wide corridors
    damage_room_size = 256  # 256x256 damage rooms
    gap = 128  # Gap between central room and damage rooms
    
    # Calculate positions
    half_central = central_size // 2  # 256
    damage_room_offset = half_central + gap + damage_room_size // 2  # 512
    
    # === STEP 1: Create all rooms as SOLID rectangles (no manual openings!) ===
    
    central = create_rectangle(central_size, central_size, center=(0, 0))
    room_north = create_rectangle(damage_room_size, damage_room_size, center=(0, damage_room_offset))
    room_south = create_rectangle(damage_room_size, damage_room_size, center=(0, -damage_room_offset))
    room_east = create_rectangle(damage_room_size, damage_room_size, center=(damage_room_offset, 0))
    room_west = create_rectangle(damage_room_size, damage_room_size, center=(-damage_room_offset, 0))
    
    # === STEP 2: Use MapBuilder to manage rooms and corridors ===
    # MapBuilder automatically creates corridors and "drills" them from rooms
    
    mb = MapBuilder(grid_size=8)
    
    # Add all rooms
    mb.add_room("central", central)
    mb.add_room("north", room_north)
    mb.add_room("south", room_south)
    mb.add_room("east", room_east)
    mb.add_room("west", room_west)
    
    # Add corridors - MapBuilder auto-generates and subtracts from rooms
    mb.add_corridor("central", "north", width=corridor_width)
    mb.add_corridor("central", "south", width=corridor_width)
    mb.add_corridor("central", "east", width=corridor_width)
    mb.add_corridor("central", "west", width=corridor_width)
    
    # Build the geometry
    result = mb.build()
    
    if not result.is_valid:
        for error in result.errors:
            print(f"Warning: {error}")
    
    # === STEP 3: Add sectors to the map ===
    
    # Sector configs
    safe_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=192, floor_texture="FLOOR4_8")
    corridor_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=176, floor_texture="FLOOR4_8")
    wall_cfg = WallConfig(middle_texture="STARTAN2", upper_texture="STARTAN2", lower_texture="STARTAN2")
    
    slime_cfg = SectorConfig(floor_height=-8, ceiling_height=128, light_level=160, floor_texture="SLIME01")
    nukage_cfg = SectorConfig(floor_height=-8, ceiling_height=128, light_level=160, floor_texture="NUKAGE1")
    lava_cfg = SectorConfig(floor_height=-8, ceiling_height=128, light_level=176, floor_texture="LAVA1")
    blood_cfg = SectorConfig(floor_height=-8, ceiling_height=128, light_level=128, floor_texture="BLOOD1")
    
    # Add central room (using resolved geometry with carved openings)
    editor.add_sector_from_polygon(result.rooms["central"], safe_cfg, wall_cfg)
    
    # Add corridors
    for corridor_info in result.corridors:
        editor.add_sector_from_polygon(corridor_info.polygon, corridor_cfg, wall_cfg)
    
    # Add damage rooms (using resolved geometry)
    idx_north = editor.add_sector_from_polygon(result.rooms["north"], nukage_cfg, wall_cfg)
    idx_south = editor.add_sector_from_polygon(result.rooms["south"], slime_cfg, wall_cfg)
    idx_east = editor.add_sector_from_polygon(result.rooms["east"], lava_cfg, wall_cfg)
    idx_west = editor.add_sector_from_polygon(result.rooms["west"], blood_cfg, wall_cfg)
    
    # Apply damage types using DamageFloorConfig
    apply_damage_to_sector(editor, idx_north, DamageFloorConfig(damage_type=DamageType.MEDIUM))
    apply_damage_to_sector(editor, idx_south, DamageFloorConfig(damage_type=DamageType.LIGHT))
    apply_damage_to_sector(editor, idx_east, DamageFloorConfig(damage_type=DamageType.HEAVY))
    apply_damage_to_sector(editor, idx_west, DamageFloorConfig(damage_type=DamageType.LETHAL))
    
    # Player start in center of central room
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    
    # Health items scattered around central room
    editor.add_thing(-128, 128, ThingType.STIMPACK, check_geometry=False)
    editor.add_thing(128, 128, ThingType.STIMPACK, check_geometry=False)
    editor.add_thing(-128, -128, ThingType.MEDIKIT, check_geometry=False)
    editor.add_thing(128, -128, ThingType.MEDIKIT, check_geometry=False)
    
    # Rewards in damage rooms
    editor.add_thing(0, damage_room_offset, ThingType.ARMOR_BONUS, check_geometry=False)
    editor.add_thing(0, -damage_room_offset, ThingType.HEALTH_BONUS, check_geometry=False)
    editor.add_thing(damage_room_offset, 0, ThingType.RADIATION_SUIT, check_geometry=False)
    editor.add_thing(-damage_room_offset, 0, ThingType.RADIATION_SUIT, check_geometry=False)
    
    wad.save(output_dir / "10b_damage_floors.wad")
    
    # Report stats
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) >= 0)
    print(f"Created output/10b_damage_floors.wad ({len(map_data.sectors)} sectors, {two_sided} two-sided linedefs)")
    print("\nDamage types: LIGHT (south/slime), MEDIUM (north/nukage), HEAVY (east/lava), LETHAL (west/blood)")
    print("Load with: gzdoom -iwad doom2.wad -file output/10b_damage_floors.wad")


if __name__ == "__main__":
    main()
