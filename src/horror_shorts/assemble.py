"""Bước 4: ghép ảnh + giọng đọc + phụ đề + nhạc thành video 9:16."""
import random
from pathlib import Path
from .utils import run, duration
from .config import ROOT

PAD = 0.45  # khoảng lặng sau mỗi cảnh, giúp nhịp kể chuyện "thở"

MOTIONS = {
    "zoom_in":   ("1+0.18*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "zoom_out":  ("1.18-0.18*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pan_left":  ("1.15", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
    "pan_right": ("1.15", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
}


def _scene_clip(img: Path, voice: Path, motion: str, out: Path, w: int, h: int, fps: int) -> float:
    dur = duration(voice) + PAD
    n = int(dur * fps)
    z, x, y = (e.format(n=n) for e in MOTIONS.get(motion, MOTIONS["zoom_in"]))
    vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={fps},"
          f"eq=saturation=0.75:contrast=1.08:brightness=-0.03,vignette=PI/4,"
          f"noise=alls=8:allf=t,fade=t=in:st=0:d=0.35,fade=t=out:st={dur-0.35:.2f}:d=0.35,format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", str(voice),
         "-vf", vf, "-af", f"apad=whole_dur={dur:.2f}", "-t", f"{dur:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(fps),
         "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)])
    return dur


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"


def _write_srt(story: dict, durs: list[float], path: Path):
    """Chia lời dẫn thành cụm ~5 từ, chia thời gian theo độ dài ký tự."""
    lines, idx, t0 = [], 1, 0.0
    for scene, d in zip(story["scenes"], durs):
        words = scene["narration"].split()
        chunks = [" ".join(words[i:i + 5]) for i in range(0, len(words), 5)]
        speak = d - PAD
        total = sum(len(c) for c in chunks) or 1
        t = t0
        for c in chunks:
            seg = speak * len(c) / total
            lines.append(f"{idx}\n{_srt_time(t)} --> {_srt_time(t + seg)}\n{c}\n")
            idx, t = idx + 1, t + seg
        t0 += d
    path.write_text("\n".join(lines), encoding="utf-8")


def assemble(cfg: dict, story: dict, images: list[Path], voices: list[Path], out: Path) -> Path:
    vc, ac = cfg["video"], cfg["audio"]
    w, h, fps = vc["width"], vc["height"], vc["fps"]

    clips, durs = [], []
    for i, (img, voice) in enumerate(zip(images, voices)):
        clip = out / f"clip_{i:02d}.mp4"
        durs.append(_scene_clip(img, voice, story["scenes"][i].get("motion", "zoom_in"), clip, w, h, fps))
        clips.append(clip)
        print(f"  dựng cảnh {i + 1}/{len(images)} ✓")

    (out / "concat.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "joined.mp4"], cwd=out)
    _write_srt(story, durs, out / "subs.srt")
    total = sum(durs)

    music = [p for p in (ROOT / ac["music_dir"]).glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    if music:
        bg = ["-stream_loop", "-1", "-i", str(random.choice(music).resolve())]
        vol = ac["music_volume"]
    else:  # tiếng ù nền u ám tự sinh, không lo bản quyền
        bg = ["-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.6,lowpass=f=180,tremolo=f=0.2:d=0.6"]
        vol = 0.35 if ac.get("ambience", True) else 0.0

    style = ("Fontname=DejaVu Sans,Fontsize=13,Bold=1,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=70")
    final = out / "final.mp4"
    run(["ffmpeg", "-y", "-i", "joined.mp4", *bg,
         "-filter_complex",
         f"[0:v]subtitles=subs.srt:force_style='{style}'[v];"
         f"[1:a]volume={vol}[bg];[0:a][bg]amix=inputs=2:duration=first:normalize=0,"
         f"afade=t=out:st={max(total-1.2,0):.2f}:d=1.2[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "final.mp4"], cwd=out)
    print(f"  video hoàn chỉnh: {total:.1f}s ✓")
    if total > 60:
        print("  ⚠ dài hơn 60s — giảm target_seconds trong config.yaml")
    return final
