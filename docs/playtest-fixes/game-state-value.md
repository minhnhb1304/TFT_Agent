# Game State Value

Hạng mục B — bước 0 thuộc mốc **M2**, bước 1–9 thuộc **M3** của [playtest fixes](overview.md). Làm cho việc đọc **tiền, cấp, EXP, chuỗi**
thực sự đổi được lời khuyên — và cho người chơi **thấy** điều đó.

## Nguyên nhân

| Trường | Dùng trong điểm lõi? |
|---|---|
| `stage` | Có — `econ_fit` |
| `hp` | Có — `tempo_fit` |
| `gold` | **Không** — chỉ ghi vào `detail` (`src/decision/scoring/econ_fit.py:69`) |
| `level`, `xp`, `streak` | **Không** |

→ HUD đọc đúng hay sai thì thứ hạng lõi vẫn y hệt. `rules_engine.xp_advice` và
`projected_income` đã có nhưng không hiện trên panel lõi.

### Riêng trong `run_replay.py` (đường chạy buổi test)

| Vấn đề | Hệ quả |
|---|---|
| HUD chỉ đọc **tại khung màn chọn lõi** — màn này che tiền/cấp | Tracker gần như không có số thật |
| `st.gold or 0`, `st.level or 1`, `st.hp or 100` | Số thiếu thành **số giả trông như thật** (0 vàng, cấp 1, 100 máu) |
| Tự dựng `GameState(gold, level, hp, stage)` thay vì dùng `tracker.state()` | Mất `xp`, `xp_needed`; `active_traits` rỗng → `board_fit` luôn trung tính |
| `bundle.economy`, `bundle.comp` được tính nhưng **không hiển thị** | Lời khuyên XP/lãi/đội hình biến mất |
| Không hiện `stale`/`never_seen` | Người xem không biết số nào là thật |
| Đường OCR **không đọc tộc/hệ** (chỉ `AugmentReader`/Gemini đọc) | Cần `read_traits` trong `OcrCardReader` |
| HUD **không có ROI chuỗi thắng/thua** | Có ROI được — xem "Ba lỗi ROI" bên dưới |

### Ba lỗi ROI đo được trên record 2026-09-16

| # | Lỗi | Bằng chứng | Cách sửa |
|---|---|---|---|
| R1 | **HP đọc nhầm người chơi khác.** ROI `hud/hp` cố định ở một dòng, nhưng bảng 8 người **sắp xếp lại theo máu** | 2/6 màn sai (88 thay vì 78; 93 thay vì 73); `hud_acc[hp]` = 0.36 ở baseline | Tìm dòng của người chơi bằng **vòng tròn vàng** quanh avatar (HSV 18–38, S>140, V>150, lấy vùng liên thông lớn nhất), rồi cắt ô số theo tâm vòng đó. Nguyên mẫu: **4/5 đúng**, ca còn lại do bảng bị che |
| R2 | **Chuỗi thắng/thua đọc được**, không cần suy từ HP | Biểu tượng lửa ngay phải số vàng: **cam = thắng**, **xanh = thua**; số khớp nhãn (`🔥3` = +3, xanh `1` = −1) | Thêm ROI `hud/streak` (~x 0.575–0.60, cùng hàng với `gold`); dấu lấy theo màu biểu tượng |
| R3 | **Mở Team Planner → mất sạch gold/level/xp.** `hud_bar_present` đòi có điểm sáng, mà panel làm tối thanh HUD | Độ sáng tối đa 107 khi mở planner, 240 lúc bình thường; cả 3 trường trả `None` | Chuẩn hoá tương phản trước khi kiểm, hoặc nới ngưỡng khi phát hiện màn bị làm tối; vẫn đọc được vì chữ còn nguyên. HUD priming che phần còn lại |

Phần lớn câu lặp ở [augment-commentary.md](augment-commentary.md) ("HP 100 còn thoải mái",
"Board chưa có đơn vị nào thuộc…") là **hệ quả trực tiếp** của bảng trên.

## Kế hoạch

| # | Bước | Kiểm chứng |
|---|---|---|
| 0a | HUD priming trong `LiveSession` (~3 s, dày hơn trước vòng lõi); dùng `tracker.state(traits=…)`; bỏ `or 0/1/100` | `hud_acc` ≥ 90% trên nhãn M0 |
| 0b | `OcrCardReader.read_traits` đọc bảng tộc/hệ qua `NameIndex` | So nhãn `traits` |
| 0c | **R1**: `hud/hp` theo dòng có vòng vàng, không theo toạ độ cố định | `hud_acc[hp]` ≥ 0.9 trên nhãn |
| 0d | **R2**: ROI `hud/streak` + dấu theo màu biểu tượng | `hud_acc[streak]` ≥ 0.9 |
| 0e | **R3**: đọc được HUD cả khi Team Planner làm tối màn | Khung 1126 s của game 2 ra đủ gold/level/xp |
| 0f | Bỏ qua lần đọc HUD nếu các ô HUD không đổi (hash nhỏ) — đo được **~1 s mỗi lần đọc**, nên quét một video 36 phút mất ~12 phút chỉ vì HUD | Thời gian `--mode session` giảm; giá trị không đổi |
| 1 | ✅ **Đo trước**: `scripts/state_effect_report.py --ablate` → **0/22 offer** đổi thứ hạng | đúng như dự đoán |
| 2 | **Dòng trạng thái** trên `AugmentPanel`: `3-2 · Lv6 (4/10 XP) · 32g (+3 lãi) · HP 64 · thua 3` | Hiện trên replay khung record |
| 3 | Thêm 1 câu từ `RulesEngine` dưới dòng trạng thái (XP lẻ, lãi, mốc tiền) | Test snapshot panel |
| 4 | ✅ `econ_fit` theo **tiền + chuỗi** (kịch lãi → giảm; nghèo hoặc thua dài mà còn máu → tăng) | 16 test trong `test_state_effect.py` |
| 5 | ✅ `tempo_fit` thêm **nhịp lên cấp** (chậm nhịp → ưu tiên sức mạnh ngay; nhanh nhịp không đổi gì) | nhịp chuẩn để trong config, ablation được |
| 7 | ✅ **Hiện ảnh hưởng**: `src/decision/state_effect.py` chấm lại với trạng thái trung tính, sinh câu "Vì 55 vàng, chậm nhịp 2 cấp: X −0.02 (từ #1 xuống #2)" | im lặng khi chênh lệch < 0.02 và thứ hạng không đổi |
| 8 | **Báo số cũ**: trường `stale`/`never_seen` hiện rõ trên dòng trạng thái, không dùng im lặng | Test với tracker thiếu dữ liệu |
| 9 | ✅ Chạy lại bước 1 → **3/22 (14%)**, trong đó 3 lần đổi cả lựa chọn đầu | xem [eval-dataset.md](eval-dataset.md) |
| 6 | ⏸ Nối archetype đội hình (fast 8 / reroll) | hoãn: cần chọn đội hình **trước** khi xếp hạng lõi, mà đường 30 giây đang chạy lõi trước |

## Lưu ý

- Hệ số mới (bước 4–6) là **lựa chọn**, chưa fit — đánh dấu trong `config/scoring_weights.yaml`
  là trục ablation. Khi có nhãn chuyên gia ([expert-knowledge.md](expert-knowledge.md)) thì fit lại.
- Màn chọn lõi che HUD → phụ thuộc HUD priming ~3 s bên ngoài màn (xem live mode).

## Related

- [Overview](overview.md)
- [HUD reader](../vision/hud-reader.md)
- [Live mode](../live-mode/overview.md)
