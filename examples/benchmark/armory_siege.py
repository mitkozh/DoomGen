#not working; very rought; if you have time you can try to fix it later
# """
# Armory Siege Defense
# ================================

# MARL benchmark: Agents spawn in central armory with limited resources,
# defend while making supply runs to three time-gated rooms.

# Features:
# - Irregular polygon shapes for all rooms
# - L-system corridors for organic winding paths
# - Time-gated doors controlled by ACS scripts
# - Room A/B/C open at different intervals (cycling)

# Scenario Description:
# - All agents spawn together in a central armory containing limited starting 
#   weapons (2 Shotguns, 1 Chaingun, 50 shells, 30 bullets total)
# - Three separate supply rooms (A/B/C) are connected to the armory via L-system corridors
# - Each room contains different resources:
#   - Room A: Heavy weapons (Rocket Launcher, Plasma Rifle, ammo)
#   - Room B: Ammo (Shells, Bullets, Rockets, Cells)
#   - Room C: Health/Armor (Medikits, Green/Blue Armor, Soulsphere)
# - Supply rooms are time-gated:
#   - Room A: ticks 0-200, 500-700, 1000-1200
#   - Room B: ticks 200-400, 700-900
#   - Room C: ticks 400-600, 900-1100
# - Enemies spawn and attack the core position
# """

# from pathlib import Path
# import math
# from typing import Optional

# import numpy as np
# from numpy.random import Generator

# from doomgen import (
#     WADWriter, MapEditor, SectorConfig, WallConfig, ThingType, ShapeBuilder, 
#     MapBuilder, SlotType, DoorAction
# )
# from doomgen.prefabs import DoorConfig, DoorType, apply_door_to_sector
# from doomgen.logic.acs_builder import ACSBuilder, ScriptType


# # =============================================================================
# # Configuration
# # =============================================================================

# ARMORY_CONFIG = {
#     "min_radius": 500,
#     "max_radius": 650,
#     "floor_texture": "FLAT5_4",
#     "ceiling_texture": "CEIL3_5",
#     "wall_texture": "STARGR1",
#     "ceiling_height": 144,
#     "light_level": 200,
# }

# SUPPLY_ROOM_CONFIG = {
#     "min_radius": 200,
#     "max_radius": 300,
#     "min_distance": 1000,
#     "max_distance": 1300,
#     "corridor_width": 96,
# }

# CORRIDOR_CONFIG = {
#     "floor_texture": "FLAT5_4",  # Use simpler flat texture to avoid tiling issues
#     "ceiling_texture": "CEIL3_5",
#     "wall_texture": "STONE2",  # Use stone texture that tiles better on irregular walls
#     "ceiling_height": 112,
#     "light_level": 128,
# }

# ROOM_THEMES = {
#     "A": {
#         "floor_texture": "CEIL5_2",
#         "ceiling_texture": "CEIL3_5",
#         "wall_texture": "STARTAN2",
#         "light_level": 160,
#         "description": "Heavy Weapons",
#     },
#     "B": {
#         "floor_texture": "FLAT5_1",
#         "ceiling_texture": "CEIL3_5",
#         "wall_texture": "STARTAN2",
#         "light_level": 176,
#         "description": "Ammunition",
#     },
#     "C": {
#         "floor_texture": "FLAT14",
#         "ceiling_texture": "CEIL3_5",
#         "wall_texture": "STARTAN2",
#         "light_level": 192,
#         "description": "Health/Armor",
#     },
# }


# # =============================================================================
# # Item/Enemy Configuration
# # =============================================================================

