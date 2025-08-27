import streamlit as st
import os
import subprocess
import re
import json
import zipfile
from datetime import datetime
import requests
from fastapi import FastAPI
from project_utils import list_projects, load_project, save_project, get_project_path, delete_project

app = FastAPI()

st.set_page_config(layout="wide", page_title="AI Film Studio")

# --- Pricing Information (Estimates as of late 2024) ---
PRICING = {
    "gemini-2.5-pro": {"input_1m_chars": 2.10, "output_1m_chars": 4.20},
    "gemini-2.5-flash": {"input_1m_chars": 0.21, "output_1m_chars": 0.42},
    "imagen-3.0-fast-generate-001": {"per_image": 0.015},
    "veo-3.0-fast-generate-001": {"per_second": 0.05},
}

# --- Helper Functions ---
def create_project_zip(project_name):
    """Creates a zip archive of the project's output files, excluding temp/archives."""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
    
    archive_dir = "output/archives"
    os.makedirs(archive_dir, exist_ok=True)
    
    zip_filename = f"project_{safe_project_name}_{now}.zip"
    zip_path = os.path.join(archive_dir, zip_filename)
    
    root_dir_to_archive = "output"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir_to_archive):
            # Prune directories we don't want to descend into
            if 'temp' in dirs:
                dirs.remove('temp')
            if 'archives' in dirs:
                dirs.remove('archives')
            
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=root_dir_to_archive)
                zipf.write(file_path, arcname)
    return zip_path

