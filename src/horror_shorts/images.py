"""Bước 2: AI tạo ảnh cho từng cảnh."""
import base64
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def _mock_image(path: Path, text: str, i: int):
    img = Image.new("RGB", (1024, 1536), (12 + i * 6, 10, 14))
    d = ImageDraw.Draw(img)
    for r in range(600, 0, -40):  # vệt sáng mờ cho có không khí
        c = 30 + (600 - r) // 12
        d.ellipse([512 - r, 700 - r, 512 + r, 700 + r], fill=(c, c // 2, c // 2))
    img = img.filter(ImageFilter.GaussianBlur(25))
    ImageDraw.Draw(img).text((60, 1400), f"SCENE {i + 1}: {text[:50]}", fill=(200, 200, 200))
    img.save(path)


def generate_images(cfg: dict, story: dict, out: Path, mock: bool = False) -> list[Path]:
    ic = cfg["image"]
    style = cfg["channel"]["style"]
    paths = []
    client = None
    if not (mock or ic["provider"] == "mock"):
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    for i, scene in enumerate(story["scenes"]):
        p = out / f"scene_{i:02d}.png"
        if client is None:
            _mock_image(p, scene["image_prompt"], i)
        else:
            prompt = f"{scene['image_prompt']}. Style: {style}. Vertical 9:16 frame, no text, no watermark."
            res = client.images.generate(model=ic["model"], prompt=prompt, size=ic["size"])
            p.write_bytes(base64.b64decode(res.data[0].b64_json))
        paths.append(p)
        print(f"  ảnh {i + 1}/{len(story['scenes'])} ✓")
    return paths