# def get_supply_room_items(room_type: str) -> list[ThingType]:
#     """Get the items to place in each supply room."""
#     items = {
#         "A": [
#             ThingType.ROCKET_LAUNCHER,
#             ThingType.PLASMA_RIFLE,
#             ThingType.ENERGY_CELL_PACK,
#             ThingType.BOX_OF_ROCKETS,
#         ],
#         "B": [
#             ThingType.BOX_OF_SHELLS,
#             ThingType.BOX_OF_SHELLS,
#             ThingType.BOX_OF_BULLETS,
#             ThingType.BOX_OF_BULLETS,
#             ThingType.BOX_OF_ROCKETS,
#             ThingType.ENERGY_CELL_PACK,
#         ],
#         "C": [
#             ThingType.MEDIKIT,
#             ThingType.MEDIKIT,
#             ThingType.MEDIKIT,
#             ThingType.GREEN_ARMOR,
#             ThingType.BLUE_ARMOR,
#             ThingType.SOULSPHERE,
#         ],
#     }
#     return items.get(room_type, [])


# def get_armory_starter_items() -> list[tuple[ThingType, tuple[float, float]]]:
#     """Get starter items for the armory: 2 shotguns, 1 chaingun, shells, bullets."""
#     return [
#         (ThingType.SHOTGUN, (-80, 80)),
#         (ThingType.SHOTGUN, (80, 80)),
#         (ThingType.CHAINGUN, (0, -100)),
#         (ThingType.BOX_OF_SHELLS, (-100, -80)),
#         (ThingType.BOX_OF_SHELLS, (100, -80)),
#         (ThingType.BOX_OF_BULLETS, (-60, -120)),
#         (ThingType.BOX_OF_BULLETS, (60, -120)),
#         (ThingType.MEDIKIT, (-120, 0)),
#         (ThingType.MEDIKIT, (120, 0)),
#     ]


# def get_enemy_wave(rng: Generator, difficulty: str = "medium") -> list[tuple[ThingType, int]]:
#     """Get enemy wave configuration based on difficulty."""
#     waves = {
#         "easy": [
#             (ThingType.ZOMBIEMAN, 4),
#             (ThingType.SHOTGUN_GUY, 2),
#             (ThingType.IMP, 3),
#         ],
#         "medium": [
#             (ThingType.ZOMBIEMAN, 6),
#             (ThingType.SHOTGUN_GUY, 4),
#             (ThingType.IMP, 5),
#             (ThingType.DEMON, 2),
#         ],
#         "hard": [
#             (ThingType.SHOTGUN_GUY, 6),
#             (ThingType.CHAINGUNNER, 3),
#             (ThingType.IMP, 6),
#             (ThingType.DEMON, 4),
#             (ThingType.HELL_KNIGHT, 2),
#         ],
#     }
#     return waves.get(difficulty, waves["medium"])


# # =============================================================================
# # ACS Script for Time-Gated Doors
# # =============================================================================

# def create_timed_door_acs(door_tags: dict[str, int], difficulty: str = "medium") -> ACSBuilder:
#     """
#     Create ACS scripts for time-gated doors and enemy spawning.
    
#     Door timing (tics, 35 tics = 1 second):
#     - Room A: 0-200, 500-700, 1000-1200 (heavy weapons)
#     - Room B: 200-400, 700-900 (ammo)
#     - Room C: 400-600, 900-1100 (health/armor)
    
#     Enemy spawning:
#     - Waves spawn periodically from spawn spots (TID 100+)
    
#     The cycle repeats every 1200 tics (~34 seconds).
#     """
#     acs = ACSBuilder()
#     acs.add_include("zcommon.acs")
    
#     # Define door tags
#     acs.add_define("DOOR_A_TAG", door_tags["A"])
#     acs.add_define("DOOR_B_TAG", door_tags["B"])
#     acs.add_define("DOOR_C_TAG", door_tags["C"])
#     acs.add_define("CYCLE_LENGTH", 1200)
    
#     # Enemy type IDs (Doom thing types)
#     acs.add_define("T_ZOMBIEMAN", 3004)
#     acs.add_define("T_SHOTGUNGUY", 9)
#     acs.add_define("T_IMP", 3001)
#     acs.add_define("T_DEMON", 3002)
#     acs.add_define("T_HELLKNIGHT", 69)
#     acs.add_define("T_CHAINGUNNER", 65)
    
#     # Spawn spot TID
#     acs.add_define("SPAWN_SPOT_TID", 100)
    
