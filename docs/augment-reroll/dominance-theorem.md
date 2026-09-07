# Ba Định Lý

Ký hiệu như [formalization.md](formalization.md). Cả ba đều được khoá bằng test trong
`tests/test_reroll_policy.py` — nếu một dòng gãy thì lỗi nằm ở code, không phải ở một
ngưỡng nào cần chỉnh.

## T1 — Luôn đổi ô tệ nhất

> Trong các ô còn giữ lượt, đổi ô có điểm thấp nhất là tối ưu.

**Chứng minh (ghép cặp).** Xét hai ô `i`, `j` còn lượt với `v_i ≤ v_j`. Đổi ô `i` giữ lại
tập `{v_l}_{l≠i}`; đổi ô `j` giữ lại `{v_l}_{l≠j}`. Hai tập chỉ khác nhau ở chỗ tập thứ
nhất chứa `v_j` còn tập thứ hai chứa `v_i`. Vì `v_i ≤ v_j`, sau khi sắp xếp thì tập thứ
nhất trội **từng phần tử**. Dùng **cùng một** hiện thực `σ` cho cả hai nhánh; vì `V` đơn
điệu không giảm theo từng đối số, giá trị của nhánh đổi `i` không nhỏ hơn. ∎

**Điều kiện cần:** các ô phải **hoán đổi được** — cùng số lượt, cùng phân bố rút. Set 14
từng có "ô chủ đề" với số lượt khác và pool bị giới hạn theo nhóm; nếu Set 18 có thứ
tương tự thì T1 hỏng. Xem [heuristic-analysis.md](heuristic-analysis.md).

## T2 — Lượt đổi miễn phí thì phải đổi

> Nếu `c = 0` và `n ≥ 2` thì REROLL **trội hơn PICK theo nghĩa yếu**.

**Chứng minh.** Với `n ≥ 2`, ô tệ nhất không phải ô đang dẫn đầu, nên cả `L` lẫn `v₍ₙ₎`
đều sống sót qua lần đổi. Trạng thái mới có `L' = max(L, σ) ≥ L` và vẫn giữ `v₍ₙ₎`. Giá
trị dừng của nó là `max(L', v₍ₙ₎) ≥ max(L, v₍ₙ₎)` = giá trị dừng cũ. Vì `V ≥` giá trị
dừng, continuation ≥ giá trị dừng hiện tại. ∎

**Hệ quả trái trực giác:** dù thẻ dẫn đầu đã là điểm tối đa, đổi ô tệ nhất vẫn không lỗ.
Nên câu *"gặp S thì chốt ngay để dành lượt"* là **lỗ EV** khi lượt đổi miễn phí — lượt
đổi không dành được cho chặng sau (xem [mechanics-assumptions.md](mechanics-assumptions.md)).

**Trội hơn là YẾU, không phải chặt.** Khi thẻ dẫn đầu đã bằng đỉnh pool, tích phân đuôi
bằng 0 và hai hành động ngang nhau. Chính sách chọn **dừng** trong trường hợp hoà: một cú
bấm không đổi lấy gì vẫn tốn đồng hồ ~30 giây và — dưới giả định `burn_on_reveal` — còn
đốt thêm một thẻ khỏi pool của chặng sau.

## T3 — Một ngưỡng duy nhất

Đặt `B = max(L, v₍ₙ₎)` và `R` = sàn giữ lại nếu đổi ô mục tiêu. Một công thức cho **cả**
`n = 1` lẫn `n ≥ 2`: bỏ đúng ô mục tiêu ra khỏi phép max.

- `n ≥ 2`: ô tệ nhất không dẫn đầu ⟹ `R = B`
- `n = 1`: nếu ô cuối cùng đang dẫn đầu thì `R` tụt về `L`

Với `g(R) = E[max(R, σ)] = R + ∫_R^1 (1 − F_S(u)) du`:

```
REROLL  ⟺  g(R) − c > B          θ* = g(R) − c
```

Với `n ≥ 2` (khi `R = B`) điều này rút gọn thành `∫_B^1 (1−F_S) du > c`. Vế trái **giảm
đơn điệu** theo `B`, nên vùng dừng **liên thông**: một khi đã dừng thì không có lý do gì
quay lại đổi. Vì thế **luật một bước chính là luật tối ưu** — không cần bảng ngưỡng theo
từng bước, và đó là lý do toàn bộ quyết định chạy trong vài microsecond.

## Vì sao ngưỡng KHÔNG nên phụ thuộc HP

`TempoFit` (w5) đã ánh xạ HP → giá trị của augment: `urgency = clamp01((70−hp)/(70−35))`,
thẻ `immediate` được nâng, thẻ `scaling` bị phạt. HP đã nằm trong `B` **và** trong `F_S`.
Đưa HP vào `θ*` một lần nữa là **đếm hai lần**.

Thêm nữa, dấu của hiệu ứng còn đang tranh cãi: ở HP thấp với board yếu, hàm trả thưởng
theo thứ hạng là **lồi** (cần top 4, về 7 hay 8 gần như không khác nhau), nên lý thuyết
nói phải **ưa rủi ro** — ngược hẳn với trực giác "HP ≤ 30 thì chơi an toàn".

Vì vậy `risk_lambda` mặc định **0** (trung lập) và tồn tại như một nhánh ablation, chứ
không phải một hiệu chỉnh mặc định.

## Related

- [formalization.md](formalization.md) — trạng thái và Bellman
- [depletion-cost.md](depletion-cost.md) — `c` đến từ đâu
- [heuristic-analysis.md](heuristic-analysis.md) — khi nào ba định lý này hỏng
