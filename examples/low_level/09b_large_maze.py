#!/usr/bin/env python3
"""Example 09b: Large Maze - Larger maze with enemies using DoomMapBuilder.

Demonstrates:
- Creating a larger 10x10 maze
- Placing enemies throughout the maze
- Adding items and weapons for survival
"""

from pathlib import Path
import sys
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from doomgen import ThingType
from shapely.geometry import Polygon
from shapely.ops import unary_union


class LargeMazeGenerator:
    """Maze generator for larger mazes with enemy placement."""
    
    def __init__(self, width: int = 10, height: int = 10, cell_size: int = 128, 
                 wall_thickness: int = 16, seed: int | None = None):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.wall_thickness = wall_thickness
        self.rng = random.Random(seed)
        
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
                
                if dx == 1:
                    self.v_walls[y][x + 1] = False
                elif dx == -1:
                    self.v_walls[y][x] = False
                elif dy == 1:
                    self.h_walls[y + 1][x] = False
                elif dy == -1:
                    self.h_walls[y][x] = False
                
                visited[ny][nx] = True
                stack.append((nx, ny))
            else:
                stack.pop()
    
    def to_polygon(self) -> Polygon:
        """Convert maze to walkable polygon."""
        cell = self.cell_size
        wall = self.wall_thickness
        
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
    
    def get_cell_center(self, x: int, y: int) -> tuple[float, float]:
        """Get center coordinates of a cell."""
        return (x * self.cell_size + self.cell_size // 2,
                y * self.cell_size + self.cell_size // 2)


def main():
    # Create larger 10x10 maze
    maze = LargeMazeGenerator(width=10, height=10, cell_size=128, wall_thickness=16, seed=123)
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
        floor_texture="FLOOR5_1",
        ceiling_texture="CEIL3_3",
        light_level=144
    )
    wall_cfg = WallConfig(middle_texture="MARBLE1")
    
    editor.add_sector_from_polygon(maze_poly, maze_cfg, wall_cfg)
    
    # Player start (bottom-left)
    px, py = maze.get_cell_center(0, 0)
    editor.add_thing(px, py, ThingType.PLAYER1_START, check_geometry=False)
    
    # Exit (top-right)
    ex, ey = maze.get_cell_center(9, 9)
    editor.add_thing(ex, ey, ThingType.TELEPORT_LANDING, check_geometry=False)
    
    # Place enemies in various cells
    enemy_positions = [
        (2, 2, ThingType.ZOMBIEMAN),
        (4, 1, ThingType.ZOMBIEMAN),
        (1, 4, ThingType.SHOTGUN_GUY),
        (5, 5, ThingType.IMP),
        (7, 3, ThingType.SHOTGUN_GUY),
        (3, 7, ThingType.IMP),
        (6, 6, ThingType.DEMON),
        (8, 8, ThingType.IMP),
    ]
    
    for x, y, enemy_type in enemy_positions:
        cx, cy = maze.get_cell_center(x, y)
        editor.add_thing(cx, cy, enemy_type, check_geometry=False)
    
    # Add weapons and items
    item_positions = [
        (1, 1, ThingType.SHOTGUN),
        (3, 3, ThingType.MEDIKIT),
        (5, 2, ThingType.BOX_OF_SHELLS),
        (2, 6, ThingType.STIMPACK),
        (7, 7, ThingType.MEDIKIT),
        (4, 8, ThingType.GREEN_ARMOR),
    ]
    
    for x, y, item_type in item_positions:
        cx, cy = maze.get_cell_center(x, y)
        editor.add_thing(cx, cy, item_type, check_geometry=False)
    
    # Save
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "09b_large_maze.wad"
    
    wad.save(str(output_path))
    print(f"Created: {output_path}")
    print("Large 10x10 maze with enemies and items")


if __name__ == "__main__":
    main()
