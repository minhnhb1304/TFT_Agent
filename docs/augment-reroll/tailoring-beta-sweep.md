# Quét Tham Số Tailoring β

Nhánh đối chứng thứ hai của D.2: `β = 1,0` (có tính đến Tailoring) so với `β = 0,0` (rút
ngẫu nhiên đồng đều). `β` chỉ tác động **một chỗ**: trọng số rút của augment trùng trait đang
bật, `w = 1 + β` nếu trùng, `1` nếu không (`reroll_policy.tailoring_weight`).

```powershell
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 2 --trials 10000 --tailoring-beta 0.0
```

## Kịch bản mặc định (`DA_Primal18:3`)

| bậc | số lõi được nhân trọng số | β | mốc | tuần tự | số lần đổi | Δ tuần tự [KTC 95%] |
|---|---|---|---|---|---|---|
| silver (1) | **0 / 62** | 1,0 và 0,0 | 0,59502 | 0,61699 | 2,22 | +0,02197 [+0,02123, +0,02271] |
| gold (2) | 4 / 132 | 1,0 | 0,59808 | 0,61652 | 2,12 | +0,01844 [+0,01783, +0,01907] |
| gold (2) | 4 / 132 | 0,0 | 0,59529 | 0,61361 | 2,18 | +0,01832 [+0,01771, +0,01895] |
| prismatic (3) | **0 / 60** | 1,0 và 0,0 | 0,61856 | 0,63754 | 1,15 | +0,01898 [+0,01829, +0,01968] |

Silver và prismatic cho kết quả **trùng khít từng chữ số** giữa hai nhánh. Đó không phải lỗi:
`data/augment_features.json` chỉ có **4 lõi** mang `trait_affinity = DA_Primal18`, và cả bốn
đều ở bậc gold. Không lõi nào trong pool silver/prismatic trùng trait ⟹ `w ≡ 1` ⟹ β không có
cần gạt nào để kéo.

Ở gold, β chỉ nhân đôi trọng số **4/132 lõi**. Nó nâng cả mốc lẫn tuần tự lên gần bằng nhau
(+0,00279 và +0,00291), nên **Δ gần như không đổi**: +0,01844 so với +0,01832, hai khoảng tin
cậy chồng lên nhau gần trọn.

## Kịch bản áp lực tối đa (5 trait cùng bật)

Toàn bảng đặc trưng chỉ có **20 lõi** mang `trait_affinity`, và **19/20** nằm ở bậc gold
(một lõi duy nhất ở silver). Gom năm trait đông augment nhất lại là đã chạm trần đòn bẩy mà dữ liệu cho phép:

```powershell
.\.venv\Scripts\python -m src.eval.reroll_ablation --tier 2 --trials 10000 `
  --traits "DA_Primal18:3,DA_18_Solar:4,DA_18_Coven:3,DA_FloraFatalis18:2,DA_18_Lunar:2" `
  --tailoring-beta 0.0
```

11 / 132 lõi được nhân trọng số:

| β | mốc | tuần tự | số lần đổi | Δ tuần tự [KTC 95%] | trần |
|---|---|---|---|---|---|
| 1,0 | 0,60708 | 0,63033 | 2,26 | +0,02325 [+0,02246, +0,02403] | 0,63291 |
| 0,0 | 0,60129 | 0,62216 | **2,38** | +0,02087 [+0,02018, +0,02159] | 0,62450 |

Ngay cả ở đây, β chỉ dịch Δ đi **+0,00238** — bằng khoảng 10% độ lớn của chính Δ.

## Kết luận: β dịch mặt bằng, không dịch kết luận

Tailoring làm **cả pool tốt lên** (mốc +0,00579, trần +0,00841), nên nó nâng cả chính sách
tuần tự lẫn chính sách mốc gần như cùng một lượng. Với thiết kế ghép cặp, phần nâng chung ấy
bị triệt tiêu trong hiệu.

Cột **số lần đổi** mới là chỗ β để lại dấu vết rõ nhất: 2,26 (β = 1) so với 2,38 (β = 0). Bỏ
qua tailoring khiến pool nghèo đi, tay bài đầu xấu hơn, và chính sách phải đổi nhiều hơn để bù.

> ⚠️ **Đây chưa phải phép đo "thiên lệch sợ-reroll".** Ở bộ mô phỏng hiện tại, β điều khiển
> **đồng thời** quá trình rút bài lẫn niềm tin của chính sách. Nó trả lời "thế giới có
> tailoring khác thế giới không có tailoring bao nhiêu", chứ không phải "mô hình sai tailoring
> thì chính sách lỗ bao nhiêu". Câu hỏi sau cần một lần chạy **lệch pha**: rút bài với
> β = 1 nhưng cho `decide()` tin là β = 0. Bộ mô phỏng chưa có đường vào cho cấu hình đó.

## Related

- [ablation-results.md](ablation-results.md) — bảng kết quả chính D.2
- [tailoring.md](tailoring.md) — cơ chế tailoring và vì sao chỉ mô hình phần bị động
- [evaluation.md](evaluation.md) — phương pháp đối chứng
