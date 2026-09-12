from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import AppSettings, Asset, Project, ProjectCreate, TextAssetCreate, URLAssetCreate
from .pipeline import manager
from .storage import assets_path, project_dir, projects_path, read_json, settings_path, write_json
from .tooling import detect_capabilities

app = FastAPI(title="Movie Production API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_project(project_id: str) -> dict:
    for project in read_json(projects_path(), []):
        if project.get("id") == project_id:
            return project
    raise HTTPException(404, "Project not found")


@app.get("/api/health")
def health():
    return {"ok": True, "version": "0.1.0"}


@app.get("/api/capabilities")
def capabilities():
    return detect_capabilities()


@app.get("/api/settings", response_model=AppSettings)
def get_settings():
    return AppSettings.model_validate(read_json(settings_path(), {}))


@app.put("/api/settings", response_model=AppSettings)
def put_settings(payload: AppSettings):
    write_json(settings_path(), payload.model_dump(mode="json"))
    return payload


@app.get("/api/projects")
def list_projects():
    projects = read_json(projects_path(), [])
    for project in projects:
        project["asset_count"] = len(read_json(assets_path(project["id"]), []))
    return projects


@app.post("/api/projects", response_model=Project)
def create_project(payload: ProjectCreate):
    stamp = now()
    project = Project(id=uuid.uuid4().hex[:10], title=payload.title.strip(), source_text=payload.source_text, created_at=stamp, updated_at=stamp)
    projects = read_json(projects_path(), [])
    projects.insert(0, project.model_dump(mode="json"))
    write_json(projects_path(), projects)
    project_dir(project.id)
    return project


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, payload: ProjectCreate):
    projects = read_json(projects_path(), [])
    found = False
    for project in projects:
        if project.get("id") == project_id:
            project["title"] = payload.title.strip()
            project["source_text"] = payload.source_text
            project["updated_at"] = now()
            found = True
            result = project
            break
    if not found:
        raise HTTPException(404, "Project not found")
    write_json(projects_path(), projects)
    return result


@app.get("/api/projects/{project_id}/assets")
def list_assets(project_id: str):
    get_project(project_id)
    return read_json(assets_path(project_id), [])


def append_asset(project_id: str, asset: Asset):
    items = read_json(assets_path(project_id), [])
    items.insert(0, asset.model_dump(mode="json"))
    write_json(assets_path(project_id), items)
    return asset


@app.post("/api/projects/{project_id}/assets/url", response_model=Asset)
def add_url_asset(project_id: str, payload: URLAssetCreate):
    get_project(project_id)
    return append_asset(project_id, Asset(id=uuid.uuid4().hex[:12], project_id=project_id, kind="url", media_type=payload.source_type, label=payload.label or payload.url, source=payload.url, created_at=now(), notes=payload.notes))


@app.post("/api/projects/{project_id}/assets/text", response_model=Asset)
def add_text_asset(project_id: str, payload: TextAssetCreate):
    get_project(project_id)
    target = project_dir(project_id) / "imports" / f"{uuid.uuid4().hex[:12]}.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.text, encoding="utf-8")
    return append_asset(project_id, Asset(id=target.stem, project_id=project_id, kind="text", media_type="text/plain", label=payload.label, source="manual", local_path=str(target), size_bytes=target.stat().st_size, sha256=hashlib.sha256(payload.text.encode()).hexdigest(), created_at=now(), notes=payload.notes))


@app.post("/api/projects/{project_id}/assets/upload", response_model=Asset)
async def upload_asset(project_id: str, file: UploadFile = File(...)):
    get_project(project_id)
    safe_name = Path(file.filename or "upload.bin").name
    target = project_dir(project_id) / "uploads" / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with target.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            out.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    media_type = file.content_type or "application/octet-stream"
    return append_asset(project_id, Asset(id=uuid.uuid4().hex[:12], project_id=project_id, kind="file", media_type=media_type, label=safe_name, source="upload", local_path=str(target), size_bytes=size, sha256=digest.hexdigest(), created_at=now()))


@app.post("/api/projects/{project_id}/jobs")
async def start_job(project_id: str):
    project = get_project(project_id)
    assets = read_json(assets_path(project_id), [])
    settings = AppSettings.model_validate(read_json(settings_path(), {}))
    job = manager.create_job(project_id)
    asyncio.create_task(manager.run(job, project.get("source_text", ""), len(assets), settings.video.target_duration_sec))
    return job


@app.get("/api/projects/{project_id}/jobs")
def list_jobs(project_id: str):
    get_project(project_id)
    return manager.list_jobs(project_id)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Active job not found; see project job history")
    return job


@app.websocket("/ws/jobs/{job_id}")
async def job_socket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    queue = manager.subscribe(job_id)
    job = manager.get_job(job_id)
    if job:
        await websocket.send_text(json.dumps({"type": "snapshot", "job": job.model_dump(mode="json")}, ensure_ascii=False))
    try:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, ensure_ascii=False))
    except WebSocketDisconnect:
        manager.unsubscribe(job_id, queue)
