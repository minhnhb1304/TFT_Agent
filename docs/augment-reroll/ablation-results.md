# Kết Quả Đối Chứng Monte-Carlo

Deliverable D.2. Chạy lại ngày 2026-10-07, `n = 10.000` tình huống mỗi ô, `seed = 20260907`,
bootstrap 2.000 vòng trên chênh lệch **đã ghép cặp**. Phương pháp: [evaluation.md](evaluation.md).

> Thay bản 2026-09-09 (pool 62/132/60, patch 18.1d). Ba thứ đã đổi từ đó: **bậc đã sửa**
> ([tier-mismatch](../offer-rounds/tier-mismatch.md), pool cùng bậc nay là 70/115/69), **pool lọc
> theo lượt chào** ([offer-round-pool.md](offer-round-pool.md), `pool_by_offer_round: true`), và
> bảng tier lên **patch 18.2**. Số cũ không còn so trực tiếp được với số dưới đây.

```powershell
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 2 --stage 2 --trials 10000
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 2 --stage 2 --pool-by-offer-round off
```

Nguồn pool: `expert-tierlist:TFT Academy (Dishsoap & Frodan)/patch=18.2` (`ordinal`). Bàn cờ giả
lập: level 7, 30 vàng, trait đang bật `DA_Primal18:3`. `--stage 2 / 3 / 4` = lượt 2-1 / 3-2 / 4-2.

## Bậc gold ở 2-1 (tier 2, N = 59)

| chính sách | điểm TB | số lần đổi | Δ so với mốc [KTC 95%] |
|---|---|---|---|
| không đổi (mốc) | 0,58391 | 0,00 | — |
| chọn bừa | 0,53597 | 0,00 | −0,04794 [−0,04907, −0,04679] |
| vét hết ba lượt | 0,58439 | 3,00 | +0,00048 [−0,00044, +0,00147] |
| **tuần tự** | **0,60113** | **2,20** | **+0,01722 [+0,01665, +0,01779]** |
| biết trước (trần) | 0,60301 | 0,91 | +0,01911 [+0,01854, +0,01969] |

Tuần tự lấy được **90,2%** khoảng cách từ mốc đến trần biết trước.

## Cả ba bậc, cả ba lượt

Pool theo lượt (`tier+round`) ở mọi ô. Cột cuối là Δ tuần tự của **nhánh đối chứng** (cờ tắt,
pool cùng bậc N = 70/115/69).

| bậc | lượt | N | mốc | tuần tự | số lần đổi | Δ tuần tự [KTC 95%] | trần | % trần | Δ khi tắt cờ |
|---|---|---|---|---|---|---|---|---|---|
| silver (1) | 2-1 | 38 | 0,60398 | 0,62599 | 2,05 | +0,02201 [+0,02128, +0,02277] | 0,62902 | 87,9% | +0,01912 |
| gold (2) | 2-1 | 59 | 0,58391 | 0,60113 | 2,20 | +0,01722 [+0,01665, +0,01779] | 0,60301 | 90,2% | +0,02238 |
| prismatic (3) | 2-1 | 31 | 0,60121 | 0,61251 | **1,24** | +0,01130 [+0,01088, +0,01172] | 0,61579 | 77,5% | +0,01664 |
| silver (1) | 3-2 | 36 | 0,56198 | 0,57715 | 1,76 | +0,01517 [+0,01470, +0,01567] | 0,57883 | 90,0% | +0,01987 |
| gold (2) | 3-2 | 63 | 0,57569 | 0,59911 | 1,86 | +0,02342 [+0,02270, +0,02420] | 0,60185 | 89,5% | +0,02400 |
| prismatic (3) | 3-2 | 32 | 0,59083 | 0,61380 | 1,94 | +0,02298 [+0,02218, +0,02376] | 0,61717 | 87,2% | +0,01709 |
| silver (1) | 4-2 | 27 | 0,54824 | 0,56411 | 2,19 | +0,01587 [+0,01537, +0,01638] | 0,56542 | 92,4% | +0,02458 |
| gold (2) | 4-2 | 40 | 0,59114 | 0,62675 | 2,08 | +0,03561 [+0,03451, +0,03675] | 0,63059 | 90,3% | +0,02781 |
| prismatic (3) | 4-2 | 30 | 0,58481 | 0,61072 | 2,23 | +0,02591 [+0,02503, +0,02679] | 0,61388 | 89,1% | +0,02039 |

