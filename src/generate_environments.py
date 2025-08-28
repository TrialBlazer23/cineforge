import argparse
import json
import os
import vertexai
from vertexai.vision_models import ImageGenerationModel

def generate_environment_plate(location_name, project, gcp_location, style_profile):
    """Generates an environment plate using Imagen, honoring a style_profile for consistency."""
    print(f"Generating environment plate for {location_name}...")
    try:
        vertexai.init(project=project, location=gcp_location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        # Resolve style prompt from config; fallback to the provided style_profile itself.
        style_prompt = None
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                styles_map = config.get("styles", {}) if isinstance(config, dict) else {}
                style_prompt = styles_map.get(style_profile)
        except FileNotFoundError:
            style_prompt = None
        style_prompt = style_prompt or style_profile

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
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    parser.add_argument("--style-profile", dest="style_profile", help="A style profile to guide all generations (e.g., 'Studio Ghibli', 'film noir').")
    # Back-compat alias
    parser.add_argument("--style", dest="legacy_style", help="Deprecated. Use --style-profile instead.")
    args = parser.parse_args()

    try:
        with open(args.schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    project_settings_file = "output/project_settings.json"
    style_profile = None
    # Resolve style_profile priority: CLI > project settings > default
    if args.style_profile:
        style_profile = args.style_profile
    elif args.legacy_style:
        style_profile = args.legacy_style
    else:
        if os.path.exists(project_settings_file):
            try:
                with open(project_settings_file, "r") as f:
                    project_settings = json.load(f)
                    style_profile = project_settings.get("style_profile") or project_settings.get("style")
            except Exception:
                style_profile = None
    if not style_profile:
        style_profile = "photorealistic"

    # Persist chosen style_profile for coherence across runs
    try:
        os.makedirs(os.path.dirname(project_settings_file), exist_ok=True)
        existing = {}
        if os.path.exists(project_settings_file):
            with open(project_settings_file, "r") as f:
                try:
                    existing = json.load(f) or {}
                except Exception:
                    existing = {}
        existing["style_profile"] = style_profile
        # Also maintain legacy key for other scripts
        existing["style"] = style_profile
        with open(project_settings_file, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass

    locations = list(set(scene.get("setting") for scene in narrative_schema.get("scenes", [])))
    for scene_location in locations:
        if not scene_location:
            continue
        generate_environment_plate(scene_location, args.project, args.location, style_profile)

    print("\nEnvironment plate generation complete.")

if __name__ == "__main__":
    main()