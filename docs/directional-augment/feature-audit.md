# Feature Audit

Định nghĩa các trường phán đoán của `data/augment_features.json` sau đợt audit 2026-10-05, và
quy ước ghi dấu dòng sửa tay. Mọi quyết định đọc từ mô tả cdragon, không từ tag MetaTFT
([metatft-tag-audit.md](metatft-tag-audit.md) chỉ là tín hiệu chọn dòng để đọc).

## Định nghĩa trường

| Trường | Đo gì | Không tính |
|---|---|---|
| `econ_value` 0–3 | Vàng, XP, reroll, tướng được tặng (kể cả Champion Duplicator), quy ra vàng. Thang theo **tổng**: 1 < 8, 2 = 8–19, 3 ≥ 20 hoặc tăng lãi | Item, component, emblem, anvil, Thief's Gloves, Reforger — thuộc `item_grants` |
| `tempo` | Đo bằng **số vòng đấu**. `scaling`: phần lớn giá trị đến muộn hơn ~3 vòng (mỗi vòng / mỗi stage / mỗi lần lên cấp, cộng dồn vĩnh viễn, mốc xa). `immediate`: phần lớn có ngay hoặc trong ~3 vòng | Cộng dồn **trong một trận** ("mỗi 2 giây") là `immediate`; chỉ số theo board hiện tại cũng vậy |
| `trait_count_reward` | `vertical`: thưởng tăng theo số đồng minh chung trait; `wide`: theo số trait đang bật. Tất định, LLM không sửa | Lõi chỉ **cho** emblem/tướng một trait |
| `category` | Loại chính của lõi, đơn nhãn. Không scorer nào đọc — chỉ demo picker và mock stats | — |

Hoà nửa-nửa trong `tempo` → `immediate` (luật bảo thủ của `extract_tempo`). Hoà thật hiếm: một
lõi trả **mỗi stage đến hết trận** (Hard Commit, Money Hungry, Epoch, Trade Sector) là `scaling`
dù có phần trả ngay.

### Ngoại lệ có chủ ý

| Lõi | Nhãn | Vì sao |
|---|---|---|
| Comeback Story | `immediate` | Mạnh theo **máu đã mất**, không theo số vòng; TempoFit phạt lõi `scaling` khi máu thấp, đúng lúc lõi này mạnh nhất |
| Hard Commit | `trait_count_reward = None` | Cho tướng một trait mỗi stage nhưng thưởng không tăng theo độ sâu. Tín hiệu "commit" định hướng cho nó **chưa có** — xem câu hỏi mở |

## Nhãn `manual-audit`

```
extraction_method = "manual-audit:<truong,...> (from <method goc>)"
vd  "manual-audit:category,econ_value,tempo (from llm:gemini-3.5-flash-lite)"
```

| Quy tắc | Ở đâu |
|---|---|
| Chỉ trường trong `MANUAL_AUDITABLE` (category, carry_type, tempo, econ_value, board_condition) | `parse_manual_audit` |
| Dòng gốc `deterministic-v1`: mọi trường **không** khai trong label phải sinh lại giống hệt | `test_committed_table_is_reproducible` |
| `build_augment_features.py --write` áp lại trường đã audit từ file cũ, `(from ...)` ghi method mới | `keep_manual_audits` |
| Thêm **trường mới** giữ `deterministic-v1`; đổi giá trị luật cũ sinh ra → lên v2, sinh lại cả bảng | `EXTRACTOR_VERSION` |

## Đợt audit 2026-10-05

| Nguồn | Dòng | Trường |
|---|---|---|
| `wf/augment-econ-value` | 27 | `econ_value` (+ `category` ở 11) |
| `wf/augment-tempo-scaling` | 41 | `tempo` |
| Tổng hợp: biến thể cùng cơ chế | 21 | `tempo` 8 · `econ_value` 12 · `category` 4 |
| Tổng (gộp trùng) | 81/254 | — |

Danh sách đầy đủ: `grep manual-audit data/augment_features.json`. Lý do từng dòng nằm trong
commit message của nhánh tương ứng.

## Related

- [metatft-tag-audit.md](metatft-tag-audit.md) — số trước/sau, giới hạn của phép so
- [trait-count-reward.md](trait-count-reward.md) — audit 18 lõi trait
- [baseline.md](baseline.md) — độ suy biến `econ_value`, hoà điểm
- [overview.md](overview.md) — bản đồ tài liệu
