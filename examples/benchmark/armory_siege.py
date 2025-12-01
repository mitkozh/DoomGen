#work in progress; doors are still not placed correctly with a corridor; connection needs some refinemenet
"""
Armory Siege Defense - MARL Benchmark Scenario

Scenario Description:
All agents spawn together in a central armory containing limited starting weapons
(2 Shotguns, 1 Chaingun, 50 shells, 30 bullets total). The armory has a vulnerable
Core object (represented by a MapSpot for ACS scripting) that enemies attack.

Three separate supply rooms (A/B/C) are connected to the armory via corridors.
Each room contains different resources that respawn every 300 ticks:
- Room A: Heavy weapons (Rocket Launcher, Plasma Rifle)
- Room B: Ammo (shells, bullets, cells)
- Room C: Health/Armor (Medikits, Armor)

Supply rooms are time-gated - each room's door opens for only 200 ticks (~6 seconds)
at staggered intervals:
- Room A: ticks 0-200, 500-700, 1000-1200, ...
- Room B: ticks 200-400, 700-900, 1200-1400, ...
- Room C: ticks 400-600, 900-1100, 1400-1600, ...

Enemies continuously spawn and attack the Core. Agents must coordinate who goes
to which room and when.

Features demonstrated:
- Structurally random layouts (irregular polygons, varied shapes)
- Mixed corridor styles (straight and L-system)
- ACS scripting for time-gated doors and enemy spawning
- Multiple player starts for MARL
- Enemy spawn points with MapSpots
- Full use of the DoomGen library API
- Safe thing placement inside polygon boundaries
"""

from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
from shapely.geometry import Polygon, Point

from doomgen import (
    DoomMapBuilder,
    RoomConfig,
    ThingType,
    ScriptType,
    ShapeBuilder,
    create_rectangle,
    create_irregular_polygon,
)


# =============================================================================
# Helper Functions for Safe Thing Placement
# =============================================================================

def get_safe_positions_in_polygon(
    polygon: Polygon,
    count: int,
    min_spacing: float = 32.0,
    margin: float = 24.0,
    rng: np.random.Generator = None
) -> List[Tuple[float, float]]:
    """
    Generate safe positions inside a polygon for thing placement.
    
    Uses polygon erosion (buffer inward) to ensure things are placed
    away from walls, then samples random points inside.
    
    Args:
        polygon: The room polygon to place things in.
        count: Number of positions to generate.
        min_spacing: Minimum distance between things.
        margin: Distance from walls (polygon is eroded by this amount).
        rng: Random number generator for reproducibility.
    
    Returns:
        List of (x, y) positions guaranteed to be inside the polygon.
    """
    if rng is None:
        rng = np.random.default_rng()
    
    # Erode polygon to create safe placement area
    safe_area = polygon.buffer(-margin)
    
    # If erosion makes polygon too small, use centroid area
    if safe_area.is_empty or safe_area.area < 100:
        centroid = polygon.centroid
        return [(centroid.x, centroid.y)] * count
    
    # Get bounding box for sampling
    minx, miny, maxx, maxy = safe_area.bounds
    
    positions = []
    max_attempts = count * 50  # Prevent infinite loops
    attempts = 0
    
    while len(positions) < count and attempts < max_attempts:
        attempts += 1
        
        # Random point in bounding box
        x = rng.uniform(minx, maxx)
        y = rng.uniform(miny, maxy)
        point = Point(x, y)
        
        # Check if inside safe area
        if not safe_area.contains(point):
            continue
        
        # Check minimum spacing from existing positions
        too_close = False
        for px, py in positions:
            if np.sqrt((x - px)**2 + (y - py)**2) < min_spacing:
                too_close = True
                break
        
        if not too_close:
            positions.append((x, y))
    
    # If we couldn't generate enough positions, fill with centroid-based positions
    while len(positions) < count:
        centroid = safe_area.centroid
        offset = len(positions) * 16  # Slight offset for each
        angle = len(positions) * (2 * np.pi / count)
        x = centroid.x + offset * np.cos(angle) * 0.3
        y = centroid.y + offset * np.sin(angle) * 0.3
        positions.append((x, y))
    
    return positions


