# DoomGen - Roadmap

## Current Status: Voronoi Core Complete ✅

The library has transitioned to a **Voronoi-First** architecture. The core pipeline (Seed -> Relax -> Mesh -> Layout -> WAD) is fully functional and capable of generating complex, organic maps with logic.

---

## Completed Features ✅

### Core Architecture
- [x] **Voronoi Mesh Generation**: Lloyd's relaxation for organic cell distribution.
- [x] **Cell Claiming**: Assigning cells to logical areas based on geometric shapes (Polygons).
- [x] **Topology Management**: Automatic adjacency detection between areas.
- [x] **Map Translation**: Converting Voronoi cells into valid Doom sectors and linedefs.

### Procedural Layout
- [x] **ProceduralMapBuilder**: High-level API for defining rooms and connections.
- [x] **Organic Corridors**: A* pathfinding on the cell mesh to connect distant areas.
- [x] **Stairs Generation**: Segmented pathfinding with interpolated floor heights.
- [x] **Boundaries**: Creating doors and windows from shared edges.

### Logic & Scripting
- [x] **ACS Builder**: Pythonic API for generating ACS bytecode.
- [x] **Script Types**: Support for OPEN, ENTER, VOID, and other script types.
- [x] **Control Flow**: Loops, conditionals, and variable management in ACS.
- [x] **Triggers**: Linedef executors (e.g., pressure plates, switches).

### Benchmarking
- [x] **Co-op Puzzle Benchmark**: A parameterized map generator for MARL testing (`coop_puzzle.py`).
- [x] **Reproducibility**: Full seeding support for map geometry and logic.

---

## TODO 🔧

### Features
- [ ] **Advanced Prefabs**: More complex structures (lifts, crushers) adapted to the Voronoi mesh.
- [ ] **Texture Alignment**: Better UV mapping for irregular Voronoi walls.
- [ ] **Enemy Placement Strategies**: Heuristics for placing enemies (e.g., "ambush", "patrol").
- [ ] **3D Floors**: Support for 3D floors (bridges, multi-story) using dummy sectors.

### Documentation
- [ ] **API Reference**: Detailed docstrings for `ProceduralMapBuilder` and `ACSBuilder`.
- [ ] **Tutorials**: Step-by-step guides for creating specific map types.

### Testing
- [ ] **Integration Tests**: Automated checks for WAD validity and playability.
- [ ] **Performance Optimization**: Speeding up the Voronoi generation and mesh building for large maps.

---

## Architecture

```
ProceduralMapBuilder (doomgen/builder.py)   <- High-level API
        |
        v
VoronoiMesh (doomgen/geometry/mesh.py)      <- Core Geometry (Cells, Edges)
        |
        v
LayoutGraph (doomgen/abstraction/layout.py) <- Logical Graph (Areas, Connections)
        |
        v
MapTranslator (doomgen/doom/translator.py)  <- "Baker": Mesh -> Doom Sectors
        |
        v
WADWriter (doomgen/doom/wad.py)             <- Binary WAD I/O
```
