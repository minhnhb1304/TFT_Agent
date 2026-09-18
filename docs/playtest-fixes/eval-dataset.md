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

- `hud` ghi giá trị **ngay trước khi mở màn**; `offers` có một mục cho mỗi trạng thái thẻ
  ổn định, gồm cả sau mỗi lần reroll.
- `expert` bỏ trống ở M0; điền ở [expert-knowledge.md](expert-knowledge.md) (`blind` = gắn
  nhãn khi chưa thấy ranking của advisor).
- Video **không** commit (nặng, cá nhân); chỉ commit file nhãn, kèm `video_sha256` để biết
  đúng file khi chấm lại trên máy khác. Đường dẫn video truyền bằng `--video`.

## Công cụ (đã có)

| Việc | File |
|---|---|
| Schema + validate nhãn | `src/eval/playtest_labels.py` |
| Bộ chấm | `src/eval/playtest_metrics.py` |
| Tách offer + gợi ý tên | `src/eval/playtest_draft.py` |
| Sinh nhãn nháp | `scripts/draft_playtest_labels.py` |
.venv\Scripts\python scripts\review_playtest_labels.py data\eval\playtest\<id>.json --video "<record>.mp4"
| Đo tầng đọc | `scripts/eval_playtest.py` (`--mode baseline \| session \| dense`) |
| Đo ảnh hưởng trạng thái | `scripts/state_effect_report.py` (`--ablate` để lấy số trước M3) |

```powershell
.venv\Scripts\python scripts\draft_playtest_labels.py --video "<record>.mp4"
.venv\Scripts\python scripts\review_playtest_labels.py data\eval\playtest\<id>.json --video "<record>.mp4"
.venv\Scripts\python scripts\eval_playtest.py data\eval\playtest\<id>.json --video "<record>.mp4" --mode session
.venv\Scripts\python scripts\state_effect_report.py data\eval\playtest\*.json
```

`baseline` thấp + `dense` cao → lỗi ở **khi nào đọc**; cả hai thấp → lỗi ở **bộ đọc thẻ**.

## Chỉ số