def get_positions_around_center(
    polygon: Polygon,
    count: int,
    radius: float = 50.0,
    margin: float = 24.0
) -> List[Tuple[float, float]]:
    """
    Generate positions arranged in a circle around the polygon centroid.
    
    Useful for player starts and central item placement.
    
    Args:
        polygon: The room polygon.
        count: Number of positions.
        radius: Distance from center.
        margin: Minimum distance from walls.
    
    Returns:
        List of (x, y) positions.
    """
    centroid = polygon.centroid
    safe_area = polygon.buffer(-margin)
    
    positions = []
    for i in range(count):
        angle = (2 * np.pi * i / count) - np.pi / 2  # Start from top
        x = centroid.x + radius * np.cos(angle)
        y = centroid.y + radius * np.sin(angle)
        
        # Ensure position is inside safe area
        point = Point(x, y)
        if safe_area.contains(point):
            positions.append((x, y))
        else:
            # Fallback to centroid with small offset
            x = centroid.x + (i * 20 - count * 10)
            y = centroid.y + (i * 20 - count * 10)
            positions.append((x, y))
    
    return positions


def create_armory_siege(
    seed: Optional[int] = None,
    output_path: str = "output/armory_siege.wad"
) -> Path:
    """
    Create the Armory Siege Defense scenario.
    
    Args:
        seed: Random seed for reproducible layouts (None for random each time)
        output_path: Output WAD file path
    
    Returns:
        Path to the created WAD file
    """
    print("=== Armory Siege Defense - MARL Benchmark ===\n")
    
    # Initialize random generator for structural randomness
    rng = np.random.default_rng(seed)
    
    # Create shape builder to access room polygons for thing placement
    shape_builder = ShapeBuilder(seed=seed)
    
    # Create builder with seed for reproducible geometry
    builder = DoomMapBuilder(seed=seed)
    
    # =========================================================================
    # Layout Constraints
    # =========================================================================
    
    # Minimum distance from armory center to supply room center
    MIN_ROOM_DISTANCE = 500
    MAX_ROOM_DISTANCE = 700
    
    # Armory radius range
    MIN_ARMORY_RADIUS = 300
    MAX_ARMORY_RADIUS = 400
    
    # Supply room size range
    MIN_SUPPLY_ROOM_SIZE = 170
    MAX_SUPPLY_ROOM_SIZE = 230
    
    # =========================================================================
    # Room Configurations with thematic textures
    # =========================================================================
    
    armory_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=160,  # Taller central room
        floor_texture="FLOOR4_8",
        ceiling_texture="CEIL3_5",
        wall_texture="STARTAN2",
        light_level=200  # Well-lit armory
    )
    
    # Supply rooms have slightly different visual themes
    room_a_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT14",  # Tech floor
        ceiling_texture="CEIL3_3",
        wall_texture="TEKWALL4",
        light_level=160  # Dimmer
    )
    
    room_b_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT5_4",  # Metal floor
        ceiling_texture="CEIL3_5",
        wall_texture="STARGR1",
        light_level=144
    )
    
    room_c_cfg = RoomConfig(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLAT5_1",  # Medical floor
        ceiling_texture="CEIL3_1",
        wall_texture="GRAY7",
        light_level=176
    )
    
    # =========================================================================
    # Create Armory (Central Hub) - Using irregular or regular polygon randomly
    # =========================================================================
    
    # Randomly choose between octagon, hexagon, or irregular polygon
    armory_style = rng.choice(["octagon", "hexagon", "irregular"])
    armory_radius = rng.integers(MIN_ARMORY_RADIUS, MAX_ARMORY_RADIUS + 1)
    
    # Create armory polygon for thing placement validation
    if armory_style == "octagon":
        armory_polygon = shape_builder.create_polygon(8, armory_radius, (0, 0))
        builder.add_polygon_room(
            "armory",
            sides=8,
            radius=armory_radius,
            center=(0, 0),
            config=armory_cfg
        )
        print(f"Armory: Regular octagon (radius={armory_radius})")
    elif armory_style == "hexagon":
        armory_polygon = shape_builder.create_polygon(6, armory_radius, (0, 0))
        builder.add_polygon_room(
            "armory",
            sides=6,
            radius=armory_radius,
            center=(0, 0),
            config=armory_cfg
        )
        print(f"Armory: Regular hexagon (radius={armory_radius})")
    else:
        irregularity = 0.1 + rng.random() * 0.15  # 0.1 to 0.25
        sides = rng.integers(6, 10)
        armory_polygon = shape_builder.create_irregular_polygon(
            (0, 0), armory_radius, sides, irregularity
        )
        builder.add_irregular_room(
            "armory",
            radius=armory_radius,
            sides=sides,
            irregularity=irregularity,
            center=(0, 0),
            config=armory_cfg
        )
        print(f"Armory: Irregular polygon (radius={armory_radius}, irregularity={irregularity:.2f})")
    
    # =========================================================================
    # Create Supply Rooms - Each with structural variation
    # =========================================================================
    
    # Room positions at 120-degree intervals around armory
    # Distance is calculated to ensure minimum gap from armory edge
    room_angles = [90, 210, 330]  # Roughly north, southwest, southeast
    
    supply_rooms = [
        ("supply_a", room_a_cfg, room_angles[0], "Heavy Weapons"),
        ("supply_b", room_b_cfg, room_angles[1], "Ammunition"),
        ("supply_c", room_c_cfg, room_angles[2], "Health/Armor"),
    ]
    
    room_centers = {}
    room_polygons = {}  # Store polygons for safe thing placement
    
    for room_name, cfg, angle, desc in supply_rooms:
        # Calculate room size first
        room_size = rng.integers(MIN_SUPPLY_ROOM_SIZE, MAX_SUPPLY_ROOM_SIZE + 1)
        
        # Calculate distance: ensure minimum gap between armory edge and room edge
        # gap = room_distance - armory_radius - room_size
        # We want gap >= corridor_width (80) + buffer (50) = 130
        min_gap = 130
        min_distance = armory_radius + room_size + min_gap
        max_distance = max(min_distance + 150, MAX_ROOM_DISTANCE)
        
        room_distance = rng.integers(min_distance, max_distance + 1)
        
        # Calculate position with slight angle variation
        rad = np.radians(angle + rng.integers(-15, 16))
        cx = room_distance * np.cos(rad)
        cy = room_distance * np.sin(rad)
        room_centers[room_name] = (cx, cy)
        
        # Randomly choose room shape
        shape_type = rng.choice(["rectangle", "irregular", "polygon"])
        
        if shape_type == "rectangle":
            width = room_size + rng.integers(-40, 41)
            height = room_size + rng.integers(-40, 41)
            room_polygons[room_name] = shape_builder.create_rectangle(width, height, (cx, cy))
            builder.add_room(
                room_name,
                width=width,
                height=height,
                center=(cx, cy),
                config=cfg
            )
            print(f"{room_name} ({desc}): Rectangle {width}x{height} at ({cx:.0f}, {cy:.0f}), dist={room_distance}")
        elif shape_type == "irregular":
            irregularity = 0.1 + rng.random() * 0.2
            sides = rng.integers(5, 8)
            room_polygons[room_name] = shape_builder.create_irregular_polygon(
                (cx, cy), room_size, sides, irregularity
            )
            builder.add_irregular_room(
                room_name,
                radius=room_size,
                sides=sides,
                irregularity=irregularity,
                center=(cx, cy),
                config=cfg
            )
            print(f"{room_name} ({desc}): Irregular {sides}-gon at ({cx:.0f}, {cy:.0f}), dist={room_distance}")
        else:
            sides = rng.integers(5, 9)
            room_polygons[room_name] = shape_builder.create_polygon(sides, room_size, (cx, cy))
            builder.add_polygon_room(
                room_name,
                sides=sides,
                radius=room_size,
                center=(cx, cy),
                config=cfg
            )
            print(f"{room_name} ({desc}): Regular {sides}-gon at ({cx:.0f}, {cy:.0f}), dist={room_distance}")
    
    # =========================================================================
    # Connect Rooms with Varied Corridor Styles
    # =========================================================================
    
    corridor_width = 80  # Wide enough for multiple players
    
    # Available L-system grammars for organic corridors
    lsystem_grammars = ["organic", "wavy", "gentle", "serpentine", "wobble"]
    
    # Connect each supply room to armory with different corridor styles
    corridor_styles = [
        rng.choice(["straight", "lsystem"]),
        rng.choice(["straight", "lsystem"]),
        rng.choice(["straight", "lsystem"]),
    ]
    
    corridor_names = ["corridor_a", "corridor_b", "corridor_c"]
    
    for i, (room_name, _, _, _) in enumerate(supply_rooms):
        style = corridor_styles[i]
        name = corridor_names[i]
        
        if style == "lsystem":
            grammar = rng.choice(lsystem_grammars)
            builder.connect(
                "armory", room_name,
                corridor_width=corridor_width,
                name=name,
                style=f"lsystem:{grammar}",
                iterations=2,
                max_deviation=0.15
            )
            print(f"{name}: L-system ({grammar}) connecting armory to {room_name}")
        else:
            builder.connect(
                "armory", room_name,
                corridor_width=corridor_width,
                name=name,
                style="straight"
            )
            print(f"{name}: Straight corridor connecting armory to {room_name}")
    
    # =========================================================================
    # Add Time-Gated Doors at Each Corridor Entrance
    # Door tags: 1 = Room A, 2 = Room B, 3 = Room C
    # =========================================================================
    
    print("\nAdding time-gated doors...")
    
    # Add doors at the supply room end of each corridor
    # These will be controlled by ACS scripts for time-gating
    for i, name in enumerate(corridor_names):
        tag = i + 1  # Tags 1, 2, 3 for rooms A, B, C
        builder.add_corridor_door(
            name,
            end="b",  # Door at supply room side
            width=corridor_width,
            depth=24,
            tag=tag
        )
        print(f"  Door {tag} at {name} (end=b)")
    
    # =========================================================================
    # ACS Scripts for Time-Gated Doors and Game Logic
    # =========================================================================
    
    print("\nGenerating ACS scripts...")
    
    # Add defines for timing
    builder.add_acs_define("DOOR_OPEN_DURATION", 200)  # ~6 seconds open
    builder.add_acs_define("CYCLE_LENGTH", 500)
    builder.add_acs_define("DOOR_A_TAG", 1)
    builder.add_acs_define("DOOR_B_TAG", 2)
    builder.add_acs_define("DOOR_C_TAG", 3)
    
    # Enemy spawn tags
    builder.add_acs_define("SPAWN_TAG_1", 10)
    builder.add_acs_define("SPAWN_TAG_2", 11)
    builder.add_acs_define("SPAWN_TAG_3", 12)
    builder.add_acs_define("SPAWN_TAG_4", 13)
    
    # Global variables
    builder.add_acs_global_var("gameTime", "int", 0)
    builder.add_acs_global_var("doorAOpen", "int", 0)
    builder.add_acs_global_var("doorBOpen", "int", 0)
    builder.add_acs_global_var("doorCOpen", "int", 0)
    builder.add_acs_global_var("waveNumber", "int", 0)
    
    # Main game controller script
    main_script = '''
// Welcome message
Delay(35);
Print(s:"ARMORY SIEGE DEFENSE");
Delay(70);
Print(s:"Defend the Core! Collect supplies from rooms A, B, C.");
Delay(70);
Print(s:"Doors open on rotation: A, B, C, repeat...");
Delay(105);

// Start door controller and spawner
ACS_Execute(2, 0);  // Door controller
ACS_Execute(3, 0);  // Enemy spawner

// Main game loop - track time
while(true) {
    Delay(1);
    gameTime = gameTime + 1;
}
'''
    builder.add_acs_script(ScriptType.OPEN, main_script)
    
    # Door controller script (Script 2)
    door_script = '''
// Time-gated door controller
// Room A: 0-200, 500-700, 1000-1200, ...
// Room B: 200-400, 700-900, 1200-1400, ...
// Room C: 400-600 (within first cycle), 900-1100, 1400-1600, ...

while(true) {
    int cyclePos = gameTime % CYCLE_LENGTH;
    
    // Door A: Open at cycle positions 0-200
    if (cyclePos >= 0 && cyclePos < DOOR_OPEN_DURATION && doorAOpen == 0) {
        Door_Open(DOOR_A_TAG, 64);
        doorAOpen = 1;
        Print(s:"Room A OPEN - Heavy Weapons!");
    }
    if (cyclePos >= DOOR_OPEN_DURATION && doorAOpen == 1) {
        Door_Close(DOOR_A_TAG, 64);
        doorAOpen = 0;
        Print(s:"Room A LOCKED");
    }
    
    // Door B: Open at cycle positions 200-400
    if (cyclePos >= 200 && cyclePos < 400 && doorBOpen == 0) {
        Door_Open(DOOR_B_TAG, 64);
        doorBOpen = 1;
        Print(s:"Room B OPEN - Ammunition!");
    }
    if (cyclePos >= 400 && cyclePos < 500 && doorBOpen == 1) {
        Door_Close(DOOR_B_TAG, 64);
        doorBOpen = 0;
        Print(s:"Room B LOCKED");
    }
    
    // Door C: Open at cycle positions 400-600 (wraps around)
    // For simplicity in first 500 ticks: 400-500 open
    if (cyclePos >= 400 && doorCOpen == 0) {
        Door_Open(DOOR_C_TAG, 64);
        doorCOpen = 1;
        Print(s:"Room C OPEN - Health/Armor!");
    }
    if (cyclePos < 100 && cyclePos > 0 && doorCOpen == 1) {
        Door_Close(DOOR_C_TAG, 64);
        doorCOpen = 0;
        Print(s:"Room C LOCKED");
    }
    
    Delay(1);
}
'''
    builder.add_acs_script(ScriptType.OPEN, door_script, number=2)
    
    # Enemy spawner script (Script 3)
    enemy_script = '''
// Enemy spawner - waves of increasing difficulty
Delay(175);  // 5 seconds before first wave

while(true) {
    waveNumber = waveNumber + 1;
    
    // Announce wave
    if (waveNumber == 1) {
        Print(s:"WAVE 1 - Zombies incoming!");
    }
    else if (waveNumber == 2) {
        Print(s:"WAVE 2 - Imps joining the fight!");
    }
    else if (waveNumber == 3) {
        Print(s:"WAVE 3 - Demons attack!");
    }
    else if (waveNumber == 4) {
        Print(s:"WAVE 4 - Heavy resistance!");
    }
    else {
        Print(s:"WAVE ", d:waveNumber, s:" - Endless assault!");
    }
    
    // Spawn enemies at MapSpots (spawn points around the map)
    // SpawnSpot takes class name and spot TID
    SpawnSpot("Zombieman", SPAWN_TAG_1, 0, 0);
    SpawnSpot("Zombieman", SPAWN_TAG_2, 0, 0);
    
    if (waveNumber >= 2) {
        SpawnSpot("DoomImp", SPAWN_TAG_3, 0, 0);
        SpawnSpot("DoomImp", SPAWN_TAG_4, 0, 0);
    }
    
    if (waveNumber >= 3) {
        SpawnSpot("Demon", SPAWN_TAG_1, 0, 0);
        SpawnSpot("Demon", SPAWN_TAG_2, 0, 0);
    }
    
    if (waveNumber >= 4) {
        SpawnSpot("ChaingunGuy", SPAWN_TAG_3, 0, 0);
        SpawnSpot("ChaingunGuy", SPAWN_TAG_4, 0, 0);
    }
    
    // Wait between waves (scales with wave number, minimum 8 seconds)
    int waveDelay = 420 - (waveNumber * 35);
    if (waveDelay < 280) { waveDelay = 280; }
    Delay(waveDelay);
}
'''
    builder.add_acs_script(ScriptType.OPEN, enemy_script, number=3)
    
    # =========================================================================
    # Place Things - Starting Equipment in Armory (Safe Placement)
    # =========================================================================
    
    print("\nPlacing things (safe placement inside polygons)...")
    
    # Player starts (4 players for MARL, arranged around center)
    player_positions = get_positions_around_center(armory_polygon, 4, radius=60, margin=32)
    for i, (px, py) in enumerate(player_positions):
        if i == 0:
            builder.add_player_start("armory", position=(px, py), angle=0)
        else:
            thing_type = [ThingType.PLAYER2_START, ThingType.PLAYER3_START, ThingType.PLAYER4_START][i-1]
            builder.add_thing("armory", thing_type, position=(px, py), angle=0)
    print("  4 player starts in armory (safe placement)")
    
    # Get safe positions for weapons and ammo in armory
    weapon_positions = get_safe_positions_in_polygon(armory_polygon, 3, min_spacing=48, margin=40, rng=rng)
    ammo_positions = get_safe_positions_in_polygon(armory_polygon, 7, min_spacing=32, margin=40, rng=rng)
    
    # Starting weapons in armory (limited!)
    builder.add_thing("armory", ThingType.SHOTGUN, position=weapon_positions[0], angle=90)
    builder.add_thing("armory", ThingType.SHOTGUN, position=weapon_positions[1], angle=270)
    builder.add_thing("armory", ThingType.CHAINGUN, position=weapon_positions[2], angle=180)
    print("  Starting weapons: 2 Shotguns, 1 Chaingun")
    
    # Starting ammo in armory (limited!)
    builder.add_thing("armory", ThingType.BOX_OF_SHELLS, position=ammo_positions[0])  # 20 shells
    builder.add_thing("armory", ThingType.SHELLS, position=ammo_positions[1])  # 4 shells  
    builder.add_thing("armory", ThingType.SHELLS, position=ammo_positions[2])  # 4 shells
    builder.add_thing("armory", ThingType.SHELLS, position=ammo_positions[3])  # 4 shells = 32 total
    builder.add_thing("armory", ThingType.CLIP, position=ammo_positions[4])  # 10 bullets
    builder.add_thing("armory", ThingType.CLIP, position=ammo_positions[5])  # 10 bullets
    builder.add_thing("armory", ThingType.CLIP, position=ammo_positions[6])  # 10 bullets = 30 total
    print("  Starting ammo: ~32 shells, 30 bullets")
    
    # Core marker at armory centroid
    centroid = armory_polygon.centroid
    builder.add_thing("armory", ThingType.CANDELABRA, position=(centroid.x, centroid.y))
    print("  Core marker (candelabra) at center")
    
    # =========================================================================
    # Place Things - Supply Room A (Heavy Weapons) - Safe Placement
    # =========================================================================
    
    room_a_poly = room_polygons["supply_a"]
    room_a_positions = get_safe_positions_in_polygon(room_a_poly, 4, min_spacing=40, margin=32, rng=rng)
    
    builder.add_thing("supply_a", ThingType.ROCKET_LAUNCHER, position=room_a_positions[0])
    builder.add_thing("supply_a", ThingType.PLASMA_RIFLE, position=room_a_positions[1])
    builder.add_thing("supply_a", ThingType.BOX_OF_ROCKETS, position=room_a_positions[2])
    builder.add_thing("supply_a", ThingType.ENERGY_CELL_PACK, position=room_a_positions[3])
    print("  Room A: Rocket Launcher, Plasma Rifle, rockets, cells (safe placement)")
    
    # =========================================================================
    # Place Things - Supply Room B (Ammunition) - Safe Placement
    # =========================================================================
    
    room_b_poly = room_polygons["supply_b"]
    room_b_positions = get_safe_positions_in_polygon(room_b_poly, 6, min_spacing=32, margin=32, rng=rng)
    
    builder.add_thing("supply_b", ThingType.BOX_OF_SHELLS, position=room_b_positions[0])
    builder.add_thing("supply_b", ThingType.BOX_OF_SHELLS, position=room_b_positions[1])
    builder.add_thing("supply_b", ThingType.BOX_OF_BULLETS, position=room_b_positions[2])
    builder.add_thing("supply_b", ThingType.BOX_OF_BULLETS, position=room_b_positions[3])
    builder.add_thing("supply_b", ThingType.BOX_OF_ROCKETS, position=room_b_positions[4])
    builder.add_thing("supply_b", ThingType.ENERGY_CELL_PACK, position=room_b_positions[5])
    print("  Room B: Shells, bullets, rockets, cells (safe placement)")
    
    # =========================================================================
    # Place Things - Supply Room C (Health/Armor) - Safe Placement
    # =========================================================================
    
    room_c_poly = room_polygons["supply_c"]
    room_c_positions = get_safe_positions_in_polygon(room_c_poly, 6, min_spacing=32, margin=32, rng=rng)
    
    builder.add_thing("supply_c", ThingType.MEDIKIT, position=room_c_positions[0])
    builder.add_thing("supply_c", ThingType.MEDIKIT, position=room_c_positions[1])
    builder.add_thing("supply_c", ThingType.SOULSPHERE, position=room_c_positions[2])
    builder.add_thing("supply_c", ThingType.BLUE_ARMOR, position=room_c_positions[3])
    builder.add_thing("supply_c", ThingType.STIMPACK, position=room_c_positions[4])
    builder.add_thing("supply_c", ThingType.STIMPACK, position=room_c_positions[5])
    print("  Room C: Medikits, Soulsphere, Blue Armor, Stimpacks (safe placement)")
    
    # =========================================================================
    # Enemy Spawn Points (MapSpots inside armory near perimeter)
    # =========================================================================
    
    # Place spawn points inside the armory, near the edges but safely within bounds
    # Use a ring pattern around the armory for enemy spawns
    spawn_positions = get_safe_positions_in_polygon(
        armory_polygon, 4, min_spacing=100, margin=48, rng=rng
    )
    
    # Add MapSpots for enemy spawning (TID 10-13)
    for i, (sx, sy) in enumerate(spawn_positions):
        tid = 10 + i
        # MapSpot uses angle field as TID in ZDoom/GZDoom
        builder.add_thing("armory", ThingType.MAP_SPOT, position=(sx, sy), angle=tid)
    print(f"  {len(spawn_positions)} enemy spawn points (MapSpots TID 10-13, safe placement)")
    
    # =========================================================================
    # Add some initial enemies inside the armory
    # =========================================================================
    
    # Get positions for initial enemies
    enemy_positions = get_safe_positions_in_polygon(
        armory_polygon, 2, min_spacing=80, margin=60, rng=rng
    )
    
    for ex, ey in enemy_positions:
        # Face toward center
        cx, cy = armory_polygon.centroid.x, armory_polygon.centroid.y
        angle = int(np.degrees(np.arctan2(cy - ey, cx - ex))) % 360
        builder.add_thing("armory", ThingType.ZOMBIEMAN, position=(ex, ey), angle=angle)
    print(f"  {len(enemy_positions)} initial zombiemen (safe placement)")
    
    # =========================================================================
    # Add Lighting Effects to rooms
    # =========================================================================
    
    builder.add_lighting("armory", effect="blink_random", light_level=200)
    
    # =========================================================================
    # Save the WAD
    # =========================================================================
    
    print("\n" + "=" * 50)
    output_file = builder.save(output_path)
    
    print("\n" + "=" * 50)
    print("ARMORY SIEGE DEFENSE - SCENARIO SUMMARY")
    print("=" * 50)
    print(f"Seed: {seed}")
    print(f"Output: {output_file}")
    print("\nRooms:")
    print("  - Armory (center): Starting weapons, Core marker, 4 player spawns")
    print("  - Supply A (north): Heavy weapons (Rocket Launcher, Plasma)")
    print("  - Supply B (southwest): Bulk ammunition")
    print("  - Supply C (southeast): Health and armor")
    print("\nDoor Schedule (500-tick cycle):")
    print("  - Room A: Open ticks 0-200")
    print("  - Room B: Open ticks 200-400")
    print("  - Room C: Open ticks 400-600 (wraps)")
    print("\nEnemy Waves: Every ~12 seconds, increasing difficulty")
    print("\nLoad with: gzdoom -iwad doom2.wad -file", output_file)
    
    return output_file


def main():
    """Main entry point - create scenario with random seed for variety."""
    import sys
    
    # Use command-line seed if provided, otherwise random
    if len(sys.argv) > 1:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            seed = None
    else:
        seed = None  # Random layout each time
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    create_armory_siege(
        seed=seed,
        output_path=str(output_dir / "armory_siege.wad")
    )


if __name__ == "__main__":
    main()
