from __future__ import annotations

import json
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any


ROOT = Path(os.getenv("MOVIE_PRODUCTION_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
ROOT.mkdir(parents=True, exist_ok=True)
_LOCK = Lock()


def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)


def read_json(path: Path, default: Any):
    if not path.exists():
        return default
    with _LOCK:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with _LOCK:
        temp.write_text(payload, encoding="utf-8")
        temp.replace(path)


def settings_path() -> Path:
    return ROOT / "settings.json"


def projects_path() -> Path:
    return ROOT / "projects.json"


def project_dir(project_id: str) -> Path:
    path = ROOT / "projects" / safe_id(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def assets_path(project_id: str) -> Path:
    return project_dir(project_id) / "assets.json"


def jobs_path(project_id: str) -> Path:
    return project_dir(project_id) / "jobs.json"


def artifacts_dir(project_id: str, job_id: str) -> Path:
    path = project_dir(project_id) / "jobs" / safe_id(job_id) / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path
