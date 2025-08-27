import argparse
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part

def deconstruct_narrative(story_content, project, location):
    """
    Deconstructs the narrative from the story content using the Gemini API.
    """
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-pro")

    # First prompt for summarization and key element extraction
    prompt1 = f"""
    Analyze the following story and provide a summary, a list of primary characters with brief descriptions, key locations, the overarching plot points, and the story's prevailing tone or genre.

    Story:
    {story_content}
    """
    response1 = model.generate_content(
        [prompt1],
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.2,
            "top_p": 1.0,
        },
    )

    # Second prompt for hierarchical outline
    prompt2 = f"""
    Based on the following summary and key elements, generate a hierarchical outline of the story.
    Break the overall plot into a sequence of distinct scenes, each with a brief summary of its constituent beats.
    The final output must be a consistent, parsable JSON object.

    The JSON object should have the following schema:
    {{
      "title": "The Last Sundown",
      "logline": "In a desolate future, a lone wanderer must...",
      "characters": [
        {{
          "name": "Elara",
          "description": "A stoic survivor in her late 20s, resourceful and cautious, with a hidden past."
        }},
        {{
          "name": "Kael",
          "description": "An aging, cynical scavenger who knows the secrets of the wasteland."
        }}
      ],
      "scenes": []
    }}

    Summary and Key Elements:
    {response1.text}
    """
    response2 = model.generate_content(
        [prompt2],
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
            "top_p": 1.0,
        },
    )

    return response2.text

def main():
    parser = argparse.ArgumentParser(description="Deconstruct a narrative from a story file.")
    parser.add_argument("story_file", help="The path to the story file.")
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")
    args = parser.parse_args()

    try:
        with open(args.story_file, "r") as f:
            story_content = f.read()
    except FileNotFoundError:
        print(f"Error: Story file not found at {args.story_file}")
        return

    print("Deconstructing narrative... (This may take a moment)")
    narrative_schema_str = deconstruct_narrative(story_content, args.project, args.location)
    print("Narrative deconstruction complete.")

    # Clean the output to be a valid JSON
    # The model sometimes returns the JSON wrapped in ```json ... ```
    if narrative_schema_str.strip().startswith("```json"):
        narrative_schema_str = narrative_schema_str.strip()[7:-4]

    try:
        narrative_schema = json.loads(narrative_schema_str)
    except json.JSONDecodeError:
        print("Error: Failed to decode the narrative schema from the model's response.")
        print("Raw response:")
        print(narrative_schema_str)
        return

    output_dir = os.path.join("output", "narrative_schema")
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.splitext(os.path.basename(args.story_file))[0] + "_schema.json"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, "w") as f:
        json.dump(narrative_schema, f, indent=2)

    print(f"Narrative schema saved to {output_path}")

if __name__ == "__main__":
    main()
