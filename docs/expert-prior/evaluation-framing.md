# Khung Đánh Giá Khi w₁ Là Tiên Nghiệm Chuyên Gia

Việc w₁ trở thành bảng tier do người xếp làm **mạnh lên** một phần của SPEC §12 và **làm
hỏng** một phần khác. Phải tách hai phần đó ra trước khi báo cáo bất cứ con số nào.

## Mạnh lên: §12.4 giờ mới là câu hỏi thật

Dòng quan trọng nhất của bảng ablation là `only("base")` — "chỉ dùng stats tĩnh". Trước
đây nó so với **nhiễu giả lập**, nên câu hỏi là *"board-state có hơn số ngẫu nhiên không"*
— gần như chắc chắn có, và vì thế gần như vô nghĩa.

Giờ nó so với một **bảng tier của cao thủ**. Câu hỏi trở thành:

> **Ngữ cảnh bàn cờ (w₂…w₅) có đánh bại một bảng tier chuyên nghiệp không?**

Đó là một câu hỏi nghiên cứu thật, có thể trả lời **không**, và nếu trả lời không thì đó
vẫn là kết quả hợp lệ phải báo cáo trung thực — đúng như SPEC §12.4 đã tự yêu cầu.

Đây là **luận điểm chính** nên dùng, vì nó miễn nhiễm với vấn đề ở mục sau.

## Hỏng: §12.3 có nguy cơ tự xác nhận

§12.3 kiểm tra advisor bằng cách so với xếp hạng của **người chơi giỏi**. Nếu w₁ *là* một
bảng tier của người chơi giỏi thì một phần đồng thuận được **tạo ra sẵn**, không phải đo
được. Cực đoan: mời đúng người đã xếp bảng tier đi đánh giá advisor chạy trên bảng tier
của họ — con số sẽ đẹp và hoàn toàn vô nghĩa.

Ba cách xử lý, dùng được cả ba:

1. **Tách người.** Người đánh giá §12.3 phải **không phải** tác giả bảng tier, và tốt nhất
   là không đọc bảng đó. Ghi rõ trong báo cáo ai xếp bảng và ai đánh giá.
2. **Báo cáo phần tăng thêm, không báo cáo mức tuyệt đối.** So `only("base")` với mô hình
   đầy đủ trên **cùng** một bộ người đánh giá. Phần nhiễm vào cả hai vế nên nó triệt tiêu;
   cái còn lại là đóng góp thật của w₂…w₅.
3. **Nói thẳng ra.** Nếu không tách được người, vẫn báo cáo con số nhưng gắn nhãn là
   **giới hạn trên** của mức đồng thuận, không phải ước lượng không thiên lệch.

> Chỉ số vẫn là **Brennan–Prediger S**, không phải Cohen's κ — lý do ở
> [augment-reroll/evaluation.md](../augment-reroll/evaluation.md).

## Không đổi: đối chứng phản thực của chính sách reroll

`src/eval/reroll_ablation.py` đo **chính sách so với chính sách trên cùng một hàm điểm**,
nên nguồn của w₁ không ảnh hưởng tới tính hợp lệ của nó. Bảng tier chỉ làm phân bố `F_S`
sắc nét hơn (đo được: σ bậc gold 0,0546 → 0,0590 khi có bảng tier), và vì `cost_unit:
sigma` nên `c` **tự co giãn theo** — không phải hiệu chỉnh lại tay.

## `ordinal_trust` là một trục ablation, không phải một hằng số

0,65 là một **lựa chọn**, chưa fit trên dữ liệu nào. Nên báo cáo độ nhạy thay vì bảo vệ
một con số:

| `ordinal_trust` | Ý nghĩa |
|---|---|
| 0,0 | w₁ chết — đối chứng dưới, tương đương không có bảng tier |
| 0,35 | giá trị cũ, khi bảng tier còn là phương án dự phòng |
| **0,65** | đang dùng |
| 1,0 | coi ý kiến ngang phép đo — đối chứng trên, **không** dùng để ship |

Đo top-1 agreement và Kendall τ của xếp hạng qua bốn mức này. Nếu kết quả gần như không
đổi thì `ordinal_trust` không quan trọng và nên nói vậy; nếu đổi mạnh thì nó là tham số
nhạy và con số 0,65 phải được biện minh chứ không chỉ được khai báo.

## Điều phải viết trong báo cáo, không được để người đọc tự suy

1. w₁ là **ý kiến có ký tên**, không phải phép đo. `sample_n = 0` ở mọi dòng, và đó là
   giá trị **đúng**.
2. Lý do chọn tiên nghiệm chuyên gia là **không còn nguồn đo được**, không phải nó ưu việt
   hơn. Cách chuẩn để xử lý nhiễu kỹ năng là lọc theo nhóm rank; đường đó đã đóng vì không
   có dữ liệu, chứ không phải vì nó sai.
3. Bảng tier **hết hạn theo bản vá**. `patch` nằm trong provenance; một bảng của 18.1 dùng
   ở 18.3 là một nguồn sai, không phải một nguồn cũ.

## Related

- [overview.md](overview.md) — vì sao đổi sang tiên nghiệm chuyên gia
- [ingestion.md](ingestion.md) — nạp dữ liệu thế nào
- [augment-reroll/evaluation.md](../augment-reroll/evaluation.md) — S vs κ, giới hạn cỡ mẫu
