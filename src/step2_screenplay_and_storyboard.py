import argparse
import json
import os
from typing import Any, Dict

import vertexai
from vertexai.generative_models import GenerativeModel

from src.config import load_config, get_path
from project_utils import (
    init_project,
    update_step,
    derive_project_name_from_schema_file,
)


class ScreenplayGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        v = self.cfg.get("vertex", {})
        self.project = v.get("project")
        self.location = v.get("location", "us-central1")
        self.model_name = v.get("models", {}).get("screenplay", "gemini-2.5-flash")
        self.gen_cfg = v.get("generation", {}).get(
            "screenplay", {"max_output_tokens": 8192, "temperature": 0.7, "top_p": 1.0}
        )

    def run(self, narrative_schema: Dict[str, Any]) -> str:
        vertexai.init(project=self.project, location=self.location)
        model = GenerativeModel(self.model_name)
        prompt = (
            "Based on the following narrative schema, write a detailed screenplay. "
            "The screenplay should be formatted correctly, with scene headings, character names, dialogue, and action descriptions.\n\n"
            f"Narrative Schema:\n{json.dumps(narrative_schema)}"
        )
        response = model.generate_content([prompt], generation_config=self.gen_cfg)
        return response.text


class StoryboardGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        v = self.cfg.get("vertex", {})
        self.project = v.get("project")
        self.location = v.get("location", "us-central1")
        self.model_name = v.get("models", {}).get("storyboard", "gemini-2.5-flash")
        self.gen_cfg = v.get("generation", {}).get(
            "storyboard", {"max_output_tokens": 8192, "temperature": 0.7, "top_p": 1.0}
        )

    def run(self, screenplay_content: str) -> str:
        vertexai.init(project=self.project, location=self.location)
        model = GenerativeModel(self.model_name)
        prompt = (
            "Based on the following screenplay, create a detailed storyboard. "
            "The storyboard should break down each scene into individual shots, with a description of the camera angle, shot type, and action for each shot.\n\n"
            f"Screenplay:\n{screenplay_content}"
        )
        response = model.generate_content([prompt], generation_config=self.gen_cfg)
        return response.text


def main():
    parser = argparse.ArgumentParser(description="Generate a screenplay and storyboard from a narrative schema.")
    parser.add_argument("schema_file", help="Path to the narrative schema JSON file.")
    parser.add_argument("--config", help="Path to central config (json|yaml).")
    parser.add_argument("--project-name", help="Optional project name to use.")

    args = parser.parse_args()
    cfg = load_config(args.config)

    # Load schema
    try:
        with open(args.schema_file, "r", encoding="utf-8") as f:
            narrative_schema = json.load(f)
    except FileNotFoundError:
        print(f"Error: Schema file not found at {args.schema_file}")
        return

    project_name = args.project_name or derive_project_name_from_schema_file(args.schema_file)
    init_project(project_name)

    # Generate screenplay
    print("Generating screenplay...")
    update_step(project_name, "screenplay_generated", status="running")
    try:
        screenplay_content = ScreenplayGenerator(cfg).run(narrative_schema)
        screenplay_dir = get_path(cfg, "screenplay_dir")
        os.makedirs(screenplay_dir, exist_ok=True)
        screenplay_filename = os.path.splitext(os.path.basename(args.schema_file))[0].replace("_schema", "") + "_screenplay.txt"
        screenplay_output_path = os.path.join(screenplay_dir, screenplay_filename)
        with open(screenplay_output_path, "w", encoding="utf-8") as f:
            f.write(screenplay_content)
        update_step(
            project_name,
            "screenplay_generated",
            status="success",
            outputs={"screenplay_file": screenplay_output_path},
        )
        print(f"Screenplay saved to {screenplay_output_path}")
    except Exception as e:
        update_step(project_name, "screenplay_generated", status="failed", error=str(e))
        raise

    # Generate storyboard
    print("\nGenerating storyboard...")
    update_step(project_name, "storyboard_generated", status="running")
    try:
        storyboard_content = StoryboardGenerator(cfg).run(screenplay_content)
        storyboard_dir = get_path(cfg, "storyboard_text_dir")
        os.makedirs(storyboard_dir, exist_ok=True)
        storyboard_filename = os.path.splitext(os.path.basename(args.schema_file))[0].replace("_schema", "") + "_storyboard.txt"
        storyboard_output_path = os.path.join(storyboard_dir, storyboard_filename)
        with open(storyboard_output_path, "w", encoding="utf-8") as f:
            f.write(storyboard_content)
        update_step(
            project_name,
            "storyboard_generated",
            status="success",
            outputs={"storyboard_file": storyboard_output_path},
        )
        print(f"Storyboard saved to {storyboard_output_path}")
    except Exception as e:
        update_step(project_name, "storyboard_generated", status="failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
