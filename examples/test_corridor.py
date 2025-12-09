from doomgen import (
    LayoutGraph, Area, AreaConfig, Transform, SeedStrategy, ConnectionType,
    SeedEngine, VoronoiMesh, WADWriter, MapTranslator
)
from doomgen.geometry.seeds import Seed
from doomgen.utils.visualization import visualize_mesh
import shutil
import subprocess
from pathlib import Path
import os

def create_corridor_map():
    print("Generating Corridor Map...")
    
    # 1. Define Layout
    graph = LayoutGraph()
    
    # Room A
    room_a = Area(
        name="Room A",
        transform=Transform(0, 0),
        strategy=SeedStrategy.GRID,
        dimensions=(256, 256),
        seed_density=0.8,
        config=AreaConfig(floor_height=0, ceiling_height=128, floor_texture="FLOOR4_8")
    )
    id_a = graph.add_area(room_a)
    
    # Room B
    room_b = Area(
        name="Room B",
        transform=Transform(512, 0),
        strategy=SeedStrategy.GRID,
        dimensions=(256, 256),
        seed_density=0.8,
        config=AreaConfig(floor_height=0, ceiling_height=128, floor_texture="FLOOR4_8")
    )
    id_b = graph.add_area(room_b)
    
    # Corridor
    # A long, thin area connecting them
    corridor = Area(
        name="Corridor",
        transform=Transform(256, 0), # Midpoint
        strategy=SeedStrategy.GRID,
        dimensions=(256, 96), # Length 256, Width 96
        shape_hint="rectangle",
        seed_density=0.6,
        config=AreaConfig(floor_height=0, ceiling_height=112, floor_texture="CEIL3_5", light_level=128)
    )
    id_corr = graph.add_area(corridor)
    
    # Connect: A <-> Corridor <-> B
    graph.connect(id_a, id_corr, ConnectionType.OPEN)
    graph.connect(id_corr, id_b, ConnectionType.OPEN)
    
    # Add Void Areas to force separation
    # Above corridor
    void_top = Area(
        name="VoidTop",
        transform=Transform(256, 128), # Above corridor
        strategy=SeedStrategy.GRID,
        dimensions=(256, 128),
        seed_density=0.5
    )
    
    # 2. Generate Seeds
    engine = SeedEngine(seed=123)
    seeds = engine.generate(graph)
    
    # Add manual void seeds between rooms
    # Top Gap: x=[128, 384], y=[48, 128] (Corridor is width 96, so y=[-48, 48])
    # Bottom Gap: x=[128, 384], y=[-128, -48]
    
    # Top Gap
    for x in range(160, 360, 32):
        for y in range(64, 160, 32):
            seeds.append(Seed(x, y, "VOID", is_boundary=True))
            
    # Bottom Gap
    for x in range(160, 360, 32):
        for y in range(-160, -64, 32):
            seeds.append(Seed(x, y, "VOID", is_boundary=True))

    print(f"Generated {len(seeds)} seeds.")
    
    # 3. Build Mesh
    mesh = VoronoiMesh(seeds, graph)
    mesh.build()
    print(f"Built mesh with {len(mesh.cells)} cells.")
    
    # Visualize
    os.makedirs("examples/output", exist_ok=True)
    visualize_mesh(mesh, "examples/output/corridor_debug.png")
    print("Saved visualization to examples/output/corridor_debug.png")
    
    # 4. Translate to Doom
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    translator = MapTranslator(map_data)
    
    translator.translate(mesh, graph)
    translator.add_player_start(id_a, 0, 0)
    
    # 5. Save
    output_path = "examples/output/corridor_test.wad"
    wad.save(output_path)
    print(f"Saved to {output_path}")
    
    # 6. Build Nodes
    if shutil.which("zdbsp"):
        subprocess.run(["zdbsp", "-o", output_path, output_path], check=False)

if __name__ == "__main__":
    create_corridor_map()
