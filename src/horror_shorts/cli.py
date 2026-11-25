"""
Lệnh:
  python -m horror_shorts.cli make [--mock] [-n 3]   tạo video mới
  python -m horror_shorts.cli list                   xem hàng chờ
  python -m horror_shorts.cli approve <id>           duyệt sau khi đã xem
  python -m horror_shorts.cli upload <id>            upload video đã duyệt
"""
import argparse
import json
from datetime import datetime
from . import db
from .config import load_config, OUTPUT
from .story import generate_story
from .images import generate_images
from .voice import generate_voice
from .assemble import assemble
from .upload import upload


def make_one(cfg, mock: bool) -> str:
    vid = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUTPUT / vid
    out.mkdir(parents=True, exist_ok=True)

    print(f"[{vid}] 1/4 viết kịch bản...")
    story = generate_story(cfg, [r[2] for r in db.all_videos()], mock)
    (out / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  «{story['title']}»")

    print("2/4 tạo ảnh...")
    images = generate_images(cfg, story, out, mock)
    print("3/4 giọng đọc...")
    voices = generate_voice(cfg, story, out, mock)
    print("4/4 dựng video...")
    final = assemble(cfg, story, images, voices, out)

    db.add(vid, story["title"], str(final))
    print(f"✅ Xong: {final}\n   Xem lại rồi chạy: approve {vid}")
    return vid


def main():
    ap = argparse.ArgumentParser(prog="horror_shorts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("--mock", action="store_true"); m.add_argument("-n", type=int, default=1)
    sub.add_parser("list")
    sub.add_parser("approve").add_argument("id")
    sub.add_parser("upload").add_argument("id")
    a = ap.parse_args()
    cfg = load_config()

    if a.cmd == "make":
        for _ in range(a.n):
            make_one(cfg, a.mock)
    elif a.cmd == "list":
        for vid, status, title, yid in db.all_videos():
            print(f"{vid}  [{status:8}]  {title}" + (f"  https://youtu.be/{yid}" if yid else ""))
    elif a.cmd == "approve":
        if not db.get(a.id):
            raise SystemExit("Không tìm thấy id")
        db.set_status(a.id, "approved"); print("Đã duyệt ✓")
    elif a.cmd == "upload":
        row = db.get(a.id)
        if not row or row[2] != "approved":
            raise SystemExit("Chỉ upload được video đã approve (bạn phải tự xem lại trước).")
        yid = upload(cfg, OUTPUT / a.id)
        db.set_status(a.id, "uploaded", yid)
        print(f"Đã upload (private): https://youtu.be/{yid}\nNhớ vào YouTube Studio kiểm tra rồi mới công khai.")


if __name__ == "__main__":
    main()
