# only works for gzdoom, so not relevant for the benchmark

# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# from typing import Dict, Any
# import random
# import math
# from shapely.geometry import Point, box
# from shapely.affinity import rotate, translate
# from doomgen.batch.scenario import Scenario
# from doomgen.builder import ProceduralMapBuilder
# from doomgen.abstraction.layout import ConnectionType
# from doomgen.logic.acs_builder import ACSBuilder, ScriptType
# from doomgen.doom.things import ThingType


# class CoopCQBScenario(Scenario):
#     """
#     Cooperative Close Quarters Battle benchmark.

#     Players must systematically clear a procedural building of hostile
#     combatants while avoiding civilian casualties and friendly fire.
#     """

#     def get_default_config(self) -> Dict[str, Any]:
#         return {
#             "num_rooms": 10,
#             "seed": None,
#             "room_min_size": 256,
#             "room_max_size": 384,
#             "corridor_width": 5,
#             "max_enemies": 32,
#             "max_civilians": 12,
#             "ambient_light": 80,
#             "enemy_detect_radius": 1024,
#             "flashlight_detect_radius": 1024,
#             "spawn_interval_tics": 140,
#             "player_count": 2,
#             "cover_objects_per_room": 3,
#             "min_spawn_distance": 512,
#         }

#     def generate(self, output_path: str) -> None:
#         cfg = self.config
#         seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)
#         random.seed(seed)

#         num_rooms = cfg["num_rooms"]
#         room_min = cfg["room_min_size"]
#         room_max = cfg["room_max_size"]
#         ambient = cfg["ambient_light"]

#         grid_cols = max(2, int(math.ceil(math.sqrt(num_rooms))))
#         grid_rows = max(2, int(math.ceil(num_rooms / grid_cols)))
#         spacing = room_max + 500
#         half_x = int((grid_cols + 2) * spacing / 2) + 1200
#         half_y = int((grid_rows + 3) * spacing / 2) + 800

#         builder = ProceduralMapBuilder(
#             bounds=(-half_x, -half_y, half_x, half_y),
#             num_seeds=120000,
#             seed=seed
#         )

#         keyconf_str = (
#             'alias ToggleFlashlight "pukename ToggleFlashlight"\n'
#             'addmenukey "Toggle Flashlight" ToggleFlashlight\n'
#             'defaultbind f ToggleFlashlight\n'
#         )
#         builder.wad_writer.add_lump("KEYCONF", keyconf_str.encode('utf-8'))
        
#         mapinfo_str = (
#             'gameinfo {\n'
#             '   playerclasses = "CQBPlayer"\n'
#             '}\n'
#             '\n'
#             'defaultmap {\n'
#             '   teamdamage = 1.0\n'
#             '}\n'
#             '\n'
#             'map MAP01 "CQB OPERATION"\n'
#             '{\n'
#             '   next = "MAP01"\n'
#             '   sky1 = "SKY1"\n'
#             '}\n'
#         )
#         builder.wad_writer.add_lump("MAPINFO", mapinfo_str.encode('utf-8'))

#         decorate_str = r"""
# ACTOR FlashlightTarget : PointLight
# {
#         +NOGRAVITY
#         +NOBLOCKMAP
#         +NOCLIP
#         Args 255, 255, 230, 200
# }

# ACTOR FlashlightToken : Inventory { Inventory.MaxAmount 1 }
# ACTOR PlayerInLight : Inventory { Inventory.MaxAmount 1 }

# ACTOR CQBPlayer : DoomPlayer
# {
#     Player.DisplayName "CQB Operative"
#     States
#     {
#     Pain:
#         PLAY G 4
#         PLAY G 4 A_Pain
#         PLAY G 0 ACS_NamedExecuteAlways("TeammateDamageHandler", 0)
#         Goto See
#     }
# }

# ACTOR CQBEnemyShot
# {
#     Radius 4
#     Height 4
#     Speed 200
#     Damage 5
#     Projectile
#     RenderStyle Add
#     Alpha 1.0
#     Scale 0.4
#     +BRIGHT
#     States
#     {
#     Spawn:
#         PUFF A 2 BRIGHT
#         Loop
#     Death:
#         PUFF CD 2 BRIGHT
#         Stop
#     }
# }

