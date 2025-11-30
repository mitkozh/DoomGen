"""
Example 08a: Simple Lift
========================

Demonstrates a basic lift between two floor levels using low-level API.

IMPORTANT: Doom lifts LOWER to lowest adjacent floor, then return UP.
The lift floor height should be set to the UPPER level, and it will
lower to the lowest adjacent floor when activated.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import (
    WADWriter, MapEditor, SectorConfig, ThingType, LiftAction,
    MapBuilder, SlotType, create_rectangle
)
from doomgen.prefabs import apply_lift_to_sector


def main():
    """Single lift between two floor levels."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create room shapes
    lower_room = create_rectangle(256, 384, center=(-192, 0))
    upper_room = create_rectangle(256, 384, center=(192, 0))
    
    # Create lift shape (positioned between rooms)
    lift = box(-64, -64, 64, 64)  # 128x128 lift at origin
    
    # Use MapBuilder for geometry management
    mb = MapBuilder(grid_size=8)
    
    # Add rooms
    mb.add_room("lower", lower_room)
    mb.add_room("upper", upper_room)
    
    # Add lift as slot from both rooms using polygon parameter
    mb.add_slot("lower", position=(0, 0), width=128, depth=128, slot_type=SlotType.LIFT, polygon=lift)
    mb.add_slot("upper", position=(0, 0), width=128, depth=128, slot_type=SlotType.LIFT, polygon=lift)
    
    # Build resolved geometry
    result = mb.build()
    
    if not result.is_valid:
        print(f"MapBuilder errors: {result.errors}")
        return
    
    # Sector configs - same ceiling to avoid texture issues
    CEILING = 192
    lower_cfg = SectorConfig(floor_height=0, ceiling_height=CEILING, light_level=176)
    upper_cfg = SectorConfig(floor_height=64, ceiling_height=CEILING, light_level=200)
    
    # Lift starts at upper level (64), lowers to lower level (0)
    lift_cfg = SectorConfig(floor_height=64, ceiling_height=CEILING, light_level=160)
    
    # Add room sectors
    editor.add_sector_from_polygon(result.rooms["lower"], lower_cfg)
    editor.add_sector_from_polygon(result.rooms["upper"], upper_cfg)
    
    # Add lift sector
    lift_idx = editor.add_sector_from_polygon(lift, lift_cfg)
    
    # Apply lift action
    apply_lift_to_sector(editor, lift_idx, tag=1, linedef_action=LiftAction.WR_LIFT)
    
    # Things
    editor.add_thing(-192, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(192, 0, ThingType.SHOTGUN, check_geometry=False)
    
    wad.save(output_dir / "08a_simple_lift.wad")
    
    two_sided = sum(1 for ld in map_data.linedefs if ld.get('back_sidedef', -1) != -1)
    print("Created output/08a_simple_lift.wad")
    print(f"  Sectors: {len(map_data.sectors)} (2 rooms + 1 lift)")
    print(f"  Two-sided linedefs: {two_sided}")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/08a_simple_lift.wad")


if __name__ == "__main__":
    main()
