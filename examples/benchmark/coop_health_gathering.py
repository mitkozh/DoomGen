import os
import random
import math
from shapely.geometry import Polygon
from typing import Any, Dict, List

from doomgen.batch.scenario import Scenario
from doomgen.builder import ProceduralMapBuilder
from doomgen.doom.things import ThingType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType

class CoopHealthGatheringScenario(Scenario):
    """
    Cooperative health gathering scenario.
    Players must navigate a toxic maze while chained together.
    Health items spawn randomly around the map.
    Game ends if any player dies.
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "seed": None,
            "max_players": 4,
            "map_radius": 2000,
            "chain_max_len": 400,
            "toxic_damage": 5,      
            "max_health_kits": 25,
            "maze_density": 0.6,
        }

    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = cfg.get("seed")
        if seed is None:
            seed = random.randint(0, 999999)
        random.seed(seed)

        max_players = int(cfg["max_players"])
        map_radius = int(cfg["map_radius"])
        chain_max_len = int(cfg["chain_max_len"])
        toxic_damage_amt = int(cfg["toxic_damage"])
        max_health_kits = int(cfg["max_health_kits"])
        maze_density = float(cfg["maze_density"])
        
        builder = ProceduralMapBuilder(
            bounds=(-map_radius, -map_radius, map_radius, map_radius),
            num_seeds=8000,
            seed=seed
        )

        floor_tag = 900
        
        num_points = random.randint(12, 24)
        base_points = []
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            r = random.uniform(map_radius * 0.6, map_radius)
            base_points.append((r * math.cos(angle), r * math.sin(angle)))
            
        base_shape = Polygon(base_points)
        
        builder.add_area(
            "BaseArena",
            shape=base_shape,
            floor_height=0,
            ceiling_height=384,
            floor_texture="NUKAGE1", 
            ceiling_texture="CEIL1_2",
            wall_texture="BRICK6",
            light_level=200,
            tag=floor_tag,
            mode="claim_void"
        )
        
        block_size = 140
        num_pillars = int(map_radius * map_radius * 4 / (block_size * block_size * 4) * maze_density)

        block_idx = 0
        for _ in range(num_pillars):
            pt = builder.get_random_point_in_area("BaseArena", safe=True)
            if not pt:
                continue

            if abs(pt[0]) < 256 and abs(pt[1]) < 256:
                continue

            w = random.randint(48, 128)
            h = random.randint(48, 128)
            x, y = pt

            builder.add_area(
                f"Pillar_{block_idx}",
                shape=(x, y, w, h),
                floor_height=0,
                ceiling_height=0, 
                floor_texture="NUKAGE1",
                wall_texture="ASHWALL6",
                light_level=200,
                mode="overwrite"
            )
            block_idx += 1
                        
        spawn_center = builder.get_random_point_in_area("BaseArena", safe=True)
        if not spawn_center:
            spawn_center = (0, 0)
        
        spawn_points = []
        for _ in range(100):
            if len(spawn_points) >= max_players:
                break
                
            pt = builder.get_random_point_in_area("BaseArena", safe=True)
            if not pt:
                continue
                
            dist_sq = (pt[0] - spawn_center[0])**2 + (pt[1] - spawn_center[1])**2
            if dist_sq < (chain_max_len / 2)**2:
                too_close = False
                for sp in spawn_points:
                    if (pt[0] - sp[0])**2 + (pt[1] - sp[1])**2 < 64**2:
                        too_close = True
                        break
                if not too_close:
                    spawn_points.append(pt)
                    
        while len(spawn_points) < max_players:
            spawn_points.append((spawn_center[0] + random.randint(-64, 64), 
                                 spawn_center[1] + random.randint(-64, 64)))
            
        player_types = [
            ThingType.PLAYER1_START, 
            ThingType.PLAYER2_START, 
            ThingType.PLAYER3_START, 
            ThingType.PLAYER4_START
        ]
        
        for i in range(max_players):
            if i < len(player_types):
                builder.add_thing(player_types[i], spawn_points[i][0], spawn_points[i][1], angle=random.randint(0, 359))
        
        num_spawn_spots = 200
        spot_tid_base = 3000
        
        for i in range(num_spawn_spots):
            pt = builder.get_random_point_in_area("BaseArena", safe=True)
            if pt:
                builder.add_thing("MAP_SPOT", pt[0], pt[1], z=0, tid=spot_tid_base + i)
        
        acs = ACSBuilder()
        acs.add_include("zcommon.acs")
        
        acs.add_global_var("chg_active_health_kits_global", 1, "int")
        acs.add_global_var("chg_total_spawned_kits_global", 2, "int")
        acs.add_global_var("chg_chain_stretches_global", 3, "int")
        
        script_setup = f"""
        int pn = PlayerNumber();
        if (pn >= 0 && pn < {max_players}) {{
            Thing_ChangeTID(0, 1000 + pn);
            SetActorProperty(0, APROP_Health, 100);
            TakeInventory("Fist", 999);
        }}
        """
        acs.add_script(ScriptType.ENTER, script_setup, number=1)
        acs.add_script(ScriptType.RESPAWN, script_setup, number=2)
        
        chain_lines: List[str] = []
        for follower in range(1, max_players):
            leader = follower - 1
            chain_lines.append(
                f"""
                if (PlayerInGame({leader}) && PlayerInGame({follower})) {{
                    int a_tid_{follower} = {1000 + leader};
                    int b_tid_{follower} = {1000 + follower};
                    if (ThingCount(0, a_tid_{follower}) > 0 && ThingCount(0, b_tid_{follower}) > 0) {{
                        int ax_{follower} = GetActorX(a_tid_{follower});
                        int ay_{follower} = GetActorY(a_tid_{follower});
                        int bx_{follower} = GetActorX(b_tid_{follower});
                        int by_{follower} = GetActorY(b_tid_{follower});

                        int dx_{follower} = ax_{follower} - bx_{follower};
                        int dy_{follower} = ay_{follower} - by_{follower};
                        int adx_{follower} = dx_{follower};
                        int ady_{follower} = dy_{follower};

                        if (adx_{follower} < 0) adx_{follower} = -adx_{follower};
                        if (ady_{follower} < 0) ady_{follower} = -ady_{follower};

                        int dist_{follower};
                        if (adx_{follower} > ady_{follower}) {{
                            dist_{follower} = adx_{follower} + (ady_{follower} >> 1);
                        }} else {{
                            dist_{follower} = ady_{follower} + (adx_{follower} >> 1);
                        }}

                        int chain_limit_{follower} = {chain_max_len} << 16;
                        if (dist_{follower} > chain_limit_{follower} && dist_{follower} > 0) {{
                            int keep_half_{follower} = ({max(64, chain_max_len - 24)} << 15);
                            int ratio_{follower} = FixedDiv(keep_half_{follower}, dist_{follower});

                            int mx_{follower} = (ax_{follower} + bx_{follower}) >> 1;
                            int my_{follower} = (ay_{follower} + by_{follower}) >> 1;
                            int nax_{follower} = mx_{follower} + FixedMul(dx_{follower}, ratio_{follower});
                            int nay_{follower} = my_{follower} + FixedMul(dy_{follower}, ratio_{follower});
                            int nbx_{follower} = mx_{follower} - FixedMul(dx_{follower}, ratio_{follower});
                            int nby_{follower} = my_{follower} - FixedMul(dy_{follower}, ratio_{follower});

                            SetActorPosition(a_tid_{follower}, nax_{follower}, nay_{follower}, GetActorZ(a_tid_{follower}), 0);
                            SetActorPosition(b_tid_{follower}, nbx_{follower}, nby_{follower}, GetActorZ(b_tid_{follower}), 0);
                            
                            // Increment chain stretch count
                            chg_chain_stretches_global++;
                        }}
                    }}
                }}
                """
            )
            
        chain_block = "".join(chain_lines)
        
        script_main = f"""
        Sector_SetDamage({floor_tag}, {toxic_damage_amt}, 14); 
        
        int tick = 0;
        int active_health_kits = 0;
        int health_kit_tid = 800;
        
        chg_active_health_kits_global = 0;
        chg_total_spawned_kits_global = 0;
        chg_chain_stretches_global = 0;
        
        while (TRUE) {{
            {chain_block}
            
            active_health_kits = ThingCount(T_NONE, health_kit_tid);
            chg_active_health_kits_global = active_health_kits;
            
            if (tick % 35 == 0) {{
                if (active_health_kits < {max_health_kits}) {{
                    int spawns = 0;
                    for (spawns = 0; spawns < 3; spawns++) {{
                        if (active_health_kits + spawns >= {max_health_kits}) break;
                        
                        int r_spot = Random(0, {num_spawn_spots - 1});
                        int target_spot_tid = {spot_tid_base} + r_spot;
                        
                        str type = "Stimpack";
                        if (Random(0, 3) == 0) type = "Medikit"; 
                        
                        SpawnSpot(type, target_spot_tid, health_kit_tid, 0);
                        chg_total_spawned_kits_global++;
                    }}
                    chg_active_health_kits_global = ThingCount(T_NONE, health_kit_tid);
                }}
            }}
            
            tick++;
            Delay(1);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_main, number=3)
        
        acs.add_script(
            ScriptType.DEATH,
            """
            Delay(1);
            Exit_Normal(0);
            """,
            number=4
        )
        
        source_acs = acs.to_code()
        builder.map_data.scripts = source_acs
        try:
            builder.map_data.behavior = acs.compile()
        except Exception as e:
            print(f"ACS Compile Warning: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"ACC Stderr: {e.stderr}")
                
        builder.build(output_path)
        
if __name__ == "__main__":
    out_dir = os.path.join("examples", "benchmark", "output")
    os.makedirs(out_dir, exist_ok=True)
    
    path = os.path.join(out_dir, "coop_health_gathering.wad")
    print(f"Generating {path}...")
    
    scen = CoopHealthGatheringScenario()
    scen.generate(path)
    print("Done.")