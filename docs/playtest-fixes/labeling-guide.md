# Labeling Guide

Cách kiểm và sửa nhãn playtest — bước M0 của [playtest fixes](overview.md). Định dạng file:
[eval-dataset.md](eval-dataset.md).

## Cách 1 — công cụ xem lại (khuyên dùng)

```powershell
.venv\Scripts\python scripts\review_playtest_labels.py `
    data\eval\playtest\<tên file>.json `
    --video "D:\workspace\tft_record\<tên video>.mp4"
```

Trang tự mở ở `127.0.0.1:8765` (chỉ chạy trong máy). Mỗi offer hiện ảnh chụp, 3 ô nhập tên lõi
có gợi ý tiếng Việt, ô chọn ô vừa reroll, và nút chèn/xoá offer. Bấm **Lưu** để ghi.
Còn lỗi thì **không ghi gì cả** và trang liệt kê lỗi — sửa rồi lưu lại.

`--video` chỉ cần khi muốn nút "Chụp ảnh tại giây này" (dùng cho offer chèn tay).

## Cách 2 — sửa tay file JSON

| Thứ | Ở đâu |
|---|---|
| File nhãn | `data\eval\playtest\<video_id>.json` |
| Ảnh từng offer | `data\eval\playtest\snapshots\<video_id>\<giây>_<stage>_offerN.jpg` |
| Video gốc | Thư mục bạn đã record, tua tới giây `at_s` / `open_s` |

### Năm việc cho mỗi màn

1. **`hud`** — tiền, cấp, XP, máu **ngay trước khi màn chọn lõi hiện ra** (tua tới trước
   `open_s` vài giây). `xp`/`xp_needed` là hai số trên thanh XP (`4/10`). `streak`: thắng
   liên tiếp là số dương, thua liên tiếp là số âm; không nhớ thì để `null`.
2. **`cards`** — 3 lõi trong ảnh, theo thứ tự ô 1 → ô 3 từ trái sang. Tra apiName:
   ```powershell
   .venv\Scripts\python -c "import sys,json; from src.knowledge.augment_catalog import normalize; d=json.load(open('data/name_index.json',encoding='utf-8'))['display']['augments']; q=normalize(sys.argv[1]); [print(a,'=',n.get('vi')) for a,n in d.items() if q in normalize(n.get('vi',''))]" "khảm bảo thạch"
   ```
   Hai lõi trùng tên (ví dụ bản thường và bản `+` nhìn giống hệt) thì ghi **cả hai**:
   `["DA_18_FloraFatalisAugment", "DA_18_FloraFatalisAugmentPlus"]`.
3. **`rerolled_slot`** — ô vừa bị reroll để ra offer này, đếm **từ 0**: ô trái `0`, giữa `1`,
   phải `2`. Offer đầu tiên luôn `null`.
4. **`picked`** — lõi bạn đã chọn (phải nằm trong offer cuối).
5. **`status`** — đổi `"draft"` thành `"verified"`. Chỉ màn `verified` mới được chấm; màn nào
   chưa chắc thì cứ để `draft`.

### Thiếu offer

Mỗi offer chỉ được khác offer trước **đúng một ô**. Khác hai ô nghĩa là thiếu một offer ở
giữa: tua video tìm lúc mới đổi một ô, rồi chèn thêm một mục vào `offers` với `at_s` là giây
đó (`snapshot` để `null` cũng được).

### Kiểm lại

```powershell
.venv\Scripts\python -c "from src.eval.playtest_labels import load; import json; k=json.load(open('data/name_index.json',encoding='utf-8'))['display']['augments'].keys(); load(r'data\eval\playtest\<tên file>.json', k); print('OK')"
```

In `OK` là hợp lệ. Có lỗi thì in đủ danh sách, kèm số màn và số offer.

## Nguyên tắc

- Ghi **điều thật sự xảy ra trên màn hình**, đừng chỉ xác nhận gợi ý: gợi ý do chính bộ OCR
  đang được đánh giá sinh ra, xác nhận bừa sẽ làm điểm số đẹp giả.
- Offer có cảnh báo **"CHƯA ỔN ĐỊNH"** = ảnh chụp lúc thẻ có thể đang lật. Xem kỹ.
- `expert` để trống ở M0 — phần đó thuộc [expert-knowledge.md](expert-knowledge.md) (M4).

## Related

- [Eval dataset](eval-dataset.md)
- [Overview](overview.md)
- [Expert knowledge](expert-knowledge.md)
