# Directional Augment Evaluation — Thẩm Định

> **Đối tượng:** `docs/directional-augment-evaluation.md`. Câu hỏi: các luận điểm trong doc
> đúng/sai đến đâu, và cần sửa gì.
> **Phương pháp:** đo trực tiếp trên codebase + dữ liệu Set 18 thật (patch 18.2), đối chiếu với
> 5 báo cáo research (EN/ZH: lý thuyết TFT; EN: prior art; EN: thuật toán; EN: explainability).
> **Ngày:** 2026-09-30.

---

## 1. Phán quyết tóm tắt

| § | Luận điểm của doc | Phán quyết |
|---|---|---|
| 1 | Ở 2-1/3-2 bàn cờ chỉ là tạm, lõi là "la bàn" định hướng cả trận | **Đúng tinh thần, sai cơ chế.** Đồng thuận EN là *board-context-first* + "keep options open", không phải "lõi dẫn bài" |
| 1 | Lõi econ chia hai họ đối nghịch: reroll-econ (dừng cấp, D tướng rẻ) vs XP-econ (fast 8/9) | **Đúng.** Có lõi chặn hẳn việc mua XP. Gold thuần là họ thứ ba trung tính |
| 1 | Ví dụ "hai lõi cùng điểm số" (Trade Sector vs lõi XP) | **Sai chi tiết.** Đo thật: lõi XP `econ_value=3`, lõi reroll `=2` → không hòa. Nhóm hòa thật là **reroll vs gold** |
| 2.1 | `EconFitScorer` mù hình thái kinh tế | **Đúng, và nhẹ hơn thực tế.** Mù bắt đầu từ tầng feature, không phải tầng scorer |
| 2.2 | Phá hòa điểm bằng alphabet thiếu căn cứ chiến thuật | **Đúng, và nhẹ hơn nhiều.** Đây không phải ca biên mà là **đường đi chính (74–94%)** |
| 2.3 | Luồng một chiều `CompSelector` → `AugmentAdvisor`, nghịch lý con gà-quả trứng | **Đúng về hiện trạng, sai về cách gỡ** |
| 3.2 | "Directional Potential" = số đội hình meta mở ra | **Khái niệm có thật nhưng thuật ngữ tự đặt**, và đếm số plan là proxy đã biết là lỗi |
| 4.1 | Giải pháp 1: truyền archetype từ `CompSelector` về `AugmentAdvisor` | **Bác bỏ như đang viết.** Sẽ khuếch đại một bias đang có, ngược đúng ý định |
| 4.2 | Giải pháp 2: thêm `econ_type = "xp" \| "reroll" \| "gold"` | **Đúng hướng, sai hình.** Phải là multi-label, và phải sửa ở tầng feature trước |
| 4.3 | Giải pháp 3: giải thích rẽ nhánh | **Đúng và có nền lý thuyết vững**, nhưng thiếu hai cảnh báo bắt buộc |
| 5 | Đóng góp luận văn: local linear → proactive branching | **Bảo vệ được**, có thuật ngữ chuẩn để dẫn. Nhưng đừng nhận novelty ở chỗ không có |

---

## 2. Đo được trên chính codebase (bằng chứng mạnh nhất của doc)

Tất cả số dưới đây đo bằng `ScoringConfig.load('config/scoring_weights.yaml')` +
`data/augment_features.json` (n=254, Set 18) + `meta_comps` (n=81).

### 2.1 `econ_fit` trả về y hệt nhau khi `econ_value` bằng nhau — đúng như doc nói

```
Prismatic Ticket  econ=2 -> 0.8333  "Giá trị kinh tế 2/3 ở 2-1 — còn 4 màn để sinh lời..."
Rolling For Days  econ=2 -> 0.8333  (chuỗi lý do GIỐNG TỪNG KÝ TỰ)
Epic Rolldown     econ=2 -> 0.8333  (giống)
```

Thang `econ_value` còn **bão hòa**: 75/254 thẻ ở mức 3, 39 ở mức 2 → 114 thẻ (45%) không phân
biệt được nhau bằng thành phần này.

