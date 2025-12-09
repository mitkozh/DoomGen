# Copilot Instructions for DoomGen

## Project Overview

A Python library for procedurally generating Doom WAD files, targeting Multi-Agent Reinforcement Learning (MARL) benchmarks. 
The library uses a **Voronoi-First** approach: the map is generated as a mesh of relaxed Voronoi cells (Lloyd's algorithm), which are then grouped into logical areas (rooms, corridors, doors). This ensures organic, non-grid-aligned geometry and robust topology.

## Architecture Layers

```
doomgen/builder.py (ProceduralMapBuilder)  <- High-level API (Voronoi-based)
doomgen/geometry/mesh.py (VoronoiMesh)     <- Voronoi Geometry & Pathfinding
doomgen/geometry/seeds.py                  <- Seed Generation (Lloyd's Relaxation)
doomgen/abstraction/layout.py              <- Logical Graph (Areas, Connections)
        |
doomgen/doom/translator.py (MapTranslator) <- "Baker": Voronoi Mesh -> Doom structures
doomgen/doom/wad.py (WADWriter)            <- Binary WAD I/O via omgifol
```

## Key Patterns

### Voronoi-First Generation
1.  **Seed Generation**: A field of random points is generated and relaxed using Lloyd's algorithm to create uniform-ish cells.
2.  **Cell Claiming**: Areas (rooms) are defined by shapes (Polygons). Any cell whose center falls within the shape is "claimed" by that area.
3.  **Topology**: The Voronoi mesh naturally handles adjacency. If two areas claim adjacent cells, they are physically connected.

### The `ProceduralMapBuilder` API

The builder provides a high-level interface for claiming cells and defining connections.

```python
from doomgen.builder import ProceduralMapBuilder
from doomgen.abstraction.layout import ConnectionType

builder = ProceduralMapBuilder(bounds=(-1024, -1024, 1024, 1024), num_seeds=2000)

# 1. Add Areas (Claim Cells)
# "claim_void" (default): Only claims unassigned cells.
# "overwrite": Claims any cell (useful for pillars/features inside rooms).
builder.add_area("Main Hall", shape=(0, 0, 512, 512))
builder.add_area("Pillar", shape=(0, 0, 64, 64), mode="overwrite", floor_height=32)

# 2. Connect Areas
# Option A: Direct Connection (if physically adjacent)
builder.connect_adjacent("Room A", "Room B", ConnectionType.OPEN)

# Option B: Boundary/Door (creates a new area from shared cells)
builder.add_boundary("Room A", "Room B", name="Door", connection_type=ConnectionType.DOOR)

# Option C: Pathfinding Corridor (A* on mesh)
builder.add_corridor("Room A", "Room B", width=2)

# Option D: Stairs (Pathfinding + Segmentation)
builder.add_stairs("Lower Room", "Upper Room", num_steps=4)
```

### Organic Pathfinding
Corridors and stairs are generated using A* pathfinding on the Voronoi cell graph.
- **Corridors**: A sequence of cells connecting two areas. Can be dilated (`width > 1`) for wider paths.
- **Stairs**: A path segmented into multiple areas with interpolated floor heights.

### Boundary Handling
Connections between areas are handled by:
1.  **Direct Connection**: The shared edge becomes a two-sided linedef.
2.  **Boundary Area**: `add_boundary` identifies cells in Area A that touch Area B and converts them into a new intermediate area (e.g., a door sector).

## Critical Types

| Type | Location | Purpose |
|------|----------|---------|
| `ProceduralMapBuilder` | `doomgen/builder.py` | Main facade for map generation |
| `VoronoiMesh` | `doomgen/geometry/mesh.py` | Manages Voronoi cells and adjacency graph |
| `Area` | `doomgen/abstraction/layout.py` | Logical region (name, config, id) |
| `AreaConfig` | `doomgen/abstraction/layout.py` | Sector properties (heights, textures) |
| `ConnectionType` | `doomgen/abstraction/layout.py` | Enum: OPEN, DOOR, SOLID |
| `MapTranslator` | `doomgen/doom/translator.py` | Converts Mesh+Graph to Doom Sectors/Linedefs |

## Development Commands

```powershell
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run examples
python examples/test_voronoi.py
python examples/test_stairs.py
python examples/test_organic_corridor.py

# Test in Doom engine
gzdoom -iwad doom2.wad -file examples/output/voronoi_test.wad
```

## Common Pitfalls
- **Seed Density**: If `num_seeds` is too low for the map size, small shapes might not claim any cells. Increase `num_seeds` or reduce `bounds`.
- **Connectivity**: `add_boundary` and `connect_adjacent` require areas to be physically adjacent in the Voronoi mesh. If they are far apart, use `add_corridor`.
- **Doors**: Doors are sectors. Use `add_boundary(..., connection_type=ConnectionType.DOOR)` to create them. Ensure `ceiling_height=floor_height` (or close to it) for the closed state.
- **Stairs**: Use `add_stairs` for organic height transitions. It returns a list of step IDs if you need to modify them (e.g., add a door).
- **Player Start**: Always use `ThingType.PLAYER1_START` (ID 1).

