import os
import random
from typing import Dict, Any, List, Tuple, Optional

from doomgen.batch.scenario import Scenario
from doomgen.abstraction.layout import ConnectionType
from doomgen.builder import ProceduralMapBuilder
from doomgen.logic.acs_builder import ACSBuilder, ScriptType
from doomgen.doom.things import ThingType


class CoopCQBScenario(Scenario):
    """
    Cooperative Close Quarters Battle (CQB) benchmark.
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "seed": None,
            "num_seeds": 9000,
            "corridor_width": 3,
            "enemy_cap": 6,
            "civilian_cap": 8,
            "enemy_spawn_interval_tics": 30,
            "civilian_spawn_interval_tics": 50,
            "enemy_spots": 36,
            "civilian_spots": 36,
            "max_enemy_slots": 28,
            "max_civilian_slots": 20,
        }

    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)
        rng = random.Random(seed)

        builder = ProceduralMapBuilder(
            bounds=(-1900, -1400, 1900, 1400),
            num_seeds=int(cfg["num_seeds"]),
            seed=seed,
        )

        corridor_width = int(cfg["corridor_width"])

        builder.add_area("SpawnHub", shape=(0, 0, 320, 240), floor_height=0, ceiling_height=160, floor_texture="FLAT5_4", ceiling_texture="CEIL5_2", wall_texture="STARTAN3", light_level=224)
        builder.add_area("Extraction", shape=(0, -250, 260, 180), floor_height=0, ceiling_height=156, floor_texture="FLAT5_4", wall_texture="STARTAN3", light_level=210)
        builder.add_area("SpineA", shape=(0, 250, 120, 280), floor_height=0, ceiling_height=148, floor_texture="FLOOR7_1", wall_texture="GRAY7", light_level=168)
        builder.add_area("SpineB", shape=(0, 520, 120, 260), floor_height=0, ceiling_height=152, floor_texture="FLOOR7_1", wall_texture="GRAY7", light_level=164)
        builder.add_area("SpineC", shape=(0, 790, 120, 260), floor_height=0, ceiling_height=164, floor_texture="FLOOR7_1", wall_texture="GRAY7", light_level=160)
        builder.add_area("Breach", shape=(0, 1060, 260, 220), floor_height=0, ceiling_height=168, floor_texture="RROCK19", wall_texture="STARTAN2", light_level=152)

        builder.add_area("WestBypassA", shape=(-250, 390, 320, 110), floor_height=0, ceiling_height=146, floor_texture="FLAT5_4", wall_texture="STONE2", light_level=158)
        builder.add_area("WestBypassB", shape=(-520, 680, 320, 110), floor_height=0, ceiling_height=150, floor_texture="FLAT5_4", wall_texture="STONE2", light_level=154)
        builder.add_area("WestFlank", shape=(-760, 920, 240, 200), floor_height=0, ceiling_height=156, floor_texture="RROCK19", wall_texture="BROWN1", light_level=148)
        builder.add_area("WestReadyRoom", shape=(-940, 620, 460, 320), floor_height=0, ceiling_height=160, floor_texture="FLAT5_4", wall_texture="STARTAN2", light_level=162)
        builder.add_area("WestObservation", shape=(-1020, 900, 320, 220), floor_height=0, ceiling_height=164, floor_texture="RROCK19", wall_texture="GRAY5", light_level=150)

        builder.add_area("EastBypassA", shape=(250, 390, 320, 110), floor_height=0, ceiling_height=146, floor_texture="FLAT5_4", wall_texture="STONE2", light_level=158)
        builder.add_area("EastBypassB", shape=(520, 680, 320, 110), floor_height=0, ceiling_height=150, floor_texture="FLAT5_4", wall_texture="STONE2", light_level=154)
        builder.add_area("EastFlank", shape=(760, 920, 240, 200), floor_height=0, ceiling_height=156, floor_texture="RROCK19", wall_texture="BROWN1", light_level=148)
        builder.add_area("EastReadyRoom", shape=(940, 620, 460, 320), floor_height=0, ceiling_height=160, floor_texture="FLAT5_4", wall_texture="STARTAN2", light_level=162)
        builder.add_area("EastObservation", shape=(1020, 900, 320, 220), floor_height=0, ceiling_height=164, floor_texture="RROCK19", wall_texture="GRAY5", light_level=150)
        builder.add_area("BreachHall", shape=(0, 1260, 620, 360), floor_height=0, ceiling_height=180, floor_texture="RROCK19", wall_texture="STARTAN2", light_level=148)

        # Tactical low-ground pits (exposure), passable but disadvantageous.
        builder.add_area("PitWestRoom", shape=(-930, 620, 120, 90), mode="overwrite", floor_height=-24, ceiling_height=160, floor_texture="RROCK19", wall_texture="BROWN1")
        builder.add_area("PitEastRoom", shape=(930, 620, 120, 90), mode="overwrite", floor_height=-24, ceiling_height=160, floor_texture="RROCK19", wall_texture="BROWN1")
        builder.add_area("PitBreachHall", shape=(0, 1260, 140, 100), mode="overwrite", floor_height=-16, ceiling_height=180, floor_texture="RROCK19", wall_texture="BROWN1")

        builder.add_corridor("Extraction", "SpawnHub", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("SpawnHub", "SpineA", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("SpineA", "SpineB", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("SpineB", "SpineC", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("SpineC", "Breach", width=corridor_width, floor_texture="FLOOR7_1")

        builder.add_corridor("SpineA", "WestBypassA", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("WestBypassA", "WestBypassB", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("WestBypassB", "WestFlank", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("WestFlank", "Breach", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("WestBypassB", "WestReadyRoom", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("WestFlank", "WestObservation", width=corridor_width, floor_texture="FLOOR7_1")

        builder.add_corridor("SpineA", "EastBypassA", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("EastBypassA", "EastBypassB", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("EastBypassB", "EastFlank", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("EastFlank", "Breach", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("EastBypassB", "EastReadyRoom", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("EastFlank", "EastObservation", width=corridor_width, floor_texture="FLOOR7_1")

        builder.add_corridor("WestBypassB", "SpineC", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("EastBypassB", "SpineC", width=corridor_width, floor_texture="FLOOR7_1")
        builder.add_corridor("Breach", "BreachHall", width=corridor_width, floor_texture="FLOOR7_1")

        tactical_areas = [
            "Extraction",
            "SpawnHub",
            "SpineA",
            "SpineB",
            "SpineC",
            "Breach",
            "WestBypassA",
            "WestBypassB",
            "WestFlank",
            "WestReadyRoom",
            "WestObservation",
            "EastBypassA",
            "EastBypassB",
            "EastFlank",
            "EastReadyRoom",
            "EastObservation",
            "BreachHall",
        ]
        for area_a in tactical_areas:
            for area_b in tactical_areas:
                if area_a != area_b:
                    builder.connect_adjacent(area_a, area_b, ConnectionType.OPEN, silent=True)

        # Center-room cover only (no corridor cover clutter).

        player_spawns = self._pick_safe_points(builder, "SpawnHub", count=3, min_dist=86, attempts=260)
        while len(player_spawns) < 3:
            fallback = builder.get_random_point_in_area("SpawnHub", safe=False)
            if fallback is None:
                raise RuntimeError("Failed to place all player starts in SpawnHub")
            player_spawns.append(fallback)

        player_starts = [ThingType.PLAYER1_START, ThingType.PLAYER2_START, ThingType.PLAYER3_START]
        player_angles = [0, 32, 352]
        for i, (x, y) in enumerate(player_spawns):
            builder.add_thing(player_starts[i], x, y, angle=player_angles[i])

        enemy_area_cycle = ["BreachHall", "Breach", "SpineC", "WestFlank", "EastFlank", "WestObservation", "EastObservation", "WestBypassB", "EastBypassB", "SpineB"]
        civilian_area_cycle = [
            "WestReadyRoom",
            "EastReadyRoom",
            "WestObservation",
            "EastObservation",
            "BreachHall",
            "Breach",
            "SpawnHub",
            "Extraction",
        ]

        enemy_spot_count = self._place_map_spots(
            builder,
            base_tid=6000,
            count=int(cfg["enemy_spots"]),
            area_cycle=enemy_area_cycle,
            rng=rng,
            avoid_points=player_spawns,
            min_distance=760.0,
        )
        civilian_spot_count = self._place_map_spots(
            builder,
            base_tid=7000,
            count=int(cfg["civilian_spots"]),
            area_cycle=civilian_area_cycle,
            rng=rng,
        )

        civ_goal_areas = ["Breach", "SpineC", "SpineB", "WestReadyRoom", "EastReadyRoom", "SpineA", "SpawnHub", "Extraction"]
        civ_goal_count = self._place_map_spots(
            builder,
            base_tid=8500,
            count=14,
            area_cycle=civ_goal_areas,
            rng=rng,
        )
        extract_point = builder.get_random_point_in_area("Extraction", safe=True) or builder.get_random_point_in_area("Extraction", safe=False)
        if extract_point is None:
            raise RuntimeError("Failed to place civilian extraction point")
        builder.add_thing(ThingType.MAP_SPOT, extract_point[0], extract_point[1], tid=8599, angle=0)

        if enemy_spot_count < 8:
            raise RuntimeError("Not enough safe enemy MapSpots were placed for CQB spawns")
        if civilian_spot_count < 6:
            raise RuntimeError("Not enough safe civilian MapSpots were placed for CQB spawns")
        if civ_goal_count < 6:
            raise RuntimeError("Not enough civilian navigation MapSpots were placed")

        self._place_supply_in_cover(builder, rng)
        self._add_center_room_cover(builder)

        decorate_str = """
