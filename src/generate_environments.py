import argparse
import json
import os
import vertexai
from vertexai.vision_models import ImageGenerationModel

def generate_environment_plate(location_name, project, location, style):
    """Generates an environment plate using Imagen."""
    print(f"Generating environment plate for {location_name}...")
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        with open("config.json", "r") as f:
            config = json.load(f)
            style_prompt = config["styles"].get(style, "")

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
    args = parser.parse_args()

    try:
        with open(args.schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    project_settings_file = "output/project_settings.json"
    style = "photorealistic" # default style
    if os.path.exists(project_settings_file):
        with open(project_settings_file, "r") as f:
            project_settings = json.load(f)
            style = project_settings.get("style", style)

    locations = list(set(scene.get("setting") for scene in narrative_schema.get("scenes", [])))
    for location in locations:
        generate_environment_plate(location, args.project, args.location, style)

    print("\nEnvironment plate generation complete.")

if __name__ == "__main__":
    main()