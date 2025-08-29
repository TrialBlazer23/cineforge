import os
import io
import json
import glob
import sys
import pathlib
import streamlit as st

# Ensure we can import utils whether run from project root or UI folder
try:
    from src import utils  # type: ignore
except Exception:
    PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
    SRC_DIR = PROJECT_ROOT / "src"
    sys.path.append(str(SRC_DIR))
    import utils  # type: ignore

# Import pipeline functions
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import api as cine_api
import requests


utils.load_env()
st.set_page_config(page_title="CineForge", layout="wide")

st.title("CineForge – Story to Film")
st.caption("Upload a story, pick a style, and run the pipeline step by step with approvals.")

# --- Sidebar: Project + Settings ---
with st.sidebar:
    st.header("Project")
    default_project = os.environ.get("VERTEX_PROJECT_ID", "")
    default_location = os.environ.get("VERTEX_LOCATION", "us-central1")
    project = st.text_input("GCP Project ID", value=default_project, placeholder="my-gcp-project")
    location = st.text_input("Vertex AI Location", value=default_location)

    # Load style options
    styles_map = {}
    try:
        with open("config.json", "r") as f:
            cfg = json.load(f)
            styles_map = cfg.get("styles", {})
    except Exception:
        pass

    styles = list(styles_map.keys()) or ["3d-cartoon", "cinematic-anime", "photorealistic"]
    style_key = st.selectbox("Style preset", styles, index=0)

    st.markdown("---")
    st.caption("Credentials (set in environment or .env)")
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    st.text_input("GOOGLE_APPLICATION_CREDENTIALS", value=creds or "", disabled=True)

    st.markdown("---")
    default_backend = os.environ.get("BACKEND_URL", "http://localhost:8001")
    st.session_state.backend_url = st.text_input("Backend API URL", value=default_backend)

    st.markdown("---")
    st.checkbox("Auto-refresh task status", value=st.session_state.get("auto_refresh", True), key="auto_refresh")
    st.slider("Refresh interval (ms)", min_value=500, max_value=5000, step=500, value=st.session_state.get("refresh_ms", 1500), key="refresh_ms")


# --- Session State ---
if "project_name" not in st.session_state:
    st.session_state.project_name = ""
if "story_path" not in st.session_state:
    st.session_state.story_path = ""
if "schema_path" not in st.session_state:
    st.session_state.schema_path = ""
if "screenplay_path" not in st.session_state:
    st.session_state.screenplay_path = ""
if "storyboard_path" not in st.session_state:
    st.session_state.storyboard_path = ""
if "last_task_id" not in st.session_state:
    st.session_state.last_task_id = ""
if "last_task_state" not in st.session_state:
    st.session_state.last_task_state = ""
if "last_task_result" not in st.session_state:
    st.session_state.last_task_result = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "refresh_ms" not in st.session_state:
    st.session_state.refresh_ms = 1500
if "selected_project" not in st.session_state:
    st.session_state.selected_project = ""


def _maybe_update_paths_from_result(result: dict):
    try:
        if not isinstance(result, dict):
            return
        if "schema_file" in result:
            st.session_state.schema_path = result.get("schema_file") or st.session_state.schema_path
        if "screenplay_file" in result:
            st.session_state.screenplay_path = result.get("screenplay_file") or st.session_state.screenplay_path
        if "storyboard_file" in result:
            st.session_state.storyboard_path = result.get("storyboard_file") or st.session_state.storyboard_path
    except Exception:
        pass


# --- Step 0: Create Project & Upload Story ---
st.header("Step 0 · Create project and upload story")
col0a, col0b = st.columns([2, 3])
with col0a:
    st.session_state.project_name = st.text_input("Project name", value=st.session_state.project_name or "My_Film_Project")
    uploaded = st.file_uploader("Upload story (.txt)", type=["txt"], accept_multiple_files=False)
    if uploaded is not None:
        os.makedirs("story", exist_ok=True)
        story_filename = os.path.join("story", os.path.basename(uploaded.name))
        with open(story_filename, "wb") as f:
            f.write(uploaded.read())
        st.session_state.story_path = story_filename
        st.success(f"Story saved: {story_filename}")
