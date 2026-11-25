# 👻 AI Horror Shorts

Pipeline tạo **phim kinh dị AI 60 giây** cho YouTube Shorts, 100% bằng AI:
kịch bản → ảnh → giọng đọc → dựng video → bạn duyệt → upload.

```
Claude (kịch bản + cảnh + metadata)
   → OpenAI gpt-image-1 (ảnh từng cảnh)
   → Edge TTS / ElevenLabs (giọng đọc)
   → ffmpeg (chuyển động Ken Burns, film grain, vignette, phụ đề, nhạc nền)
   → hàng chờ duyệt  →  YouTube Data API (upload private)
```

## Cài đặt

Cần Python 3.10+ và **ffmpeg** (`brew install ffmpeg` / `sudo apt install ffmpeg` / `winget install ffmpeg`).

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # rồi điền API key
```

## Chạy

```bash
cd src
python -m horror_shorts.cli make --mock     # chạy thử không tốn tiền, không cần key
python -m horror_shorts.cli make            # tạo 1 video thật
python -m horror_shorts.cli make -n 3       # tạo 3 video
python -m horror_shorts.cli list            # xem hàng chờ
python -m horror_shorts.cli approve <id>    # sau khi TỰ XEM output/<id>/final.mp4
python -m horror_shorts.cli upload <id>
```

Mỗi video nằm trong `output/<id>/`: `story.json` (kịch bản, sửa tay được), ảnh, giọng, `final.mp4`.

## Kết nối YouTube

1. Vào Google Cloud Console → tạo project → bật **YouTube Data API v3**.
2. Tạo **OAuth client ID** loại *Desktop app* → tải về, đổi tên thành `client_secret.json`, đặt ở thư mục gốc.
3. Lần upload đầu sẽ mở trình duyệt để đăng nhập kênh; token lưu vào `token.json`.

> Project API chưa qua audit của Google thì video upload sẽ bị khóa ở chế độ private.
> Pipeline vốn upload private, bạn vào YouTube Studio xem lại rồi tự công khai.

## Chi phí ước tính cho 1 video (6 cảnh)

| Bước | Provider | Ghi chú |
|---|---|---|
| Kịch bản | Claude | rất rẻ, vài cent |
| Ảnh | gpt-image-1 | phần tốn nhất, phụ thuộc chất lượng ảnh |
| Giọng | Edge TTS | miễn phí; ElevenLabs hay hơn nhưng trả phí |
| Dựng | ffmpeg | miễn phí, chạy trên máy |

Kiểm tra bảng giá hiện tại của từng nhà cung cấp trước khi chạy hàng loạt.

## Nâng cấp tiếp theo

- **Video AI thật** thay cho ảnh + Ken Burns: thêm provider trong `assemble.py`/module mới gọi Veo, Runway, Kling hoặc Luma (image-to-video từ chính ảnh đã tạo).
- **Nhạc nền**: bỏ file có license (YouTube Audio Library) vào `assets/music/`. Không có thì pipeline tự sinh tiếng ù nền.
- **Hiệu ứng âm thanh** (tiếng gõ cửa, bước chân) theo từng cảnh.
- **Series cố định**: một nhân vật kể chuyện xuyên suốt kênh để tạo dấu ấn riêng.
- **Thumbnail / ảnh bìa** cho video dài tổng hợp.
- **Lịch chạy tự động** (cron / GitHub Actions) cho bước `make` — bước `approve` vẫn để người làm.

## Nguyên tắc để kênh kiếm tiền được

- Luôn xem lại trước khi đăng; sửa `story.json` nếu kịch bản nhạt hoặc lặp.
- Không đăng hàng loạt nội dung na ná nhau: YouTube coi đó là *inauthentic content* và từ chối kiếm tiền.
- Giữ `contains_synthetic_media: true` (nhãn nội dung AI theo yêu cầu của YouTube).
- Kịch bản được dặn tránh máu me chi tiết để giữ quảng cáo.