ACTOR CQBCivilian : DoomImp 16000
{
    Health 55
  Radius 16
  Height 56
    Speed 14
    ReactionTime 6
        Translation "112:127=200:215"
  +SOLID
  +SHOOTABLE
  +NOBLOOD
    +LOOKALLAROUND
        +FRIGHTENED
  DamageFactor "Explosion", 0.15

  States
  {
  Spawn:
      TROO A 4 A_Look
      TROO B 4
    Loop
  See:
      TROO AABBCCDD 2 A_Chase
        Loop
    Missile:
        Goto See
    Melee:
        Goto See
  Pain:
                TROO E 4
        Goto See
    Death.EnemyFire:
                                TROO I 0 ACS_ExecuteAlways(953, 0)
                                TROO I 6
                                TROO J 6 A_Scream
                                TROO K 6 A_NoBlocking
                                TROO L -1
        Stop
  Death:
                TROO I 0 ACS_ExecuteAlways(952, 0)
                TROO I 6
                TROO J 6 A_Scream
                TROO K 6 A_NoBlocking
                TROO L -1
    Stop
  }
}

ACTOR CQBEnemyShot 16003
{
    Radius 2
    Height 2
    Speed 140
    Damage 2
    DamageType "EnemyFire"
    Projectile
    +NOGRAVITY
    +RIPPER
    States
    {
    Spawn:
        MISL A 1 Bright
        Loop
    Death:
        BAL1 BCD 2 Bright
        Stop
    }
}

