# Copilot Instructions for DoomGen

## Project Overview

A Python library for procedurally generating Doom WAD files, targeting Multi-Agent Reinforcement Learning (MARL) benchmarks. Uses Shapely for abstract geometry -> Doom structures (vertices, linedefs, sidedefs, sectors) via `omgifol`.

## Architecture Layers

```
api/doom_map.py (DoomMapBuilder)         <- High-level declarative API
geometry/builder.py (MapBuilder)         <- Mid-level CSG-based geometry
geometry/   (ShapeBuilder, shapes, csg)  <- Abstract 2D shapes (Shapely) + CSG
        |
doom/translator.py (MapEditor)           <- "Baker": Shapely -> Doom structures
doom/wad.py (WADWriter, DoomMapData)     <- Binary WAD I/O via omgifol
```

## Key Patterns

### Two API Levels
- **High-level**: `DoomMapBuilder` for declarative map building (see `examples/high_level/`)
- **Low-level**: `WADWriter` + `MapEditor` for direct sector/linedef control (see `examples/low_level/`)

### Edge-Sharing (Abutting) Corridor Model

Doom sectors share linedefs at their edges - they don't overlap. The `add_corridor()` method now uses 
**abutting mode by default**, which matches how Doom geometry actually works:

```python
# Abutting mode (default) - sectors share edges, no overlapping geometry
builder.add_corridor("hub", "arena", width=64)  # connection_style="abutting"

# Legacy overlap mode - for CSG operations (corridors cut into rooms)
builder.add_corridor("hub", "arena", width=64, connection_style="overlap", overlap=16)
```

Connection styles:
- **abutting** (default): Corridor edges align exactly with room boundaries. 
  "Portal cuts" are automatically created at connection points to add the necessary
  vertices for edge-sharing. This matches Doom's sector model where adjacent sectors
  share linedefs. The cuts are minimal (1 unit deep) and snap away, so rooms keep
  their original area while gaining the vertices needed for proper two-sided linedefs.
- **overlap** (legacy): Corridor extends INTO rooms by `overlap` amount. Rooms are carved with CSG.
  Use when you need complex geometry operations.

### The "Local Merge, Global Difference" Pattern (CSG)

This is the core pattern for creating connected rooms with separate sectors:

- **Local Merge**: Use `merge_polygons()` to combine shapes WITHIN a single room
  (e.g., creating an L-shaped room from two rectangles = one sector)
  
- **Global Difference**: Use `cut_polygon()` to create connections BETWEEN rooms
  (corridors, doors, lifts cut through rooms = separate sectors with shared edges)

```python
# Using MapBuilder (recommended for connected rooms with separate sectors)
from doomgen import MapBuilder, create_rectangle

builder = MapBuilder(grid_size=8)

# Add rooms as solid shapes
builder.add_room("hub", create_rectangle(512, 512))
builder.add_room("arena", create_rectangle(256, 256, center=(600, 0)))

# Add corridor - abutting mode by default (sectors share edges)
builder.add_corridor("hub", "arena", width=64, name="main")

# Add door at corridor entrance (works for any corridor type)
builder.add_corridor_door("main", end="a")

# Build final geometry
result = builder.build()

# Use in MapEditor - shared edges become two-sided linedefs
editor.add_sector_from_polygon(result.rooms["hub"], hub_config)
editor.add_sector_from_polygon(result.rooms["arena"], arena_config)
for corridor in result.corridors:
    editor.add_sector_from_polygon(corridor.polygon, corridor_config)
```

```python
# Using utility functions for manual CSG
from doomgen import cut_polygon, merge_polygons, create_rectangle

# Create L-shaped room (local merge - one sector)
rect1 = create_rectangle(200, 400)
rect2 = create_rectangle(400, 200, center=(100, -100))
l_room = merge_polygons(rect1, rect2)

# Cut a door from the room (global difference - separate sectors)
door = create_door_shape((200, 0), 64, 16, "vertical")
room_carved = cut_polygon(l_room, door)

editor.add_sector_from_polygon(room_carved, room_config)
editor.add_sector_from_polygon(door, door_config)
```

### Unified Corridor API

All corridor types use the same `add_corridor()` method with a `style` parameter:

```python
# Straight corridor (default) - abutting by default
builder.add_corridor("hub", "arena", width=64)

# L-system procedural corridor
builder.add_corridor("hub", "arena", width=64, style="lsystem:serpentine", name="main")

# Custom polygon corridor
builder.add_corridor("hub", "arena", style="custom", polygon=my_polygon, name="secret")

# Add doors at corridor entrances (works for ALL corridor types)
builder.add_corridor_door("main", end="a")  # Door at hub side
builder.add_corridor_door("main", end="b")  # Door at arena side

# Query corridor data
corridor = builder.get_corridor("main")
print(f"Entry points: {corridor.entry_a} -> {corridor.entry_b}")
```