# ACTOR CQBHostile : Zombieman 15001
# {
#     Health 30
#     Speed 12
#     ReactionTime 0
#     PainChance 10
#     +LOOKALLAROUND
#     +MISSILEMORE
#     SeeSound "grunt/sight"
#     DropItem "Clip" 64
#     DropItem "Shell" 4
#     States
#     {
#     Spawn:
#         POSS A 10
#         Loop
#     See:
#         POSS AABBCCDD 2 A_Chase
#         Loop
#     Missile:
#         POSS E 4 A_FaceTarget
#         POSS E 0 A_JumpIfInventory("PlayerInLight", 1, "MissileAccurate", AAPTR_TARGET)
#         POSS E 8 A_FaceTarget
#         Goto See
#     MissileAccurate:
#         POSS F 0 A_CustomMissile("CQBEnemyShot", 32, 0, 0)
#         POSS F 4 A_CustomMissile("CQBEnemyShot", 32, 0, 0)
#         POSS E 4
#         Goto See
#     Pain:
#         POSS G 2
#         POSS G 2 A_Pain
#         Goto See
#     Death:
#         POSS H 0 A_NoBlocking
#         POSS H 0 A_UnsetShootable
#         POSS H 0 Thing_ChangeTID(0, 0)
#         POSS H 0 ACS_ExecuteAlways(997, 0)
#         POSS H 5 A_Scream
#         POSS IJK 5
#         POSS L -1
#         Stop
#     }
# }

# ACTOR CQBHostileElite : Shotgunguy 15002
# {
#     Health 120
#     Speed 13
#     ReactionTime 0
#     PainChance 5
#     +LOOKALLAROUND
#     +MISSILEMORE
#     SeeSound "shotguy/sight"
#     DropItem "Shell" 6
#     States
#     {
#     Spawn:
#         SPOS A 10
#         Loop
#     See:
#         SPOS AABBCCDD 2 A_Chase
#         Loop
#     Missile:
#         SPOS E 4 A_FaceTarget
#         SPOS E 0 A_JumpIfInventory("PlayerInLight", 1, "MissileAccurate", AAPTR_TARGET)
#         SPOS E 8 A_FaceTarget
#         Goto See
#     MissileAccurate:
#         SPOS F 0 A_CustomMissile("CQBEnemyShot", 32, 0, -2)
#         SPOS F 0 A_CustomMissile("CQBEnemyShot", 32, 0, 0)
#         SPOS F 4 A_CustomMissile("CQBEnemyShot", 32, 0, 2)
#         SPOS E 4
#         Goto See
#     Pain:
#         SPOS G 2
#         SPOS G 2 A_Pain
#         Goto See
#     Death:
#         SPOS H 0 A_NoBlocking
#         SPOS H 0 A_UnsetShootable
#         SPOS H 0 Thing_ChangeTID(0, 0)
#         SPOS H 0 ACS_ExecuteAlways(997, 0)
#         SPOS H 5 A_Scream
#         SPOS IJK 5
#         SPOS L -1
#         Stop
#     }
# }

# ACTOR CQBCivilian : MarineFist 15003
# {
#     Health 20
#     Speed 4
#     Radius 16
#     Height 56
#     +FRIENDLY
#     +LOOKALLAROUND
#     Translation "112:127=176:191"
#     States
#     {
#     Spawn:
#         PLAY A 10
#         Loop
#     See:
#         PLAY AABBCCDD 4 A_Wander
#         Loop
#     Pain:
#         PLAY G 4
#         PLAY G 4 A_Pain
#         Goto See
#     Death:
#         PLAY H 0 A_SetScale(1.0)
#         PLAY H 5
#         PLAY I 5 A_Scream
#         PLAY J 5 A_NoBlocking
#         PLAY K 5 ACS_ExecuteAlways(998, 0)
#         PLAY L -1
#         Stop
#     }
# }
# """
#         builder.wad_writer.add_lump("DECORATE", decorate_str.encode('utf-8'))

        
#         rooms = []
#         room_names = []
#         room_tags = []
#         corridor_tags = []

#         entry_w, entry_h = 512, 384
#         builder.add_area(
#             "Entry",
#             shape=(0, 0, entry_w, entry_h),
#             floor_height=0,
#             ceiling_height=160,
#             floor_texture="FLAT19",
#             ceiling_texture="CEIL3_5",
#             wall_texture="METAL1",
#             light_level=ambient + 40,
#             tag=500
#         )

#         room_idx = 0
#         for row in range(grid_rows):
#             for col in range(grid_cols):
#                 if room_idx >= num_rooms:
#                     break

#                 rw = random.randint(room_min, room_max)
#                 rh = random.randint(room_min, room_max)

#                 cx = int((col - grid_cols / 2) * spacing + random.randint(-40, 40))
#                 cy = int((row + 1) * spacing + random.randint(-40, 40))

