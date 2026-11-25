"""Bước 3: AI đọc lời dẫn cho từng cảnh."""
import asyncio
import os
from pathlib import Path
import requests
from .utils import run


def _edge(text: str, path: Path, voice: str, rate: str):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(path)))


def _elevenlabs(text: str, path: Path):
    vid = os.environ["ELEVENLABS_VOICE_ID"]
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                      json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)


def _mock(text: str, path: Path):
    secs = max(2.5, len(text.split()) / 2.6)  # ước lượng thời lượng đọc
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{secs:.2f}", "-q:a", "9", str(path)])


def generate_voice(cfg: dict, story: dict, out: Path, mock: bool = False) -> list[Path]:
    vc = cfg["voice"]
    provider = "mock" if mock else vc["provider"]
    paths = []
    for i, scene in enumerate(story["scenes"]):
        p = out / f"voice_{i:02d}.mp3"
        if provider == "edge":
            _edge(scene["narration"], p, vc["edge_voice"], vc.get("rate", "+0%"))
        elif provider == "elevenlabs":
            _elevenlabs(scene["narration"], p)
        else:
            _mock(scene["narration"], p)
        paths.append(p)
    print(f"  giọng đọc {len(paths)} cảnh ✓")
    return paths
