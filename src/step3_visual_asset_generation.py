import argparse
import json
import os
import re
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

def generate_character_model_sheet(character, project, location):
    """Generates a character model sheet using Imagen."""
    print(f"Generating model sheet for {character['name']}...")
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

    prompt = (
        f"A full-body character model sheet for \"{character['name']}\". "
        f"Description: {character['description']}. "
        f"The character is in a neutral pose against a plain, simple background. "
        f"Art style: 3D cartoon animation."
    )

    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
    )

    image_path = os.path.join("output", "storyboard_images", f"character_{character['name'].lower().replace(' ', '_')}.png")
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved character model sheet to {image_path}")
    return image_path

def generate_environment_plate(location_name, project, location):
    """Generates an environment plate using Imagen."""
    print(f"Generating environment plate for {location_name}...")
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
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved environment plate to {image_path}")
    return image_path

def generate_storyboard_image(shot_description, scene_number, shot_number, project, location):
    """Generates a storyboard image from a shot description using Imagen."""
    print(f"Generating image for Scene {scene_number}, Shot {shot_number}...")
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

    # TODO: Implement character and style locking using reference images.
    # This would involve passing reference_image IDs to the generate_images call.

    images = model.generate_images(
        prompt=shot_description,
        number_of_images=1,
        aspect_ratio="16:9"
    )

    image_path = os.path.join("output", "storyboard_images", f"scene_{scene_number}_shot_{shot_number}.png")
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved storyboard image to {image_path}")
    return image_path

def main():
    parser = argparse.ArgumentParser(description="Generate visual assets for the film.")
    parser.add_argument("schema_file", help="The path to the narrative schema JSON file.")
    parser.add_argument("storyboard_file", help="The path to the text-based storyboard file.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    args = parser.parse_args()

    try:
        with open(args.schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError:
        print(f"Error: Schema file not found at {args.schema_file}")
        return

    try:
        with open(args.storyboard_file, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError:
        print(f"Error: Storyboard file not found at {args.storyboard_file}")
        return

    # Generate character model sheets
    for character in narrative_schema["characters"]:
        generate_character_model_sheet(character, args.project, args.location)

    # Generate environment plates
    locations = set(scene["setting"] for scene in narrative_schema["scenes"])
    for location_name in locations:
        generate_environment_plate(location_name, args.project, args.location)

    # Generate storyboard images
    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    for scene_number, shot_number, shot_description in shots:
        generate_storyboard_image(shot_description.strip(), scene_number, shot_number, args.project, args.location)

    print("\nVisual asset generation complete.")

if __name__ == "__main__":
    main()
