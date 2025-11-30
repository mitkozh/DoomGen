# High-Level API Examples

These examples demonstrate the **DoomMapBuilder** high-level API, which provides a clean, declarative interface for creating Doom maps.

## Overview

The high-level API is designed for:
- Quick prototyping
- Declarative map building
- Automatic geometry management (CSG operations handled internally)
- Consistent patterns for common operations

## Examples

### Basic Room Examples
| Example | Description |
|---------|-------------|
| `01_simple_room.py` | Single room with player start |
| `02_two_rooms.py` | Two rooms connected via corridor |
| `03_irregular_polygons.py` | Irregular/organic room shapes |
| `04_hub_rooms.py` | Central hub with multiple connected rooms |

### Doors
| Example | Description |
|---------|-------------|
| `07a_simple_door.py` | Single door between two rooms |
| `07b_hub_doors.py` | Hub with doors to multiple rooms |

### Lifts
| Example | Description |
|---------|-------------|
| `08a_simple_lift.py` | Basic lift between floor levels |
| `08b_multi_lift.py` | Hub with lifts to rooms at different heights |

### Hazards & Effects
| Example | Description |
|---------|-------------|
| `10a_crusher.py` | Crusher traps in corners |
| `10b_damage_floors.py` | Damaging floor types (nukage, lava, etc.) |
| `10c_lighting.py` | Dynamic lighting effects |
| `10d_stairs.py` | Auto-generated staircases |

## Usage

```python
from doomgen import DoomMapBuilder, RoomConfig, ThingType

# Create builder
builder = DoomMapBuilder()

# Add rooms
builder.add_room("spawn", width=256, height=256)
builder.add_room("arena", width=512, height=512, center=(500, 0))

# Connect rooms
builder.connect("spawn", "arena", corridor_width=64)

# Add prefabs
builder.add_door_between("spawn", "arena")
builder.add_lift("arena", position=(400, 0), upper_height=64)
builder.add_crusher("arena", position=(500, 100))
builder.add_damage_floor("arena", damage_type="lava")
builder.add_lighting("arena", effect="flicker")

# Add entities
builder.add_player_start("spawn")
builder.add_enemies("arena", ThingType.IMP, count=4)

# Save
builder.save("output/my_map.wad")
```

## Running Examples

```powershell
# Run an example
python examples/high_level/01_simple_room.py

# Test in GZDoom
gzdoom -iwad doom2.wad -file output/01_simple_room_hl.wad
```

## Comparison with Low-Level API

| Feature | High-Level API | Low-Level API |
|---------|---------------|---------------|
| Room creation | `add_room("name", ...)` | `box()` + `add_sector_from_polygon()` |
| Connections | `connect("a", "b")` | Manual CSG operations |
| Doors | `add_door_between()` | `place_door()` + `apply_door_to_sector()` |
| Lifts | `add_lift()` | Manual cutout + `apply_lift_to_sector()` |
| Geometry | Automatic | Manual polygon management |
| Flexibility | Structured | Full control |

The high-level examples produce equivalent WADs to the low-level examples, but with significantly less code and complexity.
