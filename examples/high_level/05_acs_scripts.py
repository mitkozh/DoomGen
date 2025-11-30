"""
Example 05: ACS Scripts (High-Level API)

Demonstrates embedding ACS (Action Code Script) into maps.
ACS allows for scripted events like messages, timers, and triggers.

This is the high-level API equivalent of low_level/05_acs_scripts.py

NOTE: Requires ACC compiler to be installed and in PATH for embedding.
If ACC is not found, the .acs source file will be saved separately.
"""

from pathlib import Path

from doomgen import DoomMapBuilder, RoomConfig, ThingType, ScriptType


def main():
    print("=== Example 05: ACS Scripts (High-Level) ===\n")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create builder
    builder = DoomMapBuilder()
    
    # Simple rectangular arena
    arena_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT5_4",
        ceiling_texture="CEIL3_5",
        light_level=192
    )
    builder.add_room("arena", width=600, height=400, center=(0, 0), config=arena_cfg)
    
    # Player and items
    builder.add_player_start("arena", position=(0, 0))
    builder.add_thing("arena", ThingType.SHOTGUN, position=(-100, 0))
    builder.add_thing("arena", ThingType.CHAINGUN, position=(100, 0))
    builder.add_thing("arena", ThingType.BOX_OF_SHELLS, position=(0, -100))
    builder.add_thing("arena", ThingType.BOX_OF_BULLETS, position=(0, 100))
    
    # Enemies
    builder.add_thing("arena", ThingType.IMP, position=(200, 100))
    builder.add_thing("arena", ThingType.IMP, position=(200, -100))
    builder.add_thing("arena", ThingType.DEMON, position=(-200, 100))
    builder.add_thing("arena", ThingType.DEMON, position=(-200, -100))
    
    # Add ACS script - runs when map opens
    builder.add_acs_script(
        ScriptType.OPEN,
        """
// Welcome the player
Delay(35);  // 1 second (35 tics)
Print(s:"Welcome to the ACS Demo Arena!");
Delay(105);  // 3 seconds
Print(s:"Defeat all enemies to win!");
"""
    )
    
    # Save
    wad_path = builder.save(output_dir / "05_acs_demo_hl.wad")
    print(f"\nLoad with: gzdoom -iwad doom2.wad -file {wad_path}")


if __name__ == "__main__":
    main()