### 2.2 Hòa điểm là đường đi chính, không phải ca biên

Tỉ lệ thẻ nằm trong một nhóm hòa điểm **chính xác** (cùng bậc, cùng trạng thái):

| Trạng thái | tier 1 | tier 2 | tier 3 | nhóm lớn nhất |
|---|---|---|---|---|
| 2-1, board tạm | 74% | **80%** | 72% | 10 |
| 3-2 | 76% | 80% | 75% | 10 |
| 4-2, board trống | 90% | **94%** | 90% | 26 |
| 4-2, **board đã phát triển** (carry 2 sao + 2 đồ, 3 trait bật) | 84% | **83%** | 80% | 23 |

Dòng cuối là dòng quan trọng: hòa điểm **không** biến mất khi bàn cờ đã nói rõ hướng.

Độ phân giải của cả bảng xếp hạng: khoảng cách trung vị giữa hai mức điểm kề nhau chỉ
**0.003–0.0045**, trên tổng độ rộng 0.24–0.30.

**Ví dụ tái lập được** (2-1): `Trade Sector` (reroll-econ) = `Advanced Loan+` (gold) =
`The Trait Tree+` = **0.5965**. Alphabet chọn `Advanced Loan+`. Vì tie-break tất định, **cùng
một thẻ sai thắng mọi lần** trong cùng tình huống — đây không phải nhiễu tự triệt tiêu.

### 2.3 `margin.py` im lặng đúng lúc cần nói nhất

`margin.compare()` trên nhóm hòa ba chiều trên: `gap=0.0000`, `parts={}`, và
`margin.explain()` trả về **chuỗi rỗng**. Overlay vẫn hiện `Advanced Loan+` ở vị trí #1, **không
có lý do, không có dấu hiệu nào cho biết đó là hòa**.

Ngược lại, khi có chênh lệch thì lời giải thích lại nói sai bản chất:

```
1. Level Up!         0.5825      gap=0.025, parts={'econ_fit': 0.025}
2. Prismatic Ticket  0.5575
   -> "Hơn lựa chọn kế chủ yếu nhờ kinh tế (+0.03): Giá trị kinh tế 3/3 ở 2-1..."
```

Advisor đang nói *"nhiều kinh tế hơn thì tốt hơn"*, trong khi khác biệt thật là **khác hướng**:
`Level Up!` đẩy lên fast 8/9, `Prismatic Ticket` đẩy về D tướng ở cấp thấp.

### 2.4 Mù hình thái kinh tế bắt đầu từ tầng FEATURE, không phải tầng scorer

Đây là điều doc bỏ sót, và nó làm Giải pháp 2 vô hiệu nếu không sửa trước.

So `extract_deterministic()` với bản đã lưu trong `data/augment_features.json`
(`llm_refined: true`, gemini-3.5-flash-lite, 175/254 entry bị LLM ghi đè):

| | tất định | đã lưu |
|---|---|---|
| `category == "reroll"` | 20 | **7** |
| `category == "econ"` | 73 | **110** |
| số thẻ LLM đổi `category` | — | 85/254 |
| số thẻ LLM đổi `econ_value` | — | 86/254 |

Các thẻ **mất nhãn `reroll`**, gồm đúng những ví dụ mà research EN nêu là reroll-econ kinh điển:

```
Trade Sector          reroll -> econ    ("Gain a free Shop reroll every round")
Patience Is A Virtue  reroll -> econ
Epoch                 reroll -> econ    econ_value 2 -> 3
Commerce Core         reroll -> econ    econ_value 2 -> 3
Nesting Dolls         reroll -> combat  econ_value 2 -> 0
Crafted Crafting      reroll -> item    econ_value 2 -> 0
```

> ⚠️ Caveat của phép đo: tôi gọi `extract_deterministic(item, {}, tier)` với map trait **rỗng**,
> nên các ca `trait -> combat` (x5) có thể là artifact. Các ca `reroll -> *` thì không: trong
> `extract_category()`, `reroll` được kiểm **trước tiên** nên không phụ thuộc trait.

**`econ_type` không thể là một enum.** Suy từ `desc` CDragon của 131 thẻ có `econ_value > 0`:

