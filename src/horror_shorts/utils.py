import json
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd=None) -> None:
    """Chạy ffmpeg/ffprobe, báo lỗi rõ ràng nếu hỏng."""
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if res.returncode != 0:
        raise RuntimeError(f"Lệnh lỗi: {' '.join(cmd[:6])}...\n{res.stderr[-1500:]}")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout)["format"]["duration"])
