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
            "seed": None,
            "grid_size": 8,
            "room_size": 384,
            "corridor_width": 3,
            "num_demons": 30,
        }

    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)
        random.seed(seed)

        grid_size = cfg["grid_size"]
        room_size = cfg["room_size"]
        corridor_width = cfg["corridor_width"]
        num_demons = cfg["num_demons"]

        cell_spacing = room_size + 256  # gap between centers for corridor walls

        half = (grid_size * cell_spacing) // 2 + 400
        bounds = (-half, -half, half, half)

        builder = ProceduralMapBuilder(bounds=bounds, num_seeds=20000, seed=seed)

        decorate_str = """
ACTOR MazeDemon : Demon 14001 {
  Health 50
}
"""
        builder.wad_writer.add_lump("DECORATE", decorate_str.encode("utf-8"))

        # DFS Maze Generation
        visited = set()
        edges: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        stack = [(grid_size // 2, grid_size // 2)]
        visited.add((grid_size // 2, grid_size // 2))
        while stack:
            r, c = stack[-1]
            neighbors = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
            unvisited = [
                (nr, nc)
                for nr, nc in neighbors
                if 0 <= nr < grid_size and 0 <= nc < grid_size and (nr, nc) not in visited
            ]
            if unvisited:
                nr, nc = random.choice(unvisited)
                visited.add((nr, nc))
                edges.append(((r, c), (nr, nc)))
                stack.append((nr, nc))
            else:
                stack.pop()

        # Add extra edges for loops
        extra_edges = 0
        all_cells = [(r, c) for r in range(grid_size) for c in range(grid_size)]
        random.shuffle(all_cells)
        edge_set = set((min(a, b), max(a, b)) for a, b in edges)
        for r, c in all_cells:
            if extra_edges >= 15:
                break
            for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
                if 0 <= nr < grid_size and 0 <= nc < grid_size:
                    key = (min((r, c), (nr, nc)), max((r, c), (nr, nc)))
                    if key not in edge_set:
                        edges.append(((r, c), (nr, nc)))
                        edge_set.add(key)
                        extra_edges += 1
                        break

        # Room
        spawn_cell = (grid_size // 2, grid_size // 2)
        exit_cell = (grid_size - 1, grid_size - 1)

        # Compute center position for a grid cell
        def cell_center(row: int, col: int) -> Tuple[int, int]:
            cx = (col - grid_size / 2 + 0.5) * cell_spacing
            cy = (row - grid_size / 2 + 0.5) * cell_spacing
            return int(cx), int(cy)

        room_centers: Dict[Tuple[int, int], Tuple[int, int]] = {}
        for row in range(grid_size):
            for col in range(grid_size):
                cx, cy = cell_center(row, col)
                room_centers[(row, col)] = (cx, cy)
                name = f"Room_r{row}_c{col}"
                tag = 100 + row * grid_size + col

                light = 200 if (row, col) == spawn_cell else 0
                dist_from_center = abs(row - grid_size//2) + abs(col - grid_size//2)
                floor_h = 8 if dist_from_center <= 2 else (-8 if dist_from_center > 3 else 0)

                builder.add_area(
                    name=name,
                    shape=(cx, cy, room_size, room_size),
                    floor_height=floor_h,
                    ceiling_height=192,
                    floor_texture="FLOOR4_8",
                    ceiling_texture="CEIL3_5",
                    wall_texture="STONE2",
                    light_level=light,
                    tag=tag,
                )

        # Corridors DFS edges
        corridor_info = []  # (tag, cx, cy) for light sweep
        corr_tag_base = 200
        for corr_idx, ((r1, c1), (r2, c2)) in enumerate(edges):
            name_a = f"Room_r{r1}_c{c1}"
            name_b = f"Room_r{r2}_c{c2}"
            corr_name = builder.add_corridor(
                name_a, name_b,
                width=corridor_width,
                floor_texture="FLOOR4_8",
                ceiling_height=192,
                wall_texture="METAL1",
                light_level=0,
            )

            corr_tag = corr_tag_base + corr_idx
            builder.graph.get_area(corr_name).config.tag = corr_tag

            cx1, cy1 = room_centers[(r1, c1)]
            cx2, cy2 = room_centers[(r2, c2)]
            mid_x = (cx1 + cx2) // 2
            mid_y = (cy1 + cy2) // 2
            corridor_info.append((corr_tag, mid_x, mid_y))

            if (r1, c1) == spawn_cell or (r2, c2) == spawn_cell:
                builder.graph.get_area(corr_name).config.light_level = 200

        # Find corridors adjacent to spawn
        spawn_corridor_tags = set()
        for corr_idx, ((r1, c1), (r2, c2)) in enumerate(edges):
            if (r1, c1) == spawn_cell or (r2, c2) == spawn_cell:
                spawn_corridor_tags.add(corr_tag_base + corr_idx)

        spawn_cx, spawn_cy = room_centers[spawn_cell]
        builder.add_thing(ThingType.PLAYER1_START, spawn_cx - 32, spawn_cy, angle=0)
        builder.add_thing(ThingType.PLAYER2_START, spawn_cx + 32, spawn_cy, angle=0)
        builder.add_thing(ThingType.PLAYER3_START, spawn_cx - 32, spawn_cy + 32, angle=0)
        builder.add_thing(ThingType.PLAYER4_START, spawn_cx + 32, spawn_cy + 32, angle=0)

        # Place demons in random rooms (not spawn or exit)
        eligible_rooms = [
            (r, c)
            for r in range(grid_size)
            for c in range(grid_size)
            if (r, c) not in (spawn_cell, exit_cell)
        ]
        demon_rooms = random.sample(eligible_rooms, min(num_demons, len(eligible_rooms)))
        for idx, (r, c) in enumerate(demon_rooms):
            room_name = f"Room_r{r}_c{c}"
            pt = builder.get_random_point_in_area(room_name, safe=False)
            if pt:
                builder.add_thing(14001, pt[0], pt[1])  # MazeDemon

        # Scatter pickups (health + ammo) in random non-spawn/exit rooms
        pickup_rooms = random.sample(eligible_rooms, min(12, len(eligible_rooms)))
        for idx, (r, c) in enumerate(pickup_rooms):
            room_name = f"Room_r{r}_c{c}"
            pt = builder.get_random_point_in_area(room_name, safe=False)
            if pt:
                if idx % 3 == 0:
                    builder.add_thing(ThingType.STIMPACK, pt[0], pt[1])
                elif idx % 3 == 1:
                    builder.add_thing(ThingType.BOX_OF_SHELLS, pt[0], pt[1])
                else:
                    builder.add_thing(ThingType.MEDIKIT, pt[0], pt[1])

        acs = ACSBuilder()
        acs.add_include("zcommon.acs")
        acs.add_global_var("sl_p1_alive", 41, "int")
        acs.add_global_var("sl_p2_alive", 42, "int")
        acs.add_global_var("sl_distance", 43, "int")
        acs.add_global_var("sl_demons_alive", 44, "int")

        # Script 1 (ENTER): Player setup
        script_enter = """
        int pn = PlayerNumber();
        Thing_ChangeTID(0, 1000 + pn);
        SetActorProperty(0, APROP_Health, 100);
        ClearInventory();
        if (pn == 1) {
            GiveInventory("Shotgun", 1);
            GiveInventory("Shell", 60);
            GiveInventory("Chaingun", 1);
            GiveInventory("Clip", 200);
            SetWeapon("Shotgun");
        }
        ACS_ExecuteAlways(10, 0, 0, 0, 0);
        """
        acs.add_script(ScriptType.ENTER, script_enter, number=1)

        # Script 3 (OPEN): Light sweep loop
        # Build per-room light checks in Python since ACS lacks dynamic arrays
        spawn_tag = 100 + spawn_cell[0] * grid_size + spawn_cell[1]
        # exit_tag = 100 + exit_cell[0] * grid_size + exit_cell[1]

        bright_dist = room_size // 2 + 48  # Chebyshev: covers room + Voronoi edge buffer

        light_checks = []
        for row in range(grid_size):
            for col in range(grid_size):
                tag = 100 + row * grid_size + col
                if tag == spawn_tag:
                    continue  # spawn always lit
                cx, cy = room_centers[(row, col)]
                light_checks.append(
                    f"""
            dx = p1x - {cx};
            if (dx < 0) dx = -dx;
            dy = p1y - {cy};
            if (dy < 0) dy = -dy;
            dist = dx;
            if (dy > dist) dist = dy;
            if (dist < {bright_dist}) {{
                Light_ChangeToValue({tag}, 200);
            }} else {{
                Light_ChangeToValue({tag}, 0);
            }}"""
                )

        corr_bright_dist = 250  # Chebyshev: covers corridor width + buffer

        for corr_tag, cx, cy in corridor_info:
            if corr_tag in spawn_corridor_tags:
                continue  # always lit near spawn
            light_checks.append(
                f"""
            dx = p1x - {cx};
            if (dx < 0) dx = -dx;
            dy = p1y - {cy};
            if (dy < 0) dy = -dy;
            dist = dx;
            if (dy > dist) dist = dy;
            if (dist < {corr_bright_dist}) {{
                Light_ChangeToValue({corr_tag}, 200);
            }} else {{
                Light_ChangeToValue({corr_tag}, 0);
            }}"""
            )

        light_block = "\n".join(light_checks)
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
{light_block}
            }}
            Delay(4);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_light, number=3)

        # Script 4 (OPEN): Win condition + global variable updates
        exit_cx, exit_cy = room_centers[exit_cell]
        exit_half = room_size // 2
        exit_xmin = exit_cx - exit_half
        exit_xmax = exit_cx + exit_half
        exit_ymin = exit_cy - exit_half
        exit_ymax = exit_cy + exit_half

        script_win = f"""
        int px1;
        int py1;
        int px2;
        int py2;
        int p1_in;
        int p2_in;
        int adx;
        int ady;

        while (TRUE) {{
            // Update alive status
            if (ThingCount(T_NONE, 1000) > 0) {{
                sl_p1_alive = 1;
            }} else {{
                sl_p1_alive = 0;
            }}
            if (ThingCount(T_NONE, 1001) > 0) {{
                sl_p2_alive = 1;
            }} else {{
                sl_p2_alive = 0;
            }}

            // Update demon count
            sl_demons_alive = ThingCountName("MazeDemon", 0);

            // Update distance
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

                // Win condition: both in exit room
                p1_in = (px1 >= {exit_xmin} && px1 <= {exit_xmax} && py1 >= {exit_ymin} && py1 <= {exit_ymax});
                p2_in = (px2 >= {exit_xmin} && px2 <= {exit_xmax} && py2 >= {exit_ymin} && py2 <= {exit_ymax});
                if (p1_in && p2_in) {{
                    Exit_Normal(0);
                }}
            }}

            Delay(35);
        }}
        """
        acs.add_script(ScriptType.OPEN, script_win, number=4)

        # Script 10 (VOID): Per-player HUD loop
        script_hud = """
        while (TRUE) {
            SetFont("SMALLFONT");
            int demons = sl_demons_alive;
            int dist   = sl_distance;
            str d_color = "\\cC";
            if (demons > 13) d_color = "\\cR";
            else if (demons > 7) d_color = "\\cE";

            HudMessage(s:"DEMONS: ", s:d_color, d:demons;
                HUDMSG_PLAIN, 1, CR_WHITE, 0.5, 0.80, 2.0);
            HudMessage(s:"DISTANCE: ", d:dist;
                HUDMSG_PLAIN, 2, CR_WHITE, 0.5, 0.83, 2.0);
            Delay(4);
        }
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
