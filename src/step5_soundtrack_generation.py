
import argparse
import json
import os
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part

def generate_soundtrack(project_id: str, location: str, narrative_schema_path: str, output_path: str):
    """Generates a soundtrack using Vertex AI."""
    vertexai.init(project=project_id, location=location)

    # Load the narrative schema
    with open(narrative_schema_path, "r") as f:
        schema = json.load(f)

    # Create a prompt for the music generation model
    logline = schema.get("logline", "")
    first_scene_summary = ""
    if schema.get("scenes"):
        first_scene_summary = schema["scenes"][0].get("summary", "")
    
    prompt = f"Generate a soundtrack for a story with the following theme: '{logline}' The opening scene is: '{first_scene_summary}'"

    print(f"Using prompt: {prompt}")

    model = GenerativeModel("music-generation-preview")

    response = model.generate_content(
        [prompt]
    )
    music_part = response.candidates[0].content.parts[0]

    # Save the music to the output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(music_part.blob)

    print(f"Soundtrack saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a soundtrack for a story.")
    parser.add_argument("narrative_schema_path", help="Path to the narrative schema JSON file.")
    parser.add_argument("--project", required=True, help="Google Cloud project ID.")
    parser.add_argument("--location", default="us-central1", help="Google Cloud location.")
    parser.add_argument("--output_path", default="output/soundtrack/soundtrack.mp3", help="Path to save the generated soundtrack.")
    args = parser.parse_args()

    generate_soundtrack(args.project, args.location, args.narrative_schema_path, args.output_path)
