"""
Example 06: Timer Arena (ACS)

Demonstrates a survival arena with timed wave announcements using ACS.
Shows how to use global variables and loops in ACS scripts.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import WADWriter, MapEditor, SectorConfig, ThingType, ShapeBuilder
from doomgen.logic.acs_builder import ACSBuilder, ScriptType


def main():
    print("=== Example 06: Timer Arena ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Create octagonal arena
    builder = ShapeBuilder(seed=123)
    arena = builder.create_polygon(sides=8, radius=400, center=(0, 0))
    arena = builder.snap_to_grid(arena)
    
    config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture='FLAT5_4',
        ceiling_texture='CEIL3_5',
        light_level=192
    )
    editor.add_sector_from_polygon(arena, config)
    
    # Player and weapons in center
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(-64, 0, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(64, 0, ThingType.CHAINGUN, check_geometry=False)
    editor.add_thing(0, -64, ThingType.BOX_OF_BULLETS, check_geometry=False)
    editor.add_thing(0, 64, ThingType.BOX_OF_SHELLS, check_geometry=False)
    
    # Health around perimeter
    editor.add_thing(-250, 0, ThingType.MEDIKIT, check_geometry=False)
    editor.add_thing(250, 0, ThingType.MEDIKIT, check_geometry=False)
    editor.add_thing(0, -250, ThingType.MEDIKIT, check_geometry=False)
    editor.add_thing(0, 250, ThingType.MEDIKIT, check_geometry=False)
    
    # Enemies in corners
    editor.add_thing(-200, 200, ThingType.IMP, check_geometry=False)
    editor.add_thing(200, 200, ThingType.IMP, check_geometry=False)
    editor.add_thing(-200, -200, ThingType.IMP, check_geometry=False)
    editor.add_thing(200, -200, ThingType.IMP, check_geometry=False)
    
    # Build ACS
    acs = ACSBuilder()
    acs.add_include("zcommon.acs")
    
    # Add a global variable for wave tracking
    acs.add_global_var("currentWave", "int", 0)
    
    # Main challenge script
    acs.add_script(
        ScriptType.OPEN,
        '''
Delay(35);
Print(s:"SURVIVAL CHALLENGE");
Delay(70);
Print(s:"Survive the waves!");
Delay(105);

currentWave = 1;
Print(s:"Wave 1 - Zombies!");
Delay(350);

currentWave = 2;
Print(s:"Wave 2 - Imps!");
Delay(350);

currentWave = 3;
Print(s:"Wave 3 - Demons!");
Delay(350);

Print(s:"CHALLENGE COMPLETE!");
'''
    )
    
    # Compile ACS
    try:
        behavior = acs.compile()
        if behavior:
            map_data.behavior = behavior
            print("ACS compiled and embedded successfully!")
        # Also save source for reference
        acs.save_source(output_dir / "06_timer_arena.acs")
        print(f"ACS source saved to: {output_dir / '06_timer_arena.acs'}")
    except FileNotFoundError:
        acs_path = output_dir / "06_timer_arena.acs"
        acs.save_source(acs_path)
        print(f"ACC not found. Saved ACS source to: {acs_path}")
    
    wad.save(output_dir / "06_timer_arena.wad")
    print(f"\nSaved: {output_dir / '06_timer_arena.wad'}")
    print(f"  Vertices: {len(map_data.vertices)}")
    print(f"  Linedefs: {len(map_data.linedefs)}")
    print(f"  Sectors:  {len(map_data.sectors)}")
    print(f"  Things:   {len(map_data.things)}")
    print(f"  Has ACS:  {map_data.behavior is not None}")


if __name__ == "__main__":
    main()
