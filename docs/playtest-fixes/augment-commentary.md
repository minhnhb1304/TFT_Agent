# Augment Commentary

Hạng mục C — mức A thuộc mốc **M4**, mức B/C thuộc **M6** của [playtest fixes](overview.md). Làm nhận xét về lõi **có thông tin và không lặp**.

## Nguyên nhân

- Câu mẫu cố định: `tempo_fit` 4 câu (chỉ về HP), `econ_fit` 1 câu, `board_fit` vài câu.
- Câu giống hệt lặp trên cả 3 thẻ ("Bậc S theo bảng tier…", "HP 64 còn thoải mái").
- Không có: lý do so sánh (#1 hơn #2 vì sao), tác dụng của lõi, liên hệ đội hình.
- `llm_reasoner` tắt mặc định, timeout 2 s quá ngắn.

## Mức A — tất định, rẻ (hoàn thành 2026-09-19)

| # | Bước | Trạng thái |
|---|---|---|
| A1 | **Gom câu chung** lên dải trạng thái; mỗi thẻ chỉ giữ điểm khác biệt | ✅ `_shared_reasons` — **ngưỡng đã sửa**, xem dưới |
| A2 | **Lý do so sánh** #1 vs #2 theo thành phần chênh nhiều nhất | ✅ `src/decision/margin.py`, 12 test |
| A3 | Câu biến thiên theo **số thật** của feature | ✅ đã có sẵn từ M2/M3 — việc còn lại là **đo**, làm bằng `scripts/reason_quality_report.py` |

### A2 — phép tách chính xác, không phải ước lượng

`total = Σ w_c · s_c` nên chênh lệch giữa hai thẻ tách được về từng thành phần:
`gap = Σ w_c · (s1_c − s2_c)`. Tổng các phần **bằng đúng** con số `delta` panel đang hiện —
`test_parts_cong_lai_bang_dung_gap` khoá đẳng thức này, nên nếu một ngày `score_one` không
còn cộng tuyến tính thì test đỏ đúng chỗ.

Câu nói **cả hai chiều**: "Hơn lựa chọn kế chủ yếu nhờ trang bị (+0.06) — dù kém nhịp độ (0.03)".
Giấu vế thua thiệt là cách nhanh nhất để mất tin cậy, vì người chơi nhìn bảng điểm thành phần
là thấy ngay.

Im lặng trong ba trường hợp, cả ba đều cố ý: chưa đủ hai thẻ; không thành phần nào vượt
`MIN_PART = 0.01`; và #1 không dẫn ở bất kỳ thành phần nào (chênh lệch đến từ nhiều mảnh vụn,
không có lý do nào để gọi tên).

### A1 — ngưỡng cũ sai, đo mới thấy

Luật cũ chỉ gom câu xuất hiện ở **cả ba** ô. Nhưng dạng lặp thường gặp nhất là **đúng hai** ô
(hai thẻ cùng bậc) — nó lọt lưới hoàn toàn. Ngưỡng hạ xuống **hai**, và câu chỉ đúng cho một
phần thì **phải nói rõ ô nào** (`Ô 1, Ô 2: Bậc B …`); không nói thì dải trạng thái đang phát
biểu sai về ô còn lại, một lỗi nặng hơn lặp.

### Mệnh đề xuất xứ tách khỏi câu lý do

Chuỗi `(expert-tierlist:TFT Academy (Dishsoap & Frodan)/patch=18.2) — xếp hạng chủ quan,
KHÔNG phải số đo` **giống hệt nhau trên mọi thẻ có bậc**, nên để nó trong `reason` là tự tay
tạo ra câu lặp: đo được **10/33 ô**. Nó chuyển sang `detail["caveat"]` và hiện **một lần** —
dải trạng thái ở panel, một dòng cuối ở CLI.

Bỏ hẳn thì **không được**: đó là rào chắn giữa "ý kiến" và "số đo". Bất biến SPEC 3.4.2 vì thế
chuyển chỗ chứ không mất: `full_reason()` ghép hai mảnh lại cho test kiểm, và hai test mới
(`test_xuat_xu_noi_len_dai_trang_thai_dung_mot_lan`, `test_cli_explain_van_in_xuat_xu`) canh
đúng chuyện nó **có nổi lên** ở cả hai mặt hiển thị.

### Số đo trên nhãn playtest (2 game, 22 offer, 66 ô)

```powershell
.venv\Scripts\python scripts\reason_quality_report.py data\eval\playtest\*.json
```

| | trước A1'/A2 | sau |
|---|---|---|
| `dup_reasons` | 30/66 (45%) | **0/66 (0%)** ✅ G3 |
| `dup_chars` | 1.094 (~16% số chữ) | **0** |
| `empty_slots` | 10/66 | **20/66** ⚠ |
| `distinct_reasons` | 15 | 14 |
| `edge_coverage` (A2 nói được) | — | **0.86** |

**Đánh đổi phải nói rõ**: `dup_reasons = 0` đạt được bằng cách **dời chữ**, không phải sinh
thêm chữ. Nội dung không mất (dải trạng thái mang nó, có nhãn ô), nhưng **30% cột giờ trống**.
Đó là một thiếu sót thật, chưa phải thắng lợi trọn vẹn — xem [A2b](#a2b--việc-còn-lại).

### A2b — việc còn lại

Cột trống nên mang **điểm khác biệt của riêng nó**, tức là tổng quát hoá A2 từ "#1 vs #2" thành
"mỗi thẻ so với phần còn lại". `margin.compare()` đã có sẵn phép tách; việc còn lại là chạy nó
cho từng ô thay vì chỉ cho ô đầu.

## Mức B — dữ liệu soạn trước

| # | Bước | Kiểm chứng |
|---|---|---|
| B1 | **Gắn đội hình**: "Nằm trong best augments của *[comp gần board nhất]*", "lệch hướng fast 8" | Dùng `comp_selector` + `data/meta_comps.json` |
| B2 | **`data/augment_notes.json`**: tóm tắt tác dụng, khi nào nên lấy, bẫy thường gặp. LLM soạn **offline** mỗi patch từ mô tả CDragon + guide lolchess/TFT Academy | Có `patch`, `source`; người chơi duyệt mẫu |
| B3 | Luật chuyên gia từ [expert-knowledge.md](expert-knowledge.md) là **nguồn câu ưu tiên cao nhất** | Thứ tự: luật chuyên gia → ghi chú → câu mẫu |

## Mức C — LLM không chặn

| # | Bước | Kiểm chứng |
|---|---|---|
| C1 | Hiện câu tất định ngay; LLM trả về (≤ 8 s) thì thay vào | Panel không bao giờ chờ LLM |
| C2 | Chỉ đưa dữ kiện có cấu trúc + 3–5 ví dụ người chơi đã giải thích; cấm tự bịa số | `assert_order_preserved()` vẫn giữ; số trong câu phải có trong dữ kiện |

## Đo chất lượng

- Tỉ lệ câu trùng giữa các thẻ (mục tiêu: 0).
- Số câu khác nhau trên toàn bộ khung eval.
- Người chơi chấm 20 màn chọn lõi: câu "có ích / không" (so trước và sau).

## Related

- [Overview](overview.md)
- [Expert knowledge](expert-knowledge.md)
- [Game state value](game-state-value.md)