def clear_project():
    """Resets the session state to start a new project, preserving the Project ID."""
    
    # Preserve the project ID
    project_id = st.session_state.get("project_id", "")
    project_name = st.session_state.get("project_name", "")

    # List of all state keys to reset/delete
    keys_to_clear = [
        'story_file_name', 'pipeline_state', 'paths', 
        'screenplay_text', 'storyboard_text', 'zip_path'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Re-initialize the core state structure after clearing
    st.session_state.project_id = project_id # Restore project ID
    st.session_state.project_name = project_name # Restore project name
    # The rest of the state will be re-initialized by the checks below
    
    st.toast("Project cleared! Ready for a new story.")


# --- Session State Initialization ---
# This is crucial for making the app stateful
if 'project_id' not in st.session_state:
    st.session_state.project_id = ""
if 'project_name' not in st.session_state:
    st.session_state.project_name = ""
if 'story_file_name' not in st.session_state:
    st.session_state.story_file_name = None
if 'pipeline_state' not in st.session_state:
    st.session_state.pipeline_state = {
        "schema_generated": False,
        "screenplay_generated": False,
        "assets_generated": False,
        "video_synthesized": False,
        "soundtrack_generated": False,
        "voiceover_generated": False,
        "film_assembled": False,
    }
if 'paths' not in st.session_state:
    st.session_state.paths = {
        "story": None,
        "schema": None,
        "screenplay": None,
        "storyboard": None,
        "soundtrack": None,
        "voiceover": None,
        "final_film": None
    }
if 'zip_path' not in st.session_state:
    st.session_state.zip_path = None

# --- UI ---
st.title("🎬 AI Film Studio")
st.info("**From Story to Screen:** An Architectural and Financial Blueprint for AI Filmmaking on Google Cloud")

# --- Sidebar ---
with st.sidebar:
    st.header(" Mange Projects")
    projects = list_projects()
    selected_project = st.selectbox("Select a Project", projects)

    if selected_project:
        project_data = load_project(selected_project)
        if project_data:
            st.session_state.project_name = selected_project
            st.session_state.project_id = project_data.get("project_id", "")
            st.session_state.story_file_name = project_data.get("story_file_name")
            st.session_state.pipeline_state = project_data.get("pipeline_state")
            st.session_state.paths = project_data.get("paths")
            st.session_state.zip_path = project_data.get("zip_path")

    new_project_name = st.text_input("Or Create a New Project")
    if st.button("Create Project") and new_project_name:
        st.session_state.project_name = new_project_name
        clear_project()
        save_project(new_project_name, st.session_state.to_dict())
        st.rerun()
    
    if st.session_state.project_name:
        if st.button("Delete Project", key="delete_project"):
            delete_project(st.session_state.project_name)
            st.session_state.project_name = ""
            clear_project()
            st.rerun()

    st.header("⚙️ Project Configuration")
    st.session_state.project_id = st.text_input("Your Google Cloud Project ID", st.session_state.project_id)
    uploaded_story = st.file_uploader("Upload Your Story (.txt)", type=["txt"])

    if uploaded_story:
        st.session_state.story_file_name = uploaded_story.name
        # Save the uploaded file to a consistent temp location to be processed
        temp_dir = "output/temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_story_path = os.path.join(temp_dir, uploaded_story.name)
        with open(temp_story_path, "wb") as f:
            f.write(uploaded_story.getbuffer())
        st.session_state.paths['story'] = temp_story_path
        st.success(f"Loaded `{uploaded_story.name}`")
        if st.session_state.project_name:
            save_project(st.session_state.project_name, st.session_state.to_dict())

    # Display pipeline status
    st.header("📊 Pipeline Status")
    st.checkbox("1. Narrative Schema", value=st.session_state.pipeline_state["schema_generated"])
    st.checkbox("2. Screenplay & Storyboard", value=st.session_state.pipeline_state["screenplay_generated"], disabled=not st.session_state.pipeline_state["schema_generated"])
    st.checkbox("3. Visual Assets", value=st.session_state.pipeline_state["assets_generated"], disabled=not st.session_state.pipeline_state["screenplay_generated"])
    st.checkbox("4. Video Synthesis", value=st.session_state.pipeline_state["video_synthesized"], disabled=not st.session_state.pipeline_state["assets_generated"])
    st.checkbox("5. Soundtrack", value=st.session_state.pipeline_state["soundtrack_generated"], disabled=not st.session_state.pipeline_state["video_synthesized"])
    st.checkbox("6. Voiceover", value=st.session_state.pipeline_state["voiceover_generated"], disabled=not st.session_state.pipeline_state["video_synthesized"])
    st.checkbox("7. Final Film", value=st.session_state.pipeline_state["film_assembled"], disabled=not st.session_state.pipeline_state["soundtrack_generated"] or not st.session_state.pipeline_state["voiceover_generated"])


    st.divider()
    st.button("🧹 Clear Project", on_click=clear_project, use_container_width=True)

    # --- Export Section ---
    if st.session_state.pipeline_state["film_assembled"]:
        st.divider()
        st.header("📦 Export Project")
        
        if st.button("Prepare Project Archive (.zip)", use_container_width=True):
            with st.spinner("Zipping project files..."):
                base_name = os.path.splitext(st.session_state.story_file_name)[0]
                zip_path = create_project_zip(base_name)
                st.session_state.zip_path = zip_path
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.rerun()
        
        if st.session_state.zip_path and os.path.exists(st.session_state.zip_path):
            with open(st.session_state.zip_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Project Archive",
                    data=f,
                    file_name=os.path.basename(st.session_state.zip_path),
                    mime="application/zip",
                    use_container_width=True
                )

# --- Main Content Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1. Narrative Schema", "2. Screenplay & Storyboard", "3. Visual Assets", "4. Video Synthesis", "5. Soundtrack", "6. Voiceover", "7. Final Assembly"
])