ACTOR CQBMarksman : Zombieman 16001
{
    Speed 11
    ReactionTime 6
    PainChance 22
    Translation "112:127=176:191"
    +AMBUSH
    +LOOKALLAROUND
        DropItem "Cell"
        DropItem "Shell"
  States
  {
        Spawn:
                POSS AB 4 A_Look
                Loop
        See:
                POSS AABBCCDD 2 A_Chase
                Loop
    Missile:
                POSS E 1 A_FaceTarget
            POSS F 0 A_CustomMissile("CQBEnemyShot", 32, 0, 0, 0, 0)
            POSS F 0 A_CustomMissile("CQBEnemyShot", 32, 0, 0, 0, 0)
                POSS F 1
        Goto See
  Death:
                POSS H 6
                POSS I 6 A_Scream
                POSS J 6 A_NoBlocking
                                                                POSS K -1
    Stop
  }
}
"""
        builder.wad_writer.add_lump("DECORATE", decorate_str.encode("utf-8"))

        mapinfo_str = """
GameInfo
{
    teamdamage = 1.0
}

map MAP01 "Coop CQB"
{
  allowmonstertelefrags
}
"""
        builder.wad_writer.add_lump("MAPINFO", mapinfo_str.encode("utf-8"))

        acs = ACSBuilder()
        acs.add_global_code(
            f"""
#include "zcommon.acs"

#define MAX_PLAYERS 3
#define PLAYER_BASE_TID 1000
#define CIV_SLOT_BASE 3000
#define CIV_TMP_TID 9600
#define ENEMY_TID_BASE 2000
#define ENEMY_TID_LIMIT 9000

#define ENEMY_SPOT_BASE 6000
#define CIV_SPOT_BASE 7000
#define CIV_GOAL_BASE 8500

#define NUM_ENEMY_SPOTS {enemy_spot_count}
#define NUM_CIV_SPOTS {civilian_spot_count}
#define NUM_CIV_GOALS {civ_goal_count}
#define CIV_EXTRACT_TID 8599

#define MAX_ENEMY_SLOTS {int(cfg['max_enemy_slots'])}
#define MAX_CIV_SLOTS {int(cfg['max_civilian_slots'])}

#define ENEMY_CAP {int(cfg['enemy_cap'])}
#define CIV_CAP {int(cfg['civilian_cap'])}
#define ENEMY_SPAWN_INTERVAL {int(cfg['enemy_spawn_interval_tics'])}
#define CIV_SPAWN_INTERVAL {int(cfg['civilian_spawn_interval_tics'])}
#define DESPAWN_TICS 1050
#define MIN_ENEMY_SPAWN_DIST 640

