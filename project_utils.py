import os
import json
import re
from datetime import datetime

PROJECTS_DIR = "output/projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

def get_project_path(project_name):
    """Gets the full path for a project."""
    safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
    return os.path.join(PROJECTS_DIR, f"{safe_project_name}.json")

def save_project(project_name, project_data):
    """Saves the project data to a file."""
    project_path = get_project_path(project_name)
    with open(project_path, "w") as f:
        json.dump(project_data, f, indent=4)

def load_project(project_name):
    """Loads project data from a file."""
    project_path = get_project_path(project_name)
    if os.path.exists(project_path):
        with open(project_path, "r") as f:
            return json.load(f)
    return None

def list_projects():
    """Lists all saved projects."""
    projects = []
    for filename in os.listdir(PROJECTS_DIR):
        if filename.endswith(".json"):
            project_name = os.path.splitext(filename)[0]
            projects.append(project_name)
    return projects

def delete_project(project_name):
    """Deletes a project file."""
    project_path = get_project_path(project_name)
    if os.path.exists(project_path):
        os.remove(project_path)
