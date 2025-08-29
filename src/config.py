import json
import os
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore


DEFAULT_CONFIG_PATHS = (
    "config.json",
    "config.yaml",
    "config.yml",
)


_DEFAULTS: Dict[str, Any] = {
    "vertex": {
        "project": os.environ.get("VERTEX_PROJECT_ID"),
        "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
        "models": {
            "narrative": "gemini-2.5-pro",
            "screenplay": "gemini-2.5-flash",
            "storyboard": "gemini-2.5-flash",
        },
        "generation": {
            "narrative": {"max_output_tokens": 8192, "temperature": 0.2, "top_p": 1.0},
            "screenplay": {"max_output_tokens": 8192, "temperature": 0.7, "top_p": 1.0},
            "storyboard": {"max_output_tokens": 8192, "temperature": 0.7, "top_p": 1.0},
        },
    },
    "paths": {
        "base_output_dir": "output",
        "narrative_schema_dir": os.path.join("output", "narrative_schema"),
        "screenplay_dir": os.path.join("output", "screenplay"),
        "storyboard_text_dir": os.path.join("output", "storyboard_text"),
        "projects_state_dir": os.path.join("output", "projects"),
    },
    "styles": {},
}


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("YAML support not available. Install pyyaml or use JSON config.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load central configuration. Supports JSON or YAML.

    Resolution order:
      1) explicit config_path if provided
      2) search DEFAULT_CONFIG_PATHS in CWD
      3) fall back to in-code defaults
    """
    cfg: Dict[str, Any] = dict(_DEFAULTS)

    def try_merge(path: str) -> bool:
        nonlocal cfg
        if not os.path.exists(path):
            return False
        try:
            if path.endswith(".json"):
                file_cfg = _load_json(path)
            elif path.endswith(".yaml") or path.endswith(".yml"):
                file_cfg = _load_yaml(path)
            else:
                return False
            if isinstance(file_cfg, dict):
                cfg = _deep_merge(cfg, file_cfg)
                return True
        except Exception:
            # Ignore malformed configs and keep defaults
            pass
        return False

    if config_path:
        try_merge(config_path)
    else:
        for p in DEFAULT_CONFIG_PATHS:
            if try_merge(p):
                break

    # Environment overrides for convenience
    if os.environ.get("VERTEX_PROJECT_ID"):
        cfg.setdefault("vertex", {}).setdefault("project", os.environ.get("VERTEX_PROJECT_ID"))
    if os.environ.get("VERTEX_LOCATION"):
        cfg.setdefault("vertex", {}).setdefault("location", os.environ.get("VERTEX_LOCATION"))

    return cfg


def get_path(cfg: Dict[str, Any], key: str) -> str:
    return cfg.get("paths", {}).get(key) or _DEFAULTS["paths"].get(key, "")
