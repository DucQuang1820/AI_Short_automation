# 👻 AI Horror Shorts

Pipeline tạo **phim kinh dị AI 60 giây** cho YouTube Shorts, 100% bằng AI:
kịch bản → ảnh → giọng đọc → dựng video → bạn duyệt → upload.

```
Claude (kịch bản + cảnh + metadata)  ──► cổng kiểm tra, tự viết lại tối đa 3 lần
   → OpenAI gpt-image-1 (ảnh từng cảnh)
   → Veo image-to-video cho cảnh hook & twist (tùy chọn)
   → Edge TTS / ElevenLabs (giọng đọc + mốc thời gian từng từ)
   → ffmpeg (Ken Burns, film grain, vignette, phụ đề karaoke, nhạc nền, chuẩn -14 LUFS)
   → hàng chờ duyệt  →  YouTube Data API (upload private)
```

Mỗi bước đều cache: ảnh, clip Veo, giọng đọc đã tạo sẽ không tạo lại khi chạy tiếp,
nên lỗi giữa chừng không mất tiền. Chi phí ước tính của từng video ghi trong `costs.json`.

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
python -m horror_shorts.cli make --resume <id>   # chạy tiếp video lỗi giữa chừng
python -m horror_shorts.cli list            # xem hàng chờ
python -m horror_shorts.cli approve <id>    # sau khi TỰ XEM output/<id>/final.mp4
python -m horror_shorts.cli upload <id>
```

Mỗi video nằm trong `output/<id>/`: `story.json`, ảnh, giọng, `subs.ass`, `costs.json`, `final.mp4`.

**Sửa tay rồi dựng lại:** sửa `story.json`, xóa các file của cảnh đã đổi
(`scene_XX.png`, `voice_XX.*`, `clip_XX_*.mp4`) và `final.mp4`, rồi chạy `make --resume <id>`.

## Các tính năng

| Tính năng | Cấu hình | Ghi chú |
|---|---|---|
| Cổng kiểm tra kịch bản | `story.max_hook_words`, `max_retries`, `title_similarity` | Kiểm tra độ dài, hook, cảnh trùng, tiêu đề giống video cũ |
| Veo cho cảnh hook/twist | `video.veo` | Mặc định tắt. Lỗi ở cảnh nào thì cảnh đó tự quay về Ken Burns |
| Phụ đề karaoke | `captions` | Edge TTS cho sẵn mốc từng từ; ElevenLabs dùng Whisper API; không có thì ước lượng |
| Chuẩn âm lượng | `audio.loudness_lufs` | -14 LUFS như khuyến nghị của YouTube |
| Theo dõi chi phí | `costs` | Đơn giá là ước tính, hãy cập nhật theo bảng giá thật |

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

- **Vòng phản hồi Analytics**: lấy video chạy tốt nhất 30 ngày qua để định hướng ý tưởng (nên làm khi kênh có ~20–30 video).
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

## Tham khảo

Một số ý tưởng (cổng kiểm tra kịch bản, chuẩn hóa âm lượng, Veo cho từng cảnh, phụ đề theo từng từ)
được tham khảo từ shortube (MIT), youtube-shorts-agent, yt-shorts-ai và youtube-shorts-automation.
Mã nguồn ở đây được viết lại, không sao chép.
