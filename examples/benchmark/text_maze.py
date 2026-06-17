import random
from typing import Any, Dict

from doomgen.abstraction.layout import ConnectionType
from doomgen.batch.scenario import Scenario
from doomgen.builder import ProceduralMapBuilder
from doomgen.doom.things import ThingType
from doomgen.logic.acs_builder import ACSBuilder


class TextMazeScenario(Scenario):
    """
    Two-player cooperative maze with text-based communication.

    Player 1 (Navigator) moves through a procedural lava maze.
    Player 2 (Guide) observes from stands and broadcasts direction
    tokens via the notifications buffer to guide navigation.

    Curriculum: 2 direction tokens -> 3 -> 4 as levels progress.
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "seed": 42,
            "physical_size": 18,
            "cell_size": 128,
            "initial_maze_size": 4,
            "max_maze_size": 14,
            "lava_damage": 35,
            "lava_depth": 64,
            "step_tics": 12,
            "step_cooldown_tics": 4,
            "dir_2_levels": 3,
            "dir_3_levels": 3,
        }

    def generate(self, output_path: str) -> None:
        cfg = self.config
        PHYSICAL_SIZE = int(cfg["physical_size"])
        CELL_SIZE = int(cfg["cell_size"])
        INITIAL_MAZE_SIZE = int(cfg.get("initial_maze_size", 4))
        MAX_MAZE_SIZE = int(cfg.get("max_maze_size", 14))
        LAVA_DAMAGE = int(cfg["lava_damage"])
        LAVA_DEPTH = int(cfg.get("lava_depth", 64))
        STEP_TICS = int(cfg.get("step_tics", 12))
        STEP_COOLDOWN_TICS = int(cfg.get("step_cooldown_tics", 4))
        DIR_2_LEVELS = int(cfg.get("dir_2_levels", 3))
        DIR_3_LEVELS = int(cfg.get("dir_3_levels", 3))
        seed = cfg["seed"] if cfg["seed"] is not None else random.randint(0, 999999)

        MAZE_WIDTH_UNITS = PHYSICAL_SIZE * CELL_SIZE
        OFFSET_X = -(MAZE_WIDTH_UNITS // 2)
        OFFSET_Y = -(MAZE_WIDTH_UNITS // 2)

        builder = ProceduralMapBuilder(
            bounds=(-2400, -2400, 2400, 2400),
            num_seeds=24000,
            seed=seed,
        )

        # --- Lava pit ---
        builder.add_area(
            "LavaPit",
            shape=(0, 0, 4400, 4400),
            floor_height=-LAVA_DEPTH,
            ceiling_height=800,
            floor_texture="LAVA1",
            mode="overwrite",
            light_level=255,
            tag=99,
        )

        # --- Perimeter stands ---
        STANDS_HEIGHT = 350
        STANDS_THICKNESS = 100
        STANDS_INNER = (MAZE_WIDTH_UNITS // 2) + 64

        pos_y = STANDS_INNER + STANDS_THICKNESS / 2
        stands_width = 2 * STANDS_INNER + 2 * STANDS_THICKNESS
        builder.add_area("Stands_N", shape=(0, pos_y, stands_width, STANDS_THICKNESS), floor_height=STANDS_HEIGHT, ceiling_height=1024, mode="overwrite", tag=201, wall_texture="S_YELLOW", light_level=255)
        builder.add_area("Stands_S", shape=(0, -pos_y, stands_width, STANDS_THICKNESS), floor_height=STANDS_HEIGHT, ceiling_height=1024, mode="overwrite", tag=203, wall_texture="S_BLUE", light_level=255)

        pos_x = STANDS_INNER + STANDS_THICKNESS / 2
        h_span = 2 * STANDS_INNER + 2 * STANDS_THICKNESS
        builder.add_area("Stands_E", shape=(pos_x, 0, STANDS_THICKNESS, h_span), floor_height=STANDS_HEIGHT, ceiling_height=1024, mode="overwrite", tag=200, wall_texture="S_GREEN", light_level=255)
        builder.add_area("Stands_W", shape=(-pos_x, 0, STANDS_THICKNESS, h_span), floor_height=STANDS_HEIGHT, ceiling_height=1024, mode="overwrite", tag=202, wall_texture="S_RED", light_level=255)

        # --- Grid cells ---
        base_tag = 1000
        center_idx = PHYSICAL_SIZE // 2
        for py in range(PHYSICAL_SIZE):
            for px in range(PHYSICAL_SIZE):
                cx = OFFSET_X + (px * CELL_SIZE) + (CELL_SIZE // 2)
                cy = OFFSET_Y + (py * CELL_SIZE) + (CELL_SIZE // 2)
                tag = base_tag + (py * PHYSICAL_SIZE + px)
                if px == center_idx and py == center_idx:
                    f_tex, f_h = "FLOOR4_8", 0
                else:
                    f_tex, f_h = "LAVA1", -LAVA_DEPTH
                builder.add_area(
                    f"Grid_{px}_{py}",
                    shape=(cx, cy, CELL_SIZE, CELL_SIZE),
                    floor_height=f_h,
                    ceiling_height=1024,
                    tag=tag,
                    mode="overwrite",
                    floor_texture=f_tex,
                    wall_texture="S_WALL",
                    light_level=255,
                )

        # Stands connectivity
        builder.connect_adjacent("Stands_N", "Stands_E", ConnectionType.OPEN)
        builder.connect_adjacent("Stands_E", "Stands_S", ConnectionType.OPEN)
        builder.connect_adjacent("Stands_S", "Stands_W", ConnectionType.OPEN)
        builder.connect_adjacent("Stands_W", "Stands_N", ConnectionType.OPEN)

        barrier_args = {"blocking": True, "middle_texture": "-"}
        for stand in ("Stands_N", "Stands_S", "Stands_E", "Stands_W"):
            builder.connect_adjacent(stand, "LavaPit", ConnectionType.WINDOW, **barrier_args)

        # All grid cells connected (ACS carve constrains to active directions)
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

        # Player starts
        p1_x = OFFSET_X + (center_idx * CELL_SIZE) + (CELL_SIZE // 2)
        p1_y = OFFSET_Y + (center_idx * CELL_SIZE) + (CELL_SIZE // 2)
        builder.add_thing(ThingType.PLAYER1_START, x=p1_x, y=p1_y, angle=0)

        p2_y = -(STANDS_INNER + (STANDS_THICKNESS // 2))
        builder.add_thing(ThingType.PLAYER2_START, x=0, y=p2_y, angle=90)

        acs = ACSBuilder()
        acs.add_include("zcommon.acs")

        acs.add_map_var("level_clear_lock", initial=1)

        acs.add_global_var("tm_p1_grid_x",      1, "int")
        acs.add_global_var("tm_p1_grid_y",      2, "int")
        acs.add_global_var("tm_goal_grid_x",    3, "int")
        acs.add_global_var("tm_goal_grid_y",    4, "int")
        acs.add_global_var("tm_maze_size",      5, "int")
        acs.add_global_var("tm_level",          6, "int")
        acs.add_global_var("tm_direction_count", 7, "int")
        acs.add_global_var("tm_can_see",        8, "int")

        acs.scripts = []

        STANDS_RADIUS_UNITS = int(STANDS_INNER + STANDS_THICKNESS / 2)

        maze_logic_script = f"""
    #define MAP_WIDTH {PHYSICAL_SIZE}
    #define CELL_SIZE {CELL_SIZE}
    #define BASE_TAG {base_tag}
    #define MAX_TILES {MAX_MAZE_SIZE}
    #define PLATFORM_RADIUS {STANDS_RADIUS_UNITS}
    #define TM_STEP_TICS {STEP_TICS}
    #define TM_STEP_COOLDOWN_TICS {STEP_COOLDOWN_TICS}
    #define DIR_2_LEVELS {DIR_2_LEVELS}
    #define DIR_3_LEVELS {DIR_3_LEVELS}

    int max_unlocked_size = {INITIAL_MAZE_SIZE};
    int current_maze_size = {INITIAL_MAZE_SIZE};
    int current_start_tag = 0;
    int current_end_tag = 0;

    int g_start_x = MAP_WIDTH / 2;
    int g_start_y = MAP_WIDTH / 2;

    // Bit-packed safe cells for the current maze
    int maze_bits_chunk[3];

    // Current direction vocabulary state
    int direction_bits = 3;  // bit 0=LEFT, 1=RIGHT, 2=SOUTH, 3=NORTH
    str dir_tokens[4];

    function int get_tag(int x, int y) {{
        return BASE_TAG + (y * MAP_WIDTH + x);
    }}

    function int get_world_x(int gx) {{
        return {OFFSET_X} + (gx * {CELL_SIZE}) + ({CELL_SIZE} / 2);
    }}

    function int get_world_y(int gy) {{
        return {OFFSET_Y} + (gy * {CELL_SIZE}) + ({CELL_SIZE} / 2);
    }}

    function int cell_is_safe(int x, int y) {{
        if (x < 0 || x >= MAP_WIDTH || y < 0 || y >= MAP_WIDTH) return FALSE;
        int bit_idx = y * MAP_WIDTH + x;
        int chunk = bit_idx / 27;
        int shift = bit_idx % 27;
        int mask = 1 << shift;
        if (chunk == 0) return ((maze_bits_chunk[0] & mask) != 0);
        if (chunk == 1) return ((maze_bits_chunk[1] & mask) != 0);
        if (chunk == 2) return ((maze_bits_chunk[2] & mask) != 0);
        return FALSE;
    }}

    function void reset_map(int keep_tag) {{
        int t;
        int i;
        for (i = 0; i < MAP_WIDTH * MAP_WIDTH; i++) {{
            t = BASE_TAG + i;
            if (t != keep_tag) {{
                Floor_MoveToValue(t, 2048, -{LAVA_DEPTH}, 0);
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
        Light_ChangeToValue(tag, 255);
        if (x >= 0 && x < MAP_WIDTH && y >= 0 && y < MAP_WIDTH) {{
            int bit_idx = y * MAP_WIDTH + x;
            int chunk = bit_idx / 27;
            int shift = bit_idx % 27;
            if (chunk < 3) maze_bits_chunk[chunk] = maze_bits_chunk[chunk] | (1 << shift);
        }}
    }}

    function void init_direction_tokens() {{
        // Called after direction_bits is set
        dir_tokens[0] = "LEFT";
        dir_tokens[1] = "RIGHT";
        dir_tokens[2] = "SOUTH";
        dir_tokens[3] = "NORTH";
    }}

    function int count_directions() {{
        int count = 0;
        int i;
        for (i = 0; i < 4; i++) {{
            if (direction_bits & (1 << i)) count++;
        }}
        return count;
    }}

    // Script placeholders -- filled in Tasks 2-4
    script 1 OPEN {{ }}
    script "GenerateMaze" (int sx, int sy, int size) {{ }}
    script 2 ENTER {{ }}
    script 3 ENTER {{ }}
    script "EndGame" (void) {{ }}
    script 999 DEATH {{ }}
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
    TextMazeScenario().generate("examples/benchmark/output/text_maze.wad")
