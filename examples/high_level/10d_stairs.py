"""
Example 10d: Stairs Demo (High-Level API)

Demonstrates auto-building stairs connecting two areas at different heights.
This is the high-level API equivalent of low_level/10d_stairs.py

Uses polygon-based room definitions for proper edge sharing with stairs.
The rooms are split into left/center/right sections so the center section
shares edges with the stairs.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import DoomMapBuilder, RoomConfig, ThingType
from doomgen.prefabs import StairConfig, create_stair_shapes


def main():
    print("=== Example 10d: Staircase Demo (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Stair parameters
    num_steps = 6
    step_height = 16
    step_depth = 32
    stair_width = 256
    
    total_rise = num_steps * step_height  # 96 units
    stair_depth = num_steps * step_depth  # 192 units
    
    # Get stair bounds (centered at x=0)
    stair_minx = -stair_width / 2  # -128
    stair_maxx = stair_width / 2   # 128
    
    # Room configs at different heights
    # lower_texture="STEP2" for stair risers visible from rooms
    lower_cfg = RoomConfig(
        floor_height=0, ceiling_height=128, light_level=192,
        floor_texture="FLOOR4_8", wall_texture="STARTAN2", lower_texture="STEP2"
    )
    upper_cfg = RoomConfig(
        floor_height=total_rise, ceiling_height=128 + total_rise, light_level=192,
        floor_texture="FLOOR4_8", wall_texture="STARTAN2", lower_texture="STEP2"
    )
    
    # Lower room - split into left, center, right sections
    # Center section shares edge with first stair step at y=0
    lower_left = box(-256, -256, stair_minx, 0)
    lower_center = box(stair_minx, -256, stair_maxx, 0)
    lower_right = box(stair_maxx, -256, 256, 0)
    
    # Upper room - split similarly
    # Center section shares edge with last stair step at y=stair_depth
    upper_left = box(-256, stair_depth, stair_minx, stair_depth + 192)
    upper_center = box(stair_minx, stair_depth, stair_maxx, stair_depth + 192)
    upper_right = box(stair_maxx, stair_depth, 256, stair_depth + 192)
    
    # Create stair step polygons
    stair_config = StairConfig(
        width=stair_width, step_depth=step_depth,
        step_height=step_height, num_steps=num_steps
    )
    stair_polys = create_stair_shapes((0, 0), stair_config, direction="north")
    
    # Add rooms in correct order for proper edge detection:
    # 1. Lower room parts (left, center, right share edges)
    builder.add_room("lower_left", polygon=lower_left, config=lower_cfg)
    builder.add_room("lower_center", polygon=lower_center, config=lower_cfg)
    builder.add_room("lower_right", polygon=lower_right, config=lower_cfg)
    
    # 2. Stair steps in order (each shares edge with previous, first with lower_center)
    for i, step_poly in enumerate(stair_polys):
        step_floor = (i + 1) * step_height
        step_room_cfg = RoomConfig(
            floor_height=step_floor,
            ceiling_height=128 + step_floor,  # Keep consistent headroom
            light_level=192,
            floor_texture="STEP1",
            wall_texture="STEP2",
            lower_texture="STEP2"  # For stair risers
        )
        builder.add_room(f"step_{i}", polygon=step_poly, config=step_room_cfg)
    
    # 3. Upper room parts (center shares edge with last step, then left/right)
    builder.add_room("upper_center", polygon=upper_center, config=upper_cfg)
    builder.add_room("upper_left", polygon=upper_left, config=upper_cfg)
    builder.add_room("upper_right", polygon=upper_right, config=upper_cfg)
    
    # Player in lower room center
    builder.add_player_start("lower_center", position=(0, -128))
    
    # Items on stairs (use step rooms for thing placement)
    for i in range(num_steps):
        y_pos = 16 + i * step_depth
        builder.add_thing(f"step_{i}", ThingType.ARMOR_BONUS, position=(0, y_pos))
    
    # Rewards in upper room
    builder.add_thing("upper_center", ThingType.SOULSPHERE, position=(0, stair_depth + 96))
    builder.add_thing("upper_center", ThingType.SHOTGUN, position=(-64, stair_depth + 96))
    builder.add_thing("upper_center", ThingType.CHAINGUN, position=(64, stair_depth + 96))
    
    # Save
    wad_path = builder.save(output_dir / "10d_stairs_hl.wad")
    print(f"\nStairs connect lower room (floor=0) to upper room (floor={total_rise})")
    print(f"Load with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
