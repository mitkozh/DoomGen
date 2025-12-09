from doomgen import (
    LayoutGraph, Area, AreaConfig, Transform, SeedStrategy, ConnectionType,
    SeedEngine, VoronoiMesh, WADWriter, MapTranslator, Prefab
)
from doomgen.utils.visualization import visualize_mesh
import shutil
import subprocess
from pathlib import Path
import os

def create_voronoi_map():
    print("Generating Voronoi Map...")
    
    # 1. Define Layout
    graph = LayoutGraph()
    
    # Main Hall (Grid seeds for structure)
    hall = Area(
        name="Main Hall",
        transform=Transform(0, 0),
        strategy=SeedStrategy.GRID,
        dimensions=(384, 384),
        seed_density=0.5,
        config=AreaConfig(floor_height=0, ceiling_height=128)
    )
    hall_id = graph.add_area(hall)
    
    # Cave (Poisson seeds for organic look)
    cave = Area(
        name="Cave",
        transform=Transform(400, 0),
        strategy=SeedStrategy.POISSON,
        dimensions=(256, 256),
        shape_hint="circle",
        seed_density=1.0,
        config=AreaConfig(floor_height=-16, floor_texture="NUKAGE1")
    )
    cave_id = graph.add_area(cave)
    
    # Prefab: Pillar in the hall
    # Make it a raised platform
    pillar = Prefab(
        name="Pillar",
        transform=Transform(0, 0),
        stencil_name="circle_filled", # Use filled circle to make it solid
        dimensions=(64, 64),
        config=AreaConfig(floor_height=32, ceiling_height=128, floor_texture="GATE1", wall_texture="SUPPORT3")
    )
    # Note: Prefabs are just Areas. To make it a "pillar", we might want it to be solid?
    # Or maybe it's a decorative area.
    # If we want it to be a solid pillar, we should probably make it a separate area 
    # and NOT connect it to the hall?
    # But in Voronoi, everything is connected.
    # To make a solid pillar, we can make the area have a higher floor or be void?
    # Or just a different texture.
    # Let's just add it as a sub-area.
    pillar_id = graph.add_area(pillar)
    
    # Connect them
    graph.connect(hall_id, cave_id, ConnectionType.OPEN)
    graph.connect(hall_id, pillar_id, ConnectionType.OPEN) # Connected but distinct
    
    # 2. Generate Seeds
    engine = SeedEngine(seed=42)
    seeds = engine.generate(graph)
    print(f"Generated {len(seeds)} seeds.")
    
    # 3. Build Mesh
    mesh = VoronoiMesh(seeds, graph)
    mesh.build()
    print(f"Built mesh with {len(mesh.cells)} cells.")
    
    # Visualize
    os.makedirs("examples/output", exist_ok=True)
    visualize_mesh(mesh, "examples/output/voronoi_debug.png")
    print("Saved visualization to examples/output/voronoi_debug.png")
    
    # 4. Translate to Doom
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    translator = MapTranslator(map_data)
    
    translator.translate(mesh, graph)
    translator.add_player_start(hall_id, 100, 0)
    
    # 5. Save
    output_path = "examples/output/voronoi_test.wad"
    wad.save(output_path)
    print(f"Saved to {output_path}")
    
    # 6. Build Nodes (Optional but recommended)
    if shutil.which("zdbsp"):
        subprocess.run(["zdbsp", "-o", output_path, output_path], check=False)

if __name__ == "__main__":
    create_voronoi_map()