| tổ hợp tín hiệu | số thẻ |
|---|---|
| chỉ gold | 67 |
| chỉ xp | 12 |
| chỉ reroll | 5 |
| **xp + gold** | 7 |
| **xp + reroll** | 6 (vd `Epoch`: "gain 4 XP **and** 2 free rerolls") |
| **reroll + gold** | 5 (vd `Trade Sector`) |
| **xp + reroll + gold** | 2 |
| không rõ | 27 |

20/131 thẻ mang ≥2 hình thái. Doc phê phán "Orthogonal Attributes vs. Single Category" ở §3.1
rồi lại kê đúng một single category ở §4.2.

### 2.5 `CompSelector` ở 2-1 không có gì để truyền về — và còn lệch sẵn theo archetype

Đây là lý do Giải pháp 1 **phản tác dụng**.

**(a) Tự nó đã báo là không biết.** Ở 2-1 với board tạm, `evidence = 0.000` cho **mọi** comp
trong 81 comp, và `commitment()` trả về đúng: *"chưa nên chốt — Tín hiệu trên board còn yếu,
thứ hạng mới chỉ dựa vào số liệu meta"*.

**(b) Sàn điểm khác nhau giữa các archetype.** `unit`/`emblem`/`augment` là thang gốc-0
(không tín hiệu = 0.0), còn `item`/`meta` là thang tâm-0.5 (không tín hiệu = 0.5). Vì mỗi
archetype dùng một vector trọng số khác nhau, điểm tổng **không so sánh được với nhau**:

| profile | sàn điểm khi KHÔNG có tín hiệu nào |
|---|---|
| `reroll` | 0.2000 |
| `fast_pivoted` | 0.2250 |
| `fast_holding` | **0.3500** |

Chênh lệch sàn **0.15** — lớn hơn cả `lock_margin: 0.12`, ngưỡng mà hệ thống dùng để tuyên bố
"chốt bài".

**(c) Hậu quả đo được.** Đặt **3 tướng lõi của một comp reroll đã lên 2 sao** ở 2-1 (tín hiệu
reroll gần như không thể rõ hơn):

```
1. Draven AD 9        0.3411  fast9   unit=0.00  evidence=0.000
2. Aphelios Nidalee   0.3312  fast8   unit=0.00  evidence=0.000
3. 6 Juggernaut AD    0.3271  fast8   unit=0.00  evidence=0.000
4. Aphelios Flex      0.3271  fast8   unit=0.00  evidence=0.000
5. Dragon 9           0.3236  fast9   unit=0.00  evidence=0.000
6. Caitlyn Hunters    0.3231  reroll  unit=0.43  evidence=0.286   <-- comp DUY NHAT co bang chung
```

Tách bạch nguyên nhân:

```
Draven AD 9     item 0.4300 x w=0.40 = 0.1720   <- MOT thanh BFSword roi, gan nhu trung tinh
Caitlyn Hunters unit 0.4286 x w=0.40 = 0.1714   <- 3/7 tuong loi DA 2 SAO
```

"Một thanh kiếm lẻ, chẳng nói gì" đang đáng đúng bằng "3 tướng lõi đã 2 sao".

Nghĩa là: nếu truyền archetype của comp #1 về `AugmentAdvisor` ở 2-1, hệ thống sẽ **thưởng lõi
XP và phạt lõi reroll một cách hệ thống, bất kể bàn cờ** — ngược hẳn ý định của doc.

### 2.6 Độ nhạy: một số hạng `econ_type` có đủ lực không?

`w3 = 0.15`. Một điều chỉnh ±0.20 trong không gian thành phần → ±0.030 ở điểm tổng ≈ **7–10 bậc**
ở độ phân giải trung vị 0.003. Vừa đủ để đảo thứ hạng thật (khoảng cách #1 vs #2 trong ví dụ
trên là 0.025) và **dễ quá liều**. Nên cùng biên độ với hai điều chỉnh đã có trong `econ_fit`
(`gold_swing: 0.10`, `loss_streak_bonus: 0.08`) và phải tắt được bằng config để ablation.

