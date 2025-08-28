import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------
# Argparse helpers
# ---------------
def add_vertex_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help="Your Google Cloud project ID.", required=True)
    parser.add_argument("--location", help="The Google Cloud location.", default="us-central1")


def add_style_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--style-profile",
        dest="style_profile",
        help="A style profile to guide all generations (e.g., 'Studio Ghibli', 'film noir').",
    )
    # Back-compat alias
    parser.add_argument("--style", dest="legacy_style", help="Deprecated. Use --style-profile instead.")


def add_scene_shot_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scene", help="The scene number to generate.", type=int)
    parser.add_argument("--shot", help="The shot number to generate.", type=int)


# -----------------------
# Settings/Style utilities
# -----------------------
def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def resolve_style_profile(
    cli_style_profile: Optional[str],
    legacy_style: Optional[str],
    project_settings_file: str = "output/project_settings.json",
    default: str = "photorealistic",
    persist: bool = True,
) -> str:
    style_profile: Optional[str] = None
    if cli_style_profile:
        style_profile = cli_style_profile
    elif legacy_style:
        style_profile = legacy_style
    else:
        if os.path.exists(project_settings_file):
            try:
                settings = load_json(project_settings_file)
                style_profile = settings.get("style_profile") or settings.get("style")
            except Exception:
                style_profile = None
    if not style_profile:
        style_profile = default

    if persist:
        try:
            existing: Dict[str, Any] = {}
            if os.path.exists(project_settings_file):
                try:
                    existing = load_json(project_settings_file) or {}
                except Exception:
                    existing = {}
            existing["style_profile"] = style_profile
            # Maintain legacy key for other scripts
            existing["style"] = style_profile
            save_json(project_settings_file, existing)
        except Exception:
            # Non-fatal if we cannot persist
            pass

    return style_profile


def resolve_style_prompt(style_profile: str, config_path: str = "config.json") -> str:
    """Map a style_profile to a concrete style prompt via config.json, or fallback to the raw profile."""
    try:
        cfg = load_json(config_path)
        styles_map = cfg.get("styles", {}) if isinstance(cfg, dict) else {}
        mapped = styles_map.get(style_profile)
        return mapped or style_profile
    except FileNotFoundError:
        return style_profile
    except Exception:
        return style_profile


# --------------------
# Storyboard utilities
# --------------------
SHOT_REGEX = re.compile(r"SCENE (\d+), SHOT (\d+):\n(.*?)(?=\nSCENE|\Z)", re.DOTALL)


def parse_storyboard_shots(storyboard_content: str) -> List[Tuple[str, str, str]]:
    """Return list of (scene_number, shot_number, description)."""
    return SHOT_REGEX.findall(storyboard_content)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def get_characters_in_shot(shot_description: str, narrative_schema: Dict[str, Any]) -> List[str]:
    return [c["name"] for c in narrative_schema.get("characters", []) if c.get("name") in shot_description]


def get_scene_setting(scene_number: int, narrative_schema: Dict[str, Any]) -> str:
    for scene in narrative_schema.get("scenes", []):
        try:
            if scene.get("scene_number") == int(scene_number):
                return scene.get("setting", "") or ""
        except Exception:
            continue
    return ""
