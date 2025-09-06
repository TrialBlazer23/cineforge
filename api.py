"""FastAPI application for the CineForge service.

This API exposes endpoints to initiate asynchronous Celery tasks for each
major stage of the filmmaking pipeline: narrative deconstruction,
screenplay/storyboard generation, visual asset generation, video
synthesis, soundtrack and voice‑over generation, and final assembly of
the finished film.  It also provides simple health and project state
endpoints.
"""

import os
import sys
import json
from typing import Optional

from fastapi import FastAPI, HTTPException

# Import Vertex AI modules for side effects (e.g. environment loading).  These
# imports mirror the original API module but are not directly used here.
import vertexai  # noqa: F401
from vertexai.preview.generative_models import GenerativeModel, Part  # noqa: F401
import vertexai.preview.generative_models as generative_models  # noqa: F401
from vertexai.vision_models import ImageGenerationModel  # noqa: F401

# Load environment variables early so that project_utils and pipeline can find
# credentials when invoked via Celery tasks.  We wrap this in a try/except
# because utils may not be available in all deployment contexts.
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    import utils  # type: ignore

    utils.load_env()
except Exception:
    pass

app = FastAPI(title="CineForge API", version="0.2.0")

# Project state helpers.  These functions may not be importable when the
# application is compiled for documentation, so we handle import errors
# gracefully and set them to None in that case.
try:
    from project_utils import (
        list_projects,
        load_project,
        update_step,
        init_project,
        migrate_json_states_to_sqlite,
    )
except Exception:
    list_projects = load_project = update_step = init_project = migrate_json_states_to_sqlite = None  # type: ignore

# Celery tasks and ping endpoint.  If Celery or our tasks cannot be
# imported, we expose 503 errors for those endpoints.
try:
    from celery_app import celery_app as _celery_app
    from tasks import (
        deconstruct_narrative_task,
        generate_screenplay_and_storyboard_task,
        generate_visual_assets_task,
        generate_soundtrack_task,
        generate_voiceover_task,
        assemble_final_film_task,
        full_pipeline_task,
    )
    from celery_app import ping as celery_ping
except Exception:
    deconstruct_narrative_task = None  # type: ignore
    generate_screenplay_and_storyboard_task = None  # type: ignore
    generate_visual_assets_task = None  # type: ignore
    generate_soundtrack_task = None  # type: ignore
    generate_voiceover_task = None  # type: ignore
    assemble_final_film_task = None  # type: ignore
    full_pipeline_task = None  # type: ignore
    _celery_app = None  # type: ignore
    celery_ping = None  # type: ignore


@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Async task submission endpoints
#
# Each of these endpoints returns a JSON payload containing the ID of the
# corresponding Celery task.  Clients can poll ``/tasks/{task_id}`` to check
# the status and result of the task.

@app.post("/tasks/pipeline")
def submit_full_pipeline(story_file: str, project: Optional[str] = None, location: Optional[str] = None, style: Optional[str] = None):
    if full_pipeline_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = full_pipeline_task.delay(story_file, project=project, location=location, style=style)
    return {"task_id": res.id}


@app.post("/tasks/deconstruct")
def submit_deconstruct(story_file: str, project: Optional[str] = None, location: Optional[str] = None):
    if deconstruct_narrative_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = deconstruct_narrative_task.delay(story_file, project=project, location=location)
    return {"task_id": res.id}


@app.post("/tasks/screenplay")
def submit_screenplay(schema_file: str, project: Optional[str] = None, location: Optional[str] = None):
    if generate_screenplay_and_storyboard_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = generate_screenplay_and_storyboard_task.delay(schema_file, project=project, location=location)
    return {"task_id": res.id}


@app.post("/tasks/assets")
def submit_assets(storyboard_file: str, schema_file: str, project: Optional[str] = None, location: Optional[str] = None, style: Optional[str] = None):
    if generate_visual_assets_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = generate_visual_assets_task.delay(storyboard_file, schema_file, project=project, location=location, style=style)
    return {"task_id": res.id}


@app.post("/tasks/soundtrack")
def submit_soundtrack(schema_file: str, project: Optional[str] = None, location: Optional[str] = None):
    """Submit a task to generate a soundtrack from a narrative schema."""
    if generate_soundtrack_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = generate_soundtrack_task.delay(schema_file, project=project, location=location)
    return {"task_id": res.id}


@app.post("/tasks/voiceover")
def submit_voiceover(screenplay_file: str, project: Optional[str] = None):
    """Submit a task to generate a voice‑over from a screenplay file."""
    if generate_voiceover_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = generate_voiceover_task.delay(screenplay_file, project=project)
    return {"task_id": res.id}


@app.post("/tasks/assemble")
def submit_assembly(video_clips_dir: str, voiceover_dir: str, soundtrack_dir: str, project: str):
    """Submit a task to assemble the final film from pre‑generated components."""
    if assemble_final_film_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = assemble_final_film_task.delay(video_clips_dir, voiceover_dir, soundtrack_dir, project=project)
    return {"task_id": res.id}


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    if _celery_app is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    ar = _celery_app.AsyncResult(task_id)
    payload = {"id": task_id, "state": ar.state}
    if ar.state in {"SUCCESS", "FAILURE"}:
        try:
            payload["result"] = ar.result if ar.state == "SUCCESS" else str(ar.result)
        except Exception:
            pass
    return payload


@app.post("/tasks/ping")
def submit_ping():
    if celery_ping is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = celery_ping.delay()
    return {"task_id": res.id}


# -----------------------------------------------------------------------------
# Project state endpoints

@app.get("/projects")
def api_list_projects():
    if list_projects is None:
        raise HTTPException(status_code=500, detail="State manager unavailable")
    return {"projects": list_projects()}


@app.get("/projects/{project}")
def api_get_project(project: str):
    if load_project is None:
        raise HTTPException(status_code=500, detail="State manager unavailable")
    state = load_project(project)
    if state is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return state


@app.post("/projects/{project}/init")
def api_init_project(project: str):
    if init_project is None:
        raise HTTPException(status_code=500, detail="State manager unavailable")
    return init_project(project)


@app.post("/projects/{project}/steps/{step}")
def api_update_step(project: str, step: str, status: Optional[str] = None, outputs: Optional[str] = None, error: Optional[str] = None):
    if update_step is None:
        raise HTTPException(status_code=500, detail="State manager unavailable")
    outputs_dict = None
    try:
        if outputs:
            outputs_dict = json.loads(outputs)
    except Exception:
        outputs_dict = None
    return update_step(project, step, status=status, outputs=outputs_dict, error=error)


@app.post("/projects/migrate/json-to-sqlite")
def api_migrate_json_to_sqlite():
    if migrate_json_states_to_sqlite is None:
        raise HTTPException(status_code=500, detail="State manager unavailable")
    try:
        summary = migrate_json_states_to_sqlite()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))