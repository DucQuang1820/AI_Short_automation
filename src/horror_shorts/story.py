"""Bước 1: AI viết kịch bản kinh dị + danh sách cảnh + metadata YouTube."""
import json
import os
import re

PROMPT = """Bạn là biên kịch phim kinh dị ngắn cho YouTube Shorts.
Kênh: {niche}
Viết MỘT câu chuyện kinh dị HOÀN TOÀN MỚI, dài khoảng {seconds} giây khi đọc thành tiếng,
chia đúng {scenes} cảnh. Ngôn ngữ lời dẫn: {language}.

Yêu cầu:
- Câu đầu tiên là HOOK cực mạnh (người xem quyết định ở lại trong 2 giây đầu).
- Kể ngôi thứ nhất, câu ngắn, tạo căng thẳng tăng dần.
- Cảnh cuối có cú twist bất ngờ, kết lửng khiến người xem muốn xem lại.
- Không máu me quá mức, không bạo lực chi tiết (an toàn cho quảng cáo).
- Không dựa trên phim/truyện có bản quyền hay người thật.
- Tổng lời dẫn khoảng {words} từ.
- Chủ đề tránh lặp lại các tiêu đề này: {avoid}

Mỗi cảnh có image_prompt TIẾNG ANH mô tả khung hình dọc 9:16, phong cách: {style}.
Giữ nhân vật/bối cảnh nhất quán giữa các cảnh (lặp lại mô tả nhân vật trong mỗi prompt).
motion là một trong: zoom_in, zoom_out, pan_left, pan_right.

Chỉ trả về JSON hợp lệ, không markdown:
{{"title": "...", "logline": "...",
  "scenes": [{{"narration": "...", "image_prompt": "...", "motion": "zoom_in"}}],
  "youtube": {{"title": "tối đa 70 ký tự, có #shorts", "description": "...", "tags": ["..."]}}}}"""

MOCK = {
    "title": "Tiếng gõ cửa lúc 3 giờ sáng",
    "logline": "Mỗi đêm có người gõ cửa, nhưng camera không thấy ai.",
    "scenes": [
        {"narration": "Đêm nào cũng vậy, đúng ba giờ sáng, có người gõ cửa nhà tôi.", "image_prompt": "dark apartment door at night", "motion": "zoom_in"},
        {"narration": "Tôi lắp camera. Màn hình chỉ thấy hành lang trống không.", "image_prompt": "empty hallway security camera view", "motion": "pan_left"},
        {"narration": "Nhưng tiếng gõ vẫn vang lên. Ba tiếng. Chậm rãi.", "image_prompt": "close up of door knob in darkness", "motion": "zoom_in"},
        {"narration": "Đêm qua, tôi quyết định mở cửa.", "image_prompt": "hand reaching for door handle", "motion": "zoom_out"},
        {"narration": "Bên ngoài không có ai. Chỉ có hành lang lạnh ngắt.", "image_prompt": "cold empty corridor flickering light", "motion": "pan_right"},
        {"narration": "Rồi tôi nghe tiếng gõ. Lần này, từ bên trong tủ quần áo.", "image_prompt": "wardrobe door slightly open in dark bedroom", "motion": "zoom_in"},
    ],
    "youtube": {"title": "Tiếng gõ cửa lúc 3 giờ sáng 😨 #shorts",
                "description": "Phim kinh dị ngắn tạo bằng AI.", "tags": ["kinh dị", "phim ngắn AI", "horror shorts"]},
}


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def generate_story(cfg: dict, avoid_titles: list[str], mock: bool = False) -> dict:
    sc = cfg["story"]
    if mock or sc["provider"] == "mock":
        return MOCK

    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    words = int(sc["target_seconds"] * (2.6 if cfg["channel"]["language"] == "vi" else 2.4))
    prompt = PROMPT.format(
        niche=cfg["channel"]["niche"], style=cfg["channel"]["style"],
        language=cfg["channel"]["language"], seconds=sc["target_seconds"],
        scenes=sc["scenes"], words=words, avoid=", ".join(avoid_titles[-30:]) or "(chưa có)")

    for attempt in range(3):
        msg = client.messages.create(model=sc["model"], max_tokens=4000,
                                     messages=[{"role": "user", "content": prompt}])
        try:
            story = _parse_json(msg.content[0].text)
            assert len(story["scenes"]) >= 3
            return story
        except (json.JSONDecodeError, KeyError, AssertionError):
            if attempt == 2:
                raise
    raise RuntimeError("Không tạo được kịch bản")
