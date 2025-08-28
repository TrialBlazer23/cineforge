import argparse
import json
import os
import sys
import vertexai
from vertexai.vision_models import ImageGenerationModel
try:
    from . import utils  # type: ignore
except Exception:
    # Allow running as a script: python src/generate_environments.py
    sys.path.append(os.path.dirname(__file__))
    import utils  # type: ignore

def generate_environment_plate(location_name, project, gcp_location, style_profile):
    """Generates an environment plate using Imagen, honoring a style_profile for consistency."""
    print(f"Generating environment plate for {location_name}...")
    try:
        vertexai.init(project=project, location=gcp_location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        # Resolve style prompt from config; fallback to the provided style_profile itself.
        style_prompt = utils.resolve_style_prompt(style_profile)

        prompt = (
            f"An environment concept art plate for \"{location_name}\". "
            f"Art style: {style_prompt}, cinematic lighting."
        )

        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9"
        )

        image_path = os.path.join("output", "visual_assets", f"environment_{location_name.lower().replace(' ', '_')}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        print(f"Saved environment plate to {image_path}")
        return image_path
    except Exception as e:
        print(f"Error generating environment plate for {location_name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate environment plates from a narrative schema.")
    parser.add_argument("schema_file", help="The path to the narrative schema JSON file.")
    utils.add_vertex_args(parser)
    utils.add_style_args(parser)
    args = parser.parse_args()

    try:
        with open(args.schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    style_profile = utils.resolve_style_profile(args.style_profile, args.legacy_style)

    locations = list(set(scene.get("setting") for scene in narrative_schema.get("scenes", [])))
    for scene_location in locations:
        if not scene_location:
            continue
        generate_environment_plate(scene_location, args.project, args.location, style_profile)

    print("\nEnvironment plate generation complete.")

if __name__ == "__main__":
    main()