import os
import json
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models
from vertexai.vision_models import ImageGenerationModel


def deconstruct_narrative(story_file, project, location):
    """Deconstructs a narrative into a structured schema using Gemini."""
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-pro")

    with open(story_file, "r") as f:
        story_text = f.read()

    prompt = f"""
    Analyze the following story and deconstruct it into a detailed narrative schema. The schema should be in JSON format and include the following elements:

    -   **Title**: The title of the story.
    -   **Logline**: A one-sentence summary of the story.
    -   **Characters**: A list of all characters with detailed descriptions, including their physical appearance, personality, and motivations.
    -   **Setting**: A description of the primary locations and the overall atmosphere of the story.
    -   **Plot_Summary**: A brief overview of the main plot points.
    -   **Scene_Breakdown**: A list of all scenes, where each scene includes:
        -   **Scene_Number**: The number of the scene.
        -   **Setting**: The location of the scene.
        -   **Time_of_Day**: The time of day the scene takes place.
        -   **Characters_Present**: A list of characters in the scene.
        -   **Events**: A detailed, step-by-step description of the events that unfold in the scene.

    Here is the story:

    {story_text}
    """

    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    responses = model.generate_content(
        [prompt],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    schema_json = ""
    for response in responses:
        schema_json += response.text

    # Clean up the JSON - Gemini sometimes includes ```json ... ```
    schema_json = schema_json.strip()
    if schema_json.startswith("```json"):
        schema_json = schema_json[7:]
    if schema_json.endswith("```"):
        schema_json = schema_json[:-3]

    # Save the schema to a file
    output_dir = os.path.join("output", "narrative_schema")
    os.makedirs(output_dir, exist_ok=True)
    schema_filename = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(story_file))[0]}_schema.json")
    with open(schema_filename, "w") as f:
        f.write(schema_json)

    return schema_filename


def generate_screenplay_and_storyboard(schema_file, project, location):
    """Generates a screenplay and storyboard from a narrative schema using Gemini."""
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-pro")

    with open(schema_file, "r") as f:
        schema_text = f.read()

    # Generate Screenplay
    screenplay_prompt = f"""
    Based on the following narrative schema, write a detailed screenplay. The screenplay should be formatted correctly, with scene headings, character names, dialogue, and action descriptions.

    Narrative Schema:
    {schema_text}
    """
    screenplay_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }
    screenplay_responses = model.generate_content(
        [screenplay_prompt],
        generation_config=screenplay_config,
        stream=True,
    )

    screenplay = ""
    for response in screenplay_responses:
        screenplay += response.text

    # Generate Storyboard
    storyboard_prompt = f"""
    Based on the following screenplay, create a detailed storyboard. The storyboard should break down each scene into individual shots, with a description of the camera angle, shot type, and action for each shot.

    Screenplay:
    {screenplay}
    """
    storyboard_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }
    storyboard_responses = model.generate_content(
        [storyboard_prompt],
        generation_config=storyboard_config,
        stream=True,
    )

    storyboard = ""
    for response in storyboard_responses:
        storyboard += response.text

    # Save the screenplay and storyboard to files
    project_name = os.path.splitext(os.path.basename(schema_file))[0].replace("_schema", "")
    screenplay_dir = os.path.join("output", "screenplay")
    storyboard_dir = os.path.join("output", "storyboard_text")
    os.makedirs(screenplay_dir, exist_ok=True)
    os.makedirs(storyboard_dir, exist_ok=True)

    screenplay_filename = os.path.join(screenplay_dir, f"{project_name}_screenplay.txt")
    storyboard_filename = os.path.join(storyboard_dir, f"{project_name}_storyboard.txt")

    with open(screenplay_filename, "w") as f:
        f.write(screenplay)
    with open(storyboard_filename, "w") as f:
        f.write(storyboard)

    return screenplay_filename, storyboard_filename


def generate_character_portrait(character_name, character_description, project, location, style_prompt: str | None = None):
    """Generates a character portrait using Imagen."""
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

    base_style = style_prompt or "3D cartoon animation, detailed, expressive"
    prompt = (
        f"A full-body character concept art of {character_name}. "
        f"Description: {character_description}. "
        f"Art style: {base_style}."
    )

    images = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="9:16")

    image_path = os.path.join("output", "storyboard_images", f"character_{character_name.lower().replace(' ', '_')}.png")
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    return image_path


def generate_environment_plate(location_name, project, location, style_prompt: str | None = None):
    """Generates an environment plate using Imagen."""
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        base_style = style_prompt or "3D cartoon animation, cinematic lighting"
        prompt = (
            f"An environment concept art plate for \"{location_name}\". "
            f"Art style: {base_style}."
        )

        images = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")

        image_path = os.path.join("output", "storyboard_images", f"environment_{location_name.lower().replace(' ', '_')}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        return image_path
    except Exception as e:
        print(f"Error generating environment plate for {location_name}: {e}")
        return None


def generate_storyboard_image(shot_description, scene_number, shot_number, project, location):
    """Generates a storyboard image from a shot description using Imagen."""
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")

        images = model.generate_images(prompt=shot_description, number_of_images=1, aspect_ratio="16:9")

        image_path = os.path.join("output", "storyboard_images", f"scene_{scene_number}_shot_{shot_number}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        images[0].save(location=image_path, include_generation_parameters=True)
        return image_path
    except Exception as e:
        print(f"Error generating storyboard image for Scene {scene_number}, Shot {shot_number}: {e}")
        return None


def generate_visual_assets(storyboard_file, schema_file, project, location, style: str | None = None):
    """
    Generates visual assets (character portraits, environment plates, and storyboard images)
    based on the storyboard and narrative schema.
    """
    with open(storyboard_file, "r") as f:
        storyboard_text = f.read()
    with open(schema_file, "r") as f:
        schema = json.load(f)

    # Extract character descriptions and locations from the schema
    characters = schema.get("Characters", [])
    locations = list(set(scene["Setting"] for scene in schema.get("Scene_Breakdown", [])))

    # Style preset
    style_prompt = None
    if style:
        try:
            with open("config.json", "r") as f:
                cfg = json.load(f)
                style_prompt = cfg.get("styles", {}).get(style)
        except Exception:
            style_prompt = None

    # Generate character portraits
    for character in characters:
        desc = character.get("Description") if isinstance(character, dict) else None
        name = character.get("Name") if isinstance(character, dict) else None
        generate_character_portrait(name or str(character), desc or "", project, location, style_prompt=style_prompt)

    # Generate environment plates
    for location_name in locations:
        generate_environment_plate(location_name, project, location, style_prompt=style_prompt)

    # Generate storyboard images from storyboard text
    shots = storyboard_text.strip().split("\n\n")
    for i, shot in enumerate(shots):
        scene_number = i // 10 + 1  # Assuming 10 shots per scene for placeholder
        shot_number = i % 10 + 1
        # Optionally embed style into shot description
        shot_prompt = shot
        if style_prompt:
            shot_prompt = f"{shot}\n\nStyle: {style_prompt}"
        generate_storyboard_image(shot_prompt, scene_number, shot_number, project, location)


def synthesize_video_from_storyboard(storyboard_file, project, location):
    """Synthesizes a video from a storyboard using Veo (placeholder)."""
    print("Video synthesis with Veo is not yet implemented.")
    return None