with col0b:
    if st.session_state.story_path:
        with open(st.session_state.story_path, "r", encoding="utf-8", errors="ignore") as f:
            st.text_area("Story preview", f.read(), height=240)

# --- Optional: Full pipeline (async) ---
st.header("Run full pipeline (async)")
col0c, col0d = st.columns([1, 3])
with col0c:
    run_full = st.button(
        "Run full pipeline",
        use_container_width=True,
        disabled=not (st.session_state.story_path and project and location),
    )
with col0d:
    if run_full:
        try:
            resp = requests.post(
                f"{st.session_state.backend_url}/tasks/pipeline",
                params={
                    "story_file": st.session_state.story_path,
                    "project": project,
                    "location": location,
                    "style": style_key,
                },
                timeout=30,
            )
            resp.raise_for_status()
            st.session_state.last_task_id = resp.json().get("task_id", "")
            st.success(f"Task queued: {st.session_state.last_task_id}")
        except Exception as e:
            st.error(f"Queueing failed: {e}")


# --- Step 1: Narrative Deconstruction (async) ---
st.header("Step 1 · Narrative deconstruction")
col1a, col1b = st.columns([1, 2])
with col1a:
    run_deconstruct = st.button("Run deconstruction (async)", use_container_width=True, disabled=not (st.session_state.story_path and project and location))
with col1b:
    if run_deconstruct:
        try:
            resp = requests.post(
                f"{st.session_state.backend_url}/tasks/deconstruct",
                params={"story_file": st.session_state.story_path, "project": project, "location": location},
                timeout=30,
            )
            resp.raise_for_status()
            st.session_state.last_task_id = resp.json().get("task_id", "")
            st.success(f"Task queued: {st.session_state.last_task_id}")
        except Exception as e:
            st.error(f"Queueing failed: {e}")

if st.session_state.schema_path and os.path.exists(st.session_state.schema_path):
    with st.expander("View schema JSON", expanded=False):
        st.code(open(st.session_state.schema_path, "r").read(), language="json")


# --- Step 2: Screenplay & Storyboard (async) ---
st.header("Step 2 · Screenplay and storyboard")
col2a, col2b = st.columns([1, 2])
with col2a:
    run_script_and_board = st.button(
        "Generate screenplay + storyboard (async)",
        use_container_width=True,
        disabled=not (st.session_state.schema_path and project and location),
    )
with col2b:
    if run_script_and_board:
        try:
            resp = requests.post(
                f"{st.session_state.backend_url}/tasks/screenplay",
                params={"schema_file": st.session_state.schema_path, "project": project, "location": location},
                timeout=30,
            )
            resp.raise_for_status()
            st.session_state.last_task_id = resp.json().get("task_id", "")
            st.success(f"Task queued: {st.session_state.last_task_id}")
        except Exception as e:
            st.error(f"Queueing failed: {e}")

cols = st.columns(2)
if st.session_state.screenplay_path and os.path.exists(st.session_state.screenplay_path):
    with cols[0]:
        with open(st.session_state.screenplay_path, "r", encoding="utf-8", errors="ignore") as f:
            st.text_area("Screenplay", f.read(), height=260)
if st.session_state.storyboard_path and os.path.exists(st.session_state.storyboard_path):
    with cols[1]:
        with open(st.session_state.storyboard_path, "r", encoding="utf-8", errors="ignore") as f:
            st.text_area("Storyboard", f.read(), height=260)


# --- Step 3: Visual assets (async) ---
st.header("Step 3 · Visual assets")
col3a, col3b = st.columns([1, 3])
with col3a:
    run_assets = st.button(
        "Generate character, environment, and storyboard images (async)",
        use_container_width=True,
        disabled=not (st.session_state.storyboard_path and st.session_state.schema_path and project and location),
    )
with col3b:
    if run_assets:
        try:
            resp = requests.post(
                f"{st.session_state.backend_url}/tasks/assets",
                params={
                    "storyboard_file": st.session_state.storyboard_path,
                    "schema_file": st.session_state.schema_path,
                    "project": project,
                    "location": location,
                    "style": style_key,
                },
                timeout=30,
            )
            resp.raise_for_status()
            st.session_state.last_task_id = resp.json().get("task_id", "")
            st.success(f"Task queued: {st.session_state.last_task_id}")
        except Exception as e:
            st.error(f"Queueing failed: {e}")

