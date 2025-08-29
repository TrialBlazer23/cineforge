import os
import sys
import json
from fastapi import FastAPI, HTTPException
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models
from vertexai.vision_models import ImageGenerationModel

# Minimal FastAPI app so gunicorn can load `api:app`
try:
    # Make utils importable and load .env for local runs
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    import utils  # type: ignore
    utils.load_env()
except Exception:
    pass

app = FastAPI(title="CineForge API", version="0.1.0")
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


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---- Async task endpoints (Celery) ----
try:
    from celery_app import celery_app as _celery_app
    from tasks import (
        deconstruct_narrative_task,
        generate_screenplay_and_storyboard_task,
        generate_visual_assets_task,
        full_pipeline_task,
    )
    from celery_app import ping as celery_ping
except Exception:
    deconstruct_narrative_task = None  # type: ignore
    generate_screenplay_and_storyboard_task = None  # type: ignore
    generate_visual_assets_task = None  # type: ignore
    full_pipeline_task = None  # type: ignore
    _celery_app = None  # type: ignore
    celery_ping = None  # type: ignore


@app.post("/tasks/pipeline")
def submit_full_pipeline(story_file: str, project: str | None = None, location: str | None = None, style: str | None = None):
    if full_pipeline_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = full_pipeline_task.delay(story_file, project=project, location=location, style=style)
    return {"task_id": res.id}


@app.post("/tasks/deconstruct")
def submit_deconstruct(story_file: str, project: str | None = None, location: str | None = None):
    if deconstruct_narrative_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = deconstruct_narrative_task.delay(story_file, project=project, location=location)
    return {"task_id": res.id}


@app.post("/tasks/screenplay")
def submit_screenplay(schema_file: str, project: str | None = None, location: str | None = None):
    if generate_screenplay_and_storyboard_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = generate_screenplay_and_storyboard_task.delay(schema_file, project=project, location=location)
    return {"task_id": res.id}


@app.post("/tasks/assets")
def submit_assets(storyboard_file: str, schema_file: str, project: str | None = None, location: str | None = None, style: str | None = None):
    if generate_visual_assets_task is None:
        raise HTTPException(status_code=503, detail="Task queue not available")
    res = generate_visual_assets_task.delay(storyboard_file, schema_file, project=project, location=location, style=style)
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

# ---- Project state endpoints ----
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
def api_update_step(project: str, step: str, status: str | None = None, outputs: str | None = None, error: str | None = None):
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

try:
    from src.pipeline import (
        deconstruct_narrative,
        generate_screenplay_and_storyboard,
        generate_visual_assets,
        synthesize_video_from_storyboard,
    )
except ImportError:
    # Fallback functions if pipeline import fails
    deconstruct_narrative = None  # type: ignore
    generate_screenplay_and_storyboard = None  # type: ignore
    generate_visual_assets = None  # type: ignore
    synthesize_video_from_storyboard = None  # type: ignore

