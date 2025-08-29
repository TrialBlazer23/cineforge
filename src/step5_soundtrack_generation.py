
import argparse
import json
import os
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part

def generate_soundtrack(project_id: str, location: str, narrative_schema_path: str, output_dir: str):
    """Generates a soundtrack for each scene using Vertex AI."""
    vertexai.init(project=project_id, location=location)

    # Load the narrative schema
    with open(narrative_schema_path, "r") as f:
        schema = json.load(f)

    logline = schema.get("logline", "")
    scenes = schema.get("scenes", [])

    if not scenes:
        print("No scenes found in the narrative schema.")
        return

    os.makedirs(output_dir, exist_ok=True)
    model = GenerativeModel("music-generation-preview")

    for i, scene in enumerate(scenes):
        scene_summary = scene.get("summary", "")
        mood = scene.get("mood", "")
        prompt = f"Generate a music soundtrack for a scene with the following mood: {mood}. The overall story theme is: '{logline}' The scene summary is: '{scene_summary}'"

        print(f"Using prompt for scene {i+1}: {prompt}")

        response = model.generate_content([prompt])
        music_part = response.candidates[0].content.parts[0]

        output_path = os.path.join(output_dir, f"scene_{i+1:03d}_soundtrack.mp3")
        with open(output_path, "wb") as f:
            f.write(music_part.blob)

        print(f"Soundtrack for scene {i+1} saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a soundtrack for each scene in a story.")
    parser.add_argument("narrative_schema_path", help="Path to the narrative schema JSON file.")
    parser.add_argument("--project", required=True, help="Google Cloud project ID.")
    parser.add_argument("--location", default="us-central1", help="Google Cloud location.")
    parser.add_argument("--output_dir", default="output/soundtracks", help="Directory to save the generated soundtracks.")
    args = parser.parse_args()

    generate_soundtrack(args.project, args.location, args.narrative_schema_path, args.output_dir)
