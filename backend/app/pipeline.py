from __future__ import annotations

import asyncio
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .media_engine import analyze_asset
from .models import AppSettings, Job, StageState, StageStatus
from .ranking import rank_candidates
from .renderer import qa_video, render_timeline
from .storage import artifacts_dir, jobs_path, read_json, write_json


STAGES = [
    ("ingest", "输入整理"),
    ("facts", "事实解析"),
    ("verify", "事实/时间核验"),
    ("narrative", "旁白与叙事规划"),
    ("shot_plan", "镜头需求规划"),
    ("search", "素材检索计划"),
    ("analyze_media", "素材解析"),
    ("rank", "候选片段粗筛"),
    ("ai_review", "强模型复核"),
    ("timeline", "时间线生成"),
    ("render", "视频渲染"),
    ("qa", "成片质量检查"),
]


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    parts = [x.strip() for x in re.split(r"[。！？!?\n]+", cleaned) if x.strip()]
    return parts or ([cleaned] if cleaned else ["未提供文案"])


class PipelineManager:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.listeners: dict[str, list[asyncio.Queue]] = {}

    def create_job(self, project_id: str) -> Job:
        now = datetime.now(timezone.utc).isoformat()
        job = Job(id=uuid.uuid4().hex[:12], project_id=project_id, created_at=now, updated_at=now,
                  stages=[StageStatus(id=sid, label=label) for sid, label in STAGES])
        self.jobs[job.id] = job
        self._persist(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def list_jobs(self, project_id: str) -> list[dict]:
        return read_json(jobs_path(project_id), [])

    def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.listeners.setdefault(job_id, []).append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        if queue in self.listeners.get(job_id, []):
            self.listeners[job_id].remove(queue)

    async def emit(self, job: Job, event: dict) -> None:
        event = {"job_id": job.id, **event}
        for queue in list(self.listeners.get(job.id, [])):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await queue.put(event)

    def _persist(self, job: Job) -> None:
        records = [r for r in read_json(jobs_path(job.project_id), []) if r.get("id") != job.id]
        records.insert(0, job.model_dump(mode="json"))
        write_json(jobs_path(job.project_id), records[:30])

    def _write_artifact(self, job: Job, stage_id: str, payload: dict) -> str:
        path = artifacts_dir(job.project_id, job.id) / f"{stage_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    async def _begin(self, job: Job, stage: StageStatus) -> None:
        stage.state, stage.progress, stage.detail = StageState.running, 10, "正在处理"
        self._persist(job)
        await self.emit(job, {"type": "stage", "stage": stage.model_dump(mode="json")})

    async def _finish(self, job: Job, stage: StageStatus, index: int, payload: dict) -> None:
        stage.artifact = self._write_artifact(job, stage.id, payload)
        stage.state, stage.progress = StageState.done, 100
        stage.detail = payload.get("summary", "完成")
        log = f"[{index + 1:02d}/{len(job.stages):02d}] {stage.label}: {stage.detail}"
        job.logs.append(log)
        if stage.id == "timeline":
            job.timeline = payload.get("segments", [])
        self._persist(job)
        await self.emit(job, {"type": "stage", "stage": stage.model_dump(mode="json")})
        await self.emit(job, {"type": "log", "message": log})

    async def run(self, job: Job, source_text: str, assets: list[dict], settings: AppSettings) -> None:
        job.state = "running"
        await self.emit(job, {"type": "job", "state": "running"})
        state: dict = {"sentences": _sentences(source_text), "assets": assets}
        try:
            for index, stage in enumerate(job.stages):
                await self._begin(job, stage)
                payload = await self._run_stage(stage.id, job, source_text, state, settings)
                await self._finish(job, stage, index, payload)
            job.state = "done"
            self._persist(job)
            await self.emit(job, {"type": "job", "state": "done", "timeline": job.timeline})
        except Exception as exc:
            job.state = "error"
            current = next((s for s in job.stages if s.state == StageState.running), None)
            if current:
                current.state, current.detail = StageState.error, str(exc)
            job.logs.append(f"ERROR: {exc}")
            self._persist(job)
            await self.emit(job, {"type": "job", "state": "error", "error": str(exc)})

    async def _run_stage(self, stage_id: str, job: Job, source_text: str, state: dict, settings: AppSettings) -> dict:
        sentences = state["sentences"]
        if stage_id == "ingest":
            cleaned = re.sub(r"\s+", " ", source_text or "").strip()
            return {"summary": f"整理 {len(cleaned)} 字，导入 {len(state['assets'])} 个素材", "text": cleaned}
        if stage_id == "facts":
            facts = [{"id": i + 1, "statement": s, "status": "unverified"} for i, s in enumerate(sentences[:12])]
            state["facts"] = facts
            return {"summary": f"提取 {len(facts)} 个事实单元", "facts": facts}
        if stage_id == "verify":
            checks = [{"fact_id": f["id"], "status": "needs_source_check", "statement": f["statement"]} for f in state.get("facts", [])]
            state["verification"] = checks
            return {"summary": "已建立事实核验清单；用户导入的新闻URL将作为证据来源", "checks": checks}
        if stage_id == "narrative":
            beats = [{"id": i + 1, "text": s} for i, s in enumerate(sentences[:10])]
            state["beats"] = beats
            return {"summary": f"生成 {len(beats)} 个叙事单元", "beats": beats}
        if stage_id == "shot_plan":
            shots = [{"shot": i + 1, "voiceover": b["text"], "desired": "direct_event_or_context"} for i, b in enumerate(state.get("beats", []))]
            state["shots"] = shots
            return {"summary": f"规划 {len(shots)} 个镜头", "shots": shots}
        if stage_id == "search":
            refs = [a for a in state["assets"] if a.get("kind") == "url"]
            return {"summary": f"生成 {len(state.get('shots', []))} 条检索意图，已有 {len(refs)} 个外部来源", "queries": [s["voiceover"] for s in state.get("shots", [])], "references": refs}
        if stage_id == "analyze_media":
            analyses = []
            total = max(1, len(state["assets"]))
            stage = next(s for s in job.stages if s.id == stage_id)
            for i, asset in enumerate(state["assets"]):
                result = await asyncio.to_thread(analyze_asset, asset, True)
                analyses.append(result)
                stage.progress = 10 + int((i + 1) / total * 80)
                await self.emit(job, {"type": "stage", "stage": stage.model_dump(mode="json")})
            state["analyses"] = analyses
            candidates = [c for a in analyses for c in a.get("candidates", [])]
            state["candidates"] = candidates
            return {"summary": f"分析 {len(analyses)} 个素材，生成 {len(candidates)} 个候选片段", "analyses": analyses, "candidate_count": len(candidates)}
        if stage_id == "rank":
            ranked = rank_candidates(state.get("shots", []), state.get("candidates", []), settings.max_candidate_clips_per_shot)
            state["ranked"] = ranked
            return {"summary": f"完成 {len(ranked)} 个镜头的候选排序", "ranked": ranked}
        if stage_id == "ai_review":
            selected = []
            for item in state.get("ranked", []):
                best = (item.get("candidates") or [None])[0]
                selected.append({"shot": item.get("shot"), "selected": best, "review": "provisional_top1"})
            state["selected"] = selected
            mode = settings.models.strong_model_mode
            return {"summary": "已生成强模型交接包；当前自动采用 Top-1 作为临时选择" if mode == "chatgpt_handoff" else "本地模式：采用自动排序结果", "mode": mode, "selected": selected, "manual_review_recommended": mode == "chatgpt_handoff"}
        if stage_id == "timeline":
            segments = self._build_timeline(state.get("selected", []), settings.video.target_duration_sec)
            state["timeline"] = segments
            return {"summary": f"生成 {len(segments)} 段真实时间线", "segments": segments}
        if stage_id == "render":
            out_dir = artifacts_dir(job.project_id, job.id).parent
            ext = settings.video.format
            output = out_dir / f"final.{ext}"
            if not shutil.which("ffmpeg"):
                return {"summary": "FFmpeg 未安装：时间线已生成，暂未输出视频", "output": None, "ffmpeg": False}
            await asyncio.to_thread(render_timeline, state.get("timeline", []), output, settings.video.width, settings.video.height, settings.video.fps)
            state["output"] = str(output)
            return {"summary": f"已渲染成片 {output.name}", "output": str(output), "ffmpeg": True}
        if stage_id == "qa":
            output = state.get("output")
            result = qa_video(Path(output)) if output else {"ok": False, "issues": ["尚未生成视频；请安装 FFmpeg 后重跑"]}
            return {"summary": "成片检查通过" if result.get("ok") else "成片检查完成，存在待处理项", **result}
        return {"summary": "完成"}

    def _build_timeline(self, selected: list[dict], duration: int) -> list[dict]:
        if not selected:
            return [{"id": 1, "start": 0.0, "end": float(duration), "label": "无可用素材", "track": "V1", "media_type": "placeholder"}]
        count = len(selected)
        each = max(1.5, float(duration) / count)
        cursor = 0.0
        segments = []
        for i, item in enumerate(selected):
            shot = item.get("shot") or {}
            candidate = item.get("selected") or {}
            planned = float(duration) - cursor if i == count - 1 else each
            media_type = candidate.get("media_type", "placeholder")
            if media_type == "video" and candidate.get("duration"):
                planned = min(planned, max(1.0, float(candidate["duration"])))
            end = min(float(duration), cursor + planned)
            segments.append({
                "id": i + 1, "start": round(cursor, 3), "end": round(end, 3),
                "label": (shot.get("voiceover") or f"镜头 {i+1}")[:60], "track": "V1",
                "asset_id": candidate.get("asset_id"), "media_type": media_type,
                "source_path": candidate.get("path"), "source_start": candidate.get("start", 0.0),
                "source_end": candidate.get("end", 0.0), "score": candidate.get("score", 0.0),
            })
            cursor = end
            if cursor >= duration:
                break
        if cursor < duration:
            segments.append({"id": len(segments)+1, "start": round(cursor, 3), "end": float(duration), "label": "补位镜头", "track": "V1", "media_type": "placeholder"})
        return segments


manager = PipelineManager()
