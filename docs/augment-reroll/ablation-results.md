# Kết Quả Đối Chứng Monte-Carlo

Deliverable D.2. Chạy ngày 2026-09-09, `n = 10.000` tình huống, `seed = 20260907`, bootstrap
2.000 vòng trên chênh lệch **đã ghép cặp**. Phương pháp: [evaluation.md](evaluation.md).

```powershell
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 2 --stage 2 --trials 10000
```

Nguồn pool: `expert-tierlist:TFT Academy (Dishsoap & Frodan)/patch=18.1d` (`ordinal`), sau khi
đã hiệu chuẩn lại bộ neo `TIER_PLACEMENT`. Bàn cờ giả lập: chặng 2-1, level 7, 30 vàng,
trait đang bật `DA_Primal18:3`.

## Bậc gold (tier 2, N = 132)

| chính sách | điểm TB | số lần đổi | Δ so với mốc [KTC 95%] |
|---|---|---|---|
| không đổi (mốc) | 0,59808 | 0,00 | — |
| chọn bừa | 0,54896 | 0,00 | −0,04912 [−0,05029, −0,04794] |
| vét hết ba lượt | 0,59845 | 3,00 | +0,00037 [−0,00064, +0,00143] |
| **tuần tự** | **0,61652** | **2,12** | **+0,01844 [+0,01783, +0,01907]** |
| biết trước (trần) | 0,61864 | 0,96 | +0,02056 [+0,01995, +0,02118] |

Tuần tự lấy được **89,7%** khoảng cách từ mốc đến trần biết trước.

## Cả ba bậc (chặng 2-1)

| bậc | N | mốc | tuần tự | số lần đổi | Δ tuần tự [KTC 95%] | trần | % trần |
|---|---|---|---|---|---|---|---|
| silver (1) | 62 | 0,59502 | 0,61699 | 2,22 | +0,02197 [+0,02123, +0,02271] | 0,61974 | 88,8% |
| gold (2) | 132 | 0,59808 | 0,61652 | 2,12 | +0,01844 [+0,01783, +0,01907] | 0,61864 | 89,7% |
| prismatic (3) | 60 | 0,61856 | 0,63754 | **1,15** | +0,01898 [+0,01829, +0,01968] | 0,64281 | 78,3% |

Ba điều đọc được từ bảng:

1. **Δ dương chắc chắn ở cả ba bậc** — cận dưới KTC 95% đều cách 0 rất xa (nhỏ nhất
   +0,01783). Với thiết kế ghép cặp, đây là kết luận về *cùng một tay bài*, không phải may rủi.
2. **Vét hết ba lượt ≈ không đổi lần nào** — KTC của nó **chứa 0** ở cả ba bậc. Lượt thứ ba
   bắt buộc đổi chính ô đang giữ thẻ tốt nhất nên trả lại gần hết phần lợi của hai lượt đầu.
   Đây là bằng chứng định lượng rằng giá trị nằm ở **luật dừng**, không ở việc roll nhiều.
3. **Prismatic dừng sớm hơn hẳn** — 1,15 lượt so với 2,12/2,22. Mốc prismatic đã cao (0,61856)
   nên ngưỡng `θ* = g(R) − c` bị vượt sớm, đúng chế độ mà `cost_matrix` mô tả.

Chính sách biết trước chỉ cần **0,96** lượt đổi. Khoảng cách 2,12 → 0,96 chính là cái giá của
việc không nhìn thấy trước: chính sách tuần tự phải *thăm dò* mới biết nên dừng.

## Kiểm chứng trần bằng công thức đóng

Với nhánh rút đều (β = 0), trần biết trước có dạng giải tích. Rút 6 thẻ **không lặp lại** từ
pool N thẻ, xác suất thẻ xếp hạng `k` (từ nhỏ đến lớn) là max của 6 thẻ bằng `C(k−1, 5) / C(N, 6)`:

```
E[max của 6] = Σ_{k=6}^{N} s_(k) · C(k−1, 5) / C(N, 6)
```

| bậc | N | giải tích | Monte-Carlo n = 10.000 | n = 200.000 |
|---|---|---|---|---|
| silver | 62 | 0,619268 | 0,619743 (+0,000475) | 0,619395 (+0,000126) |
| gold | 132 | 0,615237 | 0,615602 (+0,000364) | 0,615319 (+0,000081) |
| prismatic | 60 | 0,642305 | 0,642810 (+0,000506) | 0,642398 (+0,000093) |

Sai số giảm theo `1/√n` đúng như kỳ vọng (gấp 20 lần cỡ mẫu ⟹ sai số giảm ~4 lần). Đây là
**phép kiểm bộ mô phỏng**, không phải một kết quả: nếu `sample_draws` cài sai cơ chế rút
không-lặp-lại thì hai cột này đã lệch nhau ở chữ số thứ ba.

## Giới hạn phải nêu trong báo cáo

Đây là **chính sách so với chính sách trên chính hàm Score của hệ thống**. Nếu hàm Score sai
thì cả hai chính sách cùng sai và số delta này vẫn đẹp như thường. Nó **không** phải bằng
chứng về placement — xem [evaluation.md](evaluation.md).

## Related

- [evaluation.md](evaluation.md) — phương pháp và những gì chưa đo được
- [tailoring-beta-sweep.md](tailoring-beta-sweep.md) — nhánh β = 1 vs β = 0
- [dominance-theorem.md](dominance-theorem.md) — ba định lý mà bảng số này minh hoạ
- [depletion-cost.md](depletion-cost.md) — `c` và `cost_matrix` đứng sau cột "số lần đổi"
