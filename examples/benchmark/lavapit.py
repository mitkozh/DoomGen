import os
import random
import math
from typing import Any, Dict, List, Tuple

from doomgen.abstraction.layout import ConnectionType
from doomgen.batch.scenario import Scenario
from doomgen.builder import ProceduralMapBuilder
from doomgen.logic.acs_builder import ACSBuilder, ScriptType


class LavaPitScenario(Scenario):
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "seed": None,
            "random_seed_on_generate": True,
            "num_platforms": 5,
            "max_players": 4,
            "platform_width_min": 236,
            "platform_width_max": 320,
            "platform_depth_min": 164,
            "platform_depth_max": 232,
            "gap_min": 280,
            "gap_max": 420,
            "lane_jitter": 86,
            "lane_span": 560,
            "curve_amplitude": 420,
            "curve_waves": 2,
            "platform_floor_height": 0,
            "lava_height": -80,
            "lava_damage": 100,
            "poll_tics": 4,
            "runtime_jitter_tics": 2,
            "seeds_per_platform": 1000,
        }

    def validate_config(self) -> None:
        platforms = int(self.config["num_platforms"])
        if platforms < 3 or platforms > 200:
            raise ValueError("num_platforms must be in range [3, 200]")

        max_players = int(self.config["max_players"])
        if max_players < 1 or max_players > 4:
            raise ValueError("max_players must be in range [1, 4]")

        if int(self.config["platform_width_min"]) < 96:
            raise ValueError("platform_width_min must be >= 96")
        if int(self.config["platform_width_max"]) < int(self.config["platform_width_min"]):
            raise ValueError("platform_width_max must be >= platform_width_min")

        if int(self.config["platform_depth_min"]) < 96:
            raise ValueError("platform_depth_min must be >= 96")
        if int(self.config["platform_depth_max"]) < int(self.config["platform_depth_min"]):
            raise ValueError("platform_depth_max must be >= platform_depth_min")

        if int(self.config["gap_min"]) < 112:
            raise ValueError("gap_min must be >= 112")
        if int(self.config["gap_max"]) < int(self.config["gap_min"]):
            raise ValueError("gap_max must be >= gap_min")

        if int(self.config["curve_amplitude"]) < 0:
            raise ValueError("curve_amplitude must be >= 0")
        if int(self.config["curve_waves"]) < 1:
            raise ValueError("curve_waves must be >= 1")
        if int(self.config["poll_tics"]) < 1:
            raise ValueError("poll_tics must be >= 1")
        if int(self.config["runtime_jitter_tics"]) < 0:
            raise ValueError("runtime_jitter_tics must be >= 0")
        if int(self.config["seeds_per_platform"]) < 300:
            raise ValueError("seeds_per_platform must be >= 300")

    def _choose_seed(self) -> int:
        cfg = self.config
        if cfg["seed"] is not None:
            return int(cfg["seed"])
        if bool(cfg.get("random_seed_on_generate", True)):
            return random.randint(0, 999999)
        return 42

    def _auto_connect_touching_areas(self, builder: ProceduralMapBuilder) -> None:
        touching_pairs: set[Tuple[str, str]] = set()
        for idx, neighbors in builder.mesh.adjacency.items():
            area_a = builder.seeds[idx].area_id
            if area_a == "VOID":
                continue
            for n_idx in neighbors:
                area_b = builder.seeds[n_idx].area_id
                if area_b == "VOID" or area_a == area_b:
                    continue
                pair = (area_a, area_b) if area_a < area_b else (area_b, area_a)
                touching_pairs.add(pair)

        existing_pairs: set[Tuple[str, str]] = set()
        for conn in builder.graph.connections:
            pair = (
                (conn.area_a_id, conn.area_b_id)
                if conn.area_a_id < conn.area_b_id
                else (conn.area_b_id, conn.area_a_id)
            )
            existing_pairs.add(pair)

        for area_a, area_b in touching_pairs:
            if (area_a, area_b) not in existing_pairs:
                builder.graph.connect(area_a, area_b, ConnectionType.OPEN)

    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = self._choose_seed()
        rng = random.Random(seed)

        num_platforms = int(cfg["num_platforms"])
        max_players = int(cfg["max_players"])
        platform_floor_height = int(cfg["platform_floor_height"])
        lava_height = int(cfg["lava_height"])
        lava_damage = int(cfg["lava_damage"])
        poll_tics = int(cfg["poll_tics"])
        runtime_jitter_tics = int(cfg["runtime_jitter_tics"])

        platform_width_min = int(cfg["platform_width_min"])
        platform_width_max = int(cfg["platform_width_max"])
        platform_depth_min = int(cfg["platform_depth_min"])
        platform_depth_max = int(cfg["platform_depth_max"])
        gap_min = int(cfg["gap_min"])
        gap_max = int(cfg["gap_max"])
        lane_jitter = int(cfg["lane_jitter"])
        lane_span = int(cfg["lane_span"])
        curve_amplitude = int(cfg["curve_amplitude"])
        curve_waves = int(cfg["curve_waves"])

        # Keep generated geometry inside classic Doom-safe coordinate budget
        # when num_platforms is large (e.g. 120+).
        safe_chain_span = 44000
        est_span = max(1, num_platforms) * (platform_width_max + gap_max)
        scale = min(1.0, safe_chain_span / est_span)

        # Preserve larger platform footprints while shrinking gaps more aggressively.
        size_scale = min(1.0, max(0.78, scale ** 0.55))
        gap_scale = min(1.0, max(0.28, scale ** 1.60))
        lane_scale = min(1.0, max(0.45, scale ** 1.10))

        eff_platform_width_min = max(128, int(round(platform_width_min * size_scale)))
        eff_platform_width_max = max(
            eff_platform_width_min, int(round(platform_width_max * size_scale))
        )
        eff_platform_depth_min = max(120, int(round(platform_depth_min * size_scale)))
        eff_platform_depth_max = max(
            eff_platform_depth_min, int(round(platform_depth_max * size_scale))
        )
        eff_gap_min = max(112, int(round(gap_min * gap_scale)))
        eff_gap_max = max(eff_gap_min, int(round(gap_max * gap_scale)))
        eff_lane_jitter = max(0, int(round(lane_jitter * lane_scale)))
        eff_lane_span = max(120, int(round(lane_span * lane_scale)))
        eff_curve_amplitude = max(0, int(round(curve_amplitude * lane_scale)))

        platform_specs: List[Dict[str, int]] = []
        gaps = [rng.randint(eff_gap_min, eff_gap_max) for _ in range(num_platforms - 1)]

        for i in range(num_platforms):
            width = rng.randint(eff_platform_width_min, eff_platform_width_max)
            depth = rng.randint(eff_platform_depth_min, eff_platform_depth_max)

            if i == 0:
                x = 0
                y = 0
            else:
                prev = platform_specs[i - 1]
                x = int(prev["x"] + (prev["width"] // 2) + gaps[i - 1] + (width // 2))
                t = i / max(1, num_platforms - 1)
                curve_offset = int(
                    math.sin(t * 2.0 * math.pi * curve_waves) * eff_curve_amplitude
                )
                random_walk_y = prev["y"] + rng.randint(-eff_lane_jitter, eff_lane_jitter)
                y = int((2 * random_walk_y + curve_offset) / 3)
                y = max(-eff_lane_span, min(eff_lane_span, y))

            platform_specs.append({"x": x, "y": y, "width": width, "depth": depth})

        min_x_raw = min(spec["x"] - spec["width"] // 2 for spec in platform_specs)
        max_x_raw = max(spec["x"] + spec["width"] // 2 for spec in platform_specs)
        min_y_raw = min(spec["y"] - spec["depth"] // 2 for spec in platform_specs)
        max_y_raw = max(spec["y"] + spec["depth"] // 2 for spec in platform_specs)

        center_shift_x = -((min_x_raw + max_x_raw) // 2)
        center_shift_y = -((min_y_raw + max_y_raw) // 2)
        for spec in platform_specs:
            spec["x"] += center_shift_x
            spec["y"] += center_shift_y

        min_x = min(spec["x"] - spec["width"] // 2 for spec in platform_specs)
        max_x = max(spec["x"] + spec["width"] // 2 for spec in platform_specs)
        min_y = min(spec["y"] - spec["depth"] // 2 for spec in platform_specs)
        max_y = max(spec["y"] + spec["depth"] // 2 for spec in platform_specs)

        margin = max(280, int(round(560 * scale)))
        bounds = (min_x - margin, min_y - margin, max_x + margin, max_y + margin)
        lava_center_x = (min_x + max_x) // 2
        lava_center_y = (min_y + max_y) // 2
        lava_width = (max_x - min_x) + (2 * margin)
        lava_depth = (max_y - min_y) + (2 * margin)

        # Scale seeds conservatively for high platform counts.
        # Most complexity here already comes from many claimed areas (platforms/bridges/plates),
        # so uncapped per-platform seed growth can become prohibitively slow.
        seed_platform_budget = min(num_platforms, 28)
        seed_count = min(
            30000,
            max(9000, int(cfg["seeds_per_platform"]) * seed_platform_budget),
        )
        builder = ProceduralMapBuilder(bounds=bounds, num_seeds=seed_count, seed=seed)

        lava_tag = 9000
        bridge_tag_base = 9100
        green_plate_tag_base = 9300
        red_plate_tag_base = 9500
        outer_ceiling_height = 512
        outer_ceiling_texture = "RROCK16"
        platform_floor_texture = "FLOOR4_8"
        platform_wall_texture = "METAL2"

        builder.add_area(
            name="LavaSea",
            shape=(lava_center_x, lava_center_y, lava_width, lava_depth),
            floor_height=lava_height,
            ceiling_height=outer_ceiling_height,
            floor_texture="LAVA1",
            ceiling_texture=outer_ceiling_texture,
            wall_texture="ASHWALL2",
            lower_texture="ASHWALL2",
            upper_texture="ASHWALL2",
            light_level=156,
            tag=lava_tag,
            mode="overwrite",
        )
        platform_names: List[str] = []

        for i, spec in enumerate(platform_specs):
            name = f"Platform_{i:02d}"
            builder.add_area(
                name=name,
                shape=(spec["x"], spec["y"], spec["width"], spec["depth"]),
                floor_height=platform_floor_height,
                ceiling_height=outer_ceiling_height,
                floor_texture=platform_floor_texture,
                ceiling_texture=outer_ceiling_texture,
                wall_texture=platform_wall_texture,
                lower_texture=platform_wall_texture,
                upper_texture=platform_wall_texture,
                light_level=188,
                tag=7000 + i,
                mode="overwrite",
            )
            platform_names.append(name)

        bridge_tags: List[int] = []
        green_plate_tags_for_bridge: List[int] = []
        red_plate_tags_for_bridge: List[int] = []

        for i in range(num_platforms - 1):
            left = platform_specs[i]
            right = platform_specs[i + 1]

            bx = (left["x"] + right["x"]) // 2
            by = (left["y"] + right["y"]) // 2

            x_span = abs(right["x"] - left["x"]) - ((left["width"] + right["width"]) // 2)
            bridge_w = int(max(96, x_span + 72))
            bridge_h = int(max(108, abs(right["y"] - left["y"]) + 88))

            bridge_tag = bridge_tag_base + i
            builder.add_area(
                name=f"Bridge_{i:02d}",
                shape=(bx, by, bridge_w, bridge_h),
                floor_height=lava_height,
                ceiling_height=outer_ceiling_height,
                floor_texture="LAVA1",
                ceiling_texture=outer_ceiling_texture,
                wall_texture=platform_wall_texture,
                lower_texture=platform_wall_texture,
                upper_texture=platform_wall_texture,
                light_level=156,
                tag=bridge_tag,
                mode="overwrite",
            )
            bridge_tags.append(bridge_tag)

            green_plate_tags_for_bridge.append(green_plate_tag_base + i)
            red_plate_tags_for_bridge.append(red_plate_tag_base + i)

        plate_size = 72 if num_platforms >= 60 else 56
        for i, spec in enumerate(platform_specs):
            x = spec["x"]
            y = spec["y"]
            x_offset = max(22, int(spec["width"] * 0.22))
            y_offset = max(14, int(spec["depth"] * 0.14))

            if i < num_platforms - 1:
                builder.add_area(
                    name=f"GreenPlate_{i:02d}",
                    shape=(x + x_offset, y - y_offset, plate_size, plate_size),
                    floor_height=platform_floor_height + 2,
                    ceiling_height=outer_ceiling_height,
                    floor_texture="CEIL5_1",
                    ceiling_texture=outer_ceiling_texture,
                    wall_texture="METAL2",
                    light_level=220,
                    tag=green_plate_tag_base + i,
                    mode="overwrite",
                )

            if i > 0:
                builder.add_area(
                    name=f"RedPlate_{i:02d}",
                    shape=(x - x_offset, y + y_offset, plate_size, plate_size),
                    floor_height=platform_floor_height + 2,
                    ceiling_height=outer_ceiling_height,
                    floor_texture="CEIL5_1",
                    ceiling_texture=outer_ceiling_texture,
                    wall_texture="METAL2",
                    light_level=220,
                    tag=red_plate_tag_base + (i - 1),
                    mode="overwrite",
                )

        self._auto_connect_touching_areas(builder)

        spawn_offsets = [(-28, -18), (28, 18), (-28, 18), (28, -18)]
        sx = platform_specs[0]["x"]
        sy = platform_specs[0]["y"]
        for i in range(4):
            dx, dy = spawn_offsets[i]
            builder.add_thing("MAP_SPOT", sx + dx, sy + dy, tid=100 + i)

        builder.add_thing("PLAYER1_START", sx - 28, sy - 18, angle=0)
        builder.add_thing("PLAYER2_START", sx + 28, sy + 18, angle=0)
        builder.add_thing("PLAYER3_START", sx - 28, sy + 18, angle=0)
        builder.add_thing("PLAYER4_START", sx + 28, sy - 18, angle=0)

        acs = ACSBuilder()
        acs.add_include("zcommon.acs")

        acs.add_script(
            ScriptType.ENTER,
            f"""
            int pn = PlayerNumber();
            if (pn < 0 || pn >= {max_players}) terminate;
            Thing_ChangeTID(0, 1000 + pn);
            SetActorProperty(0, APROP_Health, 100);
            // Ensure players have no weapons (fists only)
            ClearInventory();
            GiveInventory("Fist", 1);
            SetWeapon("Fist");
            """,
            number=998,
        )

        acs.add_script(
            ScriptType.RESPAWN,
            f"""
            int pn = PlayerNumber();
            int p_tid;
            int spot;
            if (pn < 0 || pn >= {max_players}) terminate;
            p_tid = 1000 + pn;
            Thing_ChangeTID(0, p_tid);
            SetActorProperty(0, APROP_Health, 100);
            spot = 100 + pn;
            SetActorPosition(0, GetActorX(spot), GetActorY(spot), GetActorZ(spot), 0);
            // Remove all weapons on respawn so players keep only fists
            ClearInventory();
            GiveInventory("Fist", 1);
            SetWeapon("Fist");
            """,
            number=997,
        )

        bridge_blocks: List[str] = []
        for i, bridge_tag in enumerate(bridge_tags):
            green_tag = green_plate_tags_for_bridge[i]
            red_tag = red_plate_tags_for_bridge[i]
            count_checks = "\n".join(
                [
                    f"hold_{i} += ThingCountSector(0, {1000 + p}, {green_tag});\n"
                    f"hold_{i} += ThingCountSector(0, {1000 + p}, {red_tag});"
                    for p in range(max_players)
                ]
            )

            block = f"""
            int hold_{i} = 0;
            {count_checks}

            if (hold_{i} > 0) {{
                if (bridge_state[{i}] != 1) {{
                    bridge_state[{i}] = 1;
                    int speed_up_{i} = 24 + Random(0, 10);
                    Floor_MoveToValue({bridge_tag}, speed_up_{i}, {platform_floor_height}, 0);
                    ChangeFloor({bridge_tag}, "{platform_floor_texture}");
                    Sector_SetDamage({bridge_tag}, 0, 0);
                    Light_ChangeToValue({bridge_tag}, 208);
                }}
            }} else {{
                if (bridge_state[{i}] != 0) {{
                    bridge_state[{i}] = 0;
                    int speed_down_{i} = 52 + Random(0, 20);
                    Floor_MoveToValue({bridge_tag}, speed_down_{i}, {lava_height}, 0);
                    ChangeFloor({bridge_tag}, "LAVA1");
                    Sector_SetDamage({bridge_tag}, {lava_damage}, 14);
                    Light_ChangeToValue({bridge_tag}, 156);
                }}
            }}
            """
            bridge_blocks.append(block)

        green_color_lines = "\n".join(
            [f"Sector_SetColor({tag}, 24, 180, 32);" for tag in green_plate_tags_for_bridge]
        )
        red_color_lines = "\n".join(
            [f"Sector_SetColor({tag}, 200, 44, 44);" for tag in red_plate_tags_for_bridge]
        )
        platform_reached_lines = "\n".join(
            [
                "int reached_platform = 1;",
                *[
                    (
                        f"if (ThingCountSector(0, {1000 + p}, {7000 + i}) > 0 && reached_platform < {i + 1}) "
                        f"reached_platform = {i + 1};"
                    )
                    for i in range(num_platforms)
                    for p in range(max_players)
                ],
                "lavapit_platform_reached_global = reached_platform;",
            ]
        )

        acs.add_global_var("lavapit_platform_reached_global", 58, "int")

        open_script = f"""
        int bridge_state[{len(bridge_tags)}];
        int i;

        for (i = 0; i < {len(bridge_tags)}; i++) {{
            bridge_state[i] = -1;
        }}

        Sector_SetDamage({lava_tag}, {lava_damage}, 14);
        {green_color_lines}
        {red_color_lines}
        lavapit_platform_reached_global = 1;

        while (TRUE)
        {{
            {' '.join(bridge_blocks)}
            {platform_reached_lines}
            Delay({poll_tics} + Random(0, {runtime_jitter_tics}));
        }}
        """
        acs.add_script(ScriptType.OPEN, open_script, number=1)

        acs.add_script(
            ScriptType.DEATH,
            """
            Delay(1);
            Exit_Normal(0);
            """,
            number=996,
        )

        builder.map_data.scripts = acs.to_code()
        try:
            compiled = acs.compile()
            builder.map_data.behavior = (
                compiled if compiled else b"ACSE\x08\x00\x00\x00\x00\x00\x00\x00"
            )
        except Exception as exc:
            print(f"ACS compile warning: {exc}")
            try:
                debug_path = os.path.join(os.path.dirname(output_path), "lavapit_debug.acs")
                acs.save_source(debug_path)
                print(f"Wrote ACS debug source to {debug_path}")
            except Exception:
                pass
            builder.map_data.behavior = b"ACSE\x08\x00\x00\x00\x00\x00\x00\x00"

        builder.build(output_path)
        print(f"Lavapit WAD written to {output_path} (seed={seed}, platforms={num_platforms})")


if __name__ == "__main__":
    output = "examples/benchmark/output/lavapit.wad"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    scenario = LavaPitScenario(config={"seed": random.randint(0, 999999)})
    scenario.generate(output)
