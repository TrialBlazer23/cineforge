import argparse
import json
import re
import os
import sys
import vertexai
from vertexai.vision_models import ImageGenerationModel
try:
    from . import utils  # type: ignore
except Exception:
    # Allow running as a script: python src/generate_storyboard_images.py
    sys.path.append(os.path.dirname(__file__))
    import utils  # type: ignore

def generate_storyboard_image(
    shot_description,
    scene_number,
    shot_number,
    project,
    gcp_location,
    style_profile,
    narrative_schema=None,
):
    """Generates a storyboard image for a shot, honoring a style_profile for visual coherence."""
    print(f"Generating image for Scene {scene_number}, Shot {shot_number}...")
    try:
        vertexai.init(project=project, location=gcp_location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        # Resolve style prompt from config; fallback to the provided style_profile string itself.
        style_prompt = utils.resolve_style_prompt(style_profile)

        characters_in_shot = utils.get_characters_in_shot(shot_description, narrative_schema or {})
        scene_setting = utils.get_scene_setting(int(scene_number), narrative_schema or {})

        prompt = f"{shot_description}\n\n"
        if characters_in_shot:
            prompt += f"Use the character portrait for '{', '.join(characters_in_shot)}' "
        if scene_setting:
            prompt += f"and the environment plate for '{scene_setting}' "
        if characters_in_shot or scene_setting:
            prompt += "as a reference for this shot.\n\n"

        prompt += f"Style: {style_prompt}"

        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
        )

        image_path = os.path.join(
            "output", "visual_assets", f"scene_{scene_number}_shot_{shot_number}.png"
        )
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        print(f"Saved storyboard image to {image_path}")
        return image_path
    except Exception as e:
        print(
            f"Error generating storyboard image for Scene {scene_number}, Shot {shot_number}: {e}"
        )
        return None


def generate_storyboard_images(
    storyboard_file,
    narrative_schema_file,
    project,
    gcp_location,
    scene=None,
    shot=None,
    style_profile=None,
    legacy_style=None,
):
    try:
        with open(storyboard_file, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    narrative_schema = {}
    if narrative_schema_file:
        try:
            with open(narrative_schema_file, "r") as f:
                narrative_schema = json.load(f)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return

    style_profile = utils.resolve_style_profile(style_profile, legacy_style)

    shots = utils.parse_storyboard_shots(storyboard_content)

    for scene_number, shot_number, shot_description in shots:
        if scene is not None and int(scene_number) != scene:
            continue
        if shot is not None and int(shot_number) != shot:
            continue
        generate_storyboard_image(
            shot_description.strip(),
            scene_number,
            shot_number,
            project,
            gcp_location,
            style_profile,
            narrative_schema,
        )

    print("\nStoryboard image generation complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate storyboard images from a storyboard file."
    )
    parser.add_argument("storyboard_file", help="The path to the text-based storyboard file.")
    parser.add_argument(
        "narrative_schema_file", help="The path to the narrative schema JSON file."
    )
    utils.add_vertex_args(parser)
    utils.add_scene_shot_args(parser)
    utils.add_style_args(parser)
    args = parser.parse_args()

    generate_storyboard_images(
        args.storyboard_file,
        args.narrative_schema_file,
        args.project,
        args.location,
        scene=args.scene,
        shot=args.shot,
        style_profile=args.style_profile,
        legacy_style=args.legacy_style,
    )


if __name__ == "__main__":
    main()