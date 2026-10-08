# Definition

Định nghĩa 6 nhãn của `categories`, luật chọn nhãn chính, `carry_type`, `frontline` và các bất
biến test phải giữ. Mọi quyết định đọc từ **mô tả cdragon** (`data/cdragon_cache/en_us.json`),
không từ tag MetaTFT. Bản chốt 2026-10-05.

## Sáu nhãn

| Nhãn | Gán khi lõi… | Không gán khi |
|---|---|---|
| `econ` | cho vàng, XP, tướng (quy ra vàng), tăng lãi. **Bắt buộc** khi `econ_value > 0` | Chỉ cho item/đe/emblem |
| `reroll` | cho lượt đổi shop miễn phí, giảm giá roll, tăng giá trị shop. Nhãn **riêng** tới khi có `econ_type` (Q2) | Chỉ "đổi lõi" (augment reroll), vì đó không phải shop |
| `item` | cho mảnh, đồ hoàn chỉnh, đe, emblem, Artifact, Radiant. **Bắt buộc** khi `item_grants ≠ ∅` | Chỉ sửa đồ đang có mà không cho thêm (Reforger đơn lẻ) |
| `trait` | **liên quan đến tộc hệ**: cho ấn (kể cả ấn ngẫu nhiên), cho tướng một tộc cụ thể, hoặc thưởng theo độ sâu/rộng tộc hệ. **Bắt buộc** khi `trait_affinity ≠ ∅`, `trait_count_reward` khác `None`, hoặc `item_grants` có `Emblem` | Ấn ngẫu nhiên vẫn để `trait_affinity` **rỗng**: trường đó chỉ chứa tộc cụ thể, điền bừa thì BoardFit phạt sai |
| `combat` | cho chỉ số / hiệu ứng **trong trận** (máu, sát thương, tốc đánh, khiên, choáng…) | Chỉ số đến từ món đồ được tặng: phần đó đã là `item` |
| `utility` | làm việc khác: máu người chơi, vị trí, thông tin, thao tác bàn | Lõi đã có nhãn khác: `utility` **chỉ đi một mình** |

Trần **3 nhãn** (Q1, `MAX_CATEGORIES`).

## Nhãn chính (`categories[0]` = `category`)

Nhãn chính là **phần lớn giá trị** của lõi, với người chơi ở thời điểm chọn. Hoà thì lấy theo
thứ tự `reroll > econ > item > trait > combat > utility` (thứ tự của `extract_category`). Cách
này giữ `category` cũ cho mọi lõi không được duyệt lại.

## Ngưỡng "đáng kể" cho nhãn phụ (Q3)

Gán nhãn phụ chỉ khi phần đó là **một cơ chế được nêu rõ** trong mô tả và có **giá trị độc lập**:
bỏ phần chính đi, phần phụ vẫn khiến người chơi cân nhắc lõi này. Nhãn bắt buộc (bảng trên) luôn
được gán, kể cả khi phần đó nhỏ.

| Lõi | Nhãn | Ghi chú |
|---|---|---|
| Big Grab Bag: 3 mảnh + 2 vàng + Reforger | `item, econ` | 2 vàng làm `econ_value>0` nên `econ` bắt buộc |
| We Stick Together: emblem + đe đồ + tốc đánh | `item, trait, combat` | Emblem ngẫu nhiên nhưng có thưởng theo trait chung |
| Iron Assets: đe mảnh + 3 vàng | `item, econ` | |
| Sweet Treats: đe Artifact + máu theo số đồ | `item, combat` | |
| Ascension: 35% khuếch đại sát thương | `combat` | Một nhãn là đủ |

## `carry_type`: AD | AP | both | none

Lõi phục vụ carry **sát thương** nào. `tank` không còn là giá trị hợp lệ: đội nào cũng cần tank,
nên đó không phải hướng carry.

| Giá trị | Khi |
|---|---|
| `AD` / `AP` | Lõi buff rõ một phía chỉ số (sát thương vật lý, tốc đánh, chí mạng / sức mạnh phép, năng lượng) |
| `both` | Phục vụ **rõ** cả AD lẫn AP: có chỉ số cả hai phía, hoặc buff "carry / tướng mạnh nhất" bất kể loại |
| `none` | Buff chung cả đội, lõi kinh tế/trang bị không định hướng, và lõi **chống chịu** |

## `frontline`: bool

`true` khi giá trị lõi **chủ yếu** là chống chịu: máu, giáp, kháng phép, khiên, hồi máu, giảm
sát thương. Độc lập với `carry_type` (lõi chống chịu thường là `carry_type = none`).

Dữ liệu cũ `carry_type = "tank"` được chuyển thành `none` + `frontline = true` tại một chỗ
(`AugmentFeature.__post_init__`); entry duyệt tay cũ được chuyển khi trang duyệt đọc lên.

## Bất biến (`check_feature`, test khoá)

`src/knowledge/augment_features.py::check_feature(f)` trả danh sách lỗi, rỗng = hợp lệ:

| Bất biến | |
|---|---|
| 1–3 nhãn, không trùng, nhãn thuộc `CATEGORIES` | Q1 |
| `category == categories[0]` | D1 |
| `utility` đi một mình | |
| `econ_value > 0` ⇒ `econ`; `item_grants ≠ ∅` ⇒ `item`; `trait_affinity` / `trait_count_reward` / `Emblem` trong `item_grants` ⇒ `trait` | D3 |
| `carry_type ∈ CARRY_TYPES` | D6 |

Chiều ngược (`econ` ∈ cats ⇒ `econ_value > 0`) **không** bắt buộc: `reroll` thuần có
`econ_value` theo định nghĩa riêng, xem [feature-audit.md](../directional-augment/feature-audit.md).
Trang duyệt gọi cùng hàm này trước khi lưu, nên nhãn tay vi phạm bị chặn ngay.

## Related

- [overview.md](overview.md): vì sao, quyết định D1–D7, câu hỏi đã chốt
- [phases.md](phases.md): các pha
- [../directional-augment/feature-audit.md](../directional-augment/feature-audit.md): định nghĩa `econ_value`, `tempo` (xét tại lượt chào, `offer_rounds`)
