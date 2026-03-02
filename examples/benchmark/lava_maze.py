import random
from typing import Any, Dict

from doomgen.abstraction.layout import ConnectionType
from doomgen.batch.scenario import Scenario
from doomgen.builder import ProceduralMapBuilder
from doomgen.doom.things import ThingType
from doomgen.logic.acs_builder import ACSBuilder


class LavaMazeScenario(Scenario):
    """
    Two-player cooperative maze scenario.

    Player 1 navigates a procedurally-generated lava maze from inside.
    Player 2 observes from elevated stands and signals directions via
    colored screen flashes triggered by weapon fire.
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "physical_size": 9,
            "cell_size": 128,
            "initial_maze_size": 4,
            "lava_damage": 10,
            "seed": None,
        }

    def generate(self, output_path: str) -> None:
        cfg = self.config
        PHYSICAL_SIZE = int(cfg["physical_size"])
        CELL_SIZE = int(cfg["cell_size"])
        INITIAL_MAZE_SIZE = int(cfg["initial_maze_size"])
        LAVA_DAMAGE = int(cfg["lava_damage"])
        seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)

        MAZE_WIDTH_UNITS = PHYSICAL_SIZE * CELL_SIZE
        OFFSET_X = -(MAZE_WIDTH_UNITS // 2)
        OFFSET_Y = -(MAZE_WIDTH_UNITS // 2)

        builder = ProceduralMapBuilder(
            bounds=(-1600, -1600, 1600, 1600),
            num_seeds=12000,
            seed=seed,
        )

        builder.add_area(
            "LavaPit",
            shape=(0, 0, 2400, 2400),
            floor_height=-64,
            ceiling_height=512,
            floor_texture="LAVA1",
            mode="overwrite",
            tag=99,
        )

        STANDS_HEIGHT = 224
        STANDS_THICKNESS = 256
        STANDS_INNER = (MAZE_WIDTH_UNITS // 2) + 64

        pos_y = STANDS_INNER + STANDS_THICKNESS / 2
        stands_width = 2 * STANDS_INNER + 2 * STANDS_THICKNESS
        builder.add_area("Stands_N", shape=(0, pos_y, stands_width, STANDS_THICKNESS),   floor_height=STANDS_HEIGHT, ceiling_height=512, mode="overwrite", tag=201, wall_texture="DOGLDIR",  light_level=255)
        builder.add_area("Stands_S", shape=(0, -pos_y, stands_width, STANDS_THICKNESS),  floor_height=STANDS_HEIGHT, ceiling_height=512, mode="overwrite", tag=203, wall_texture="COMPBLUE", light_level=255)

        pos_x = STANDS_INNER + STANDS_THICKNESS / 2
        h_span = 2 * STANDS_INNER + 2 * STANDS_THICKNESS
        builder.add_area("Stands_E", shape=( pos_x, 0, STANDS_THICKNESS, h_span), floor_height=STANDS_HEIGHT, ceiling_height=512, mode="overwrite", tag=200, wall_texture="A-CAMO5", light_level=255)
        builder.add_area("Stands_W", shape=(-pos_x, 0, STANDS_THICKNESS, h_span), floor_height=STANDS_HEIGHT, ceiling_height=512, mode="overwrite", tag=202, wall_texture="REDWALL",  light_level=255)

        base_tag = 100
        for py in range(PHYSICAL_SIZE):
            for px in range(PHYSICAL_SIZE):
                cx = OFFSET_X + (px * CELL_SIZE) + (CELL_SIZE // 2)
                cy = OFFSET_Y + (py * CELL_SIZE) + (CELL_SIZE // 2)
                tag = base_tag + (py * PHYSICAL_SIZE + px)
                if px == 1 and py == 1:
                    f_tex, f_h = "FLOOR4_8", 0
                else:
                    f_tex, f_h = "LAVA1", -64
                builder.add_area(
                    f"Grid_{px}_{py}",
                    shape=(cx, cy, CELL_SIZE, CELL_SIZE),
                    floor_height=f_h,
                    ceiling_height=512,
                    tag=tag,
                    mode="overwrite",
                    floor_texture=f_tex,
                    wall_texture="ASHWALL2",
                )

        print("Building Connectivity Graph...")

        builder.connect_adjacent("Stands_N", "Stands_E", ConnectionType.OPEN)
        builder.connect_adjacent("Stands_E", "Stands_S", ConnectionType.OPEN)
        builder.connect_adjacent("Stands_S", "Stands_W", ConnectionType.OPEN)
        builder.connect_adjacent("Stands_W", "Stands_N", ConnectionType.OPEN)

        barrier_args = {"blocking": True, "middle_texture": "-"}
        for stand in ("Stands_N", "Stands_S", "Stands_E", "Stands_W"):
            builder.connect_adjacent(stand, "LavaPit", ConnectionType.WINDOW, **barrier_args)

        for py in range(PHYSICAL_SIZE):
            for px in range(PHYSICAL_SIZE):
                curr = f"Grid_{px}_{py}"
                if px < PHYSICAL_SIZE - 1:
                    builder.connect_adjacent(curr, f"Grid_{px+1}_{py}", ConnectionType.OPEN, silent=True)
                if py < PHYSICAL_SIZE - 1:
                    builder.connect_adjacent(curr, f"Grid_{px}_{py+1}", ConnectionType.OPEN, silent=True)
                if px < PHYSICAL_SIZE - 1 and py < PHYSICAL_SIZE - 1:
                    builder.connect_adjacent(curr, f"Grid_{px+1}_{py+1}", ConnectionType.OPEN, silent=True)
                if px > 0 and py < PHYSICAL_SIZE - 1:
                    builder.connect_adjacent(curr, f"Grid_{px-1}_{py+1}", ConnectionType.OPEN, silent=True)
                builder.connect_adjacent(curr, "LavaPit", ConnectionType.OPEN, silent=True)

        p1_x = OFFSET_X + (1 * CELL_SIZE) + (CELL_SIZE // 2)
        p1_y = OFFSET_Y + (1 * CELL_SIZE) + (CELL_SIZE // 2)
        builder.add_thing(ThingType.PLAYER1_START, x=p1_x, y=p1_y, angle=0)

        p2_y = -(STANDS_INNER + 64)
        builder.add_thing(ThingType.PLAYER2_START, x=0, y=p2_y, angle=90)

        acs = ACSBuilder()
        acs.add_include("zcommon.acs")

        acs.add_map_var("g_flash_timer", initial=0)
        acs.add_map_var("g_flash_r",     initial=0)
        acs.add_map_var("g_flash_g",     initial=0)
        acs.add_map_var("g_flash_b",     initial=0)
        acs.add_map_var("g_flash_state", initial=0)
        acs.add_global_var("lm_maze_size_global",        11, "int")
        acs.add_global_var("lm_goal_grid_x_global",      13, "int")
        acs.add_global_var("lm_p1_grid_x_global",        14, "int")
        acs.add_global_var("lm_p1_grid_y_global",        15, "int")
        acs.add_global_var("lm_flash_signal_global",     16, "int")
        acs.add_global_var("lm_flash_active_global",     17, "int")
        acs.add_global_var("lm_goal_grid_y_global",      18, "int")
        acs.add_global_var("lm_maze_bits_0_global",      19, "int")
        acs.add_global_var("lm_maze_bits_1_global",      20, "int")
        acs.add_global_var("lm_maze_bits_2_global",      21, "int")
        acs.add_global_var("lm_levels_completed_global", 22, "int")

        acs.scripts = []

        maze_logic_script = f"""
    #define MAP_WIDTH {PHYSICAL_SIZE}
    #define CELL_SIZE {CELL_SIZE}
    #define BASE_TAG {base_tag}
    #define MAX_TILES 20
    #define APROP_PainChance 21

    int current_maze_size = {INITIAL_MAZE_SIZE};
    int current_start_tag = 0;
    int current_end_tag = 0;

    int g_start_x = 1;
    int g_start_y = 1;

    int visited[MAP_WIDTH * MAP_WIDTH];
    int stack[100];
    int maze_bits_chunk[3];

    function int get_tag(int x, int y) {{
        return BASE_TAG + (y * MAP_WIDTH + x);
    }}

    function int get_world_x(int gx) {{
        return {OFFSET_X} + (gx * {CELL_SIZE}) + ({CELL_SIZE} / 2);
    }}

    function int get_world_y(int gy) {{
        return {OFFSET_Y} + (gy * {CELL_SIZE}) + ({CELL_SIZE} / 2);
    }}

    function void reset_map(int keep_tag) {{
        int t;
        int i;
        for (i = 0; i < MAP_WIDTH * MAP_WIDTH; i++) {{
            t = BASE_TAG + i;
            if (t != keep_tag) {{
                Floor_MoveToValue(t, 2048, -64, 0);
                ChangeFloor(t, "LAVA1");
                Sector_SetDamage(t, {LAVA_DAMAGE}, 14);
                Sector_SetColor(t, 255, 255, 255);
            }}
        }}
    }}

    function void carve(int x, int y) {{
        int tag = get_tag(x, y);
        Floor_MoveToValue(tag, 2048, 0, 0);
        ChangeFloor(tag, "FLOOR4_8");
        Sector_SetDamage(tag, 0, 0);
        Light_ChangeToValue(tag, 160);
        if (x >= 0 && x < MAP_WIDTH && y >= 0 && y < MAP_WIDTH) {{
            int bit_idx = y * MAP_WIDTH + x;
            int chunk = bit_idx / 27;
            int shift = bit_idx % 27;
            maze_bits_chunk[chunk] = maze_bits_chunk[chunk] | (1 << shift);
        }}
    }}

    script 1 OPEN {{
        Sector_SetDamage(99, {LAVA_DAMAGE}, 14);

        g_start_x = Random(0, MAP_WIDTH - 1);
        g_start_y = Random(0, MAP_WIDTH - 1);

        current_start_tag = get_tag(g_start_x, g_start_y);
        lm_maze_size_global        = current_maze_size;
        lm_goal_grid_x_global      = -1;
        lm_goal_grid_y_global      = -1;
        lm_p1_grid_x_global        = -1;
        lm_p1_grid_y_global        = -1;
        lm_flash_signal_global     = 0;
        lm_flash_active_global     = 0;
        lm_maze_bits_0_global      = 0;
        lm_maze_bits_1_global      = 0;
        lm_maze_bits_2_global      = 0;

        ACS_NamedExecute("GenerateMaze", 0, g_start_x, g_start_y, current_maze_size);

        while (TRUE) {{
            Delay(5);
        }}
    }}

    script "GenerateMaze" (int sx, int sy, int size) {{
        int start_tag = get_tag(sx, sy);
        int i;
        reset_map(start_tag);
        Delay(1);

        for (i = 0; i < 3; i++) maze_bits_chunk[i] = 0;

        carve(sx, sy);
        Sector_SetColor(start_tag, 0, 255, 0);

        for (i = 0; i < MAP_WIDTH * MAP_WIDTH; i++) visited[i] = 0;

        int stack_ptr = 0;
        int cx = sx;
        int cy = sy;
        int count_carved = 1;

        visited[cy * MAP_WIDTH + cx] = 1;
        stack[stack_ptr++] = (cx << 8) | cy;

        int neighbors[4];
        int n_count;
        int next_packed, nx, ny, wall_x, wall_y;
        int last_visited_tag = start_tag;
        int last_x = sx;
        int last_y = sy;

        while (count_carved < size && stack_ptr > 0) {{
            int packed = stack[stack_ptr-1];
            cx = packed >> 8;
            cy = packed & 0xFF;

            n_count = 0;

            if (cy + 2 < MAP_WIDTH && visited[(cy+2)*MAP_WIDTH + cx] == 0)
                neighbors[n_count++] = (cx << 8) | (cy+2);
            if (cy - 2 >= 0 && visited[(cy-2)*MAP_WIDTH + cx] == 0)
                neighbors[n_count++] = (cx << 8) | (cy-2);
            if (cx + 2 < MAP_WIDTH && visited[cy*MAP_WIDTH + (cx+2)] == 0)
                neighbors[n_count++] = ((cx+2) << 8) | cy;
            if (cx - 2 >= 0 && visited[cy*MAP_WIDTH + (cx-2)] == 0)
                neighbors[n_count++] = ((cx-2) << 8) | cy;

            if (n_count > 0) {{
                int r = Random(0, n_count-1);
                next_packed = neighbors[r];
                nx = next_packed >> 8;
                ny = next_packed & 0xFF;

                wall_x = (cx + nx) / 2;
                wall_y = (cy + ny) / 2;

                carve(wall_x, wall_y);
                carve(nx, ny);

                visited[ny * MAP_WIDTH + nx] = 1;
                count_carved += 2;
                last_visited_tag = get_tag(nx, ny);
                last_x = nx;
                last_y = ny;

                stack[stack_ptr++] = next_packed;
            }} else {{
                stack_ptr--;
            }}
        }}

        current_end_tag = last_visited_tag;
        lm_maze_size_global        = current_maze_size;
        lm_goal_grid_x_global      = last_x;
        lm_goal_grid_y_global      = last_y;
        lm_maze_bits_0_global      = maze_bits_chunk[0];
        lm_maze_bits_1_global      = maze_bits_chunk[1];
        lm_maze_bits_2_global      = maze_bits_chunk[2];

        Sector_SetColor(current_end_tag, 0, 0, 255);
        Print(s:"Level Up! Size: ", d:size);
    }}

    script "EndGame" (void) {{
        Exit_Normal(0);
    }}

    script 999 DEATH {{
        if (PlayerNumber() != -1) {{
            ACS_NamedExecuteAlways("EndGame", 0);
        }}
    }}

    script 2 ENTER {{
        if (PlayerNumber() != 0) terminate;

        Thing_ChangeTID(0, 1000);

        int wx = get_world_x(g_start_x) << 16;
        int wy = get_world_y(g_start_y) << 16;

        SetActorPosition(0, wx, wy, 0, 0);
        SetActorProperty(0, APROP_ViewHeight, 45.0);
        SetActorProperty(0, APROP_Mass, 0x7FFFFFFF);
        SetActorProperty(0, 21, 0);

        FadeTo(0, 0, 0, 1.0, 0.0);
        ClearInventory();

        while (TRUE) {{
            if (GetActorProperty(0, APROP_HEALTH) <= 0) {{
                ACS_NamedExecute("EndGame", 0);
                terminate;
            }}

            int x = GetActorX(0);
            int y = GetActorY(0);

            int offset = (MAP_WIDTH * CELL_SIZE) / 2;
            int gx = ((x >> 16) + offset) / CELL_SIZE;
            int gy = ((y >> 16) + offset) / CELL_SIZE;

            if (gx >= 0 && gx < MAP_WIDTH && gy >= 0 && gy < MAP_WIDTH) {{
                lm_p1_grid_x_global = gx;
                lm_p1_grid_y_global = gy;
                int my_tag = get_tag(gx, gy);

                if (my_tag == current_end_tag) {{
                    lm_levels_completed_global++;
                    current_maze_size += 2;
                    if (current_maze_size > MAX_TILES) current_maze_size = MAX_TILES;
                    if (current_maze_size < {INITIAL_MAZE_SIZE}) current_maze_size = {INITIAL_MAZE_SIZE};
                    lm_maze_size_global = current_maze_size;

                    ACS_NamedExecute("GenerateMaze", 0, gx, gy, current_maze_size);
                }}
            }} else {{
                lm_p1_grid_x_global = -1;
                lm_p1_grid_y_global = -1;
            }}

            if (g_flash_timer > 0) {{
                g_flash_timer--;
                if (g_flash_state == 0 || g_flash_timer > 18) {{
                     FadeTo(g_flash_r, g_flash_g, g_flash_b, 1.0, 0.1);
                     g_flash_state = 1;
                     lm_flash_active_global = 1;
                }}
            }} else {{
                if (g_flash_state == 1) {{
                    FadeTo(0, 0, 0, 1.0, 0.5);
                    g_flash_state = 0;
                    lm_flash_active_global = 0;
                }}
            }}

            SetActorAngle(1000, 0);
            SetActorPitch(1000, 0);

            Delay(1);
        }}
    }}

    script 3 ENTER {{
        if (PlayerNumber() != 1) terminate;

        Thing_ChangeTID(0, 1001);

        ClearInventory();
        GiveInventory("Pistol",      1);
        GiveInventory("Shotgun",     1);
        GiveInventory("Chaingun",    1);
        GiveInventory("PlasmaRifle", 1);
        GiveInventory("Clip",   200);
        GiveInventory("Shell",   50);
        GiveInventory("Cell",   200);
        SetWeapon("Pistol");

        int btns, old_btns;

        while(TRUE) {{
            GiveInventory("Clip",  1);
            GiveInventory("Shell", 1);
            GiveInventory("Cell",  1);

            btns = GetPlayerInput(-1, INPUT_BUTTONS);

            if (btns & BT_ATTACK) {{
                int signal = 0;
                str w_name = "";
                if      (CheckWeapon("Pistol"))      {{ signal = 1; w_name = "GREEN";  }}
                else if (CheckWeapon("Shotgun"))     {{ signal = 2; w_name = "RED";    }}
                else if (CheckWeapon("Chaingun"))    {{ signal = 3; w_name = "YELLOW"; }}
                else if (CheckWeapon("PlasmaRifle")) {{ signal = 4; w_name = "BLUE";   }}

                if (signal != 0) {{
                    lm_flash_signal_global = signal;
                    int fr=0, fg=0, fb=0;
                    if (signal == 1) {{ fr=0;   fg=255; fb=0;   }}
                    if (signal == 2) {{ fr=255; fg=0;   fb=0;   }}
                    if (signal == 3) {{ fr=255; fg=255; fb=0;   }}
                    if (signal == 4) {{ fr=0;   fg=0;   fb=255; }}

                    g_flash_r = fr;
                    g_flash_g = fg;
                    g_flash_b = fb;
                    g_flash_timer = 20;

                    HudMessage(s:"Signaling: ", s:w_name; HUDMSG_FADEOUT, 2, CR_WHITE, 0.5, 0.8, 1.0, 0.5);
                }}
            }}
            old_btns = btns;
            Delay(1);
        }}
    }}
    """

        acs.add_global_code(maze_logic_script)

        source_acs = acs.to_code()
        builder.map_data.scripts = source_acs
        try:
            builder.map_data.behavior = acs.compile()
        except Exception as e:
            print(f"ACS Compile Warning: {e}")
            if hasattr(e, "stderr") and e.stderr:
                print(f"ACC Stderr: {e.stderr}")

        builder.build(output_path)
        print(f"Built: {output_path}")


if __name__ == "__main__":
    LavaMazeScenario().generate("examples/benchmark/output/lava_maze.wad")
