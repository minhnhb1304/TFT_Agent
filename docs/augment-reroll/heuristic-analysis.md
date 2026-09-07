# Trực Giác Của Cao Thủ: Đúng Ở Đâu, Hỏng Ở Đâu

Trực giác thường được phát biểu là:

> Giữ thẻ "ít tệ nhất" làm lưới an toàn → đổi thẻ tệ nhất trước → nếu thẻ mới xuất sắc thì
> chốt ngay và để dành lượt đổi → nếu vẫn tầm thường thì đổi tiếp → hết lượt thì lấy thẻ
> tốt nhất trong ba thẻ cuối.

## Phần đúng

**"Đổi thẻ tệ nhất trước"** và **"giữ thẻ tốt nhất làm lưới an toàn"** là **T1** và **T2** —
chứng minh được, không phải kinh nghiệm. Hướng dẫn công khai của cộng đồng cũng hội tụ về
đúng luật này ("reroll your augments that are worse than the best one"), nên toán và thực
hành khớp nhau ở đây.

Điều đó cũng có nghĩa: **giá trị gia tăng của engine không nằm ở luật dừng**. Luật dừng
gần như tầm thường. Nó nằm ở chỗ chấm `Score(a│S)` cho đúng theo board.

## Phần sai

**"Thẻ mới xuất sắc thì chốt ngay để DÀNH lượt đổi"** — lượt đổi **không dành được**. Chúng
không chuyển sang chặng sau. Nếu lượt đổi miễn phí thì dừng sớm là lỗ EV thuần (T2).

Hành vi ấy chỉ hợp lý khi lượt đổi **có giá**, và giá đó không phải "để dành" mà là
**đốt pool** ([depletion-cost.md](depletion-cost.md)) — cộng với đồng hồ 30 giây.

## Phần cũng sai theo hướng ngược lại

**"Hết lượt thì lấy thẻ tốt nhất trong ba thẻ cuối"** ngầm giả định vét hết lượt là ổn.
Không ổn: lượt thứ ba bắt buộc đổi chính ô đang giữ thẻ tốt nhất. Đo được (n = 20.000):
vét hết ba lượt **không hơn gì không đổi lần nào**.

## Bảng các chỗ giả thiết vỡ

T1/T2 tối ưu dưới tập giả thiết {ô hoán đổi được, rút i.i.d., đổi miễn phí, trung lập rủi
ro, điểm chính xác}. Mỗi lỗi là một giả thiết bị vi phạm:

| # | Vi phạm | Hậu quả | Xử lý |
|---|---|---|---|
| 1 | Ô không hoán đổi được (kiểu "ô chủ đề" Set 14) | T1 hỏng: có thể nên đổi thẻ khá ở ô giàu hơn thẻ tệ ở ô nghèo | Chưa xử lý — Set 18 chưa thấy dấu hiệu |
| 2 | Tailoring | `F_S` không đều, engine sợ reroll | `tailoring_beta` — xem [tailoring.md](tailoring.md) |
| 3 | **Lời nguyền người tối ưu** | Điểm có nhiễu; lấy max trên **nhiều** lần rút khuếch đại thiên lệch chọn lọc ⟹ chính sách tối ưu-có-nhiễu phải reroll **ít hơn** chính sách không nhiễu | Đã ghi nhận, **chưa** cài co ngót — xem dưới |
| 4 | Augment liên chặng (`Augmented Power`, `Reroll Transfer`) | Phá tính tách rời trong một chặng | Chưa xử lý; `Reroll Transfer` khiến lượt thừa có giá trị thật |
| 5 | Cặp không phân biệt được | Có thể đổi mất một thẻ hoá ra rất tốt | Khoảng `[lo, hi]`; chỉ hành động khi quyết định bất biến |
| 6 | HP đếm hai lần | `TempoFit` đã có HP | `risk_lambda = 0` mặc định |

## Về mục 3, nói thẳng

`Base` (w1) chiếm **30% điểm** và hiện đang chạy trên `MOCK-NOT-REAL` ở cả 254 augment.
Nghĩa là `Score` hiện có nhiễu **không đo được**, và chính sách này lấy max trên tối đa 6
lần rút.

Đó là điều kiện chuẩn của lời nguyền người tối ưu: giá trị thật của thẻ được chọn thấp
hơn điểm của nó một cách hệ thống, và sai lệch **tăng** theo số lần rút.

Hệ quả đúng là thêm một số hạng co ngót vào `g(R)`. Chưa cài, **có chủ ý**: độ lớn của co
ngót phụ thuộc phương sai nhiễu, mà cái đó chỉ ước lượng được khi có số liệu placement
thật. Cài một hằng số đoán vào đây sẽ tạo ra đúng thứ mà `ExpertTierListProvider` được
viết ra để tránh — một hệ thống chạy mượt và tư vấn sai với vẻ tự tin.

Ghi nhận là nợ, không phải là xong.

## Related

- [dominance-theorem.md](dominance-theorem.md) — T1/T2/T3
- [depletion-cost.md](depletion-cost.md) — vì sao dừng sớm đôi khi đúng
- [evaluation.md](evaluation.md) — đo phần nào đo được
