"""Bước 4: ghép ảnh + giọng đọc + phụ đề + nhạc thành video 9:16."""
import random
from pathlib import Path
from .utils import run, duration
from .config import ROOT
from .captions import write_ass

PAD = 0.45  # khoảng lặng sau mỗi cảnh, giúp nhịp kể chuyện "thở"

MOTIONS = {
    "zoom_in":   ("1+0.18*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "zoom_out":  ("1.18-0.18*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pan_left":  ("1.15", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
    "pan_right": ("1.15", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
}


def _grade(dur: float) -> str:
    """Tông màu kinh dị dùng chung: giảm bão hòa, vignette, film grain, fade."""
    return (f"eq=saturation=0.75:contrast=1.08:brightness=-0.03,vignette=PI/4,"
            f"noise=alls=8:allf=t,fade=t=in:st=0:d=0.35,fade=t=out:st={dur-0.35:.2f}:d=0.35,format=yuv420p")


def _encode(inputs: list[str], vf: str, voice: Path, dur: float, fps: int, out: Path):
    run(["ffmpeg", "-y", *inputs, "-i", str(voice),
         "-map", "0:v", "-map", "1:a", "-vf", vf, "-af", f"apad=whole_dur={dur:.2f}", "-t", f"{dur:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(fps),
         "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)])


def _kenburns_clip(img: Path, voice: Path, motion: str, out: Path, w: int, h: int, fps: int, dur: float):
    n = int(dur * fps)
    z, x, y = (e.format(n=n) for e in MOTIONS.get(motion, MOTIONS["zoom_in"]))
    vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={fps}," + _grade(dur))
    _encode(["-loop", "1", "-i", str(img)], vf, voice, dur, fps, out)


def _veo_clip(src: Path, voice: Path, out: Path, w: int, h: int, fps: int, dur: float):
    """Bỏ tiếng gốc của Veo, lặp/cắt cho khớp giọng đọc, cùng tông màu với các cảnh khác."""
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}," + _grade(dur)
    _encode(["-stream_loop", "-1", "-i", str(src)], vf, voice, dur, fps, out)


def assemble(cfg: dict, story: dict, images: list[Path], voices: list[Path], out: Path,
             veo_clips: dict[int, Path] | None = None) -> Path:
    vc, ac = cfg["video"], cfg["audio"]
    w, h, fps = vc["width"], vc["height"], vc["fps"]
    veo_clips = veo_clips or {}

    clips, durs = [], []
    for i, (img, voice) in enumerate(zip(images, voices)):
        dur = duration(voice) + PAD
        kind = "veo" if i in veo_clips else "kb"
        clip = out / f"clip_{i:02d}_{kind}.mp4"
        if not clip.exists():
            if kind == "veo":
                _veo_clip(veo_clips[i], voice, clip, w, h, fps, dur)
            else:
                _kenburns_clip(img, voice, story["scenes"][i].get("motion", "zoom_in"), clip, w, h, fps, dur)
        durs.append(dur)
        clips.append(clip)
        print(f"  dựng cảnh {i + 1}/{len(images)} ({'Veo' if kind == 'veo' else 'Ken Burns'}) ✓")

    (out / "concat.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "joined.mp4"], cwd=out)
    offsets = [sum(durs[:i]) for i in range(len(durs))]
    write_ass(cfg, voices, offsets, out / "subs.ass")
    total = sum(durs)

    music = [p for p in (ROOT / ac["music_dir"]).glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    if music:
        bg = ["-stream_loop", "-1", "-i", str(random.choice(music).resolve())]
        vol = ac["music_volume"]
    else:  # tiếng ù nền u ám tự sinh, không lo bản quyền
        bg = ["-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.6,lowpass=f=180,tremolo=f=0.2:d=0.6"]
        vol = 0.35 if ac.get("ambience", True) else 0.0

    lufs = ac.get("loudness_lufs", -14)
    final = out / "final.mp4"
    run(["ffmpeg", "-y", "-i", "joined.mp4", *bg,
         "-filter_complex",
         "[0:v]ass=subs.ass[v];"
         f"[1:a]volume={vol}[bg];[0:a][bg]amix=inputs=2:duration=first:normalize=0,"
         f"afade=t=out:st={max(total-1.2,0):.2f}:d=1.2,"
         f"loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=44100[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "final.mp4"], cwd=out)
    print(f"  video hoàn chỉnh: {total:.1f}s ✓")
    if total > 60:
        print("  ⚠ dài hơn 60s — giảm target_seconds trong config.yaml")
    return final
