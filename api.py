from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form
from pydantic import BaseModel
import os
import json
import re
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.preview.vision_models import ImageGenerationModel
from google.cloud import texttospeech
import ffmpeg

app = FastAPI()

# --- TASKS ---

def deconstruct_narrative_task(story_content: str, project: str, location: str, output_path: str):
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

    narrative_schema_str = response2.text

    # Clean the output to be a valid JSON
    if narrative_schema_str.strip().startswith("```json"):
        narrative_schema_str = narrative_schema_str.strip()[7:-4]

    try:
        narrative_schema = json.loads(narrative_schema_str)
    except json.JSONDecodeError:
        # Handle error, maybe save the raw response for debugging
        print(f"Error: Failed to decode the narrative schema from the model's response.")
        # For now, we'll just save the raw text
        narrative_schema = {"error": "Failed to decode JSON", "raw_response": narrative_schema_str}

    with open(output_path, "w") as f:
        json.dump(narrative_schema, f, indent=2)

def generate_screenplay_and_storyboard_task(narrative_schema, project, location, screenplay_path, storyboard_path):
    """
    Generates a screenplay and storyboard from the narrative schema.
    """
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-1.5-flash")

    screenplay = ""
    storyboard = ""

    for scene in narrative_schema["scenes"]:
        scene_number = scene["scene_number"]
        scene_title = scene["title"]
        scene_setting = scene.get("setting", "")
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

    with open(screenplay_path, "w") as f:
        f.write(screenplay)

    with open(storyboard_path, "w") as f:
        f.write(storyboard)

