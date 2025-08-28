import os
import json
import argparse
import re
from src import utils
from api import (
    deconstruct_narrative,
    generate_screenplay_and_storyboard,
    synthesize_video_from_storyboard,
)

def main():
    """Main function to run the narrative-to-video pipeline."""
    # Load env vars from .env if present
    utils.load_env()

    with open("config.json", "r") as f:
        config = json.load(f)
        styles = list(config["styles"].keys())

    parser = argparse.ArgumentParser(description="Narrative to Video Pipeline")
    parser.add_argument("story_file", help="Path to the story file")
    # Defaults now provided from environment variables via utils.add_vertex_args semantics
    parser.add_argument("--project", default=os.environ.get("VERTEX_PROJECT_ID"), help="GCP project ID")
    parser.add_argument("--location", default=os.environ.get("VERTEX_LOCATION", "us-central1"), help="GCP location")
    parser.add_argument("--style", choices=styles, help="The visual style to use for the generated images.")
    parser.add_argument("--regenerate-shot", nargs=2, metavar=("SCENE", "SHOT"), help="Regenerate a specific shot (scene and shot number)")
    parser.add_argument("--delete-shot", nargs=2, metavar=("SCENE", "SHOT"), help="Delete a specific shot (scene and shot number)")
    parser.add_argument("--generate-scene", help="Generate a specific scene", type=int)

    args = parser.parse_args()
    
    story_name = os.path.splitext(os.path.basename(args.story_file))[0]
    storyboard_file = f"output/storyboard_text/{story_name}_storyboard.txt"
    project_settings_file = f"output/project_settings.json"

    if args.style:
        with open(project_settings_file, "w") as f:
            json.dump({"style": args.style}, f)

    if args.regenerate_shot:
        scene_number, shot_number = args.regenerate_shot
        try:
            with open(storyboard_file, "r") as f:
                storyboard_content = f.read()
            shot_regex = re.compile(r"SCENE " + scene_number + r", SHOT " + shot_number + r":\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
            shot_description = shot_regex.search(storyboard_content).group(1).strip()
            os.system(f'''python3 src/regenerate_shot.py {scene_number} {shot_number} "{shot_description}" --project={args.project} --location={args.location}''')
        except (FileNotFoundError, AttributeError) as e:
            print(f"Error: Could not find shot {shot_number} in scene {scene_number} of {storyboard_file}. {e}")
        return

    if args.delete_shot:
        scene_number, shot_number = args.delete_shot
        os.system(f"python3 src/delete_shot.py {scene_number} {shot_number}")
        return

    if args.generate_scene:
        print(f"\nGenerating scene {args.generate_scene}...")
        os.system(f"python3 src/generate_scene.py {storyboard_file} {args.generate_scene} --project={args.project} --location={args.location}")
        return

    # Step 1: Narrative Deconstruction
    print("Starting narrative deconstruction...")
    schema_file = deconstruct_narrative(args.story_file, args.project, args.location)
    print(f"Narrative schema saved to: {schema_file}")

    # Step 2: Screenplay and Storyboard Generation
    print("\nGenerating screenplay and storyboard...")
    screenplay_file, storyboard_file = generate_screenplay_and_storyboard(
        schema_file, args.project, args.location
    )
    print(f"Screenplay saved to: {screenplay_file}")
    print(f"Storyboard saved to: {storyboard_file}")

    # Step 3: Visual Asset Generation
    print("\nGenerating character portraits...")
    os.system(f"python3 src/generate_characters.py {schema_file} --project={args.project} --location={args.location}")

    print("\nGenerating environment plates...")
    os.system(f"python3 src/generate_environments.py {schema_file} --project={args.project} --location={args.location}")

    print("\nGenerating storyboard images...")
    os.system(f"python3 src/generate_storyboard_images.py {storyboard_file} --project={args.project} --location={args.location}")
    print("Visual assets generated.")

    # Step 4: Video Synthesis (Placeholder)
    print("\nSynthesizing video...")
    video_file = synthesize_video_from_storyboard(storyboard_file, args.project, args.location)
    if video_file:
        print(f"Video synthesis complete. Video saved to: {video_file}")

if __name__ == "__main__":
    main()