with tab1:
    st.header("Step 1: Deconstruct Narrative")
    st.write("This step analyzes your story to create a structured JSON 'Narrative Schema', breaking down characters, scenes, and plot points.")

    model_choice_step1 = st.selectbox(
        "Select Model",
        ("gemini-2.5-pro", "gemini-2.5-flash"),
        key="model_step1",
        help="Gemini Pro is higher quality but more expensive. Gemini Flash is faster and cheaper."
    )

    with st.expander("Cost Estimation"):
        selected_model_pricing_step1 = PRICING[model_choice_step1]
        st.info(f"""
        - **Model:** `{model_choice_step1}`
        - **Pricing:**
            - Input: ${selected_model_pricing_step1['input_1m_chars']:.2f} per 1 million characters
            - Output: ${selected_model_pricing_step1['output_1m_chars']:.2f} per 1 million characters
        - **Estimate:** Typically less than $0.10 for a short story.
        """)

    if st.button("Generate Narrative Schema", disabled=not st.session_state.paths['story'] or not st.session_state.project_id):
        with st.spinner("Sending story for analysis..."):
            story_path = st.session_state.paths.get('story')
            story_name = st.session_state.get('story_file_name')

            if story_path and story_name:
                with open(story_path, "rb") as f:
                    files = {'story_file': (story_name, f, 'text/plain')}
                    response = requests.post(
                        "http://backend:8000/narrative_deconstruction",
                        data={"project_id": st.session_state.project_id, "location": "us-central1"},
                        files=files
                    )

                if response.status_code == 200:
                    response_data = response.json()
                    st.session_state.paths['schema'] = response_data.get("output_path")
                    st.session_state.pipeline_state["schema_generated"] = True
                    if st.session_state.project_name:
                        save_project(st.session_state.project_name, st.session_state.to_dict())
                    st.success("Narrative deconstruction started successfully!")
                    st.info(f"Schema will be saved to: {response_data.get('output_path')}")
                    st.rerun()
                else:
                    st.error(f"Failed to start narrative deconstruction: {response.text}")
            else:
                st.error("Story file information is missing. Please re-upload your story file.")

    # Check for the existence of the schema file to update the state
    schema_path = st.session_state.paths.get('schema')
    if schema_path and os.path.exists(schema_path):
        st.session_state.pipeline_state["schema_generated"] = True

    if st.session_state.pipeline_state["schema_generated"]:
        st.subheader("Generated Narrative Schema")
        try:
            with open(st.session_state.paths['schema'], "r") as f:
                st.json(f.read())
        except (FileNotFoundError, TypeError):
            st.error("Could not find or read the generated schema file. Please check the API server logs and try again.")
            st.session_state.pipeline_state["schema_generated"] = False # Reset state
    elif schema_path:
        st.info("Narrative schema is being generated in the background.")
        if st.button("Check Status / Refresh"):
            st.rerun()