# --- Task monitor ---
st.header("Task monitor")
if st.session_state.get("last_task_id"):
    cols = st.columns([1,1,3])
    with cols[0]:
        st.write(f"Task ID: {st.session_state.last_task_id}")
    with cols[1]:
        if st.button("Refresh status", use_container_width=True):
            try:
                res = requests.get(f"{st.session_state.backend_url}/tasks/{st.session_state.last_task_id}", timeout=30)
                res.raise_for_status()
                data = res.json()
                st.session_state.last_task_state = data.get("state", "")
                st.session_state.last_task_result = data.get("result")
                if st.session_state.last_task_state == "SUCCESS":
                    _maybe_update_paths_from_result(st.session_state.last_task_result)
            except Exception as e:
                st.error(f"Status check failed: {e}")
    with cols[2]:
        st.write(f"State: {st.session_state.get('last_task_state')}")
        if st.session_state.get("last_task_result"):
            st.json(st.session_state.last_task_result)

    # Auto-refresh on rerun
    if st.session_state.auto_refresh:
        try:
            res = requests.get(f"{st.session_state.backend_url}/tasks/{st.session_state.last_task_id}", timeout=15)
            if res.ok:
                data = res.json()
                st.session_state.last_task_state = data.get("state", "")
                st.session_state.last_task_result = data.get("result")
                if st.session_state.last_task_state == "SUCCESS":
                    _maybe_update_paths_from_result(st.session_state.last_task_result)
        except Exception:
            pass
        # Trigger a timed rerun
        st.autorefresh(interval=st.session_state.refresh_ms, key="task_autorefresh")

images = sorted(glob.glob(os.path.join("output", "storyboard_images", "*.png")))
if images:
    st.caption("Generated images")
    grid_cols = st.columns(3)
    for idx, img in enumerate(images):
        grid_cols[idx % 3].image(img, caption=os.path.basename(img), use_container_width=True)


# --- Step 4: Video synthesis ---
st.header("Step 4 · Video synthesis (preview)")
st.info("Veo integration is a placeholder in this repo. You can still assemble a cut using FFmpeg from available clips when implemented.")

st.markdown("---")
st.caption("Tip: Ensure your Vertex AI credentials are correctly mounted inside the container.")


# --- Project state viewer ---
st.header("Project state")
cols_state = st.columns([1, 3])
with cols_state[0]:
    try:
        resp = requests.get(f"{st.session_state.backend_url}/projects", timeout=10)
        projects = resp.json().get("projects", []) if resp.ok else []
    except Exception:
        projects = []
    if projects:
        sel = st.selectbox("Select project", options=[""] + projects, index=0, help="Projects tracked in JSON state")
        st.session_state.selected_project = sel
    else:
        st.info("No projects found yet. They'll appear after you run a task.")
with cols_state[1]:
    if st.session_state.selected_project:
        try:
            res = requests.get(f"{st.session_state.backend_url}/projects/{st.session_state.selected_project}", timeout=15)
            if res.ok:
                state = res.json()
                arts = state.get("artifacts", {})
                st.subheader(f"{state.get('project')}")
                st.caption(f"Updated: {state.get('updated_at')}")
                steps = state.get("steps", {})
                # Render compact status rows
                for key in [
                    "narrative_deconstructed",
                    "screenplay_generated",
                    "storyboard_generated",
                    "visual_assets_generated",
                    "video_synthesized",
                ]:
                    step = steps.get(key, {})
                    status = step.get("status", "not_started")
                    started = step.get("started_at") or ""
                    finished = step.get("finished_at") or ""
                    err = step.get("error")
                    with st.container():
                        st.write(f"- {key}: {status}  (start: {started}, end: {finished})")
                        if err:
                            st.error(err)
                if any(arts.values()):
                    st.markdown("\nArtifacts:")
                    for k, v in arts.items():
                        if v:
                            st.write(f"• {k}: {v}")
            else:
                st.warning("Failed to load project state")
        except Exception as e:
            st.warning(f"State read error: {e}")
