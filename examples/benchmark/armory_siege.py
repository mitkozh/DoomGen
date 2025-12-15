import os
import random
from doomgen.builder import ProceduralMapBuilder
from doomgen.abstraction.layout import ConnectionType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType
from shapely.geometry import Point

def create_armory_siege():
    print("Generating Armory Siege Defense Benchmark...")
    
    # 1. Initialize Builder
    # Use a fixed seed for structural reproducibility if needed, or random for benchmark variation
    seed = random.randint(0, 999999)
    print(f"Seed: {seed}")
    builder = ProceduralMapBuilder(bounds=(-1500, -1500, 1500, 1500), num_seeds=4000, seed=seed)
    
    # 0. Add DECORATE for Defense Core
    decorate_str = """
ACTOR DefenseCore 15000
{
  //$Category "Objectives"
  Health 800
  Radius 16
  Height 50
  Speed 0
  +SOLID
  +SHOOTABLE
  +NOBLOOD
  +FRIENDLY
  +ISMONSTER
  +LOOKALLAROUND
  DamageFactor "Player", 0
  
  States
  {
  Spawn:
    TLMP ABCD 4
    TLMP A 0 A_Look
    Loop
  See:
    TLMP A 4 A_Chase
    Loop
  Missile:
    TLMP A 0 A_CustomBulletAttack(0, 0, 1, 1, "BulletPuff", 10000)
    TLMP A 5
    Goto See
  Death:
    TLMP A 1
    TLMP A 0 ACS_Execute(999, 0)
    Stop
  }
}

ACTOR PlaceablePistol : Pistol 15001
{
  //$Category "Weapons"
}
"""
    builder.wad_writer.add_lump("DECORATE", decorate_str.encode('utf-8'))
    
    # 2. Define Areas
    
    # Central Armory
    builder.add_area(
        name="Armory",
        shape=(0, 0, 512, 512),
        floor_height=0,
        ceiling_height=192,
        floor_texture="FLOOR4_8",
        ceiling_texture="TLITE6_4",
        wall_texture="STARTAN3"
    )
    
    # Supply Room A (Heavy Weapons) - North
    builder.add_area(
        name="Room A",
        shape=(0, 800, 384, 384),
        floor_height=0,
        ceiling_height=160,
        floor_texture="CEIL5_2", # Distinct floor
        wall_texture="STONE2"
    )
    
    # Supply Room B (Ammo) - South East
    builder.add_area(
        name="Room B",
        shape=(700, -600, 384, 384),
        floor_height=0,
        ceiling_height=160,
        floor_texture="FLAT5_4",
        wall_texture="BROWN1"
    )
    
    # Supply Room C (Health/Armor) - South West
    builder.add_area(
        name="Room C",
        shape=(-700, -600, 384, 384),
        floor_height=0,
        ceiling_height=160,
        floor_texture="MFLR8_1",
        wall_texture="STARGR1"
    )
    
    # 3. Connect via Corridors
    
    # Corridor A
    corr_a = builder.add_corridor("Armory", "Room A", width=2, floor_texture="RROCK19")
    # Corridor B
    corr_b = builder.add_corridor("Armory", "Room B", width=2, floor_texture="RROCK19")
    # Corridor C
    corr_c = builder.add_corridor("Armory", "Room C", width=2, floor_texture="RROCK19")
    
    # 4. Add Doors (Time-Gated)
    # We need tags for these doors to control them via ACS.
    TAG_DOOR_A = 10
    TAG_DOOR_B = 11
    TAG_DOOR_C = 12
    
    # Door A (Between Corridor A and Room A)
    door_a_id = builder.add_boundary(
        "Room A", corr_a, 
        name="Door A", 
        connection_type=ConnectionType.DOOR,
        floor_height=0, ceiling_height=0, # Closed
        floor_texture="GATE1", ceiling_texture="GATE1", wall_texture="BIGDOOR2"
    )
    builder.graph.get_area(door_a_id).config.tag = TAG_DOOR_A
    
    # Door B
    door_b_id = builder.add_boundary(
        "Room B", corr_b, 
        name="Door B", 
        connection_type=ConnectionType.DOOR,
        floor_height=0, ceiling_height=0,
        floor_texture="GATE1", ceiling_texture="GATE1", wall_texture="BIGDOOR2"
    )
    builder.graph.get_area(door_b_id).config.tag = TAG_DOOR_B
    
    # Door C
    door_c_id = builder.add_boundary(
        "Room C", corr_c, 
        name="Door C", 
        connection_type=ConnectionType.DOOR,
        floor_height=0, ceiling_height=0,
        floor_texture="GATE1", ceiling_texture="GATE1", wall_texture="BIGDOOR2"
    )
    builder.graph.get_area(door_c_id).config.tag = TAG_DOOR_C
    
    # 5. Add Things
    
    # Core in Armory (TID 100) - REMOVED, Spawning via ACS
    TID_CORE = 100
    # builder.add_thing(15000, 0, 0, tid=TID_CORE)
    
    # Player Starts (3 Players)
    # Keep them for initialization, but they will be moved
    builder.add_thing("PLAYER1_START", -64, -64, angle=45)
    builder.add_thing("PLAYER2_START", 64, -64, angle=135)
    builder.add_thing("PLAYER3_START", 0, 64, angle=270)
    
    # Helper to place clusters of MapSpots
    def place_spawn_cluster(area_name, base_tid, count=5):
        for i in range(count):
            pt = builder.get_random_point_in_area(area_name)
            if pt:
                builder.add_thing("MAP_SPOT", pt[0], pt[1], tid=base_tid + i)
                
    # Place Spawn Clusters
    # Core Spawn Cluster (Armory): Base 50
    place_spawn_cluster("Armory", 50, count=5)
    
    # Player Spawn Cluster (Armory): Base 60
    place_spawn_cluster("Armory", 60, count=10)

    # Room A Supply (RocketLauncher): Base 100
    place_spawn_cluster("Room A", 100)
    
    # Room B Supply (BoxOfRockets): Base 110
    place_spawn_cluster("Room B", 110)
    
    # Room C Supply (Medikit): Base 120
    place_spawn_cluster("Room C", 120)
    
    # Enemy Spawns: Base 200, 210, 220
    place_spawn_cluster(corr_a, 200)
    place_spawn_cluster(corr_b, 210)
    place_spawn_cluster(corr_c, 220)
    
    # Corridor Items (Pistol/Clip)
    # Corridor A: Pistol 300, Clip 310
    place_spawn_cluster(corr_a, 300)
    place_spawn_cluster(corr_a, 310)
    
    # Corridor B: Pistol 320, Clip 330
    place_spawn_cluster(corr_b, 320)
    place_spawn_cluster(corr_b, 330)
    
    # Corridor C: Pistol 340, Clip 350
    place_spawn_cluster(corr_c, 340)
    place_spawn_cluster(corr_c, 350)
    
    # 6. Generate ACS Script
    acs = ACSBuilder()
    acs.add_include("zcommon.acs")
    
    acs.add_global_var("core_health_global", 1, "int")
    
    # Assign TIDs to players on Enter so we can target them for Score syncing
    acs.add_script(ScriptType.ENTER, """
        int p_tid = 1000 + PlayerNumber();
        Thing_ChangeTID(0, p_tid);
        ClearInventory();
        
        // Randomize position using Player Spawn Cluster (60-69)
        int dest_spot = 60 + Random(0, 9);
        SetActorPosition(0, GetActorX(dest_spot), GetActorY(dest_spot), GetActorZ(dest_spot), 0);
    """)

    # Respawn script: Lose everything
    acs.add_script(ScriptType.RESPAWN, """
        int p_tid = 1000 + PlayerNumber();
        Thing_ChangeTID(0, p_tid);
        ClearInventory();
        
        // Randomize position on respawn too?
        int dest_spot = 60 + Random(0, 9);
        SetActorPosition(0, GetActorX(dest_spot), GetActorY(dest_spot), GetActorZ(dest_spot), 0);
    """)
    
    # Script 1: Game Loop (Door Control & Spawning)
    # Room A: 0-200 Open, 500-700 Open, 1000-1200 Open
    # Room B: 200-400 Open, 700-900 Open
    # Room C: 400-600 Open, 900-1100 Open
    
    script_body = f"""
    core_health_global = 800;
    int tick = 0;
    int cycle = 0;
    int wave = 0;
    int TID_ITEM_A = 401;
    int TID_ITEM_B = 402;
    int TID_ITEM_C = 403;
    int TID_ENEMY_UNIT = 500;
    
    // Spawn Core at random spot (50-54)
    SpawnSpot("DefenseCore", 50 + Random(0, 4), {TID_CORE}, 0);
    
    // Spawn Initial Corridor Items (Pistols/Clips)
    // Pick random spot from clusters (0-4)
    SpawnSpot("PlaceablePistol", 300 + Random(0, 4), 0, 0);
    SpawnSpot("Clip", 310 + Random(0, 4), 0, 0);
    
    SpawnSpot("PlaceablePistol", 320 + Random(0, 4), 0, 0);
    SpawnSpot("Clip", 330 + Random(0, 4), 0, 0);
    
    SpawnSpot("PlaceablePistol", 340 + Random(0, 4), 0, 0);
    SpawnSpot("Clip", 350 + Random(0, 4), 0, 0);
    
    // Initial State: All Closed
    Sector_SetColor({TAG_DOOR_A}, 255, 0, 0); // Red
    Sector_SetColor({TAG_DOOR_B}, 255, 0, 0);
    Sector_SetColor({TAG_DOOR_C}, 255, 0, 0);
    
    int door_a_open = 0;
    int door_b_open = 0;
    int door_c_open = 0;
    
    while (TRUE) {{
        cycle = tick % 1200;
        wave = tick / 1050; // Increase difficulty every ~30 seconds
        
        // Sync Core Health to Global Variable 1
        core_health_global = GetActorProperty({TID_CORE}, APROP_HEALTH);
        
        // Room A Control
        int should_open_a = (cycle >= 0 && cycle < 200) || (cycle >= 500 && cycle < 700) || (cycle >= 1000 && cycle < 1200);
        if (should_open_a) {{
            if (!door_a_open) {{
                Door_Open({TAG_DOOR_A}, 16, 0);
                Sector_SetColor({TAG_DOOR_A}, 0, 255, 0); // Green
                door_a_open = 1;
                // Spawn ONLY ONCE when opening
                if (ThingCount(T_NONE, TID_ITEM_A) == 0) {{
                    SpawnSpot("RocketLauncher", 100 + Random(0, 4), TID_ITEM_A, 0);
                }}
            }}
        }} else {{
            if (door_a_open) {{
                Door_Close({TAG_DOOR_A}, 16, 0);
                Sector_SetColor({TAG_DOOR_A}, 255, 0, 0); // Red
                door_a_open = 0;
            }}
        }}
        
        // Room B Control
        int should_open_b = (cycle >= 200 && cycle < 400) || (cycle >= 700 && cycle < 900);
        if (should_open_b) {{
            if (!door_b_open) {{
                Door_Open({TAG_DOOR_B}, 16, 0);
                Sector_SetColor({TAG_DOOR_B}, 0, 255, 0);
                door_b_open = 1;
                if (ThingCount(T_NONE, TID_ITEM_B) == 0) {{
                    SpawnSpot("RocketBox", 110 + Random(0, 4), TID_ITEM_B, 0);
                }}
            }}
        }} else {{
            if (door_b_open) {{
                Door_Close({TAG_DOOR_B}, 16, 0);
                Sector_SetColor({TAG_DOOR_B}, 255, 0, 0);
                door_b_open = 0;
            }}
        }}
        
        // Room C Control
        int should_open_c = (cycle >= 400 && cycle < 600) || (cycle >= 900 && cycle < 1100);
        if (should_open_c) {{
            if (!door_c_open) {{
                Door_Open({TAG_DOOR_C}, 16, 0);
                Sector_SetColor({TAG_DOOR_C}, 0, 255, 0);
                door_c_open = 1;
                if (ThingCount(T_NONE, TID_ITEM_C) == 0) {{
                    SpawnSpot("Medikit", 120 + Random(0, 4), TID_ITEM_C, 0);
                }}
            }}
        }} else {{
            if (door_c_open) {{
                Door_Close({TAG_DOOR_C}, 16, 0);
                Sector_SetColor({TAG_DOOR_C}, 255, 0, 0);
                door_c_open = 0;
            }}
        }}
        
        // Wave System
        
        // Wave System
        int spawn_interval = 200 - (wave * 20);
        if (spawn_interval < 40) spawn_interval = 40; // Cap max speed
        
        if (tick % spawn_interval == 0 && tick > 0 && ThingCount(T_NONE, TID_ENEMY_UNIT) < (20 + wave * 5)) {{
            int r = Random(0, 10);
            int spawn_base = 200;
            int r_spawn = Random(0, 2);
            if (r_spawn == 1) spawn_base = 210;
            if (r_spawn == 2) spawn_base = 220;
            
            int spawn_tid = spawn_base + Random(0, 4);
            
            if (wave == 0) {{
                SpawnSpot("DoomImp", spawn_tid, TID_ENEMY_UNIT, 0);
            }} else if (wave < 3) {{
                if (r < 7) SpawnSpot("DoomImp", spawn_tid, TID_ENEMY_UNIT, 0);
                else SpawnSpot("ShotgunGuy", spawn_tid, TID_ENEMY_UNIT, 0);
            }} else {{
                if (r < 5) SpawnSpot("DoomImp", spawn_tid, TID_ENEMY_UNIT, 0);
                else if (r < 8) SpawnSpot("ShotgunGuy", spawn_tid, TID_ENEMY_UNIT, 0);
                else SpawnSpot("Demon", spawn_tid, TID_ENEMY_UNIT, 0);
            }}
        }}
        
        Delay(1);
        tick++;
    }}
    """
    acs.add_script(ScriptType.OPEN, script_body)
    
    # Script 999: Game Over (Called by DefenseCore death)
    game_over_script = """
    Delay(35*3);
    Exit_Normal(0);
    """
    acs.add_script(ScriptType.VOID, game_over_script, number=999)
    
    # 7. Build
    # Try to compile ACS
    try:
        print("Compiling ACS...")
        # Assuming 'acc' is in PATH. If not, user might need to specify path or install it.
        # If compilation fails, we fall back to dummy behavior (things work, but scripts won't run until compiled by GZDoom)
        bytecode = acs.compile()
        if bytecode:
            builder.map_data.behavior = bytecode
            print("ACS compiled successfully.")
        else:
            raise Exception("No bytecode generated.")
    except Exception as e:
        print(f"ACS compilation failed: {e}")
        print("Using dummy BEHAVIOR lump. GZDoom will compile SCRIPTS on load.")
        # Force Hexen format by setting a dummy behavior lump
        builder.map_data.behavior = b'ACSE\x08\x00\x00\x00\x00\x00\x00\x00' # Minimal header

    builder.map_data.scripts = acs.to_code()
    
    output_path = "examples/benchmark/output/armory_siege.wad"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    builder.build(output_path)
    print(f"WAD written to {output_path}")

if __name__ == "__main__":
    create_armory_siege()
