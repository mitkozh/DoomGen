
import random
import math
from typing import Dict, Any, List
from doomgen.builder import ProceduralMapBuilder
from doomgen.abstraction.layout import ConnectionType
from doomgen.logic.acs_builder import ACSBuilder, ScriptType
from doomgen.batch.scenario import Scenario
from doomgen.doom.things import ThingType
import subprocess
import os

class AmmoCarrierScenario(Scenario):
    """
    Cooperative scenario: One immobile shooter, multiple ammo carriers.
    Role-based Gameplay:
    - Shooter (Red): Stuck in center, must defend against waves. Needs ammo.
    - Carrier (Green): Fast, no weapons. Must run to depots, grab ammo, and bring it to shooter.
    """
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            'map_radius': 1200,
            'num_depots': 6,
            'enemy_density': 1.0,
            'seed': None,
        }
        
    def generate(self, output_path: str) -> None:
        cfg = self.config
        seed = cfg['seed'] if cfg['seed'] is not None else random.randint(0, 999999)
        random.seed(seed)
        
        radius = cfg['map_radius']
        bounds_pad = 512
        bounds = (-(radius+bounds_pad), -(radius+bounds_pad), (radius+bounds_pad), (radius+bounds_pad))
        
        # 1. Initialize Builder
        # High seed count for smooth walls and organic corridors
        builder = ProceduralMapBuilder(
            bounds=bounds,
            num_seeds=8000, 
            seed=seed
        )

        # --- DECORATE (Custom Actors) ---
        decorate_str = """
        // Custom monsters that don't drop items (so carriers MUST fetch ammo)
        // and fade out to avoid clutter
        ACTOR BenchZombie : Zombieman 15001 {
          DropItem "None"
          States {
          Death:
            POSS H 0 ACS_ExecuteAlways(998, 0)
            POSS H 5
            POSS I 5 A_Scream
            POSS J 5 A_NoBlocking
            POSS K 5
            POSS L 5
            POSS M 5
            POSS N 1 A_FadeOut(0.1)
            Wait
          }
        }
        ACTOR BenchShotgunGuy : ShotgunGuy 15002 {
          DropItem "None"
          States {
          Death:
            SPOS H 0 ACS_ExecuteAlways(998, 0)
            SPOS H 5
            SPOS I 5 A_Scream
            SPOS J 5 A_NoBlocking
            SPOS K 5
            SPOS L 5
            SPOS L 1 A_FadeOut(0.1)
            Wait
          }
        }
        ACTOR BenchImp : DoomImp 15003 {
          States {
          Death:
            TROO I 0 ACS_ExecuteAlways(998, 0)
            TROO I 8
            TROO J 8 A_Scream
            TROO K 6
            TROO L 6 A_NoBlocking
            TROO M 5
            TROO M 1 A_FadeOut(0.1)
            Wait
          }
        }
        ACTOR BenchDemon : Demon 15004 {
          States {
          Death:
            SARG I 0 ACS_ExecuteAlways(998, 0)
            SARG I 8
            SARG J 8 A_Scream
            SARG K 4
            SARG L 4 A_NoBlocking
            SARG M 4
            SARG N 5
            SARG N 1 A_FadeOut(0.1)
            Wait
          }
        }
        """
        builder.wad_writer.add_lump("DECORATE", decorate_str.encode('utf-8'))
        
        # --- ACS Logic ---
        acs = ACSBuilder()
        acs.add_include("zcommon.acs")
        acs.add_global_var("ac_shooter_ammo_global", 41, "int")
        acs.add_global_var("ac_carrier_deliveries_global", 42, "int")
        acs.add_global_var("ac_world_ammo_packs_global", 43, "int")
        acs.add_global_var("ac_alive_enemies_global", 44, "int")
        acs.add_global_var("ac_low_ammo_alert_global", 45, "int")
        
        # Script 1: Player Setup & Role Assignment
        script_setup = """
        int pid = PlayerNumber();
        int tid;
        
        // Setup HUD script (Script 10)
        ACS_ExecuteAlways(10, 0, 0, 0, 0);

        if (pid == 0) {
            // --- SHOOTER ROLE ---
            tid = 100;
            Thing_ChangeTID(0, tid);
            
            // Teleport to Center (TID 10-14)
            int dest = 10 + Random(0,4);
            SetActorPosition(0, GetActorX(dest), GetActorY(dest), GetActorZ(dest), 0);
            
            // Attributes: Heavy, Slow, Healthy
            SetActorProperty(0, APROP_Health, 200);
            SetActorProperty(0, APROP_SpawnHealth, 200);
            SetActorProperty(0, APROP_Speed, 0.0);
            SetActorProperty(0, APROP_Mass, 0x7FFFFFFF); 
            
            // Gear: Chaingun, limited ammo
            ClearInventory();
            SetAmmoCapacity("Clip", 10000); // Uncapped ammo
            GiveInventory("Chaingun", 1);
            GiveInventory("Clip", 100); // Start with a decent amount
            GiveInventory("GreenArmor", 1);
            SetWeapon("Chaingun");
            
            // Start immobility loop
            ACS_ExecuteAlways(5, 0, 0, 0, 0); 
            
        } else {
            // --- CARRIER ROLE ---
            tid = 200 + pid;
            Thing_ChangeTID(0, tid);
            
            // Teleport to Outskirts (TID 20-29)
            int dest2 = 20 + Random(0,9);
            SetActorPosition(0, GetActorX(dest2), GetActorY(dest2), GetActorZ(dest2), 0);
            
            // Attributes: Fast, Fragile
            SetActorProperty(0, APROP_Speed, 1.5); // Very fast
            ClearInventory();
            // No Weapons - Pacifist run
            
            // Start carrier delivery loop
            ACS_ExecuteAlways(2, 0, 0, 0, 0);
        }
        """
        acs.add_script(ScriptType.ENTER, script_setup, number=1)
        acs.add_script(ScriptType.RESPAWN, script_setup, number=3)
        
        # Script 2: Carrier Delivery Loop
        # Giving ammo to shooter when close
        script_carrier = """
        while (TRUE) {
            // Calculate distance to Shooter (TID 100)
            int x = GetActorX(0) - GetActorX(100);
            int y = GetActorY(0) - GetActorY(100);
            
            int dx = x >> 16;
            int dy = y >> 16;
            int dist_sq = dx*dx + dy*dy; 
            
            // 256 units radius approx = 65536
            if (dist_sq < 65536) {
                int clips = CheckInventory("Clip");
                if (clips > 0) {
                    TakeInventory("Clip", clips);
                    // Give to shooter
                    GiveActorInventory(100, "Clip", clips);
                    ac_carrier_deliveries_global++;
                    AmbientSound("misc/pickup", 127);
                    
                    // Visual feedback
                    SpawnSpotFacing("TeleportFog", 0, 0);
                }
            }
            Delay(4);
        }
        """
        acs.add_script(ScriptType.VOID, script_carrier, number=2)
        
        # Script 10: Persistent HUD
        # Simple squares above HUD
        script_hud = """
        while (TRUE) {
            SetFont("SMALLFONT");
            int tid = ActivatorTID();
            
            // Determine Role
            if (tid == 100) { 
                // SHOOTER HUD
                
                // Role Indicator (Red Square)
                HudMessage(s:"[ DEFENDER ]"; 
                    HUDMSG_PLAIN, 1, CR_RED, 0.5, 0.82, 0.1);
                
                // Vital Stats
                int hp = GetActorProperty(0, APROP_Health);
                int ammo = CheckInventory("Clip");
                str ammoColor = "\\cC"; // Gold
                if (ammo < 20) ammoColor = "\\cR"; // Red warning
                
                HudMessage(s:"HP: ", d:hp, s:"  ", s:ammoColor, s:"AMMO: ", d:ammo; 
                    HUDMSG_PLAIN, 2, CR_WHITE, 0.5, 0.85, 0.1);
                    
            } else {
                // CARRIER HUD
                
                // Role Indicator (Green Square)
                HudMessage(s:"[ RUNNER ]"; 
                    HUDMSG_PLAIN, 1, CR_GREEN, 0.5, 0.82, 0.1);
                
                // Carry Status
                int c_ammo = CheckInventory("Clip");
                
                if (c_ammo > 0) {
                    HudMessage(s:"\\cD", d:c_ammo; 
                        HUDMSG_PLAIN, 2, CR_WHITE, 0.5, 0.85, 0.1);
                } else {
                    HudMessage(s:"\\cR EMPTY - FIND AMMO"; 
                        HUDMSG_PLAIN, 2, CR_WHITE, 0.5, 0.85, 0.1);
                }
            }
            Delay(1);
        }
        """
        acs.add_script(ScriptType.VOID, script_hud, number=10)

        # Script 4: Enemy Spawner
        script_spawner = """
        int spot_tid_base = 1000;
        int max_spots = 10; // Adjust max spots based on layout
        
        // Initial Grace Period
        Delay(35 * 15); // Wait 15 seconds before first wave
        
        while (TRUE) {
            // Wave Logic
            Delay(35 * 6); // Wait 6 seconds
            
            int spawned = 0;
            for (int i=0; i<max_spots; i++) {
                 if (Random(0, 3) == 0) { // 25% chance per spot
                     int spot_tid = spot_tid_base + i; 
                     int r = Random(0, 10);
                     str type = "BenchZombie";
                     if (r > 5) type = "BenchImp";
                     if (r > 8) type = "BenchShotgunGuy";
                     if (r == 10) type = "BenchDemon";
                     
                     // Spawn if spot exists
                     if (ThingCount(T_NONE, spot_tid) > 0) {
                        SpawnSpotFacing(type, spot_tid, 700);
                        spawned++;
                     }
                 }
            }
            ac_alive_enemies_global = ThingCount(T_NONE, 700);
            if (spawned > 0) {
                // Alert if wave is huge?
            }
        }
        """
        acs.add_script(ScriptType.OPEN, script_spawner, number=4)

        acs.add_script(ScriptType.OPEN, """
        ac_shooter_ammo_global = 0;
        ac_carrier_deliveries_global = 0;
        ac_world_ammo_packs_global = 0;
        ac_alive_enemies_global = 0;
        ac_low_ammo_alert_global = 0;

        while (TRUE) {
            int shooter_ammo = CheckActorInventory(100, "Clip");
            ac_shooter_ammo_global = shooter_ammo;
            if (shooter_ammo < 40) {
                ac_low_ammo_alert_global = 1;
            } else {
                ac_low_ammo_alert_global = 0;
            }
            ac_alive_enemies_global = ThingCount(T_NONE, 700);
            Delay(4);
        }
        """, number=7)

        # Script 5: Force Freeze
        acs.add_script(ScriptType.VOID, "SetActorVelocity(0, 0, 0, 0, FALSE, FALSE); while(TRUE) { SetActorVelocity(0, 0, 0, 0, FALSE, FALSE); Delay(1); }", number=5)
        
        # Script 998: Kill Reward
        acs.add_script(ScriptType.VOID, """
        SetActivatorToTarget(0); // Killer
        if (PlayerNumber() == 0) { // If Shooter killed it
             // Heal Shooter
             GiveActorInventory(100, "HealthBonus", 10);
             
             // Heal all potential Carriers (Players 1-7)
             for (int p = 1; p < 8; p++) {
                 if (PlayerInGame(p)) {
                     GiveActorInventory(200 + p, "HealthBonus", 10);
                 }
             }
        }
        """, number=998)
        
        # Script 6: Ammo Spawner (Dynamic Respawn with Cap)
        # Injected by Python Loop below to set correct num_ammo_spots
                
        # --- MAP LAYOUT GENERATION ---
        
        # 1. CENTRAL HUB
        # A medium sized octagonal shapes
        builder.add_area("Hub", shape=(0, 0, 700, 700), floor_height=0, ceiling_height=256, 
                         floor_texture="FLOOR4_8", wall_texture="STONE3")
        
        # Add pillars inside Hub using 'overwrite' mode
        # This carves out areas for cover
        pillar_dist = 200
        builder.add_area("Pillar_NE", shape=(pillar_dist, pillar_dist, 64, 64), mode="overwrite", 
                         floor_height=0, ceiling_height=0, wall_texture="STONE3", floor_texture="FLOOR4_8") # Floor=Ceil = Solid Column effect if valid
        # Actually standard Doom way for pillars is just a void or a sector with unique height.
        # Let's make raised platforms instead for cover
        # (Though technically distinct areas, keeping them flat-ish helps AI)
        builder.add_area("Platform_NE", shape=(pillar_dist, pillar_dist, 96, 96), mode="overwrite",
                         floor_height=0, floor_texture="FLAT19")
        builder.add_area("Platform_NW", shape=(-pillar_dist, pillar_dist, 96, 96), mode="overwrite",
                         floor_height=0, floor_texture="FLAT19")
        builder.add_area("Platform_SE", shape=(pillar_dist, -pillar_dist, 96, 96), mode="overwrite",
                         floor_height=0, floor_texture="FLAT19")
        builder.add_area("Platform_SW", shape=(-pillar_dist, -pillar_dist, 96, 96), mode="overwrite",
                         floor_height=0, floor_texture="FLAT19")

        # 2. SATELLITE DEPOTS (Ammo Sources)
        depots = []
        num_depots = cfg['num_depots']
        depot_radius = radius * 0.8
        
        # Ammo Spot Logic
        ammo_spot_base = 3000
        total_ammo_spots = 0
        
        for i in range(num_depots):
            angle = (2 * math.pi * i) / num_depots
            dx = int(math.cos(angle) * depot_radius)
            dy = int(math.sin(angle) * depot_radius)
            
            name = f"Depot_{i}"
            # Create Depot
            builder.add_area(name, shape=(dx, dy, 400, 400), 
                             floor_height=0, ceiling_height=200, 
                             floor_texture="CEIL5_1", wall_texture="BROWN96")
            depots.append(name)
            
            # Connect to Hub (Spoke)
            # Use 'add_corridor' which pathfinds around the void
            builder.add_corridor("Hub", name, width=4, floor_texture="RROCK19")
            
            # 3. PLACEMENT IN DEPOT
            # Spawn Points for Enemies (TID 1000+)
            # Use safe=True to ensure it's on the navmesh
            pt = builder.get_random_point_in_area(name, safe=True)
            if pt:
                builder.add_thing("MAP_SPOT", pt[0], pt[1], tid=1000+i)
                
            # Ammo Clusters (Replaced by MapSpots for Dynamic Spawning)
            # 8 possible spawn spots per depot
            for _ in range(8):
                pt = builder.get_random_point_in_area(name, safe=True)
                if pt:
                    # Place MapSpot with sequential TID
                    builder.add_thing("MAP_SPOT", pt[0], pt[1], tid=ammo_spot_base + total_ammo_spots)
                    total_ammo_spots += 1
            
        # Add the Dynamic Spawner Script now that we know total_ammo_spots
        script_ammo_spawner = f"""
        int ammo_spot_base = 3000;
        int num_ammo_spots = {total_ammo_spots};
        int tid_ammo = 800;
        int max_ammo = 25; // Global Cap
        
        while(TRUE) {{
            // Count current ammo in the world
            int current_ammo = ThingCount(T_NONE, tid_ammo);
            ac_world_ammo_packs_global = current_ammo;
            
            if (current_ammo < max_ammo) {{
                // Try to spawn new ammo
                if (num_ammo_spots > 0) {{
                    int spot_index = Random(0, num_ammo_spots - 1);
                    int spot_tid = ammo_spot_base + spot_index;
                    
                    // Randomize type (80% Clip, 20% Box)
                    str type = "Clip";
                    if (Random(0,4) == 0) type = "ClipBox"; 
                    
                    // Spawn with TID 800 so we can count it
                    SpawnSpot(type, spot_tid, tid_ammo, 0);
                }}
            }}
            
            Delay(35 * 2); // Check every 2 seconds
        }}
        """
        acs.add_script(ScriptType.OPEN, script_ammo_spawner, number=6)
        
        # Compile ACS
        try:
            print("Compiling ACS...")
            compiled = acs.compile(acc_path="acc")
            if compiled:
                if hasattr(builder.map_data, 'behavior'):
                     builder.map_data.behavior = compiled
        except Exception as e:
            print(f"ACS Error: {e}")

        # 4. OUTER RING (Connectivity)
        # Connect depots to neighbors to creating a cycling path
        for i in range(num_depots):
            next_i = (i + 1) % num_depots
            curr_depot = depots[i]
            next_depot = depots[next_i]
            
            # Create a path between depots
            builder.add_corridor(curr_depot, next_depot, width=3, floor_texture="GRASS1")

        # 5. SPAWN POINTS setup
        # Shooter candidates in Hub
        for i in range(5):
            pt = builder.get_random_point_in_area("Hub", safe=True)
            if pt:
                builder.add_thing("MAP_SPOT", pt[0], pt[1], tid=10+i)
                
        # Carrier candidates in Depots or Hub outskirts
        for i in range(10):
            # Pick a random depot
            d_name = random.choice(depots)
            pt = builder.get_random_point_in_area(d_name, safe=True)
            if pt:
                builder.add_thing("MAP_SPOT", pt[0], pt[1], tid=20+i)

        # Standard Starts (required by engine)
        builder.add_thing(ThingType.PLAYER1_START, 0, 0)
        builder.add_thing(ThingType.PLAYER2_START, 64, 0)
        builder.add_thing(ThingType.PLAYER3_START, -64, 0)
        builder.add_thing(ThingType.PLAYER4_START, 0, 64)

        # --- Build ---
        builder.build(output_path)

if __name__ == "__main__":
    import sys
    
    # Ensure output dir exists
    out_dir = os.path.join("examples", "benchmark", "output")
    os.makedirs(out_dir, exist_ok=True)
    
    path = os.path.join(out_dir, "ammo_carrier.wad")
    print(f"Generating {path}...")
    
    scen = AmmoCarrierScenario()
    scen.generate(path)
    print("Done.")