with tab2:
    st.header("Step 2: Generate Screenplay & Storyboard")
    st.write("Using the schema, this step generates a full screenplay and a detailed, shot-by-shot text storyboard.")

    model_choice_step2 = st.selectbox(
        "Select Model",
        ("gemini-2.5-flash", "gemini-2.5-pro"),
        key="model_step2",
        help="Gemini Flash is faster and cheaper, suitable for this task. Gemini Pro may yield more creative results."
    )

    with st.expander("Cost Estimation"):
        selected_model_pricing_step2 = PRICING[model_choice_step2]
        st.info(f"""
        - **Model:** `{model_choice_step2}`
        - **Pricing:**
            - Input: ${selected_model_pricing_step2['input_1m_chars']:.2f} per 1 million characters
            - Output: ${selected_model_pricing_step2['output_1m_chars']:.2f} per 1 million characters
        - **Estimate:** Varies with story length. Typically $0.10 - $0.50.
        """)

    if st.button("Generate Screenplay & Storyboard", disabled=not st.session_state.pipeline_state["schema_generated"]):
        with st.spinner("Sending request for screenplay and storyboard generation..."):
            response = requests.post(
                "http://backend:8000/screenplay_and_storyboard",
                json={"schema_path": st.session_state.paths['schema'], "project_id": st.session_state.project_id}
            )

            if response.status_code == 200:
                response_data = response.json()
                st.session_state.paths['screenplay'] = response_data.get("screenplay_path")
                st.session_state.paths['storyboard'] = response_data.get("storyboard_path")
                st.session_state.pipeline_state["screenplay_generated"] = True
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Screenplay and storyboard generation started successfully!")
                st.info(f"Screenplay will be saved to: {response_data.get('screenplay_path')}")
                st.info(f"Storyboard will be saved to: {response_data.get('storyboard_path')}")
                st.rerun()
            else:
                st.error(f"Failed to start screenplay and storyboard generation: {response.text}")

    if st.session_state.pipeline_state["screenplay_generated"]:
        st.subheader("Generated Outputs")
        st.info("You can edit the screenplay and storyboard below. Click 'Save Edits' to apply your changes before proceeding to the next step.")

        # On first load after generation, populate the text area state from the file.
        # The text_area widget will then manage the state via its key.
        if 'screenplay_text' not in st.session_state:
            try:
                with open(st.session_state.paths['screenplay'], "r") as f:
                    st.session_state.screenplay_text = f.read()
            except (FileNotFoundError, TypeError):
                st.session_state.screenplay_text = "Error: Could not load screenplay file."

        if 'storyboard_text' not in st.session_state:
            try:
                with open(st.session_state.paths['storyboard'], "r") as f:
                    st.session_state.storyboard_text = f.read()
            except (FileNotFoundError, TypeError):
                st.session_state.storyboard_text = "Error: Could not load storyboard file."

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Screenplay")
            st.text_area("Screenplay", height=600, key="screenplay_text", label_visibility="collapsed")
        with col2:
            st.markdown("### Storyboard")
            st.text_area("Storyboard", height=600, key="storyboard_text", label_visibility="collapsed")

        if st.button("Save Edits"):
            try:
                with open(st.session_state.paths['screenplay'], "w") as f:
                    f.write(st.session_state.screenplay_text)
                with open(st.session_state.paths['storyboard'], "w") as f:
                    f.write(st.session_state.storyboard_text)
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Your edits have been saved successfully!")
                # Rerun to update cost estimates which depend on the storyboard content
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save edits: {e}")

