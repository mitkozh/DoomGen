import os
import random
from typing import Any, Dict

from doomgen.batch.scenario import Scenario
from doomgen.builder import ProceduralMapBuilder
from doomgen.doom.things import ThingType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType


class UncommonHarvestScenario(Scenario):

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "seed": None,
            "field_size": 1200,
            "cleanup_size": 384,
            "cleanup_distance": 1000,
            "corridor_width": 3,
            "num_agents": 2,
            "initial_spawn_rate": 80,
            "harvest_degrade": 1,
            "natural_decay_rate": 1,
            "cleanup_boost": 15,
            "cleanup_time": 70,
            "hp_drain": 2,
            "spots_per_room": 16,
        }

    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)
        random.seed(seed)

        field_size       = cfg["field_size"]
        cleanup_size     = cfg["cleanup_size"]
        cleanup_distance = cfg["cleanup_distance"]
        corridor_w       = cfg["corridor_width"]
        total_spots      = cfg["spots_per_room"]
        initial_sr       = cfg["initial_spawn_rate"]
        harvest_deg      = cfg["harvest_degrade"]
        decay_rate       = cfg["natural_decay_rate"]
        cleanup_boost    = cfg["cleanup_boost"]
        cleanup_time     = cfg["cleanup_time"]
        hp_drain         = cfg["hp_drain"]

        cleanup_half = cleanup_size // 2

        # Cleanup zone bounds
        cz_cx = 0
        cz_cy = -cleanup_distance
        cz_xmin = cz_cx - cleanup_half
        cz_xmax = cz_cx + cleanup_half
        cz_ymin = cz_cy - cleanup_half
        cz_ymax = cz_cy + cleanup_half

        far_edge = max(field_size // 2, cleanup_distance + cleanup_size // 2)
        pad      = 400
        bounds   = (-(far_edge + pad), -(far_edge + pad),
                      far_edge + pad,    far_edge + pad)

        builder = ProceduralMapBuilder(bounds=bounds, num_seeds=8000, seed=seed)

        decorate_str = """
ACTOR ForageBonus : CustomInventory 15040 {
  +AUTOACTIVATE
  Inventory.MaxAmount 0
  States {
  Spawn:
    BON1 ABCDCB 6
    Loop
  Pickup:
    TNT1 A 0 ACS_ExecuteAlways(997, 0)
    Stop
  }
}
"""
        builder.wad_writer.add_lump("DECORATE", decorate_str.encode("utf-8"))

        acs = ACSBuilder()
        acs.add_include("zcommon.acs")
        acs.add_global_var("fc_spawn_rate",     51, "int")
        acs.add_global_var("fc_total_harvest",  52, "int")
        acs.add_global_var("fc_total_cleanups", 53, "int")
        acs.add_global_var("fc_p1_health",      54, "int")
        acs.add_global_var("fc_p2_health",      55, "int")

        # Harvest Field — large open area
        builder.add_area(
            "Harvest Field",
            shape=(0, 0, field_size, field_size),
            floor_height=0,
            ceiling_height=256,
            floor_texture="CEIL5_2",
            ceiling_texture="CEIL3_5",
            wall_texture="BROWN96",
            light_level=180,
        )

        # Cleanup Station — south of field
        builder.add_area(
            "Cleanup Station",
            shape=(cz_cx, cz_cy, cleanup_size, cleanup_size),
            floor_height=0,
            ceiling_height=256,
            floor_texture="NUKAGE1",
            ceiling_texture="TLITE6_4",
            wall_texture="PIPE4",
            light_level=255,
            tag=200,
        )

        # Corridor connecting field to cleanup
        builder.add_corridor(
            "Harvest Field", "Cleanup Station",
            width=corridor_w,
            floor_texture="CEIL5_2",
            ceiling_height=200,
            wall_texture="BROWN96",
            light_level=160,
        )

        # Player starts (field center)
        builder.add_thing(ThingType.PLAYER1_START, -48, 0, angle=0)
        builder.add_thing(ThingType.PLAYER2_START,  48, 0, angle=0)

        # MAP_SPOTs in Harvest Field (TIDs 3000+)
        spot_base = 3000
        placed_spots = 0
        for i in range(total_spots):
            pt = builder.get_random_point_in_area("Harvest Field", safe=False)
            if pt:
                builder.add_thing(
                    "MAP_SPOT", pt[0], pt[1],
                    tid=spot_base + i,
                )
                placed_spots += 1

        spot_start = 0
        spot_end = placed_spots - 1

        # Script 1 (ENTER): Player setup
        script_setup = """
        int pn;
        pn = PlayerNumber();
        Thing_ChangeTID(0, 1000 + pn);
        ClearInventory();
        ACS_ExecuteAlways(10, 0, 0, 0, 0);
        """
        acs.add_script(ScriptType.ENTER,   script_setup, number=1)
        acs.add_script(ScriptType.RESPAWN, script_setup, number=2)

        # Script 997 (VOID): Harvest callback — degrade spawn rate, give HP
        script_harvest = f"""
        fc_spawn_rate = fc_spawn_rate - {harvest_deg};
        if (fc_spawn_rate < 5) fc_spawn_rate = 5;
        fc_total_harvest = fc_total_harvest + 1;
        int hp;
        hp = GetActorProperty(0, APROP_Health);
        hp = hp + 2;
        if (hp > 200) hp = 200;
        SetActorProperty(0, APROP_Health, hp);
        """
        acs.add_script(ScriptType.VOID, script_harvest, number=997)

        # Script 3 (OPEN): Main spawn loop — spawn rate mechanic
        script_spawn = f"""
        fc_spawn_rate = {initial_sr};
        fc_total_harvest = 0;
        fc_total_cleanups = 0;
        int decay_tick;
        decay_tick = 0;

        Delay(35 * 3);

        int agents;
        int att;

        while (TRUE) {{
            agents = 0;
            if (PlayerInGame(0)) agents = agents + 1;
            if (PlayerInGame(1)) agents = agents + 1;
            if (PlayerInGame(2)) agents = agents + 1;
            if (PlayerInGame(3)) agents = agents + 1;

            for (att = 0; att < agents; att = att + 1) {{
                if (ThingCount(T_NONE, 800) < 48) {{
                    if (fc_spawn_rate > Random(0, 100)) {{
                        SpawnSpot("ForageBonus", {spot_base} + Random({spot_start}, {spot_end}), 800, 0);
                    }}
                }}
            }}

            decay_tick = decay_tick + 1;
            if (decay_tick >= 3) {{
                fc_spawn_rate = fc_spawn_rate - {decay_rate};
                if (fc_spawn_rate < 5) fc_spawn_rate = 5;
                decay_tick = 0;
            }}

            Delay(15);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_spawn, number=3)

        # Script 4 (OPEN): Cleanup detection — single station
        script_cleanup = f"""
        int c_p0;
        int c_p1;
        int px;
        int py;
        c_p0 = 0;
        c_p1 = 0;

        Delay(35);

        while (TRUE) {{
            if (PlayerInGame(0) && ThingCount(T_NONE, 1000) > 0) {{
                px = GetActorX(1000) >> 16;
                py = GetActorY(1000) >> 16;
                if (px >= {cz_xmin} && px <= {cz_xmax} && py >= {cz_ymin} && py <= {cz_ymax}) {{
                    c_p0 = c_p0 + 4;
                    if (c_p0 >= {cleanup_time}) {{
                        fc_spawn_rate = fc_spawn_rate + {cleanup_boost};
                        if (fc_spawn_rate > 100) fc_spawn_rate = 100;
                        fc_total_cleanups = fc_total_cleanups + 1;
                        c_p0 = 0;
                    }}
                }} else {{
                    c_p0 = 0;
                }}
            }}

            if (PlayerInGame(1) && ThingCount(T_NONE, 1001) > 0) {{
                px = GetActorX(1001) >> 16;
                py = GetActorY(1001) >> 16;
                if (px >= {cz_xmin} && px <= {cz_xmax} && py >= {cz_ymin} && py <= {cz_ymax}) {{
                    c_p1 = c_p1 + 4;
                    if (c_p1 >= {cleanup_time}) {{
                        fc_spawn_rate = fc_spawn_rate + {cleanup_boost};
                        if (fc_spawn_rate > 100) fc_spawn_rate = 100;
                        fc_total_cleanups = fc_total_cleanups + 1;
                        c_p1 = 0;
                    }}
                }} else {{
                    c_p1 = 0;
                }}
            }}

            fc_p1_health = GetActorProperty(1000, APROP_Health);
            fc_p2_health = GetActorProperty(1001, APROP_Health);

            Delay(4);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_cleanup, number=4)

        # Script 5 (OPEN): Health drain loop
        script_drain = f"""
        int hp;

        Delay(35 * 3);

        while (TRUE) {{
            if (PlayerInGame(0) && ThingCount(T_NONE, 1000) > 0) {{
                hp = GetActorProperty(1000, APROP_Health);
                hp = hp - {hp_drain};
                SetActorProperty(1000, APROP_Health, hp);
                if (hp <= 0) {{
                    Exit_Normal(0);
                }}
            }}
            if (PlayerInGame(1) && ThingCount(T_NONE, 1001) > 0) {{
                hp = GetActorProperty(1001, APROP_Health);
                hp = hp - {hp_drain};
                SetActorProperty(1001, APROP_Health, hp);
                if (hp <= 0) {{
                    Exit_Normal(0);
                }}
            }}

            Delay(35);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_drain, number=5)

        # Script 10 (VOID): Per-player HUD loop
        bar_cases = []
        for i in range(21):
            filled = "=" * i
            empty  = "-" * (20 - i)
            bar_cases.append(
                f'case {i}: bar_gfx = "\\cD{filled}\\cG{empty}"; break;'
            )
        bar_switch_str = "\n                ".join(bar_cases)

        script_hud = f"""
        int sr;
        int idx;
        str bar_gfx;
        str sr_color;

        while (TRUE) {{
            SetFont("SMALLFONT");

            sr = fc_spawn_rate;
            idx = sr / 5;
            if (idx < 0) idx = 0;
            if (idx > 20) idx = 20;
            bar_gfx = "";

            switch (idx) {{
                {bar_switch_str}
            }}

            sr_color = "\\cA";
            if (sr > 60) sr_color = "\\cD";
            else if (sr > 30) sr_color = "\\cF";

            HudMessage(s:"SPAWN RATE: ", s:bar_gfx, s:" ", s:sr_color, d:sr, s:"%";
                HUDMSG_PLAIN, 1, CR_WHITE, 0.5, 0.78, 2.0);
            HudMessage(s:"HARVEST: ", d:fc_total_harvest,
                s:"   CLEANUPS: ", d:fc_total_cleanups;
                HUDMSG_PLAIN, 2, CR_WHITE, 0.5, 0.82, 2.0);

            Delay(4);
        }}
        """
        acs.add_script(ScriptType.VOID, script_hud, number=10)

        try:
            builder.map_data.behavior = acs.compile()
        except Exception as e:
            print(f"ACS compile warning: {e}")
            if hasattr(e, "stderr") and e.stderr:
                print(f"ACC stderr: {e.stderr}")

        builder.build(output_path)


if __name__ == "__main__":
    out_dir = os.path.join("examples", "benchmark", "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "foraging_commons.wad")
    print(f"Generating {path}...")
    UncommonHarvestScenario().generate(path)
    print("Done.")