global int 40:g_civ_kia;
global int 41:g_civ_kia_e;

int failed = 0;
int finished = 0;
int civilians_escaped = 0;
int civilians_killed_total = 0;
int civilians_killed_with_enemies = 0;
int next_enemy_spawn_time = 0;
int next_civ_spawn_time = 0;
int next_enemy_tid = ENEMY_TID_BASE;
int enemy_track_tid[MAX_ENEMY_SLOTS];
int enemy_birth[MAX_ENEMY_SLOTS];
int civ_birth[MAX_CIV_SLOTS];
int enemy_alert[MAX_ENEMY_SLOTS];
int civ_goal_tid[MAX_CIV_SLOTS];

function int LivingPlayers(void)
{{
    int alive = 0;
    int i;
    for (i = 0; i < MAX_PLAYERS; i++) {{
        int ptid = PLAYER_BASE_TID + i;
        if (GetActorProperty(ptid, APROP_Health) > 0) {{
            alive++;
        }}
    }}
    return alive;
}}

function void EquipPlayer(int player_tid, int player_num)
{{
    ClearActorInventory(player_tid);

    if (player_num == 0) {{
        GiveActorInventory(player_tid, "Shotgun", 1);
        GiveActorInventory(player_tid, "Shell", 40);
        SetActivator(player_tid);
        SetWeapon("Shotgun");
        SetActivator(0);
        return;
    }}

    if (player_num == 1) {{
        GiveActorInventory(player_tid, "PlasmaRifle", 1);
        GiveActorInventory(player_tid, "Cell", 120);
        SetActivator(player_tid);
        SetWeapon("PlasmaRifle");
        SetActivator(0);
        return;
    }}

    GiveActorInventory(player_tid, "Shotgun", 1);
    GiveActorInventory(player_tid, "PlasmaRifle", 1);
    GiveActorInventory(player_tid, "Shell", 24);
    GiveActorInventory(player_tid, "Cell", 80);
    SetActivator(player_tid);
    SetWeapon("Shotgun");
    SetActivator(0);
}}

function int ActiveEnemies(void)
{{
    int alive = 0;
    int i;
    for (i = 0; i < MAX_ENEMY_SLOTS; i++) {{
        int etid = enemy_track_tid[i];
        if (etid > 0 && ThingCount(T_NONE, etid) > 0 && GetActorProperty(etid, APROP_Health) > 0) alive++;
    }}
    return alive;
}}

function int AbsInt(int value)
{{
    if (value < 0) return -value;
    return value;
}}

function int ActiveCivilians(void)
{{
    int alive = 0;
    int i;
    for (i = 0; i < MAX_CIV_SLOTS; i++) {{
        int ctid = CIV_SLOT_BASE + i;
        if (ThingCount(T_NONE, ctid) > 0 && GetActorProperty(ctid, APROP_Health) > 0) alive++;
    }}
    return alive;
}}

function int RandomAliveCivilianTID(void)
{{
    int tries = 0;
    while (tries < 8) {{
        int idx = Random(0, MAX_CIV_SLOTS - 1);
        int ctid = CIV_SLOT_BASE + idx;
        if (ThingCount(T_NONE, ctid) > 0 && GetActorProperty(ctid, APROP_Health) > 0) return ctid;
        tries++;
    }}
    return 0;
}}

function int RandomAliveEnemyTID(void)
{{
    int tries = 0;
    while (tries < 10) {{
        int idx = Random(0, MAX_ENEMY_SLOTS - 1);
        int etid = enemy_track_tid[idx];
        if (etid > 0 && ThingCount(T_NONE, etid) > 0 && GetActorProperty(etid, APROP_Health) > 0) return etid;
        tries++;
    }}
    return 0;
}}

function int AllocateEnemyTID(void)
{{
    int tries = 0;
    while (tries < (ENEMY_TID_LIMIT - ENEMY_TID_BASE)) {{
        if (next_enemy_tid >= ENEMY_TID_LIMIT) {{
            next_enemy_tid = ENEMY_TID_BASE;
        }}
        int candidate = next_enemy_tid;
        next_enemy_tid++;
        if (ThingCount(T_NONE, candidate) == 0) {{
            return candidate;
        }}
        tries++;
    }}
    return 0;
}}

function int RandomAlivePlayerTID(void)
{{
    int tries = 0;
    while (tries < 8) {{
        int pid = Random(0, MAX_PLAYERS - 1);
        int ptid = PLAYER_BASE_TID + pid;
        if (GetActorProperty(ptid, APROP_Health) > 0) return ptid;
        tries++;
    }}
    return 0;
}}

