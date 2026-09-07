# Giá Của Một Lần Đổi

`c` **không phải** một hằng số để chỉnh cho ra kết quả đẹp. Dưới giả định
[burn-on-reveal](mechanics-assumptions.md), nó là **phần giá trị quyền chọn tương lai bị
huỷ** khi ta để lộ thêm một thẻ.

```
c(tier, stage) = γ(tier, stage) · E_ã[ 1{ã không được chọn} · ΔW(ã) ]
```

- `γ` = xác suất một chặng sau lại rút đúng bậc này
- `ΔW(ã)` = phần giá trị tương lai mất đi vì `ã` bị đốt

## Chi phí đến từ đâu — và không đến từ đâu

Đốt một thẻ **tệ** thực ra **có lợi** cho pool tương lai: nó dọn bớt rác. Chi phí chỉ phát
sinh ở **trường hợp ở giữa**: thẻ vừa lộ ra **tốt nhưng không hơn `B`**, nên bị đốt mà
không được lấy.

Đó chính xác là kịch bản "viên Prismatic S-tier thứ hai mà bạn không được phép cầm".

## Ba chế độ

| Chế độ | Vì sao | Hệ quả |
|---|---|---|
| Prismatic (N = 60), chặng 2-1 | pool nhỏ nhất; với một lối chơi cụ thể chỉ 3–5 thẻ thật sự S | `c > 0` ⟹ dừng sớm có thể tối ưu |
| Gold (N = 132) / Silver (N = 62) | đốt ~1% pool | `c ≈ 0` ⟹ vét lượt đổi |
| Bất kỳ bậc nào, chặng 4-2 | **không còn chặng sau để đốt**, `γ = 0` | `c ≡ 0` tuyệt đối |

Dòng cuối là **điều kiện biên**, không phải lựa chọn hiệu chỉnh. Nó được khoá bằng test
`test_stage_four_costs_nothing_for_every_tier`.

## Vì sao là bảng tra, không phải công thức chạy lúc runtime

`γ` cần **bảng liên hợp** của bậc augment qua ba chặng. Riot dùng bảng chung cho cả phòng
và **không công bố cho Set 18** — chỉ tìm được số của Set 16 (28/62/10 · 35/45/20 ·
6/74/20). Các chặng **không độc lập**, nên không được nhân biên với nhau.

Tính `ΔW` lúc runtime cũng khả thi về mặt toán — với điểm đã sắp tăng dần, xác suất `σ_j`
là max của `m` lần rút không lặp từ `N` là `C(j−1, m−1)/C(N, m)`, nên
`W(P) = Σ_j σ_j·C(j−1,m−1)/C(N,m)` và bỏ một phần tử là một lần đánh lại chỉ số `O(N)`.

Nhưng: (a) `γ` không quan sát được nên tử số vẫn phải đoán, và (b) chạy tổ hợp thuần
Python trên `N = 132` mỗi quyết định là rủi ro không cần thiết cho ngân sách 5 ms — để
đổi lấy một con số gần như không nhúc nhích.

**Kết luận: `c` là một phép tra bảng `O(1)`.** Lập luận ở trên tồn tại để giải thích
*hình dạng* của bảng, không phải để chạy.

## Đơn vị: bội của σ, không phải điểm thô

**Đây là chỗ suýt sai.** Bảng số ban đầu (prismatic 0,08 / gold 0,01) được đặt ra mà chưa
đối chiếu với thang đo thật của `Score`.

Đo ngày 2026-09-07 trên trạng thái thật:

| bậc | N | sd(Score) | tích phân đuôi tại q75 | tại q90 |
|---|---|---|---|---|
| silver | 62 | 0,0437 | 0,0057 | 0,0013 |
| gold | 132 | 0,0551 | 0,0072 | 0,0020 |
| prismatic | 60 | 0,0547 | 0,0093 | 0,0043 |

Đọc bảng `c` như **tuyệt đối** thì gold `0,01` và prismatic `0,08` đều **lớn hơn mọi lợi
ích có thể có** — chính sách sẽ không bao giờ đổi thẻ, trái hẳn ý đồ đã phát biểu.

Đọc như **bội của σ của chính pool đó** thì đúng những con số ấy lại rơi vào chỗ:

| bậc, chặng | hệ số | `c` thật | dừng đổi khi thẻ dẫn đầu vượt |
|---|---|---|---|
| gold, 2-1 | 0,01 σ | 0,00055 | ~q97 — gần như luôn đổi ✔ |
| prismatic, 2-1 | 0,08 σ | 0,00437 | ~q85 — dừng khi đã có thẻ mạnh ✔ |
| prismatic, 4-2 | 0,00 | 0,00000 | ~q98 — vét lượt ✔ |

Cách đọc theo σ còn khiến bảng **không phải hiệu chỉnh lại** khi `Score` đổi thang đo —
ví dụ khi số liệu thật thay cho `MOCK-NOT-REAL`. `cost_unit: absolute` giữ ngữ nghĩa cũ,
dành cho ablation.

## Trạng thái bằng chứng

Các con số trong `cost_matrix` là **tiên nghiệm do người đặt**, chưa fit trên dữ liệu nào.
Thứ đã được kiểm chứng là **thứ tự** (prismatic > gold, và 4-2 = 0), không phải độ lớn.

## Related

- [dominance-theorem.md](dominance-theorem.md) — `c` vào luật dừng ở đâu
- [mechanics-assumptions.md](mechanics-assumptions.md) — burn-on-reveal chưa được xác nhận
- [evaluation.md](evaluation.md) — cách đo độ nhạy theo `c`