Cột "Δ khi tắt cờ" rút bài từ **một thế giới khác** (pool cùng bậc), nên hiệu của hai cột Δ
**không** phải lợi ích của cờ. Phép so đúng (cùng tay bài, hai niềm tin) ở
[offer-round-pool.md](offer-round-pool.md).

Ba điều đọc được từ bảng:

1. **Δ dương chắc chắn ở cả 9 ô**, và ở cả 9 ô của nhánh đối chứng: cận dưới KTC 95% nhỏ nhất
   là +0,01088 (prismatic 2-1). Thiết kế ghép cặp nên đây là kết luận về *cùng một tay bài*.
2. **Vét hết ba lượt ≈ không đổi lần nào**: KTC của nó **chứa 0** ở cả 18 lần chạy. Lượt thứ ba
   bắt buộc đổi chính ô đang giữ thẻ tốt nhất nên trả lại gần hết phần lợi của hai lượt đầu.
   Giá trị nằm ở **luật dừng**, không ở việc roll nhiều.
3. **Prismatic 2-1 dừng sớm hơn hẳn**: 1,24 lượt so với 2,05 / 2,20, và chỉ lấy được 77,5% trần.
   Đây là ô có `c` lớn nhất (0,00362), đúng chế độ mà `cost_matrix` mô tả. Ở 4-2 `c = 0` nên
   prismatic đổi 2,23 lượt như hai bậc kia.

Tuần tự lấy được **77,5–92,4%** trần. Chính sách biết trước chỉ cần 0,89–0,98 lượt đổi; khoảng
cách tới ~2 lượt của tuần tự là cái giá của việc phải *thăm dò* mới biết nên dừng.

## Kiểm chứng trần bằng công thức đóng

Với nhánh rút đều (β = 0), trần biết trước có dạng giải tích. Rút 6 thẻ **không lặp lại** từ
pool N thẻ, xác suất thẻ xếp hạng `k` (từ nhỏ đến lớn) là max của 6 thẻ bằng `C(k−1, 5) / C(N, 6)`:

```
E[max của 6] = Σ_{k=6}^{N} s_(k) · C(k−1, 5) / C(N, 6)
```

Pool theo lượt ở 2-1:

| bậc | N | giải tích | Monte-Carlo n = 10.000 | n = 200.000 |
|---|---|---|---|---|
| silver | 38 | 0,628204 | 0,629019 (+0,000815) | 0,628374 (+0,000171) |
| gold | 59 | 0,602715 | 0,603013 (+0,000298) | 0,602764 (+0,000049) |
| prismatic | 31 | 0,615492 | 0,615790 (+0,000298) | 0,615565 (+0,000073) |

Sai số giảm 4–6 lần khi cỡ mẫu gấp 20, khớp `1/√n`. Silver ở n = 10.000 lệch +0,0008, lớn hơn
mốc `< 5·10⁻⁴` của bản tháng 9; pool nhỏ hơn và có một thẻ đứng tách hẳn (0,6965). Đây là
**phép kiểm bộ mô phỏng**, không phải một kết quả.

Trần của lần chạy chính (có trọng số tailoring) **trùng** cột n = 10.000 tới 5 chữ số ở cả ba
bậc: với pool theo lượt ở 2-1, β không dịch gì. Bảng [tailoring-beta-sweep.md](tailoring-beta-sweep.md)
đo trên pool cũ N = 132 và **chưa chạy lại**.

## Giới hạn phải nêu trong báo cáo

Đây là **chính sách so với chính sách trên chính hàm Score của hệ thống**. Nếu hàm Score sai
thì cả hai chính sách cùng sai và số delta này vẫn đẹp như thường. Nó **không** phải bằng
chứng về placement — xem [evaluation.md](evaluation.md).

## Related

- [evaluation.md](evaluation.md) — phương pháp và những gì chưa đo được
- [offer-round-pool.md](offer-round-pool.md) — pool theo lượt, phép so cờ bật/tắt ghép cặp
- [tailoring-beta-sweep.md](tailoring-beta-sweep.md) — nhánh β = 1 vs β = 0 (số pool cũ)
- [dominance-theorem.md](dominance-theorem.md) — ba định lý mà bảng số này minh hoạ
- [depletion-cost.md](depletion-cost.md) — `c` và `cost_matrix` đứng sau cột "số lần đổi"
