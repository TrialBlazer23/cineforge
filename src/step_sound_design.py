import argparse
import json
import os

def generate_sound_effects(
    narrative_schema_path: str,
    output_dir: str
):
    """Generates placeholder sound effects based on narrative schema."""

    with open(narrative_schema_path, "r") as f:
        schema = json.load(f)

    scenes = schema.get("scenes", [])

    if not scenes:
        print("No scenes found in the narrative schema.")
        return

    os.makedirs(output_dir, exist_ok=True)

    sound_effect_keywords = {
        "door": "door_creak.mp3",
        "footsteps": "footsteps.mp3",
        "car": "car_pass_by.mp3",
        "rain": "rain_loop.mp3",
        "explosion": "explosion.mp3",
        "wind": "wind_howl.mp3",
        "scream": "scream.mp3",
        "gunshot": "gunshot.mp3",
        "water": "water_splash.mp3",
        "fire": "fire_crackling.mp3",
    }

    for i, scene in enumerate(scenes):
        scene_num = i + 1
        scene_summary = scene.get("summary", "").lower()
        
        found_sfx_count = 0
        for keyword, sfx_filename in sound_effect_keywords.items():
            if keyword in scene_summary:
                found_sfx_count += 1
                sfx_output_path = os.path.join(output_dir, f"scene_{scene_num:03d}_sfx_{found_sfx_count:03d}_{sfx_filename}")
                
                # Create a placeholder empty MP3 file
                with open(sfx_output_path, "wb") as f:
                    f.write(b'') # Empty file

                print(f"Placeholder sound effect '{sfx_filename}' generated for Scene {scene_num} at {sfx_output_path}")

    print("\nSound effect generation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate placeholder sound effects.")
    parser.add_argument("narrative_schema_path", help="Path to the narrative schema JSON file.")
    parser.add_argument("--output_dir", default="output/sound_effects", help="Directory to save the generated sound effects.")
    args = parser.parse_args()

    generate_sound_effects(args.narrative_schema_path, args.output_dir)
