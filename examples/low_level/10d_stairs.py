"""
Example 10d: Staircase Demo
===========================

Demonstrates auto-building stairs connecting two areas at different heights.
The stairs are geometrically connected to both the lower and upper rooms.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import WADWriter, MapEditor, SectorConfig, WallConfig, ThingType
from doomgen.prefabs import StairConfig, create_stair_shapes


def main():
    """Demo of stairs connecting lower and upper rooms."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Stair configuration - 6 steps, each 16 units high = 96 total rise
    stair_cfg = StairConfig(
        width=256,        # Full width matching rooms
        step_height=16,   # 16 units per step
        step_depth=32,    # 32 units deep per step
        num_steps=6,      # 6 steps * 16 = 96 units total rise
    )
    
    # Calculate stair total depth (6 steps * 32 = 192 units)
    stair_depth = stair_cfg.num_steps * stair_cfg.step_depth
    
    # Create stair shapes centered at x=0, starting at y=0
    stair_polys = create_stair_shapes((0, 0), stair_cfg, direction="north")
    
    # Get stair bounds
    stair_minx = -stair_cfg.width / 2  # -128
    stair_maxx = stair_cfg.width / 2   # 128
    
    # Lower room - ends exactly where stairs start (y=0)
    # Split into left, center, right sections so center shares edge with first step
    lower_left = box(-256, -256, stair_minx, 0)
    lower_center = box(stair_minx, -256, stair_maxx, 0)  # Shares edge with first step
    lower_right = box(stair_maxx, -256, 256, 0)
    
    # Upper room - starts exactly where stairs end (y=stair_depth)
    # Split similarly so center shares edge with last step
    upper_left = box(-256, stair_depth, stair_minx, stair_depth + 192)
    upper_center = box(stair_minx, stair_depth, stair_maxx, stair_depth + 192)  # Shares edge with last step
    upper_right = box(stair_maxx, stair_depth, 256, stair_depth + 192)
    
    # Sector and wall configs
    lower_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=192, floor_texture="FLOOR4_8")
    upper_cfg = SectorConfig(floor_height=96, ceiling_height=224, light_level=192, floor_texture="FLOOR4_8")
    wall_cfg = WallConfig(middle_texture="STARTAN2", upper_texture="STARTAN2", lower_texture="STEP2")
    stair_wall_cfg = WallConfig(middle_texture="STEP2", upper_texture="STARTAN2", lower_texture="STEP2")
    
    # Add lower room parts
    editor.add_sector_from_polygon(lower_left, lower_cfg, wall_cfg)
    editor.add_sector_from_polygon(lower_center, lower_cfg, wall_cfg)
    editor.add_sector_from_polygon(lower_right, lower_cfg, wall_cfg)
    
    # Add stair steps - each step is higher
    for i, step_poly in enumerate(stair_polys):
        step_height = (i + 1) * stair_cfg.step_height
        step_cfg = SectorConfig(
            floor_height=step_height,
            ceiling_height=128 + step_height,  # Keep consistent headroom
            light_level=192,
            floor_texture="STEP1",
        )
        editor.add_sector_from_polygon(step_poly, step_cfg, stair_wall_cfg)
    
    # Add upper room parts
    editor.add_sector_from_polygon(upper_left, upper_cfg, wall_cfg)
    editor.add_sector_from_polygon(upper_center, upper_cfg, wall_cfg)
    editor.add_sector_from_polygon(upper_right, upper_cfg, wall_cfg)
    
    # Player in lower room
    editor.add_thing(0, -128, ThingType.PLAYER1_START, check_geometry=False)
    
    # Items on stairs
    for i in range(len(stair_polys)):
        y_pos = 16 + i * stair_cfg.step_depth
        editor.add_thing(0, y_pos, ThingType.ARMOR_BONUS, check_geometry=False)
    
    # Reward in upper room
    editor.add_thing(0, stair_depth + 96, ThingType.SOULSPHERE, check_geometry=False)
    editor.add_thing(-64, stair_depth + 96, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(64, stair_depth + 96, ThingType.CHAINGUN, check_geometry=False)
    
    wad.save(output_dir / "10d_stairs.wad")
    
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) >= 0)
    print(f"Created output/10d_stairs.wad ({len(map_data.sectors)} sectors, {two_sided} two-sided linedefs)")
    print("\nStairs connect lower room (floor=0) to upper room (floor=96)")
    print("Load with: gzdoom -iwad doom2.wad -file output/10d_stairs.wad")


if __name__ == "__main__":
    main()
