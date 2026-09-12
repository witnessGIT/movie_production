from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def materialize_video_url(asset: dict, target_dir: Path) -> dict:
    """Download a user-supplied public video URL when yt-dlp is available.

    This intentionally does not provide cookies, credentials, DRM bypasses, or login-wall workarounds.
    Failures are returned as metadata and never crash the pipeline.
    """
    url = str(asset.get("source") or "").strip()
    if asset.get("kind") != "url" or asset.get("media_type") != "video":
        return asset
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {**asset, "download_error": "invalid URL"}
    exe = shutil.which("yt-dlp")
    if not exe:
        return {**asset, "download_error": "yt-dlp not installed"}
    target_dir.mkdir(parents=True, exist_ok=True)
    template = str(target_dir / f"{asset.get('id','video')}.%(ext)s")
    cmd = [
        exe, "--no-playlist", "--no-warnings", "--restrict-filenames",
        "-f", "bestvideo*+bestaudio/best", "--merge-output-format", "mp4",
        "--print", "after_move:filepath", "-o", template, url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    except Exception as exc:
        return {**asset, "download_error": str(exc)}
    if proc.returncode != 0:
        return {**asset, "download_error": (proc.stderr or "download failed")[-1000:]}
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return {**asset, "download_error": "yt-dlp returned no output path"}
    path = Path(lines[-1])
    if not path.exists():
        return {**asset, "download_error": "downloaded file not found"}
    return {**asset, "local_path": str(path), "kind": "file", "media_type": "video/mp4", "downloaded_from": url}
