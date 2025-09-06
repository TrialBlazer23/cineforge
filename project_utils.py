"""Project state management helpers for the CineForge pipeline.

This module defines a simplified backend for tracking the status of each
pipeline step in a JSON file per project. It includes functions to
initialize a project, update the status of individual steps, and mirror
important output artefacts to top-level pointers within the state.

The canonical pipeline steps are extended beyond the basic four to
include video synthesis, soundtrack generation, voiceover generation,
and final film assembly.
"""

import os
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional


PROJECTS_DIR = "output/projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

# Canonical step keys for the extended pipeline
PIPELINE_STEPS = [
    "narrative_deconstructed",  # outputs: schema_file
    "screenplay_generated",     # outputs: screenplay_file
    "storyboard_generated",     # outputs: storyboard_file
    "visual_assets_generated",  # outputs: images_dir (or counts)
    "video_synthesized",        # outputs: video_file
    "soundtrack_generated",     # outputs: soundtrack_dir
    "voiceover_generated",      # outputs: voiceover_file
    "final_film_assembled",     # outputs: final_film_file
]


def _now_iso() -> str:
    """Return the current UTC time in ISO 8601 format with a 'Z' suffix."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_project_path(project_name: str) -> str:
    """Return the filesystem path where the project state JSON should be stored."""
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", project_name)
    return os.path.join(PROJECTS_DIR, f"{safe_name}.json")


def _default_state(project_name: str) -> Dict[str, Any]:
    """Construct a default state dictionary for a new project."""
    return {
        "project": project_name,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "steps": {
            step: {
                "status": "not_started",
                "started_at": None,
                "finished_at": None,
                "error": None,
                "outputs": {},
            }
            for step in PIPELINE_STEPS
        },
        "artifacts": {
            "schema_file": None,
            "screenplay_file": None,
            "storyboard_file": None,
            "video_file": None,
            "soundtrack_dir": None,
            "voiceover_file": None,
            "final_film_file": None,
        },
        "history": [],
    }


def save_project(project_name: str, state: Dict[str, Any]) -> None:
    """Write the project state to disk atomically."""
    path = get_project_path(project_name)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def load_project(project_name: str) -> Optional[Dict[str, Any]]:
    """Load the project state from disk, or return None if missing."""
    path = get_project_path(project_name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def init_project(project_name: str) -> Dict[str, Any]:
    """Ensure that a state file exists for the given project and return it."""
    state = load_project(project_name)
    if state is None:
        state = _default_state(project_name)
        save_project(project_name, state)
    return state


def ensure_project(project_name: str) -> Dict[str, Any]:
    """Alias for init_project for backward compatibility."""
    return init_project(project_name)


def update_step(
    project_name: str,
    step_key: str,
    *,
    status: Optional[str] = None,
    outputs: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update the status, outputs and/or error for a pipeline step on the given project.

    Parameters
    ----------
    project_name: str
        The identifier for the project whose state should be updated.
    step_key: str
        The canonical or custom key representing the pipeline step.
    status: Optional[str]
        The new status ("running", "success", or "failed").
    outputs: Optional[dict]
        A mapping of output artefacts produced by the step.
    error: Optional[str]
        An error message if the step failed.

    Returns
    -------
    dict
        The updated project state.
    """
    state = ensure_project(project_name)
    steps = state.setdefault("steps", {})
    if step_key not in steps:
        # allow registration of custom steps
        steps[step_key] = {
            "status": "not_started",
            "started_at": None,
            "finished_at": None,
            "error": None,
            "outputs": {},
        }
    step = steps[step_key]
    now = _now_iso()
    prev_status = step.get("status")
    if status:
        step["status"] = status
        if status == "running" and step["started_at"] is None:
            step["started_at"] = now
        if status in {"success", "failed"}:
            step["finished_at"] = now
        state.setdefault("history", []).append({
            "time": now,
            "event": f"step:{step_key}:{status}",
            "meta": {"prev": prev_status},
        })
    if outputs:
        step_outputs = step.setdefault("outputs", {})
        step_outputs.update(outputs)
        # Mirror important artefacts to top-level keys if present
        artifacts = state.setdefault("artifacts", {})
        for key in [
            "schema_file",
            "screenplay_file",
            "storyboard_file",
            "video_file",
            "soundtrack_dir",
            "voiceover_file",
            "final_film_file",
        ]:
            if key in outputs and outputs[key]:
                artifacts[key] = outputs[key]
    if error:
        step["error"] = error
        # If no explicit status set, mark as failed
        if not status:
            step["status"] = "failed"
            step["finished_at"] = now
        state.setdefault("history", []).append({
            "time": now,
            "event": f"step:{step_key}:error",
            "meta": {"error": error[:500]},
        })
    state["updated_at"] = now
    save_project(project_name, state)
    return state