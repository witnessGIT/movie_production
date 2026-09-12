from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class StageState(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"
    skipped = "skipped"


class GPTProfile(BaseModel):
    id: str
    label: str
    browser_profile_dir: str = ""
    handoff_mode: Literal["manual_work", "manual_chat"] = "manual_work"
    notes: str = ""


class VideoSettings(BaseModel):
    width: int = Field(1920, ge=320, le=7680)
    height: int = Field(1080, ge=240, le=4320)
    fps: int = Field(30, ge=12, le=120)
    target_duration_sec: int = Field(60, ge=5, le=7200)
    bitrate: str = "8M"
    format: Literal["mp4", "mov", "webm"] = "mp4"
    subtitle_enabled: bool = True
    voiceover_enabled: bool = True
    aspect_mode: Literal["16:9", "9:16", "1:1", "custom"] = "16:9"


class ModelTierSettings(BaseModel):
    tier1_provider: Literal["ollama", "lmstudio", "disabled"] = "ollama"
    tier1_model: str = "qwen3.5:4b"
    tier2_provider: Literal["ollama", "lmstudio", "disabled"] = "ollama"
    tier2_model: str = "qwen3.5:9b"
    embedding_model: str = "bge-m3"
    whisper_model: str = "small"
    strong_model_mode: Literal["chatgpt_handoff", "local_only"] = "chatgpt_handoff"


class AppSettings(BaseModel):
    active_gpt_profile_id: str | None = None
    gpt_profiles: list[GPTProfile] = Field(default_factory=list)
    video: VideoSettings = Field(default_factory=VideoSettings)
    models: ModelTierSettings = Field(default_factory=ModelTierSettings)
    max_candidate_clips_per_shot: int = Field(3, ge=1, le=20)
    keep_intermediate_files: bool = True


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_text: str = Field(default="", max_length=200000)


class Project(BaseModel):
    id: str
    title: str
    source_text: str = ""
    created_at: str
    updated_at: str
    asset_count: int = 0


class URLAssetCreate(BaseModel):
    url: str
    label: str = ""
    source_type: Literal["news", "video", "image", "audio", "reference"] = "reference"
    notes: str = ""


class TextAssetCreate(BaseModel):
    label: str = "文本素材"
    text: str
    notes: str = ""


class Asset(BaseModel):
    id: str
    project_id: str
    kind: Literal["file", "url", "text"]
    media_type: str
    label: str
    source: str
    local_path: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    created_at: str
    notes: str = ""


class StageStatus(BaseModel):
    id: str
    label: str
    state: StageState = StageState.pending
    progress: int = Field(0, ge=0, le=100)
    detail: str = ""
    artifact: str | None = None


class Job(BaseModel):
    id: str
    project_id: str
    state: Literal["queued", "running", "done", "error"] = "queued"
    created_at: str
    updated_at: str
    stages: list[StageStatus]
    logs: list[str] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)
