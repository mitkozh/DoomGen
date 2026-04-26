import os
import random
from typing import Any, Dict, List, Tuple

from doomgen.batch.scenario import Scenario
from doomgen.builder import ProceduralMapBuilder
from doomgen.doom.things import ThingType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType


class StealthLabyrinthScenario(Scenario):
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "seed": 42,
            "hub_size": 448,
            "room_size": 384,
            "corridor_width": 4,
            "num_relays": 3,
            "relay_hold_tics": 36,
            "extract_hold_tics": 44,
            "guards_per_relay": 2,
        }

    @staticmethod
    def _square_check(px: str, py: str, cx: int, cy: int, radius: int) -> str:
        return (
            f"{px} >= {cx - radius} && {px} <= {cx + radius} && "
            f"{py} >= {cy - radius} && {py} <= {cy + radius}"
        )

    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)
        random.seed(seed)
        print(f"seed: {seed}")

        hub_size = int(cfg["hub_size"])
        room_size = cfg["room_size"]
        corridor_width = int(cfg["corridor_width"])
        num_relays = int(cfg["num_relays"])
        relay_hold_tics = int(cfg["relay_hold_tics"])
        extract_hold_tics = int(cfg["extract_hold_tics"])
        guards_per_relay = int(cfg["guards_per_relay"])

        room_gap = room_size + 288
        relay_gap = room_gap * 2
        bounds_half = relay_gap + room_size + 800
        builder = ProceduralMapBuilder(
            bounds=(-bounds_half, -bounds_half, bounds_half, bounds_half),
            num_seeds=18000,
            seed=seed,
        )

        decorate_str = """
ACTOR ShadowGuard : DoomImp 14001 {
  Health 40
  DropItem "None"
  States {
  Death:
    TROO H 8
    TROO I 8 A_Scream
    TROO J 6
    TROO K 6 A_NoBlocking
    TROO K 0 ACS_ExecuteAlways(998, 0)
    TROO L 4
    TROO M 1 A_FadeOut(0.10)
    Wait
  }
}
"""
        builder.wad_writer.add_lump("DECORATE", decorate_str.encode("utf-8"))

        room_specs: List[Tuple[str, Tuple[int, int], int, str, str, str]] = [
            ("Hub", (0, 0), 100, "FLOOR4_8", "CEIL3_5", "STONE2"),
            ("North Approach", (0, room_gap), 101, "FLOOR4_8", "CEIL3_5", "METAL1"),
            ("North Relay", (0, relay_gap), 102, "FLOOR5_2", "TLITE6_6", "STONE3"),
            ("West Approach", (-room_gap, 0), 103, "FLOOR4_8", "CEIL3_5", "METAL1"),
            ("West Relay", (-relay_gap, 0), 104, "FLOOR5_2", "TLITE6_6", "STONE3"),
            ("East Approach", (room_gap, 0), 105, "FLOOR4_8", "CEIL3_5", "METAL1"),
            ("East Relay", (relay_gap, 0), 106, "FLOOR5_2", "TLITE6_6", "STONE3"),
            ("Extraction Hall", (0, -room_gap), 107, "FLOOR4_8", "CEIL3_5", "COMPBLUE"),
            ("Extraction Chamber", (0, -relay_gap), 108, "FLOOR0_1", "TLITE6_5", "COMPBLUE"),
        ]

        area_centers: Dict[str, Tuple[int, int]] = {}
        room_tags: Dict[str, int] = {}
        for name, (cx, cy), tag, floor_tex, ceil_tex, wall_tex in room_specs:
            area_centers[name] = (cx, cy)
            room_tags[name] = tag
            is_hub = name == "Hub"
            builder.add_area(
                name=name,
                shape=(cx, cy, hub_size if is_hub else room_size, hub_size if is_hub else room_size),
                floor_height=0,
                ceiling_height=192,
                floor_texture=floor_tex,
                ceiling_texture=ceil_tex,
                wall_texture=wall_tex,
                light_level=0,
                tag=tag,
            )

        corridor_specs = [
            ("Hub", "North Approach", 200),
            ("North Approach", "North Relay", 201),
            ("Hub", "West Approach", 202),
            ("West Approach", "West Relay", 203),
            ("Hub", "East Approach", 204),
            ("East Approach", "East Relay", 205),
            ("Hub", "Extraction Hall", 206),
            ("Extraction Hall", "Extraction Chamber", 207),
        ]
        corridor_centers: List[Tuple[int, int, int]] = []
        for room_a, room_b, tag in corridor_specs:
            corridor_name = builder.add_corridor(
                room_a,
                room_b,
                width=corridor_width,
                floor_texture="FLOOR4_8",
                ceiling_height=192,
                wall_texture="METAL1",
                light_level=0,
            )
            builder.graph.get_area(corridor_name).config.tag = tag

            ax, ay = area_centers[room_a]
            bx, by = area_centers[room_b]
            corridor_centers.append((tag, (ax + bx) // 2, (ay + by) // 2))

        builder.add_thing(ThingType.PLAYER1_START, -40, -48, angle=90)
        builder.add_thing(ThingType.PLAYER2_START, 40, -48, angle=90)
        builder.add_thing(ThingType.PLAYER3_START, -40, 32, angle=90)
        builder.add_thing(ThingType.PLAYER4_START, 40, 32, angle=90)

        relay_names = ["North Relay", "West Relay", "East Relay"][:num_relays]
        relay_specs: List[Dict[str, Any]] = []
        for relay_idx, relay_name in enumerate(relay_names):
            cx, cy = area_centers[relay_name]
            approach_name = relay_name.replace("Relay", "Approach")
            relay_specs.append(
                {
                    "name": relay_name,
                    "approach": approach_name,
                    "room_tag": room_tags[relay_name],
                    "center": (cx, cy),
                }
            )

        extraction_center = area_centers["Extraction Chamber"]
        extraction_pad = (extraction_center[0], extraction_center[1] - 96)

        for relay in relay_specs:
            cx, cy = relay["center"]
            builder.add_thing(ThingType.TECH_LAMP2, cx - 96, cy)
            builder.add_thing(ThingType.TECH_LAMP2, cx + 96, cy)
            builder.add_thing(ThingType.BOX_OF_SHELLS, cx, cy - 80)
            builder.add_thing(ThingType.MEDIKIT, cx, cy + 80)
            builder.add_thing(ThingType.FLOOR_LAMP, cx, cy + 120)

            for _ in range(max(1, guards_per_relay - 1)):
                pt = builder.get_random_point_in_area(relay["name"], safe=False)
                if pt is not None:
                    builder.add_thing(14001, pt[0], pt[1])

            pt = builder.get_random_point_in_area(relay["approach"], safe=False)
            if pt is not None:
                builder.add_thing(14001, pt[0], pt[1])

        builder.add_thing(ThingType.TECH_LAMP, extraction_center[0] - 96, extraction_center[1] + 24)
        builder.add_thing(ThingType.TECH_LAMP, extraction_center[0] + 96, extraction_center[1] + 24)
        builder.add_thing(ThingType.TALL_RED_PILLAR, extraction_pad[0], extraction_pad[1])

        acs = ACSBuilder()
        acs.add_include("zcommon.acs")
        acs.add_global_var("sl_relay_done_0", 1, "int")
        acs.add_global_var("sl_relay_done_1", 2, "int")
        acs.add_global_var("sl_relay_done_2", 3, "int")
        acs.add_global_var("sl_relay_progress_0", 4, "int")
        acs.add_global_var("sl_relay_progress_1", 5, "int")
        acs.add_global_var("sl_relay_progress_2", 6, "int")
        acs.add_global_var("sl_extract_progress", 7, "int")
        acs.add_global_var("sl_extract_progress_user", 8, "int")
        acs.add_global_var("sl_team_kills", 9, "int")
        acs.add_global_var("sl_unused_10", 10, "int")

        acs.add_global_var("sl_p1_alive", 41, "int")
        acs.add_global_var("sl_p2_alive", 42, "int")
        acs.add_global_var("sl_distance", 43, "int")
        acs.add_global_var("sl_relays_done", 44, "int")
        acs.add_global_var("sl_active_objective", 45, "int")
        acs.add_global_var("sl_objective_progress", 46, "int")
        acs.add_global_var("sl_extraction_unlocked", 47, "int")
        acs.add_global_var("sl_sync_state", 48, "int")
        acs.add_global_var("sl_extract_progress_flag", 49, "int")

        script_enter = """
        int pn = PlayerNumber();
        Thing_ChangeTID(0, 1000 + pn);
        SetActorProperty(0, APROP_Health, 100);
        ClearInventory();
        if (pn == 1) {
            GiveInventory("Shotgun", 1);
            GiveInventory("Shell", 40);
            SetWeapon("Shotgun");
        }
        ACS_ExecuteAlways(10, 0, 0, 0, 0);
        """
        acs.add_script(ScriptType.ENTER, script_enter, number=1)

        room_light_checks: List[str] = []
        room_bright_dist = room_size // 2 + 64
        hub_bright_dist = hub_size // 2 + 64
        for name, (cx, cy), tag, _, _, _ in room_specs:
            bright_dist = hub_bright_dist if name == "Hub" else room_bright_dist
            room_light_checks.append(
                f"""
            dx = p1x - {cx};
            if (dx < 0) dx = -dx;
            dy = p1y - {cy};
            if (dy < 0) dy = -dy;
            dist = dx;
            if (dy > dist) dist = dy;
            if (dist < {bright_dist}) {{
                Light_ChangeToValue({tag}, 208);
            }} else {{
                Light_ChangeToValue({tag}, 0);
            }}"""
            )

        corridor_light_checks: List[str] = []
        for corr_tag, cx, cy in corridor_centers:
            corridor_light_checks.append(
                f"""
            dx = p1x - {cx};
            if (dx < 0) dx = -dx;
            dy = p1y - {cy};
            if (dy < 0) dy = -dy;
            dist = dx;
            if (dy > dist) dist = dy;
            if (dist < 300) {{
                Light_ChangeToValue({corr_tag}, 192);
            }} else {{
                Light_ChangeToValue({corr_tag}, 0);
            }}"""
            )

        script_light = f"""
        int p1x;
        int p1y;
        int dx;
        int dy;
        int dist;

        while (TRUE) {{
            if (ThingCount(T_NONE, 1000) > 0) {{
                p1x = GetActorX(1000) >> 16;
                p1y = GetActorY(1000) >> 16;
{"".join(room_light_checks)}
{"".join(corridor_light_checks)}
            }}
            Delay(4);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_light, number=3)

        relay_blocks: List[str] = []
        for relay_idx, relay in enumerate(relay_specs):
            room_check_p1 = self._square_check("px1", "py1", relay["center"][0], relay["center"][1], room_size // 2 - 12)
            room_check_p2 = self._square_check("px2", "py2", relay["center"][0], relay["center"][1], room_size // 2 - 12)
            relay_blocks.append(
                f"""
                if (sl_relay_done_{relay_idx} == 0) {{
                    if ({room_check_p1} && {room_check_p2}) {{
                        sl_sync_state = 1;
                        sl_active_objective = {relay_idx};
                        sl_relay_progress_{relay_idx}++;
                        sl_objective_progress = sl_relay_progress_{relay_idx};
                        if (sl_relay_progress_{relay_idx} >= {relay_hold_tics}) {{
                            sl_relay_done_{relay_idx} = 1;
                            sl_relay_progress_{relay_idx} = 0;
                            sl_relays_done++;
                            Light_ChangeToValue({relay["room_tag"]}, 255);
                        }}
                    }} else {{
                        sl_relay_progress_{relay_idx} = 0;
                    }}
                }}"""
            )

        extract_room_check_p1 = self._square_check("px1", "py1", extraction_center[0], extraction_center[1], room_size // 2 - 12)
        extract_room_check_p2 = self._square_check("px2", "py2", extraction_center[0], extraction_center[1], room_size // 2 - 12)

        script_logic = f"""
        int px1;
        int py1;
        int px2;
        int py2;
        int adx;
        int ady;

        while (TRUE) {{
            sl_p1_alive = ThingCount(T_NONE, 1000) > 0;
            sl_p2_alive = ThingCount(T_NONE, 1001) > 0;
            sl_extract_progress_flag = sl_extract_progress;
            sl_active_objective = -1;
            sl_objective_progress = 0;
            sl_sync_state = 0;
            sl_extraction_unlocked = sl_relays_done >= {num_relays};
            sl_distance = 0;
            if (sl_p1_alive && sl_p2_alive) {{
                px1 = GetActorX(1000) >> 16;
                py1 = GetActorY(1000) >> 16;
                px2 = GetActorX(1001) >> 16;
                py2 = GetActorY(1001) >> 16;
                adx = px1 - px2;
                if (adx < 0) adx = -adx;
                ady = py1 - py2;
                if (ady < 0) ady = -ady;
                sl_distance = adx + ady;

{"".join(relay_blocks)}

                if (sl_relays_done >= {num_relays}) {{
                    if ({extract_room_check_p1} && {extract_room_check_p2}) {{
                        sl_sync_state = 1;
                        sl_active_objective = {num_relays};
                        sl_extract_progress++;
                        sl_extract_progress_user = sl_extract_progress;
                        sl_objective_progress = sl_extract_progress;
                        if (sl_extract_progress >= {extract_hold_tics}) {{
                            Delay(1);
                            Exit_Normal(0);
                        }}
                    }} else {{
                        sl_extract_progress = 0;
                        sl_extract_progress_user = 0;
                    }}
                }}
            }} else {{
                sl_extract_progress = 0;
                sl_extract_progress_user = 0;
                sl_relay_progress_0 = 0;
                sl_relay_progress_1 = 0;
                sl_relay_progress_2 = 0;
            }}

            Delay(4);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_logic, number=4)

        acs.add_script(ScriptType.DEATH, """
        Delay(1);
        Exit_Normal(0);
        """, number=8)

        acs.add_script(ScriptType.VOID, """
        sl_team_kills++;
        """, number=998)

        top_bar_cases = []
        for i in range(21):
            filled = "=" * i
            empty = "-" * (20 - i)
            top_bar_cases.append(
                f'case {i}: top_bar_gfx = "\\cD{filled}\\cG{empty}"; break;'
            )
        top_bar_switch = "\n                ".join(top_bar_cases)

        bottom_bar_cases = []
        for i in range(21):
            filled = "=" * i
            empty = "-" * (20 - i)
            bottom_bar_cases.append(
                f'case {i}: bottom_bar_gfx = "\\cB{filled}\\cG{empty}"; break;'
            )
        bottom_bar_switch = "\n                ".join(bottom_bar_cases)

        script_hud = f"""
        int top_idx;
        int bottom_idx;
        int p;
        str top_bar_gfx;
        str bottom_bar_gfx;

        while (TRUE) {{
            SetHudSize(320, 240, 1);
            SetFont("SMALLFONT");

            top_idx = sl_relays_done * 20 / {num_relays};
            if (top_idx < 0) top_idx = 0;
            if (top_idx > 20) top_idx = 20;

            p = sl_objective_progress;
            if (sl_extraction_unlocked) {{
                bottom_idx = p * 20 / {extract_hold_tics};
            }} else {{
                bottom_idx = p * 20 / {relay_hold_tics};
            }}
            if (bottom_idx < 0) bottom_idx = 0;
            if (bottom_idx > 20) bottom_idx = 20;

            top_bar_gfx = "";
            bottom_bar_gfx = "";

            switch (top_idx) {{
                {top_bar_switch}
            }}
            switch (bottom_idx) {{
                {bottom_bar_switch}
            }}

            HudMessage(s:top_bar_gfx; HUDMSG_PLAIN, 1, CR_WHITE, 160.0, 6.0, 0.0);
            HudMessage(s:bottom_bar_gfx; HUDMSG_PLAIN, 2, CR_WHITE, 160.0, 200.0, 0.0);
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
    path = os.path.join(out_dir, "stealth_labyrinth.wad")
    print(f"Generating {path}...")
    StealthLabyrinthScenario().generate(path)
    print("Done.")