with tab3:
    st.header("Step 3: Visual Asset Generation")
    st.write("Creates character model sheets, environment plates, and storyboard images using the text storyboard as a prompt guide.")

    # Cost Estimation for Step 3
    if st.session_state.pipeline_state["screenplay_generated"]:
        with st.expander("Cost Estimation", expanded=True):
            try:
                with open(st.session_state.paths['schema'], "r") as f:
                    schema = json.load(f)
                with open(st.session_state.paths['storyboard'], "r") as f:
                    storyboard_content = f.read()

                num_chars = len(schema.get("characters", []))
                num_locs = len(set(scene.get("setting", "Unknown") for scene in schema.get("scenes", [])))
                
                shot_regex = re.compile(r"SCENE \d+, SHOT \d+:")
                num_shots = len(shot_regex.findall(storyboard_content))

                total_images = num_chars + num_locs + num_shots
                estimated_cost = total_images * PRICING['imagen-3.0-fast-generate-001']['per_image']

                st.info(f"""
                - **Model:** `imagen-3.0-fast-generate-001`
                - **Pricing:** ${PRICING['imagen-3.0-fast-generate-001']['per_image']:.3f} per image.
                - **Calculation:**
                    - Character Sheets: `{num_chars}` | Environment Plates: `{num_locs}` | Storyboard Shots: `{num_shots}`
                    - **Total Images to Generate: {total_images}**
                - ### **Estimated Cost for this step: ${estimated_cost:.2f}**
                """)
            except (FileNotFoundError, TypeError, json.JSONDecodeError) as e:
                st.warning(f"Could not calculate cost estimate: {e}")

    if st.button("Generate Visual Assets", disabled=not st.session_state.pipeline_state["screenplay_generated"]):
        with st.spinner("Sending request for visual asset generation..."):
            response = requests.post(
                "http://backend:8000/visual_asset_generation",
                json={
                    "schema_path": st.session_state.paths['schema'],
                    "storyboard_path": st.session_state.paths['storyboard'],
                    "project_id": st.session_state.project_id
                }
            )

            if response.status_code == 200:
                st.session_state.pipeline_state["assets_generated"] = True
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Visual asset generation started successfully!")
                st.rerun()
            else:
                st.error(f"Failed to start visual asset generation: {response.text}")

    if st.session_state.pipeline_state["assets_generated"]:
        st.subheader("Generated Visual Assets")
        image_dir = "output/storyboard_images"

        if not os.path.isdir(image_dir):
            st.warning("Image directory not found, but asset generation was marked complete. Please check script output.")
        else:
            all_images = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

            char_images = sorted([img for img in all_images if img.startswith("character_")])
            env_images = sorted([img for img in all_images if img.startswith("environment_")])
            storyboard_images = sorted(
                [img for img in all_images if img.startswith("scene_")],
                key=lambda f: tuple(map(int, re.findall(r'\d+', f)))
            )

            if char_images:
                with st.expander("Character Model Sheets", expanded=True):
                    st.image([os.path.join(image_dir, img) for img in char_images], width=250)
            if env_images:
                with st.expander("Environment Plates", expanded=True):
                    st.image([os.path.join(image_dir, img) for img in env_images], width=350)
            if storyboard_images:
                with st.expander("Storyboard Images", expanded=True):
                    st.info("Don't like a shot? Edit the storyboard text in the previous tab and click 'Save Edits', then regenerate the specific image here.")
                    cols = st.columns(4)
                    for i, img_file in enumerate(storyboard_images):
                        with cols[i % 4]:
                            with st.container(border=True):
                                caption = os.path.splitext(img_file)[0].replace("_", " ").replace("Scene", "S").replace("Shot", "Sh").title()
                                st.image(os.path.join(image_dir, img_file), caption=caption)
                                
                                match = re.search(r"scene_(\d+)_shot_(\d+)", img_file)
                                if match:
                                    scene_num, shot_num = match.groups()
                                    if st.button("🔄 Regenerate", key=f"regen_{scene_num}_{shot_num}", use_container_width=True):
                                        with st.status(f"Regenerating S{scene_num} Sh{shot_num}...", expanded=False) as status:
                                            status.update(label=f"Regenerating S{scene_num} Sh{shot_num}...", state="running", expanded=True)
                                            st.write(f"Calling `regenerate_shot.py` for Scene {scene_num}, Shot {shot_num}...")
                                            process = subprocess.run(
                                                [
                                                    "python3", "src/regenerate_shot.py",
                                                    st.session_state.paths['storyboard'],
                                                    "--project", st.session_state.project_id,
                                                    "--scene", scene_num,
                                                    "--shot", shot_num
                                                ],
                                                capture_output=True, text=True
                                            )
                                            st.code(process.stdout, language='bash')
                                            if process.stderr:
                                                st.error(process.stderr)

                                            if process.returncode == 0:
                                                st.toast(f"✅ S{scene_num} Sh{shot_num} regenerated!")
                                                st.rerun()
                                            else:
                                                status.update(label="Regeneration failed!", state="error")

