?"]\[i+:?{mport os
import json
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

PROJECTS_DIR = "output/projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

# Backend selection: json (default) or sqlite
STATE_BACKEND = os.environ.get("STATE_BACKEND", "json").strip().lower()
DB_PATH = os.environ.get("STATE_DB_PATH", os.path.join(PROJECTS_DIR, "state.db"))

# Canonical step keys for the pipeline
PIPELINE_STEPS = [
    "narrative_deconstructed",   # outputs: schema_file
    "screenplay_generated",      # outputs: screenplay_file
    "storyboard_generated",      # outputs: storyboard_file
    "visual_assets_generated",   # outputs: images_dir (or counts)
    "video_synthesized",         # outputs: video_file (when implemented)
]


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def get_project_path(project_name: str) -> str:
    """Gets the full path for a project."""
    safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
    return os.path.join(PROJECTS_DIR, f"{safe_project_name}.json")

def save_project(project_name: str, project_data: Dict[str, Any]) -> None:
    """Saves the project data to a file."""
    if STATE_BACKEND == "sqlite":
        # For sqlite backend, ignore full-save; use update_step/init functions instead
        _sqlite_upsert_full(project_data)
        return
    project_path = get_project_path(project_name)
    # Write atomically to reduce risk of corruption
    tmp_path = project_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, project_path)