### 2.7 Một tín hiệu định hướng KHÔNG vòng lặp, đang có sẵn mà chưa ai dùng

`GameState.augments` (các lõi **đã cầm**) hiện chỉ được `CompSelector.augment_score()` đọc.
**Không scorer nào trong 5 scorer của `AugmentAdvisor` đọc nó.** Nhưng ở 3-2 và 4-2, lõi đã
chọn ở 2-1 chính là tuyên bố kế hoạch rõ nhất, và nó **không tạo vòng lặp** vì nó đã là quá khứ.
Đây là cách vào rẻ hơn và an toàn hơn Giải pháp 1.

---

## 3. Chỗ doc cần sửa

| # | Chỗ | Sửa thành |
|---|---|---|
| 1 | §1 ví dụ "hai lõi kinh tế cùng điểm số" XP vs Reroll | Thay bằng nhóm hòa thật, tái lập được: `Trade Sector` = `Advanced Loan+` = `The Trait Tree+` = 0.5965 ở 2-1 |
| 2 | §2.1 "Cả hai lõi XP và Reroll có cùng `econ_value = 2`" | Sai: đo thật `Level Up!` = 3, `Prismatic Ticket` = 2. Giữ luận điểm, đổi số |
| 3 | §2.1 quy trách nhiệm cho `EconFitScorer` | Thêm: mù bắt đầu ở `augment_features.json` — LLM pass bóp `reroll` 20 → 7, đổi `category` của 85/254 thẻ |
| 4 | §2.2 "giải pháp kỹ thuật ... ca hòa điểm" | Nêu rõ đây là đường đi chính: 74–94% thẻ cùng bậc nằm trong nhóm hòa, cả khi board đã phát triển |
| 5 | §2.3 thiếu mất `margin.py` | Bổ sung: `margin.explain()` trả chuỗi rỗng đúng trên ca hòa, nên người chơi không nhận được gì |
| 6 | §3.2 "Directional Potential" | Ghi rõ đây là thuật ngữ nội bộ của đồ án, không phải vocabulary cộng đồng; và đếm số plan là proxy có lỗi đã biết |
| 7 | §3.3 "Anchor Augment (Lõi neo bài)" | "anchor augment" / "high-commitment augment" **không tồn tại** trong nguồn nào. Dùng "direction augment", "comp-defining augment", "flex vs forced" |
| 8 | §4.1 Giải pháp 1 | Viết lại (xem §4 dưới) |
| 9 | §4.2 `econ_type` enum | Đổi sang multi-label + nói rõ phải sửa tầng feature trước |
| 10 | §4.3 | Thêm hai cảnh báo bắt buộc: automation bias và LLM unfaithfulness |
| 11 | Toàn doc | Thiếu `## Related` (yêu cầu của `rules/documentation.md`) |

---

## 4. Ba giải pháp: thẩm định và phương án thay thế

### Giải pháp 1 — Liên kết hai chiều: **bác bỏ như đang viết**

Ba lý do độc lập:

1. **Không có gì để truyền.** Ở 2-1, `evidence = 0.000` cho mọi comp; `CompSelector` tự nói
   "chưa nên chốt". Truyền về chỉ là truyền một **meta prior**, rồi trộn nó vào `econ_fit` như
   thể đó là tín hiệu bàn cờ.
2. **Truyền về sẽ khuếch đại bias.** Sàn điểm `fast_holding` cao hơn `reroll` 0.15 > `lock_margin`
   0.12 → ở 2-1, comp #1 gần như luôn là fast8/9 → lõi XP luôn được thưởng, lõi reroll luôn bị
   phạt, **bất kể bàn cờ**. Đúng ngược ý định.
3. **Kiến trúc SOTA của bài toán tương đương đã tránh đúng cách này.** DraftFM (draft bot
   foundation-model, 149M lượt pick trong MTG draft — bài toán y hệt: giá trị của thẻ phụ thuộc
   archetype, archetype lộ ra qua các lượt pick) biểu diễn cam kết archetype bằng một
   **embedding liên tục cập nhật mỗi lượt pick**, cố ý **không** có node "archetype classifier
   → feed back vào card scorer". BayesBot/NNetBot cũng mã hoá archetype ngầm qua co-occurrence.

