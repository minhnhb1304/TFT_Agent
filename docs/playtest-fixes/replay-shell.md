# Replay Shell

Mốc **M1** (phần vỏ) của [playtest fixes](overview.md). Biến `run_replay.py` (819 dòng) thành
**vỏ mỏng** trên [core-session.md](core-session.md), đồng thời thành công cụ gắn nhãn.

## Hiện trạng cần bỏ

| Trong `run_replay.py` | Thay bằng |
|---|---|
| `DynamicCardRecognizer` | `OcrCardReader` trong lõi |
| `VideoScannerThread` (quét 4 s, gom cụm 25 s) | Worker chạy `LiveSession.step` nhanh trên video → danh sách `ScreenOpened` |
| `analyze_current_frame` tự đọc HUD/nút/thẻ, tự dựng `GameState` | Hiển thị `AdviceReady` |
| `st.gold or 0`, `level or 1`, `hp or 100` | `state` từ lõi + `stale_fields` |
| Phát video không phân tích | Worker phân tích theo vị trí phát |
| `bundle.economy`, `bundle.comp` bị bỏ | Hiện trên panel |

## Bố cục mới

| File | Nội dung | Giới hạn |
|---|---|---|
| `run_replay.py` | Entry point, parse CLI, gọi `ReplayWindow` | < 60 dòng |
| `src/replay/window.py` | `ReplayWindow`: video, slider, nút mốc, panel | < 400 dòng |
| `src/replay/worker.py` | `ReplayWorker(QThread)`: đọc khung theo vị trí phát → `session.step` → signal | < 150 dòng |
| `src/replay/scan.py` | Quét nhanh cả video bằng lõi (bước 0.5 s quanh vùng nghi vấn) | Không Qt |
| `src/replay/labeler.py` | Form gắn nhãn → `data/eval/playtest/*.json` | Sau pilot M0 |

`src/replay/` được import Qt; `src/live/` thì không.

## Hành vi

| Hành động | Kết quả |
|---|---|
| Mở video | Quét nền → nút mốc tại **khung ổn định đầu tiên** mỗi màn |
| Phát | Worker gọi `step` ~5 Hz theo thời gian video; panel tự cập nhật khi reroll |
| Tua tới | `session.seek(t)`; tracker giữ HUD đã đọc |
| Tua lùi / bấm mốc cũ | `seek(t)` → `new_game()` rồi **chạy lại nhanh** 20 s trước mốc để lấy HUD |
| Bấm "Quét lại" | `session.force_refresh()` |
| Dòng trạng thái | `Stage · Lv (xp/need) · vàng (+lãi) · HP · chuỗi` — trường cũ/thiếu tô xám + "?" |
| Ô không đọc được | Hàng riêng trên panel: "Ô 2: chưa đọc được (OCR: …)" |
| Bấm "Gắn nhãn" | Mở form điền sẵn từ `AdviceReady`, người chơi sửa rồi lưu |

## CLI

```
python run_replay.py [video] [--card-reader ocr|gemini] [--speed 1.0] [--start 600]
python run_replay.py --headless video.mp4 --out data/eval/runs/<ts>.jsonl   # cho eval_playtest
```

`--headless` chạy cùng lõi không mở cửa sổ — nền của `scripts/eval_playtest.py` và của so
sánh replay/live (G5).

## Việc

| # | Việc | Kiểm chứng |
|---|---|---|
| 1 | Tách `window.py`, `worker.py` từ `run_replay.py`, chưa đổi logic | App mở, phát được như cũ |
| 2 | Thay phân tích bằng `LiveSession` qua worker | Trên record: panel tự đổi khi reroll |
| 3 | Thay scanner bằng `scan.py` | Số mốc = số màn trong nhãn M0 |
| 4 | `--headless` + JSONL output | `eval_playtest.py` đọc được |
| 5 | Dòng trạng thái, hàng ô lỗi, `economy`/`comp` | Test `QT_QPA_PLATFORM=offscreen` |
| 6 | `labeler.py` | Gắn nhãn 1 game < 20 phút |

## Rủi ro riêng

- `cv2.VideoCapture.set(POS_FRAMES)` chậm và không chính xác keyframe trên MP4 → worker đọc
  **tuần tự** khi phát, chỉ `set` khi tua; kiểm lệch khung trên record.
- Người chơi đang sửa `run_replay.py` trên máy test → **hỏi trước** khi bước 1 đụng file.

## Related

- [Core session](core-session.md)
- [Eval dataset](eval-dataset.md)
- [Live track](live-track.md)
