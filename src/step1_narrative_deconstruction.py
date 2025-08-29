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
    derive_project_name_from_story_file,
)


class NarrativeDeconstructor:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        v = self.cfg.get("vertex", {})
        self.project = v.get("project")
        self.location = v.get("location", "us-central1")
        self.model_name = v.get("models", {}).get("narrative", "gemini-2.5-pro")
        self.gen_cfg = v.get("generation", {}).get("narrative", {"max_output_tokens": 8192, "temperature": 0.2, "top_p": 1.0})

    def _first_pass(self, story_content: str) -> str:
        vertexai.init(project=self.project, location=self.location)
        model = GenerativeModel(self.model_name)
        prompt = f"""
Analyze the following story and provide a summary, a list of primary characters with brief descriptions, key locations, the overarching plot points, and the story's prevailing tone or genre.

Story:
{story_content}
"""
        response = model.generate_content([prompt], generation_config=self.gen_cfg)
        return response.text

    def _second_pass(self, summary_text: str) -> str:
        vertexai.init(project=self.project, location=self.location)
        model = GenerativeModel(self.model_name)
        prompt = f"""
Based on the following summary and key elements, generate a hierarchical outline of the story.
For each character and location, provide a detailed visual description. This should include physical attributes, clothing, typical expressions, and any other details that would help in generating consistent images.
Break the overall plot into a sequence of distinct scenes, each with a brief summary of its constituent beats.
The final output must be a consistent, parsable JSON object.

The JSON object should have the following schema:
{{
  "title": "The Last Sundown",
  "logline": "In a desolate future, a lone wanderer must...",
  "characters": [
    {{
      "name": "Elara",
      "description": "A stoic survivor in her late 20s, with piercing blue eyes, a weathered face, and a scar across her left eyebrow. She wears practical, patched-up clothing suited for the harsh environment: a dusty leather jacket, cargo pants, and sturdy boots. Her expression is typically one of cautious vigilance."
    }},
    {{
      "name": "Kael",
      "description": "An aging, cynical scavenger in his early 60s, with a grizzled beard, and a perpetual squint from years in the sun. He is often seen in a tattered duster coat and carries a modified energy rifle. His face is etched with the lines of past hardships, but his eyes still hold a spark of cunning."
    }}
  ],
  "locations": [
    {{
        "name": "The Dustbowl Outpost",
        "description": "A ramshackle settlement built from salvaged metal and scrap. The central marketplace is a chaotic maze of stalls, lit by flickering neon signs and powered by a sputtering generator. The air is thick with the smell of ozone and roasted strange meats."
    }}
  ],
  "scenes": []
}}

Summary and Key Elements:
{summary_text}
"""
        response = model.generate_content([prompt], generation_config=self.gen_cfg)
        return response.text

    def run(self, story_path: str, project_name: str | None = None) -> str:
        # Read story content
        with open(story_path, "r", encoding="utf-8") as f:
            story_content = f.read()

        project_name = project_name or derive_project_name_from_story_file(story_path)
        init_project(project_name)
        update_step(project_name, "narrative_deconstructed", status="running")

        try:
            summary = self._first_pass(story_content)
            outline = self._second_pass(summary)

            # Normalize fenced code blocks like ```json ... ```
            outline_str = outline.strip()
            if outline_str.startswith("```json"):
                outline_str = outline_str[7:]
            if outline_str.endswith("```"):
                outline_str = outline_str[:-3]

            schema = json.loads(outline_str)

            # Output path from central config
            out_dir = get_path(self.cfg, "narrative_schema_dir")
            os.makedirs(out_dir, exist_ok=True)
            out_fn = os.path.splitext(os.path.basename(story_path))[0] + "_schema.json"
            out_path = os.path.join(out_dir, out_fn)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2)

            update_step(
                project_name,
                "narrative_deconstructed",
                status="success",
                outputs={"schema_file": out_path},
            )
            return out_path
        except Exception as e:
            update_step(project_name, "narrative_deconstructed", status="failed", error=str(e))
            raise


def main():
    parser = argparse.ArgumentParser(description="Deconstruct a narrative from a story file.")
    parser.add_argument("story_file", help="Path to the story text file.")
    parser.add_argument("--config", help="Path to central config (json|yaml).")
    parser.add_argument("--project-name", help="Optional project name to use.")

    args = parser.parse_args()
    cfg = load_config(args.config)

    # Allow CLI override of Vertex settings via env handled in load_config
    deconstructor = NarrativeDeconstructor(cfg)
    try:
        out_path = deconstructor.run(args.story_file, args.project_name)
        print(f"Narrative schema saved to {out_path}")
    except Exception as e:
        print("Error: Failed to deconstruct narrative.")
        print(str(e))
        raise


if __name__ == "__main__":
    main()
