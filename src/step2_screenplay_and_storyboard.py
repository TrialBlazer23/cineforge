import argparse
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel

def generate_screenplay_and_storyboard(narrative_schema, project, location):
    """
    Generates a screenplay and storyboard from the narrative schema.
    """
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-flash")

    screenplay = ""
    storyboard = ""

    for scene in narrative_schema["scenes"]:
        scene_number = scene["scene_number"]
        scene_title = scene["title"]
        scene_setting = scene["setting"]
        scene_summary = scene["summary"]
        characters_in_scene = [char['name'] for char in narrative_schema['characters']]


        # Generate Screenplay for the scene
        screenplay_prompt = f"""
        Generate a screenplay scene based on the following information.
        The output should be in standard screenplay format (SCENE HEADING, ACTION, CHARACTER, DIALOGUE, PARENTHETICAL).

        **Example Format:**
        SCENE HEADING
        ACTION
        CHARACTER
        (PARENTHETICAL)
        DIALOGUE

        **Scene Information:**
        **Scene Number:** {scene_number}
        **Scene Title:** {scene_title}
        **Setting:** {scene_setting}
        **Summary:** {scene_summary}
        **Characters:** {', '.join(characters_in_scene)}

        **Generate the screenplay for this scene:**
        """

        screenplay_response = model.generate_content(
            [screenplay_prompt],
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.7,
                "top_p": 1.0,
            },
        )
        screenplay += f"\n\n## SCENE {scene_number}: {scene_title.upper()}\n\n" + screenplay_response.text

        # Generate Storyboard for the scene
        storyboard_prompt = f"""
        Generate a descriptive, shot-by-shot text storyboard for the following scene.
        Each shot description should be detailed and actionable, serving as a direct prompt for later image and video generation stages.
        Start each shot with "SCENE {scene_number}, SHOT X:"

        **Scene Information:**
        **Scene Number:** {scene_number}
        **Scene Title:** {scene_title}
        **Setting:** {scene_setting}
        **Summary:** {scene_summary}

        **Generate the storyboard for this scene:**
        """

        storyboard_response = model.generate_content(
            [storyboard_prompt],
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.7,
                "top_p": 1.0,
            },
        )
        storyboard += "\n\n" + storyboard_response.text

    return screenplay, storyboard

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
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {args.schema_file}")
        return

    print("Generating screenplay and storyboard... (This may take a moment)")
    screenplay, storyboard = generate_screenplay_and_storyboard(narrative_schema, args.project, args.location)
    print("Screenplay and storyboard generation complete.")

    base_name = os.path.splitext(os.path.basename(args.schema_file))[0].replace('_schema', '')

    # Save the screenplay
    screenplay_dir = os.path.join("output", "screenplay")
    os.makedirs(screenplay_dir, exist_ok=True)
    screenplay_path = os.path.join(screenplay_dir, f"{base_name}_screenplay.txt")
    with open(screenplay_path, "w") as f:
        f.write(screenplay)
    print(f"Screenplay saved to {screenplay_path}")

    # Save the storyboard
    storyboard_dir = os.path.join("output", "storyboard_text")
    os.makedirs(storyboard_dir, exist_ok=True)
    storyboard_path = os.path.join(storyboard_dir, f"{base_name}_storyboard.txt")
    with open(storyboard_path, "w") as f:
        f.write(storyboard)
    print(f"Storyboard saved to {storyboard_path}")

if __name__ == "__main__":
    main()