#     # Enemy counts based on difficulty
#     if difficulty == "easy":
#         acs.add_define("WAVE_ZOMBIES", 2)
#         acs.add_define("WAVE_SHOTGUNNERS", 1)
#         acs.add_define("WAVE_IMPS", 2)
#         acs.add_define("WAVE_DEMONS", 0)
#         acs.add_define("WAVE_HEAVY", 0)
#     elif difficulty == "hard":
#         acs.add_define("WAVE_ZOMBIES", 3)
#         acs.add_define("WAVE_SHOTGUNNERS", 2)
#         acs.add_define("WAVE_IMPS", 3)
#         acs.add_define("WAVE_DEMONS", 2)
#         acs.add_define("WAVE_HEAVY", 1)
#     else:  # medium
#         acs.add_define("WAVE_ZOMBIES", 2)
#         acs.add_define("WAVE_SHOTGUNNERS", 2)
#         acs.add_define("WAVE_IMPS", 2)
#         acs.add_define("WAVE_DEMONS", 1)
#         acs.add_define("WAVE_HEAVY", 0)
    
#     # Door timing script - runs continuously
#     door_script = """
# int tick;
# int cycle_tick;

# // Initial delay and announcement
# Delay(35);
# Print(s:"ARMORY SIEGE DEFENSE");
# Delay(70);
# Print(s:"Defend the core! Supply rooms open on rotation.");
# Delay(105);
# Print(s:"Room A: Heavy Weapons | Room B: Ammo | Room C: Health");
# Delay(70);

# while (true)
# {
#     tick = Timer();
#     cycle_tick = tick % CYCLE_LENGTH;
    
#     // Room A: 0-200, 500-700, 1000-1200 (Heavy Weapons)
#     if ((cycle_tick >= 0 && cycle_tick < 200) ||
#         (cycle_tick >= 500 && cycle_tick < 700) ||
#         (cycle_tick >= 1000 && cycle_tick < 1200))
#     {
#         Door_Open(DOOR_A_TAG, 32);
#     }
#     else
#     {
#         Door_Close(DOOR_A_TAG, 32);
#     }
    
#     // Room B: 200-400, 700-900 (Ammo)
#     if ((cycle_tick >= 200 && cycle_tick < 400) ||
#         (cycle_tick >= 700 && cycle_tick < 900))
#     {
#         Door_Open(DOOR_B_TAG, 32);
#     }
#     else
#     {
#         Door_Close(DOOR_B_TAG, 32);
#     }
    
#     // Room C: 400-600, 900-1100 (Health/Armor)
#     if ((cycle_tick >= 400 && cycle_tick < 600) ||
#         (cycle_tick >= 900 && cycle_tick < 1100))
#     {
#         Door_Open(DOOR_C_TAG, 32);
#     }
#     else
#     {
#         Door_Close(DOOR_C_TAG, 32);
#     }
    
#     Delay(1);
# }
# """
#     acs.add_script(ScriptType.OPEN, door_script, number=1)
    
#     # Enemy spawning script
#     spawn_script = """
# int i;
# int wave;

# // Wait for game to start
# Delay(35 * 5);  // 5 second delay before first wave

# wave = 0;
# while (true)
# {
#     wave = wave + 1;
#     Print(s:"Wave ", d:wave, s:" incoming!");
#     Delay(35);  // Brief pause after announcement
    
#     // Spawn zombies
#     for (i = 0; i < WAVE_ZOMBIES; i++)
#     {
#         SpawnSpot("ZombieMan", SPAWN_SPOT_TID, 0, 0);
#         Delay(5);
#     }
    
#     // Spawn shotgun guys
#     for (i = 0; i < WAVE_SHOTGUNNERS; i++)
#     {
#         SpawnSpot("ShotgunGuy", SPAWN_SPOT_TID, 0, 0);
#         Delay(5);
#     }
    
#     // Spawn imps
#     for (i = 0; i < WAVE_IMPS; i++)
#     {
#         SpawnSpot("DoomImp", SPAWN_SPOT_TID, 0, 0);
#         Delay(5);
#     }
    
