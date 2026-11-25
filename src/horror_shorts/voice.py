"""Bước 3: AI đọc lời dẫn + lấy mốc thời gian từng từ cho phụ đề karaoke.

Mỗi cảnh tạo voice_XX.mp3 và voice_XX.words.json: [{"w": "từ", "s": 0.12, "e": 0.40}, ...]
Đã có file thì bỏ qua (chạy lại không tốn tiền).
"""
import asyncio
import json
import os
from pathlib import Path
import requests
from .utils import run, duration


async def _edge_async(text: str, path: Path, voice: str, rate: str) -> list[dict]:
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7  # đơn vị 100 nano giây -> giây
                words.append({"w": chunk["text"], "s": s, "e": s + chunk["duration"] / 1e7})
    return words


def _elevenlabs(text: str, path: Path):
    vid = os.environ["ELEVENLABS_VOICE_ID"]
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                      json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)


def _mock(text: str, path: Path):
    secs = max(2.5, len(text.split()) / 2.6)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{secs:.2f}", "-q:a", "9", str(path)])


def _whisper_words(text: str, path: Path) -> list[dict]:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    with open(path, "rb") as f:
        res = client.audio.transcriptions.create(
            model="whisper-1", file=f, response_format="verbose_json",
            timestamp_granularities=["word"])
    got = [{"w": w.word, "s": w.start, "e": w.end} for w in (res.words or [])]
    script = text.split()
    if len(got) == len(script):  # cùng số từ: giữ chính tả gốc của kịch bản
        for g, w in zip(got, script):
            g["w"] = w
    return got


def estimate_words(text: str, total: float) -> list[dict]:
    """Ước lượng mốc thời gian theo độ dài từ khi không có dữ liệu chính xác."""
    words = text.split()
    weights = [len(w) + 2 for w in words]
    unit, t, out = total / (sum(weights) or 1), 0.0, []
    for w, k in zip(words, weights):
        out.append({"w": w, "s": t, "e": t + k * unit})
        t += k * unit
    return out


def generate_voice(cfg: dict, story: dict, out: Path, mock: bool = False, costs=None) -> list[Path]:
    vc = cfg["voice"]
    provider = "mock" if mock else vc["provider"]
    timing = vc.get("timing", "auto")
    paths = []
    for i, scene in enumerate(story["scenes"]):
        text = scene["narration"]
        p, wp = out / f"voice_{i:02d}.mp3", out / f"voice_{i:02d}.words.json"
        paths.append(p)
        if p.exists() and wp.exists():
            continue  # cache

        words = None
        if provider == "edge":
            words = asyncio.run(_edge_async(text, p, vc["edge_voice"], vc.get("rate", "+0%")))
        elif provider == "elevenlabs":
            _elevenlabs(text, p)
            if costs:
                costs.add("elevenlabs_per_1k_chars", len(text) / 1000, f"cảnh {i + 1}")
        else:
            _mock(text, p)

        if not words and timing in ("auto", "whisper_api") and provider != "mock":
            try:
                words = _whisper_words(text, p)
                if costs:
                    costs.add("whisper_per_minute", duration(p) / 60, f"cảnh {i + 1}")
            except Exception as e:  # thiếu key / lỗi mạng -> ước lượng
                print(f"  ⚠ whisper lỗi ({e}), dùng ước lượng")
        if not words:
            words = estimate_words(text, duration(p))
        wp.write_text(json.dumps(words, ensure_ascii=False))
    print(f"  giọng đọc + mốc từng từ {len(paths)} cảnh ✓")
    return paths
