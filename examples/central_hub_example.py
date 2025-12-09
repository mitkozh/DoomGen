import os
from doomgen import MapBuilder, ThingType

def main():
    print("Generating Central Hub Map with Builder...")
    
    # 1. Initialize the Builder
    builder = MapBuilder(seed=42)

    # 2. Add Rooms
    # Central Hub: High ceiling, nice floor
    builder.add_room(
        name="central_hub", 
        x=0, y=0, 
        width=256, 
        floor_height=0, 
        ceiling_height=192, 
        floor_texture="FLOOR4_8", 
        ceiling_texture="CEIL3_5"
    )
    
    # Slime Pit: Lower floor, damaging nukage
    builder.add_room(
        name="slime_pit", 
        x=-600, y=400, 
        width=180, 
        floor_height=-16, 
        floor_texture="NUKAGE1", 
        special=16 # Damage 20%
    )
    
    # Hell Keep: Higher floor, rocky
    builder.add_room(
        name="hell_keep", 
        x=600, y=400, 
        width=200, 
        floor_height=32, 
        floor_texture="RROCK19",
        ceiling_texture="FLOOR6_1"
    )
    
    # Tech Lab: Standard techbase
    builder.add_room(
        name="tech_lab", 
        x=0, y=-600, 
        width=160, 
        floor_height=0, 
        ceiling_texture="TLITE6_4"
    )

    # 3. Add Corridors
    # Connect hub to others with doors at the hub side
    builder.add_corridor("central_hub", "slime_pit", width=96, style="wavy", door_a=True)
    builder.add_corridor("central_hub", "hell_keep", width=112, style="wavy", door_a=True)
    builder.add_corridor("central_hub", "tech_lab", width=80, style="straight", door_a=True)

    # 4. Add Things using the new High-Level API
    # This places things randomly within the room's area
    builder.add_thing("central_hub", ThingType.PLAYER1_START, count=1, angle=90)
    builder.add_thing("slime_pit", ThingType.SHOTGUN_GUY, count=3)
    builder.add_thing("hell_keep", ThingType.IMP, count=5)
    builder.add_thing("tech_lab", ThingType.DEMON, count=2)

    # 5. Advanced Usage: Step-by-step build
    # Instead of calling builder.build(), we call the steps manually.
    # This allows us to intervene and use the lower-level APIs (Integration).
    
    print("Step 1: Generating Geometry...")
    builder.generate_geometry()
    
    print("Step 2: Translating to Doom Format...")
    map_data = builder.translate("MAP01")
    
    # 6. Manual Intervention (Integration)
    # We can now access the raw DoomMapData object to add custom elements
    # that the high-level API might not support yet.
    print("Step 3: Manual Intervention - Adding a Cyberdemon...")
    map_data.add_thing(x=0, y=0, thing_type=ThingType.CYBERDEMON, angle=270)

    # 7. Save
    output_path = os.path.join("examples", "output", "central_hub.wad")
    builder.save(output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()