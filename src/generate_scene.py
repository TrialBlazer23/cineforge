import argparse
import os
import sys

try:
    from .generate_storyboard_images import generate_storyboard_images  # type: ignore
except Exception:
    sys.path.append(os.path.dirname(__file__))
    from generate_storyboard_images import generate_storyboard_images  # type: ignore


def generate_scene(
    storyboard_file, scene_number, project, location, narrative_schema_file=None
):
    """Generates all shots for a given scene."""
    generate_storyboard_images(
        storyboard_file,
        narrative_schema_file,
        project,
        location,
        scene=scene_number,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate all shots for a given scene."
    )
    parser.add_argument(
        "storyboard_file", help="The path to the text-based storyboard file."
    )
    parser.add_argument(
        "scene_number", help="The scene number to generate.", type=int
    )
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument(
        "--location", help="The Google Cloud location.", default="us-central1"
    )
    args = parser.parse_args()

    generate_scene(args.storyboard_file, args.scene_number, args.project, args.location)

