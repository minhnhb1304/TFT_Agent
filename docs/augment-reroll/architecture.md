# Kiến Trúc & Ngân Sách 5 ms

## Câu trả lời đến từ phép đo, không phải phỏng đoán

Đo trên máy này (`.venv`, Python 3.14.7, 50 lần lặp):

| Đường | p50 | p95 |
|---|---|---|
| `score_one` × bậc gold (N=132) | 1,39 ms | 2,18 ms |
| `score_one` × cả 254 | 4,52 ms | **12,24 ms** ❌ |
| `rank(3)` (đường hiện có) | 0,05 ms | 0,11 ms |

Hai kết luận:

1. **Không bao giờ chấm cả bảng.** Lọc theo bậc trước. Cả ba thẻ một chặng cùng một bậc
   (đã đối chiếu trên frame Set 18 thật), nên việc lọc là chính xác chứ không phải xấp xỉ.
2. **Không cần viết lại bằng NumPy.** Dựng pool một lần đã nằm trong ngân sách.

## Cache một lần, truy vấn nhiều lần

Trạng thái game **đứng yên** trong ~30 giây của màn chọn augment. Nên:

```
vào màn chọn  →  pool_distribution()  ~2,2 ms p95, MỘT lần
mỗi quyết định →  advise_reroll(pool=cache)  ~vài microsecond
```

`PoolDistribution` giữ điểm đã sắp tăng dần cộng **tổng hậu tố có trọng số**, nên
`expected_max(floor)` là một lần `bisect` cộng hai phép cộng:

```
g(floor) = floor · W(≤floor) + Σ_{σ_j > floor} w_j·σ_j
```

Chính xác tuyệt đối, không xấp xỉ. `test_expected_max_matches_brute_force` khoá điều này
tới 1e-12 — đây là nền móng, nếu nó lệch thì mọi ngưỡng đều sai mà không có triệu chứng
nào khác.

## Vì sao KHÔNG viết bản NumPy

Một bản vectorised sẽ phải **cài lại cả năm scorer**. Hai bản cài đặt của cùng một công
thức sẽ trôi khỏi nhau, và khi trôi thì xếp hạng và chính sách reroll sẽ bất đồng — kiểu
hỏng khó thấy nhất.

Nếu phép đo **khi game đang chạy** (SPEC §12.1: "đo khi game đang chạy — không đo trên máy
rảnh") cho thấy lần dựng pool quá chậm, thì mới thêm, và phải kèm test đối chiếu khẳng
định kết quả trùng khít `score_one` trên mọi augment × một ma trận trạng thái.

## Hợp đồng dữ liệu

| Kiểu | Vai trò |
|---|---|
| `RerollState` | ô nào còn lượt (`available`), thẻ đã lộ (`burned`) |
| `PoolDistribution` | `F_S` có trọng số + `sigma` + provenance |
| `RerollAdvice` | `action` (LUÔN có), `target_slot`, `fallback_slot`, `expected_gain`, `threshold`, `evidence` |
| `RerollTuning` | đọc từ khối `reroll_policy:` trong YAML |

API cộng thêm trên `AugmentAdvisor` — `rank()` và `score_one()` **không đổi**:

```python
def pool_distribution(self, tier, state, exclude=()) -> PoolDistribution
def advise_reroll(self, ranking, state, rerolls=None, pool=None) -> RerollAdvice
```

## Trạng thái lượt đổi phải được TRUYỀN VÀO

Frame Set 18 thật cho thấy **ba nút đổi riêng từng thẻ** và **không có bộ đếm số nào** trên
màn hình. Nên lớp nhận dạng không thể suy ra số lượt còn lại từ một khung hình đơn lẻ.

`RerollState` là tham số tường minh, mặc định `(True, True, True)` — tức trạng thái vừa vào
màn chọn. Nhờ vậy toàn bộ chính sách test được offline ngay hôm nay, còn lớp thị giác
(ROI nút đổi + bộ phân loại trạng thái sáng/mờ) là việc của Track B.

## Mức bằng chứng KHÔNG chặn hành động

`advise_reroll` **luôn** trả về một hành động cụ thể.

`B` và `F_S` cùng sinh ra từ **một** hàm điểm, nên phép so sánh giữa chúng **bất biến qua
mọi phép hiệu chỉnh đơn điệu** của `Score`. Nó vẫn đúng khi `Base` trung tính ở cả 254
augment. Từ chối trả lời là vứt đi một so sánh hợp lệ chỉ vì thiếu một phép hiệu chuẩn
tuyệt đối.

Cái **không** tuyên bố được là "ngưỡng này quy ra placement". Trường `evidence` hạ giọng
câu chữ và thêm dấu `?` trên overlay; nó không đụng tới hành động.
`test_uncalibrated_pool_still_returns_a_concrete_action` là test hồi quy cho lỗi này.

Lưu ý: bộ số giả lập bịa sẵn `sample_n > 200` nên `AugmentStats.is_evidence` trả True cho
nó. `is_fabricated()` nhìn thêm tên nguồn, vì `evidence` điều khiển câu cảnh báo.

## Related

- [formalization.md](formalization.md) — `F_S` là gì
- [tailoring.md](tailoring.md) — trọng số vào đâu
- [evaluation.md](evaluation.md) — đo cái gì
