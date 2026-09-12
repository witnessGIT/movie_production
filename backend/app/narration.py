from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def generate_narration(text: str, output: Path, enabled: bool = True) -> Path | None:
    """Best-effort local TTS. No cloud API is used.

    Windows uses System.Speech through PowerShell. macOS uses `say` when available.
    Linux returns None unless a future local TTS provider is installed.
    """
    if not enabled or not text.strip():
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32" and shutil.which("powershell"):
        safe_text = text.replace("'", "''")
        safe_path = str(output).replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SetOutputToWaveFile('{safe_path}'); "
            f"$s.Speak('{safe_text}'); $s.Dispose();"
        )
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
        return output if proc.returncode == 0 and output.exists() else None
    if sys.platform == "darwin" and shutil.which("say"):
        aiff = output.with_suffix(".aiff")
        proc = subprocess.run(["say", "-o", str(aiff), text], capture_output=True, text=True, check=False)
        if proc.returncode == 0 and aiff.exists() and shutil.which("ffmpeg"):
            conv = subprocess.run(["ffmpeg", "-y", "-i", str(aiff), str(output)], capture_output=True, text=True, check=False)
            aiff.unlink(missing_ok=True)
            return output if conv.returncode == 0 and output.exists() else None
    return None
