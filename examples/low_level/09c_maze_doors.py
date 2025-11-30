"""
Example 09c: Maze with Doors
============================

6x6 maze with doors at some passages.
Demonstrates combining procedural maze with door prefabs.
"""

from pathlib import Path
import random
from typing import List, Set, Tuple
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

from doomgen import WADWriter, MapEditor, SectorConfig, ThingType
from doomgen.prefabs import (
    place_door, DoorConfig, apply_door_to_sector
)


class MazeGenerator:
    """Generates random mazes using recursive backtracking."""
    
    def __init__(self, width: int, height: int, cell_size: int = 128):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.wall_thickness = 16
        
        self.walls: List[List[Set[str]]] = [
            [{'N', 'S', 'E', 'W'} for _ in range(width)]
            for _ in range(height)
        ]
        self.visited: List[List[bool]] = [
            [False for _ in range(width)]
            for _ in range(height)
        ]
    
    def generate(self, seed: int = None) -> None:
        if seed is not None:
            random.seed(seed)
        
        start_x = random.randint(0, self.width - 1)
        start_y = random.randint(0, self.height - 1)
        self._carve(start_x, start_y)
    
    def _carve(self, x: int, y: int) -> None:
        self.visited[y][x] = True
        directions = [('N', 0, -1), ('S', 0, 1), ('E', 1, 0), ('W', -1, 0)]
        random.shuffle(directions)
        
        for direction, dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if not self.visited[ny][nx]:
                    self.walls[y][x].discard(direction)
                    opposite = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
                    self.walls[ny][nx].discard(opposite[direction])
                    self._carve(nx, ny)
    
    def get_cell_polygon(self, x: int, y: int) -> Polygon:
        world_x = x * self.cell_size
        world_y = y * self.cell_size
        return box(
            world_x + self.wall_thickness,
            world_y + self.wall_thickness,
            world_x + self.cell_size - self.wall_thickness,
            world_y + self.cell_size - self.wall_thickness
        )
    
    def get_passage_polygon(self, x: int, y: int, direction: str) -> Polygon:
        world_x = x * self.cell_size
        world_y = y * self.cell_size
        wt = self.wall_thickness
        cs = self.cell_size
        
        if direction == 'N':
            return box(world_x + wt, world_y, world_x + cs - wt, world_y + wt)
        elif direction == 'S':
            return box(world_x + wt, world_y + cs - wt, world_x + cs - wt, world_y + cs)
        elif direction == 'E':
            return box(world_x + cs - wt, world_y + wt, world_x + cs, world_y + cs - wt)
        else:
            return box(world_x, world_y + wt, world_x + wt, world_y + cs - wt)
    
    def to_polygon(self) -> Polygon:
        polygons = []
        for y in range(self.height):
            for x in range(self.width):
                polygons.append(self.get_cell_polygon(x, y))
                for direction in ['N', 'S', 'E', 'W']:
                    if direction not in self.walls[y][x]:
                        polygons.append(self.get_passage_polygon(x, y, direction))
        return unary_union(polygons)
    
    def get_random_positions(self, count: int, min_dist: float = 64) -> List[Tuple[float, float]]:
        positions = []
        for _ in range(count * 10):
            if len(positions) >= count:
                break
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            world_x = x * self.cell_size + self.cell_size // 2
            world_y = y * self.cell_size + self.cell_size // 2
            
            too_close = False
            for px, py in positions:
                if ((world_x - px) ** 2 + (world_y - py) ** 2) < min_dist ** 2:
                    too_close = True
                    break
            if not too_close:
                positions.append((world_x, world_y))
        return positions


def main():
    """Create a maze with doors at some passages."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    wad = WADWriter()
    map_data = wad.create_map("MAP01")
    editor = MapEditor(map_data)
    
    # Generate maze
    maze = MazeGenerator(6, 6, cell_size=160)
    maze.generate(seed=99)
    
    maze_poly = maze.to_polygon()
    
    # Find passages for doors
    door_positions = []
    for y in range(maze.height):
        for x in range(maze.width):
            if 'E' not in maze.walls[y][x] and x < maze.width - 1:
                if random.random() < 0.2:
                    door_x = (x + 1) * maze.cell_size
                    door_y = y * maze.cell_size + maze.cell_size // 2
                    door_positions.append((door_x, door_y, "vertical"))
            
            if 'S' not in maze.walls[y][x] and y < maze.height - 1:
                if random.random() < 0.2:
                    door_x = x * maze.cell_size + maze.cell_size // 2
                    door_y = (y + 1) * maze.cell_size
                    door_positions.append((door_x, door_y, "horizontal"))
    
    door_positions = door_positions[:4]
    
    # Cut doors from maze geometry
    door_placements = []
    current_geom = maze_poly
    
    for door_x, door_y, direction in door_positions:
        door_cfg = DoorConfig(width=96, depth=16)
        placement = place_door(current_geom, (door_x, door_y), direction, door_cfg)
        current_geom = placement.modified_geometry
        door_placements.append(placement)
    
    # Sector configs
    room_config = SectorConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLOOR4_8",
        light_level=176
    )
    
    door_sector_config = SectorConfig(
        floor_height=0,
        ceiling_height=0,
        floor_texture="FLOOR4_8",
        light_level=144
    )
    
    # Add maze (may be split by doors)
    if current_geom.geom_type == 'MultiPolygon':
        for poly in current_geom.geoms:
            editor.add_sector_from_polygon(poly, room_config)
    else:
        editor.add_sector_from_polygon(current_geom, room_config)
    
    # Add doors
    for placement in door_placements:
        door_idx = editor.add_sector_from_polygon(
            placement.polygon,
            door_sector_config
        )
        apply_door_to_sector(editor, door_idx, placement.door.config, placement.linedef_action)
    
    # Player and items
    start_x = maze.cell_size // 2
    start_y = maze.cell_size // 2
    editor.add_thing(start_x, start_y, ThingType.PLAYER1_START, check_geometry=False)
    
    exit_x = (maze.width - 1) * maze.cell_size + maze.cell_size // 2
    exit_y = (maze.height - 1) * maze.cell_size + maze.cell_size // 2
    editor.add_thing(exit_x, exit_y, ThingType.BLUE_KEYCARD, check_geometry=False)
    
    positions = maze.get_random_positions(6)
    for x, y in positions:
        editor.add_thing(x, y, ThingType.STIMPACK, check_geometry=False)
    
    wad.save(output_dir / "09c_maze_doors.wad")
    print(f"Created output/09c_maze_doors.wad")
    print(f"  Maze size: {maze.width}x{maze.height}")
    print(f"  Doors: {len(door_placements)}")
    print(f"  Sectors: {len(map_data.sectors)}")
    print("\nLoad with: gzdoom -iwad doom2.wad -file output/09c_maze_doors.wad")


if __name__ == "__main__":
    main()