function int GoalForCivilian(int ctid)
{{
    int idx = ctid - CIV_SLOT_BASE;
    if (idx < 0 || idx >= MAX_CIV_SLOTS) return CIV_EXTRACT_TID;
    if (civ_goal_tid[idx] <= 0) {{
        civ_goal_tid[idx] = CIV_GOAL_BASE + Random(0, NUM_CIV_GOALS - 1);
    }}
    return civ_goal_tid[idx];
}}

function void MoveCivilianToward(int ctid, int goal_tid)
{{
    int cx = GetActorX(ctid) >> 16;
    int cy = GetActorY(ctid) >> 16;
    int gx = GetActorX(goal_tid) >> 16;
    int gy = GetActorY(goal_tid) >> 16;
    int dx = gx - cx;
    int dy = gy - cy;
    int vx = 0;
    int vy = 0;
    if (dx > 16) vx = 7;
    if (dx < -16) vx = -7;
    if (dy > 16) vy = 7;
    if (dy < -16) vy = -7;
    SetActorVelocity(ctid, vx, vy, 0.0, 0, 0);
}}

function int VisiblePlayerForEnemy(int enemy_tid)
{{
    int p;
    for (p = 0; p < MAX_PLAYERS; p++) {{
        int ptid = PLAYER_BASE_TID + p;
        if (GetActorProperty(ptid, APROP_Health) > 0) {{
            if (CheckSight(enemy_tid, ptid, 0)) {{
                return ptid;
            }}
        }}
    }}
    return 0;
}}

function int IsSpotSafeFromPlayers(int spot_tid)
{{
    int sx = GetActorX(spot_tid) >> 16;
    int sy = GetActorY(spot_tid) >> 16;
    int p;
    for (p = 0; p < MAX_PLAYERS; p++) {{
        int ptid = PLAYER_BASE_TID + p;
        if (GetActorProperty(ptid, APROP_Health) <= 0) {{
            continue;
        }}
        int px = GetActorX(ptid) >> 16;
        int py = GetActorY(ptid) >> 16;
        if (AbsInt(px - sx) < MIN_ENEMY_SPAWN_DIST && AbsInt(py - sy) < MIN_ENEMY_SPAWN_DIST) {{
            return 0;
        }}
    }}
    return 1;
}}

function int PlayerLikelyCausedCivilianDeath(void)
{{
    int cx = GetActorX(0) >> 16;
    int cy = GetActorY(0) >> 16;
    int p;
    for (p = 0; p < MAX_PLAYERS; p++) {{
        int ptid = PLAYER_BASE_TID + p;
        if (GetActorProperty(ptid, APROP_Health) <= 0) {{
            continue;
        }}
        int px = GetActorX(ptid) >> 16;
        int py = GetActorY(ptid) >> 16;
        if (AbsInt(px - cx) < 224 && AbsInt(py - cy) < 224) {{
            return 1;
        }}
    }}
    return 0;
}}

function void TriggerFail(str msg)
{{
    if (failed || finished) return;
    failed = 1;
    HudMessage(s:msg; HUDMSG_FADEOUT, 900, CR_RED, 0.5, 0.42, 2.0, 1.2);
    FadeTo(1.0, 0.0, 0.0, 0.6, 0.0);
    Exit_Normal(0);
}}

function void AssignEnemyTarget(int enemy_tid)
{{
    int civ_target = RandomAliveCivilianTID();
    if (civ_target > 0) {{
        Thing_Hate(enemy_tid, civ_target, 6);
        Thing_SetGoal(enemy_tid, civ_target, 0);
        Thing_Activate(enemy_tid);
        SetActorState(enemy_tid, "See");
        return;
    }}

    int ptid = RandomAlivePlayerTID();
    if (ptid > 0) {{
        Thing_Hate(enemy_tid, ptid, 6);
        Thing_SetGoal(enemy_tid, ptid, 0);
        Thing_Activate(enemy_tid);
        SetActorState(enemy_tid, "See");
    }}
}}

function int SpawnEnemyAtRandomSpot(int slot_idx)
{{
    int attempts = 0;
    while (attempts < 18) {{
        int spot_tid = ENEMY_SPOT_BASE + Random(0, NUM_ENEMY_SPOTS - 1);
        if (!IsSpotSafeFromPlayers(spot_tid)) {{
            attempts++;
            continue;
        }}
        int etid = AllocateEnemyTID();
        if (etid <= 0) {{
            return 0;
        }}
        if (SpawnSpotFacing("CQBMarksman", spot_tid, etid)) {{
            if (ThingCount(T_NONE, etid) == 0) {{
                attempts++;
                continue;
            }}
            SetActorProperty(etid, APROP_Invulnerable, 0);
            TakeActorInventory(etid, "PowerInvulnerable", 255);
            enemy_track_tid[slot_idx] = etid;
            enemy_birth[slot_idx] = Timer();
            enemy_alert[slot_idx] = 0;
            AssignEnemyTarget(etid);
            Thing_Activate(etid);
            SetActorState(etid, "See");
            return 1;
        }}
        attempts++;
    }}
    return 0;
}}

