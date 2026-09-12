import json
import shutil
import uuid
from pathlib import Path

import pytest

from app.models import AppSettings, ModelTierSettings, VideoSettings
from app.pipeline import manager
from app.storage import artifacts_dir


@pytest.mark.asyncio
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
async def test_pipeline_runs_text_to_mp4():
    project_id = f"ci_{uuid.uuid4().hex[:8]}"
    settings = AppSettings(
        video=VideoSettings(width=320, height=240, fps=12, target_duration_sec=5, subtitle_enabled=True, voiceover_enabled=False),
        models=ModelTierSettings(tier1_provider="disabled", tier2_provider="disabled", strong_model_mode="local_only"),
    )
    job = manager.create_job(project_id)
    await manager.run(job, "日本央行宣布维持利率不变。市场随后出现波动。", [], settings)
    assert job.state == "done"
    assert job.timeline
    render_json = artifacts_dir(project_id, job.id) / "render.json"
    assert render_json.exists()
    render = json.loads(render_json.read_text(encoding="utf-8"))
    assert render["output"]
    output = Path(render["output"])
    assert output.exists()
    assert output.stat().st_size > 1024
    qa_json = artifacts_dir(project_id, job.id) / "qa.json"
    qa = json.loads(qa_json.read_text(encoding="utf-8"))
    assert qa["ok"] is True
