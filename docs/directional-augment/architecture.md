# Architecture

Ba giải pháp sau khi thẩm định bằng research
([synthesis](../../research/260930-directional-augment/synthesis.md) §4). Vấn đề:
[blind-spots.md](blind-spots.md).

## Ràng buộc: phải là một trục ablation ngay từ đầu

Chốt 2026-09-30, **trước** thiết kế chi tiết. Mọi thay đổi dưới đây phải **tắt được bằng một cờ**
trong `config/scoring_weights.yaml`, nhánh cũ giữ nguyên làm dòng đối chứng.

Tiền lệ đã có: `comp_selector.adaptive` là một cờ, comment ghi thẳng *"Trục ablation: chạy cả hai
trên cùng dataset"*.

| Vì sao bắt buộc | |
|---|---|
| Biến tính năng thành bằng chứng | Báo cáo được **"directional bật vs tắt"** như delta đo trên held-out |
| Cứu tính đọc-được của ablation | Hồi tiếp **tắt được** không phá; hồi tiếp **ngầm** thì phá |
| Retrofit thì đắt | Nối cứng rồi mới nghĩ tới ablation là phải tháo ra, lúc đó đã hết thời gian |

## Giải pháp 1 — Hồi tiếp hai chiều: **bác bỏ như bản đầu viết**

Ba lý do độc lập:

1. **Không có gì để truyền.** Ở 2-1, `evidence = 0.000` cho **cả 81 comp**, và `commitment()` tự
   trả về *"chưa nên chốt — tín hiệu trên board còn yếu"*. Truyền về chỉ là truyền một **meta
   prior**, rồi trộn nó vào `econ_fit` như thể đó là tín hiệu bàn cờ.
2. **Truyền về sẽ khuếch đại một bias đang có.** `CompSelector` lệch sẵn theo archetype vì
   `unit`/`emblem`/`augment` là thang **gốc-0** còn `item_type`/`meta` là thang **tâm-0,5** — xem
   [centering-fix.md](centering-fix.md) cho cơ chế và cách sửa.

   Sàn điểm khi board **không có tín hiệu nào** (đo trên 81 comp, `stage 2-1`):

   | profile | sàn | vì sao |
   |---|---|---|
   | `fixed` (comp không nhãn) | **0,0000** | dùng `item_score` gốc-0 |
   | `reroll` | **0,0800** | `item_type` 0,40 × w 0,20 |
   | `fast8` / `fast9` | **0,1600** | `item_type` 0,40 × w **0,40** |

   Chênh lệch sàn: **0,08** (fast vs reroll) và **0,16** (fast vs comp không nhãn) — cái sau vượt
   `lock_margin` 0,12.

   Hệ quả tái lập được: đặt **3/7 tướng lõi của một comp reroll đã lên 2 sao** ở 2-1
   (`evidence = 0,429`), comp đó xếp **thứ 4/81**, sau **ba** comp fast8/9 có `unit = 0.00` và
   `evidence = 0.000`. Nên truyền archetype của comp #1 về sẽ **thưởng lõi XP và phạt lõi reroll
   một cách hệ thống, bất kể bàn cờ** — ngược hẳn ý định.

   > Synthesis ghi sàn 0,2000 / 0,2250 / 0,3500 và chênh 0,15; con số ở đây là **đo lại trực
   > tiếp** trên `config/scoring_weights.yaml` hiện tại và không tái lập được bộ đó (khả năng
   > synthesis dùng state khác). Kết luận không đổi, chỉ biên độ nhỏ hơn.
3. **Kiến trúc SOTA của bài toán tương đương tránh đúng cách này.** DraftFM (arXiv:2608.19568; 149M
   lượt pick MTG draft — bài toán y hệt) biểu diễn cam kết bằng **một embedding liên tục cập nhật
   mỗi lượt**, và tuyên bố thẳng: *archetype là **hệ quả ngầm** của các thẻ đã chọn, không phải một
   biến điều kiện riêng có thể vòng lại ảnh hưởng giá trị thẻ*.

### Cách gỡ đúng, theo thứ tự chi phí tăng dần