#                 room_name = f"Room_{room_idx}"
#                 room_tag = 100 + room_idx

#                 shape_type = random.choice(["rect", "L", "T"])
                
#                 if shape_type == "rect":
#                     poly = box(cx - rw/2, cy - rh/2, cx + rw/2, cy + rh/2)
#                 elif shape_type == "L":
#                     base = box(cx - rw/2, cy - rh/2, cx + rw/2, cy + rh/2)
#                     cut_w, cut_h = rw // 2, rh // 2
#                     qx = random.choice([-1, 1])
#                     qy = random.choice([-1, 1])
#                     cut_x = cx + (qx * cut_w / 2)
#                     cut_y = cy + (qy * cut_h / 2)
#                     cutout = box(cut_x - cut_w/2, cut_y - cut_h/2, cut_x + cut_w/2, cut_y + cut_h/2)
#                     poly = base.difference(cutout)
#                 else: # T-Shape
#                     bar_w = rw
#                     bar_h = rh // 3
#                     h_rect = box(cx - bar_w/2, cy - bar_h/2, cx + bar_w/2, cy + bar_h/2)
                    
#                     stem_w = rw // 3
#                     stem_h = rh
#                     v_rect = box(cx - stem_w/2, cy - stem_h/2, cx + stem_w/2, cy + stem_h/2)
#                     poly = h_rect.union(v_rect)

#                 builder.add_area(
#                     room_name,
#                     shape=poly,
#                     floor_height=0,
#                     ceiling_height=random.choice([128, 144, 160, 192]),
#                     floor_texture=random.choice(["FLAT19", "FLOOR4_8", "FLAT5_4", "FLOOR4_1"]),
#                     ceiling_texture=random.choice(["CEIL3_5", "CEIL3_3", "FLAT5_4"]),
#                     wall_texture=random.choice(["METAL1", "STONE2", "STARG3", "BROWN1"]),
#                     light_level=ambient,
#                     tag=room_tag
#                 )

#                 rooms.append((room_name, cx, cy, rw, rh))
#                 room_names.append(room_name)
#                 room_tags.append(room_tag)

                
#                 for ci in range(cfg["cover_objects_per_room"]):
#                     inset = 96
#                     cover_x = cx + random.randint(-rw // 2 + inset, rw // 2 - inset)
#                     cover_y = cy + random.randint(-rh // 2 + inset, rh // 2 - inset)
#                     cover_w = random.randint(32, 48)
#                     cover_h = random.randint(32, 48)

#                     builder.add_area(
#                         f"Cover_{room_idx}_{ci}",
#                         shape=(cover_x, cover_y, cover_w, cover_h),
#                         floor_height=64,
#                         ceiling_height=160,
#                         wall_texture=random.choice(["CRATE1", "CRATE2", "CRATWIDE"]),
#                         mode="overwrite"
#                     )

#                 room_idx += 1

        
#         cw = cfg["corridor_width"]
#         corridor_tag_counter = 600

        
#         def add_curved_corridor(src_name, dst_name, wall_tex="METAL1", use_waypoint=False):
#             nonlocal corridor_tag_counter
#             ctag = corridor_tag_counter
#             corridor_tag_counter += 1

#             if use_waypoint:
                
#                 src_data = next((r for r in rooms if r[0] == src_name), None)
#                 dst_data = next((r for r in rooms if r[0] == dst_name), None)
                
#                 if src_name == "Entry":
#                     sx, sy = entry_w // 2, entry_h // 2
#                 elif src_data:
#                     sx, sy = src_data[1], src_data[2]
#                 else:
#                     sx, sy = 0, 0
#                 if dst_data:
#                     dx, dy = dst_data[1], dst_data[2]
#                 else:
#                     dx, dy = 0, 0

#                 mid_x = (sx + dx) // 2
#                 mid_y = (sy + dy) // 2
                
#                 dir_x = dx - sx
#                 dir_y = dy - sy
#                 length = max(1, int(math.sqrt(dir_x * dir_x + dir_y * dir_y)))
                
#                 offset_mag = random.choice([-1, 1]) * random.randint(80, 160)
#                 perp_x = -dir_y * offset_mag // length
#                 perp_y = dir_x * offset_mag // length

#                 wp_x = mid_x + perp_x
#                 wp_y = mid_y + perp_y
#                 wp_name = f"WP_{src_name}_{dst_name}"