| Chỉ số | Định nghĩa | Mốc dùng |
|---|---|---|
| `card_acc` | Thẻ đọc đúng apiName / tổng thẻ trên mọi `offers` | M1, M2 |
| `card_wrong_silent` | Thẻ khớp **sai** mà không báo mơ hồ/thiếu | M2 (đích 0) |
| `reroll_recall` | Lần reroll bắt được / tổng lần reroll | M2 (đích 100%) |
| `read_latency_s` | Từ lúc thẻ ổn định đến lúc có ranking | M2, M5 |
| `hud_acc[field]` | Giá trị HUD mà lõi dùng ở mốc = nhãn | M2 |
| `state_effect`, `dup_reasons`, `top1_agree`, `replay_live_diff` | dùng ở M3–M5, định nghĩa trong [overview.md](overview.md#mục-tiêu) | M3+ |

## Kết quả

Nhãn: record 2026-09-16, **2 game, 6 màn chọn lõi, 33 ô, 16 lần reroll**, người chơi đã kiểm
từng ảnh (`verified`). Đo ngày 2026-09-18 tại commit `d537eb0`.

| Game | Mode | card_acc | wrong_silent | missing | reroll_recall | latency p95 | gold/level/xp | hp |
|---|---|---|---|---|---|---|---|---|
| 1 | baseline | 0.55 | 15 | 0 | **0/8** | 3.15 s | 0.00 | 0.36 |
| 1 | **session (M1)** | **1.00** | 0 | 0 | **7/8** | 0.50 s | **1.00** | 0.36 |
| 1 | **session (M2)** | **1.00** | 0 | 0 | **7/8** | 0.48 s | **1.00** | **1.00** |
| 1 | dense | 1.00 | 0 | 0 | 7/8 | 2.15 s | 1.00 | 0.36 |
| 2 | baseline | 0.18 | 3 | 24 | **0/8** | 0.75 s | 0.00 | 0.27 |
| 2 | **session (M1)** | **1.00** | 0 | 0 | **6/8** | 2.01 s | 0.36–1.00 | 0.64 |
| 2 | **session (M2)** | **1.00** | 0 | 0 | 5/8 | 0.51 s | 0.36–1.00 | **1.00** |
| 2 | dense | 1.00 | 0 | 0 | 8/8 | 0.55 s | 0.64 | 0.64 |

`streak` = 0.00 ở baseline/dense (chưa đọc trường này); `session` có 0.27–0.36 chỉ vì đoán
đúng khi chuỗi = 0. `session` là lõi `src/live/LiveSession` (mốc M1), chạy 5 khung/giây.

### Đọc được gì từ bảng

1. **Bộ đọc thẻ OCR không phải thủ phạm.** Cùng bộ đọc đó, chỉ đổi *khi nào* đọc thì `card_acc`
   nhảy từ 0.18–0.55 lên **1.00**. Lỗi #2 nằm ở tầng kích hoạt, đã thay ở M1.
2. **`wrong_silent` là kiểu hỏng nguy hiểm nhất**: baseline có 18 ô đọc ra lõi **khác** mà không
   báo gì. Từ M1 trở đi: **0**.
3. **gold/level/xp = 0.00 ở baseline** vì chỉ đọc HUD đúng lúc màn chọn lõi che HUD.
4. **`hp` 0.36 → 1.00 ở M2**: lỗi ROI, không phải lỗi thời điểm.

### M3: trạng thái trận đã đổi được xếp hạng

`python scripts/state_effect_report.py data/eval/playtest/*.json [--ablate]`

| Cấu hình | Offer đổi thứ hạng | Đổi cả lựa chọn đầu |
|---|---|---|
| Trước M3 (`--ablate`: tắt tiền, chuỗi, nhịp cấp) | **0/22** | 0 |
| Sau M3 | **3/22 (14%)** | 3 |

Đây là câu trả lời bằng số cho "đọc tiền/EXP để làm gì": trước M3, đọc đúng hay sai thì xếp
hạng **không đổi một lần nào**. Con số 14% còn thấp vì hệ số M3 là **lựa chọn chưa fit**
(`gold_swing`, `loss_streak_bonus`, `pace_weight` trong `config/scoring_weights.yaml`) — chúng
là trục ablation, sẽ hiệu chỉnh khi có nhãn chuyên gia (M4).

### Còn lại sau M1

| Việc | Trạng thái |
|---|---|
| ~~`hp` 0.36–0.64~~ | **Xong (M2)**: tìm dòng bằng vòng vàng → `hp` 1.00; không thấy vòng thì báo thiếu chứ không đọc dòng người khác |
| ~~`streak` chưa đọc~~ | **Xong (M2)**: số + dấu theo màu biểu tượng → 0.82 |
| ~~Team Planner làm tối HUD~~ | **Xong (M2)**: kéo sáng trước khi kiểm → đọc lại đủ 5 trường |
| ~~Tộc/hệ luôn rỗng ở đường OCR~~ | **Xong (M2)**: đọc bảng bên trái, khớp tên qua `NameIndex` |
| 4/16 lần reroll sót | Còn — đều là roll **ngay trước lúc màn đóng**: thẻ chưa kịp đứng yên đủ 2 khung thì màn đã tắt |
| Đọc HUD tốn 3,1 s vì thêm chuỗi + máu động | Đã giảm còn 0,6–0,9 s bằng cache theo từng ô; vẫn cần theo dõi khi chạy live |

## Related

- [Overview](overview.md)
- [Labeling guide](labeling-guide.md)
- [Augment reroll rescan](augment-reroll-rescan.md)
- [Expert knowledge](expert-knowledge.md)
- [Evaluation framing](../expert-prior/evaluation-framing.md)