#     // Spawn demons
#     for (i = 0; i < WAVE_DEMONS; i++)
#     {
#         SpawnSpot("Demon", SPAWN_SPOT_TID, 0, 0);
#         Delay(5);
#     }
    
#     // Spawn heavy enemies (hell knights on hard)
#     for (i = 0; i < WAVE_HEAVY; i++)
#     {
#         SpawnSpot("HellKnight", SPAWN_SPOT_TID, 0, 0);
#         Delay(5);
#     }
    
#     // Wait before next wave (about 20 seconds)
#     Delay(35 * 20);
# }
# """
#     acs.add_script(ScriptType.OPEN, spawn_script, number=2)
    
#     return acs


# # =============================================================================
# # Helper Functions
# # =============================================================================

# # =============================================================================
# # Main Map Creation
# # =============================================================================

# def create_armory_siege(
#     seed: Optional[int] = None,
#     output_path: Optional[str] = None,
#     difficulty: str = "medium",
#     num_players: int = 4,
# ) -> tuple:
#     """
#     Create the Armory Siege Defense scenario.
    
#     Args:
#         seed: Random seed for reproducibility.
#         output_path: Path to save the WAD file.
#         difficulty: Enemy difficulty ("easy", "medium", "hard").
#         num_players: Number of player starts (1-4).
    
#     Returns:
#         Tuple of (WADWriter, MapData, stats dict).
#     """
#     rng = np.random.default_rng(seed)
#     shape_builder = ShapeBuilder(rng=rng)
    
#     # =========================================================================
#     # Use MapBuilder for all geometry (simplified API)
#     # =========================================================================
    
#     map_builder = MapBuilder(grid_size=8, rng=rng)
    
#     # Central armory (irregular octagon/hexagon)
#     armory_radius = rng.uniform(ARMORY_CONFIG["min_radius"], ARMORY_CONFIG["max_radius"])
#     armory_sides = rng.choice([6, 7, 8])
#     armory_irregularity = rng.uniform(0.15, 0.3)
    
#     armory_poly = shape_builder.create_irregular_polygon(
#         center=(0, 0),
#         radius=armory_radius,
#         sides=armory_sides,
#         irregularity=armory_irregularity,
#         grid_size=8
#     )
#     map_builder.add_room("armory", armory_poly)
    
#     # Supply rooms with irregular shapes
#     base_angles = [0, 2 * math.pi / 3, 4 * math.pi / 3]  # 120 degrees apart
#     angle_jitter = math.pi / 8  # ±22.5 degrees
    
#     # Pick a random grammar for corridor variety
#     lsystem_grammars = ["gentle", "wobble", "kinked", "direct", "wavy", "koch", "serpentine"]
#     #testing
    
#     supply_rooms: dict[str, dict] = {}
    
#     for i, label in enumerate(["A", "B", "C"]):
#         # Position with some randomness
#         angle = base_angles[i] + rng.uniform(-angle_jitter, angle_jitter)
#         distance = rng.uniform(
#             SUPPLY_ROOM_CONFIG["min_distance"],
#             SUPPLY_ROOM_CONFIG["max_distance"]
#         )
#         x = distance * math.cos(angle)
#         y = distance * math.sin(angle)
        
#         # Create irregular polygon for supply room
#         radius = rng.uniform(
#             SUPPLY_ROOM_CONFIG["min_radius"],
#             SUPPLY_ROOM_CONFIG["max_radius"]
#         )
#         sides = rng.choice([5, 6, 7, 8])
#         irregularity = rng.uniform(0.15, 0.35)
        
#         supply_poly = shape_builder.create_irregular_polygon(
#             center=(x, y),
#             radius=radius,
#             sides=sides,
#             irregularity=irregularity,
#             grid_size=8
#         )
        
#         room_name = f"supply_{label}"
#         map_builder.add_room(room_name, supply_poly)
        
#         # Store room info
#         supply_rooms[label] = {
#             "name": room_name,
#             "center": (x, y),
#             "angle": angle,
#             "radius": radius,
#         }
        