#                 builder.add_area(
#                     wp_name,
#                     shape=(wp_x, wp_y, 128, 128),
#                     floor_height=0,
#                     ceiling_height=160,
#                     floor_texture="FLAT19",
#                     ceiling_texture="CEIL3_5",
#                     wall_texture=wall_tex,
#                     light_level=ambient - 20,
#                     tag=ctag
#                 )
                
                
#                 ox = random.choice([-24, 24])
#                 oy = random.choice([-24, 24])
#                 builder.add_area(
#                     f"Cover_{wp_name}",
#                     shape=(wp_x + ox, wp_y + oy, 40, 40),
#                     floor_height=64,
#                     ceiling_height=160,
#                     wall_texture=random.choice(["CRATE1", "CRATE2"]),
#                     mode="overwrite"
#                 )
#                 corridor_tags.append(ctag)

                
#                 ctag2 = corridor_tag_counter
#                 corridor_tag_counter += 1
#                 builder.add_corridor(
#                     src_name, wp_name,
#                     width=cw,
#                     floor_texture="FLAT19",
#                     wall_texture=wall_tex,
#                     light_level=ambient - 20,
#                     tag=ctag2
#                 )
#                 corridor_tags.append(ctag2)

                
#                 ctag3 = corridor_tag_counter
#                 corridor_tag_counter += 1
#                 builder.add_corridor(
#                     wp_name, dst_name,
#                     width=cw,
#                     floor_texture="FLAT19",
#                     wall_texture=wall_tex,
#                     light_level=ambient - 20,
#                     tag=ctag3
#                 )
#                 corridor_tags.append(ctag3)

#             else:
#                 builder.add_corridor(
#                     src_name, dst_name,
#                     width=cw,
#                     floor_texture="FLAT19",
#                     wall_texture=wall_tex,
#                     light_level=ambient - 20,
#                     tag=ctag
#                 )
#                 corridor_tags.append(ctag)

        
#         connect_count = min(3, len(room_names))
#         for i in range(connect_count):
#             add_curved_corridor("Entry", room_names[i], "METAL1", use_waypoint=(i % 2 == 0))

        
#         for i in range(len(room_names) - 1):
#             add_curved_corridor(
#                 room_names[i], room_names[i + 1], "STONE2",
#                 use_waypoint=(i % 3 != 0)
#             )

        
#         if len(room_names) > 4:
#             cross_pairs = random.sample(
#                 [(i, j) for i in range(len(room_names))
#                  for j in range(i + 2, min(i + 5, len(room_names)))],
#                 k=min(3, len(room_names) // 3)
#             )
#             for i, j in cross_pairs:
#                 try:
#                     add_curved_corridor(
#                         room_names[i], room_names[j], "BROWN1",
#                         use_waypoint=True
#                     )
#                 except Exception:
#                     pass

        
#         builder.add_thing(ThingType.PLAYER1_START, -64, -32, angle=90)
#         builder.add_thing(ThingType.PLAYER2_START, 64, -32, angle=90)
#         builder.add_thing(ThingType.PLAYER3_START, -64, 32, angle=90)
#         builder.add_thing(ThingType.PLAYER4_START, 64, 32, angle=90)

        
#         enemy_spot_base = 2000
#         total_enemy_spots = 0
#         enemy_spot_positions = []
#         for i, rname in enumerate(room_names):
#             spots_per_room = random.randint(6, 10)
#             for s in range(spots_per_room):
#                 pt = builder.get_random_point_in_area(rname, safe=True)
#                 if pt:
#                     builder.add_thing(
#                         ThingType.MAP_SPOT, pt[0], pt[1],
#                         tid=enemy_spot_base + total_enemy_spots
#                     )
#                     enemy_spot_positions.append((int(pt[0]), int(pt[1])))
#                     total_enemy_spots += 1

        
#         civilian_spot_base = 3000
#         total_civilian_spots = 0
#         civilian_spot_positions = []
#         civilian_rooms = random.sample(
#             room_names,
#             k=max(3, int(len(room_names) * 0.8))
#         )
#         for rname in civilian_rooms:
            
#             for _ in range(3):
#                 pt = builder.get_random_point_in_area(rname, safe=True)
#                 if pt:
#                     builder.add_thing(
#                         ThingType.MAP_SPOT, pt[0], pt[1],
#                         tid=civilian_spot_base + total_civilian_spots
#                     )
#                     civilian_spot_positions.append((int(pt[0]), int(pt[1])))
#                     total_civilian_spots += 1

        
#         acs = ACSBuilder()
#         acs.add_include("zcommon.acs")
        
