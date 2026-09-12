from __future__ import annotations

import shutil
import socket
from dataclasses import asdict, dataclass


@dataclass
class Capability:
    id: str
    label: str
    available: bool
    detail: str
    tier: str


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def detect_capabilities() -> list[dict]:
    checks = [
        Capability("ffmpeg", "FFmpeg", shutil.which("ffmpeg") is not None, "视频剪辑/编码", "TIER 0"),
        Capability("ffprobe", "FFprobe", shutil.which("ffprobe") is not None, "媒体元数据检测", "TIER 0"),
        Capability("yt_dlp", "yt-dlp", shutil.which("yt-dlp") is not None, "允许来源的视频获取", "TIER 0"),
        Capability("ollama", "Ollama", _port_open("127.0.0.1", 11434), "本地模型服务 localhost:11434", "TIER 1/2"),
        Capability("lmstudio", "LM Studio", _port_open("127.0.0.1", 1234), "本地模型服务 localhost:1234", "TIER 1/2"),
    ]
    try:
        import faster_whisper  # noqa: F401
        checks.append(Capability("whisper", "faster-whisper", True, "语音转文字", "专用模型"))
    except Exception:
        checks.append(Capability("whisper", "faster-whisper", False, "未安装 Python 包", "专用模型"))
    try:
        import scenedetect  # noqa: F401
        checks.append(Capability("scenedetect", "PySceneDetect", True, "视频镜头切分", "TIER 0"))
    except Exception:
        checks.append(Capability("scenedetect", "PySceneDetect", False, "未安装 Python 包", "TIER 0"))
    return [asdict(item) for item in checks]
