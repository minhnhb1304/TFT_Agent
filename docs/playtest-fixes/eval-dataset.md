# Eval Dataset

Mốc **M0** của [playtest fixes](overview.md). Biến bản record buổi test thành bộ nhãn cố
định, để mọi mốc sau **đo được** chứ không đánh giá bằng mắt.

## Vì sao làm trước

Không có baseline thì không biết M2 sửa được bao nhiêu, và không bắt được hồi quy khi M3/M4
đổi scorer. Bản record là dữ liệu **đúng tầm rank người chơi** và đúng máy test.

## File nhãn — `data/eval/playtest/<record_id>.json`

```json
{ "video": "...", "video_sha256": "...", "size": [1920, 1080],
  "screens": [{ "stage": "3-2", "status": "verified", "open_s": 626.8, "close_s": 647.0,
    "hud": {"gold": 55, "level": 4, "xp": 8, "xp_needed": 10, "hp": 88, "streak": -1},
    "offers": [{"at_s": 628.3, "cards": [["DA_A"], ["DA_B"], ["DA_C"]], "rerolled_slot": null},
               {"at_s": 636.5, "cards": [["DA_A"], ["DA_B"], ["DA_D"]], "rerolled_slot": 2}],
    "picked": "DA_D", "expert": null }] }
```

- `hud` ghi giá trị **ngay trước khi mở màn** (lúc HUD còn thấy).
- `offers` có một mục cho mỗi trạng thái thẻ ổn định, gồm cả sau mỗi lần reroll.
- `expert` bỏ trống ở M0; điền ở [expert-knowledge.md](expert-knowledge.md). `blind` = gắn
  nhãn khi **chưa** thấy ranking của advisor.
- Video **không** commit (nặng, cá nhân); chỉ commit file nhãn, kèm `video_sha256` để biết
  đúng file khi chấm lại trên máy khác. Đường dẫn video truyền bằng `--video`.

## Công cụ (đã có)

| Việc | File | Ghi chú |
|---|---|---|
| Schema + loader + validate | `src/eval/playtest_labels.py` | `verified` kiểm chặt: đủ 3 ô, `rerolled_slot` = ô thực sự đổi, `picked` ∈ offer cuối |
| Bộ chấm | `src/eval/playtest_metrics.py` | Thẻ "đang hiện" = lần đọc cuối trước khi offer kết thúc |
| Tách offer + gợi ý tên | `src/eval/playtest_draft.py` | Reroll = nút `active → pressed/disabled`; thẻ yên = lệch < 2 |
| Sinh nhãn nháp | `scripts/draft_playtest_labels.py` | Ảnh mỗi offer vào `snapshots/` (gitignore) |
| Xem lại / sửa nhãn | `scripts/review_playtest_labels.py` + `src/eval/playtest_review.py` | Trang 127.0.0.1; còn lỗi thì **không ghi** — xem [labeling-guide.md](labeling-guide.md) |
| Đo | `scripts/eval_playtest.py` | `--mode baseline` (y hệt `run_replay.py` d537eb0) / `dense` (chẩn đoán) |
| Test | `tests/test_playtest_eval.py` | 37 test, số kỳ vọng tính tay |

```powershell
.venv\Scripts\python scripts\draft_playtest_labels.py --video "<record>.mp4"
.venv\Scripts\python scripts\review_playtest_labels.py data\eval\playtest\<id>.json --video "<record>.mp4"
.venv\Scripts\python scripts\eval_playtest.py data\eval\playtest\<id>.json --video "<record>.mp4" --mode baseline
.venv\Scripts\python scripts\eval_playtest.py data\eval\playtest\<id>.json --video "<record>.mp4" --mode dense
```

`baseline` thấp + `dense` cao → lỗi ở **khi nào đọc**; cả hai thấp → lỗi ở **bộ đọc thẻ**.

Số đo tín hiệu dùng để đặt ngưỡng: [augment-reroll-rescan.md](augment-reroll-rescan.md#số-đo-tín-hiệu).

## Chỉ số

| Chỉ số | Định nghĩa | Mốc dùng |
|---|---|---|
| `card_acc` | Thẻ đọc đúng apiName / tổng thẻ trên mọi `offers` | M1, M2 |
| `card_wrong_silent` | Thẻ khớp **sai** mà không báo mơ hồ/thiếu | M2 (đích 0) |
| `reroll_recall` | Lần reroll bắt được / tổng lần reroll | M2 (đích 100%) |
| `read_latency_s` | Từ lúc thẻ ổn định đến lúc có ranking | M2, M5 |
| `hud_acc[field]` | Giá trị HUD mà lõi dùng ở mốc = nhãn | M2 |
| `state_effect` | % màn mà ranking có state ≠ ranking với state trung tính | M3 |
| `dup_reasons` | Số câu lý do trùng giữa các thẻ cùng màn | M4 (đích 0) |
| `top1_agree` | Top-1 advisor = top-1 chuyên gia (chỉ nhãn `blind`) | M4, M6 |
| `replay_live_diff` | Số màn ranking khác giữa vỏ replay và vỏ live | M5 (đích 0) |

## Kết quả

Nhãn: record 2026-09-16, **2 game, 6 màn chọn lõi, 33 ô, 16 lần reroll**, người chơi đã kiểm
từng ảnh (`verified`). Đo ngày 2026-09-18 tại commit `d537eb0`.

| Game | Mode | card_acc | wrong_silent | missing | reroll_recall | latency p95 | gold/level/xp | hp |
|---|---|---|---|---|---|---|---|---|
| 1 | baseline | 0.55 | 15 | 0 | **0/8** | 3.15 s | 0.00 | 0.36 |
| 1 | dense | **1.00** | 0 | 0 | 7/8 | 2.15 s | 1.00 | 0.36 |
| 2 | baseline | 0.18 | 3 | 24 | **0/8** | 0.75 s | 0.00 | 0.27 |
| 2 | dense | **1.00** | 0 | 0 | **8/8** | 0.55 s | 0.64 | 0.64 |

`streak` = 0.00 ở mọi dòng: hiện chưa đọc trường này.

### Đọc được gì từ bảng

1. **Bộ đọc thẻ OCR không phải thủ phạm.** Cùng bộ đọc đó, chỉ đổi *khi nào* đọc, `card_acc`
   nhảy từ 0.18-0.55 lên **1.00** và bắt được 15/16 lần reroll. Lỗi #2 nằm hoàn toàn ở tầng
   kích hoạt - đúng thứ [core-session.md](core-session.md) sẽ thay.
2. **`wrong_silent` mới là kiểu hỏng nguy hiểm**: 18 ô đọc ra một lõi **khác** mà không báo -
   người chơi không có cách nào biết mình đang xem lời khuyên cho thẻ đã bị đổi.
3. **gold/level/xp = 0.00 ở baseline** vì chỉ đọc HUD đúng lúc màn chọn lõi che HUD. Dense
   prime trước 15 s thì lên 1.00 (game 1); game 2 còn 0.64 vì Team Planner làm tối HUD.
4. **hp <= 0.36 ở cả hai chế độ**: lỗi ROI chứ không phải lỗi thời điểm - xem
   [game-state-value.md](game-state-value.md) R1.

## Related

- [Overview](overview.md)
- [Labeling guide](labeling-guide.md)
- [Augment reroll rescan](augment-reroll-rescan.md)
- [Expert knowledge](expert-knowledge.md)
- [Evaluation framing](../expert-prior/evaluation-framing.md)