#         acs.add_global_var("cqb_score_global", 50, "int")
#         acs.add_global_var("cqb_rooms_cleared_global", 51, "int")
#         acs.add_global_var("cqb_alive_enemies_global", 52, "int")
#         acs.add_global_var("cqb_alive_civilians_global", 53, "int")
#         acs.add_global_var("cqb_flashlight_p0_global", 54, "int")
#         acs.add_global_var("cqb_flashlight_p1_global", 55, "int")
#         acs.add_global_var("cqb_wave_global", 56, "int")

#         room_tags_str = ", ".join(str(t) for t in room_tags)

#         enemy_spot_x_str = ", ".join(str(p[0]) for p in enemy_spot_positions) if enemy_spot_positions else "0"
#         enemy_spot_y_str = ", ".join(str(p[1]) for p in enemy_spot_positions) if enemy_spot_positions else "0"
#         civ_spot_x_str = ", ".join(str(p[0]) for p in civilian_spot_positions) if civilian_spot_positions else "0"
#         civ_spot_y_str = ", ".join(str(p[1]) for p in civilian_spot_positions) if civilian_spot_positions else "0"

#         acs_code = f"""
# #define MAX_ENEMIES {cfg['max_enemies']}
# #define MAX_CIVILIANS {cfg['max_civilians']}
# #define NUM_ROOMS {len(room_names)}
# #define PLAYER_COUNT {cfg['player_count']}
# #define AMBIENT_LIGHT {ambient}
# #define ENEMY_DETECT_RADIUS {cfg['enemy_detect_radius']}
# #define FLASH_DETECT_RADIUS {cfg['flashlight_detect_radius']}
# #define ENEMY_SPOT_BASE {enemy_spot_base}
# #define TOTAL_ENEMY_SPOTS {total_enemy_spots}
# #define CIV_SPOT_BASE {civilian_spot_base}
# #define TOTAL_CIV_SPOTS {total_civilian_spots}
# #define ENEMY_TID_BASE 800
# #define CIV_TID_BASE 700
# #define PLAYER_TID_BASE 400
# #define SPAWN_INTERVAL {cfg['spawn_interval_tics']}
# #define ENTRY_TAG 500
# #define MIN_SPAWN_DIST {cfg['min_spawn_distance']}

# int room_tags[{len(room_names)}] = {{ {room_tags_str} }};
# int enemy_aware[MAX_ENEMIES];
# int cover_timer[MAX_ENEMIES];
# int slot_dead_timer[MAX_ENEMIES];

# int espawn_x[{max(1, total_enemy_spots)}] = {{ {enemy_spot_x_str} }};
# int espawn_y[{max(1, total_enemy_spots)}] = {{ {enemy_spot_y_str} }};
# int cspawn_x[{max(1, total_civilian_spots)}] = {{ {civ_spot_x_str} }};
# int cspawn_y[{max(1, total_civilian_spots)}] = {{ {civ_spot_y_str} }};

# script "ToggleFlashlight" (void) NET {{
#     int pNum = PlayerNumber();
#     int tid = 1000 + pNum;

#     if (CheckInventory("FlashlightToken") == 0) {{
#         GiveInventory("FlashlightToken", 1);
#         SpawnForced("FlashlightTarget", GetActorX(0), GetActorY(0), GetActorZ(0) + 40.0, tid, 0);
#         ACS_NamedExecuteAlways("FlashlightTicker", 0, pNum);
#         LocalAmbientSound("switches/normbutn", 80);
#     }} else {{
#         TakeInventory("FlashlightToken", 1);
#         Thing_Remove(tid);
#         LocalAmbientSound("switches/normbutn", 50);
#     }}

#     if (pNum == 0) cqb_flashlight_p0_global = CheckInventory("FlashlightToken");
#     if (pNum == 1) cqb_flashlight_p1_global = CheckInventory("FlashlightToken");
# }}

# script 10 OPEN {{
#     while (TRUE) {{
#         int p;
#         for (p = 0; p < PLAYER_COUNT; p++) {{
#             int ptid = PLAYER_TID_BASE + p;
#             if (GetActorProperty(ptid, APROP_Health) <= 0) continue;

#             int light = GetActorLightLevel(ptid);
#             int in_flux = 0;

#             if (CheckActorInventory(ptid, "FlashlightToken") > 0) in_flux = 1;
#             if (light > 95) in_flux = 1;

#             if (in_flux) {{
#                 GiveActorInventory(ptid, "PlayerInLight", 1);
#             }} else {{
#                 TakeActorInventory(ptid, "PlayerInLight", 1);
#             }}
#         }}
#         Delay(5);
#     }}
# }}

