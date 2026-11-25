"""Bước 1: AI viết kịch bản kinh dị + danh sách cảnh + metadata YouTube."""
import json
import os
import re
from difflib import SequenceMatcher

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


def _words_per_sec(cfg: dict) -> float:
    return 2.6 if cfg["channel"]["language"] == "vi" else 2.4


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def validate_story(story: dict, cfg: dict, past_titles: list[str]) -> list[str]:
    """Cổng kiểm tra: trả về danh sách lỗi (rỗng = đạt)."""
    sc, errors = cfg["story"], []
    scenes = story.get("scenes") or []
    if len(scenes) != sc["scenes"]:
        errors.append(f"cần đúng {sc['scenes']} cảnh, đang có {len(scenes)}")
    for i, scene in enumerate(scenes):
        if not scene.get("narration", "").strip() or not scene.get("image_prompt", "").strip():
            errors.append(f"cảnh {i + 1} thiếu narration hoặc image_prompt")
    if errors:
        return errors

    words = sum(len(x["narration"].split()) for x in scenes)
    est = words / _words_per_sec(cfg) + 0.45 * len(scenes)
    if est > sc["target_seconds"] + 2:
        errors.append(f"lời dẫn quá dài (~{est:.0f}s), cần cắt còn dưới {sc['target_seconds']}s")
    if est < sc["target_seconds"] * 0.6:
        errors.append(f"lời dẫn quá ngắn (~{est:.0f}s), cần viết thêm")

    hook = re.split(r"(?<=[.!?…])\s", scenes[0]["narration"].strip())[0]
    if len(hook.split()) > sc.get("max_hook_words", 16):
        errors.append(f"câu hook {len(hook.split())} từ, phải ngắn hơn {sc.get('max_hook_words', 16)} từ")

    for i in range(len(scenes)):
        for j in range(i + 1, len(scenes)):
            if _similar(scenes[i]["narration"], scenes[j]["narration"]) > 0.8:
                errors.append(f"cảnh {i + 1} và {j + 1} gần như trùng nhau")

    title = story.get("title", "")
    for old in past_titles:
        if _similar(title, old) >= sc.get("title_similarity", 0.75):
            errors.append(f"tiêu đề quá giống video cũ «{old}», cần ý tưởng khác")
            break
    if len(story.get("youtube", {}).get("title", "")) > 100:
        errors.append("youtube.title vượt 100 ký tự")
    return errors


def generate_story(cfg: dict, past_titles: list[str], mock: bool = False, costs=None) -> dict:
    sc = cfg["story"]
    if mock or sc["provider"] == "mock":
        errs = validate_story(MOCK, cfg, [])
        if errs:
            print("  ⚠ mock story:", errs)
        return MOCK

    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = PROMPT.format(
        niche=cfg["channel"]["niche"], style=cfg["channel"]["style"],
        language=cfg["channel"]["language"], seconds=sc["target_seconds"],
        scenes=sc["scenes"], words=int(sc["target_seconds"] * _words_per_sec(cfg) * 0.9),
        avoid=", ".join(past_titles[-30:]) or "(chưa có)")
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(1, sc.get("max_retries", 3) + 1):
        msg = client.messages.create(model=sc["model"], max_tokens=4000, messages=messages)
        if costs:
            costs.add("story", note=f"lần {attempt}")
        raw = msg.content[0].text
        try:
            story = _parse_json(raw)
            errors = validate_story(story, cfg, past_titles)
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            errors = [f"JSON không hợp lệ: {e}"]
        if not errors:
            return story
        print(f"  ✗ kịch bản lần {attempt} chưa đạt: {'; '.join(errors)}")
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": "Sửa các lỗi sau và trả lại toàn bộ JSON:\n- "
                                                 + "\n- ".join(errors)}]
    raise RuntimeError("Kịch bản không qua kiểm tra sau nhiều lần thử")
