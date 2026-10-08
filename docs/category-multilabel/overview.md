# Category Multi-label

Kế hoạch đổi `category` của lõi từ **một nhãn** sang **1–3 nhãn**, lập 2026-10-05. Cùng đợt đổi
schema: `carry_type` bỏ giá trị `tank`, thêm `both`, và thêm trường `frontline`. Trạng thái:
**đang triển khai** (Q1–Q4 đã chốt 2026-10-05).

## Vấn đề

Một lõi thường làm nhiều việc. Big Grab Bag cho 3 mảnh **và** 2 vàng; We Stick Together cho
emblem, đe đồ **và** tốc đánh. Một nhãn buộc phải bỏ đi phần còn lại, nên bảng feature mô tả
thiếu lõi, và phép so với MetaTFT (vốn 1–3 tag/lõi: 122 lõi 1 tag · 106 lõi 2 · 25 lõi 3) chỉ so
được "nhãn ta có nằm trong tag họ không".

`carry_type = tank` trộn hai trục: hướng carry sát thương (AD/AP) và độ lì. Đội nào cũng cần
tank, nên "tank" không phải một hướng carry; lõi buff cả AD lẫn AP thì không có giá trị nào đúng.

## Sự thật phải nói trước

**Hôm nay không scorer nào đọc `category`.** Sức mạnh lõi đi vào điểm qua các trường khác:

| Phần sức mạnh | Trường scorer đọc |
|---|---|
| Kinh tế | `econ_value` → EconFit |
| Trang bị | `item_grants` → ItemFit |
| Tộc hệ | `trait_affinity`, `trait_count_reward` |
| Thời điểm | `tempo` → TempoFit |
| Kiểu carry | `carry_type` |

Đọc runtime duy nhất là `_pick_demo_augments` (`src/decision/augment_advisor.py`). Vậy
multi-label **tự nó không đổi một điểm số nào**. Nó có giá trị ở ba chỗ:

1. **Mô tả đúng** lõi: dữ liệu thô cho luận văn (đóng góp #1: trích feature).
2. **Đo đúng**: so tập-với-tập với MetaTFT (Jaccard, P/R/F1 từng nhãn) và với nhãn tay.
3. **Giải thích**: overlay nói "lõi này: kinh tế + trang bị" thay vì một chữ.

Đưa `categories` vào **chấm điểm** là việc riêng, có cổng quyết định
([phases.md](phases.md) P6): các trường ở bảng trên đã chấm từng phần, cộng thêm điểm theo nhãn
rất dễ **đếm hai lần** cùng một phần sức mạnh.

## Quyết định thiết kế (đã chốt)

| # | Quyết định | Lý do |
|---|---|---|
| D1 | Thêm `categories: list[str]`, **giữ** `category` = `categories[0]` (nhãn chính) | Các chỗ đọc `category` không vỡ. Bảng lên `deterministic-v2` vì `carry_type` đổi giá trị (D6) |
| D2 | Giữ 6 nhãn hiện có, không thêm `scaling` | `scaling` đã là `tempo`; hai trường nói cùng một điều sẽ lệch nhau |
| D3 | Nhãn có nền dữ liệu là **bất biến** với trường cấu trúc (`check_feature`) | Không để hai nguồn mâu thuẫn; test và trang duyệt bắt được ngay |
| D4 | LLM **không** được ghi `categories` | Bài học blind-spots §2: 13/13 lõi mất nhãn `reroll` đều do LLM ghi đè |
| D5 | Ground truth là **nhãn tay** qua trang duyệt; MetaTFT chỉ là tín hiệu | Như [metatft-tag-audit.md](../directional-augment/metatft-tag-audit.md) |
| D6 | `carry_type` ∈ `AD \| AP \| both \| none`; dữ liệu cũ `tank` → `none` + `frontline = true` | Đổi một lần, cùng đợt với `categories`, để bạn chỉ phải duyệt tay **một lần** |
| D7 | Thêm `frontline: bool` | Độ lì là trục riêng, không phải hướng carry |

Định nghĩa từng nhãn, `carry_type`, `frontline` và luật chọn nhãn chính: [definition.md](definition.md).

## Câu hỏi đã chốt

| # | Câu hỏi | Chốt |
|---|---|---|
| Q1 | Trần 3 nhãn/lõi? | **Có** (`MAX_CATEGORIES = 3`). Khớp MetaTFT |
| Q2 | `reroll` riêng hay gộp vào `econ`? | **Giữ riêng** tới khi có `econ_type` (next-steps #2), rồi quyết lại |
| Q3 | Nhãn phụ cần "đáng kể" tới mức nào? | Cơ chế **nêu rõ** trong mô tả, có giá trị **độc lập**. Ngưỡng ở [definition.md](definition.md) |
| Q4 | Làm trước hay sau directional (#3)? | **P1–P5 trước** directional; P6 để sau |

## Related

- [definition.md](definition.md): định nghĩa nhãn, carry, frontline, nhãn chính, bất biến
- [phases.md](phases.md): các pha, file đụng tới, tiêu chí xong
- [../directional-augment/feature-audit.md](../directional-augment/feature-audit.md): định nghĩa các trường khác, nhãn `manual-audit`
- [../directional-augment/blind-spots.md](../directional-augment/blind-spots.md): §2, LLM ghi đè nhãn
- [../next-steps.md](../next-steps.md): bảng việc
