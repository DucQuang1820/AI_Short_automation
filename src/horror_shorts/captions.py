"""Phụ đề karaoke (.ass): hiện từng cụm vài từ, tô màu đúng từ đang được đọc."""
import json
from pathlib import Path


def _t(sec: float) -> str:
    cs = int(round(max(sec, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _clean(w: str) -> str:
    return w.replace("{", "(").replace("}", ")").replace("\\", "")


def write_ass(cfg: dict, voice_paths: list[Path], offsets: list[float], path: Path):
    cc, vc = cfg["captions"], cfg["video"]
    n, hi, base = cc.get("words_per_group", 3), cc["highlight"], cc["color"]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {vc['width']}
PlayResY: {vc['height']}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{cc['font']},{cc['size']},{base},{base},&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,6,2,2,80,80,{cc['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for vp, off in zip(voice_paths, offsets):
        words = json.loads(vp.with_suffix(".words.json").read_text(encoding="utf-8"))
        for g in range(0, len(words), n):
            group = words[g:g + n]
            for k, cur in enumerate(group):
                # giữ chữ tới khi từ kế tiếp bắt đầu: không nhấp nháy, không chồng 2 dòng
                nxt = g + k + 1
                end = words[nxt]["s"] if nxt < len(words) else cur["e"] + 0.15
                end = max(end, cur["s"] + 0.05)
                text = " ".join(
                    (f"{{\\c{hi}\\fscx108\\fscy108}}{_clean(w['w'])}{{\\c{base}\\fscx100\\fscy100}}"
                     if j == k else _clean(w["w"])) for j, w in enumerate(group))
                events.append(f"Dialogue: 0,{_t(off + cur['s'])},{_t(off + end)},Main,,0,0,0,,{text}")
    path.write_text(head + "\n".join(events) + "\n", encoding="utf-8")
