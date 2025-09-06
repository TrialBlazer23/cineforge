"""Core pipeline functions for the CineForge project.

This module provides end-to-end orchestration for the filmmaking pipeline.
It wraps Gemini/Imagen calls for narrative deconstruction, screenplay and
storyboard generation, and adds support for video synthesis using Veo,
soundtrack and voice-over generation, and final film assembly.

The functions defined here are designed to be imported by Celery tasks
or called directly from a CLI.
"""

import os
import json
import re
from collections import defaultdict
from typing import List, Tuple, Optional

import ffmpeg  # type: ignore
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models
from vertexai.vision_models import ImageGenerationModel

from .step4_video_synthesis import generate_video_clip
from .step5_soundtrack_generation import generate_soundtrack
from .step6_voiceover_generation import generate_voiceover
from .step7_final_assembly import assemble_film


def deconstruct_narrative(story_file: str, project: str, location: str) -> str:
    """Deconstruct a raw story into a structured narrative schema using Gemini."""
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-pro")
    with open(story_file, "r", encoding="utf-8") as f:
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
    schema_json = schema_json.strip()
    if schema_json.startswith("```json"):
        schema_json = schema_json[7:]
    if schema_json.endswith("```"):
        schema_json = schema_json[:-3]
    output_dir = os.path.join("output", "narrative_schema")
    os.makedirs(output_dir, exist_ok=True)
    schema_filename = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(story_file))[0]}_schema.json")
    with open(schema_filename, "w", encoding="utf-8") as f:
        f.write(schema_json)
    return schema_filename


def generate_screenplay_and_storyboard(schema_file: str, project: str, location: str) -> Tuple[str, str]:
    """Generate a screenplay and a storyboard from a narrative schema using Gemini."""
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-pro")
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_text = f.read()
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
    screenplay_responses = model.generate_content([
        screenplay_prompt
    ], generation_config=screenplay_config, stream=True)
    screenplay = "".join([r.text for r in screenplay_responses])
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
    storyboard_responses = model.generate_content([
        storyboard_prompt
    ], generation_config=storyboard_config, stream=True)
    storyboard = "".join([r.text for r in storyboard_responses])
    project_name = os.path.splitext(os.path.basename(schema_file))[0].replace("_schema", "")
    screenplay_dir = os.path.join("output", "screenplay")
    storyboard_dir = os.path.join("output", "storyboard_text")
    os.makedirs(screenplay_dir, exist_ok=True)
    os.makedirs(storyboard_dir, exist_ok=True)
    screenplay_filename = os.path.join(screenplay_dir, f"{project_name}_screenplay.txt")
    storyboard_filename = os.path.join(storyboard_dir, f"{project_name}_storyboard.txt")
    with open(screenplay_filename, "w", encoding="utf-8") as f:
        f.write(screenplay)
    with open(storyboard_filename, "w", encoding="utf-8") as f:
        f.write(storyboard)
    return screenplay_filename, storyboard_filename


def generate_character_portrait(
    character_name: str,
    character_description: str,
    project: str,
    location: str,
    style_prompt: Optional[str] | None = None,
) -> str:
    """Generate a single character portrait using Imagen."""
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
    base_style = style_prompt or "3D cartoon animation, detailed, expressive"
    prompt = (
        f"A full-body character concept art of {character_name}. "
        f"Description: {character_description}. "
        f"Art style: {base_style}."
    )
    images = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="9:16")
    image_path = os.path.join(
        "output",
        "storyboard_images",
        f"character_{character_name.lower().replace(' ', '_')}.png",
    )
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    return image_path


def generate_environment_plate(
    location_name: str,
    project: str,
    location: str,
    style_prompt: Optional[str] | None = None,
) -> str:
    """Generate an environment plate using Imagen."""
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
    base_style = style_prompt or "3D cartoon animation, detailed, expressive"
    prompt = (
        f"A highly detailed background environment of {location_name}. "
        f"Art style: {base_style}."
    )
    images = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")
    image_path = os.path.join(
        "output",
        "storyboard_images",
        f"environment_{location_name.lower().replace(' ', '_')}.png",
    )
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    return image_path


def generate_storyboard_image(
    shot_description: str,
    scene_number: int,
    shot_number: int,
    project: str,
    location: str,
    style_prompt: Optional[str] | None = None,
) -> str:
    """Generate a storyboard image for a single shot using Imagen."""
    vertexai.init(project=project, location=location)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
    prompt = shot_description
    if style_prompt:
        prompt += f"\n\nStyle: {style_prompt}"
    images = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")
    image_path = os.path.join(
        "output",
        "storyboard_images",
        f"scene_{scene_number}_shot_{shot_number}.png",
    )
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    images[0].save(location=image_path, include_generation_parameters=True)
    return image_path


