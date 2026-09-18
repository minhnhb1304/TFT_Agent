# Augment Commentary

Hạng mục C — mức A thuộc mốc **M4**, mức B/C thuộc **M6** của [playtest fixes](overview.md). Làm nhận xét về lõi **có thông tin và không lặp**.

## Nguyên nhân

- Câu mẫu cố định: `tempo_fit` 4 câu (chỉ về HP), `econ_fit` 1 câu, `board_fit` vài câu.
- Câu giống hệt lặp trên cả 3 thẻ ("Bậc S theo bảng tier…", "HP 64 còn thoải mái").
- Không có: lý do so sánh (#1 hơn #2 vì sao), tác dụng của lõi, liên hệ đội hình.
- `llm_reasoner` tắt mặc định, timeout 2 s quá ngắn.

## Mức A — tất định, rẻ

| # | Bước | Kiểm chứng |
|---|---|---|
| A1 | **Gom câu chung**: câu xuất hiện ở cả 3 thẻ → 1 dòng đầu panel; mỗi thẻ chỉ giữ điểm khác biệt | Test: không câu nào lặp giữa các thẻ |
| A2 | **Lý do so sánh**: thành phần chênh nhiều nhất giữa #1 và #2 → "Hơn X chủ yếu nhờ khớp Ravager 3 (+0.12)" | Unit test trên ranking mẫu |
| A3 | Thêm biến thể câu theo **số thật** của feature (`econ_value`, `tempo`, `item_grants`) | Đếm số câu khác nhau trên 60 khung eval |

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
