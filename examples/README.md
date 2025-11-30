# Doom Map Generator Examples

This directory contains examples demonstrating how to use the doom-map-generator library.

## Directory Structure

```
examples/
├── high_level/     # DoomMap declarative API examples
│   ├── 01_simple_room.py      - Single room with player
│   ├── 02_two_rooms.py        - Two connected rooms (merged)
│   ├── 02b_two_rooms_csg.py   - Two connected rooms (separate sectors)
│   ├── 03_irregular_polygons.py - Rooms with rough edges
│   ├── 04_hub_rooms.py        - Hub with 4 connected rooms (merged)
│   ├── 04b_hub_rooms_csg.py   - Hub with 4 connected rooms (separate sectors)
│   ├── 05_multi_floor.py      - Rooms with different floor/ceiling heights
│   ├── 06_large_arena.py      - Large combat arena with many rooms
│   ├── 07_chain_rooms.py      - Linear chain of connected rooms
│   ├── 08_radial_layout.py    - Central hub with rooms in a circle
│   ├── 09_grid_layout.py      - 3x3 grid of interconnected rooms
│   └── 10_mixed_shapes.py     - Various room shapes demonstration
│
└── low_level/      # WADWriter/MapEditor direct API examples
    ├── 01_simple_room.py      - Basic room creation
    ├── 02_two_rooms.py        - Merged geometry with unary_union
    ├── 02b_two_rooms_csg.py   - CSG with GeometryResolver
    ├── 03_irregular_polygons.py
    ├── 04_hub_rooms.py
    ├── 04b_hub_rooms_csg.py
    ├── 05_acs_scripts.py      - ACS scripting
    ├── 06_timer_arena.py      - Timed arena with ACS
    ├── 07_doors.py            - Door prefabs
    ├── 07a_simple_door.py
    ├── 07b_hub_doors.py
    ├── 07c_key_doors.py
    ├── 08_lifts.py            - Lift prefabs
    ├── 08a_simple_lift.py
    ├── 08b_multi_lift.py
    ├── 09_maze.py             - Maze generation
    ├── 09a_simple_maze.py
    ├── 09b_large_maze.py
    ├── 09c_maze_doors.py
    ├── 10a_crusher.py         - Crusher traps
    ├── 10b_damage_floors.py   - Damage floor types
    ├── 10c_lighting.py        - Lighting effects
    └── 10d_stairs.py          - Stair generation
```

## High-Level API (DoomMap)

The high-level API provides a declarative interface for map creation:

```python
from doomgen import DoomMap, ThingType

# Create a map
doom_map = DoomMap(seed=42)

# Add rooms
hub = doom_map.add_room("hub", shape="octagon", radius=512, center=(0, 0))
hub.set_floor(texture='FLAT5_4')
hub.set_light(200)
hub.place_thing(ThingType.PLAYER1_START, "center")

arena = doom_map.add_room("arena", shape="square", radius=256, center=(800, 0))
arena.place_things(ThingType.IMP, count=4, distribution="perimeter")

# Connect rooms
doom_map.connect("hub", "arena", width=96)

# Compile to WAD
doom_map.compile("output/my_map.wad")
```

### Separate Sectors Mode

For MARL benchmarks or maps with different lighting per area:

```python
doom_map = DoomMap(seed=42, separate_sectors=True)
# Each room and corridor becomes its own sector
```

## Low-Level API (WADWriter/MapEditor)

For fine-grained control over Doom structures:

```python
from doomgen import WADWriter, MapEditor, SectorConfig, ThingType
from shapely.geometry import box

wad = WADWriter()
map_data = wad.create_map("MAP01")
editor = MapEditor(map_data)

# Add sector from polygon
room = box(-256, -256, 256, 256)
config = SectorConfig(floor_height=0, ceiling_height=128, light_level=200)
editor.add_sector_from_polygon(room, config)

# Add things
editor.add_thing(0, 0, ThingType.PLAYER1_START)

wad.save("output/my_map.wad")
```

## Running Examples

```bash
# Run a high-level example
python examples/high_level/01_simple_room.py

# Run a low-level example
python examples/low_level/07a_simple_door.py

# Test in GZDoom
gzdoom -iwad doom2.wad -file output/01_simple_room_hl.wad
```

## Output

All examples save WAD files to the `output/` directory.
