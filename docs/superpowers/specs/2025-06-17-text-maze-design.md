# Text Maze — Design Spec

## Overview

A two-player asymmetric benchmark where agents must learn to ground text tokens
to spatial meaning through emergent communication. One agent receives text
describing the other's movement and must broadcast directional text back to
guide navigation through a procedural lava maze.

## Core Problem

Both agents face the same learning problem from different sensory channels:

- **Guide (spectator)**: Receives text `"EAST"` while visually observing the
  Navigator move east → learns that `"EAST"` means "that direction."
- **Navigator**: Receives broadcast text `"EAST"` from Guide + lives the
  movement outcome → learns that `"EAST"` in the text buffer means "move that
  way."

Neither agent knows the token meanings a priori. The only supervision is the
shared goal (reach the goal tile) mediated through the game's reward signal.

## Curriculum (progressive direction vocabulary)

Vocabulary of **available safe directions** grows with `tm_level`. The Navigator
can always attempt movement in all 4 directions; the maze constrains which are
actually safe.

| Levels cleared | Safe directions | Tokens in play | Maze type |
|---------------|-----------------|----------------|-----------|
| 0-2           | 2               | `"EAST"`, `"WEST"` | 1D line along X |
| 3-5           | 3               | One axis excluded at random per generation | 2D grid, 3-axis |
| 6+            | 4               | `"NORTH"`, `"SOUTH"`, `"EAST"`, `"WEST"` | 2D grid, full |

Stage thresholds are configurable (`dir_2_levels`, `dir_3_levels`).

Maze generation for 2D stages uses the existing Lava Maze DFS carve algorithm
but constrains the carve to only the allowed directions for that stage.

## Agent Modalities

### Navigator (Player 1, TID 1000)
- **Visual**: First-person view from inside maze
- **Text buffer (input)**: Receives Guide's broadcast text from notifications buffer
- **Action**: FORWARD/BACK/MOVE_LEFT/MOVE_RIGHT mapped to NORTH/SOUTH/WEST/EAST
  grid movement. Always all 4 directions available; the maze constrains which are safe.
- **Mobility**: Free movement with step timer + cooldown, same as lava_maze_simple

### Guide (Player 2, TID 1001)
- **Visual**: Bird's-eye perimeter stand view (same as lava_maze)
- **Text buffer (input)**: Receives the direction the Navigator most recently moved
- **Action**: 4 binary buttons (ATTACK→EAST, USE→WEST, RELOAD→SOUTH, JUMP→NORTH).
  Pressing a button broadcasts that token via `PrintBold`.
- **Mobility**: Frozen on stand, auto-tracks Navigator position (same as lava_maze_simple script 3)

## Communication Protocol

1. Navigator completes a step in direction D
2. ACS `PrintBold`s the token for D (e.g. `"EAST"`) — broadcast to ALL clients'
   console, captured by each agent's notifications buffer
3. Guide reads `"EAST"` from their notifications buffer + visually confirms the movement
4. Guide presses button corresponding to `"EAST"` → ACS `PrintBold`s `"EAST"` broadcast
5. Navigator reads `"EAST"` from their notifications buffer → uses it as guidance for
   next step decision

Both agents see all text. Learning problem is attentional: each must learn which
tokens to act on for their role.

**Why `PrintBold` not `Print`:** In a networked ZDoom game, `Print` only sends
output to the script activator's client (gated by `CheckLocalView(consoleplayer)`).
`PrintBold` has no such gating — all connected clients receive the output, so
both the Guide and Navigator see every message in their notifications buffer.

## Map & Maze

- Uses existing lava_maze_simple 1D layout for stage 0 (single row of cells,
  east-west line over lava pit)
- Uses existing lava_maze 2D grid layout for stages 1+ (NxN pillars over lava)
- Perimeter stands for Guide — same elevated platforms
- Start cell always solid; goal cell marked with colored floor texture
- Lava damage for stepping off safe path = instant death (same as lava_maze_simple)

## Episode Flow

1. Maze generates at start position with current size + direction vocabulary
2. Navigator starts at center safe cell
3. Guide placed on opposite stand, auto-aiming at Navigator
4. Navigator moves freely with step-timer system (all 4 directions always available)
5. On each step completion, ACS `PrintBold`s the movement direction
6. Guide may broadcast a direction at any time via 4 binary buttons
7. Navigator reaching goal tile → level cleared, maze resets at larger size
8. Navigator stepping into lava → EndGame
9. Episode also ends on timeout (configurable)

## RL Telemetry (global ints)

| User var | Name | Purpose |
|----------|------|---------|
| USER1 | `tm_p1_grid_x` | Navigator current X |
| USER2 | `tm_p1_grid_y` | Navigator current Y |
| USER3 | `tm_goal_grid_x` | Goal X |
| USER4 | `tm_goal_grid_y` | Goal Y |
| USER5 | `tm_maze_size` | Current maze extent |
| USER6 | `tm_level` | Levels completed (curriculum progress) |
| USER7 | `tm_direction_count` | Active safe direction count (2/3/4) |
| USER8 | `tm_can_see` | Guide FOV check on Navigator |

## ViZDoom Config Requirements

```ini
notifications_buffer_enabled = true
available_buttons = { MOVE_FORWARD, MOVE_BACKWARD, MOVE_LEFT, MOVE_RIGHT, ATTACK, USE, RELOAD, JUMP }
```

The game must be launched with `+viz_notifications 1` in the game args (this
CVAR defaults to `false`). The PettingZoo wrapper's `configure_doom_game` should
include this in the host's `add_game_args`.

## Config (defaults)

```python
{
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
```

## Deviations from Existing Benchmarks

- **No HudMessage / image lumps**: All communication goes through `PrintBold` into
  the notifications buffer.
- **No weapons**: Guide does not fire weapons to signal. Binary buttons directly
  trigger `PrintBold` calls.
- **Notifications buffer must be enabled**: Config needs `notifications_buffer_enabled = true`
  AND `+viz_notifications 1` in game args (the CVAR defaults to false).
- **PrintBold, not Print**: `Print` is player-local in netgames; `PrintBold` broadcasts
  to all connected clients.

## Files

- `examples/benchmark/text_maze.py` — scenario generator
- `examples/benchmark/output/text_maze.wad` — generated WAD