Cách gỡ đúng (theo thứ tự chi phí tăng dần):

| Bước | Nội dung | Vì sao không vòng lặp |
|---|---|---|
| 1 | **Sửa lỗi centering trong `CompSelector`** — đưa `unit`/`emblem`/`augment` về thang tâm-0.5, hoặc chuẩn hoá theo sàn của từng profile | Sửa bug độc lập, phải làm dù có làm gì tiếp hay không |
| 2 | Dùng `state.augments` (lõi ĐÃ cầm) làm tín hiệu kế hoạch cho 3-2/4-2 | Quá khứ, không phụ thuộc đầu ra hiện tại |
| 3 | Dùng **`econ_type` của chính thẻ đó** làm tín hiệu hướng | Đặc trưng nội tại của thẻ, không đọc từ `CompSelector` |
| 4 | Nếu vẫn cần plan: **belief over plans**, `Score(a) = Σ_φ b(φ)·Score(a\|φ)` — không phải argmax của `CompSelector` | Đây là dạng chuẩn (POMDP/BAMDP: latent ẩn + belief), không phải one-pass feedback |

**Cảnh báo về `max` over plans:** "giá trị = trường hợp tốt nhất nếu cam kết theo hướng thẻ này
mạnh nhất" chính là **maximax** — một quy tắc quyết định lạc quan cổ điển đã bị phê phán: nó
thiên vị lựa chọn có upside cao nhưng xác suất thấp và bỏ qua likelihood. Nếu doc muốn dùng
"Directional Potential" theo nghĩa max, phải gọi đúng tên và nói rõ nhược điểm.

### Giải pháp 2 — Phân tách nhánh trong `EconFit`: **đúng hướng, sai hình**

Ba điều chỉnh:

1. **Multi-label, không enum.** 20/131 thẻ mang ≥2 hình thái (§2.4). Dùng ba trường độc lập
   (`econ_xp` / `econ_reroll` / `econ_gold`) hoặc một list — đúng khuôn `trait_affinity` và
   `item_grants` đang dùng.
2. **Sửa tầng feature trước.** Không có ích gì khi thêm `econ_type` vào scorer nếu
   `augment_features.json` đã xoá nhãn `reroll` của `Trade Sector`. Cần: sinh lại bảng với
   `econ_type` trích tất định (không để LLM ghi đè trường này), hoặc thêm test khoá
   `reroll_kw(desc) == True ⇒ econ_reroll == True`.
3. **`level_pace` đang nằm ở `tuning.tempo_fit`, không phải `econ_fit`.** Doc nói chấm
   `econ_type` × `level_pace` mà không nói lấy ở đâu. Chia sẻ tham số giữa hai scorer làm
   ablation khó đọc (§12.4 quy định `tuning` phải giữ nguyên giữa các lần ablation) — nên nhân
   bản có chủ đích và ghi rõ, hoặc đưa lên cấp cao hơn.

Biên độ đề nghị: ±0.08…0.10 trong không gian thành phần, cùng thang với `gold_swing` /
`loss_streak_bonus`, và tắt được bằng config.

### Giải pháp 3 — Giải thích rẽ nhánh: **đúng, có nền lý thuyết, nhưng thiếu hai cảnh báo**

Nền lý thuyết vững hơn doc tưởng:

- **Miller 2017/2019** (arXiv:1706.07269): giải thích vốn là **fact-vs-foil**; nêu nguyên nhân
  khác biệt mạnh hơn nêu xác suất. Chính xác là điều `margin.py` đang làm — và đang bỏ lửng
  trên ca hòa.
- **Sukkerd, Simmons & Garlan 2020** (arXiv:2004.12960), *Tradeoff-Focused Contrastive
  Explanation for MDP Planning*: có sẵn template verbalization khớp gần 1:1 với thiết kế
  "Chọn A: … / Chọn B: …", kèm kết quả cải thiện 3.8x độ đúng của người dùng.

