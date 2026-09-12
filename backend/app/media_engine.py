from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
from pathlib import Path
from typing import Any


def run_command(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def ffprobe(path: Path) -> dict[str, Any]:
    if not shutil.which("ffprobe"):
        return {"available": False, "duration": 0.0, "width": None, "height": None, "fps": None, "streams": []}
    proc = run_command([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json", str(path),
    ])
    if proc.returncode != 0:
        return {"available": True, "error": proc.stderr.strip(), "duration": 0.0, "streams": []}
    data = json.loads(proc.stdout or "{}")
    duration = float((data.get("format") or {}).get("duration") or 0.0)
    width = height = None
    fps = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width, height = stream.get("width"), stream.get("height")
            rate = stream.get("r_frame_rate") or "0/1"
            try:
                a, b = rate.split("/")
                fps = round(float(a) / max(float(b), 1.0), 3)
            except Exception:
                fps = None
            break
    return {"available": True, "duration": duration, "width": width, "height": height, "fps": fps, "streams": data.get("streams", []), "format": data.get("format", {})}


def detect_scenes(path: Path, duration: float) -> list[dict[str, float]]:
    try:
        from scenedetect import ContentDetector, detect
        scenes = detect(str(path), ContentDetector(threshold=27.0), start_in_scene=True)
        result = [{"start": round(a.get_seconds(), 3), "end": round(b.get_seconds(), 3)} for a, b in scenes if b.get_seconds() > a.get_seconds()]
        if result:
            return result
    except Exception:
        pass
    if duration > 0:
        return [{"start": 0.0, "end": round(duration, 3)}]
    return []


def transcribe(path: Path, model_name: str = "small") -> list[dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return []
    try:
        model = WhisperModel(model_name, device="auto", compute_type="int8")
        segments, _ = model.transcribe(str(path), vad_filter=True)
        return [{"start": round(float(s.start), 3), "end": round(float(s.end), 3), "text": s.text.strip()} for s in segments]
    except Exception:
        return []


def _scene_text(scene: dict[str, float], transcript: list[dict[str, Any]]) -> str:
    pieces = []
    for item in transcript:
        if item["end"] >= scene["start"] and item["start"] <= scene["end"]:
            pieces.append(item["text"])
    return " ".join(pieces).strip()


def analyze_asset(asset: dict, enable_transcription: bool = True, whisper_model: str = "small") -> dict[str, Any]:
    local = asset.get("local_path")
    media_type = asset.get("media_type") or mimetypes.guess_type(asset.get("label", ""))[0] or "application/octet-stream"
    result: dict[str, Any] = {"asset_id": asset.get("id"), "label": asset.get("label", ""), "kind": asset.get("kind"), "media_type": media_type, "source": asset.get("source", ""), "local_path": local, "candidates": []}
    if not local:
        result["status"] = "remote_reference"
        return result
    path = Path(local)
    if not path.exists():
        result["status"] = "missing"
        return result
    if media_type.startswith("text/") or path.suffix.lower() in {".txt", ".md", ".srt", ".vtt"}:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:50000]
        except Exception:
            text = ""
        result.update({"status": "ok", "text": text, "candidates": [{"asset_id": asset.get("id"), "start": 0.0, "end": 0.0, "text": text[:4000], "media_type": "text"}]})
        return result
    if media_type.startswith("image/") or path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        result.update({"status": "ok", "candidates": [{"asset_id": asset.get("id"), "start": 0.0, "end": 5.0, "text": asset.get("label", ""), "media_type": "image", "path": str(path)}]})
        return result
    meta = ffprobe(path)
    result["metadata"] = meta
    duration = float(meta.get("duration") or 0.0)
    transcript = transcribe(path, whisper_model) if enable_transcription and (media_type.startswith("video/") or media_type.startswith("audio/")) else []
    result["transcript"] = transcript
    if media_type.startswith("video/") or path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
        scenes = detect_scenes(path, duration)
        result["scenes"] = scenes
        result["candidates"] = [{"asset_id": asset.get("id"), "start": s["start"], "end": s["end"], "duration": round(s["end"] - s["start"], 3), "text": _scene_text(s, transcript) or asset.get("label", ""), "media_type": "video", "path": str(path), "width": meta.get("width"), "height": meta.get("height")} for s in scenes]
    elif media_type.startswith("audio/"):
        result["candidates"] = [{"asset_id": asset.get("id"), "start": x["start"], "end": x["end"], "duration": round(x["end"] - x["start"], 3), "text": x["text"], "media_type": "audio", "path": str(path)} for x in transcript]
    result["status"] = "ok"
    return result