# script "FlashlightTicker" (int pNum) {{
#     int tid = 1000 + pNum;
#     while (CheckInventory("FlashlightToken") > 0) {{
#         SetActorPosition(tid, GetActorX(0), GetActorY(0), GetActorZ(0) + 40.0, FALSE);
#         Delay(1);
#     }}
# }}

# script 50 (void) NET {{
#     ACS_NamedExecuteAlways("ToggleFlashlight", 0);
# }}

# script 100 ENTER {{
#     int pid = PlayerNumber();
#     Thing_ChangeTID(0, PLAYER_TID_BASE + pid);

#     ClearInventory();

#     if (pid == 0) {{
#         GiveInventory("SuperShotgun", 1);
#         GiveInventory("Shell", 20);
#         SetWeapon("SuperShotgun");
#     }} else {{
#         GiveInventory("PlasmaRifle", 1);
#         GiveInventory("Cell", 40);
#         SetWeapon("PlasmaRifle");
#     }}

#     GiveInventory("GreenArmor", 1);

#     HudMessage(s:"\\cGCQB OPERATION ACTIVE";
#         HUDMSG_FADEOUT, 10, CR_GREEN, 0.5, 0.3, 3.0, 1.0);
#     HudMessage(s:"\\cDFriendly fire: ENABLED | Civilians: DO NOT ENGAGE | Press F: Flashlight";
#         HUDMSG_FADEOUT, 11, CR_GOLD, 0.5, 0.35, 5.0, 1.0);
# }}

# script 1 OPEN {{
#     cqb_score_global = 0;
#     cqb_rooms_cleared_global = 0;
#     cqb_alive_enemies_global = 0;
#     cqb_alive_civilians_global = 0;
#     cqb_wave_global = 0;

#     int i;
#     for (i = 0; i < MAX_ENEMIES; i++) {{
#         enemy_aware[i] = 0;
#         cover_timer[i] = 0;
#     }}

#     while (TRUE) {{
#         int alive_e = 0;
#         int alive_c = 0;
#         for (i = 0; i < MAX_ENEMIES; i++) {{
#             if (ThingCount(T_NONE, ENEMY_TID_BASE + i) > 0) alive_e++;
#         }}
#         for (i = 0; i < MAX_CIVILIANS; i++) {{
#             if (ThingCount(T_NONE, CIV_TID_BASE + i) > 0) alive_c++;
#         }}
#         cqb_alive_enemies_global = alive_e;
#         cqb_alive_civilians_global = alive_c;

#         SetFont("SMALLFONT");
#         HudMessage(s:"\\cDHOSTILES: ", d:alive_e,
#                    s:"  \\cCCIVILIANS: ", d:alive_c,
#                    s:"  \\cGSCORE: ", d:cqb_score_global,
#                    s:"  \\cNWAVE: ", d:cqb_wave_global;
#             HUDMSG_PLAIN, 1, CR_WHITE, 0.5, 0.05, 0.1);

#         Delay(4);
#     }}
# }}

# function int NearestPlayerDistSq(int sx, int sy) {{
#     int best = 2147483647;
#     int p;
#     for (p = 0; p < PLAYER_COUNT; p++) {{
#         int ptid = PLAYER_TID_BASE + p;
#         if (GetActorProperty(ptid, APROP_Health) <= 0) continue;
#         int px = GetActorX(ptid) >> 16;
#         int py = GetActorY(ptid) >> 16;
#         int dx = sx - px;
#         int dy = sy - py;
#         int dsq = dx * dx + dy * dy;
#         if (dsq < best) best = dsq;
#     }}
#     return best;
# }}

# script 2 OPEN {{
#     Delay(35 * 4);

#     int wave = 0;
#     int min_dist_sq = MIN_SPAWN_DIST * MIN_SPAWN_DIST;
#     int last_spot_used = -1;

#     while (TRUE) {{
#         wave++;
#         cqb_wave_global = wave;

#         int needed = 0;
#         int slot_free[MAX_ENEMIES];
#         int i;
#         for (i = 0; i < MAX_ENEMIES; i++) {{
#             if (slot_dead_timer[i] > 0) {{
#                 slot_dead_timer[i]--;
#                 slot_free[i] = 0;
#             }} else if (ThingCount(T_NONE, ENEMY_TID_BASE + i) == 0) {{
#                 slot_free[i] = 1;
#                 needed++;
#             }} else {{
#                 slot_free[i] = 0;
#             }}
#         }}

#         int to_spawn = needed;
#         if (to_spawn > 5) to_spawn = 5;

