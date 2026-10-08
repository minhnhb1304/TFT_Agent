# Phases

Các pha, theo thứ tự. Mỗi pha một commit (hoặc một nhánh nhỏ) và có tiêu chí kiểm được.
P1–P3 làm cùng một đợt (2026-10-05) để schema chỉ đổi **một lần**: `categories`, `carry_type`
AD/AP/both/none, `frontline`. P4 là bạn duyệt tay. P5 đo. P6 là cổng quyết định. Theo Q4, P1–P5
làm **trước** directional (#3).

| Pha | Trạng thái |
|---|---|
| P0 chốt định nghĩa | Xong 2026-10-05 |
| P1–P3 schema, trích, trang duyệt | Đang triển khai |
| P4–P6 | Chưa bắt đầu |

## P0: Chốt định nghĩa (xong)

Q1–Q4 chốt ở [overview.md](overview.md); nhãn, `carry_type`, `frontline` ở
[definition.md](definition.md); dòng định nghĩa đã vào `feature-audit.md`.

## P1: Schema, không đổi hành vi

| File | Thay đổi |
|---|---|
| `src/knowledge/augment_features.py` | `categories`, `frontline`; `CARRY_TYPES` bỏ `tank` thêm `both`; `__post_init__` chuyển dữ liệu cũ; `check_feature()`; `MANUAL_AUDITABLE` thêm `categories`, `frontline` |
| `scripts/build_augment_features.py` | `categories` **không** vào `LLM_REFINABLE` (D4); `keep_manual_audits` giữ cả list; `summarize()` đếm theo từng nhãn |
| `tests/test_augment_features.py` | `check_feature` trên cả bảng; LLM không ghi được `categories`; chuyển đổi `tank` |

Xong khi: `pytest` xanh, `data/augment_features.json` sinh lại có `categories`, `frontline`, không
còn `tank`, `test_committed_table_is_reproducible` vẫn xanh.

## P2: Trích tất định

| Việc | Chi tiết |
|---|---|
| `extract_categories` | Nhãn chính = `category` hiện có; thêm nhãn bắt buộc theo D3; thêm `combat` nếu có từ khoá chỉ số trận và chưa đủ 3 |
| `carry_type` / `frontline` | Tín hiệu chống chịu đi vào `frontline`, không vào `carry_type` |

Xong khi: 0 dòng vi phạm `check_feature`, báo số lõi 1/2/3 nhãn.

## P3: Trang duyệt (`scripts/review_augment_features.py` + `.html`)

| Việc | Đã làm |
|---|---|
| Nhãn | 6 ô tick + nút ★ chọn nhãn chính; `carry_type` AD/AP/both/none; ô tick `frontline` |
| Lọc | "có nhãn X" (bất kỳ vị trí); trạng thái "Cần xem lại" |
| Kiểm tra | Server dựng `AugmentFeature` từ nhãn gốc + sửa, gọi `check_feature`, trả lỗi 400 cho trang |
| Dữ liệu duyệt cũ | Chuyển **khi đọc**, không ghi đè file: `fix.category` → `categories=[…]`, `tank` → `none` + `frontline`, gắn cờ "cần xem lại". Entry chỉ đổi shape khi bạn lưu lại |

## P4: Duyệt tay 254 lõi (bạn)

Ưu tiên: lõi bị gắn "cần xem lại" → lõi MetaTFT ≥2 tag (131 lõi) → lõi `item_grants≠∅` → còn lại.
Kết quả áp vào bảng dưới nhãn `manual-audit:categories,… (from …)`.

## P5: Đo

| Phép đo | So với | Ở đâu |
|---|---|---|
| Jaccard trung bình, P/R/F1 từng nhãn | Nhãn tay (P4), **ground truth** | `scripts/compare_category_labels.py` (mới) |
| Như trên, tách theo `extraction_method` | Nhãn tay | cùng script, đo tầng 1 so với LLM |
| Jaccard, P/R/F1 từng nhãn | Tag MetaTFT, chỉ là tín hiệu | `src/eval/metatft_tags.py`, giữ check cũ trên `category` |

Xong khi: bảng số vào `metatft-tag-audit.md` (mục mới) và một file kết quả cho luận văn.

## P6: Cổng: có đưa `categories` vào chấm điểm không?

**Mặc định là không.** Chỉ mở khi có bằng chứng scorer hiện tại xếp sai **vì thiếu** thông tin
nhãn mà `econ_value`, `item_grants`, `trait_*`, `tempo` chưa mang. Nếu mở thì đặt sau cờ trong
`config/scoring_weights.yaml` (quy tắc ablation) và sau directional (#3).

## Rủi ro

| Rủi ro | Chặn bằng |
|---|---|
| Đếm hai lần sức mạnh nếu vội đưa vào scorer | P6 là cổng, mặc định đóng |
| LLM hoặc bước build ghi đè nhãn tay | D4 + `keep_manual_audits` + test |
| Nhãn phụ tuỳ hứng, mỗi lần duyệt một kiểu | Ngưỡng ở `definition.md`, gợi ý ngay trên trang duyệt |
| Mất nhãn tay đang làm dở khi đổi schema | Chuyển đổi khi đọc, không ghi đè file review |
| Số "sau" đẹp do chọn mẫu | P5 so với nhãn tay trên **toàn bộ** 254 lõi |

## Related

- [overview.md](overview.md): vấn đề, quyết định, câu hỏi đã chốt
- [definition.md](definition.md): nhãn, carry, frontline, bất biến
- [../directional-augment/metatft-tag-audit.md](../directional-augment/metatft-tag-audit.md): số hiện tại