def generate_visual_assets_from_storyboard(
    storyboard_file: str,
    project: str,
    location: str,
    style_prompt: Optional[str] | None = None,
) -> None:
    """Generate storyboard images for each shot described in a storyboard text file."""
    with open(storyboard_file, "r", encoding="utf-8") as f:
        storyboard_text = f.read()
    shots = storyboard_text.strip().split("\n\n")
    for i, shot in enumerate(shots):
        scene_number = i // 10 + 1
        shot_number = i % 10 + 1
        shot_prompt = shot.strip()
        if style_prompt:
            shot_prompt += f"\n\nStyle: {style_prompt}"
        generate_storyboard_image(shot_prompt, scene_number, shot_number, project, location)


def synthesize_video_from_storyboard(storyboard_file: str, project: str, location: str) -> Optional[str]:
    """
    Synthesizes a video from storyboard text and images using Veo.

    Reads the storyboard file to parse scenes and shots, generates video clips for each shot
    using the pre-trained Veo model, concatenates them into scene-level videos, and finally
    concatenates all scenes into a single video. Returns the path to the final video file
    or None if no videos were generated.
    """
    with open(storyboard_file, "r", encoding="utf-8") as f:
        storyboard_text = f.read()
    shot_regex = re.compile(r"SCENE\s+(\d+),\s*SHOT\s+(\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)
    matches = shot_regex.findall(storyboard_text)
    shots_by_scene: dict[int, list[tuple[int, str]]] = defaultdict(list)
    if matches:
        for scene_str, shot_str, description in matches:
            scene_num = int(scene_str)
            shot_num = int(shot_str)
            shots_by_scene[scene_num].append((shot_num, description.strip()))
    else:
        paragraphs = [p.strip() for p in storyboard_text.split("\n\n") if p.strip()]
        for idx, desc in enumerate(paragraphs):
            scene_num = idx // 10 + 1
            shot_num = idx % 10 + 1
            shots_by_scene[scene_num].append((shot_num, desc))
    output_dir = os.path.join("output", "video_clips")
    os.makedirs(output_dir, exist_ok=True)
    scene_video_paths: list[str] = []
    for scene_num, scene_shots in sorted(shots_by_scene.items()):
        shot_video_paths: list[str] = []
        for shot_num, description in scene_shots:
            image_name = f"scene_{scene_num}_shot_{shot_num}.png"
            image_path = os.path.join("output", "storyboard_images", image_name)
            if os.path.exists(image_path):
                video_path = generate_video_clip(description, image_path, scene_num, shot_num, project, location)
                shot_video_paths.append(video_path)
            else:
                print(f"Warning: Storyboard image not found at {image_path} for Scene {scene_num}, Shot {shot_num}")
        if shot_video_paths:
            concat_list_path = os.path.join(output_dir, f"concat_scene_{scene_num}.txt")
            with open(concat_list_path, "w", encoding="utf-8") as cf:
                for vp in shot_video_paths:
                    cf.write(f"file '{os.path.basename(vp)}'\n")
            scene_video_path = os.path.join(output_dir, f"scene_{scene_num:03d}.mp4")
            (ffmpeg.input(concat_list_path, format='concat', safe=0)
             .output(scene_video_path, c='copy')
             .run(overwrite_output=True))
            for vp in shot_video_paths:
                os.remove(vp)
            os.remove(concat_list_path)
            scene_video_paths.append(scene_video_path)
    if scene_video_paths:
        concat_all_path = os.path.join(output_dir, "concat_all.txt")
        with open(concat_all_path, "w", encoding="utf-8") as cf:
            for vp in scene_video_paths:
                cf.write(f"file '{os.path.basename(vp)}'\n")
        final_path = os.path.join(output_dir, "combined_video.mp4")
        (ffmpeg.input(concat_all_path, format='concat', safe=0)
         .output(final_path, c='copy')
         .run(overwrite_output=True))
        for vp in scene_video_paths:
            os.remove(vp)
        os.remove(concat_all_path)
        print(f"Video synthesis complete. Final video at {final_path}")
        return final_path
    print("No video clips were generated from the storyboard.")
    return None


def generate_soundtrack_for_project(schema_file: str, project: str, location: str) -> str:
    """Generate soundtracks for each scene based on the narrative schema."""
    output_dir = os.path.join("output", "soundtracks")
    os.makedirs(output_dir, exist_ok=True)
    generate_soundtrack(project, location, schema_file, output_dir)
    return output_dir


def generate_voiceover_for_project(screenplay_file: str, project: str) -> Optional[str]:
    """Generate a single voiceover MP3 for the entire screenplay."""
    output_dir = os.path.join("output", "voiceover")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(screenplay_file))[0]
    output_path = os.path.join(output_dir, f"{base_name}_voiceover.mp3")
    generate_voiceover(project, screenplay_file, output_path)
    return output_path


def assemble_final_film(
    video_clips_dir: str,
    voiceover_dir: str,
    soundtrack_dir: str,
    project: str,
) -> str:
    """Assemble the final film from synthesized video clips, voiceover, and soundtrack."""
    output_dir = os.path.join("output", "final_film")
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{project}_final_film.mp4"
    assemble_film(video_clips_dir, voiceover_dir, soundtrack_dir, output_dir, output_filename)
    return os.path.join(output_dir, output_filename)
