"""Tùy chọn: biến ảnh của cảnh hook/twist thành video thật bằng Veo (image-to-video).

Chỉ chạy cho các cảnh trong video.veo.scenes để giữ chi phí thấp.
Clip đã tạo được lưu lại (veo_XX.mp4) nên chạy lại không tốn thêm tiền.
"""
import os
import time
from pathlib import Path

POLL_SECONDS = 10
MAX_WAIT = 600


def _wanted(cfg: dict, n_scenes: int) -> set[int]:
    return {i % n_scenes for i in cfg["video"]["veo"].get("scenes", [0])}


def generate_veo_clips(cfg: dict, story: dict, images: list[Path], out: Path,
                       mock: bool = False, costs=None) -> dict[int, Path]:
    vc = cfg["video"].get("veo", {})
    if mock or not vc.get("enabled"):
        return {}
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    style = cfg["channel"]["style"]
    clips = {}
    for i in sorted(_wanted(cfg, len(images))):
        path = out / f"veo_{i:02d}.mp4"
        if path.exists():
            clips[i] = path
            continue
        scene = story["scenes"][i]
        prompt = (f"{scene['image_prompt']}. {style}. Slow, eerie camera movement, subtle motion, "
                  "horror atmosphere. No text, no subtitles.")
        print(f"  Veo cảnh {i + 1}: đang gửi yêu cầu (mất vài phút)...")
        try:
            op = client.models.generate_videos(
                model=vc["model"],
                source=types.GenerateVideosSource(
                    prompt=prompt,
                    image=types.Image(image_bytes=images[i].read_bytes(), mime_type="image/png")),
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16", duration_seconds=8, resolution=vc.get("resolution", "720p"),
                    negative_prompt="text, watermark, gore, blood, cartoon"))
            waited = 0
            while not op.done and waited < MAX_WAIT:
                time.sleep(POLL_SECONDS)
                waited += POLL_SECONDS
                op = client.operations.get(op)
            if not op.done or not op.response or not op.response.generated_videos:
                raise RuntimeError("Veo không trả về video (hết thời gian hoặc bị chặn bởi bộ lọc)")
            video = op.response.generated_videos[0].video
            client.files.download(file=video)
            video.save(str(path))
            clips[i] = path
            if costs:
                costs.add("veo_per_second", 8, f"cảnh {i + 1}")
            print(f"  Veo cảnh {i + 1} ✓")
        except Exception as e:  # lỗi thì cảnh đó quay về Ken Burns, không hỏng cả video
            print(f"  ⚠ Veo cảnh {i + 1} lỗi: {e} — dùng ảnh + chuyển động thay thế")
    return clips
