from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import Job, StageState, StageStatus
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


class PipelineManager:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.listeners: dict[str, list[asyncio.Queue]] = {}

    def create_job(self, project_id: str) -> Job:
        now = datetime.now(timezone.utc).isoformat()
        job = Job(
            id=uuid.uuid4().hex[:12],
            project_id=project_id,
            created_at=now,
            updated_at=now,
            stages=[StageStatus(id=sid, label=label) for sid, label in STAGES],
        )
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
        if job_id in self.listeners and queue in self.listeners[job_id]:
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
        records = read_json(jobs_path(job.project_id), [])
        records = [r for r in records if r.get("id") != job.id]
        records.insert(0, job.model_dump(mode="json"))
        write_json(jobs_path(job.project_id), records[:30])

    def _write_artifact(self, job: Job, stage_id: str, payload: dict) -> str:
        path = artifacts_dir(job.project_id, job.id) / f"{stage_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    async def run(self, job: Job, source_text: str, asset_count: int, target_duration: int) -> None:
        job.state = "running"
        await self.emit(job, {"type": "job", "state": job.state})
        try:
            for index, stage in enumerate(job.stages):
                stage.state = StageState.running
                stage.progress = 5
                stage.detail = "正在处理"
                job.updated_at = datetime.now(timezone.utc).isoformat()
                self._persist(job)
                await self.emit(job, {"type": "stage", "stage": stage.model_dump(mode="json")})

                for progress in (25, 55, 80):
                    await asyncio.sleep(0.22)
                    stage.progress = progress
                    await self.emit(job, {"type": "stage", "stage": stage.model_dump(mode="json")})

                artifact = self._stage_payload(stage.id, source_text, asset_count, target_duration)
                stage.artifact = self._write_artifact(job, stage.id, artifact)
                stage.state = StageState.done
                stage.progress = 100
                stage.detail = artifact.get("summary", "完成")
                log = f"[{index + 1:02d}/{len(job.stages):02d}] {stage.label}: {stage.detail}"
                job.logs.append(log)

                if stage.id == "timeline":
                    job.timeline = artifact.get("segments", [])

                self._persist(job)
                await self.emit(job, {"type": "stage", "stage": stage.model_dump(mode="json")})
                await self.emit(job, {"type": "log", "message": log})

            job.state = "done"
            self._persist(job)
            await self.emit(job, {"type": "job", "state": "done", "timeline": job.timeline})
        except Exception as exc:
            job.state = "error"
            job.logs.append(f"ERROR: {exc}")
            self._persist(job)
            await self.emit(job, {"type": "job", "state": "error", "error": str(exc)})

    def _stage_payload(self, stage_id: str, source_text: str, asset_count: int, duration: int) -> dict:
        cleaned = re.sub(r"\s+", " ", source_text).strip()
        sentences = [s.strip() for s in re.split(r"[。！？!?\n]+", cleaned) if s.strip()]
        if not sentences and cleaned:
            sentences = [cleaned]
        if stage_id == "ingest":
            return {"summary": f"整理 {len(cleaned)} 字，已导入 {asset_count} 个素材", "text": cleaned}
        if stage_id == "facts":
            return {"summary": f"生成 {max(1, min(len(sentences), 8))} 个事实候选", "facts": [{"id": i + 1, "statement": s} for i, s in enumerate(sentences[:8])]}
        if stage_id == "verify":
            return {"summary": "已建立待核验事实清单", "status": "needs_source_adapters"}
        if stage_id == "narrative":
            return {"summary": "已生成叙事占位结构", "beats": sentences[:6]}
        if stage_id == "shot_plan":
            return {"summary": f"规划 {max(1, min(len(sentences), 8))} 个镜头单元", "shots": [{"shot": i + 1, "voiceover": s, "desired": "direct_event_or_context"} for i, s in enumerate(sentences[:8])]}
        if stage_id == "search":
            return {"summary": "已生成素材检索计划；等待具体站点适配器", "queries": sentences[:8]}
        if stage_id == "analyze_media":
            return {"summary": f"素材池当前 {asset_count} 项；真实媒体分析将在安装工具后启用", "asset_count": asset_count}
        if stage_id == "rank":
            return {"summary": "已建立候选排序接口", "strategy": "tool -> embedding -> local model -> top-N"}
        if stage_id == "ai_review":
            return {"summary": "强模型阶段已生成交接点", "mode": "ChatGPT Work/manual handoff"}
        if stage_id == "timeline":
            count = max(1, min(len(sentences), 6))
            each = max(2, duration // count)
            segments = []
            cursor = 0
            for i in range(count):
                end = duration if i == count - 1 else min(duration, cursor + each)
                segments.append({"id": i + 1, "start": cursor, "end": end, "label": sentences[i][:26] if i < len(sentences) else f"镜头 {i+1}", "track": "V1"})
                cursor = end
            return {"summary": f"生成 {count} 段可视化时间线", "segments": segments}
        if stage_id == "render":
            return {"summary": "渲染器接口就绪；有真实片段后调用 FFmpeg", "output": "final.mp4"}
        if stage_id == "qa":
            return {"summary": "QA 检查表已生成", "checks": ["黑帧", "重复镜头", "字幕越界", "画面/事实错配", "资料画面标记", "音量", "清晰度"]}
        return {"summary": "完成"}


manager = PipelineManager()