Hai cảnh báo **bắt buộc** phải vào doc:

1. **Vered, Livni, Howe, Miller & Sonenberg 2023**, *Artificial Intelligence* 322:103952: lời
   giải thích **không làm giảm** và **có thể làm tăng** automation bias — văn trôi chảy được đọc
   như tín hiệu năng lực, bất kể đúng sai. Nghĩa là dán một câu "Chọn A: định hướng Reroll cấp
   6…" lên một chênh lệch **0.000** làm tình hình **xấu hơn** hiện trạng im lặng, trừ khi
   **dòng đầu tiên** nói rõ đây là hòa. Dưới áp lực ~30 giây (đồng hồ màn chọn lõi), chỉ dòng
   đầu được đọc — nên tín hiệu trung thực phải nằm ở đó, không nằm ở dòng dưới.
2. **Agarwal, Tanneru & Lakkaraju 2024** (arXiv:2402.04614) + **Lyu et al. 2024** (*Computational
   Linguistics*): post-hoc rationalization của LLM có thể hợp lý mà **không faithful**, kể cả
   bịa dữ kiện hỗ trợ. Doc gợi ý dùng `LlmReasoner` cho việc này — nếu làm, phải giới hạn ở
   **điền template trên dữ kiện đã tính sẵn**, không sinh văn tự do. (Kiến trúc hiện tại đã
   cấm LLM đổi thứ hạng; cảnh báo này nói về *nội dung câu chữ*, một lớp khác.)

Gợi ý khung trung thực hơn cho ca hòa — **Miller 2023** (FAccT), *Evaluative AI*: trình bày
bằng chứng ủng hộ/phản đối cho từng lựa chọn thay vì một khuyến nghị tự tin duy nhất.

---

## 5. Thuật ngữ: dùng gì, bỏ gì

| Dùng (có nguồn) | Bỏ (không nguồn nào dùng) |
|---|---|
| **direction augment** (một trong 4 loại: econ/item/combat/direction) | ~~anchor augment~~ |
| **comp-defining augment** | ~~optionality~~ (như thuật ngữ cộng đồng) |
| **flex vs forced** (dichotomy có trang guide riêng) | ~~high-commitment augment~~ |
| **keep your options open** | |
| **comp-specific vs generic augment** | |
| ZH: **打工体系 / 打工阵容**, **定路线**, **成型阵容**, **D牌 / D牌流**, **容错率**, **保血冲人口**, **撞车 / 抢卡**, **卡池** | ZH chưa xác nhận được: 定体系, 转型, 强制体系, 开局符文, 上人口流, 卡级 |

Thuật ngữ học thuật để dẫn trong chương Hạn chế:

- **myopic / one-step greedy vs lookahead** — Efroni et al., *Beyond the One-Step Greedy
  Approach in RL*. Đúng cách khung của doc.
- **POMDP / BAMDP, belief over latent plan** — dạng chuẩn của "nghịch lý con gà-quả trứng".
- **maximax** — tên đúng của "max over plans" (và nó bị phê phán).
- **empowerment** — tên trong RL của "đếm số plan mở ra"; failure mode đã ghi nhận: thưởng cho
  hành động chung chung-tốt-cho-mọi-thứ.
- **feature saturation** — chẩn đoán chuẩn cho tie-mass.

---

## 6. Đóng góp luận văn: khung lại cho đúng

**Giữ được:** khung "State-Reactive Scoring → Proactive Strategic Branching" bảo vệ được, và có
thuật ngữ chuẩn (myopic/greedy vs lookahead) để không phải tự đặt tên.

**Ba điều chỉnh để không bị phản biện:**

1. **Đừng nhận novelty ở archetype-conditioning.** Prior art: `Craggles2304/climb-ai` (PR #12
   "Augment Decision Lab") đã chấm augment theo 6 trục có điều kiện board state;
   `buinguyenbaokhanh/hexcall` làm tra cứu hai chiều augment↔comp bằng empirical Bayes
   shrinkage. Cả hai đều 0–3 sao, mới ~6 tuần, chưa validated — nên đây là **niche đang sôi
   động, chưa ai làm chín**, không phải đất trống. (hexcall tự nhận dùng "real match data" —
   mâu thuẫn với phát hiện đã chốt của dự án là Riot đã bỏ trường `augments` ở Set 18; đáng
   theo dõi, chưa xác minh được.)
