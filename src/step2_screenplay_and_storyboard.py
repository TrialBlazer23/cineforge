import argparse
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part

def generate_screenplay(narrative_schema, project, location):
    """Generates a screenplay from a narrative schema using the Gemini API."""
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Based on the following narrative schema, write a detailed screenplay. The screenplay should be formatted correctly, with scene headings, character names, dialogue, and action descriptions.

    Narrative Schema:
    {json.dumps(narrative_schema)}
    """

    response = model.generate_content(
        [prompt],
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )
    return response.text

def generate_storyboard(screenplay_content, project, location):
    """Generates a storyboard from a screenplay using the Gemini API."""
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Based on the following screenplay, create a detailed storyboard. The storyboard should break down each scene into individual shots, with a description of the camera angle, shot type, and action for each shot.

    Screenplay:
    {screenplay_content}
    """

    response = model.generate_content(
        [prompt],
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )
    return response.text

def main():
    parser = argparse.ArgumentParser(description="Generate a screenplay and storyboard from a narrative schema.")
    parser.add_argument("schema_file", help="The path to the narrative schema JSON file.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    args = parser.parse_args()

    try:
        with open(args.schema_file, "r") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError:
        print(f"Error: Schema file not found at {args.schema_file}")
        return

    print("Generating screenplay...")
    screenplay_content = generate_screenplay(narrative_schema, args.project, args.location)
    screenplay_filename = os.path.splitext(os.path.basename(args.schema_file))[0].replace("_schema", "") + "_screenplay.txt"
    screenplay_output_path = os.path.join("output", "screenplay", screenplay_filename)
    os.makedirs(os.path.dirname(screenplay_output_path), exist_ok=True)
    with open(screenplay_output_path, "w") as f:
        f.write(screenplay_content)
    print(f"Screenplay saved to {screenplay_output_path}")

    print("\nGenerating storyboard...")
    storyboard_content = generate_storyboard(screenplay_content, args.project, args.location)
    storyboard_filename = os.path.splitext(os.path.basename(args.schema_file))[0].replace("_schema", "") + "_storyboard.txt"
    storyboard_output_path = os.path.join("output", "storyboard_text", storyboard_filename)
    os.makedirs(os.path.dirname(storyboard_output_path), exist_ok=True)
    with open(storyboard_output_path, "w") as f:
        f.write(storyboard_content)
    print(f"Storyboard saved to {storyboard_output_path}")

if __name__ == "__main__":
    main()
