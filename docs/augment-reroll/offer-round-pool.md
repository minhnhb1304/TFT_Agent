# Pool Theo Lượt Chào

Pha P4 của [offer-rounds](../offer-rounds/phases.md). Đo ngày 2026-10-06, `n = 10.000` tay
bài mỗi ô, `seed = 20260907`, bootstrap 2.000 vòng trên chênh lệch **đã ghép cặp**.
**Bậc đã sửa 2026-10-06** ([tier-mismatch](../offer-rounds/tier-mismatch.md)); số dưới đây đo lại sau khi sửa, số cũ dùng bậc sai.

```powershell
.\.venv\Scripts\python scripts\measure_offer_round_pool.py
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 3 --stage 2 --pool-by-offer-round off
```

## Thay đổi

`F_S` trước đây dựng trên **mọi lõi cùng bậc**. Nay pool = cùng bậc **và**
`AugmentFeature.offered_at(lượt)`. Lượt lấy theo **số chặng** (2 → 2-1, 3 → 3-2, 4 → 4-2).

| Khoá trong `reroll_policy:` | Mặc định | Nghĩa |
|---|---|---|
| `pool_by_offer_round` | `true` | `false` = pool cùng bậc như cũ (nhánh đối chứng) |
| `min_round_pool` | `12` | Pool theo lượt nhỏ hơn số này thì lùi về pool cùng bậc |

`pool_scope` (trong `RerollAdvice`, log scenario, báo cáo ablation) ghi pool nào đã dùng.
`pool_source` giữ nghĩa cũ: xuất xứ **số liệu**.

| `pool_scope` | Khi nào |
|---|---|
| `tier` | Cờ tắt |
| `tier+round` | Cờ bật, đã lọc theo lượt |
| `tier:fallback-small` | Pool theo lượt < `min_round_pool` |
| `tier:no-round-data` | Cả bậc chưa có dòng nào biết `offer_rounds` |
| `tier:no-round` | Chặng không phải lượt chào lõi (đọc stage hỏng, chặng 5+) |

Ba quy tắc giữ cho bộ lọc không làm hỏng logic cũ:

- Lõi không có `offer_rounds` **ở lại** mọi pool. Thiếu dữ liệu không bao giờ làm pool nhỏ đi.
- Ngưỡng xét trên pool **chưa trừ** thẻ đang hiện và thẻ đã đốt, vì kích thước đó là thuộc tính
  của (bậc, lượt). Xét sau khi trừ thì pool có thể đổi kiểu giữa hai lần đổi trong một màn.
- Thẻ đang hiện và thẻ đã đốt vẫn bị trừ như cũ, **sau** khi lọc. Thẻ đốt ở lượt khác mà không
  chào ở lượt này đã bị bộ lọc loại sẵn, không trừ hai lần.

`12` = 2 × 6 thẻ một màn có thể lộ ra. Pool thật nhỏ nhất là 27 (bậc 1 ở 4-2), nên ngưỡng
**chưa bao giờ kích hoạt** trên dữ liệu hiện tại; nó chỉ chặn dữ liệu hỏng.

## Pool trước và sau

Bàn cờ giả lập như [ablation-results.md](ablation-results.md), chỉ đổi stage. `g(med)` =
`expected_max` tại trung vị của pool thật. Ở 5/9 ô, thẻ điểm cao nhất của bậc không thể xuất hiện.

| bậc | lượt | N | sigma | điểm cao nhất | g(med) |
|---|---|---|---|---|---|
| 1 | 2-1 | 70 → 38 | 0,0488 → 0,0493 | 0,6965 → 0,6965 | 0,5784 → 0,5824 |
| 1 | 3-2 | 70 → 36 | 0,0456 → 0,0408 | 0,6965 → 0,5983 | 0,5529 → 0,5453 |
| 1 | 4-2 | 70 → 27 | 0,0468 → 0,0358 | 0,6965 → 0,5938 | 0,5355 → 0,5294 |
| 2 | 2-1 | 115 → 59 | 0,0643 → 0,0610 | 0,7033 → 0,6455 | 0,5739 → 0,5663 |
| 2 | 3-2 | 115 → 63 | 0,0596 → 0,0588 | 0,7033 → 0,6433 | 0,5530 → 0,5459 |
| 2 | 4-2 | 115 → 40 | 0,0571 → 0,0670 | 0,7033 → 0,7033 | 0,5395 → 0,5475 |
| 3 | 2-1 | 69 → 31 | 0,0579 → 0,0453 | 0,6808 → 0,6440 | 0,5863 → 0,5849 |
| 3 | 3-2 | 69 → 32 | 0,0544 → 0,0568 | 0,6808 → 0,6808 | 0,5713 → 0,5695 |
| 3 | 4-2 | 69 → 30 | 0,0540 → 0,0627 | 0,6808 → 0,6808 | 0,5649 → 0,5674 |

