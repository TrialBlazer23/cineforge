import argparse
import re
import os

def generate_scene(storyboard_file, scene_number, project, location):
    """Generates all shots for a given scene."""
    try:
        with open(storyboard_file, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    for current_scene_number, shot_number, shot_description in shots:
        if int(current_scene_number) == scene_number:
            os.system(f"python3 src/generate_storyboard_images.py {storyboard_file} --project={project} --location={location} --scene={current_scene_number} --shot={shot_number}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate all shots for a given scene.")
    parser.add_argument("storyboard_file", help="The path to the text-based storyboard file.")
    parser.add_argument("scene_number", help="The scene number to generate.", type=int)
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    args = parser.parse_args()

    generate_scene(args.storyboard_file, args.scene_number, args.project, args.location)