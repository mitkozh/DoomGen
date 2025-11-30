"""
Example 05: ACS Scripts

Demonstrates embedding ACS (Action Code Script) into maps.
ACS allows for scripted events like messages, timers, and triggers.

NOTE: Requires ACC compiler to be installed and in PATH for embedding.
If ACC is not found, the .acs source file will be saved separately.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import WADWriter, MapEditor, SectorConfig, ThingType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType


def main():
    print("=== Example 05: ACS Scripts ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Simple rectangular arena
    arena = box(-300, -200, 300, 200)
    
    config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture='FLAT5_4',
        ceiling_texture='CEIL3_5',
        light_level=192
    )
    editor.add_sector_from_polygon(arena, config)
    
    # Player and items
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(-100, 0, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(100, 0, ThingType.CHAINGUN, check_geometry=False)
    editor.add_thing(0, -100, ThingType.BOX_OF_SHELLS, check_geometry=False)
    editor.add_thing(0, 100, ThingType.BOX_OF_BULLETS, check_geometry=False)
    
    # Enemies
    editor.add_thing(200, 100, ThingType.IMP, angle=180, check_geometry=False)
    editor.add_thing(200, -100, ThingType.IMP, angle=180, check_geometry=False)
    editor.add_thing(-200, 100, ThingType.DEMON, angle=0, check_geometry=False)
    editor.add_thing(-200, -100, ThingType.DEMON, angle=0, check_geometry=False)
    
    # Build ACS script
    acs = ACSBuilder()
    acs.add_include("zcommon.acs")
    
    # Script that runs when the map opens
    acs.add_script(
        ScriptType.OPEN,
        """
// Welcome the player
Delay(35);  // 1 second (35 tics)
Print(s:"Welcome to the ACS Demo Arena!");
Delay(105);  // 3 seconds
Print(s:"Defeat all enemies to win!");
"""
    )
    
    # Try to compile and embed
    try:
        behavior = acs.compile()
        if behavior:
            map_data.behavior = behavior
            # Also embed the source code in SCRIPTS lump
            map_data.scripts = acs.to_code()
            print("ACS compiled and embedded successfully!")
            print("ACS source embedded in SCRIPTS lump!")
        # Also save source for reference
        acs.save_source(output_dir / "05_acs_demo.acs")
        print(f"ACS source also saved to: {output_dir / '05_acs_demo.acs'}")
    except FileNotFoundError:
        # ACC not found - save source file
        acs_path = output_dir / "05_acs_demo.acs"
        acs.save_source(acs_path)
        print(f"ACC compiler not found. Saved ACS source to: {acs_path}")
        print("To compile: acc 05_acs_demo.acs")
    
    wad.save(output_dir / "05_acs_demo.wad")
    print(f"\nSaved: {output_dir / '05_acs_demo.wad'}")
    print(f"  Vertices: {len(map_data.vertices)}")
    print(f"  Linedefs: {len(map_data.linedefs)}")
    print(f"  Sectors:  {len(map_data.sectors)}")
    print(f"  Things:   {len(map_data.things)}")
    print(f"  Has ACS BEHAVIOR: {map_data.behavior is not None}")
    print(f"  Has ACS SCRIPTS:  {map_data.scripts is not None}")


if __name__ == "__main__":
    main()
