import argparse
import json
import os
import vertexai
from vertexai.vision_models import ImageGenerationModel

def generate_character_portrait(character_name, character_description, project, location, style):
    """Generates a character portrait using Imagen."""
    print(f"Generating portrait for {character_name}...")
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

    with open("config.json", "r") as f:
        config = json.load(f)
        style_prompt = config["styles"].get(style, "")

    prompt = (
        f"A full-body character concept art of {character_name}. "
        f"Description: {character_description}. "
        f"Art style: {style_prompt}."
    )

    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="9:16"
    )

    image_path = os.path.join(
        "output", "visual_assets", f"character_{character_name.lower().replace(' ', '_')}.png"
    )
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved character portrait to {image_path}")
    return image_path


def generate_characters(schema_file, project, location):
    try:
        with open(schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    project_settings_file = "output/project_settings.json"
    style = "photorealistic"  # default style
    if os.path.exists(project_settings_file):
        with open(project_settings_file, "r") as f:
            project_settings = json.load(f)
            style = project_settings.get("style", style)

    characters = narrative_schema.get("characters", [])
    for character in characters:
        generate_character_portrait(
            character.get("name"),
            character.get("description"),
            project,
            location,
            style,
        )

    print("\nCharacter portrait generation complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate character portraits from a narrative schema."
    )
    parser.add_argument("schema_file", help="The path to the narrative schema JSON file.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument(
        "--location", help="The Google Cloud location.", default="us-central1"
    )
    args = parser.parse_args()

    generate_characters(args.schema_file, args.project, args.location)


if __name__ == "__main__":
    main()