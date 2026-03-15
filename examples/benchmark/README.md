# DoomGen Benchmark Scenarios

This directory contains several benchmark scenarios for Multi-Agent Reinforcement Learning (MARL), designed to test different aspects of agent coordination, navigation, and combat.

## Scenario Overviews

### Ammo Carrier (`ammo_carrier.py`)
This scenario features a cooperative role-based mission where one player acts as a stationary "Defender" while others are "Runners". The Defender is anchored in the center with heavy firepower but limited ammunition, while Runners are fast and unarmed, tasked with fetching ammo from outlying depots. Successful gameplay requires constant communication and efficient delivery cycles to keep the Defender from being overwhelmed by waves of enemies. This benchmark tests role specialization, resource management, and team-based priority shifting.

### Armory Siege (`armory_siege.py`)
In this defensive scenario, players are tasked with protecting a central "Defense Core" entity from relentless waves of melee-based monsters. The environment includes a central hub connected via corridors to specialized supply rooms for weapons, ammunition, and medical supplies. The doors to the supply rooms are time-gated, so agents have to be careful when making runs not to get stuck leaving the core helpless. Players must balance defending the core with making risky supply runs to upgrade their arsenal and restore health. It primarily tests combat skill, area control, and the strategic management of supply lines. It also test whether agents can swap roles betweeen defending and rushing.

### Co-op Puzzle (`coop_puzzle.py`)
This benchmark presents a series of linear zones where two players are physically separated but must interact through windows and partitions. Progress is gated by pressure plates that open doors for the partner on the opposite side, requiring synchronized movements and coordinated timing. Some puzzles feature "AND" logic, necessitating both players to occupy specific spots simultaneously to advance. It tests synchronization, communication density, and multi-agent logical coordination.

### Rhythm Sync (`rhythm_sync.py`)
This scenario is a progressive rhythm-synchronization benchmark where two agents are separated into parallel rooms and cannot exchange explicit messages. Each stage contains wall switches that must be pressed simultaneously within a strict tolerance window; pressing alone immediately fails the episode. The environment emits a visual tick (red flash) as a shared timing signal, starting with a fixed 4-second rhythm, then moving to a jittered $4s \pm 1s$ rhythm, and finally a silent-partner variant where only Agent A receives the tick while Agent B must infer timing by observing Agent A through a window. It tests implicit coordination, temporal prediction, and adaptation to partial observability.

### Lava Maze (`lava_maze.py`)
Lava Maze is an asymmetric cooperative mission where one agent navigates a procedural grid of pillars over a lava pit while another agent watches from a high-altitude spectator stand. The navigator has an obstructed view and must rely on the spectator's ability to trigger light signals (color-coded flashes) to determine the safe path. The maze is dynamic, with pillars rising or sinking based on the navigator's position and the spectator's inputs. This tests asymmetric communication, spatial reasoning, and trust between agents.

### Lava Pit (`lavapit.py`)
A high-stakes platforming scenario that requires players to traverse a vast lava sea using a series of isolated platforms and retractable bridges. Bridges are activated by pressure plates located on nearby platforms, requiring one player to hold a position so their partner can cross. It tests precise spatial navigation, timing-based coordination, and altruistic behavior in multi-agent systems.

### Platform Chain (`platform_chain.py`)
Inspired by the game *Chained Together*, this scenario features a massive serpentine path of 120 levels where players are physically linked by a virtual chain. Agents must coordinate their movement to stay within a maximum distance or risk being snapped back, with visual feedback (color-coded screen fades) indicating chain tension. The vertical ascent is fraught with diverse hazards, including moving polyobject panels, dynamic lifts, and lethal vertical crushers. It tests long-horizon planning, precision platforming, and tight movement synchronization in a vast, hazardous state space.

### Smart Enemies (`smart_enemies.py`)
Set in a circular arena with damaging toxic floors, this scenario focuses on combat against enemies with adaptive AI behavior. These "hunted" demons change their speed and aggression levels based on the proximity and density of the players, punishing many agents attacking the same enemy at once. Players must manage their health and ammo by looting defeated enemies while avoiding environmental damage and navigating obstacles. It tests dynamic combat adaptation, team spacing, and tactical prioritization.

### Co-op CQB (`coop_cqb.py`)
This is a tight close-quarters battle scenario for marines operating in narrow interconnected corridors. At spawn, one marine is shotgun-only, one is plasma-only. The team must survive fast rushing shooter specialist while avoiding severe friendly-fire mistakes. Tere are also static civilians mixed into combat space, forcing agents to balance lethality with line-of-fire discipline. The objective is to kill as many enemies as possible. Civilian collateral immediately fails the episode.

### Common Harvest Doom (`common_harvest.py`)
Inspired by MeltingPot 2.0's "Common Harvest" scenario - the social dilemma benchmark. Two agents share an ammo pool in a central combat arena connected to four separate ammo rooms. Enemies spawn continuously in the arena, and defeating them yields rewards. However, ammo only spawns inside the outlying rooms when a player is physically present, and pickups benefit both agents equally. To collect ammo, an agent must leave the arena, traverse a corridor that blocks line-of-sight to enemies, and sacrifice their own combat time to restock. If both agents selfishly remain in the arena to score kills, the shared ammo pool depletes and all progress halts. At least one agent must routinely act altruistically by restocking—analogous to cleaning the river in the original MeltingPot scenario. The environment provides global RL observations for cumulative kills, shared ammo, world ammo items, and live enemy counts. It tests social dilemma resolution, altruistic behavior, and shared resource management.