#         # Pick a different grammar for each corridor for variety
#         grammar = rng.choice(lsystem_grammars)
        
#         # Add L-system corridor with automatic boundary detection
#         corridor_name = f"corridor_{label}"
#         map_builder.add_corridor(
#             room_a="armory",
#             room_b=room_name,
#             name=corridor_name,
#             width=SUPPLY_ROOM_CONFIG["corridor_width"],
#             style=f"lsystem:{grammar}",
#             iterations=2,
#             seed=seed + i if seed else None
#         )
        
#         # Add door at armory entrance (end="a" is the first room = armory)
#         # The API automatically calculates position and direction
#         map_builder.add_corridor_door(
#             corridor_name,
#             end="a",
#             width=SUPPLY_ROOM_CONFIG["corridor_width"],
#             depth=16,
#             tag=i + 1  # Door tags: A=1, B=2, C=3
#         )
    
#     # Build the geometry (CSG operations)
#     result = map_builder.build()
    
#     if not result.is_valid:
#         print(f"Warning: MapBuilder had errors: {result.errors}")
    
#     # =========================================================================
#     # Create WAD and Sectors
#     # =========================================================================
    
#     wad = WADWriter()
#     map_data = wad.create_map("MAP01")
#     editor = MapEditor(map_data)
    
#     # Armory sector
#     armory_sector_cfg = SectorConfig(
#         floor_height=0,
#         ceiling_height=ARMORY_CONFIG["ceiling_height"],
#         floor_texture=ARMORY_CONFIG["floor_texture"],
#         ceiling_texture=ARMORY_CONFIG["ceiling_texture"],
#         light_level=ARMORY_CONFIG["light_level"]
#     )
#     armory_wall_cfg = WallConfig(
#         middle_texture=ARMORY_CONFIG["wall_texture"],
#         upper_texture=ARMORY_CONFIG["wall_texture"],
#         lower_texture=ARMORY_CONFIG["wall_texture"],
#     )
#     editor.add_sector_from_polygon(result.rooms["armory"], armory_sector_cfg, armory_wall_cfg)
    
#     # Corridor sectors
#     corridor_sector_cfg = SectorConfig(
#         floor_height=0,
#         ceiling_height=CORRIDOR_CONFIG["ceiling_height"],
#         floor_texture=CORRIDOR_CONFIG["floor_texture"],
#         ceiling_texture=CORRIDOR_CONFIG["ceiling_texture"],
#         light_level=CORRIDOR_CONFIG["light_level"]
#     )
#     corridor_wall_cfg = WallConfig(
#         middle_texture=CORRIDOR_CONFIG["wall_texture"],
#         upper_texture=CORRIDOR_CONFIG["wall_texture"],
#         lower_texture=CORRIDOR_CONFIG["wall_texture"],
#     )
    
#     for corridor in result.corridors:
#         editor.add_sector_from_polygon(corridor.polygon, corridor_sector_cfg, corridor_wall_cfg)
    
#     # Supply room sectors
#     for label, room_info in supply_rooms.items():
#         theme = ROOM_THEMES[label]
#         room_sector_cfg = SectorConfig(
#             floor_height=0,
#             ceiling_height=128,
#             floor_texture=theme["floor_texture"],
#             ceiling_texture=theme["ceiling_texture"],
#             light_level=theme["light_level"]
#         )
#         room_wall_cfg = WallConfig(
#             middle_texture=theme["wall_texture"],
#             upper_texture=theme["wall_texture"],
#             lower_texture=theme["wall_texture"],
#         )
#         editor.add_sector_from_polygon(
#             result.rooms[room_info["name"]], room_sector_cfg, room_wall_cfg
#         )
    
#     # =========================================================================
#     # Add Doors (with sector tags for ACS control)
#     # =========================================================================
    
