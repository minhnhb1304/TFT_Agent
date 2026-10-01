# Branching Explainability

Giải thích *vì sao thẻ này chứ không phải thẻ kia*, khi khác biệt thật là **khác hướng** chứ không
phải khác độ mạnh. Giải pháp 3 của [architecture.md](architecture.md).

## Mục tiêu

Thay vì:

> *"Hơn lựa chọn kế chủ yếu nhờ kinh tế (+0.03): Giá trị kinh tế 3/3 ở 2-1…"*

thì nói:

> *"Chọn [lõi reroll]: định hướng chốt bài reroll cấp 6 (đội hình đề xuất: X, Y)."*
> *"Chọn [lõi XP]: định hướng fast 8 tại 4-2 (đội hình đề xuất: Z)."*

## Nền lý thuyết — vững hơn bản đầu tưởng

| Nguồn | Nội dung dùng được |
|---|---|
| **Miller 2017/2019**, arXiv:1706.07269 (qua Hilton 1990, Lipton 1990) | Giải thích vốn là **fact-vs-foil**. Nêu **nguyên nhân khác biệt** mạnh hơn nêu xác suất: *"referring to probabilities… is not as effective as referring to causes."* Đúng điều `margin.py` đang làm — và đang bỏ lửng trên ca hoà |
| **Lipton's Difference Condition** | Nêu *"một nguyên nhân của P và sự vắng mặt của nó trong lịch sử của not-Q"*. Và giải thích tương phản **dễ dựng hơn** giải thích đầy đủ, không khó hơn |
| **Sukkerd, Simmons & Garlan 2020**, arXiv:2004.12960 | Template verbalization khớp gần 1:1 với thiết kế trên, **đã kiểm định thực nghiệm: cải thiện 3,8× độ đúng** của người dùng so với baseline chỉ hiển thị kế hoạch |
| **Temporal Policy Decomposition / EFO**, arXiv:2501.03902 | Giải thích một hành động bằng **quỹ đạo kết quả tương lai** thay vì mô tả trạng thái hiện tại — đúng cú chuyển từ *"board_fit = 0.7"* sang *"cam kết bạn vào X"* |
| **RADAR-X**, arXiv:2011.09644 | Ghép giải thích tương phản với **một kế hoạch thay thế được đề xuất** — cơ sở cho việc kèm "đội hình đề xuất" |

Template của Sukkerd et al., dịch sang bài toán này:

```
Tôi có thể [cải thiện các mặt này, mức này] bằng [lựa chọn thay thế].
Nhưng làm vậy sẽ [làm xấu các mặt khác, mức này].
→ đã không chọn vì [cái được] không đáng [cái mất].
```

## Hai cảnh báo BẮT BUỘC

### 1. Lời giải thích không làm giảm automation bias — có thể làm tăng

**Vered, Livni, Howe, Miller & Sonenberg 2023**, *Artificial Intelligence* 322:103952: giải thích,
kể cả giải thích tương phản viết tốt, **"did not reduce automation bias… and sometimes increased
it"** — văn trôi chảy được đọc như **tín hiệu năng lực**, bất kể nội dung đúng hay sai.

Hệ quả trực tiếp: dán một câu *"Chọn A: định hướng reroll cấp 6…"* lên một chênh lệch **0,000**
làm tình hình **xấu hơn** hiện trạng im lặng.

Nên: **dòng đầu tiên phải nói rõ đây là hoà.** Không phải dòng thứ hai.

Lý do dòng đầu: **Swaroop et al. 2024** (IUI'24, arXiv:2306.07458) — dưới áp lực thời gian, người
dùng quyết nhanh hơn và dựa **gần như hoàn toàn** vào dòng khuyến nghị đầu, không xử lý phần chi
tiết. Màn chọn lõi có đồng hồ ~30 giây, nên phần chi tiết mở rộng gần như chắc chắn không được
đọc. Tài liệu CDS y khoa cùng kết luận: khuyến nghị + **một** lý do + các lựa chọn hành động ở
trên, chi tiết đẩy xuống progressive disclosure.

### 2. LLM hợp lý mà không faithful

**Agarwal, Tanneru & Lakkaraju 2024**, arXiv:2402.04614 + **Lyu et al. 2024**, *Computational
Linguistics*: post-hoc rationalization của LLM *"ưu tiên plausibility hơn faithfulness"*, và **có
thể bịa dữ kiện hỗ trợ** để biện minh cho một kết luận đã đạt được bằng cách khác.

Bản đầu gợi ý dùng `LlmReasoner` cho việc này. Nếu làm, phải giới hạn ở **điền template trên dữ
kiện đã tính sẵn** (comp, cấp, margin), **không sinh văn tự do**.

> Kiến trúc hiện tại đã cấm LLM đổi thứ hạng (`assert_order_preserved`). Cảnh báo này nói về **nội
> dung câu chữ** — một lớp khác, hiện chưa có rào nào.

## Khung trung thực hơn cho ca hoà

**Miller 2023** (FAccT'23, arXiv:2302.12389), *Evaluative AI*: thay vì một khuyến nghị tự tin duy
nhất kèm biện minh, **trình bày bằng chứng ủng hộ/phản đối cho từng lựa chọn** và để người dùng
phán. Miller lập luận XAI kiểu recommendation-driven có thể *"counter-productive to better human
decision making."*

Với 10,9% ca hoà tuyệt đối và 28,6% ca gần hoà ([baseline.md](baseline.md)), đây là khung đáng cân
nhắc cho **đúng nhóm ca đó**, không nhất thiết cho mọi ca.

Kèm theo — **Google PAIR**: hiển thị rằng dự đoán có thể sai làm giảm tin tưởng ngắn hạn nhưng xây
được sự tin cậy dài hạn; khuyến nghị đánh đổi đó. Và đồng thuận chung: **tránh điểm số thập phân
giả chính xác**, dùng dải định tính.

## Ràng buộc triển khai

| | |
|---|---|
| Dòng đầu mang tín hiệu trung thực | Hoà → nói "ngang điểm" ngay dòng đầu, không ở chi tiết |
| Không con số thập phân trên overlay | Dải định tính; con số giữ trong `detail` cho `ScenarioLogger` |
| LLM chỉ điền template | Dữ kiện tính trước, không sinh văn tự do |
| Tắt được bằng config | Cùng lý do với mọi thứ khác ở [architecture.md](architecture.md) |

Chỉ số đã có để đo: `dup_reasons`, `dup_chars`, `empty_slots`, `edge_coverage` trong
[eval-dataset.md](../playtest-fixes/eval-dataset.md). `empty_slots` bắt đúng ca
`margin.explain() -> ''`.

## Related

- [Overview](overview.md) · [Architecture](architecture.md) · [Baseline](baseline.md)
- [Augment commentary](../playtest-fixes/augment-commentary.md) — mốc M4, chỉ số câu lý do
- [Research synthesis](../../research/260930-directional-augment/synthesis.md) §4.3