def generate_visual_assets_task(schema_path, storyboard_path, project, location):
    """Generates visual assets for the film."""
    try:
        with open(schema_path, "r") as f:
            narrative_schema = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: Failed to read or parse schema file: {e}")
        return

    try:
        with open(storyboard_path, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError:
        print(f"Error: Storyboard file not found at {storyboard_path}")
        return

    # Generate character model sheets
    for character in narrative_schema["characters"]:
        generate_character_model_sheet(character, project, location)

    # Generate environment plates
    locations = set(scene["setting"] for scene in narrative_schema["scenes"])
    for location_name in locations:
        generate_environment_plate(location_name, project, location)

    # Generate storyboard images
    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    for scene_number, shot_number, shot_description in shots:
        generate_storyboard_image(shot_description.strip(), scene_number, shot_number, project, location)

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
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
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
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
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
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    print(f"Saved storyboard image to {image_path}")
    return image_path

def generate_video_synthesis_task(storyboard_path, images_directory, project, location):
    """Generates video clips from storyboard images."""
    try:
        with open(storyboard_path, "r") as f:
            storyboard_content = f.read()
    except FileNotFoundError:
        print(f"Error: Storyboard file not found at {storyboard_path}")
        return

    shot_regex = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    shots = shot_regex.findall(storyboard_content)

    for scene_number, shot_number, shot_description in shots:
        image_name = f"scene_{scene_number}_shot_{shot_number}.png"
        image_path = os.path.join(images_directory, image_name)

        if os.path.exists(image_path):
            generate_video_clip(shot_description.strip(), image_path, scene_number, shot_number, project, location)
        else:
            print(f"Warning: Image not found for Scene {scene_number}, Shot {shot_number} at {image_path}")

def generate_video_clip(shot_description, image_path, scene_number, shot_number, project, location):
    """Generates a video clip from an image and a description using Veo."""
    print(f"Generating video for Scene {scene_number}, Shot {shot_number}...")
    vertexai.init(project=project, location=location)
    model = GenerativeModel("veo-3.0-fast-generate-001")

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    image_part = Part.from_data(data=image_data, mime_type="image/png")

    response = model.generate_content(
        [image_part, shot_description],
        generation_config={
            "video_length_sec": 8,
            "aspect_ratio": "16:9"
        }
    )
    videos = response.candidates

    video_path = os.path.join("output", "video_clips", f"scene_{scene_number}_shot_{shot_number}.mp4")
    with open(video_path, "wb") as video_file:
        video_file.write(videos[0].content.data)

    print(f"Saved video clip to {video_path}")
    return video_path


def generate_soundtrack_task(project_id: str, location: str, narrative_schema_path: str, output_path: str):
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

def generate_voiceover_task(project_id: str, screenplay_path: str, output_path: str):
    """Generates a voiceover from a screenplay using Google Cloud Text-to-Speech."""

    # Initialize the Text-to-Speech client
    client = texttospeech.TextToSpeechClient()

    # Read the screenplay
    with open(screenplay_path, "r") as f:
        screenplay = f.read()

    # Extract dialogue from the screenplay (simple extraction logic)
    dialogue_lines = []
    for line in screenplay.split('\n'):
        if line.isupper() and not line.startswith('SCENE') and not line.startswith('INT.') and not line.startswith('EXT.'):
            # This is likely a character name
            pass
        elif line.startswith('('):
            # This is likely a parenthetical
            pass
        elif line.strip() and not line.isupper():
            dialogue_lines.append(line.strip())

    dialogue = " ".join(dialogue_lines)

    if not dialogue:
        print("No dialogue found in the screenplay.")
        return

    synthesis_input = texttospeech.SynthesisInput(text=dialogue)

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    # Select the type of audio file you want
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the text-to-speech request
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the audio to the output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    print(f"Voiceover saved to {output_path}")

def assemble_film_task(
    video_clips_dir: str,
    soundtrack_path: str,
    voiceover_path: str,
    output_path: str,
    output_filename: str
):
    """Assembles the final film from video clips, soundtrack, and voiceover."""

    # Get all video clips and sort them
    video_files = sorted([f for f in os.listdir(video_clips_dir) if f.endswith(".mp4")] )
    video_paths = [os.path.join(video_clips_dir, f) for f in video_files]

    if not video_paths:
        print("No video clips found.")
        return

    # Create a temporary file with the list of video files for concatenation
    concat_file_path = os.path.join(video_clips_dir, "concat.txt")
    with open(concat_file_path, "w") as f:
        for path in video_paths:
            f.write(f"file '{os.path.basename(path)}'\n")

    # Concatenate video clips
    video_stream = ffmpeg.input(concat_file_path, format='concat', safe=0, r=24)

    # Input soundtrack and voiceover
    soundtrack_stream = ffmpeg.input(soundtrack_path)
    voiceover_stream = ffmpeg.input(voiceover_path)

    # Combine audio streams
    combined_audio = ffmpeg.filter([
        soundtrack_stream, 
        voiceover_stream
    ], 'amix', inputs=2, duration='first')

    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    final_output_path = os.path.join(output_path, output_filename)

    # Mux video and combined audio
    (
        ffmpeg
        .output(video_stream, combined_audio, final_output_path, vcodec='copy', acodec='aac', shortest=None)
        .run(overwrite_output=True)
    )

    # Clean up the temporary concat file
    os.remove(concat_file_path)

    print(f"Final film assembled at {final_output_path}")

# --- REQUEST MODELS ---

class ScreenplayStoryboardRequest(BaseModel):
    schema_path: str
    project_id: str
    location: str = "us-central1"

class VisualAssetGenerationRequest(BaseModel):
    schema_path: str
    storyboard_path: str
    project_id: str
    location: str = "us-central1"

class VideoSynthesisRequest(BaseModel):
    storyboard_path: str
    images_directory: str
    project_id: str
    location: str = "us-central1"

class SoundtrackGenerationRequest(BaseModel):
    schema_path: str
    project_id: str
    location: str = "us-central1"

class VoiceoverGenerationRequest(BaseModel):
    screenplay_path: str
    project_id: str

class FinalAssemblyRequest(BaseModel):
    video_clips_dir: str
    soundtrack_path: str
    voiceover_path: str
    output_path: str
    output_filename: str

# --- ENDPOINTS ---

@app.post("/narrative_deconstruction")
async def narrative_deconstruction_endpoint(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    location: str = Form("us-central1"),
    story_file: UploadFile = File(...)
):
    story_content = (await story_file.read()).decode("utf-8")
    
    output_dir = os.path.join("output", "narrative_schema")
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.splitext(story_file.filename)[0] + "_schema.json"
    output_path = os.path.join(output_dir, output_filename)

    background_tasks.add_task(deconstruct_narrative_task, story_content, project_id, location, output_path)

    return {"message": "Narrative deconstruction started in the background.", "output_path": output_path}

@app.post("/screenplay_and_storyboard")
async def screenplay_and_storyboard_endpoint(request: ScreenplayStoryboardRequest, background_tasks: BackgroundTasks):
    try:
        with open(request.schema_path, "r") as f:
            narrative_schema = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": f"Failed to read or parse schema file: {e}"}

    base_name = os.path.splitext(os.path.basename(request.schema_path))[0].replace('_schema', '')

    screenplay_dir = os.path.join("output", "screenplay")
    os.makedirs(screenplay_dir, exist_ok=True)
    screenplay_path = os.path.join(screenplay_dir, f"{base_name}_screenplay.txt")

    storyboard_dir = os.path.join("output", "storyboard_text")
    os.makedirs(storyboard_dir, exist_ok=True)
    storyboard_path = os.path.join(storyboard_dir, f"{base_name}_storyboard.txt")

    background_tasks.add_task(generate_screenplay_and_storyboard_task, narrative_schema, request.project_id, request.location, screenplay_path, storyboard_path)

    return {
        "message": "Screenplay and storyboard generation started in the background.",
        "screenplay_path": screenplay_path,
        "storyboard_path": storyboard_path
    }

@app.post("/visual_asset_generation")
async def visual_asset_generation_endpoint(request: VisualAssetGenerationRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_visual_assets_task, request.schema_path, request.storyboard_path, request.project_id, request.location)
    return {"message": "Visual asset generation started in the background."}

@app.post("/video_synthesis")
async def video_synthesis_endpoint(request: VideoSynthesisRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_video_synthesis_task, request.storyboard_path, request.images_directory, request.project_id, request.location)
    return {"message": "Video synthesis started in the background."}

@app.post("/soundtrack_generation")
async def soundtrack_generation_endpoint(request: SoundtrackGenerationRequest, background_tasks: BackgroundTasks):
    output_path = "output/soundtrack/soundtrack.mp3"
    background_tasks.add_task(generate_soundtrack_task, request.project_id, request.location, request.schema_path, output_path)
    return {"message": "Soundtrack generation started in the background.", "output_path": output_path}

@app.post("/voiceover_generation")
async def voiceover_generation_endpoint(request: VoiceoverGenerationRequest, background_tasks: BackgroundTasks):
    output_path = "output/voiceover/voiceover.mp3"
    background_tasks.add_task(generate_voiceover_task, request.project_id, request.screenplay_path, output_path)
    return {"message": "Voiceover generation started in the background.", "output_path": output_path}

@app.post("/final_assembly")
async def final_assembly_endpoint(request: FinalAssemblyRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(assemble_film_task, request.video_clips_dir, request.soundtrack_path, request.voiceover_path, request.output_path, request.output_filename)
    return {"message": "Final assembly started in the background."}

@app.get("/")
def read_root():
    return {"Hello": "World"}