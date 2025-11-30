"""
Example 08b: Multi-Lift Hub
===========================

Hub room with 3 lifts going to rooms at different heights.
Uses MapBuilder for clean room management with lifts as slots.

IMPORTANT: Doom lifts LOWER to lowest adjacent floor.
- To go DOWN: Lift floor = higher level, lowers to lower level
- To go UP: Lift floor = higher level, player rides up when it returns

The "Local Merge, Global Difference" Pattern:
- Rooms are managed by MapBuilder
- Lifts are added with add_slot which cuts through room geometry
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType, LiftAction,
    MapBuilder, SlotType, create_rectangle
)
from doomgen.prefabs import apply_lift_to_sector


def main():
    """Hub with 3 lifts going to different heights."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create room shapes
    hub = create_rectangle(384, 384, center=(0, 0))
    west_room = create_rectangle(192, 256, center=(-288, 0))
    east_room = create_rectangle(192, 256, center=(288, 0))
    north_room = create_rectangle(256, 192, center=(0, 288))
    
    # Create lift shapes (as boxes for precise control)
    lift1 = box(-192, -48, -128, 48)   # West
    lift2 = box(128, -48, 192, 48)     # East  
    lift3 = box(-48, 128, 48, 192)     # North
    
    # Use MapBuilder for geometry management
    mb = MapBuilder(grid_size=8)
    
    # Add rooms
    mb.add_room("hub", hub)
    mb.add_room("west", west_room)
    mb.add_room("east", east_room)
    mb.add_room("north", north_room)
    
    # Add lifts as slots - they cut from adjacent rooms
    mb.add_slot("hub", position=(-160, 0), width=64, depth=96, slot_type=SlotType.LIFT, polygon=lift1)
    mb.add_slot("hub", position=(160, 0), width=64, depth=96, slot_type=SlotType.LIFT, polygon=lift2)
    mb.add_slot("hub", position=(0, 160), width=96, depth=64, slot_type=SlotType.LIFT, polygon=lift3)
    mb.add_slot("west", position=(-160, 0), width=64, depth=96, slot_type=SlotType.LIFT, polygon=lift1)
    mb.add_slot("east", position=(160, 0), width=64, depth=96, slot_type=SlotType.LIFT, polygon=lift2)
    mb.add_slot("north", position=(0, 160), width=96, depth=64, slot_type=SlotType.LIFT, polygon=lift3)
    
    # Build resolved geometry
    result = mb.build()
    
    if not result.is_valid:
        print(f"MapBuilder errors: {result.errors}")
        return
    
    # Use same ceiling height everywhere to prevent texture issues
    CEILING = 128
    
    # Configs at different floor heights, same ceiling
    hub_cfg = SectorConfig(floor_height=0, ceiling_height=CEILING, light_level=192)
    west_cfg = SectorConfig(floor_height=-32, ceiling_height=CEILING, light_level=160)
    east_cfg = SectorConfig(floor_height=48, ceiling_height=CEILING, light_level=208)
    north_cfg = SectorConfig(floor_height=32, ceiling_height=CEILING, light_level=176)
    
    # Lift configs 
    # IMPORTANT: Doom lifts LOWER to lowest adjacent floor, then return UP.
    # - lift1: goes from hub (0) DOWN to west room (-32) - start at hub level
    # - lift2: needs to reach east room (48) - start at 48, lower to hub (0)
    # - lift3: needs to reach north room (32) - start at 32, lower to hub (0)
    lift1_cfg = SectorConfig(floor_height=0, ceiling_height=CEILING, light_level=144)
    lift2_cfg = SectorConfig(floor_height=48, ceiling_height=CEILING, light_level=144)
    lift3_cfg = SectorConfig(floor_height=32, ceiling_height=CEILING, light_level=144)
    
    # Add room sectors
    editor.add_sector_from_polygon(result.rooms["hub"], hub_cfg)
    editor.add_sector_from_polygon(result.rooms["west"], west_cfg)
    editor.add_sector_from_polygon(result.rooms["east"], east_cfg)
    editor.add_sector_from_polygon(result.rooms["north"], north_cfg)
    
    # Add lift sectors
    lift1_idx = editor.add_sector_from_polygon(lift1, lift1_cfg)
    lift2_idx = editor.add_sector_from_polygon(lift2, lift2_cfg)
    lift3_idx = editor.add_sector_from_polygon(lift3, lift3_cfg)
    
    # Apply lifts with different tags
    apply_lift_to_sector(editor, lift1_idx, tag=1, linedef_action=LiftAction.SR_LIFT)
    apply_lift_to_sector(editor, lift2_idx, tag=2, linedef_action=LiftAction.SR_LIFT)
    apply_lift_to_sector(editor, lift3_idx, tag=3, linedef_action=LiftAction.SR_LIFT)
    
    # Things
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(-288, 0, ThingType.MEDIKIT, check_geometry=False)
    editor.add_thing(288, 0, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(0, 288, ThingType.CHAINGUN, check_geometry=False)
    
    wad.save(output_dir / "08b_multi_lift.wad")
    
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) != -1)
    print(f"Created output/08b_multi_lift.wad")
    print(f"  Sectors: {len(map_data.sectors)} (hub + 3 rooms + 3 lifts)")
    print(f"  Two-sided linedefs: {two_sided}")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/08b_multi_lift.wad")


if __name__ == "__main__":
    main()
