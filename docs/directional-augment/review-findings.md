# Review Findings

Mười một chỗ mà [research synthesis](../../research/260930-directional-augment/synthesis.md) §3 yêu
cầu sửa so với bản đầu của tài liệu (`docs/directional-augment-evaluation.md`, 2026-09-30), kèm
trạng thái.

Giữ file này để **không mất dấu** phán quyết nào — và để biết chỗ nào là quyết định nội dung còn
chờ người viết luận văn.

| # | Chỗ | Yêu cầu | Trạng thái |
|---|---|---|---|
| 1 | §1 ví dụ "hai lõi kinh tế cùng điểm" XP vs Reroll | Thay bằng nhóm hoà thật, tái lập được: `Trade Sector` = `Advanced Loan+` = `The Trait Tree+` = 0,5965 ở 2-1 | ✅ [baseline.md](baseline.md) |
| 2 | §2.1 "cả hai lõi XP và Reroll cùng `econ_value = 2`" | Sai. Đo thật `Level Up!` = 3, `Prismatic Ticket` = 2. Giữ luận điểm, đổi số | ✅ [blind-spots.md](blind-spots.md) §1 |
| 3 | §2.1 quy trách nhiệm cho `EconFitScorer` | Thêm: mù bắt đầu ở tầng feature — LLM bóp `reroll` 20 → 7, đổi `category` 85/254 lõi | ✅ [blind-spots.md](blind-spots.md) §2, đo lại **13/13 do LLM** |
| 4 | §2.2 "giải pháp kỹ thuật … ca hoà điểm" | Nêu rõ đây là **đường đi chính**: 74–94% lõi cùng bậc nằm trong nhóm hoà, cả khi board đã phát triển | ✅ [baseline.md](baseline.md) |
| 5 | §2.3 thiếu `margin.py` | Bổ sung: `margin.explain()` trả **chuỗi rỗng** đúng trên ca hoà | ✅ [blind-spots.md](blind-spots.md) §4, xác minh trực tiếp |
| 6 | §3.2 "Directional Potential" | Ghi rõ là thuật ngữ **nội bộ đồ án**; và đếm số plan là proxy có lỗi đã biết (empowerment) | ✅ [contribution.md](contribution.md) |
| 7 | §3.3 "Anchor Augment (Lõi neo bài)" | Thuật ngữ này **không tồn tại** trong nguồn nào. Dùng *direction augment* / *comp-defining* / *flex vs forced* | ✅ bảng thuật ngữ ở [contribution.md](contribution.md) |
| 8 | §4.1 Giải pháp 1 | Viết lại — bác bỏ như bản đầu, kèm 4 bước gỡ theo chi phí tăng dần | ✅ [architecture.md](architecture.md) |
| 9 | §4.2 `econ_type` enum | Đổi sang **multi-label** + nói rõ phải sửa tầng feature trước | ✅ [architecture.md](architecture.md) |
| 10 | §4.3 | Thêm **hai cảnh báo bắt buộc**: automation bias và LLM unfaithfulness | ✅ [explainability.md](explainability.md) |
| 11 | Toàn doc | Thiếu `## Related` (yêu cầu của `rules/documentation.md`) | ✅ mọi file trong thư mục này đều có |

## Còn là quyết định nội dung, chưa chốt

Ba chỗ research nêu nhưng thuộc phần lập luận của người viết luận văn, không phải sự thật kiểm
được:

| | Câu hỏi còn mở |
|---|---|
| Cách phát biểu §1 | [overview.md](overview.md) đã đổi sang *"keep options open vs current-fit"*. Nếu muốn giữ hình ảnh "la bàn" thì phải hạ mức xuống — EN nghiêng về **bác bỏ** cơ chế "lõi dẫn bài", và Mortdog ghi Riot chủ ý giảm lõi ép hướng ở 2-1 |
| Có dùng khung *Evaluative AI* cho ca hoà không | [explainability.md](explainability.md) nêu như lựa chọn. Nó đổi cả hình dáng overlay (bằng chứng ủng hộ/phản đối thay vì một khuyến nghị), nên là quyết định sản phẩm |
| Dẫn `tft.ninja` hay không | Nguồn mạnh nhất cho nguyên tắc optionality, nhưng không có nhãn set và ngày cập nhật **trước** ngày Set 18 live. Phải kiểm độ hiện hành trước |

## Phần chưa giải quyết được (giới hạn của research)

| Vấn đề | Tình trạng |
|---|---|
| Nguồn ZH giàu nhất không truy cập được | 知乎专栏 403 (5 lần), NGA không index, một cột Bilibili trống → phán quyết ZH là *"chưa xác nhận"*, không phải *"đã bác bỏ"* |
| Không pro nào đứng tên | Mọi nguồn xác nhận đều là tác giả guide-site |
| Dữ liệu augment×comp công khai | **Không tồn tại** cho Set 18 → số hạng `econ_type` buộc phải là prior đặt tay, không fit được |
| Nguồn ggclan bị gán nhãn "Set 14" | **Sai nhãn** — SPEC §8 xác nhận Set 18 = "Enchanted Wilds" nên nguồn đó có thể là Set 18. Không đổi kết luận, nhưng làm phản-luận-điểm *"force sớm khi meta chưa giải"* đáng cân nhắc hơn |
| `hexcall` tự nhận dùng "real match data" | Mâu thuẫn với phát hiện đã chốt là Riot bỏ trường `augments`. Đáng theo dõi, chưa xác minh được |

## Related

- [Overview](overview.md) · [Architecture](architecture.md) · [Contribution](contribution.md)
- [Research synthesis](../../research/260930-directional-augment/synthesis.md)