with tab4:
    st.header("Step 4: Video Synthesis")
    st.write("Animates the storyboard images into short video clips. This step uses Google's Veo model and can be time-consuming.")

    # Cost Estimation for Step 4
    if st.session_state.pipeline_state["assets_generated"]:
        with st.expander("Cost Estimation", expanded=True):
            try:
                with open(st.session_state.paths['storyboard'], "r") as f:
                    storyboard_content = f.read()

                shot_regex = re.compile(r"SCENE \d+, SHOT \d+:")
                num_shots = len(shot_regex.findall(storyboard_content))
                clip_length_sec = 8 # As defined in the generation script
                total_seconds = num_shots * clip_length_sec
                estimated_cost = total_seconds * PRICING['veo-3.0-fast-generate-001']['per_second']

                st.info(f"""
                - **Model:** `veo-3.0-fast-generate-001`
                - **Pricing:** ${PRICING['veo-3.0-fast-generate-001']['per_second']:.2f} per second of generated video.
                - **Calculation:**
                    - Shots to Animate: `{num_shots}`
                    - Clip Length: `{clip_length_sec}` seconds per shot
                    - **Total Video to Generate: {total_seconds} seconds**
                - ### **Estimated Cost for this step: ${estimated_cost:.2f}**
                """)
            except (FileNotFoundError, TypeError) as e:
                st.warning(f"Could not calculate cost estimate: {e}")

    if st.button("Synthesize Video Clips", disabled=not st.session_state.pipeline_state["assets_generated"]):
        with st.spinner("Sending request for video synthesis..."):
            response = requests.post(
                "http://backend:8000/video_synthesis",
                json={
                    "storyboard_path": st.session_state.paths['storyboard'],
                    "images_directory": "output/storyboard_images",
                    "project_id": st.session_state.project_id
                }
            )

            if response.status_code == 200:
                st.session_state.pipeline_state["video_synthesized"] = True
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Video synthesis started successfully!")
                st.rerun()
            else:
                st.error(f"Failed to start video synthesis: {response.text}")

    if st.session_state.pipeline_state["video_synthesized"]:
        st.subheader("Generated Video Clips")
        video_dir = "output/video_clips"
        if not os.path.isdir(video_dir):
            st.warning("Video clips directory not found.")
        else:
            all_videos = sorted(
                [f for f in os.listdir(video_dir) if f.endswith(".mp4")],
                key=lambda f: tuple(map(int, re.findall(r'\d+', f)))
            )
            if not all_videos:
                st.info("No video clips found in the output directory.")
            else:
                cols = st.columns(3)
                for i, video_file in enumerate(all_videos):
                    with cols[i % 3]:
                        with st.container(border=True):
                            caption = os.path.splitext(video_file)[0].replace("_", " ").replace("Scene", "S").replace("Shot", "Sh").title()
                            st.video(os.path.join(video_dir, video_file))
                            st.caption(caption)

                            match = re.search(r"scene_(\d+)_shot_(\d+)", video_file)
                            if match:
                                scene_num, shot_num = match.groups()
                                if st.button("🔄 Regenerate", key=f"regen_clip_{scene_num}_{shot_num}", use_container_width=True):
                                    with st.status(f"Regenerating Clip S{scene_num} Sh{shot_num}...", expanded=False) as status:
                                        status.update(label=f"Regenerating Clip S{scene_num} Sh{shot_num}...", state="running", expanded=True)
                                        st.write(f"Calling `regenerate_clip.py` for Scene {scene_num}, Shot {shot_num}...")
                                        process = subprocess.run(
                                            [
                                                "python3", "src/regenerate_clip.py",
                                                st.session_state.paths['storyboard'],
                                                "output/storyboard_images",
                                                "--project", st.session_state.project_id,
                                                "--scene", scene_num,
                                                "--shot", shot_num
                                            ],
                                            capture_output=True, text=True
                                        )
                                        st.code(process.stdout, language='bash')
                                        if process.stderr:
                                            st.error(process.stderr)

                                        if process.returncode == 0:
                                            st.toast(f"✅ Clip S{scene_num} Sh{shot_num} regenerated!")
                                            st.rerun()
                                        else:
                                            status.update(label="Clip regeneration failed!", state="error")

