# Directional Augment Evaluation

Đánh giá lõi theo **hướng đi mà nó mở ra**, không theo độ khớp với bàn cờ tạm thời. Soạn
2026-09-30, thẩm định bằng 5 báo cáo research cùng ngày
([synthesis](../../research/260930-directional-augment/synthesis.md)).

> **Trạng thái: TÍNH NĂNG BẮT BUỘC.** Bản đầu xếp phần này vào chương *Hạn chế & Hướng phát
> triển*. Quyết định lại 2026-09-30: đây là tính năng phải có, và nó **phát biểu lại đóng góp
> #3** chứ không thêm đóng góp thứ năm — xem [contribution.md](contribution.md).

## Vấn đề

Ở chặng **2-1** và **3-2**, người chơi chưa chốt bài: bàn cờ chỉ là tướng 1–2 sao giữ máu tạm.
Giá trị của một lõi lúc đó không nằm ở việc nó cộng bao nhiêu chỉ số cho bàn cờ **hiện tại**, mà
ở việc nó mở ra hay khoá lại những hướng đi **sau đó**.

Trường hợp điển hình — hai lõi kinh tế rẽ ra hai trường phái đối nghịch:

| Họ lõi | Cơ chế | Hệ quả chiến thuật |
|---|---|---|
| **Reroll-econ** | Thưởng tiền roll, một số lõi **chặn hẳn việc mua XP** (vd `Wise Spending`) | Dừng ở cấp 5/6/7, cạn tiền tìm tướng 3 sao giá 1–3 |
| **XP-econ** | Cho XP trực tiếp (vd `Epoch`, `Upward Mobility`) | Giữ máu, fast 8/9, roll tướng 4–5 giá 2 sao |
| **Gold thuần** | Chỉ cộng vàng | **Trung tính về hướng** — họ thứ ba, không phải nhánh của hai họ trên |

Cơ chế này **đã xác nhận được** trong nguồn EN. Điều chưa ai viết ra là **phân loại nó thành một
taxonomy** — đó là chỗ đóng góp của đồ án nằm ([contribution.md](contribution.md)).

## Một đính chính về cách phát biểu

Bản đầu viết *"lõi là la bàn định hướng toàn bộ trận đấu"*. Research EN **không ủng hộ** cách
phát biểu mạnh đó. Đồng thuận hiện hành (tftsense.gg, Set 18) là **board-context-first**:

```
Bàn cờ mạnh   → lõi trang bị (mặc định)
Bàn cờ yếu    → lõi kinh tế
Chưa rõ hướng → lõi định hướng (direction augment)
```

Và tft.ninja phát biểu nguyên tắc *keep options open* gần nguyên văn: *"một lựa chọn hơi yếu hơn
nhưng chạy được với ba đội hình thường tốt hơn một lựa chọn hơi mạnh hơn mà chỉ chạy được nếu
đúng một carry xuất hiện"* — kèm điều kiện đảo: *"trừ khi một lõi comp-specific mạnh đến mức
đáng để chốt hướng trước khi có thông tin gì."*

Nên phát biểu đúng là **"keep options open vs current-fit"**, không phải "lõi dẫn bài". Mortdog
(Set 16) còn ghi Riot **chủ ý giảm** số lõi ép hướng ở 2-1.

Luận điểm cốt lõi không đổi: hàm điểm hiện tại chỉ đo *current-fit*, và không có chỗ nào đo
*options open*.

## Bản đồ tài liệu

| File | Nội dung |
|---|---|
| [blind-spots.md](blind-spots.md) | Ba điểm nghẽn kiến trúc, và điểm nghẽn thứ tư ở tầng feature |
| [baseline.md](baseline.md) | Số "TRƯỚC" — chốt tại `347f5d1`, có script tái lập |
| [architecture.md](architecture.md) | Ba giải pháp sau thẩm định + ràng buộc ablation |
| [explainability.md](explainability.md) | Giải thích rẽ nhánh, và hai cảnh báo bắt buộc |
| [contribution.md](contribution.md) | Khung đóng góp luận văn, thuật ngữ, novelty |
| [centering-fix.md](centering-fix.md) | **Bước 1** — lỗi centering `CompSelector`: đo, ba phương án, blast radius |
| [review-findings.md](review-findings.md) | 11 chỗ research yêu cầu sửa — trạng thái từng chỗ |

## Related

- [Research synthesis](../../research/260930-directional-augment/synthesis.md) — thẩm định đầy đủ
- [Augment reroll](../augment-reroll/overview.md) — chính sách dừng tối ưu trên cùng hàm điểm
- [Dataset split](../playtest-fixes/dataset-split.md) — tập held-out để đo delta
- SPEC §3.5.2 (Comp Selection) · §3.5.4 (Augment Scoring) · §12.4 (Ablation)
