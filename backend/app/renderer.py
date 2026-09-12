from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(args: list[str]) -> None:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffmpeg failed")


def render_timeline(timeline: list[dict[str, Any]], output: Path, width: int, height: int, fps: int) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg 未安装")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / "render_parts"
    work.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for idx, seg in enumerate(timeline):
        duration = max(0.4, float(seg.get("end", 0)) - float(seg.get("start", 0)))
        src = seg.get("source_path")
        media_type = seg.get("media_type", "")
        part = work / f"{idx:04d}.mp4"
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
        if src and Path(src).exists() and media_type == "video":
            start = max(0.0, float(seg.get("source_start", 0)))
            _run(["ffmpeg", "-y", "-ss", str(start), "-i", src, "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(part)])
        elif src and Path(src).exists() and media_type == "image":
            _run(["ffmpeg", "-y", "-loop", "1", "-i", src, "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(part)])
        else:
            label = str(seg.get("label", "镜头")).replace("'", "")[:80]
            _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}:d={duration}", "-vf", f"drawtext=text='{label}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=(h-text_h)/2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(part)])
        parts.append(part)
    manifest = work / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in parts), encoding="utf-8")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(output)])
    (output.parent / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def qa_video(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "issues": ["输出文件不存在"]}
    size = path.stat().st_size
    issues = []
    if size < 1024:
        issues.append("输出文件异常偏小")
    return {"ok": not issues, "size_bytes": size, "issues": issues}