Available L-system grammars:
- Organic: 'direct', 'wavy', 'wobble', 'organic', 'gentle', 'kinked'
- Complex: 'serpentine', 'koch', 'zigzag', 'meander'

### Slot-Based Prefab API

Prefab areas (doors, lifts, crushers) use the slot-based API with `SlotType` enum:

```python
from doomgen import MapBuilder, SlotType

# Add a slot to a room
builder.add_slot("room", position=(100, 0), width=64, depth=16, 
                slot_type=SlotType.DOOR, key_type="blue")

# Add a slot between two rooms
builder.add_slot_between("room_a", "room_b", width=64, depth=16,
                        slot_type=SlotType.DOOR, direction="auto")

# Add slot at corridor entrance (works for all corridor types)
builder.add_slot_at_corridor("main", end="a", slot_type=SlotType.DOOR, depth=16)
builder.add_corridor_door("main", end="b")  # Convenience alias for door slots
```

SlotType enum values: DOOR, LIFT, CRUSHER, TELEPORTER, STAIRS, DAMAGE_FLOOR, LIGHTING, GENERIC

### Cookie-Cutter Prefab Pattern
Doors, lifts, teleporters use geometry subtraction to create interactive elements:
1. Create element polygon at position
2. Cut from static geometry with `cut_polygon(room, element)` (or use slots in abutting mode)
3. Add both as sectors -> shared edges become two-sided linedefs
4. Apply linedef specials via `apply_door_to_sector()` / `apply_lift_to_sector()`

See `prefabs/__init__.py` for `DoorPrefab`, `LiftPrefab`, `CrusherPrefab`, etc.

### Doom Geometry Constraints
- Coordinates must be integers (use `snap_to_grid()`, `to_integer_coords()`)
- Sectors wound clockwise for proper texture rendering
- Adjacent sectors share edges -> `MapEditor` auto-detects and creates two-sided linedefs
- Minimum corridor width: 64 units; scale: ~32 units = 1 meter

### Reproducibility
All randomness uses `numpy.random.Generator`. Pass `seed=` to `MapBuilder` or `ShapeBuilder` for deterministic output.

## Critical Types

| Type | Location | Purpose |
|------|----------|---------|
| `MapBuilder` | `geometry/builder.py` | CSG-based map geometry builder |
| `CorridorData` | `geometry/builder.py` | Corridor storage with entry points |
| `CorridorStyle` | `geometry/builder.py` | STRAIGHT, LSYSTEM, CUSTOM |
| `SlotInfo` | `geometry/builder.py` | Prefab slot information |
| `SlotType` | `geometry/builder.py` | Enum: DOOR, LIFT, CRUSHER, TELEPORTER, etc. |
| `cut_polygon` | `geometry/operations.py` | Subtract one polygon from another |
| `merge_polygons` | `geometry/operations.py` | Union multiple polygons into one |
| `SectorConfig` | `doom/translator.py` | Floor/ceiling heights, textures, lighting |
| `WallConfig` | `doom/translator.py` | Upper/middle/lower textures |
| `ThingType` | `doom/things.py` | Doom 2 entity types (enemies, items, players) |
| `DoorAction`, `LiftAction` | `doom/specials.py` | Linedef action types |
| `LinedefFlags` | `doom/specials.py` | TWO_SIDED, BLOCKING, UPPER_UNPEGGED, etc. |
| `BasePrefab` | `prefabs/base.py` | Base class for all prefabs |

## Development Commands

```powershell
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run example (creates WAD in output/)
python examples/low_level/01_simple_room.py

# Test in Doom engine
gzdoom -iwad doom2.wad -file output/01_simple_room.wad
```

## File Conventions
- Examples in `examples/low_level/` and `examples/high_level/`
- Output WADs go to `output/` directory
- ACS scripts (if `acc` unavailable) saved as `.acs` alongside `.wad`

## Common Pitfalls
- Always check `polygon.is_valid` before adding sectors; use `make_valid()` for repair
- `MultiPolygon` results from boolean ops -> handled by `ensure_polygon()` or `max(geoms, key=lambda p: p.area)`
- Thing placement: use `check_geometry=False` when geometry is merged/modified after sector creation
- Door sectors need `ceiling_height=floor_height` (closed state), open via linedef action
- For connected rooms with SEPARATE sectors, use MapBuilder with `add_corridor()`
- For connected rooms as ONE sector, use `unary_union()` or `merge_polygons()`
- Use `add_corridor_door()` for placing doors at corridor entrances (works for all corridor types)
- Default corridor mode is "abutting" - rooms share edges with corridors, no CSG cutting
- Use `connection_style="overlap"` for legacy CSG-based corridor connections
