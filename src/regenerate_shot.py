import argparse
import os
import vertexai
from vertexai.vision_models import ImageGenerationModel

def regenerate_storyboard_image(shot_description, scene_number, shot_number, project, location):
    """Generates a storyboard image from a shot description using Imagen."""
    print(f"Regenerating image for Scene {scene_number}, Shot {shot_number}...")
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

    images = model.generate_images(
        prompt=shot_description,
        number_of_images=1,
        aspect_ratio="16:9"
    )

    image_path = os.path.join("output", "visual_assets", f"scene_{scene_number}_shot_{shot_number}.png")
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved regenerated storyboard image to {image_path}")
    return image_path

def main():
    parser = argparse.ArgumentParser(description="Regenerate a specific shot's image.")
    parser.add_argument("scene_number", type=int, help="The scene number of the shot to regenerate.")
    parser.add_argument("shot_number", type=int, help="The shot number of the shot to regenerate.")
    parser.add_argument("shot_description", help="The description of the shot to regenerate.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    args = parser.parse_args()

    regenerate_storyboard_image(args.shot_description, args.scene_number, args.shot_number, args.project, args.location)

if __name__ == "__main__":
    main()
