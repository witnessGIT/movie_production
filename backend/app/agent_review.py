from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


SAMPLE_RATIOS = (0.15, 0.5, 0.85)


def _sample_times(start: float, end: float) -> list[float]:
    duration = max(0.0, end - start)
    if duration <= 0:
        return [max(0.0, start)]
    return [round(start + duration * ratio, 3) for ratio in SAMPLE_RATIOS]


def build_agent_review_packet(video_path: Path, timeline: list[dict[str, Any]], output_dir: Path | None = None) -> dict[str, Any]:
    """Turn a video into still-image evidence that an agent without playback can inspect."""
    output_dir = output_dir or video_path.parent / "agent_review_frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    segments: list[dict[str, Any]] = []
    extraction_errors: list[dict[str, Any]] = []

    for index, segment in enumerate(timeline, 1):
        start = float(segment.get("start") or 0.0)
        end = float(segment.get("end") or start)
        frames: list[dict[str, Any]] = []
        for frame_index, timestamp in enumerate(_sample_times(start, end), 1):
            frame_path = output_dir / f"segment_{index:03d}_frame_{frame_index}.jpg"
            proc = subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-ss", str(timestamp), "-i", str(video_path),
                    "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "3", str(frame_path),
                ],
                capture_output=True, text=True, check=False,
            )
            if proc.returncode == 0 and frame_path.exists() and frame_path.stat().st_size > 0:
                frames.append({
                    "position": ("start", "middle", "end")[frame_index - 1],
                    "timestamp_sec": timestamp,
                    "path": str(frame_path),
                })
            else:
                extraction_errors.append({
                    "segment_id": segment.get("id", index),
                    "timestamp_sec": timestamp,
                    "error": proc.stderr.strip() or "关键帧提取失败",
                })

        segments.append({
            "segment_id": segment.get("id", index),
            "timeline_start_sec": start,
            "timeline_end_sec": end,
            "voiceover_or_label": segment.get("label", ""),
            "asset_id": segment.get("asset_id"),
            "media_type": segment.get("media_type", "unknown"),
            "source_path": segment.get("source_path"),
            "source_start_sec": segment.get("source_start", 0.0),
            "source_end_sec": segment.get("source_end", 0.0),
            "frames": frames,
            "agent_checks": {
                "visual_matches_voiceover": "pending",
                "person_place_event_match": "pending",
                "time_context_not_misleading": "pending",
                "visible_text_consistent": "pending",
                "notes": "",
            },
        })

    packet = {
        "schema_version": "1.0",
        "video": str(video_path),
        "purpose": "供无法直接播放视频的普通 Agent 逐镜头检查语义",
        "instructions": [
            "依次查看每个镜头的 start、middle、end 三张关键帧。",
            "把画面与 voiceover_or_label、素材来源和时间码比较。",
            "只能把有图像证据支持的项目改为 pass；不确定时填 needs_human_review。",
            "人物、地点、事件或时间背景不一致时填 fail，并在 notes 中说明。",
            "不得仅根据文件名、候选分数或程序 QA 推断语义通过。",
        ],
        "segments": segments,
        "extraction_errors": extraction_errors,
        "review_status": "blocked" if extraction_errors or any(len(x["frames"]) < 3 for x in segments) else "pending",
        "review_result_path": str(video_path.parent / "agent_review_result.json"),
        "result_schema": {
            "reviewer": "普通 Agent 的名称或运行标识",
            "segments": [{
                "segment_id": "必须与本文件中的 segment_id 一致",
                "visual_matches_voiceover": "pass | fail | needs_human_review",
                "person_place_event_match": "pass | fail | needs_human_review",
                "time_context_not_misleading": "pass | fail | needs_human_review",
                "visible_text_consistent": "pass | fail | needs_human_review",
                "notes": "判断依据；fail 或 needs_human_review 时必填",
            }],
        },
    }
    packet_path = video_path.parent / "agent_review.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**packet, "packet_path": str(packet_path)}


def load_timeline(video_path: Path) -> list[dict[str, Any]]:
    path = video_path.parent / "timeline.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


REQUIRED_CHECKS = (
    "visual_matches_voiceover",
    "person_place_event_match",
    "time_context_not_misleading",
    "visible_text_consistent",
)


def evaluate_agent_review_result(video_path: Path, packet: dict[str, Any]) -> dict[str, Any]:
    """Validate an ordinary Agent's structured review without trusting a bare pass flag."""
    result_path = video_path.parent / "agent_review_result.json"
    if packet.get("review_status") == "blocked":
        return {"status": "blocked", "result_path": str(result_path), "issues": ["关键帧证据不完整"]}
    if not result_path.exists():
        return {"status": "pending", "result_path": str(result_path), "issues": ["尚未提交普通 Agent 语义检查结果"]}
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "result_path": str(result_path), "issues": ["agent_review_result.json 无法读取"]}

    expected_ids = [segment.get("segment_id") for segment in packet.get("segments", [])]
    reviews = result.get("segments")
    if not isinstance(reviews, list):
        return {"status": "invalid", "result_path": str(result_path), "issues": ["检查结果缺少 segments 数组"]}
    by_id = {item.get("segment_id"): item for item in reviews if isinstance(item, dict)}
    issues: list[str] = []
    has_fail = False
    has_escalation = False
    for segment_id in expected_ids:
        review = by_id.get(segment_id)
        if review is None:
            issues.append(f"镜头 {segment_id} 缺少检查结果")
            continue
        for check in REQUIRED_CHECKS:
            value = review.get(check)
            if value not in {"pass", "fail", "needs_human_review"}:
                issues.append(f"镜头 {segment_id} 的 {check} 状态无效")
            elif value == "fail":
                has_fail = True
            elif value == "needs_human_review":
                has_escalation = True
        if any(review.get(check) in {"fail", "needs_human_review"} for check in REQUIRED_CHECKS) and not str(review.get("notes") or "").strip():
            issues.append(f"镜头 {segment_id} 未说明失败或升级依据")

    if issues:
        status = "invalid"
    elif has_fail:
        status = "failed"
    elif has_escalation:
        status = "needs_human_review"
    else:
        status = "passed"
    return {
        "status": status,
        "result_path": str(result_path),
        "reviewer": result.get("reviewer"),
        "issues": issues,
    }
