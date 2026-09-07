# Cơ Chế: Đã Kiểm Chứng vs Giả Định

Chính sách reroll đứng trên một số phát biểu về cơ chế Set 18. File này ghi rõ cái nào đã
kiểm chứng và cái nào chưa, để không ai phải đoán lại — và để biết cái gì vỡ nếu một giả
định sai.

## Đã kiểm chứng bằng mắt

Nguồn: `data/frames/s7h-jHMpFmQ/augment_select/augment_select_023_011007.png`, chặng 3-2,
VOD giải Set 18 thật.

| Phát biểu | Trạng thái |
|---|---|
| Màn `Chọn Một` có **ba thẻ** | ✅ xác nhận |
| **Ba nút đổi RIÊNG từng thẻ** | ✅ xác nhận — trạng thái phân biệt được bằng hình ảnh |
| Ba thẻ một chặng **cùng một bậc** | ✅ xác nhận tại 3-2 (cả ba đều gold) |
| **Không có bộ đếm số** lượt đổi trên màn hình | ✅ xác nhận |

Điều cuối quan trọng về mặt kiến trúc: số lượt còn lại **không đọc được** từ một khung
hình đơn lẻ theo cách nào khác ngoài phân loại trạng thái nút. Vì thế `RerollState` là
tham số truyền vào, không phải thứ suy ra được.

## Giả định — chưa nguồn công khai nào xác nhận

Nghiên cứu (EN + ZH, 5 agent) **không** xác nhận được ba điều dưới đây từ bất kỳ nguồn sơ
cấp nào. `wiki.leagueoflegends.com` và fandom đều trả 403/402.

### 1. Burn-on-reveal

> Augment đã hiện ra (kể cả bị đổi đi) bị gỡ khỏi pool của người chơi đó ở các chặng sau.
> Biến thể theo chặng (`X`, `X +`, `X ++`) là các thực thể **riêng**; nhưng **chọn** một
> biến thể thì khoá hết các biến thể còn lại.

- **Trạng thái**: chưa xác minh. Nguồn tiếng Trung chỉ xác nhận cho **riêng** hero augment.
- **Cờ**: `reroll_policy.burn_on_reveal` (mặc định `true`)
- **Vỡ cái gì nếu sai**: toàn bộ lập luận về `c`. Nếu thẻ không bị đốt thì `c ≡ 0` ở mọi
  bậc, và chính sách đúng trở thành "vét lượt trừ khi hết đường cải thiện".

### 2. Một lượt đổi mỗi ô, không dồn sang chặng sau

- **Trạng thái**: một phần. Ba nút riêng đã thấy; **số lượt mỗi ô** và **việc dồn** thì chưa.
- **Mâu thuẫn trong nguồn**: mô tả Set 9 nói 1 lượt/ô (3 mỗi chặng); một đoạn tóm tắt
  không rõ nguồn lại nói 1 lượt mỗi chặng.
- **Vỡ cái gì nếu sai**: nếu 3 lượt là một quỹ chung tiêu được hết vào một ô thì T1 vẫn
  đúng nhưng tập mốc khả dĩ đổi, và `run_exhaust`/`run_oracle` phải viết lại.

### 3. Đổi không tốn vàng

- **Trạng thái**: chưa xác minh. Không nguồn nào nói có giá, cũng không nguồn nào nói không.
- **Vỡ cái gì nếu sai**: cần một phép quy đổi vàng → điểm, và `c` không còn thuần là chi
  phí đốt pool.

## Đã xác nhận là ngõ cụt

| Nguồn | Kết quả |
|---|---|
| `tft-match-v1` trường `augments` | Riot đã gỡ ở Set 18 (dev_log #2) |
| `d3.tft.tools` | payload trả `{"singles": []}` trên mọi rank/patch Set 18. Tiêu đề cột HTML là chỗ trống — **phải đo payload, không đọc tiêu đề** |
| datatft.com | bảng tier hardcode trong bundle JS |
| tftacademy.com | robots.txt Disallow |
| Bảng liên hợp bậc theo chặng (`γ`) | chỉ có số Set 16; không có bản Set 18 |

Chi tiết và ngày đo: `config/data_sources.yaml`.

## Hệ quả với báo cáo

Hai điều phải nói rõ, không được để người đọc tự suy:

1. w₁ (**30%** điểm) chạy trên **tiên nghiệm chuyên gia**, không phải số đo — và hiện tại
   còn chưa có cả tiên nghiệm đó, nên `Base` trung tính ở mọi augment. Chính sách reroll
   vẫn hợp lệ vì nó chỉ dùng **thứ tự tương đối** trong cùng một hàm điểm (xem
   [architecture.md](architecture.md)), nhưng ngưỡng **không** quy ra placement được.
   Xem [expert-prior/overview.md](../expert-prior/overview.md).
2. Các con số trong `cost_matrix` là tiên nghiệm do người đặt. Thứ đã kiểm chứng là **thứ
   tự** (prismatic > gold; 4-2 = 0), không phải độ lớn.

## Related

- [depletion-cost.md](depletion-cost.md) — burn-on-reveal dùng để làm gì
- [architecture.md](architecture.md) — vì sao `RerollState` phải truyền vào
- [evaluation.md](evaluation.md) — giới hạn cỡ mẫu
