# Baseline

Số **"TRƯỚC"** của tính năng directional, chốt tại `347f5d1` ngày **2026-09-30**. Chúng biến mất
ngay khi scorer đổi, nên phải chốt trước khi code động vào — không có "trước" thì "sau" chỉ còn
là lập luận.

```powershell
.venv\Scripts\python scripts/directional_baseline.py
```

## Trên scenario đã log

| Chỉ số | Giá trị | Xác nhận |
|---|---|---|
| Top-1 **hoà tuyệt đối** → alphabet chọn hộ | **16/147 = 10,9%** | [blind-spots §3](blind-spots.md) |
| Top-1 và #2 cách nhau **< 0,01** | **42/147 = 28,6%** | Vùng cần lý do rẽ nhánh |
| Lõi có `econ_value > 0` | **131/254 = 51,6%** | [blind-spots §1](blind-spots.md) |
| Nhóm lớn nhất cùng `econ_value = 3` | **75/131** | 75 lõi hoà ở đỉnh chiều kinh tế |

Phân bố `econ_value`: `{1: 17, 2: 39, 3: 75}`.
Audit 2026-10-05 co nhóm này 75 → 56 nhưng **không** hạ hoà điểm — xem [metatft-tag-audit.md](metatft-tag-audit.md).

> Mẫu là 147 scenario trong `data/scenarios/` (3 bản ghi bị bỏ vì chỉ có một lựa chọn — một lựa
> chọn thì không thể hoà; tính vào sẽ làm loãng tỉ lệ). Đây là scenario **chưa gắn nhãn**, nên con
> số đo *tính chất của hàm điểm*, không phải chất lượng tư vấn — nó không cần nhãn để đúng.
>
> **Cả 150 bản ghi dùng chung đúng một bộ trọng số** (`base .30 · board_fit .30 · econ_fit .15 ·
> item_fit .15 · tempo_fit .10`) — đã kiểm. Nên tỉ lệ hoà không phải hệ quả của việc trộn nhiều
> phiên bản scorer, một phản biện dễ gặp với dataset tích luỹ dần.

## Khối lượng hoà điểm trong cả một bậc

Chỉ số trên đo trên ba thẻ **thực sự được chào**. Phép đo dưới đây rộng hơn: tỉ lệ lõi **cùng
bậc** nằm trong một nhóm hoà điểm chính xác, ở một trạng thái cho trước
([synthesis](../../research/260930-directional-augment/synthesis.md) §2.2).

| Trạng thái | tier 1 | tier 2 | tier 3 | nhóm lớn nhất |
|---|---|---|---|---|
| 2-1, board tạm | 74% | **80%** | 72% | 10 |
| 3-2 | 76% | 80% | 75% | 10 |
| 4-2, board trống | 90% | **94%** | 90% | 26 |
| 4-2, **board đã phát triển** (carry 2 sao + 2 đồ, 3 trait bật) | 84% | **83%** | 80% | 23 |

Dòng cuối là dòng quan trọng nhất: **hoà điểm không biến mất khi bàn cờ đã nói rõ hướng.** Nếu nó
biến mất thì vấn đề chỉ là "thiếu thông tin ở đầu trận"; nó không biến mất, nên vấn đề là **bản
thân hàm điểm thiếu độ phân giải**.

**Độ phân giải của bảng xếp hạng:** khoảng cách trung vị giữa hai mức điểm kề nhau chỉ
**0,003–0,0045**, trên tổng độ rộng 0,24–0,30.

## Ví dụ tái lập được

2-1, board tạm, `gold=22 level=4 hp=90 xp=2`:

```
DA_AdvancedLoanPlus   0.5965     (gold thuần)
DA_TheTraitTreePlus   0.5965
DA_TradeSector        0.5965     (reroll-econ)

margin.compare() -> gap = 0.0, parts = {}
margin.explain() -> ''
```

Alphabet chọn `Advanced Loan+`. Overlay hiện nó ở #1 **không kèm lý do nào**. Và vì tie-break tất
định, cùng một lõi thắng **mọi lần** ở tình huống này.

Đây cũng là đính chính cho ví dụ trong bản đầu: nhóm hoà thật không phải *XP vs reroll* (hai cái
đó khác `econ_value` nên không hoà) mà là **reroll vs gold thuần** — tức đúng hai họ mà taxonomy
`econ_type` cần tách ra.

## Tầng feature

| | tất định | đã lưu | LLM đổi |
|---|---|---|---|
| `category == "reroll"` | 20 | **7** | 13/13 |
| `extraction_method == llm:*` | — | 175/254 | — |

Chi tiết và danh sách 13 lõi: [blind-spots §2](blind-spots.md).

## Tiêu chí thành công

Mục tiêu trực tiếp của tính năng là **hạ con số 10,9%** (và khối lượng hoà 74–94%) mà **không**
làm xấu các chỉ số đã có. Đo bằng delta **directional bật vs tắt** trên tập held-out
([dataset split](../playtest-fixes/dataset-split.md)).

> ⚠️ Cảnh báo từ tài liệu tie-handling (arXiv:2609.26977): nếu số hạng mới **tương quan** với các
> thành phần đã có — `item_fit` và `board_fit` vốn đã ngầm mã hoá "đội hình nào" — thì nó **sẽ
> không** phá được hoà điểm. Phải kiểm tương quan giữa số hạng mới và 5 thành phần cũ trước khi
> tin vào delta.

## Tái lập

- `scripts/directional_baseline.py` — CLI, `--json` để lấy số thô
- `tests/test_directional_baseline.py` — **11 test**, theo nguyên tắc README: mỗi con số trong
  báo cáo phải có một test dựng lại được

Hai chỗ có test riêng vì sai một cách im lặng: dựng lại `total` từ `component_scores × weights`
thay vì đọc `ranking` (đã sắp xếp nên không nói được về hoà điểm), và bỏ bản ghi một lựa chọn ra
khỏi mẫu thay vì tính là "không hoà".

## Related

- [Overview](overview.md) · [Blind spots](blind-spots.md) · [Architecture](architecture.md)
- [Research synthesis](../../research/260930-directional-augment/synthesis.md) §2
