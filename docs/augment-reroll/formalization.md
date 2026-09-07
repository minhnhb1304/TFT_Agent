# Hình Thức Hoá

## Trạng thái

Xét **một** chặng augment (2-1, 3-2 hoặc 4-2). Trên màn hình luôn có đúng 3 ô.

| Ký hiệu | Nghĩa |
|---|---|
| `L` | điểm cao nhất trong các ô **đã tiêu** lượt đổi — an toàn vĩnh viễn |
| `v₍₁₎ ≤ … ≤ v₍ₙ₎` | điểm các ô **còn giữ** lượt đổi |
| `n` | số lượt đổi còn lại (mỗi ô một lượt) |
| `F_S` | phân bố của `Score(a │ S)` trên pool cùng bậc |
| `c` | giá phải trả cho một lần đổi |

`F_S` **không phải một giả định tham số**. Nó là hàm phân bố thực nghiệm chính xác thu
được bằng cách chấm điểm mọi augment trong bậc đó với trạng thái hiện tại. Vì vậy nó
tự động phản ứng theo board, HP, gold, item — không cần mô hình sinh nào cả.

## Phương trình Bellman

```
V(L, ∅)          = L
V(L, v₍₁..ₙ₎)    = max( max(L, v₍ₙ₎),                          ← PICK
                        E[ V(max(L,σ), v₍₂..ₙ₎) ] − c )        ← REROLL ô tệ nhất
```

Đổi ô `v₍₁₎`: thẻ mới rơi vào ô đó và **mất lượt**, nên nó gia nhập `L`. Thẻ cũ biến mất
hẳn — không chọn lại được.

Một hệ quả đáng chú ý: **vế continuation không chứa `v₍₁₎`**. Điểm của thẻ sắp bị đổi đi
không ảnh hưởng gì tới giá trị của việc đổi nó, khi `n ≥ 2`.

## Ràng buộc cơ chế dễ bỏ quên

Ba lượt đổi tiêu vào **ba ô khác nhau**, nên tập thẻ có thể đang giữ thu hẹp dần:

| số lần đổi | ba ô đang hiện | thẻ tốt nhất giữ được |
|---|---|---|
| 0 | v₁, v₂, v₃ | `max(v₁,v₂,v₃)` |
| 1 | v₂, v₃, r₁ | `max(v₂,v₃,r₁)` |
| 2 | v₃, r₁, r₂ | `max(v₃,r₁,r₂)` |
| 3 | r₁, r₂, r₃ | `max(r₁,r₂,r₃)` |

Lượt thứ ba **bắt buộc** đổi ô đang giữ thẻ ban đầu tốt nhất. Đây là lý do "cứ đổi cho
hết" là một lời khuyên tồi — xem bảng đo ở [overview.md](overview.md).

## Mô hình chuẩn — và cái tên dễ đặt sai

| Mô hình | Biết F? | Nhớ lại được? | Mục tiêu |
|---|---|---|---|
| Secretary problem | không | **không** | P(chọn đúng cái tốt nhất) |
| Gilbert–Mosteller | có | không | P(chọn đúng cái tốt nhất) |
| Cayley–Moser / house-selling | có | **không** | E[giá trị], có hạn chót |
| **McCall sequential search** | **có** | **có** | **E[giá trị] − chi phí tìm** |

Bài toán này thuộc dòng cuối: **biết `F_S`** (tự tính được) và **giữ lại được** thẻ đã
thấy (nó vẫn nằm trên màn hình). Vì thế:

- Gọi đây là *secretary problem* là **sai** — secretary là không nhớ và không biết F.
- Gọi đây là *Cayley–Moser* cũng **sai** — Cayley–Moser đặc tả rõ là **không** nhớ lại.

Công thức đệ quy dùng ở đây là dạng house-selling **có nhớ**, tức thay giá trị dừng bằng
`max(tốt nhất đang giữ, giá trị tiếp tục)`. Tài liệu gốc gọn nhất: Ferguson,
*Optimal Stopping and Applications*, chương 2 —
<https://www.math.ucla.edu/~tom/Stopping/sr2.pdf>.

## Vì sao horizon thật sự là 1

Với `n ≥ 2`, việc đổi ô tệ nhất **không đụng** tới `B = max(L, v₍ₙ₎)`. Nên bài toán không
có sự đánh đổi liên thời gian nào: mỗi lần đổi là một quyền chọn độc lập trên cùng một
sàn. Vế phải của luật dừng giảm đơn điệu theo `B`, nên vùng dừng **liên thông** và luật
một bước chính là luật tối ưu.

Nói cách khác: toàn bộ phần "optimal stopping" gói lại thành một phép so sánh, và mọi
độ khó còn lại nằm ở chỗ **ước lượng `F_S` cho đúng** — tức ở hàm Score, không ở luật dừng.

## Related

- [dominance-theorem.md](dominance-theorem.md) — chứng minh T1/T2/T3
- [tailoring.md](tailoring.md) — vì sao `F_S` không đều
- [architecture.md](architecture.md) — `F_S` được tính và cache thế nào
- [overview.md](overview.md) — tóm tắt