#         int valid_spots[TOTAL_ENEMY_SPOTS];
#         int num_valid = 0;
#         int s;
#         for (s = 0; s < TOTAL_ENEMY_SPOTS; s++) {{
#             int dsq = NearestPlayerDistSq(espawn_x[s], espawn_y[s]);
#             if (dsq >= min_dist_sq) {{
#                 valid_spots[num_valid] = s;
#                 num_valid++;
#             }}
#         }}

#         int spawned = 0;
#         if (num_valid > 0) {{
#             for (i = 0; i < MAX_ENEMIES && spawned < to_spawn; i++) {{
#                 if (slot_free[i] == 0) continue;

#                 int rand_idx = Random(0, num_valid - 1);
#                 int real_spot = valid_spots[rand_idx];
#                 int spot_tid = ENEMY_SPOT_BASE + real_spot;

#                 str etype = "CQBHostile";
#                 if (wave > 2 && Random(0, 3) == 0) etype = "CQBHostileElite";
#                 if (wave > 5 && Random(0, 4) == 0) etype = "CQBHostileElite";

#                 int tmp_tid = 9900;
#                 if (SpawnSpotFacing(etype, spot_tid, tmp_tid)) {{
#                     enemy_aware[i] = 0;
#                     cover_timer[i] = Random(105, 245);
#                     Thing_ChangeTID(tmp_tid, ENEMY_TID_BASE + i);
#                     spawned++;
#                 }}
#             }}
#         }}

#         Delay(SPAWN_INTERVAL);
#     }}
# }}

# script 3 OPEN {{
#     Delay(35 * 2);

#     int min_dist_sq = MIN_SPAWN_DIST * MIN_SPAWN_DIST;
#     int last_civ_spot = -1;

#     while (TRUE) {{
#         int i;
#         int s;

#         int needed = 0;
#         for (i = 0; i < MAX_CIVILIANS; i++) {{
#             if (ThingCount(T_NONE, CIV_TID_BASE + i) == 0) needed++;
#         }}
#         if (needed > 2) needed = 2;

#         int valid_spots[TOTAL_CIV_SPOTS];
#         int num_valid = 0;
#         for (s = 0; s < TOTAL_CIV_SPOTS; s++) {{
#             int dsq = NearestPlayerDistSq(cspawn_x[s], cspawn_y[s]);
#             if (dsq >= min_dist_sq) {{
#                 valid_spots[num_valid] = s;
#                 num_valid++;
#             }}
#         }}

#         int spawned = 0;
#         if (num_valid > 0) {{
#             int spot_idx = (last_civ_spot + 1) % num_valid;
#             for (i = 0; i < MAX_CIVILIANS && spawned < needed; i++) {{
#                 if (ThingCount(T_NONE, CIV_TID_BASE + i) > 0) continue;

#                 int real_spot = valid_spots[spot_idx % num_valid];
#                 int spot_tid = CIV_SPOT_BASE + real_spot;

#                 int tmp_tid = 9901;
#                 if (SpawnSpotFacing("CQBCivilian", spot_tid, tmp_tid)) {{
#                     Thing_ChangeTID(tmp_tid, CIV_TID_BASE + i);
#                     spawned++;
#                     last_civ_spot = spot_idx;
#                     spot_idx = (spot_idx + 2) % num_valid;
#                 }} else {{
#                     spot_idx = (spot_idx + 1) % num_valid;
#                 }}
#             }}
#         }}

#         Delay(35 * 8);
#     }}
# }}

# script 4 OPEN {{
#     while (TRUE) {{
#         int i;
#         int p;

#         for (i = 0; i < MAX_ENEMIES; i++) {{
#             int etid = ENEMY_TID_BASE + i;

#             if (ThingCount(T_NONE, etid) == 0) continue;
#             if (GetActorProperty(etid, APROP_Health) <= 0) continue;

#             int ex = GetActorX(etid) >> 16;
#             int ey = GetActorY(etid) >> 16;

#             int should_wake = 0;
#             int closest_ptid = 0;
#             int closest_dist = 2147483647;

#             for (p = 0; p < PLAYER_COUNT; p++) {{
#                 int ptid = PLAYER_TID_BASE + p;
#                 if (GetActorProperty(ptid, APROP_Health) <= 0) continue;

#                 int px = GetActorX(ptid) >> 16;
#                 int py = GetActorY(ptid) >> 16;
#                 int dx = ex - px;
#                 int dy = ey - py;
#                 int dist_sq = dx * dx + dy * dy;

#                 if (dist_sq < closest_dist) {{
#                     closest_dist = dist_sq;
#                     closest_ptid = ptid;
#                 }}