function void SpawnEnemies(int amount)
{{
    int spawned = 0;
    int i;
    for (i = 0; i < MAX_ENEMY_SLOTS && spawned < amount; i++) {{
        int etid = enemy_track_tid[i];
        if (etid <= 0 || ThingCount(T_NONE, etid) == 0 || GetActorProperty(etid, APROP_Health) <= 0) {{
            enemy_track_tid[i] = 0;
            enemy_birth[i] = 0;
            enemy_alert[i] = 0;
            if (SpawnEnemyAtRandomSpot(i)) {{
                spawned++;
            }}
        }}
    }}
}}

function void SpawnCivilians(int amount)
{{
    int spawned = 0;
    int i;
    for (i = 0; i < MAX_CIV_SLOTS && spawned < amount; i++) {{
        int ctid = CIV_SLOT_BASE + i;
        if (ThingCount(T_NONE, ctid) > 0) {{
            continue;
        }}
        int spot_tid = CIV_SPOT_BASE + Random(0, NUM_CIV_SPOTS - 1);
        if (SpawnSpotFacing("CQBCivilian", spot_tid, CIV_TMP_TID)) {{
            Thing_ChangeTID(CIV_TMP_TID, ctid);
            SetActorProperty(ctid, APROP_Speed, Random(12, 17));
            civ_goal_tid[i] = CIV_GOAL_BASE + Random(0, NUM_CIV_GOALS - 1);
            Thing_SetGoal(ctid, civ_goal_tid[i], 0);
            Thing_Activate(ctid);
            SetActorState(ctid, "See");
            civ_birth[i] = Timer();
            spawned++;
        }}
    }}
}}

function void CivilianBehaviorTick(void)
{{
    int gx = GetActorX(CIV_EXTRACT_TID) >> 16;
    int gy = GetActorY(CIV_EXTRACT_TID) >> 16;
    int i;

    for (i = 0; i < MAX_CIV_SLOTS; i++) {{
        int ctid = CIV_SLOT_BASE + i;
        if (ThingCount(T_NONE, ctid) == 0) {{
            continue;
        }}
        if (GetActorProperty(ctid, APROP_Health) <= 0) {{
            Thing_Remove(ctid);
            civ_birth[i] = 0;
            civ_goal_tid[i] = 0;
            continue;
        }}

        int cx = GetActorX(ctid) >> 16;
        int cy = GetActorY(ctid) >> 16;
        int near_extract = (AbsInt(cx - gx) < 72) && (AbsInt(cy - gy) < 72);
        if (near_extract) {{
            Thing_Remove(ctid);
            civ_birth[i] = 0;
            civilians_escaped++;
            continue;
        }}

        int goal_tid = GoalForCivilian(ctid);
        if (Random(0, 99) < 20) {{
            goal_tid = CIV_GOAL_BASE + Random(0, NUM_CIV_GOALS - 1);
            civ_goal_tid[i] = goal_tid;
        }}
        if (Random(0, 99) < 15) {{
            goal_tid = CIV_EXTRACT_TID;
        }}
        Thing_SetGoal(ctid, goal_tid, 0);
        Thing_Activate(ctid);
        SetActorState(ctid, "See");
        MoveCivilianToward(ctid, goal_tid);

        if (civ_birth[i] > 0 && (Timer() - civ_birth[i]) > DESPAWN_TICS) {{
            Thing_Remove(ctid);
            civ_birth[i] = 0;
            civilians_killed_total++;
            if (ActiveEnemies() > 0) {{
                civilians_killed_with_enemies++;
                g_civ_kia_e = civilians_killed_with_enemies;
            }}
            g_civ_kia = civilians_killed_total;
        }}
    }}
}}

