# Labeling Guide

Cách kiểm và sửa nhãn playtest — bước M0 của [playtest fixes](overview.md). Định dạng file:
[eval-dataset.md](eval-dataset.md).

## Bước 0 — tra `role` trước khi mở video

Mở [`data/eval/split.json`](dataset-split.md) xem video này là `development` hay `heldout`.

| `role` | Được làm gì |
|---|---|
| `development` | Gắn nhãn, xem đầu ra của máy, sửa ngưỡng, chạy lại — thoải mái |
| `heldout` | **Chỉ** gắn nhãn. Không chạy `eval_playtest.py`, không xem ranking của advisor, không sửa gì sau khi xem |

Xem kết quả máy trên một video held-out là làm nhiễm nó vĩnh viễn, và không có cách nào hoàn lại.

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

### Bốn trường cấp file — gắn một lần cho cả video

| Trường | Lấy ở đâu |
|---|---|
| `game_id` | `"<video_id>#<số ván trong video>"`, ví dụ `"nam_01#1"`. Outplayed ghi một ván một file nên gần như luôn `#1`. Giữ hậu tố để định dạng thống nhất với VOD nhiều ván |
| `player_id` | Copy từ `split.json`. **Đừng** parse ra từ tên file |
| `final_placement` | Người chơi tự khai (xem [recording protocol](recording-protocol.md)). Đối chiếu với màn kết trận nếu video có |
| `capture_profile` | Copy từ `split.json`: `tool`, `size`, `lang`, `fps`, `original_name` |

`game_id` phải **giống hệt** giá trị mà `ScenarioLogger` ghi ở runtime, nếu không
`correlation.py` sẽ không join được và nó **không báo lỗi** — chỉ trả `n_games = None` rồi coi
mọi quyết định là độc lập, đúng cái bẫy [dev_log §8c](../../dev_log.md) đã sửa. Vì thế cả công
cụ gắn nhãn và runtime phải dùng **một hàm dẫn xuất duy nhất**.

> ⏳ Bốn trường này **chưa có** trong `src/eval/playtest_labels.py` (schema 1). Cần thêm ở cấp
> `PlaytestLabels` trước khi gắn nhãn video đầu tiên — xem [eval-dataset.md](eval-dataset.md).

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

- [Dataset split](dataset-split.md) — tra `role` trước khi gắn nhãn
- [Recording protocol](recording-protocol.md) — nhận video và đổi tên
- [Eval dataset](eval-dataset.md)
- [Overview](overview.md)
- [Expert knowledge](expert-knowledge.md)
