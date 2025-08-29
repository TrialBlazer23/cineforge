# AI Filmmaking on Google Cloud

This project is an implementation of the "From Story to Screen" blueprint, creating a generative filmmaking pipeline on Google Cloud. It transforms a written story into a finished film by orchestrating Google's generative AI models (Gemini, Imagen, Veo) through a series of automated steps.

## Pipeline Stages

1. **Narrative Deconstruction**: Analyzes a raw text story to produce a structured "Narrative Schema" in JSON format.
2. **Screenplay & Storyboard Generation**: Generates a screenplay and a descriptive text-based storyboard from the Narrative Schema.
3. **Visual Asset Generation**: Creates character model sheets, environment plates, and consistent storyboard images using Imagen.
4. **Video Synthesis**: Animates the storyboard images into video clips using Veo.
5. **Final Assembly**: Assembles the video clips into a final film using FFmpeg.

This application is designed with a "human-in-the-loop" workflow, allowing for review and approval at each critical stage of the creative process.

## Quick start

1) Prepare credentials

- Ensure you have Google Cloud Application Default Credentials available locally (e.g., via `gcloud auth application-default login`).
- On Windows, docker-compose mounts `${APPDATA}/gcloud/application_default_credentials.json` into the container.

1) Configure environment

- Copy `.env.example` to `.env` and set `VERTEX_PROJECT_ID` and optionally `VERTEX_LOCATION`.
- Optionally set `GOOGLE_APPLICATION_CREDENTIALS` on your host; docker-compose already mounts ADC by default on Windows.

1) Run with Docker

- Build optimized, multi-stage image is used by compose.
- Start API only (Windows PowerShell):

```powershell
docker compose --profile api up --build
```

- Start UI (depends on API):

```powershell
docker compose --profile ui up --build
```

- Open the UI: <http://localhost:8501>

1) Use the UI

- Enter your GCP project and location in the sidebar.
- Upload a story file, then run each step (Deconstruction -> Screenplay/Storyboard -> Visual Assets).
- Images are saved under `output/`.

### Optional: run locally without Docker

- Install dependencies:

```powershell
pip install -r requirements.txt
```

- Set env (via .env or system env): VERTEX_PROJECT_ID, VERTEX_LOCATION, GOOGLE_APPLICATION_CREDENTIALS.

- Start API:

```powershell
gunicorn --bind :8000 -k uvicorn.workers.UvicornWorker api:app
```

- Start UI:

```powershell
streamlit run ui/app.py
```

## Asynchronous tasks (Celery + Redis)

You can now run each pipeline step asynchronously via the API with a task queue.

 - flower (optional dashboard at <http://localhost:5555>)

Start UI as well:

```powershell
docker compose --profile ui up -d --build
```

Notes

- docker compose automatically reads `.env` from the project root (c:\cineforge). We also set `env_file: .env` on services so the variables are present inside containers.
- On Windows, ADC is mounted from `${APPDATA}\gcloud\application_default_credentials.json` into the containers at `/app/application_default_credentials.json`.

API endpoints:

- POST /tasks/pipeline — run full pipeline; returns { task_id }
- POST /tasks/deconstruct — returns { task_id }
- POST /tasks/screenplay — returns { task_id }
- POST /tasks/assets — returns { task_id }
- GET /tasks/{task_id} — returns state and result when ready
