# doomgen - Roadmap

## Current Status: Feature Complete ✅

The library is feature-complete for its target use case (MARL benchmarks). Core functionality for map generation works end-to-end.

---

## Completed Features ✅

### Core WAD Generation
- [x] WAD file I/O via omgifol
- [x] Shapely polygon → Doom sectors/linedefs
- [x] Vertex deduplication and grid snapping
- [x] Shared edge detection for connected rooms
- [x] Proper linedef orientation (clockwise winding)

### Geometry System
- [x] Shape primitives: rectangles, regular polygons, circles
- [x] Irregular polygon generation
- [x] CSG operations: cut, merge, buffer
- [x] L-System corridor generation
- [x] Recursive edge subdivision
- [x] MapBuilder for complex geometry management

### Entity & Things
- [x] All Doom 2 thing types (enemies, items, decorations)
- [x] Player starts (1-4 players)
- [x] Thing placement with geometry validation
- [x] Collision radius checks

### Prefabs
- [x] Doors (manual, key-locked)
- [x] Lifts (standard, fast, perpetual)
- [x] Crushers (slow, fast, silent)
- [x] Damage floors (nukage, lava, blood)
- [x] Lighting effects (blink, flicker, oscillate)
- [x] Stairs generation
- [x] Teleporters

### Scripting
- [x] ACS script builder (Pythonic API)
- [x] ACC compiler integration
- [x] BEHAVIOR lump embedding
- [x] Common script templates (messages, timers, doors)

### High-Level API
- [x] DoomMapBuilder - declarative map construction
- [x] Room/corridor/prefab orchestration
- [x] Procedural modifiers (subdivision, noise, L-systems)

### Quality
- [x] Full type hints (py.typed)
- [x] Seedable randomness for reproducibility
- [x] Error handling with meaningful messages
- [x] unit tests passing

---

## TODO 🔧
### Features
- [ ] Fix connection algorithm (make more robust)
- [ ] Make library more generalizable
- [ ] Implement batch generation

### Documentation
- [ ] Clean up docstrings (remove bloat)
- [ ] Add Sphinx documentation
- [ ] API reference
- [ ] Tutorial examples

### Testing
- [ ] Integration tests (full WAD generation)
- [ ] Edge case coverage
- [ ] Performance benchmarks

### Examples
- [ ] More MARL-specific examples

### Future Ideas (Low Priority)
- [ ] PyPI publishing
- [ ] Visual map preview
- [ ] Texture pack support
- [ ] Custom thing definitions

---

## Architecture

```
DoomMapBuilder (api/doom_map.py)     ← High-level declarative API
        │
MapBuilder (geometry/builder.py)     ← CSG-based geometry management
        │
ShapeBuilder + operations            ← Pure Shapely geometry
        │
MapEditor (doom/translator.py)       ← Shapely → Doom structures
        │
WADWriter (doom/wad.py)              ← Binary WAD I/O via omgifol
```

---

## Module Overview

| Module | Purpose |
|--------|---------|
| `api/` | High-level DoomMapBuilder |
| `geometry/` | Shape creation, CSG operations, modifiers |
| `doom/` | WAD I/O, translator, things, specials |
| `prefabs/` | Doors, lifts, crushers, damage, lighting, stairs |
| `logic/` | ACS script generation |
| `batch/` | YAML/JSON batch generation |
| `utils/` | Constants, validation helpers |