def load_project(project_name: str) -> Optional[Dict[str, Any]]:
    """Loads project data from a file."""
    if STATE_BACKEND == "sqlite":
        return _sqlite_load_project(project_name)
    project_path = get_project_path(project_name)
    if os.path.exists(project_path):
        with open(project_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def list_projects() -> list[str]:
    """Lists all saved projects."""
    if STATE_BACKEND == "sqlite":
        return _sqlite_list_projects()
    projects = []
    for filename in os.listdir(PROJECTS_DIR):
        if filename.endswith(".json"):
            project_name = os.path.splitext(filename)[0]
            projects.append(project_name)
    return projects

def delete_project(project_name: str) -> None:
    """Deletes a project file."""
    if STATE_BACKEND == "sqlite":
        _sqlite_delete_project(project_name)
        return
    project_path = get_project_path(project_name)
    if os.path.exists(project_path):
        os.remove(project_path)


# ---- Project state helpers ----

def _default_state(project_name: str) -> Dict[str, Any]:
    return {
        "project": project_name,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "steps": {
            step: {
                "status": "not_started",  # not_started | running | success | failed
                "started_at": None,
                "finished_at": None,
                "error": None,
                "outputs": {},
            }
            for step in PIPELINE_STEPS
        },
        "artifacts": {
            # convenience top-level pointers
            "schema_file": None,
            "screenplay_file": None,
            "storyboard_file": None,
            "video_file": None,
        },
        "history": [],  # list of {time, event, meta}
    }


def init_project(project_name: str) -> Dict[str, Any]:
    """Create a new project state file if missing, return the state."""
    if STATE_BACKEND == "sqlite":
        _sqlite_init()
        _sqlite_init_project(project_name)
        return _sqlite_load_project(project_name) or _default_state(project_name)
    else:
        state = load_project(project_name)
        if state is None:
            state = _default_state(project_name)
            save_project(project_name, state)
        return state


def ensure_project(project_name: str) -> Dict[str, Any]:
    return init_project(project_name)


def update_step(
    project_name: str,
    step_key: str,
    *,
    status: Optional[str] = None,
    outputs: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Update step status/outputs/error with timestamps. Returns new state."""
    if STATE_BACKEND == "sqlite":
        _sqlite_init()
        _sqlite_update_step(project_name, step_key, status=status, outputs=outputs, error=error)
        return _sqlite_load_project(project_name) or _default_state(project_name)

    state = ensure_project(project_name)
    steps = state.setdefault("steps", {})
    if step_key not in steps:
        # Allow custom steps beyond the canonical list
        steps[step_key] = {"status": "not_started", "started_at": None, "finished_at": None, "error": None, "outputs": {}}

    step = steps[step_key]
    now = _now_iso()

    if status:
        prev = step.get("status")
        step["status"] = status
        if status == "running" and step.get("started_at") is None:
            step["started_at"] = now
        if status in {"success", "failed"}:
            step["finished_at"] = now
        state.setdefault("history", []).append({
            "time": now,
            "event": f"step:{step_key}:{status}",
            "meta": {"prev": prev},
        })

    if outputs:
        step_outputs = step.setdefault("outputs", {})
        step_outputs.update(outputs)
        # Mirror important artifacts to top-level shortcuts if present
        arts = state.setdefault("artifacts", {})
        for k in ("schema_file", "screenplay_file", "storyboard_file", "video_file"):
            if k in outputs and outputs[k]:
                arts[k] = outputs[k]

    if error is not None:
        step["error"] = error
        if status is None:
            # If caller only sets error, mark as failed and finish
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


def derive_project_name_from_story_file(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r'[^a-zA-Z0-9_-]', '_', base)


def derive_project_name_from_schema_file(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"_schema$", "", base)
    return re.sub(r'[^a-zA-Z0-9_-]', '_', base)


def derive_project_name_from_storyboard_file(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"_storyboard$", "", base)
    return re.sub(r'[^a-zA-Z0-9_-]', '_', base)


# -----------------
# SQLite operations
# -----------------

def _sqlite_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_init() -> None:
    with _sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS steps (
                project TEXT NOT NULL,
                step_key TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                error TEXT,
                outputs_json TEXT,
                PRIMARY KEY (project, step_key),
                FOREIGN KEY (project) REFERENCES projects(project) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                project TEXT PRIMARY KEY,
                schema_file TEXT,
                screenplay_file TEXT,
                storyboard_file TEXT,
                video_file TEXT,
                FOREIGN KEY (project) REFERENCES projects(project) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                time TEXT NOT NULL,
                event TEXT NOT NULL,
                meta_json TEXT,
                FOREIGN KEY (project) REFERENCES projects(project) ON DELETE CASCADE
            )
            """
        )
        conn.commit()


def _sqlite_init_project(project: str) -> None:
    now = _now_iso()
    with _sqlite_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO projects(project, created_at, updated_at) VALUES(?,?,?)", (project, now, now))
        cur.execute("INSERT OR IGNORE INTO artifacts(project) VALUES(?)", (project,))
        # Seed canonical steps if missing
        for step in PIPELINE_STEPS:
            cur.execute(
                "INSERT OR IGNORE INTO steps(project, step_key, status, started_at, finished_at, error, outputs_json) VALUES(?,?,?,?,?,?,?)",
                (project, step, "not_started", None, None, None, json.dumps({})),
            )
        conn.commit()


def _sqlite_update_project_ts(conn: sqlite3.Connection, project: str) -> None:
    conn.execute("UPDATE projects SET updated_at=? WHERE project=?", (_now_iso(), project))


def _sqlite_update_step(project: str, step_key: str, *, status: Optional[str], outputs: Optional[Dict[str, Any]], error: Optional[str]) -> None:
    _sqlite_init_project(project)
    now = _now_iso()
    with _sqlite_conn() as conn:
        cur = conn.cursor()
        # Fetch existing row
        cur.execute("SELECT status, started_at, finished_at, error, outputs_json FROM steps WHERE project=? AND step_key=?", (project, step_key))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO steps(project, step_key, status, started_at, finished_at, error, outputs_json) VALUES(?,?,?,?,?,?,?)",
                (project, step_key, "not_started", None, None, None, json.dumps({})),
            )
            outputs_json = {}
            curr_status = "not_started"
            started_at = None
            finished_at = None
            curr_error = None
        else:
            curr_status = row["status"]
            started_at = row["started_at"]
            finished_at = row["finished_at"]
            curr_error = row["error"]
            try:
                outputs_json = json.loads(row["outputs_json"]) if row["outputs_json"] else {}
            except Exception:
                outputs_json = {}

        new_status = curr_status
        new_started = started_at
        new_finished = finished_at
        new_error = curr_error

        if status:
            new_status = status
            if status == "running" and not started_at:
                new_started = now
            if status in {"success", "failed"}:
                new_finished = now
            conn.execute(
                "INSERT INTO history(project, time, event, meta_json) VALUES(?,?,?,?)",
                (project, now, f"step:{step_key}:{status}", json.dumps({"prev": curr_status})),
            )

        if outputs:
            outputs_json.update(outputs)
            # Mirror artifacts
            arts_updates = {k: v for k, v in outputs.items() if k in {"schema_file", "screenplay_file", "storyboard_file", "video_file"} and v}
            if arts_updates:
                set_clause = ", ".join([f"{k}=?" for k in arts_updates.keys()])
                conn.execute(f"UPDATE artifacts SET {set_clause} WHERE project=?", [*arts_updates.values(), project])

        if error is not None:
            new_error = error
            if not status:
                new_status = "failed"
                new_finished = now
            conn.execute(
                "INSERT INTO history(project, time, event, meta_json) VALUES(?,?,?,?)",
                (project, now, f"step:{step_key}:error", json.dumps({"error": (error or "")[:500]})),
            )

        cur.execute(
            "UPDATE steps SET status=?, started_at=?, finished_at=?, error=?, outputs_json=? WHERE project=? AND step_key=?",
            (new_status, new_started, new_finished, new_error, json.dumps(outputs_json), project, step_key),
        )
        _sqlite_update_project_ts(conn, project)
        conn.commit()


