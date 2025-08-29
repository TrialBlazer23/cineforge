import argparse
import os
import re
import ffmpeg
import vertexai
from vertexai.preview.vision_models import VideoGenerationModel
from collections import defaultdict

def generate_video_clip(shot_description, image_path, scene_number, shot_number, project, location):
    """Generates a video clip from an image and a description using Veo."""
    print(f"Generating video for Scene {scene_number}, Shot {shot_number}...")
    vertexai.init(project=project, location=location)
    model = VideoGenerationModel.from_pretrained("veo-3.0-fast-generate-001")

    with open(image_path, "rb") as image_file:
        input_image = image_file.read()

    videos = model.generate(
        prompt=shot_description,
        image=input_image,
        video_length_sec=8,
        aspect_ratio="16:9"
    )

    video_path = os.path.join("output", "video_clips", f"scene_{scene_number}_shot_{shot_number}.mp4")
    with open(video_path, "wb") as video_file:
        video_file.write(videos[0].read())

    print(f"Saved video clip to {video_path}")
    return video_path

def main():
    parser = argparse.ArgumentParser(description="Generate video clips from storyboard images.")
    parser.add_argument("storyboard_file", help="The path to the text-based storyboard file.")
    parser.add_argument("images_directory", help="The directory containing the storyboard images.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    parser.add_argument("--scene", help="The scene number to generate videos for.", type=int)
    args = parser.parse_args()

    try:
        with open(args.storyboard_file, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError:
        print(f"Error: Storyboard file not found at {args.storyboard_file}")
        return

    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    shots_by_scene = defaultdict(list)
    for scene_number, shot_number, shot_description in shots:
        shots_by_scene[int(scene_number)].append((shot_number, shot_description))

    for scene_number, scene_shots in shots_by_scene.items():
        if args.scene is not None and scene_number != args.scene:
            continue

        generated_shot_paths = []
        for shot_number, shot_description in scene_shots:
            image_name = f"scene_{scene_number}_shot_{shot_number}.png"
            image_path = os.path.join(args.images_directory, image_name)

            if os.path.exists(image_path):
                video_path = generate_video_clip(shot_description.strip(), image_path, scene_number, shot_number, args.project, args.location)
                generated_shot_paths.append(video_path)
            else:
                print(f"Warning: Image not found for Scene {scene_number}, Shot {shot_number} at {image_path}")

        if generated_shot_paths:
            scene_video_path = os.path.join("output", "video_clips", f"scene_{scene_number}.mp4")
            
            # Create a temporary file with the list of video files for concatenation
            concat_file_path = os.path.join("output", "video_clips", f"concat_scene_{scene_number}.txt")
            with open(concat_file_path, "w") as f:
                for path in generated_shot_paths:
                    f.write(f"file '{os.path.basename(path)}'\n")
            
            (ffmpeg.input(concat_file_path, format='concat', safe=0)
             .output(scene_video_path, c='copy').run(overwrite_output=True))

            print(f"Concatenated shots into {scene_video_path}")

            # Clean up individual shot videos and concat file
            for path in generated_shot_paths:
                os.remove(path)
            os.remove(concat_file_path)

    print("\nVideo synthesis complete.")

if __name__ == "__main__":
    main()