with tab5:
    st.header("Step 5: Soundtrack Generation")
    st.write("This step generates a soundtrack for your film.")

    if st.button("Generate Soundtrack", disabled=not st.session_state.pipeline_state["video_synthesized"]):
        with st.spinner("Sending request for soundtrack generation..."):
            response = requests.post(
                "http://backend:8000/soundtrack_generation",
                json={
                    "schema_path": st.session_state.paths['schema'],
                    "project_id": st.session_state.project_id
                }
            )

            if response.status_code == 200:
                response_data = response.json()
                st.session_state.paths['soundtrack'] = response_data.get("output_path")
                st.session_state.pipeline_state["soundtrack_generated"] = True
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Soundtrack generation started successfully!")
                st.info(f"Soundtrack will be saved to: {response_data.get('output_path')}")
                st.rerun()
            else:
                st.error(f"Failed to start soundtrack generation: {response.text}")

    if st.session_state.pipeline_state["soundtrack_generated"]:
        st.subheader("Generated Soundtrack")
        try:
            with open(st.session_state.paths['soundtrack'], "rb") as f:
                st.audio(f.read(), format="audio/mp3")
        except (FileNotFoundError, TypeError):
            st.error("Could not find or read the generated soundtrack file. Please try generating it again.")

with tab6:
    st.header("Step 6: Voiceover Generation")
    st.write("This step generates a voiceover for your film.")

    if st.button("Generate Voiceover", disabled=not st.session_state.pipeline_state["video_synthesized"]):
        with st.spinner("Sending request for voiceover generation..."):
            response = requests.post(
                "http://backend:8000/voiceover_generation",
                json={
                    "screenplay_path": st.session_state.paths['screenplay'],
                    "project_id": st.session_state.project_id
                }
            )

            if response.status_code == 200:
                response_data = response.json()
                st.session_state.paths['voiceover'] = response_data.get("output_path")
                st.session_state.pipeline_state["voiceover_generated"] = True
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Voiceover generation started successfully!")
                st.info(f"Voiceover will be saved to: {response_data.get('output_path')}")
                st.rerun()
            else:
                st.error(f"Failed to start voiceover generation: {response.text}")

    if st.session_state.pipeline_state["voiceover_generated"]:
        st.subheader("Generated Voiceover")
        try:
            with open(st.session_state.paths['voiceover'], "rb") as f:
                st.audio(f.read(), format="audio/mp3")
        except (FileNotFoundError, TypeError):
            st.error("Could not find or read the generated voiceover file. Please try generating it again.")

with tab7:
    st.header("Step 7: Final Assembly")
    st.write("Assembles all the video clips, soundtrack, and voiceover into a final, cohesive film using FFmpeg.")

    with st.expander("Cost Estimation"):
        st.info("""
        - **Tool:** FFmpeg (local processing)
        - **Cost:** This step does not use a cloud AI model and incurs no direct model costs.
        """)

    if st.button("Assemble Final Film", disabled=not st.session_state.pipeline_state["soundtrack_generated"] or not st.session_state.pipeline_state["voiceover_generated"]):
        with st.spinner("Sending request for final assembly..."):
            base_name = os.path.splitext(st.session_state.story_file_name)[0]
            output_filename = f"{base_name}_final_film.mp4"
            response = requests.post(
                "http://backend:8000/final_assembly",
                json={
                    "video_clips_dir": "output/video_clips",
                    "soundtrack_path": st.session_state.paths['soundtrack'],
                    "voiceover_path": st.session_state.paths['voiceover'],
                    "output_path": "output/final_film",
                    "output_filename": output_filename
                }
            )

            if response.status_code == 200:
                st.session_state.pipeline_state["film_assembled"] = True
                st.session_state.paths['final_film'] = os.path.join("output/final_film", output_filename)
                if st.session_state.project_name:
                    save_project(st.session_state.project_name, st.session_state.to_dict())
                st.success("Final assembly started successfully!")
                st.rerun()
            else:
                st.error(f"Failed to start final assembly: {response.text}")

    if st.session_state.pipeline_state["film_assembled"]:
        st.subheader("🎬 Your Final Film")
        try:
            video_path = st.session_state.paths['final_film']
            with open(video_path, "rb") as video_file:
                video_bytes = video_file.read()
            st.video(video_bytes)
            st.success(f"Congratulations! Your film is complete and saved at `{video_path}`")
        except (FileNotFoundError, TypeError):
            st.error("Could not find or read the final film file. Please try assembling it again.")

server = app