function void EnemyMaintenanceTick(void)
{{
    int i;
    for (i = 0; i < MAX_ENEMY_SLOTS; i++) {{
        int etid = enemy_track_tid[i];
        if (etid <= 0) {{
            enemy_birth[i] = 0;
            enemy_alert[i] = 0;
            continue;
        }}

        if (ThingCount(T_NONE, etid) == 0) {{
            enemy_track_tid[i] = 0;
            enemy_birth[i] = 0;
            enemy_alert[i] = 0;
            continue;
        }}

        SetActorProperty(etid, APROP_Invulnerable, 0);
        TakeActorInventory(etid, "PowerInvulnerable", 255);

        if (GetActorProperty(etid, APROP_Health) <= 0) {{
            enemy_track_tid[i] = 0;
            enemy_birth[i] = 0;
            enemy_alert[i] = 0;
            continue;
        }}

        if (enemy_birth[i] > 0 && (Timer() - enemy_birth[i]) > DESPAWN_TICS) {{
            Thing_Remove(etid);
            enemy_track_tid[i] = 0;
            enemy_birth[i] = 0;
            enemy_alert[i] = 0;
            continue;
        }}

        int vis_player = VisiblePlayerForEnemy(etid);
        if (vis_player > 0) {{
            enemy_alert[i] = 1;
            Thing_Hate(etid, vis_player, 6);
            continue;
        }}

        if (!enemy_alert[i]) {{
            int civ_target = RandomAliveCivilianTID();
            if (civ_target > 0) {{
                Thing_Hate(etid, civ_target, 6);
                Thing_SetGoal(etid, civ_target, 0);
                Thing_Activate(etid);
                SetActorState(etid, "See");
            }} else if (Random(0, 99) < 20) {{
                Thing_SetGoal(etid, ENEMY_SPOT_BASE + Random(0, NUM_ENEMY_SPOTS - 1), 0);
            }}
        }} else if (Random(0, 99) < 35) {{
            int civ_target_alt = RandomAliveCivilianTID();
            if (civ_target_alt > 0) {{
                Thing_Hate(etid, civ_target_alt, 6);
                Thing_SetGoal(etid, civ_target_alt, 0);
                Thing_Activate(etid);
                SetActorState(etid, "See");
            }} else if (Random(0, 99) < 25) {{
                AssignEnemyTarget(etid);
            }}
        }}
    }}

}}
"""
        )

        acs.add_script(
            ScriptType.ENTER,
            """
int pn = PlayerNumber();
int ptid = PLAYER_BASE_TID + pn;
Thing_ChangeTID(0, ptid);
EquipPlayer(ptid, pn);

""",
            number=100,
        )

        acs.add_script(
            ScriptType.RESPAWN,
            """
int pn = PlayerNumber();
int ptid = PLAYER_BASE_TID + pn;
Thing_ChangeTID(0, ptid);
EquipPlayer(ptid, pn);
""",
            number=101,
        )

        acs.add_script(
            ScriptType.OPEN,
            """
Delay(20);
next_enemy_spawn_time = Timer() + 20;
while (!failed && !finished) {
    EnemyMaintenanceTick();

    if (LivingPlayers() == 0) {
        TriggerFail("All marines down.");
        terminate;
    }

    if (Timer() >= next_enemy_spawn_time) {
        if (ActiveEnemies() < ENEMY_CAP) {
            SpawnEnemies(1);
        }
        next_enemy_spawn_time = Timer() + ENEMY_SPAWN_INTERVAL + Random(0, ENEMY_SPAWN_INTERVAL);
    }

    Delay(6);
}
""",
            number=1,
        )

        acs.add_script(
            ScriptType.OPEN,
            """
Delay(20);
next_civ_spawn_time = Timer() + 15;

while (!failed && !finished) {
    CivilianBehaviorTick();

    if (Timer() >= next_civ_spawn_time) {
        if (ActiveCivilians() < CIV_CAP) {
            SpawnCivilians(1);
        }
        next_civ_spawn_time = Timer() + CIV_SPAWN_INTERVAL + Random(0, CIV_SPAWN_INTERVAL);
    }

    Delay(8);
}
""",
            number=2,
        )

        acs.add_script(
            ScriptType.VOID,
            """
TriggerFail("Mission failed: civilian collateral.");
""",
            number=951,
        )

        acs.add_script(
            ScriptType.VOID,
            """
civilians_killed_total++;
g_civ_kia = civilians_killed_total;
TriggerFail("Mission failed: civilian collateral.");
""",
            number=952,
        )

        acs.add_script(
            ScriptType.VOID,
            """
civilians_killed_total++;
civilians_killed_with_enemies++;
g_civ_kia = civilians_killed_total;
g_civ_kia_e = civilians_killed_with_enemies;
""",
            number=953,
        )

        acs.add_script(
            ScriptType.VOID,
            """
