# Chính Sách Reroll Augment

`AugmentAdvisor.rank()` trả lời câu hỏi *"thẻ nào tốt nhất trong ba thẻ đang hiện"*.
Set 18 cho mỗi ô một nút đổi riêng, nên câu hỏi thật sự là một chuỗi quyết định:
*đổi hay chốt, và nếu đổi thì đổi ô nào*.

Module `src/decision/reroll_policy.py` trả lời câu hỏi thứ hai. Nó **cộng thêm** vào
advisor chứ không thay thế: `rank()` và `score_one()` không đổi một dòng nào.

## Kết quả chính

Bài toán nhìn có vẻ cần quy hoạch động nhiều tầng, nhưng nó sụp xuống còn **một phép
so sánh**:

```
REROLL  ⟺  g(R) − c > B
```

với `B` = điểm cao nhất hiện có, `R` = sàn giữ lại nếu đổi ô mục tiêu, và
`g(R) = E[max(R, σ)]` tính trên phân bố điểm của cả bậc augment đó.

Ba định lý dẫn tới đó nằm ở [dominance-theorem.md](dominance-theorem.md).

## Điều bất ngờ nhất

Trực giác phổ biến — *"gặp thẻ S thì chốt ngay để dành lượt đổi"* — **sai** khi lượt đổi
miễn phí. Đổi ô tệ nhất không đụng tới thẻ dẫn đầu, nên nó là một quyền chọn miễn phí:
giá trị dừng không thể tụt. Dừng sớm lúc đó là lỗ EV.

Hành vi dừng sớm chỉ hợp lý khi lượt đổi **có giá**. Giá đó là gì, và vì sao nó khác nhau
giữa các bậc, xem [depletion-cost.md](depletion-cost.md).

## Nhưng vét hết lượt cũng sai

Đo bằng mô phỏng (n = 10.000, bậc gold): chính sách **vét hết ba lượt** không hơn gì
chính sách **không đổi lần nào** — chênh lệch +0,0004 với khoảng tin cậy ôm lấy 0.

Lý do là một ràng buộc cơ chế dễ bỏ quên: lượt đổi thứ ba bắt buộc phải đổi chính ô đang
giữ thẻ tốt nhất, nên nó trả lại gần hết phần lợi của hai lượt đầu.

| chính sách | điểm TB | số lần đổi | Δ so với không đổi |
|---|---|---|---|
| không đổi (first_look) | 0,59808 | 0,00 | (mốc) |
| chọn bừa | 0,54896 | 0,00 | −0,04912 |
| vét hết ba lượt | 0,59845 | 3,00 | +0,00037 *(không phân biệt được với mốc)* |
| **tuần tự (module này)** | **0,61652** | **2,12** | **+0,01844** |
| biết trước (trần) | 0,61864 | 0,96 | +0,02056 |

Chính sách tuần tự lấy được **89,7%** khoảng cách tới trần biết trước. Bảng đầy đủ cả ba bậc:
[ablation-results.md](ablation-results.md).

⚠️ Đây là **chính sách so với chính sách trên chính hàm Score của hệ thống**, không phải
bằng chứng về placement. Xem [evaluation.md](evaluation.md).

## Bản đồ tài liệu

| File | Nội dung |
|---|---|
| [formalization.md](formalization.md) | Trạng thái, phương trình Bellman, mô hình chuẩn |
| [dominance-theorem.md](dominance-theorem.md) | T1/T2/T3 và chứng minh |
| [depletion-cost.md](depletion-cost.md) | `c(tier, stage)` đến từ đâu, và vì sao đo bằng σ |
| [tailoring.md](tailoring.md) | Vì sao pool đều là sai, và sai theo hướng nào |
| [heuristic-analysis.md](heuristic-analysis.md) | Khi nào trực giác của cao thủ đúng, khi nào hỏng |
| [architecture.md](architecture.md) | Hợp đồng dữ liệu, cache, ngân sách 5 ms |
| [evaluation.md](evaluation.md) | Đối chứng phản thực + phần bị chặn bởi Track B |
| [ablation-results.md](ablation-results.md) | Kết quả D.2: bảng ba bậc, KTC, trần giải tích |
| [tailoring-beta-sweep.md](tailoring-beta-sweep.md) | Nhánh β = 1 vs β = 0 |
| [mechanics-assumptions.md](mechanics-assumptions.md) | Cái gì đã kiểm chứng, cái gì là giả định |

## Related

- [SPEC.md](../../SPEC.md) — §3.5.4 scoring engine, §3.5.5 chính sách reroll, §12 đánh giá
- [dev_log.md](../../dev_log.md) — mục 2 (số liệu augment), mục 9 (VOD Set 18)
- [augment-reroll-plan.md](../augment-reroll-plan.md) — kế hoạch đã duyệt