2. **Novelty thật nằm ở taxonomy `econ_type`.** Research ZH tìm trong nguồn Trung không thấy
   **bất kỳ** nguồn nào phát biểu phân loại "reroll-econ vs XP-econ vs gold-econ" như một
   taxonomy — kể cả một bài chuyên về lõi kinh tế (bài đó xếp theo bậc mạnh/yếu). Research EN
   xác nhận **cơ chế** (có lõi chặn hẳn mua XP) nhưng cũng không thấy ai viết thành taxonomy.
   Kết luận đúng: **cơ chế là có thật, việc hình thức hoá nó là đóng góp của đồ án** — mạnh hơn
   là trình bày nó như kiến thức phổ thông.
3. **Nói luôn cái giá của lookahead.** Efroni et al. ghi rõ: lookahead đổi một nguồn sai số
   (horizon ngắn) lấy một nguồn khác (model error tích luỹ). Ở đây "model" là một
   `CompSelector` trọng số đặt tay với `evidence = 0.000` ở 2-1 — nên cái giá đó là **thật, đo
   được**, không phải lý thuyết. Nêu ra làm luận điểm mạnh hơn, không yếu hơn.

---

## 7. Căng thẳng giữa các nguồn & phần chưa giải quyết

| Vấn đề | Tình trạng |
|---|---|
| EN xác nhận taxonomy econ, ZH không thấy | **Không phải mâu thuẫn thật.** EN xác nhận cơ chế; ZH nói không ai xuất bản taxonomy. Đọc thành: cơ chế thật, taxonomy là của đồ án |
| "Lõi dẫn bài" ở 2-1 | EN nghiêng về *bác bỏ* cơ chế (board-context-first + keep options open); Mortdog nói Riot **chủ ý giảm** lõi ép hướng ở 2-1 (nguồn Set 16, cũ). Cần diễn đạt lại thành "keep-options-open vs current-fit" |
| Nguồn ggclan bị agent gán "Set 14" | **Sai nhãn.** SPEC §8 xác nhận Set 18 = "Enchanted Wilds" → nguồn đó có thể là Set 18. Không đổi kết luận nhưng làm phản-luận-điểm "force sớm khi meta chưa giải" đáng cân nhắc hơn |
| Nguồn ZH giàu nhất không truy cập được | 知乎专栏 403 (5 lần), NGA không index, một cột Bilibili trống. Các phán quyết ZH đọc là "chưa xác nhận", không phải "đã bác bỏ" |
| Không có pro nào đứng tên | Không tìm được Frodan/Dishsoap/k3soju… phát biểu trực tiếp về triết lý lõi 2-1. Mọi nguồn xác nhận đều là tác giả guide-site |
| Dữ liệu augment×comp công khai | **Không tồn tại.** tactics.tools rỗng; MetaTFT API loại augment hẳn. Nên số hạng `econ_type` buộc phải là heuristic/prior đặt tay, không fit được — đúng như doc đang tự nhận |
| `tft.ninja` — nguồn xác nhận mạnh nhất cho §3.2 | Không có nhãn set; ngày cập nhật trang lại **trước** ngày Set 18 live. Cần kiểm lại độ hiện hành trước khi dẫn trong luận văn |

---

## Related

- [Đối tượng thẩm định](../../docs/directional-augment-evaluation.md)
- Báo cáo thành phần: [EN lý thuyết TFT](en-tft-theory.md) · [ZH lý thuyết TFT](zh-tft-theory.md) ·
  [EN prior art](en-prior-art.md) · [EN thuật toán](en-algorithms.md) ·
  [EN explainability](en-explainability.md)
- [Open questions](../open-questions.md) — bối cảnh dữ liệu Set 18
- SPEC §3.5.2 (Comp Selection) · §3.5.4 (Augment Scoring) · §12.4 (Ablation)