def _sqlite_list_projects() -> list[str]:
    _sqlite_init()
    with _sqlite_conn() as conn:
        rows = conn.execute("SELECT project FROM projects ORDER BY project").fetchall()
        return [r[0] for r in rows]


def _sqlite_load_project(project: str) -> Optional[Dict[str, Any]]:
    _sqlite_init()
    with _sqlite_conn() as conn:
        p = conn.execute("SELECT project, created_at, updated_at FROM projects WHERE project=?", (project,)).fetchone()
        if not p:
            return None
        arts = conn.execute("SELECT schema_file, screenplay_file, storyboard_file, video_file FROM artifacts WHERE project=?", (project,)).fetchone()
        steps_rows = conn.execute("SELECT step_key, status, started_at, finished_at, error, outputs_json FROM steps WHERE project=?", (project,)).fetchall()
        steps: Dict[str, Any] = {}
        for r in steps_rows:
            try:
                outs = json.loads(r["outputs_json"]) if r["outputs_json"] else {}
            except Exception:
                outs = {}
            steps[r["step_key"]] = {
                "status": r["status"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "error": r["error"],
                "outputs": outs,
            }
        # Ensure canonical steps exist in view
        for s in PIPELINE_STEPS:
            steps.setdefault(s, {"status": "not_started", "started_at": None, "finished_at": None, "error": None, "outputs": {}})

        state = {
            "project": p["project"],
            "created_at": p["created_at"],
            "updated_at": p["updated_at"],
            "steps": steps,
            "artifacts": {
                "schema_file": arts["schema_file"] if arts else None,
                "screenplay_file": arts["screenplay_file"] if arts else None,
                "storyboard_file": arts["storyboard_file"] if arts else None,
                "video_file": arts["video_file"] if arts else None,
            },
            # history is omitted for size from default view; could add endpoint to page it
            "history": [],
        }
        return state


def _sqlite_delete_project(project: str) -> None:
    _sqlite_init()
    with _sqlite_conn() as conn:
        conn.execute("DELETE FROM steps WHERE project=?", (project,))
        conn.execute("DELETE FROM artifacts WHERE project=?", (project,))
        conn.execute("DELETE FROM history WHERE project=?", (project,))
        conn.execute("DELETE FROM projects WHERE project=?", (project,))
        conn.commit()


def _sqlite_upsert_full(state: Dict[str, Any]) -> None:
    """Best-effort import of a full JSON state into SQLite (used if someone saves JSON while on sqlite backend)."""
    project = state.get("project")
    if not project:
        return
    _sqlite_init_project(project)
    with _sqlite_conn() as conn:
        # Artifacts
        arts = state.get("artifacts", {}) or {}
        conn.execute(
            "UPDATE artifacts SET schema_file=?, screenplay_file=?, storyboard_file=?, video_file=? WHERE project=?",
            (
                arts.get("schema_file"),
                arts.get("screenplay_file"),
                arts.get("storyboard_file"),
                arts.get("video_file"),
                project,
            ),
        )
        # Steps
        steps: Dict[str, Any] = state.get("steps", {}) or {}
        for key, s in steps.items():
            conn.execute(
                "INSERT INTO steps(project, step_key, status, started_at, finished_at, error, outputs_json) VALUES(?,?,?,?,?,?,?)\n                 ON CONFLICT(project, step_key) DO UPDATE SET status=excluded.status, started_at=excluded.started_at, finished_at=excluded.finished_at, error=excluded.error, outputs_json=excluded.outputs_json",
                (
                    project,
                    key,
                    s.get("status", "not_started"),
                    s.get("started_at"),
                    s.get("finished_at"),
                    s.get("error"),
                    json.dumps(s.get("outputs", {}) or {}),
                ),
            )
        _sqlite_update_project_ts(conn, project)
        conn.commit()


# ---------
# Migration
# ---------

def import_json_state_to_sqlite(state: Dict[str, Any]) -> None:
    """Public helper to import a single JSON state dict into SQLite."""
    _sqlite_init()
    _sqlite_upsert_full(state)


def migrate_json_states_to_sqlite(source_dir: Optional[str] = None) -> Dict[str, Any]:
    """Migrate all JSON state files in source_dir to the SQLite database.

    Returns a summary dict with counts.
    """
    src = source_dir or PROJECTS_DIR
    os.makedirs(src, exist_ok=True)
    _sqlite_init()
    migrated = 0
    skipped = 0
    errors: list[Dict[str, str]] = []
    for fn in os.listdir(src):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(src, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict) and state.get("project"):
                _sqlite_upsert_full(state)
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append({"file": path, "error": str(e)})
    return {"migrated": migrated, "skipped": skipped, "errors": errors}

