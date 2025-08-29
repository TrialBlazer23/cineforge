import argparse
import json
import os
import re
import vertexai
from vertexai.vision_models import ImageGenerationModel

def generate_character_portrait(character_name, character_description, project, location):
    """Generates a character portrait using Imagen."""
    print(f"Generating portrait for {character_name}...")
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

    prompt = (
        f"A full-body character concept art of {character_name}. "
        f"Description: {character_description}. "
        f"Art style: 3D cartoon animation, detailed, expressive."
    )

    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="9:16"
    )

    image_path = os.path.join("output", "storyboard_images", f"character_{character_name.lower().replace(' ', '_')}.png")
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved character portrait to {image_path}")
    return image_path

def generate_environment_plate(location_name, project, location):
    """Generates an environment plate using Imagen."""
    print(f"Generating environment plate for {location_name}...")
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        prompt = (
            f"An environment concept art plate for \"{location_name}\". "
            f"Art style: 3D cartoon animation, cinematic lighting."
        )

        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9"
        )

        image_path = os.path.join("output", "storyboard_images", f"environment_{location_name.lower().replace(' ', '_')}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        print(f"Saved environment plate to {image_path}")
        return image_path
    except Exception as e:
        print(f"Error generating environment plate for {location_name}: {e}")
        return None

def generate_storyboard_image(shot_description, scene_number, shot_number, project, location):
    """Generates a storyboard image from a shot description using Imagen."""
    print(f"Generating image for Scene {scene_number}, Shot {shot_number}...")
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        images = model.generate_images(
            prompt=shot_description,
            number_of_images=1,
            aspect_ratio="16:9"
        )

        image_path = os.path.join("output", "storyboard_images", f"scene_{scene_number}_shot_{shot_number}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        print(f"Saved storyboard image to {image_path}")
        return image_path
    except Exception as e:
        print(f"Error generating storyboard image for Scene {scene_number}, Shot {shot_number}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate visual assets from a storyboard and narrative schema.")
    parser.add_argument("storyboard_file", help="The path to the text-based storyboard file.")
    parser.add_argument("schema_file", help="The path to the narrative schema JSON file.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    args = parser.parse_args()

    try:
        with open(args.storyboard_file, "r") as f:
            storyboard_content = f.read()
        with open(args.schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Generate character portraits
    characters = narrative_schema.get("characters", [])
    for character in characters:
        generate_character_portrait(character.get("name"), character.get("description"), args.project, args.location)

    # Generate environment plates
    locations = list(set(scene.get("setting") for scene in narrative_schema.get("scenes", [])))
    for location in locations:
        generate_environment_plate(location, args.project, args.location)

    # Generate storyboard images
    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    for scene_number, shot_number, shot_description in shots:
        generate_storyboard_image(shot_description.strip(), scene_number, shot_number, args.project, args.location)

    print("\nVisual asset generation complete.")

if __name__ == "__main__":
    main()
