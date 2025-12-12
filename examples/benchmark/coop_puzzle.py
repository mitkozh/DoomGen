import os
import random
from doomgen.builder import ProceduralMapBuilder
from doomgen.abstraction.layout import ConnectionType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType

def create_coop_puzzle(num_zones=10):
    seed = random.randint(0, 999999)
    print(f"Generating Co-op Puzzle Benchmark with {num_zones} zones (Seed: {seed})...")
    
    # 1. Initialize Builder
    # num_zones rooms * 512 units = length.
    map_length = num_zones * 512
    builder = ProceduralMapBuilder(bounds=(-1000, -1000, map_length + 1000, 1000), num_seeds=1500 * num_zones, seed=seed)
    
    # Constants
    ROOM_SIZE = 512
    PLATE_SIZE = 64
    NUM_ZONES = num_zones
    
    # Tags
    # Door L (i -> i+1): 100 + (i+1)
    # Door R (i -> i+1): 200 + (i+1)
    
    acs = ACSBuilder()
    acs.add_include("zcommon.acs")
    
    # Assign TIDs to players on Enter
    acs.add_script(ScriptType.ENTER, "Thing_ChangeTID(0, 1000 + PlayerNumber());", number=999)

    
    # 2. Generate Rooms & Doors
    prev_room_L = None
    prev_room_R = None
    
    for i in range(NUM_ZONES):
        room_name_L = f"Zone_{i}_L"
        room_name_R = f"Zone_{i}_R"
        x_pos = i * ROOM_SIZE
        
        # Create Left Room (y > 0)
        builder.add_area(
            name=room_name_L,
            shape=(x_pos, 128, ROOM_SIZE, 256), # Top half
            floor_height=0,
            ceiling_height=128,
            floor_texture="FLAT19",
            ceiling_texture="PLANET1",
            wall_texture="SILVER1"
        )
        
        # Create Right Room (y < 0)
        builder.add_area(
            name=room_name_R,
            shape=(x_pos, -128, ROOM_SIZE, 256), # Bottom half
            floor_height=0,
            ceiling_height=128,
            floor_texture="FLAT19",
            ceiling_texture="PLANET1",
            wall_texture="SILVER1"
        )
        
        # Connect L and R with a Window (Barrier)
        builder.connect_adjacent(
            room_name_L, room_name_R, 
            ConnectionType.WINDOW,
            middle_texture="MIDGRATE",
            blocking=True
        )
        
        # Add Player Starts in Zone 0
        if i == 0:
            builder.add_thing("PLAYER1_START", x_pos - 64, 64, angle=0) # Left
            builder.add_thing("PLAYER2_START", x_pos - 64, -64, angle=0) # Right
            
        # Connect to previous room with a Door
        if prev_room_L:
            door_tag_L = 100 + i
            door_tag_R = 200 + i
            
            # Door Left
            door_name_L = f"Door_{i-1}_{i}_L"
            door_id_L = builder.add_boundary(
                prev_room_L, room_name_L,
                name=door_name_L,
                connection_type=ConnectionType.DOOR,
                floor_height=0, ceiling_height=0,
                wall_texture="DOORTRAK",
                floor_texture="GATE1",
                ceiling_texture="GATE1"
            )
            builder.graph.get_area(door_id_L).config.tag = door_tag_L
            
            # Door Right
            door_name_R = f"Door_{i-1}_{i}_R"
            door_id_R = builder.add_boundary(
                prev_room_R, room_name_R,
                name=door_name_R,
                connection_type=ConnectionType.DOOR,
                floor_height=0, ceiling_height=0,
                wall_texture="DOORTRAK",
                floor_texture="GATE1",
                ceiling_texture="GATE1"
            )
            builder.graph.get_area(door_id_R).config.tag = door_tag_R
        
        # Determine Puzzle Type
        if i == NUM_ZONES - 1:
            # Final Room Logic
            # The active agent is here. The partner is stuck in the previous room.
            # We need a plate to open the partner's entry door.
            
            is_left = (i % 2 != 0)
            active_room = room_name_L if is_left else room_name_R
            y_base = 128 if is_left else -128
            
            # Partner needs Door (i-1 -> i)
            # If Left Active, Partner is Right. Needs Door R (i-1 -> i) [Tag 200 + i]
            partner_door_tag = (200 if is_left else 100) + i
            plate_final_tag = 7000 + i
            
            base_id = 10 + (i * 10)
            s_enter = base_id + 0
            
            script_body = f"""
                Door_Open({partner_door_tag}, 16, 0);
                Delay(5);
                int count = 1;
                while (count > 0) {{
                    count = 0;
                    for (int p = 0; p < 8; p++) {{
                        if (ThingCountSector(0, 1000 + p, {plate_final_tag}) > 0) count++;
                    }}
                    Delay(5);
                }}
                Door_Close({partner_door_tag}, 16, 0);
            """
            acs.add_script(ScriptType.VOID, script_body, number=s_enter)
            
            plate_final = f"Plate_{i}_Final"
            plate_id = builder.add_area(plate_final, shape=(x_pos, y_base, PLATE_SIZE, PLATE_SIZE), mode="overwrite", floor_height=0, floor_texture="CEIL5_1")
            builder.graph.get_area(plate_id).config.tag = plate_final_tag
            
            builder.connect_adjacent(active_room, plate_final, ConnectionType.OPEN, special=80, args=[s_enter, 0, 0, 0, 0], flags=512)
            
        elif i == 0:
            # Zone 0: Right Plate opens Door L (0->1)
            target_door_tag = 100 + (i + 1)
            plate_tag = 3000 + i
            
            # Script: Open, Wait for players to leave plate_tag, Close
            s_enter = 10 + (i * 10)
            
            script_body = f"""
                Door_Open({target_door_tag}, 16, 0);
                Delay(5); // Wait for physics
                int count = 1;
                while (count > 0) {{
                    count = 0;
                    for (int p = 0; p < 8; p++) {{
                        if (ThingCountSector(0, 1000 + p, {plate_tag}) > 0) count++;
                    }}
                    Delay(5);
                }}
                Door_Close({target_door_tag}, 16, 0);
            """
            acs.add_script(ScriptType.VOID, script_body, number=s_enter)
            
            # Add Plate
            plate_name = f"Plate_{i}_R"
            # Note: We need to set the tag of the plate area!
            # We can do this by getting the area after creation.
            plate_id = builder.add_area(plate_name, shape=(x_pos, -128, PLATE_SIZE, PLATE_SIZE), mode="overwrite", floor_height=0, floor_texture="CEIL5_1")
            builder.graph.get_area(plate_id).config.tag = plate_tag
            
            # Connect with Linedef Trigger
            builder.connect_adjacent(room_name_R, plate_name, ConnectionType.OPEN, special=80, args=[s_enter, 0, 0, 0, 0], flags=512)
            
        else:
            # Determine Active Side
            # Odd (1, 3, ...) -> Left Active
            # Even (2, 4, ...) -> Right Active
            is_left = (i % 2 != 0)
            
            active_room = room_name_L if is_left else room_name_R
            y_base = 128 if is_left else -128
            
            base_id = 10 + (i * 10)
            
            # 1. Back Plate (Opens Previous Door for Partner)
            partner_door_tag = (200 if is_left else 100) + i
            plate_back_tag = 4000 + i
            
            s_enter = base_id + 0
            
            script_body = f"""
                Door_Open({partner_door_tag}, 16, 0);
                Delay(5);
                int count = 1;
                while (count > 0) {{
                    count = 0;
                    for (int p = 0; p < 8; p++) {{
                        if (ThingCountSector(0, 1000 + p, {plate_back_tag}) > 0) count++;
                    }}
                    Delay(5);
                }}
                Door_Close({partner_door_tag}, 16, 0);
            """
            acs.add_script(ScriptType.VOID, script_body, number=s_enter)
            
            plate_back = f"Plate_{i}_{'L' if is_left else 'R'}_Back"
            plate_id = builder.add_area(plate_back, shape=(x_pos - 128, y_base, PLATE_SIZE, PLATE_SIZE), mode="overwrite", floor_height=0, floor_texture="CEIL5_1")
            builder.graph.get_area(plate_id).config.tag = plate_back_tag
            
            builder.connect_adjacent(active_room, plate_back, ConnectionType.OPEN, special=80, args=[s_enter, 0, 0, 0, 0], flags=512)
            
            # 2. Forward Plate (Opens Next Door for Partner)
            next_door_tag = (200 if is_left else 100) + (i + 1)
            
            # Check for AND Logic (e.g. every 3rd room: 3, 6, 9)
            if i % 3 == 0:
                # AND Logic: Two plates required
                var1 = f"plate_{i}_1"
                var2 = f"plate_{i}_2"
                acs.add_global_var(var1, "int", 0)
                acs.add_global_var(var2, "int", 0)
                
                plate1_tag = 5000 + (i * 2)
                plate2_tag = 5000 + (i * 2) + 1
                
                # Plate 1 Script
                s1_enter = base_id + 2
                script1_body = f"""
                    {var1} = 1;
                    if ({var2}) Door_Open({next_door_tag}, 16, 0);
                    
                    Delay(5);
                    int count = 1;
                    while (count > 0) {{
                        count = 0;
                        for (int p = 0; p < 8; p++) {{
                            if (ThingCountSector(0, 1000 + p, {plate1_tag}) > 0) count++;
                        }}
                        Delay(5);
                    }}
                    
                    {var1} = 0;
                    Door_Close({next_door_tag}, 16, 0);
                """
                acs.add_script(ScriptType.VOID, script1_body, number=s1_enter)
                
                # Plate 2 Script
                s2_enter = base_id + 3
                script2_body = f"""
                    {var2} = 1;
                    if ({var1}) Door_Open({next_door_tag}, 16, 0);
                    
                    Delay(5);
                    int count = 1;
                    while (count > 0) {{
                        count = 0;
                        for (int p = 0; p < 8; p++) {{
                            if (ThingCountSector(0, 1000 + p, {plate2_tag}) > 0) count++;
                        }}
                        Delay(5);
                    }}
                    
                    {var2} = 0;
                    Door_Close({next_door_tag}, 16, 0);
                """
                acs.add_script(ScriptType.VOID, script2_body, number=s2_enter)
                
                # Place Plates
                # Plate 1 (Left Side)
                p1_name = f"Plate_{i}_L_Fwd"
                pid1 = builder.add_area(p1_name, shape=(x_pos + 128, 128, PLATE_SIZE, PLATE_SIZE), mode="overwrite", floor_height=0, floor_texture="CEIL5_1")
                builder.graph.get_area(pid1).config.tag = plate1_tag
                builder.connect_adjacent(room_name_L, p1_name, ConnectionType.OPEN, special=80, args=[s1_enter, 0, 0, 0, 0], flags=512)

                # Plate 2 (Right Side)
                p2_name = f"Plate_{i}_R_Fwd"
                pid2 = builder.add_area(p2_name, shape=(x_pos + 128, -128, PLATE_SIZE, PLATE_SIZE), mode="overwrite", floor_height=0, floor_texture="CEIL5_1")
                builder.graph.get_area(pid2).config.tag = plate2_tag
                builder.connect_adjacent(room_name_R, p2_name, ConnectionType.OPEN, special=80, args=[s2_enter, 0, 0, 0, 0], flags=512)
                
            else:
                # Standard Single Plate
                plate_fwd_tag = 6000 + i
                s_enter = base_id + 2
                
                script_body = f"""
                    Door_Open({next_door_tag}, 16, 0);
                    Delay(5);
                    int count = 1;
                    while (count > 0) {{
                        count = 0;
                        for (int p = 0; p < 8; p++) {{
                            if (ThingCountSector(0, 1000 + p, {plate_fwd_tag}) > 0) count++;
                        }}
                        Delay(5);
                    }}
                    Door_Close({next_door_tag}, 16, 0);
                """
                acs.add_script(ScriptType.VOID, script_body, number=s_enter)
                
                plate_fwd = f"Plate_{i}_{'L' if is_left else 'R'}_Fwd"
                pid = builder.add_area(plate_fwd, shape=(x_pos + 128, y_base, PLATE_SIZE, PLATE_SIZE), mode="overwrite", floor_height=0, floor_texture="CEIL5_1")
                builder.graph.get_area(pid).config.tag = plate_fwd_tag
                
                builder.connect_adjacent(active_room, plate_fwd, ConnectionType.OPEN, special=80, args=[s_enter, 0, 0, 0, 0], flags=512)
            
        prev_room_L = room_name_L
        prev_room_R = room_name_R

    # 3. Generate ACS
    try:
        print("Compiling ACS...")
        bytecode = acs.compile()
        if bytecode:
            builder.map_data.behavior = bytecode
            print("ACS compiled successfully.")
        else:
            raise Exception("No bytecode generated.")
    except Exception as e:
        print(f"ACS compilation failed: {e}")
        print("Using dummy BEHAVIOR lump. GZDoom will compile SCRIPTS on load.")
        builder.map_data.behavior = b'ACSE\x08\x00\x00\x00\x00\x00\x00\x00'

    builder.map_data.scripts = acs.to_code()
    
    # 4. Save Map
    output_path = "examples/benchmark/output/coop_puzzle.wad"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    builder.build(output_path)
    print(f"WAD written to {output_path}")

if __name__ == "__main__":
    create_coop_puzzle(num_zones=10)
