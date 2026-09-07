# Tiên Nghiệm Chuyên Gia Cho w₁

`Base` (w₁) chiếm **30% tổng điểm**. Từ 2026-09-07, nguồn của nó là **bảng tier do người
chơi giỏi xếp**, không phải số liệu placement đo được.

## Vì sao đổi

Không còn nguồn đo được nào, ở bất kỳ mức rank nào:

| Nguồn | Kết quả |
|---|---|
| `tft-match-v1` trường `augments` | Riot đã gỡ ở Set 18 |
| `d3.tft.tools` | payload trả `{"singles": []}` trên mọi rank group / patch Set 18 |
| datatft.com | bảng tier hardcode trong bundle JS |
| tftacademy.com | dữ liệu dưới `/_app/`, robots.txt ghi Disallow |

Chi tiết và ngày đo: [`config/data_sources.yaml`](../../config/data_sources.yaml).

## Phát biểu được và phát biểu KHÔNG được

Đây là chỗ dễ nói quá tay, và nói quá tay ở đây thì không bảo vệ được.

> ✅ **"Không còn nguồn đo được, nên w₁ dùng một tiên nghiệm thứ tự có ký tên, kèm hệ số
> co ngót tường minh."**

> ❌ **"Bảng tier của cao thủ tốt hơn placement thô."**

Lập luận thứ hai *có phần đúng*: placement thô đúng là bị nhiễu bởi kỹ năng — `Cruel Pact`
có placement trung bình xấu vì người chơi kém hay lấy rồi chơi hỏng, chứ không phải vì
augment đó dở. Nhưng cách xử lý chuẩn cho việc đó là **lọc theo nhóm rank**
(Challenger/GM), không phải bỏ hẳn phép đo — và MetaTFT/tactics.tools công bố đúng những
lát cắt ấy.

Nên lý do thật là **không có sẵn**, không phải **ưu việt hơn**. Ta chọn tiên nghiệm chuyên
gia vì nó là thứ duy nhất còn lại, và ta nói đúng như vậy.

## Ba ràng buộc KHÔNG được phá

Đây là những gì `ExpertTierListProvider` được viết ra để giữ, và
`tests/test_augment_tiers.py` khoá lại:

1. `sample_n` **luôn = 0**. Không bao giờ bịa một cỡ mẫu để tín hiệu này nặng lên — đó
   chính là cách một ý kiến biến thành "số liệu" trong báo cáo.
2. `is_ordinal = True`, nên `is_evidence` **luôn False**.
3. `avg_place` chỉ là **mã hoá đơn điệu** của bậc, không phải placement đo được. Reason
   string phải nói rõ điều đó.

Promote **nguồn**, không promote **địa vị nhận thức** của nó.

## `ordinal_trust`: 0.35 → 0.65

`BaseScorer` co ngót điểm về trung tính theo `trust`:
`score = 0.5 + (raw − 0.5) × trust`.

0.35 được đặt khi bảng tier chỉ là **phương án dự phòng** đứng sau số liệu đo được. Giờ nó
là nguồn **duy nhất** của w₁, nên để 0.35 nghĩa là 30% tổng điểm chỉ đóng góp một phần ba
biên độ của nó.

**Không đặt 1.0, và đó là có ý.** Phần co ngót chính là chỗ trung thực của thiết kế. 0.65
là một **lựa chọn**, chưa fit trên dữ liệu nào — nó là một trục ablation, xem
[evaluation-framing.md](evaluation-framing.md).

## Trạng thái hôm nay

`data/augment_tiers.json` **chưa tồn tại**. Hệ thống suy giảm đúng như thiết kế: provider
rỗng → `Base` trung tính ở cả 254 augment → `evidence = uncalibrated`.

Phần đường ống đã xong; thiếu **dữ liệu**. Cần gì và định dạng ra sao:
[ingestion.md](ingestion.md).

## Bẫy đã bịt

Bộ số giả lập bịa sẵn `sample_n > 200`, nên `is_evidence` trả **True** cho nó. Vì nó phủ
đủ 254 augment, nó **che hết** bảng tier trong `default_provider` (CSV → tiers → Null):
thả một bảng tier thật vào repo cũng không đổi được gì, mà không có gì báo cả.

Đã sửa: `default_provider(..., allow_fabricated=False)` là mặc định — dòng nào tự khai báo
là giả thì bị bỏ ngay lúc nạp.

## Related

- [ingestion.md](ingestion.md) — định dạng và quy trình nạp
- [evaluation-framing.md](evaluation-framing.md) — vòng lặp tự xác nhận và cách tránh
- [augment-reroll/overview.md](../augment-reroll/overview.md) — chính sách reroll dùng w₁ thế nào
