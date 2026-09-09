# Bộ Phân Loại Nút Đổi Thẻ

`src/vision/reroll_buttons.py` biến một khung hình thành vector `r = (r₀, r₁, r₂)` mà
`RerollState` cần. Màn hình **không có bộ đếm số** ở đâu cả — thứ duy nhất đọc được là
ba cái nút dưới ba thẻ bài, mỗi cái mang trạng thái riêng.

## Hình học: đo, không đo tay

Chạy Canny trên **255 khung** `augment_select` của **ba VOD** rồi lấy cột/hàng có cạnh.
Cả ba VOD trả về đúng một bộ số ở 1920×1080:

| Ô | trái | trên | rộng | cao |
|---|------|------|------|-----|
| `reroll_0` | 500 | 834 | 100 | 52 |
| `reroll_1` | 910 | 834 | 100 | 52 |
| `reroll_2` | 1320 | 834 | 100 | 52 |

Bước nhảy 410 px giữa ba ô khớp với bước nhảy của ba thẻ bài. Số này nằm ở
`SEED_PIXELS["augment_select"]` trong `tools/calibrate.py`, không nằm trong code đọc pixel.

## Ba trạng thái, không phải hai

| Trạng thái | nền nút | viền | `warm` | `fill_value` | n |
|---|---|---|---|---|---|
| `active` | nâu vàng | vàng | **+24,3 … +49,6** | 39,5 … 45,8 | 350 |
| `pressed` | gần đen | vàng | −6,3 … −2,6 | **7,6 … 8,2** | 11 |
| `disabled` | xanh than | xám | **−8,4 … −2,1** | **29,8 … 37,9** | 148 |
| `unknown` | *không phải màn chọn augment* | — | −46 … +55 | 13 … 98 | 256 |

`warm = mean(R) − mean(B)` trên lòng nút; `fill_value` là độ sáng trung bình của **40%
điểm tối nhất** trong lòng nút — lấy phần tối nhất thì nét glyph và con trỏ chuột bị
loại, còn lại đúng màu nền.

**`pressed` là cái bẫy.** Nền nó gần đen nên `warm` âm y hệt nút đã dùng; đọc bằng màu
thôi sẽ gọi nó là `disabled`. Chuỗi thời gian trên ba VOD nói ngược lại: khung kế tiếp
nó là một nút **sáng bình thường trở lại** (`s7h` @ 066–070 ô 2, @ 081–085 ô 0). Đó là
khung nháy lúc bấm chuột. Gọi nhầm nó thành `disabled` là tự tay xoá một lượt roll
người chơi vẫn còn — và chính sách tuần tự sẽ dừng sớm một cách vô cớ.

## Nhận biết "có nút ở đây" phải dùng hình dạng

Khung trích quanh mốc sự kiện có cả khung **không phải** màn chọn augment. `warm` của
địa hình chạy khắp khoảng — đo được một mảng cỏ **+54**, cao hơn cả nút sáng. Chỉ hình
mũi tên vòng tròn là không lặp lại ở đâu khác.

Độ khớp lấy `max` trên **bốn nửa** của mẫu (trái/phải/trên/dưới) chứ không trên cả mẫu:
con trỏ chuột nằm đè lên glyph ở một số khung, che một nửa thì nửa kia vẫn khớp. Khớp
trên cả mẫu tụt về 0,37 — lẫn vào địa hình; khớp trên nửa không bị che vẫn 0,72.

## Ba cái khe

Mỗi ngưỡng nằm giữa một khe đã đo, không phải một số chọn cho đẹp:

| Ngưỡng | giá trị | khe |
|---|---|---|
| `min_glyph_match` | 0,68 | nút thật thấp nhất **0,723** / địa hình cao nhất **0,636** |
| `active_warm` | 12,0 | `disabled` cao nhất **−2,1** / `active` thấp nhất **+24,3** |
| `pressed_fill_value` | 20,0 | `pressed` cao nhất **8,2** / `disabled` thấp nhất **29,8** |

## Đối chứng với nhãn tay

Khe tách rời **không** chứng minh cụm đó đúng tên — nó chỉ chứng minh máy phân biệt
được ba thứ. Nên có `data/eval/reroll_button_labels.json`: **35 khung / 105 ô** gán nhãn
bằng mắt (24 khung bốc ngẫu nhiên seed 20260909, cộng cả 11 khung có ô `pressed` — lớp
hiếm nhất, bốc ngẫu nhiên thì không khung nào rơi vào).

```powershell
.\.venv\Scripts\python scripts/read_reroll_buttons.py `
    --frames-dir data/frames/s7h-jHMpFmQ/augment_select `
    --labels data/eval/reroll_button_labels.json
```

**105/105 = 100,00%**, không ô nào lệch, trên cả ba VOD. Trong 255 khung: 169 khung hiện
đủ ba nút, và 158/169 ngã ngũ cả ba ô ngay ở khung đơn lẻ — 11 khung còn lại vướng đúng
những ô `pressed`, và cách xử lý là đọc lại ở khung kế tiếp.

## Cái không tuyên bố được

Số ở đây đo trên **3 VOD Set 18, 1920×1080, giao diện tiếng Việt**. Đổi độ phân giải thì
ROI vẫn đúng (toạ độ lưu dạng tỉ lệ) nhưng ngưỡng khớp mẫu **chưa** được đo lại. Đổi Set
hoặc đổi giao diện thì phải chạy lại `scripts/build_reroll_template.py` và đo lại trang này.

Và 255 khung này thuộc **tập phát triển** (`manifest.json` ghi `role: development`) — cùng
bộ khung dùng để chỉnh ngưỡng. Con số P/R/F1 cho SPEC 12.1 phải đo trên bản ghi tự quay,
theo `research/vanguard/testing-protocol.md` bước 3.

## Related

- [overview.md](overview.md) — ba chân của tầng thị giác và chân nào còn thiếu
- [../augment-reroll/overview.md](../augment-reroll/overview.md) — chính sách tiêu thụ vector `r`
- [../vod_pipeline_sop.md](../vod_pipeline_sop.md) — sinh lại `data/frames/` từ VOD
