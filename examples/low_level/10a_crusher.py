"""
Example 10a: Crusher Arena
==========================

Arena with crushing ceiling traps in the corners.
Crushers are triggered when player walks over the crusher area.
"""

from pathlib import Path
from shapely.geometry import box

from doomgen import WADWriter, MapEditor, SectorConfig, WallConfig, ThingType
from doomgen.prefabs import (
    CrusherConfig, CrusherType, create_crusher_shape, apply_crusher_to_sector,
)


def main():
    """Arena with crusher traps."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Main arena
    arena = box(-384, -384, 384, 384)
    
    # Crusher areas (4 corners)
    crusher_positions = [
        (-256, -256), (256, -256), (-256, 256), (256, 256)
    ]
    crusher_polys = [create_crusher_shape(pos, 96, 96) for pos in crusher_positions]
    
    # Cut crushers from arena
    arena_cut = arena
    for cp in crusher_polys:
        arena_cut = arena_cut.difference(cp)
    
    # Add sectors with proper wall textures
    arena_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=192)
    crusher_cfg = SectorConfig(floor_height=0, ceiling_height=128, light_level=144)
    wall_cfg = WallConfig(middle_texture="STARTAN2", upper_texture="STARTAN2", lower_texture="STARTAN2")
    
    editor.add_sector_from_polygon(arena_cut, arena_cfg, wall_cfg)
    
    crusher_indices = []
    for cp in crusher_polys:
        idx = editor.add_sector_from_polygon(cp, crusher_cfg, wall_cfg)
        crusher_indices.append(idx)
    
    # Apply crushers with increasing tags
    for i, idx in enumerate(crusher_indices):
        apply_crusher_to_sector(editor, idx, tag=i+1, config=CrusherConfig(crusher_type=CrusherType.SLOW))
    
    # Player and items
    editor.add_thing(0, 0, ThingType.PLAYER1_START, check_geometry=False)
    editor.add_thing(-100, 0, ThingType.SHOTGUN, check_geometry=False)
    editor.add_thing(100, 0, ThingType.MEDIKIT, check_geometry=False)
    
    # Enemies in crusher zones (will get crushed!)
    for pos in crusher_positions:
        editor.add_thing(pos[0], pos[1], ThingType.ZOMBIEMAN, check_geometry=False)
    
    wad.save(output_dir / "10a_crusher.wad")
    print(f"Created output/10a_crusher.wad ({len(map_data.sectors)} sectors)")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/10a_crusher.wad")


if __name__ == "__main__":
    main()
