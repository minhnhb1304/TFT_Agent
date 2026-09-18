# Augment Reroll Rescan

Hạng mục A — mốc **M2** của [playtest fixes](overview.md). Bước 1–2 thuộc **M0** ([eval-dataset.md](eval-dataset.md)); bước 3–9 nằm trong lõi `src/live/screen_tracker.py` và `card_reader.py`. Sửa lỗi **quét sót lõi sau khi reroll**.
Buổi test chạy bằng `run_replay.py` (commit `d537eb0`) — script này dùng OCR + fuzzy riêng
(`DynamicCardRecognizer`), **không** đi qua `AugmentReader`/Gemini/aHash.

## Nguyên nhân (đã kiểm trong `run_replay.py`)

| # | Nguyên nhân | Chỗ trong code | Mức |
|---|---|---|---|
| 1 | **Không có gì tự đọc lại sau reroll.** Chỉ phân tích khi bấm mốc (frame **đầu tiên** của cụm, tức trước mọi lần reroll) hoặc bấm quét tay. Khi phát video, `_next_frame` không gọi `analyze_current_frame`; `_last_analyzed_second` khai báo nhưng không dùng | `_on_scan_finished`, `_next_frame` | **Gốc** |
| 2 | Quét mốc 4 s/lần rồi lấy hit đầu cụm → có thể rơi vào lúc thẻ **đang hiện ra** → OCR đọc thiếu | `VideoScannerThread.run` | Cao |
| 3 | Chỉ lấy `texts[0]` làm tên: tên dài xuống 2 dòng hoặc OCR trả dòng khác trước → khớp sai/không khớp | `recognize_cards` | Cao |
| 4 | `cutoff=0.45` quá lỏng → **khớp nhầm im lặng** sang lõi khác, nhìn như "sót" | `recognize_cards` | Cao |
| 5 | Ô không khớp bị **bỏ khỏi `choices`** → xếp hạng 2 thẻ mà không báo ô thiếu | `analyze_current_frame` | Trung bình |
| 6 | `lookup` theo tên hiển thị → cặp lõi trùng tên bị **ghi đè**, chọn bừa 1 — trái nguyên tắc "không đoán cặp mơ hồ" | `DynamicCardRecognizer.__init__` | Trung bình |
| 7 | Nút `pressed`/`unknown` lúc animation bị tính là **đã dùng** reroll | `avail = state == "active"` | Thấp |

## Kế hoạch

| # | Bước | Kiểm chứng |
|---|---|---|
| 1 | Gắn nhãn tay mọi màn chọn lõi + mọi lần reroll trong bản record (thời điểm, ô, lõi trước/sau) → `data/eval/playtest/<record_id>.json` (trường `offers`) | Đủ số lần reroll của game |
| 2 | Script headless đo **tỉ lệ đọc đúng** từng thẻ trên các mốc nhãn, `scripts/eval_playtest.py` trên code hiện tại | Baseline cho lỗi 3, 4, 6 |
| 3 | **Theo dõi liên tục trong màn chọn lõi**: khi `screen_present`, lấy mẫu ~5 Hz; nút ô *i* chuyển `active → pressed/disabled` → đánh dấu ô *i* cần đọc lại | Test chuỗi khung giả lập |
| 4 | **Chờ ổn định**: đọc lại ô *i* chỉ khi crop của ô giống nhau ≥ 3 khung liên tiếp (hash riêng từng ô) | Không đọc khung đang lật |
| 5 | Mốc tự động nhảy tới **khung ổn định đầu tiên**, không phải hit thô | Mốc trên record đọc đủ 3 thẻ |
| 6 | Ghép **mọi dòng OCR** của thẻ làm tên, thử 1 và 2 dòng đầu; nâng cutoff (đo từ bước 2) | Tỉ lệ đúng bước 2 tăng, không khớp nhầm |
| 7 | Dùng `NameIndex`/`AugmentCatalog` sẵn có thay `lookup` tự dựng → cặp mơ hồ trả **cả hai** | Test cặp trùng tên |
| 8 | Ô không khớp vẫn hiện trên panel: "Ô 2: chưa đọc được (OCR: …)" | Không còn xếp hạng thiếu thẻ im lặng |
| 9 | Lõi bị reroll mất → `RerollState.burned` | Chính sách reroll loại lõi đã thấy |
| 10 | Chạy lại bước 2 + đếm reroll bắt được / tổng | Bắt đủ mọi reroll trên record |

## Số đo tín hiệu

### Trên VOD `s7h-jHMpFmQ`

| Tình huống | Lệch thumbnail 48×12 (0–255) |
|---|---|
| Thẻ đứng yên | ≤ 0.6 |
| Đổi chữ khi reroll | 6–12 |
| Thẻ đang lật / hiện ra | 20–90 |

→ Ngưỡng "đổi thẻ" và "đã yên" phải **tách riêng**; một ngưỡng 12 bỏ sót 2/3 lần reroll.
Nút reroll là tín hiệu chính xác hơn nội dung thẻ — bài học trực tiếp cho M2.

### Trên record người chơi (2026-09-16, 2 game)

| Quan sát | Hệ quả cho M2 |
|---|---|
| Người chơi **ẩn màn chọn lõi ~10 s** rồi mở lại (cả 2 game) | `grace_s = 1 s` là quá ngắn — giữ trạng thái màn tới ~30 s |
| Thẻ lật xong **chậm hơn** VOD streamer | Sau khi nút chuyển `pressed`, phải chờ nội dung ô đó đổi rồi mới đọc |
| Mỗi game 3 vòng lõi, tổng 12 lần reroll | Đủ dữ liệu để đo `reroll_recall` |

## Lưu ý

- Ngưỡng hash và cutoff **phải đo**, không đặt tay (giống cách đã làm cho nút reroll).
- Bước 3–5 nên nằm trong module thuần (không Qt) để dùng chung cho live mode
  (`LiveSession` trong [live mode phase 2](../live-mode/phase-2-session.md)).
- Nghi vấn aHash 8×8 trong `AugmentReader` vẫn đúng cho đường Gemini — sửa khi live mode dùng nó.

## Related

- [Overview](overview.md)
- [Reroll buttons](../vision/reroll-buttons.md)
- [Augment reader](../vision/augment-reader.md)
