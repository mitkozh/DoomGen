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
  Health 100
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
    
    # Core in Armory (TID 100)
    TID_CORE = 100
    builder.add_thing(15000, 0, 0, tid=TID_CORE)
    
    # Player Starts (3 Players)
    builder.add_thing("PLAYER1_START", -64, -64, angle=45)
    builder.add_thing("PLAYER2_START", 64, -64, angle=135)
    builder.add_thing("PLAYER3_START", 0, 64, angle=270)
    
    # Starting Weapons in Armory
    builder.add_thing("SHOTGUN", -100, 0)
    builder.add_thing("SHOTGUN", 100, 0)
    builder.add_thing("CHAINGUN", 0, -100)
    builder.add_thing("BOX_OF_SHELLS", -120, 20) # 50 shells approx (Box=20, Shells=4. Need multiple?)
    # Actually Box is 20. 2 Boxes + 2 Shells = 48. Close enough.
    builder.add_thing("BOX_OF_SHELLS", -140, 20)
    builder.add_thing("SHELLS", -160, 20)
    builder.add_thing("BOX_OF_BULLETS", 120, -20) # 50 bullets (Box=50)
    
    # MapSpots for Spawning (TIDs 200+)
    # Room A (Heavy Weapons)
    TID_SPAWN_A = 201
    builder.add_thing("MAP_SPOT", 0, 800, tid=TID_SPAWN_A)
    
    # Room B (Ammo)
    TID_SPAWN_B = 202
    builder.add_thing("MAP_SPOT", 700, -600, tid=TID_SPAWN_B)
    
    # Room C (Health/Armor)
    TID_SPAWN_C = 203
    builder.add_thing("MAP_SPOT", -700, -600, tid=TID_SPAWN_C)
    
    # Enemy Spawns (Outside corridors, maybe?)
    # Let's put them in the corridors or near the rooms
    TID_SPAWN_ENEMY = 300
    builder.add_thing("MAP_SPOT", 0, 600, tid=TID_SPAWN_ENEMY) # Near A
    builder.add_thing("MAP_SPOT", 500, -400, tid=TID_SPAWN_ENEMY) # Near B
    builder.add_thing("MAP_SPOT", -500, -400, tid=TID_SPAWN_ENEMY) # Near C
    
    # 6. Generate ACS Script
    acs = ACSBuilder()
    acs.add_include("zcommon.acs")
    
    # Script 1: Game Loop (Door Control & Spawning)
    # Room A: 0-200 Open, 500-700 Open, 1000-1200 Open
    # Room B: 200-400 Open, 700-900 Open
    # Room C: 400-600 Open, 900-1100 Open
    
    script_body = f"""
    int tick = 0;
    int cycle = 0;
    int TID_ITEM_A = 401;
    int TID_ITEM_B = 402;
    int TID_ITEM_C = 403;
    int TID_ENEMY_UNIT = 500;
    
    // Initial State: All Closed
    Sector_SetColor({TAG_DOOR_A}, 255, 0, 0); // Red
    Sector_SetColor({TAG_DOOR_B}, 255, 0, 0);
    Sector_SetColor({TAG_DOOR_C}, 255, 0, 0);
    
    while (TRUE) {{
        cycle = tick % 1200;
        
        // Room A Control
        if ((cycle >= 0 && cycle < 200) || (cycle >= 500 && cycle < 700) || (cycle >= 1000 && cycle < 1200)) {{
            Door_Open({TAG_DOOR_A}, 16, 0);
            Sector_SetColor({TAG_DOOR_A}, 0, 255, 0); // Green
        }} else {{
            Door_Close({TAG_DOOR_A}, 16, 0);
            Sector_SetColor({TAG_DOOR_A}, 255, 0, 0); // Red
        }}
        
        // Room B Control
        if ((cycle >= 200 && cycle < 400) || (cycle >= 700 && cycle < 900)) {{
            Door_Open({TAG_DOOR_B}, 16, 0);
            Sector_SetColor({TAG_DOOR_B}, 0, 255, 0);
        }} else {{
            Door_Close({TAG_DOOR_B}, 16, 0);
            Sector_SetColor({TAG_DOOR_B}, 255, 0, 0);
        }}
        
        // Room C Control
        if ((cycle >= 400 && cycle < 600) || (cycle >= 900 && cycle < 1100)) {{
            Door_Open({TAG_DOOR_C}, 16, 0);
            Sector_SetColor({TAG_DOOR_C}, 0, 255, 0);
        }} else {{
            Door_Close({TAG_DOOR_C}, 16, 0);
            Sector_SetColor({TAG_DOOR_C}, 255, 0, 0);
        }}
        
        // Resource Respawn (Every 300 ticks)
        if (tick % 300 == 0) {{
            // Room A: Heavy Weapons
            if (ThingCount(T_NONE, TID_ITEM_A) == 0) {{
                SpawnSpot("RocketLauncher", {TID_SPAWN_A}, TID_ITEM_A, 0);
            }}
            
            // Room B: Ammo
            if (ThingCount(T_NONE, TID_ITEM_B) == 0) {{
                SpawnSpot("BoxOfRockets", {TID_SPAWN_B}, TID_ITEM_B, 0);
            }}
            
            // Room C: Health/Armor
            if (ThingCount(T_NONE, TID_ITEM_C) == 0) {{
                SpawnSpot("Medikit", {TID_SPAWN_C}, TID_ITEM_C, 0);
            }}
            
            Print(s:"Supplies Checked!");
        }}
        
        // Enemy Spawn (Continuous, e.g., every 100 ticks)
        if (tick % 100 == 0 && tick > 0 && ThingCount(T_NONE, TID_ENEMY_UNIT) < 50) {{
            SpawnSpot("DoomImp", {TID_SPAWN_ENEMY}, TID_ENEMY_UNIT, 0);
            SpawnSpot("ShotgunGuy", {TID_SPAWN_ENEMY}, TID_ENEMY_UNIT, 0);
        }}
        
        Delay(1);
        tick++;
    }}
    """
    acs.add_script(ScriptType.OPEN, script_body)
    
    # Script 999: Game Over (Called by DefenseCore death)
    game_over_script = """
    Print(s:"CORE DESTROYED! GAME OVER!");
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