// no-op (legacy hook kept for backward compatibility)
""",
            number=954,
        )

        builder.map_data.scripts = acs.to_code()

        try:
            builder.map_data.behavior = acs.compile()
        except Exception as exc:
            print(f"ACS compile warning: {exc}")
            if hasattr(exc, "stderr") and exc.stderr:
                print(f"ACC stderr: {exc.stderr}")
            builder.map_data.behavior = b"ACSE\x08\x00\x00\x00\x00\x00\x00\x00"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        builder.build(output_path)

    def _pick_safe_points(
        self,
        builder: ProceduralMapBuilder,
        area_name: str,
        count: int,
        min_dist: float,
        attempts: int,
    ) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        tries = 0
        while len(points) < count and tries < attempts:
            tries += 1
            point = builder.get_random_point_in_area(area_name, safe=True)
            if point is None:
                continue

            px, py = point
            if all((px - ox) ** 2 + (py - oy) ** 2 >= min_dist * min_dist for ox, oy in points):
                points.append(point)

        return points

    def _place_map_spots(
        self,
        builder: ProceduralMapBuilder,
        base_tid: int,
        count: int,
        area_cycle: List[str],
        rng: random.Random,
        avoid_points: Optional[List[Tuple[float, float]]] = None,
        min_distance: float = 0.0,
    ) -> int:
        placed = 0
        attempts = 0
        max_attempts = max(count * 20, 100)

        while placed < count and attempts < max_attempts:
            attempts += 1
            area_name = area_cycle[(placed + attempts) % len(area_cycle)]
            safe_first = attempts % 3 != 0
            point = builder.get_random_point_in_area(area_name, safe=safe_first)
            if point is None:
                area_name = rng.choice(area_cycle)
                point = builder.get_random_point_in_area(area_name, safe=False)
            if point is None:
                continue

            if avoid_points:
                px, py = point
                too_close = False
                for ox, oy in avoid_points:
                    if (px - ox) ** 2 + (py - oy) ** 2 < (min_distance * min_distance):
                        too_close = True
                        break
                if too_close:
                    continue

            x, y = point
            builder.add_thing(ThingType.MAP_SPOT, x, y, tid=base_tid + placed, angle=rng.randint(0, 359))
            placed += 1

        return placed

    def _place_supply_in_cover(self, builder: ProceduralMapBuilder, rng: random.Random) -> None:
        supply_plan = [
            ("WestReadyRoom", ThingType.BOX_OF_SHELLS, 2),
            ("WestReadyRoom", ThingType.ENERGY_CELL_PACK, 1),
            ("EastReadyRoom", ThingType.BOX_OF_SHELLS, 1),
            ("EastReadyRoom", ThingType.ENERGY_CELL_PACK, 2),
            ("BreachHall", ThingType.CELL, 3),
            ("SpineB", ThingType.SHELLS, 2),
            ("SpineC", ThingType.SHELLS, 2),
            ("SpineA", ThingType.MEDIKIT, 1),
            ("WestObservation", ThingType.STIMPACK, 1),
            ("EastObservation", ThingType.STIMPACK, 1),
            ("Breach", ThingType.ARMOR_BONUS, 3),
        ]

        for area_name, thing_type, count in supply_plan:
            for _ in range(count):
                pt = builder.get_random_point_in_area(area_name, safe=True)
                if pt is None:
                    pt = builder.get_random_point_in_area(area_name, safe=False)
                if pt is None:
                    continue
                builder.add_thing(thing_type, pt[0], pt[1], angle=rng.randint(0, 359))

    def _add_center_room_cover(self, builder: ProceduralMapBuilder) -> None:
        room_specs = {
            "WestReadyRoom": [("hard", 56, 56), ("waist", 92, 48)],
            "EastReadyRoom": [("hard", 56, 56), ("waist", 92, 48)],
            "BreachHall": [("hard", 76, 76), ("waist", 108, 50)],
        }

        cover_idx = 0
        for area_name, shapes in room_specs.items():
            center = builder.get_area_centroid(area_name)
            if center is None:
                continue
            cx, cy = center

            for cover_kind, w, h in shapes:
                if cover_kind == "hard":
                    floor_h, ceil_h = 136, 136
                    ox, oy = 0.0, 0.0
                elif cover_kind == "waist":
                    floor_h, ceil_h = 40, 180
                    ox, oy = float(w), 0.0
                else:
                    floor_h, ceil_h = 16, 180
                    ox, oy = float(-w), 0.0

                builder.add_area(
                    f"CenterCover_{cover_idx}",
                    shape=(cx + ox, cy + oy, w, h),
                    mode="overwrite",
                    floor_height=floor_h,
                    ceiling_height=ceil_h,
                    wall_texture="BIGBRIK1",
                )
                cover_idx += 1


if __name__ == "__main__":
    output = "examples/benchmark/output/coop_cqb.wad"
    scenario = CoopCQBScenario(config={"seed": random.randint(0, 999999)})
    scenario.generate(output)
