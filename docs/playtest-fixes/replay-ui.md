# Replay UI

Thiết kế giao diện vỏ replay, chốt 2026-09-18. Màu và chữ: [ui-tokens.md](ui-tokens.md).
Overlay live **thiết kế riêng**, chỉ dùng chung dữ liệu (`AdviceReady`), không dùng chung layout.

## Vấn đề của bản hiện tại

| Lỗi | Hệ quả |
|---|---|
| Video chiếm ~60% diện tích | Thứ cần đọc (quyết định) bị đẩy xuống góc |
| Kết luận nằm ở dòng chữ nhỏ nhất, dưới cùng | Phải tìm mới thấy |
| Mọi thứ đều xanh phát sáng | Không có gì nổi hơn gì |
| Bảng xếp hạng sắp theo điểm | Không khớp thứ tự ô trên màn game, mắt phải dịch |

## Bố cục

```
┌ 3-2 · Lv4 (8/10 XP) · 55 vàng · HP 88 · thua 1 ······· đổi thẻ 2/3 ┐  ← dải trạng thái
│ Còn 2 XP lên cấp 5: 4 vàng (1 lần mua)                            │  ← 1 dòng kinh tế
├───────────────────────────────────────────────────────────────────┤
│ ► CHỌN Ô 2 · Dư Âm Ma Thuật+          hơn ô 3 là +0,08            │  ← dải kết luận
├─────────────────┬─────────────────┬───────────────────────────────┤
│ ▁▁▁ bạc         │ ▁▁▁ vàng        │ ▁▁▁ bạc        ← sọc độ hiếm  │
│ Ô1 Cảm Thấy…    │ Ô2 Dư Âm Ma…    │ Ô3 Xoay Bài Tự Động           │
│ A ▌▌▌▌░  0.55   │ S ▌▌▌▌▌  0.63   │ B ▌▌▌░░  0.41                 │
│ · lãi tới 5 vàng│ · khớp hệ (3)   │ · lệch hướng carry            │
│ · HP thoải mái  │ · hơn #2 nhờ… │ · bậc B                       │
│ ✓ còn đổi       │ ✓ còn đổi       │ ✗ đã đổi                      │
├─────────────────┴─────────────────┴───────────────────────────────┤
│                        video (thu gọn được)                       │
├───────────────────────────────────────────────────────────────────┤
│ ◀ offer 2/4 ▶   ▬▬▬●▬▬▬▬▬▬▬▲▬●▬▬▬▬▬▬▬▲▬▬●▬▬▬  ● vòng lõi ▲ reroll │
└───────────────────────────────────────────────────────────────────┘
```

Cột được khuyên: viền `accent` + nền `accent-fill`. Không tô màu cột nào khác.

## Quy tắc từng khối

| Khối | Quy tắc |
|---|---|
| Dải trạng thái | Số dùng font đẳng khoảng. Trường cũ/chưa đọc hiện `?` màu `warn`, kèm tooltip nói vì sao |
| Dải kết luận | Một câu, động từ trước: "CHỌN Ô n" hoặc "ĐỔI Ô n". Bên phải là **chênh lệch** với lựa chọn kế, không phải điểm tuyệt đối |
| Cột thẻ | Thứ tự **theo ô trên màn game**, không theo thứ hạng. Thứ hạng nằm ở thanh điểm |
| Lý do | Tối đa 3 dòng/thẻ. Câu chung cho cả 3 thẻ bị **gom lên dải trạng thái**, không lặp (mục [C](augment-commentary.md)) |
| Ô chưa đọc | Viền đứt + chữ "chưa đọc được" + chữ OCR thô, **không bao giờ ẩn đi** |
| Chân cột | Trạng thái nút đổi thẻ: `✓ còn đổi` (`ok`) / `✗ đã đổi` (`text-muted`) |
| Video | Thu gọn được; khi xem lại chuỗi quyết định thì video không phải thứ chính |
| Dải thời gian | Mốc vòng lõi (●) và từng lần reroll (▲) — bấm để nhảy. `◀ ▶` bước qua từng trạng thái thẻ trong vòng hiện tại |

## Trạng thái phải vẽ được

`đang quét video` · `đang đọc thẻ` · `chưa ở màn chọn lõi` · `đã rời màn` ·
`chưa đọc được 1–3 ô` · `số HUD cũ` · `dữ liệu patch cũ` · `lỗi đọc`.

Mỗi trạng thái là **một dòng ở dải trạng thái**, không phải hộp thoại — người xem đang tua
video, không nên bị chặn.

## Việc

| # | Việc | Kiểm chứng |
|---|---|---|
| 1 | `src/replay/theme.py`: token màu/chữ, sinh QSS từ đó | Không hex rời rạc trong widget |
| 2 | `src/replay/widgets/slot_column.py`: cột thẻ (sọc độ hiếm, tier, thanh điểm, lý do, chân) | Test dựng dữ liệu → nhãn, không cần Qt vẽ |
| 3 | `verdict_bar.py`, `state_strip.py` | Hiện `?` đúng chỗ khi thiếu số |
| 4 | `timeline.py`: mốc vòng + reroll, bước offer | Số mốc = số vòng; ▲ = số lần reroll |
| 5 | Ráp vào `window.py`, bỏ panel cũ | Ảnh chụp trước/sau |

## Related

- [UI tokens](ui-tokens.md)
- [Replay shell](replay-shell.md)
- [Augment commentary](augment-commentary.md)
