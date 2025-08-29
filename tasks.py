import os
import json
from typing import Optional, Tuple
from celery import states

from celery_app import celery_app

# Import pipeline functions
from src.pipeline import (
    deconstruct_narrative,
    generate_screenplay_and_storyboard,
    generate_visual_assets,
    synthesize_video_from_storyboard,
)
from project_utils import (
    init_project,
    update_step,
    derive_project_name_from_story_file,
    derive_project_name_from_schema_file,
    derive_project_name_from_storyboard_file,
)


def _require_env(project: Optional[str], location: Optional[str]) -> Tuple[str, str]:
    proj = project or os.environ.get("VERTEX_PROJECT_ID")
    loc = location or os.environ.get("VERTEX_LOCATION", "us-central1")
    if not proj:
        raise ValueError("VERTEX_PROJECT_ID is required")
    return proj, loc


@celery_app.task(
    bind=True,
    name="cineforge.deconstruct_narrative_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def deconstruct_narrative_task(self, story_file: str, project: Optional[str] = None, location: Optional[str] = None):
    try:
        project, location = _require_env(project, location)
        project_name = derive_project_name_from_story_file(story_file)
        init_project(project_name)
        update_step(project_name, "narrative_deconstructed", status="running")
        self.update_state(state=states.STARTED, meta={"stage": "deconstruct", "msg": "Starting narrative deconstruction"})
        schema_file = deconstruct_narrative(story_file, project, location)
        update_step(project_name, "narrative_deconstructed", status="success", outputs={"schema_file": schema_file})
        return {"schema_file": schema_file, "project": project_name}
    except Exception as e:
        try:
            project_name = derive_project_name_from_story_file(story_file)
            update_step(project_name, "narrative_deconstructed", status="failed", error=str(e))
        except Exception:
            pass
        self.update_state(state=states.FAILURE, meta={"exc": str(e)})
        raise


@celery_app.task(
    bind=True,
    name="cineforge.generate_screenplay_and_storyboard_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_screenplay_and_storyboard_task(self, schema_file: str, project: Optional[str] = None, location: Optional[str] = None):
    try:
        project, location = _require_env(project, location)
        project_name = derive_project_name_from_schema_file(schema_file)
        init_project(project_name)
        update_step(project_name, "screenplay_generated", status="running")
        update_step(project_name, "storyboard_generated", status="running")
        self.update_state(state=states.STARTED, meta={"stage": "script+storyboard", "msg": "Generating screenplay and storyboard"})
        screenplay_file, storyboard_file = generate_screenplay_and_storyboard(schema_file, project, location)
        update_step(project_name, "screenplay_generated", status="success", outputs={"screenplay_file": screenplay_file})
        update_step(project_name, "storyboard_generated", status="success", outputs={"storyboard_file": storyboard_file})
        return {
            "screenplay_file": screenplay_file,
            "storyboard_file": storyboard_file,
            "project": project_name,
        }
    except Exception as e:
        try:
            project_name = derive_project_name_from_schema_file(schema_file)
            update_step(project_name, "screenplay_generated", status="failed", error=str(e))
            update_step(project_name, "storyboard_generated", status="failed", error=str(e))
        except Exception:
            pass
        self.update_state(state=states.FAILURE, meta={"exc": str(e)})
        raise


@celery_app.task(
    bind=True,
    name="cineforge.generate_visual_assets_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_visual_assets_task(self, storyboard_file: str, schema_file: str, project: Optional[str] = None, location: Optional[str] = None, style: Optional[str] = None):
    try:
        project, location = _require_env(project, location)
        project_name = derive_project_name_from_storyboard_file(storyboard_file)
        init_project(project_name)
        update_step(project_name, "visual_assets_generated", status="running")
        self.update_state(state=states.STARTED, meta={"stage": "assets", "msg": "Generating visual assets"})
        generate_visual_assets(storyboard_file, schema_file, project, location, style=style)
        update_step(project_name, "visual_assets_generated", status="success")
        return {"ok": True, "project": project_name}
    except Exception as e:
        try:
            project_name = derive_project_name_from_storyboard_file(storyboard_file)
            update_step(project_name, "visual_assets_generated", status="failed", error=str(e))
        except Exception:
            pass
        self.update_state(state=states.FAILURE, meta={"exc": str(e)})
        raise


@celery_app.task(
    bind=True,
    name="cineforge.full_pipeline_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 1},
)
def full_pipeline_task(self, story_file: str, project: Optional[str] = None, location: Optional[str] = None, style: Optional[str] = None):
    """Run the whole pipeline sequentially as a chain inside a single task."""
    try:
        project, location = _require_env(project, location)
        project_name = derive_project_name_from_story_file(story_file)
        init_project(project_name)
        self.update_state(state=states.STARTED, meta={"stage": "deconstruct", "progress": 0.1, "msg": "Deconstructing narrative"})
        update_step(project_name, "narrative_deconstructed", status="running")
        schema_file = deconstruct_narrative(story_file, project, location)
        update_step(project_name, "narrative_deconstructed", status="success", outputs={"schema_file": schema_file})
        self.update_state(state=states.STARTED, meta={"stage": "script+storyboard", "progress": 0.45, "msg": "Generating screenplay & storyboard"})
        update_step(project_name, "screenplay_generated", status="running")
        update_step(project_name, "storyboard_generated", status="running")
        screenplay_file, storyboard_file = generate_screenplay_and_storyboard(schema_file, project, location)
        update_step(project_name, "screenplay_generated", status="success", outputs={"screenplay_file": screenplay_file})
        update_step(project_name, "storyboard_generated", status="success", outputs={"storyboard_file": storyboard_file})
        self.update_state(state=states.STARTED, meta={"stage": "assets", "progress": 0.75, "msg": "Generating visual assets"})
        update_step(project_name, "visual_assets_generated", status="running")
        generate_visual_assets(storyboard_file, schema_file, project, location, style=style)
        update_step(project_name, "visual_assets_generated", status="success")
        self.update_state(state=states.STARTED, meta={"stage": "video", "progress": 0.9, "msg": "Synthesizing video (placeholder)"})
        video_file = synthesize_video_from_storyboard(storyboard_file, project, location)
        if video_file:
            update_step(project_name, "video_synthesized", status="success", outputs={"video_file": video_file})
        else:
            update_step(project_name, "video_synthesized", status="failed", error="Video synthesis not implemented")
        return {
            "schema_file": schema_file,
            "screenplay_file": screenplay_file,
            "storyboard_file": storyboard_file,
            "video_file": video_file,
            "project": project_name,
        }
    except Exception as e:
        try:
            project_name = derive_project_name_from_story_file(story_file)
            update_step(project_name, "video_synthesized", status="failed", error=str(e))
        except Exception:
            pass
        self.update_state(state=states.FAILURE, meta={"exc": str(e)})
        raise