| Bước | Nội dung | Vì sao không vòng lặp |
|---|---|---|
| 1 | **Sửa lỗi centering trong `CompSelector`** — đưa `unit`/`emblem`/`augment` về thang tâm-0,5, hoặc chuẩn hoá theo sàn từng profile | Là sửa bug độc lập, phải làm dù có làm gì tiếp hay không |
| 2 | Dùng **`state.augments`** (lõi ĐÃ cầm) làm tín hiệu kế hoạch cho 3-2/4-2 | Quá khứ — không phụ thuộc đầu ra hiện tại |
| 3 | Dùng **`econ_type` của chính thẻ đó** làm tín hiệu hướng | Đặc trưng nội tại của thẻ, không đọc từ `CompSelector` |
| 4 | Nếu vẫn cần plan: **belief over plans**, `Score(a) = Σ_φ b(φ)·Score(a\|φ)` | Dạng chuẩn (POMDP/BAMDP: latent ẩn + belief), không phải one-pass feedback |

**Bước 2 là cách vào rẻ nhất và chưa ai dùng.** `GameState.augments` hiện **chỉ** được
`CompSelector.augment_score()` đọc — không scorer nào trong 5 scorer của `AugmentAdvisor` đọc nó.
Nhưng ở 3-2/4-2, lõi đã chọn ở 2-1 chính là tuyên bố kế hoạch rõ nhất, và nó đã là quá khứ.

> ⚠️ **Đừng dùng `max` over plans.** Đó là **maximax** — quy tắc lạc quan đã bị phê phán: thiên vị
> lựa chọn upside cao nhưng xác suất thấp, bỏ qua likelihood. Dạng đúng của field là **kỳ vọng dưới
> belief**. Nếu vẫn dùng max thì phải gọi đúng tên và nêu nhược điểm.

## Giải pháp 2 — Tách nhánh trong `EconFit`: **đúng hướng, sai hình**

Ba điều chỉnh:

1. **Multi-label, không phải enum.** Suy từ `desc` CDragon của 131 lõi có `econ_value > 0`:

   | tổ hợp tín hiệu | số lõi | | tổ hợp | số lõi |
   |---|---|---|---|---|
   | chỉ gold | 67 | | **xp + gold** | 7 |
   | chỉ xp | 12 | | **xp + reroll** | 6 (`Epoch`: *"gain 4 XP **and** 2 free rerolls"*) |
   | chỉ reroll | 5 | | **reroll + gold** | 5 (`Trade Sector`) |
   | không rõ | 27 | | **xp + reroll + gold** | 2 |

   **20/131 lõi mang ≥2 hình thái.** Dùng ba trường độc lập (`econ_xp` / `econ_reroll` /
   `econ_gold`) hoặc một list — đúng khuôn `trait_affinity` và `item_grants` đang dùng. Bản đầu phê
   phán *"Orthogonal Attributes vs. Single Category"* rồi lại kê đúng một single category.

2. **Sửa tầng feature TRƯỚC.** Thêm `econ_type` vào scorer không có ích gì khi
   `augment_features.json` đã xoá nhãn `reroll` của `Trade Sector`
   ([blind-spots §2](blind-spots.md)). Cần: sinh lại bảng với `econ_type` trích **tất định**, và
   **khoá bằng test** — `reroll_kw(desc) == True ⇒ econ_reroll == True` — để LLM không ghi đè được.
   Đây là thi hành nguyên tắc `dev_log` §4, không phải thêm quy ước mới.

3. **`level_pace` nằm ở `tuning.tempo_fit`, không phải `econ_fit`.** Bản đầu nói chấm `econ_type ×
   level_pace` mà không nói lấy ở đâu. Chia sẻ tham số giữa hai scorer làm ablation khó đọc (§12.4
   quy định `tuning` phải giữ nguyên giữa các lần ablation) — nên **nhân bản có chủ đích và ghi
   rõ**, hoặc đưa lên cấp cao hơn.

**Biên độ đề nghị: ±0,08…0,10** trong không gian thành phần, cùng thang với `gold_swing: 0.10` và
`loss_streak_bonus: 0.08`.

Cơ sở: `w3 = 0.15`, nên ±0,20 trong không gian thành phần → ±0,030 ở điểm tổng ≈ **7–10 bậc** ở độ
phân giải trung vị 0,003. Vừa đủ đảo thứ hạng thật (khoảng cách #1 vs #2 trong ví dụ đo được là
0,025) và **dễ quá liều**.

## Giải pháp 3 — Giải thích rẽ nhánh

Xem [explainability.md](explainability.md) — có nền lý thuyết vững hơn bản đầu tưởng, nhưng kèm
hai cảnh báo bắt buộc.

## Related

- [Overview](overview.md) · [Blind spots](blind-spots.md) · [Baseline](baseline.md)
- [Explainability](explainability.md) · [Contribution](contribution.md)
- [Research synthesis](../../research/260930-directional-augment/synthesis.md) §4