#                 int close_prox = 192 * 192;
                
#                 if (dist_sq < close_prox) {{
#                     should_wake = 1;
#                 }}

#                 if (CheckSight(etid, ptid, 0)) {{
#                     if (CheckActorInventory(ptid, "FlashlightToken") > 0) {{
#                         if (dist_sq < 2048 * 2048) {{
#                             should_wake = 1;
#                         }}
#                     }} else if (CheckActorInventory(ptid, "PlayerInLight") > 0) {{
#                         if (dist_sq < 1024 * 1024) {{
#                             should_wake = 1;
#                         }}
#                     }} else {{
#                         if (dist_sq < 256 * 256) {{
#                             should_wake = 1;
#                         }}
#                     }}
#                 }}
#             }}

#             if (should_wake && enemy_aware[i] == 0) {{
#                 enemy_aware[i] = 1;
#                 SetActorState(etid, "See");
#                 if (closest_ptid > 0) {{
#                     Thing_Hate(etid, closest_ptid, 1);
#                 }}
#             }}
#         }}

#         Delay(15);
#     }}
# }}

# script 997 (void) {{
#     int tid = ActivatorTID();
#     int slot = tid - ENEMY_TID_BASE;

#     if (slot >= 0 && slot < MAX_ENEMIES) {{
#         enemy_aware[slot] = 0;
#         slot_dead_timer[slot] = 5; 
#     }}

#     cqb_score_global++;

#     int p;
#     for (p = 0; p < PLAYER_COUNT; p++) {{
#         int ptid = PLAYER_TID_BASE + p;
#         GiveActorInventory(ptid, "Shell", 2);
#         GiveActorInventory(ptid, "Cell", 2);
#     }}

#     Delay(35 * 4);
#     Thing_Remove(0);
# }}

# script 998 (void) {{
#     SetActivatorToTarget(0);
    
#     if (PlayerNumber() != -1) {{
#         hudmessage(s:"CIVILIAN CASUALTY! MISSION FAILED."; HUDMSG_PLAIN, 1, CR_RED, 0.5, 0.4, 5.0);
#         DamageThing(0);
#     }} else {{
#         hudmessage(s:"Civilian killed by hostile forces."; HUDMSG_PLAIN, 2, CR_ORANGE, 0.5, 0.45, 3.0);
#     }}
# }}

# script "TeammateDamageHandler" (void) {{
#     int victim_num = PlayerNumber();
    
#     if (SetActivatorToTarget(0)) {{
#         int attacker_num = PlayerNumber();
        
#         if (attacker_num != -1 && attacker_num != victim_num) {{
#             SetFont("BIGFONT");
#             HudMessage(s:"\\cRFRIENDLY FIRE - MISSION FAILED";
#                 HUDMSG_PLAIN, 1, CR_RED, 0.5, 0.4, 5.0);
            
#             Log(s:"Friendly Fire: Player ", d:attacker_num, s:" hit Player ", d:victim_num);
            
#             Delay(35);
#             DamageThing(0, 0);
#         }}
#     }}
# }}

# script 999 DEATH {{
#     if (PlayerNumber() != -1) {{
#         SetFont("BIGFONT");
#         HudMessage(s:"\\cRMISSION FAILED\\c- - OPERATIVE DOWN";
#             HUDMSG_PLAIN, 99, CR_RED, 0.5, 0.5, 3.0);

#         Delay(35 * 2);
#         Exit_Normal(0);
#     }}
# }}
# """

#         acs.add_global_code(acs_code)

#         builder.map_data.scripts = acs.to_code()
#         try:
#             compiled = acs.compile()
#             if compiled:
#                 builder.map_data.behavior = compiled
#             else:
#                 print("ACS: No bytecode generated, scripts will compile at load time.")
#                 builder.map_data.behavior = b'ACSE\x08\x00\x00\x00\x00\x00\x00\x00'
#         except Exception as e:
#             print(f"ACS Compilation Warning: {e}")
#             if hasattr(e, 'stderr') and e.stderr:
#                 print(f"ACC Stderr: {e.stderr}")
#             builder.map_data.behavior = b'ACSE\x08\x00\x00\x00\x00\x00\x00\x00'

#         builder.build(output_path)
#         print(f"CQB Benchmark WAD written to {output_path}")


# if __name__ == "__main__":
#     os.makedirs("examples/benchmark/output", exist_ok=True)
#     scenario = CoopCQBScenario(config={"seed": random.randint(0, 99999)})
#     scenario.generate("examples/benchmark/output/coop_cqb.wad")
