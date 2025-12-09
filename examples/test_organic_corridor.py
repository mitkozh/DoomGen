
from doomgen import (
    LayoutGraph, Area, AreaConfig, Transform, SeedStrategy, ConnectionType,
    SeedEngine, VoronoiMesh, WADWriter, MapTranslator, Prefab
)
from doomgen.utils.visualization import visualize_mesh
import shutil
import subprocess
from pathlib import Path
import os
import numpy as np

def create_organic_corridor_map():
    print("Generating Organic Corridor Map...")
    
    # 1. Define Layout
    graph = LayoutGraph()
    
    # Room A (Start)
    room_a = Area(
        name="Start Room",
        transform=Transform(-100, 0),
        strategy=SeedStrategy.GRID,
        dimensions=(128, 128),
        config=AreaConfig(floor_height=0, ceiling_height=128, floor_texture="FLOOR4_8")
    )
    id_a = graph.add_area(room_a)
    
    # Room B (End)
    room_b = Area(
        name="End Room",
        transform=Transform(400, 0),
        strategy=SeedStrategy.GRID,
        dimensions=(128, 128),
        config=AreaConfig(floor_height=0, ceiling_height=128, floor_texture="FLOOR4_8")
    )
    id_b = graph.add_area(room_b)
    
    # Organic Corridor (Path)
    # Generate a sine wave path
    x = np.linspace(0, 300, 20)
    y = 50 * np.sin(x / 50)
    path_points = list(zip(x, y))
    
    corridor = Area(
        name="Organic Corridor",
        transform=Transform(0, 0), # Path is relative to this? No, path points are local.
        # If transform is (0,0), local = global.
        strategy=SeedStrategy.PATH,
        path_points=path_points,
        dimensions=(96, 0), # Width 96
        seed_density=1.0,
        config=AreaConfig(floor_height=0, ceiling_height=112, floor_texture="RROCK19", light_level=128)
    )
    id_corr = graph.add_area(corridor)
    
    # Door between Room A and Corridor
    # We place the door at the start of the corridor (approx 0,0)
    # But Room A is at -100,0.
    # Let's place the door at (-50, 0)
    door = Prefab(
        name="Door A",
        transform=Transform(-50, 0),
        stencil_name="door_linear",
        dimensions=(64, 16),
        config=AreaConfig(
            floor_height=0, 
            ceiling_height=0, # Closed
            floor_texture="FLOOR4_8",
            ceiling_texture="CEIL3_5",
            wall_texture="BIGDOOR2",
            lower_texture="BIGDOOR2",
            upper_texture="BIGDOOR2"
        )
    )
    id_door = graph.add_area(door)
    
    # Connections
    # Room A <-> Door <-> Corridor
    graph.connect(id_a, id_door, ConnectionType.DOOR) # Door trigger
    graph.connect(id_door, id_corr, ConnectionType.DOOR) # Door trigger (from inside too)
    
    # Corridor <-> Room B (Open connection)
    graph.connect(id_corr, id_b, ConnectionType.OPEN)
    
    # 2. Generate Seeds
    engine = SeedEngine(seed=123)
    seeds = engine.generate(graph)
    print(f"Generated {len(seeds)} seeds.")
    
    # 3. Build Mesh
    mesh = VoronoiMesh(seeds, graph)
    mesh.build()
    print(f"Built mesh with {len(mesh.cells)} cells.")
    
    # Visualize
    os.makedirs("examples/output", exist_ok=True)
    visualize_mesh(mesh, "examples/output/organic_corridor_debug.png")
    print("Saved visualization to examples/output/organic_corridor_debug.png")
    
    # 4. Translate to Doom
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    translator = MapTranslator(map_data)
    
    translator.translate(mesh, graph)
    translator.add_player_start(id_a, -100, 0)
    
    # 5. Save
    output_path = "examples/output/organic_corridor.wad"
    wad.save(output_path)
    print(f"Saved to {output_path}")
    
    # 6. Build Nodes
    if shutil.which("zdbsp"):
        subprocess.run(["zdbsp", "-o", output_path, output_path], check=False)

if __name__ == "__main__":
    create_organic_corridor_map()