#     # Door ceiling starts at floor level (closed), ACS will open it
#     # The door texture needs to show when closed
#     door_sector_cfg = SectorConfig(
#         floor_height=0,
#         ceiling_height=0,  # Starts closed (ceiling at floor level)
#         floor_texture="FLAT5_4",
#         ceiling_texture="FLAT5_4",
#         light_level=160
#     )
#     # Upper texture shows when door is closed (between door ceiling and adjacent ceiling)
#     door_wall_cfg = WallConfig(
#         middle_texture="-",  # No middle texture needed
#         upper_texture="BIGDOOR2",  # This is the visible door texture
#         lower_texture="-"
#     )
    
#     # Use doors from MapBuilder result (automatically positioned via add_corridor_door)
#     for slot in result.slots:
#         if slot.slot_type == SlotType.DOOR:
#             door_idx = editor.add_sector_from_polygon(
#                 slot.polygon, door_sector_cfg, door_wall_cfg
#             )
            
#             # Set sector tag for ACS control (from metadata)
#             if slot.metadata.get("tag"):
#                 map_data.sectors[door_idx]['tag'] = slot.metadata["tag"]
            
#             # Apply door properties (REMOTE type since ACS controls it)
#             door_config = DoorConfig(
#                 width=slot.width,
#                 depth=slot.depth,
#                 door_type=DoorType.REMOTE
#             )
#             # Note: For ACS-controlled doors, we don't use normal door actions
#             # The ACS script uses Door_Open/Door_Close with the sector tag
#             apply_door_to_sector(editor, door_idx, door_config, DoorAction.SR_OPEN_WAIT_CLOSE)
    
#     # =========================================================================
#     # Place Things
#     # =========================================================================
    
#     # Player spawns in armory
#     player_starts = [
#         ThingType.PLAYER1_START,
#         ThingType.PLAYER2_START,
#         ThingType.PLAYER3_START,
#         ThingType.PLAYER4_START
#     ]
    
#     for i in range(min(num_players, 4)):
#         if num_players == 1:
#             # Single player at center
#             editor.add_thing(0, 0, player_starts[i], angle=0, check_geometry=False)
#         else:
#             # Multiple players in a circle
#             angle = (i / num_players) * 2 * math.pi
#             x = 64 * math.cos(angle)
#             y = 64 * math.sin(angle)
#             facing = int(math.degrees(angle + math.pi)) % 360
#             editor.add_thing(x, y, player_starts[i], angle=facing, check_geometry=False)
    
#     # Starter items in armory
#     for item_type, (x, y) in get_armory_starter_items():
#         editor.add_thing(x, y, item_type, check_geometry=False)
    
#     # Items in supply rooms
#     for label, room_info in supply_rooms.items():
#         cx, cy = room_info["center"]
#         items = get_supply_room_items(label)
        
#         # Distribute items in a circle around the room center
#         for j, item_type in enumerate(items):
#             angle = (j / len(items)) * 2 * math.pi
#             radius = room_info["radius"] * 0.4  # Place at 40% of room radius
#             x = cx + radius * math.cos(angle)
#             y = cy + radius * math.sin(angle)
#             editor.add_thing(x, y, item_type, check_geometry=False)
    
#     # Add spawn spots for ACS enemy spawning (using MapSpot, TID=100)
#     # Place spawn spots in a ring around the armory center
#     num_spawn_spots = 8  # Number of spawn locations
#     spawn_radius = armory_radius * 0.5  # 50% of armory radius
    
#     for i in range(num_spawn_spots):
#         angle = (i / num_spawn_spots) * 2 * math.pi
#         x = spawn_radius * math.cos(angle)
#         y = spawn_radius * math.sin(angle)
#         # MapSpot with TID 100 - used by ACS SpawnSpot function
#         editor.add_thing(x, y, ThingType.MAP_SPOT, angle=0, check_geometry=False, tid=100)
    
#     # =========================================================================
#     # ACS Scripts
#     # =========================================================================
    
#     # Door tags match the order: A=1, B=2, C=3 (as passed in add_corridor_door above)
#     door_tags = {"A": 1, "B": 2, "C": 3}
#     acs_builder = create_timed_door_acs(door_tags, difficulty)
    
#     if output_path:
#         output_path = Path(output_path)
        