## Quyết định lật

Thế giới thật = pool theo lượt. Cùng một tay bài, chính sách chơi hai lần: tin pool cùng bậc
(tắt) và tin pool theo lượt (bật). "Mục tiêu" = điểm − `c` × số lần đổi, `c` tính trên pool thật.

| bậc | lượt | lật bước 1 | lật cả ván | số lần đổi | Δ điểm [KTC 95%] | Δ mục tiêu [KTC 95%] |
|---|---|---|---|---|---|---|
| 1 | 2-1 | 0 | 355 | 2,02 → 2,05 | +0,00017 [+0,00005, +0,00030] | +0,00015 [+0,00003, +0,00028] |
| 1 | 3-2 | 2.387 | 4.375 | 2,53 → 1,76 | +0,00003 [−0,00009, +0,00014] | +0,00034 [+0,00023, +0,00045] |
| 1 | 4-2 | 1.085 | 1.996 | 2,53 → 2,19 | −0,00005 [−0,00012, +0,00001] | −0,00005 [−0,00012, +0,00001] |
| 2 | 2-1 | 963 | 2.080 | 2,54 → 2,20 | +0,00001 [−0,00010, +0,00012] | +0,00021 [+0,00010, +0,00032] |
| 2 | 3-2 | 2.182 | 3.704 | 2,53 → 1,86 | −0,00005 [−0,00017, +0,00006] | +0,00034 [+0,00022, +0,00045] |
| 2 | 4-2 | 0 | 277 | 2,05 → 2,08 | +0,00021 [+0,00006, +0,00037] | +0,00021 [+0,00006, +0,00037] |
| 3 | 2-1 | 711 | 1.229 | 1,44 → 1,24 | **−0,00061** [−0,00071, −0,00052] | +0,00010 [+0,00001, +0,00019] |
| 3 | 3-2 | 0 | 148 | 1,96 → 1,94 | **−0,00017** [−0,00028, −0,00006] | **−0,00014** [−0,00025, −0,00003] |
| 3 | 4-2 | 0 | 214 | 2,21 → 2,23 | +0,00013 [+0,00003, +0,00025] | +0,00013 [+0,00003, +0,00025] |

Mọi quyết định lật ở bước 1 đều theo một chiều: **REROLL → PICK**.

## Vì sao mặc định vẫn là bật

- **Mục tiêu tăng ở 7/9 ô** (cận dưới KTC > 0); bậc 1 ở 4-2 có KTC chứa 0.
- **Mục tiêu giảm có ý nghĩa ở 1 ô**: bậc 3 ở 3-2, −0,00014 (≈ 0,0025 sigma). Trước khi sửa
  bậc không ô nào giảm; câu "mục tiêu không giảm ở ô nào" **không còn đúng**. Mức giảm nhỏ hơn
  mức tăng ở mọi ô có ý nghĩa, nên cờ giữ `true`; ai coi ô này là quan trọng thì đặt `false`.
- **Điểm thô giảm có ý nghĩa ở 2 ô** (bậc 3 ở 2-1 và 3-2), đều là ô `c > 0`: chính sách cũ đổi
  nhiều hơn nhờ tin sai, nhặt thêm chút điểm thô và trả `c` mà cột điểm không thấy.
- Kết luận **phụ thuộc vào `cost_matrix`**, là tiên nghiệm, không phải số đo ([depletion-cost.md](depletion-cost.md)).

## Giới hạn

- `offer_rounds` lấy từ datatft (máy chủ CN): tín hiệu, không phải ground truth. Thẻ đang hiện
  mà dữ liệu nói "không chào ở lượt này" là dấu hiệu dữ liệu lệch; hiện chưa ghi log riêng.
- Chính sách so với chính sách trên cùng hàm Score. **Không** phải bằng chứng về placement.

## Related

- [ablation-results.md](ablation-results.md): số Monte-Carlo gốc (pool cùng bậc)
- [depletion-cost.md](depletion-cost.md): `c` và `cost_matrix`
- [../offer-rounds/overview.md](../offer-rounds/overview.md): nguồn `offer_rounds`
