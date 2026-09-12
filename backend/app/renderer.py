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


def _encode_part(args: list[str], part: Path, bitrate: str) -> None:
    _run(args + ["-an", "-c:v", "libx264", "-preset", "veryfast", "-b:v", bitrate, "-pix_fmt", "yuv420p", str(part)])


def _srt_time(value: float) -> str:
    ms = int(round(max(0.0, value) * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def write_srt(timeline: list[dict[str, Any]], path: Path) -> Path:
    blocks = []
    for i, seg in enumerate(timeline, 1):
        label = str(seg.get("label") or "").strip()
        if not label:
            continue
        blocks.append(f"{i}\n{_srt_time(float(seg.get('start', 0)))} --> {_srt_time(float(seg.get('end', 0)))}\n{label}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path


def render_timeline(timeline: list[dict[str, Any]], output: Path, width: int, height: int, fps: int,
                    narration: Path | None = None, subtitles: bool = True, bitrate: str = "8M") -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg 未安装")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / "render_parts"
    work.mkdir(parents=True, exist_ok=True)
    if not timeline:
        timeline = [{"start": 0.0, "end": 3.0, "media_type": "placeholder", "label": "empty"}]
    parts: list[Path] = []
    for idx, seg in enumerate(timeline):
        duration = max(0.4, float(seg.get("end", 0)) - float(seg.get("start", 0)))
        src = seg.get("source_path")
        media_type = seg.get("media_type", "")
        part = work / f"{idx:04d}.mp4"
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
        if src and Path(src).exists() and media_type == "video":
            start = max(0.0, float(seg.get("source_start", 0)))
            _encode_part(["ffmpeg", "-y", "-ss", str(start), "-i", src, "-t", str(duration), "-vf", vf], part, bitrate)
        elif src and Path(src).exists() and media_type == "image":
            _encode_part(["ffmpeg", "-y", "-loop", "1", "-i", src, "-t", str(duration), "-vf", vf], part, bitrate)
        else:
            _encode_part(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}:d={duration}", "-t", str(duration)], part, bitrate)
        parts.append(part)
    manifest = work / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in parts), encoding="utf-8")
    visual = work / "visual.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(visual)])

    subtitle_path = output.with_suffix(".srt")
    if subtitles:
        write_srt(timeline, subtitle_path)

    has_audio = narration is not None and narration.exists()
    suffix = output.suffix.lower()
    if suffix == ".webm":
        cmd = ["ffmpeg", "-y", "-i", str(visual)]
        if has_audio:
            cmd += ["-i", str(narration)]
        cmd += ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33"]
        cmd += ["-c:a", "libopus", "-shortest"] if has_audio else ["-an"]
        cmd += [str(output)]
        _run(cmd)
    elif suffix == ".mov":
        cmd = ["ffmpeg", "-y", "-i", str(visual)]
        if has_audio:
            cmd += ["-i", str(narration), "-c:v", "copy", "-c:a", "aac", "-shortest"]
        else:
            cmd += ["-c:v", "copy", "-an"]
        cmd += [str(output)]
        _run(cmd)
    elif has_audio:
        _run(["ffmpeg", "-y", "-i", str(visual), "-i", str(narration), "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)])
    else:
        shutil.copy2(visual, output)

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
