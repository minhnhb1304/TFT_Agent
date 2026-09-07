# Tailoring

TFT **không** chào augment đều tay. Cơ chế tailoring ưu tiên những thẻ ăn khớp với trait
đang bật trên bàn. Coi pool là đều là một sai lệch **có hướng biết trước**.

## Sai theo hướng nào

Thẻ trùng trait cũng chính là thẻ được `BoardFit` (w2) cho điểm cao. Nên:

```
pool đều  ⟹  E[max] bị hạ thấp  ⟹  g(R) nhỏ đi  ⟹  ngưỡng θ* thấp đi
           ⟹  máy sợ reroll một cách nhân tạo
```

Một hệ thống dùng pool đều sẽ khuyên "chốt đi" ở đúng những tình huống mà người chơi giỏi
sẽ đổi — vì nó không tin rằng lần rút tới có cửa trúng trait.

## Cách xử lý

Một tham số, đặt trong trọng số rút chứ không phải trong điểm:

```
w_j  ∝  1 + β · 1{ trait_affinity(j) ∩ active_traits(S) ≠ ∅ }
```

`F_S` thành hàm phân bố thực nghiệm **có trọng số**. Chi phí bằng 0: tổng hậu tố có trọng
số thay cho phép đếm, vẫn `O(N)` lúc dựng và `O(log N)` mỗi truy vấn.

`β = 0` trả về pool đều — nhánh đối chứng sạch của ablation.

## Điều module này CỐ Ý không làm

Tailoring phụ thuộc board **tại thời điểm bấm đổi**, nên nó **điều khiển được**: cất hết
quân của một trait xuống ghế dự bị thì pool tailoring co lại quanh trait còn lại. Đây là
kỹ thuật đã được ghi nhận công khai (Dishsoap mô tả việc cất 3 Fortune để không bị chào
augment Fortune), và Riot đã nói thẳng là họ không muốn nó tồn tại.

Advisor mô hình hoá **phần bị động** của cơ chế và dừng ở đó:

1. SPEC §1.3 cấm hệ thống tác động vào game — nó chỉ đọc.
2. Khuyên người chơi xáo bàn để bóp pool là biến một công cụ đọc thành công cụ khai thác.
3. Riot có thể vá bất cứ lúc nào, và khi đó lời khuyên thành sai.

## Đo được (n = 20.000, bậc gold, chặng 2-1)

| | `first_look` | `sequential` | số lần đổi |
|---|---|---|---|
| β = 0 (pool đều) | 0,57074 | 0,58954 | **2,22** |
| β = 1 (có tailoring) | 0,57408 | 0,59405 | **2,36** |

Đúng hướng đã dự đoán: pool đều khiến chính sách đổi **ít hơn**. Chênh lệch nhỏ, và phần
sau giải thích vì sao.

## Giới hạn: `trait_affinity` rất thưa

Chỉ **20 trên 254** augment có `trait_affinity` khác rỗng — và **19 trong số đó là bậc
gold**. Nên thực tế:

- Ở bậc **silver** và **prismatic**, `tailoring_beta` gần như **không làm gì**.
- Kể cả ở gold, nó chỉ chạm vào 19/132 thẻ.

Đây phần lớn là **đúng với game**: đa số augment TFT là combat/econ/item chung chung, không
gắn với trait nào. Nhưng cơ chế tailoring thật của Riot nhiều khả năng còn cân theo **loại
carry** và **lối chơi**, chứ không chỉ theo trait. Mô hình hiện tại **chưa** bắt phần đó.

> ⚠️ Một cái bẫy đã dính khi đo lần đầu: dùng tên trait của set cũ (`Ravager`) thì **không
> khớp augment nào** và nhánh tailoring im lặng không làm gì — hai lần chạy ra số **giống
> hệt nhau**. Trait Set 18 có dạng `DA_Primal18`, `DA_18_Solar`, `DA_18_Coven`. Hai kết quả
> giống hệt nhau là dấu hiệu của một nhánh chết, không phải của một tham số vô hại.

## Trạng thái bằng chứng

Cơ chế tailoring **có tồn tại** — điều này được xác nhận qua nhiều nguồn cộng đồng. Cái
**chưa** xác nhận được là *độ mạnh* của nó: không nguồn công khai nào cho biết Riot cân
trọng số bao nhiêu.

Vì thế `β = 1.0` (thẻ trùng trait được chào gấp đôi) là một **giả định**, không phải số
đo. Nó nằm trong `config/scoring_weights.yaml` để ablation bật tắt được, và
`test_tailoring_beta_zero_recovers_the_uniform_pool` khoá nhánh đối chứng.

Hướng của sai lệch thì chắc chắn; độ lớn thì không. Nếu phải sai, sai với `β` hơi lớn còn
đỡ hơn `β = 0`: `β = 0` **chắc chắn** sai theo một hướng đã biết.

## Related

- [formalization.md](formalization.md) — `F_S` được định nghĩa ở đâu
- [architecture.md](architecture.md) — trọng số vào tổng hậu tố thế nào
- [mechanics-assumptions.md](mechanics-assumptions.md) — bảng trạng thái kiểm chứng
