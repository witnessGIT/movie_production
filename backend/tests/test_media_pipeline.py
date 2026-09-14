import shutil
from pathlib import Path

import pytest

from app.media_engine import analyze_asset
from app.ranking import lexical_score, rank_candidates
from app.renderer import qa_video, render_timeline


def test_text_asset_analysis(tmp_path: Path):
    p = tmp_path / "news.txt"
    p.write_text("日本央行宣布维持利率不变", encoding="utf-8")
    result = analyze_asset({"id": "a1", "label": "news", "kind": "file", "media_type": "text/plain", "local_path": str(p), "source": "upload"})
    assert result["status"] == "ok"
    assert result["candidates"]
    assert "日本央行" in result["candidates"][0]["text"]


def test_lexical_ranking_prefers_related_candidate():
    assert lexical_score("日本央行维持利率", "日本央行宣布维持政策利率不变") > lexical_score("日本央行维持利率", "足球比赛结束")
    ranked = rank_candidates(
        [{"shot": 1, "voiceover": "日本央行维持利率"}],
        [
            {"asset_id": "bad", "text": "足球比赛结束", "media_type": "video", "duration": 5},
            {"asset_id": "good", "text": "日本央行维持政策利率不变", "media_type": "video", "duration": 5},
        ],
        2,
    )
    assert ranked[0]["candidates"][0]["asset_id"] == "good"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_ffmpeg_render_smoke(tmp_path: Path):
    output = tmp_path / "smoke.mp4"
    render_timeline(
        [{"id": 1, "start": 0.0, "end": 1.0, "label": "smoke", "track": "V1", "media_type": "placeholder"}],
        output,
        320,
        240,
        12,
    )
    assert output.exists()
    assert output.stat().st_size > 1024
    qa = qa_video(output)
    assert qa["ok"] is True
    assert qa["duration_sec"] > 0
    assert qa["width"] == 320
    assert qa["height"] == 240


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not installed")
def test_qa_rejects_large_invalid_mp4(tmp_path: Path):
    output = tmp_path / "broken.mp4"
    output.write_bytes(b"not-a-video" * 200)
    qa = qa_video(output)
    assert qa["ok"] is False
    assert "FFprobe 无法读取成片" in qa["issues"]