#         # Always save ACS source for reference
#         acs_path = output_path.with_suffix('.acs')
#         acs_builder.save_source(acs_path)
        
#         try:
#             behavior = acs_builder.compile()
#             if behavior:
#                 map_data.behavior = behavior
#                 map_data.scripts = acs_builder.to_code()
#                 print("ACS compiled and embedded successfully!")
#         except FileNotFoundError:
#             print(f"Note: ACC compiler not found. ACS source saved to {acs_path}")
#             print("       Install ACC to embed compiled scripts in the WAD.")
#         except Exception as e:
#             print(f"Warning: ACS compilation failed: {e}")
#             print(f"         ACS source saved to {acs_path}")
        
#         wad.save(str(output_path))
    
#     # Calculate stats
#     stats = {
#         "room_count": len(result.rooms),
#         "corridor_count": len(result.corridors),
#         "sector_count": len(map_data.sectors),
#         "total_things": len(map_data.things),
#         "vertices": len(map_data.vertices),
#         "linedefs": len(map_data.linedefs),
#     }
    
#     return wad, map_data, stats


# def main():
#     import argparse
    
#     parser = argparse.ArgumentParser(description="Generate Armory Siege Defense scenario")
#     parser.add_argument("--seed", type=int, default=None, help="Random seed")
#     parser.add_argument(
#         "--difficulty",
#         choices=["easy", "medium", "hard"],
#         default="medium",
#         help="Enemy difficulty"
#     )
#     parser.add_argument(
#         "--players",
#         type=int,
#         default=4,
#         choices=[1, 2, 3, 4],
#         help="Number of player starts"
#     )
#     parser.add_argument("--output", type=str, default=None, help="Output path")
#     parser.add_argument("--batch", type=int, default=1, help="Number of maps to generate")
    
#     args = parser.parse_args()
    
#     output_dir = Path("output")
#     output_dir.mkdir(exist_ok=True)
    
#     if args.batch > 1:
#         # Batch generation
#         base_seed = args.seed if args.seed is not None else 0
#         for i in range(args.batch):
#             seed = base_seed + i
#             output_path = output_dir / f"armory_siege_{seed}.wad"
#             _, _, stats = create_armory_siege(
#                 seed=seed,
#                 output_path=str(output_path),
#                 difficulty=args.difficulty,
#                 num_players=args.players
#             )
#             print(f"Generated: {output_path} (seed={seed}, things={stats['total_things']})")
#     else:
#         # Single map generation
#         seed = args.seed if args.seed is not None else 42
#         output_path = args.output or str(output_dir / "armory_siege.wad")
        
#         print("=" * 60)
#         print("ARMORY SIEGE DEFENSE")
#         print("=" * 60)
#         print(f"\nSeed: {seed}")
#         print(f"Difficulty: {args.difficulty}")
#         print(f"Players: {args.players}")
#         print()
        
#         _, _, stats = create_armory_siege(
#             seed=seed,
#             output_path=output_path,
#             difficulty=args.difficulty,
#             num_players=args.players
#         )
        
#         print(f"\nMap Statistics:")
#         print(f"  Rooms: {stats['room_count']}")
#         print(f"  Corridors: {stats['corridor_count']}")
#         print(f"  Sectors: {stats['sector_count']}")
#         print(f"  Things: {stats['total_things']}")
#         print(f"  Vertices: {stats['vertices']}")
#         print(f"  Linedefs: {stats['linedefs']}")
        
#         print(f"\nSaved: {output_path}")
#         print(f"\nLoad with: gzdoom -iwad doom2.wad -file {output_path}")
        
#         print("\n" + "=" * 60)
#         print("DOOR TIMING (35 tics = 1 second)")
#         print("=" * 60)
#         print("Room A (Heavy Weapons): ticks 0-200, 500-700, 1000-1200")
#         print("Room B (Ammunition):    ticks 200-400, 700-900")
#         print("Room C (Health/Armor):  ticks 400-600, 900-1100")
#         print("Cycle repeats every 1200 ticks (~34 seconds)")


# if __name__ == "__main__":
#     main()
