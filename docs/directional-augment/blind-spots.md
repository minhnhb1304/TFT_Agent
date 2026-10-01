# Blind Spots

Bốn điểm nghẽn kiến trúc chặn việc đánh giá lõi theo hướng. Số đo:
[baseline.md](baseline.md).

## 1. `EconFitScorer` mù hình thái kinh tế

`src/decision/scoring/econ_fit.py` gom toàn bộ vàng, XP và lượt roll vào **một chỉ số vô hướng**
`econ_value` (0–3). Hai lõi cùng `econ_value` nhận điểm **và chuỗi lý do giống từng ký tự**:

```
Prismatic Ticket  econ=2 -> 0.8333  "Giá trị kinh tế 2/3 ở 2-1 — còn 4 màn để sinh lời…"
Rolling For Days  econ=2 -> 0.8333  (giống từng ký tự)
Epic Rolldown     econ=2 -> 0.8333  (giống)
```

Thang này còn **bão hoà**: 75/254 lõi ở mức 3, 39 ở mức 2 → **114 lõi (45%)** không phân biệt
được nhau bằng thành phần này.

> ⚠️ Đính chính so với bản đầu: ví dụ *"lõi XP và lõi reroll cùng `econ_value = 2`"* **sai**. Đo
> thật: `Level Up!` = 3, `Prismatic Ticket` = 2 — chúng **không** hoà. Nhóm hoà thật là
> **reroll vs gold** ([baseline.md](baseline.md)).

## 2. Mù bắt đầu từ tầng FEATURE, không phải tầng scorer

Đây là điểm nghẽn bản đầu bỏ sót, và nó làm [Giải pháp 2](architecture.md) vô hiệu nếu không sửa
trước.

`AugmentFeature` **đã có** trường `category` với sáu giá trị, trong đó có `reroll`. Nhưng bảng đã
lưu bị tầng LLM ghi đè (`extraction_method` = `llm:gemini-3.5-flash-lite` trên **175/254** dòng):

```
Lõi có từ khoá reroll trong `desc` CDragon : 20
  còn giữ category == "reroll"             :  7
  MẤT nhãn reroll                          : 13
  trong số mất, do LLM ghi đè              : 13/13   ← 100%
```

Mười ba lõi mất nhãn, gồm đúng những ví dụ mà research EN nêu là reroll-econ kinh điển:
`Trade Sector` · `Trade Sector+` · `Patience Is A Virtue` · `Epoch` · `Commerce Core` ·
`Cognitive Overload` · `Shopping Spree` · `Recombobulator` · `Invested+` · `Invested++` ·
`Crafted Crafting` (→ item) · `Nesting Dolls` (→ combat).

`extract_category()` kiểm `reroll` **trước tiên** nên nhãn tất định không phụ thuộc trait map —
đây không phải artifact của phép đo.

**Đây là cùng một lớp lỗi dự án đã chẩn đoán một lần rồi.** `dev_log` §4 đã rút ra nguyên tắc:
*"LLM chỉ được dùng cho phần phán đoán đọc từ văn bản; phần định danh luôn lấy từ dữ liệu có cấu
trúc."* `category` **là** nhãn suy ra bằng luật từ khoá tất định — thuộc nhóm "định danh". Nguyên
tắc đã viết đúng; chỗ này chưa ai kiểm lại. Hệ quả: phải khoá `category` (và `econ_type` sau này)
khỏi LLM bằng **test**, không bằng quy ước.

## 3. Phá hoà điểm bằng bảng chữ cái — và đây là đường đi chính

`src/decision/augment_advisor.py`:

```python
entries.sort(key=lambda e: (-e.total, e.api_name))
```

Tất định cho test, nhưng **không có căn cứ chiến thuật nào**. Và đây không phải ca biên:
**74–94%** lõi cùng bậc nằm trong một nhóm hoà điểm chính xác, kể cả khi bàn cờ đã phát triển
([baseline.md](baseline.md)).

Vì tie-break tất định, **cùng một lõi sai thắng mọi lần** trong cùng tình huống — đây không phải
nhiễu tự triệt tiêu.

Chẩn đoán chuẩn trong tài liệu: **feature saturation** (arXiv:2609.26977) — ba nguyên nhân là
bão hoà đặc trưng, đặc trưng thô/lượng tử hoá, và thiếu tín hiệu. Cả ba đều đúng ở đây. Đơn thuốc
của tài liệu: tie-break phải **tường minh, công bố và audit được**, không phải im lặng và tuỳ ý.

## 4. `margin.py` im lặng đúng lúc cần nói nhất

Trên nhóm hoà ba chiều ở 2-1 (`Trade Sector` = `Advanced Loan+` = `The Trait Tree+` = **0.5965**):

```
#1 = DA_AdvancedLoanPlus   gap = 0.0   parts = {}
margin.explain(...) -> ''
```

Overlay vẫn hiện `Advanced Loan+` ở vị trí #1, **không lý do, không dấu hiệu nào cho biết đó là
hoà**.

Ngược lại, khi có chênh lệch thì lời giải thích nói **sai bản chất**:

```
1. Level Up!         0.5825   gap=0.025, parts={'econ_fit': 0.025}
2. Prismatic Ticket  0.5575
   -> "Hơn lựa chọn kế chủ yếu nhờ kinh tế (+0.03): Giá trị kinh tế 3/3 ở 2-1…"
```

Advisor đang nói *"nhiều kinh tế hơn thì tốt hơn"*, trong khi khác biệt thật là **khác hướng**:
`Level Up!` đẩy lên fast 8/9, `Prismatic Ticket` đẩy về roll tướng ở cấp thấp.

## 5. Luồng một chiều và nghịch lý con gà — quả trứng

`src/decision/advisor.py` gọi `AugmentAdvisor.rank()` **trước**, `CompSelector.select()` **sau**;
`archetype` nhận diện được **không đi ngược lại**.

Hiện trạng này đúng như bản đầu mô tả. Nhưng cách gỡ thì **không** phải truyền archetype về —
xem [architecture.md](architecture.md): ở 2-1 `CompSelector` tự báo `evidence = 0.000` cho mọi
comp, và nó còn **lệch sẵn theo archetype** với chênh lệch sàn điểm 0.15 > `lock_margin` 0.12.

## Related

- [Overview](overview.md) · [Baseline](baseline.md) · [Architecture](architecture.md)
- [Research synthesis](../../research/260930-directional-augment/synthesis.md) §2
