# DoomGen

A modular, extensible Python library for generating valid `.wad` files for Doom (Doom 2 format). Specifically designed for creating benchmarks for **Multi-Agent Reinforcement Learning (MARL)**.

## Features

- **Abstract Geometry**: Work with Shapely polygons, convert to Doom sectors at compile time
- **Procedural Generation**: L-systems, recursive subdivision, room templates
- **Deterministic**: Fully seedable for reproducible RL benchmarks
- **ACS Scripting**: Inject game logic via Python-generated ACS scripts
- **High-Level API**: Define maps declaratively with minimal code

## Installation (not yet applicable)

```bash
pip install doomgen
```

Or for development:

```bash
git clone https://github.com/mitkozh/doomgen.git
cd doomgen
pip install -e ".[dev]"
```

## Quick Start

```python
from doomgen import DoomMapBuilder, ThingType

# Create a map builder
builder = DoomMapBuilder()

# Add rooms
builder.add_room("spawn", width=256, height=256)
builder.add_room("arena", width=512, height=512, center=(600, 0))

# Connect rooms with a corridor
builder.connect("spawn", "arena", corridor_width=64)

# Add player start and enemies
builder.add_player_start("spawn")
builder.add_enemies("arena", ThingType.IMP, count=4)

# Generate the WAD
builder.save("output/my_map.wad")
```

## Documentation

See [SPECIFICATION.md](SPECIFICATION.md) for detailed architecture and [ROADMAP.md](ROADMAP.md) for implementation status.

## Requirements

- Python 3.10+
- omgifol >= 0.5.0
- Shapely >= 2.0.0
- NumPy >= 1.24.0
- NetworkX >= 3.0

### Optional

- `acc` (ACS Compiler) for logic injection - must be in PATH

## License

MIT License
