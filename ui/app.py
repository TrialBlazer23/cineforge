import os
import io
import json
import glob
import streamlit as st
from src import utils

# Import pipeline functions
import api as cine_api


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


# --- Step 1: Narrative Deconstruction ---
st.header("Step 1 · Narrative deconstruction")
col1a, col1b = st.columns([1, 2])
with col1a:
    run_deconstruct = st.button("Run deconstruction", use_container_width=True, disabled=not (st.session_state.story_path and project and location))
with col1b:
    if run_deconstruct:
        try:
            schema_path = cine_api.deconstruct_narrative(st.session_state.story_path, project, location)
            st.session_state.schema_path = schema_path
            st.success(f"Schema saved to: {schema_path}")
        except Exception as e:
            st.error(f"Deconstruction failed: {e}")

if st.session_state.schema_path and os.path.exists(st.session_state.schema_path):
    with st.expander("View schema JSON", expanded=False):
        st.code(open(st.session_state.schema_path, "r").read(), language="json")


# --- Step 2: Screenplay & Storyboard ---
st.header("Step 2 · Screenplay and storyboard")
col2a, col2b = st.columns([1, 2])
with col2a:
    run_script_and_board = st.button(
        "Generate screenplay + storyboard",
        use_container_width=True,
        disabled=not (st.session_state.schema_path and project and location),
    )
with col2b:
    if run_script_and_board:
        try:
            screenplay_path, storyboard_path = cine_api.generate_screenplay_and_storyboard(
                st.session_state.schema_path, project, location
            )
            st.session_state.screenplay_path = screenplay_path
            st.session_state.storyboard_path = storyboard_path
            st.success(f"Screenplay: {screenplay_path}\nStoryboard: {storyboard_path}")
        except Exception as e:
            st.error(f"Generation failed: {e}")

cols = st.columns(2)
if st.session_state.screenplay_path and os.path.exists(st.session_state.screenplay_path):
    with cols[0]:
        with open(st.session_state.screenplay_path, "r", encoding="utf-8", errors="ignore") as f:
            st.text_area("Screenplay", f.read(), height=260)
if st.session_state.storyboard_path and os.path.exists(st.session_state.storyboard_path):
    with cols[1]:
        with open(st.session_state.storyboard_path, "r", encoding="utf-8", errors="ignore") as f:
            st.text_area("Storyboard", f.read(), height=260)


# --- Step 3: Visual assets ---
st.header("Step 3 · Visual assets")
col3a, col3b = st.columns([1, 3])
with col3a:
    run_assets = st.button(
        "Generate character, environment, and storyboard images",
        use_container_width=True,
        disabled=not (st.session_state.storyboard_path and st.session_state.schema_path and project and location),
    )
with col3b:
    if run_assets:
        try:
            # Pass style into assets generation
            cine_api.generate_visual_assets(
                st.session_state.storyboard_path,
                st.session_state.schema_path,
                project,
                location,
                style_key,
            )
            st.success("Visual assets generated.")
        except Exception as e:
            st.error(f"Asset generation failed: {e}")

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
