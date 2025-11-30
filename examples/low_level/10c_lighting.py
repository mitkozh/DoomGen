"""
Example 10c: Lighting Effects
=============================

Arena demonstrating various sector lighting effects.
All areas are connected so the player can walk between them.

Uses the CSG (Constructive Solid Geometry) pattern with MapBuilder:
1. Create rooms as solid polygons
2. Use MapBuilder to automatically generate and "drill" corridors
3. The shared edges become proper two-sided linedefs (passable walls)
"""

from pathlib import Path

from doomgen import (
    WADWriter, MapEditor, SectorConfig, WallConfig, ThingType,
    create_rectangle, MapBuilder,
)
from doomgen.prefabs import LightEffect, LightConfig, apply_light_effect


def main():
    """Arena with various lighting effects."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Dimensions
    central_size = 384  # 384x384 central hub
    corridor_width = 64  # 64-unit wide corridors
    gap = 96  # Gap between rooms
    effect_room_size = 256  # 256x256 effect rooms
    
    # Calculate positions
    half_central = central_size // 2  # 192
    effect_room_offset = half_central + gap + effect_room_size // 2  # 416
    
    # === STEP 1: Create all rooms as SOLID rectangles ===
    
    central = create_rectangle(central_size, central_size, center=(0, 0))
    room_blink_random = create_rectangle(effect_room_size, effect_room_size, center=(0, effect_room_offset))
    room_blink_half = create_rectangle(effect_room_size, effect_room_size, center=(0, -effect_room_offset))
    room_blink_1sec = create_rectangle(effect_room_size, effect_room_size, center=(effect_room_offset, 0))
    room_oscillate = create_rectangle(effect_room_size, effect_room_size, center=(-effect_room_offset, 0))
    
    # === STEP 2: Use MapBuilder to manage rooms and corridors ===
    
    mb = MapBuilder(grid_size=8)
    
    # Add all rooms
    mb.add_room("central", central)
    mb.add_room("blink_random", room_blink_random)
    mb.add_room("blink_half", room_blink_half)
    mb.add_room("blink_1sec", room_blink_1sec)
    mb.add_room("oscillate", room_oscillate)
    
    # Add corridors - MapBuilder auto-generates and subtracts from rooms
    mb.add_corridor("central", "blink_random", width=corridor_width)
    mb.add_corridor("central", "blink_half", width=corridor_width)
    mb.add_corridor("central", "blink_1sec", width=corridor_width)
    mb.add_corridor("central", "oscillate", width=corridor_width)
    
    # Build the geometry
    result = mb.build()
    
    if not result.is_valid:
        for error in result.errors:
            print(f"Warning: {error}")
    
    # === STEP 3: Add sectors to the map ===
    
    # Sector configs
    bright_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=255, floor_texture="CEIL5_1")
    corridor_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=200, floor_texture="CEIL5_1")
    dim_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=128, floor_texture="CEIL5_2")
    wall_cfg = WallConfig(middle_texture="METAL1", upper_texture="METAL1", lower_texture="METAL1")
    
    # Add central hub
    editor.add_sector_from_polygon(result.rooms["central"], bright_cfg, wall_cfg)
    
    # Add corridors
    for corridor_info in result.corridors:
        editor.add_sector_from_polygon(corridor_info.polygon, corridor_cfg, wall_cfg)
    
    # Add effect rooms
    idx_blink_random = editor.add_sector_from_polygon(result.rooms["blink_random"], dim_cfg, wall_cfg)
    idx_blink_half = editor.add_sector_from_polygon(result.rooms["blink_half"], dim_cfg, wall_cfg)
    idx_blink_1sec = editor.add_sector_from_polygon(result.rooms["blink_1sec"], dim_cfg, wall_cfg)
    idx_oscillate = editor.add_sector_from_polygon(result.rooms["oscillate"], dim_cfg, wall_cfg)
    
    # Apply lighting effects
    apply_light_effect(editor, idx_blink_random, LightConfig(effect=LightEffect.BLINK_RANDOM))
    apply_light_effect(editor, idx_blink_half, LightConfig(effect=LightEffect.BLINK_HALF_SEC))
    apply_light_effect(editor, idx_blink_1sec, LightConfig(effect=LightEffect.BLINK_1_SEC))
    apply_light_effect(editor, idx_oscillate, LightConfig(effect=LightEffect.OSCILLATE))
    
    # Player start in center of central room
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    
    # Decorative pillars in each room
    editor.add_thing(0, effect_room_offset, ThingType.TALL_GREEN_PILLAR, check_geometry=False)
    editor.add_thing(0, -effect_room_offset, ThingType.TALL_RED_PILLAR, check_geometry=False)
    editor.add_thing(effect_room_offset, 0, ThingType.TALL_GREEN_PILLAR, check_geometry=False)
    editor.add_thing(-effect_room_offset, 0, ThingType.TALL_RED_PILLAR, check_geometry=False)
    
    wad.save(output_dir / "10c_lighting.wad")
    
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) >= 0)
    print(f"Created output/10c_lighting.wad ({len(map_data.sectors)} sectors, {two_sided} two-sided linedefs)")
    print("\nLighting effects: random blink, 0.5s blink, 1s blink, oscillate")
    print("Load with: gzdoom -iwad doom2.wad -file output/10c_lighting.wad")


if __name__ == "__main__":
    main()
