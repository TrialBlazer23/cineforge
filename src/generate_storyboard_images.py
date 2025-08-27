import argparse
import json
import re
import os
import vertexai
from vertexai.vision_models import ImageGenerationModel

def generate_storyboard_image(shot_description, scene_number, shot_number, project, location, style, narrative_schema):
    """Generates a storyboard image from a shot description using Imagen."""
    print(f"Generating image for Scene {scene_number}, Shot {shot_number}...")
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        with open("config.json", "r") as f:
            config = json.load(f)
            style_prompt = config["styles"].get(style, "")

        characters_in_shot = [char["name"] for char in narrative_schema["characters"] if char["name"] in shot_description]

        scene_info = next((scene for scene in narrative_schema["scenes"] if scene["scene_number"] == int(scene_number)), None)
        location = scene_info.get("setting", "") if scene_info else ""

        prompt = f"{shot_description}\n\n"
        if characters_in_shot:
            prompt += f"Use the character portrait for '{', '.join(characters_in_shot)}' "
        if location:
            prompt += f"and the environment plate for '{location}' "
        if characters_in_shot or location:
            prompt += "as a reference for this shot.\n\n"

        prompt += f"Style: {style_prompt}"

        images = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9"
        )

        image_path = os.path.join("output", "visual_assets", f"scene_{scene_number}_shot_{shot_number}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        print(f"Saved storyboard image to {image_path}")
        return image_path
    except Exception as e:
        print(f"Error generating storyboard image for Scene {scene_number}, Shot {shot_number}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images from a storyboard file.")
    parser.add_argument("storyboard_file", help="The path to the text-based storyboard file.")
    parser.add_argument("narrative_schema_file", help="The path to the narrative schema JSON file.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    parser.add_argument("--scene", help="The scene number to generate.", type=int)
    parser.add_argument("--shot", help="The shot number to generate.", type=int)
    args = parser.parse_args()

    try:
        with open(args.storyboard_file, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    try:
        with open(args.narrative_schema_file, "r") as f:
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

    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    for scene_number, shot_number, shot_description in shots:
      feature/detailed-descriptions
        if args.scene is not None:
            if int(scene_number) == args.scene:
                if args.shot is not None:
                    if int(shot_number) == args.shot:
                        generate_storyboard_image(shot_description.strip(), scene_number, shot_number, args.project, args.location, style, narrative_schema)
                else:
                    generate_storyboard_image(shot_description.strip(), scene_number, shot_number, args.project, args.location, style, narrative_schema)


    print("\nStoryboard image generation complete.")

if __name__ == "__main__":
    main()