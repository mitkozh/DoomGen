"""
Example 04: Hub With Multiple Rooms (High-Level API)

Demonstrates a more complex layout with a central hub
connected to multiple surrounding rooms.
This is the high-level API equivalent of low_level/04_hub_rooms.py

NOTE: This example uses the merged_room approach for reliable 
corridor connections with irregular polygons. When rooms are 
irregular, auto-corridors may not properly intersect, so we use
add_merged_room() to combine all geometry into one sector.
"""

from pathlib import Path
from shapely.geometry import box
from shapely.ops import unary_union

from doomgen import DoomMapBuilder, RoomConfig, ThingType, ShapeBuilder


def main():
    print("=== Example 04: Hub With Multiple Rooms (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create shape builder with seed for reproducibility
    shape_builder = ShapeBuilder(seed=42)
    
    # Room config
    room_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT5_4",
        ceiling_texture="CEIL3_5",
        light_level=180
    )
    
    # Create geometry shapes manually for proper merging
    hub = shape_builder.create_polygon(sides=8, radius=300, center=(0, 0))
    hub = shape_builder.snap_to_grid(hub)
    
    north = shape_builder.create_irregular_polygon((0, 500), 150, sides=6, irregularity=0.15)
    south = shape_builder.create_irregular_polygon((0, -500), 150, sides=6, irregularity=0.15)
    east = shape_builder.create_irregular_polygon((500, 0), 150, sides=5, irregularity=0.15)
    west = shape_builder.create_irregular_polygon((-500, 0), 150, sides=5, irregularity=0.15)
    
    # Corridors connecting hub to rooms (using box for precise control)
    corridors = [
        box(-40, 250, 40, 400),   # North
        box(-40, -400, 40, -250), # South
        box(250, -40, 400, 40),   # East
        box(-400, -40, -250, 40), # West
    ]
    
    # Merge everything into one polygon
    all_shapes = [hub, north, south, east, west] + corridors
    merged = unary_union(all_shapes)
    
    if merged.geom_type == 'MultiPolygon':
        merged = max(merged.geoms, key=lambda p: p.area)
    
    # Create builder and add merged room
    builder = DoomMapBuilder(seed=42)
    builder.add_merged_room("arena", merged, config=room_cfg)
    
    # Player in center
    builder.add_player_start("arena", position=(0, 0))
    
    # Weapons in hub
    builder.add_thing("arena", ThingType.SHOTGUN, position=(-80, 80))
    builder.add_thing("arena", ThingType.CHAINGUN, position=(80, 80))
    builder.add_thing("arena", ThingType.BOX_OF_SHELLS, position=(-80, -80))
    builder.add_thing("arena", ThingType.BOX_OF_BULLETS, position=(80, -80))
    
    # Items in rooms
    builder.add_thing("arena", ThingType.SOULSPHERE, position=(0, 480))
    builder.add_thing("arena", ThingType.BLUE_KEYCARD, position=(0, -480))
    builder.add_thing("arena", ThingType.ROCKET_LAUNCHER, position=(480, 0))
    builder.add_thing("arena", ThingType.MEDIKIT, position=(-480, 0))
    
    # Enemies guarding corridors
    builder.add_thing("arena", ThingType.IMP, position=(0, 300))
    builder.add_thing("arena", ThingType.IMP, position=(0, -300))
    builder.add_thing("arena", ThingType.DEMON, position=(300, 0))
    builder.add_thing("arena", ThingType.SHOTGUN_GUY, position=(-300, 0))
    
    # Save
    wad_path = builder.save(output_dir / "04_hub_rooms_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
