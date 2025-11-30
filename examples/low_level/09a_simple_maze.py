#!/usr/bin/env python3
"""Example 09a: Simple Maze - Small maze using DoomMapBuilder.

Demonstrates:
- Creating a simple 5x5 maze with MazeGenerator
- Converting maze to polygon for DoomMapBuilder
- Basic maze navigation gameplay
"""

from pathlib import Path
import sys
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from doomgen import ThingType
from shapely.geometry import Polygon
from shapely.ops import unary_union


class SimpleMazeGenerator:
    """Simple maze generator using recursive backtracking."""
    
    def __init__(self, width: int = 5, height: int = 5, cell_size: int = 128, 
                 wall_thickness: int = 16, seed: int | None = None):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.wall_thickness = wall_thickness
        self.rng = random.Random(seed)
        
        # Initialize grid - all walls present
        self.h_walls = [[True] * width for _ in range(height + 1)]
        self.v_walls = [[True] * (width + 1) for _ in range(height)]
        
    def generate(self) -> None:
        """Generate maze using recursive backtracking."""
        visited = [[False] * self.width for _ in range(self.height)]
        stack = [(0, 0)]
        visited[0][0] = True
        
        while stack:
            x, y = stack[-1]
            neighbors = []
            
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and not visited[ny][nx]:
                    neighbors.append((nx, ny, dx, dy))
            
            if neighbors:
                nx, ny, dx, dy = self.rng.choice(neighbors)
                
                # Remove wall between cells
                if dx == 1:  # Moving right
                    self.v_walls[y][x + 1] = False
                elif dx == -1:  # Moving left
                    self.v_walls[y][x] = False
                elif dy == 1:  # Moving down
                    self.h_walls[y + 1][x] = False
                elif dy == -1:  # Moving up
                    self.h_walls[y][x] = False
                
                visited[ny][nx] = True
                stack.append((nx, ny))
            else:
                stack.pop()
    
    def to_polygon(self) -> Polygon:
        """Convert maze to a single walkable polygon."""
        cell = self.cell_size
        wall = self.wall_thickness
        
        # Create floor for each cell
        floors = []
        for y in range(self.height):
            for x in range(self.width):
                x0, y0 = x * cell, y * cell
                floors.append(Polygon([
                    (x0 + wall, y0 + wall),
                    (x0 + cell - wall, y0 + wall),
                    (x0 + cell - wall, y0 + cell - wall),
                    (x0 + wall, y0 + cell - wall),
                ]))
        
        # Add passages where walls are removed
        for y in range(self.height):
            for x in range(self.width + 1):
                if not self.v_walls[y][x] and 0 < x < self.width:
                    x0, y0 = x * cell, y * cell
                    floors.append(Polygon([
                        (x0 - wall, y0 + wall),
                        (x0 + wall, y0 + wall),
                        (x0 + wall, y0 + cell - wall),
                        (x0 - wall, y0 + cell - wall),
                    ]))
        
        for y in range(self.height + 1):
            for x in range(self.width):
                if not self.h_walls[y][x] and 0 < y < self.height:
                    x0, y0 = x * cell, y * cell
                    floors.append(Polygon([
                        (x0 + wall, y0 - wall),
                        (x0 + cell - wall, y0 - wall),
                        (x0 + cell - wall, y0 + wall),
                        (x0 + wall, y0 + wall),
                    ]))
        
        return unary_union(floors)


def main():
    # Create simple 5x5 maze
    maze = SimpleMazeGenerator(width=5, height=5, cell_size=128, wall_thickness=16, seed=42)
    maze.generate()
    maze_poly = maze.to_polygon()
    
    # Build map using low-level API
    from doomgen import WADWriter, MapEditor, SectorConfig, WallConfig
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Add maze as a single sector
    maze_cfg = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLOOR4_8",
        ceiling_texture="CEIL3_5",
        light_level=160
    )
    wall_cfg = WallConfig(middle_texture="STONE2")
    
    editor.add_sector_from_polygon(maze_poly, maze_cfg, wall_cfg)
    
    # Player start (bottom-left cell)
    cell_size = 128
    editor.add_thing(
        cell_size // 2,
        cell_size // 2,
        ThingType.PLAYER1_START,
        check_geometry=False
    )
    
    # Exit at top-right cell
    exit_x = (maze.width - 1) * cell_size + cell_size // 2
    exit_y = (maze.height - 1) * cell_size + cell_size // 2
    editor.add_thing(exit_x, exit_y, ThingType.TELEPORT_LANDING, check_geometry=False)
    
    # Add some health pickups along the path
    editor.add_thing(2 * cell_size + 64, 2 * cell_size + 64, ThingType.STIMPACK, check_geometry=False)
    
    # Save the WAD
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "09a_simple_maze.wad"
    
    wad.save(str(output_path))
    print(f"Created: {output_path}")
    print("Simple 5x5 maze with player start and exit marker")


if __name__ == "__main__":
    main()
