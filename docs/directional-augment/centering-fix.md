# Centering Fix

Bước 1 của [architecture.md](architecture.md). Là **sửa bug độc lập** — phải làm dù có làm
directional hay không. Chưa tiến hành; file này là bản tóm tắt để chốt trước khi sửa.

## Lỗi

`CompSelector.score_comp()` gộp 4–5 điểm thành phần bằng `total = Σ w[k] · parts[k]`, nhưng các
thành phần **không cùng quy ước gốc**:

| Thành phần | Không có tín hiệu → | Quy ước |
|---|---|---|
| `unit_score` | `0.0` | gốc-0 |
| `item_score` | `0.0` | gốc-0 |
| `emblem_score` | `0.0` (docstring nói thẳng *"Khong khop -> 0"*) | gốc-0 |
| `augment_score` | `0.0` | gốc-0 |
| `meta_score` | `0.5` (`0.5 + (raw−0.5)·trust`, `trust=0` khi `sample_n=0`) | **tâm-0,5** |
| `item_type_score` | `0.40` (`0.8 × 0.5 + 0.2 × 0.0`) | **tâm-0,5** (pha 20% `item_score`) |

Trộn hai quy ước trong một tổng có trọng số nghĩa là: **"không biết" được cộng điểm**, và cộng
**nhiều hay ít tuỳ trọng số của profile**. Vì mỗi archetype dùng một vector trọng số khác nhau,
điểm tổng **không so sánh được giữa các archetype**.

## Bằng chứng: code đã biết, nhưng chỉ sửa một nửa

`_evidence()` **đã** re-center đúng thành phần này:

```python
if adaptive and "item" in signal:
    signal["item"] = max(0.0, signal["item"] - 0.5) * 2.0
```

Nghĩa là tác giả đã nhận ra `item` là thang tâm-0,5 và xử lý — **nhưng chỉ trong `evidence`, không
trong `total`**. `evidence` vì thế đúng; `total` thì không. Đó cũng là lý do hai đại lượng này
"nói" hai điều khác nhau ở cùng một comp.

## Đo được

Sàn điểm khi board **không có tín hiệu nào** (81 comp, `stage 2-1`, board rỗng):

| profile | trọng số `item` | sàn | tối đa ở mức không tín hiệu |
|---|---|---|---|
| `fixed` (comp không nhãn archetype) | 0,25 (`item_score`, gốc-0) | **0,0000** | 0,1622 |
| `reroll` | 0,20 | **0,0800** | 0,1859 |
| `fast8` | 0,40 | **0,1600** | 0,3231 |
| `fast9` | 0,40 | **0,1600** | 0,3291 |

Chênh lệch sàn: **0,08** (fast vs reroll), **0,16** (fast vs comp không nhãn — vượt
`lock_margin` 0,12).

**Hệ quả xếp hạng, tái lập được.** Đặt 3/7 tướng lõi của comp reroll `Caitlyn Hunters` **đã 2
sao** ở 2-1:

```
1. Dragon 9          0.3291  fast9   unit=0.00  evidence=0.000
2. Draven AD 9       0.3291  fast9   unit=0.00  evidence=0.000
3. Ahri Morgana      0.3231  fast8   unit=0.00  evidence=0.000
4. Caitlyn Hunters   0.3183  reroll  unit=0.43  evidence=0.429   <-- comp DUY NHAT co bang chung
```

Ba comp **không có bằng chứng nào** đang xếp trên comp duy nhất có bằng chứng thật.

## Ba phương án sửa

| # | Cách | Ưu | Nhược |
|---|---|---|---|
| **A** | Đưa `item_type_score` và `meta_score` về **gốc-0**: không tín hiệu → `0.0` | Một quy ước duy nhất, đơn giản nhất để giải thích | `meta_score` mất khả năng **hạ điểm** comp có số liệu xấu (hiện `raw<0.5` kéo xuống dưới 0,5) |
| **B** | Đưa `unit`/`item`/`emblem`/`augment` về **tâm-0,5** | Giữ được khả năng hai chiều của mọi thành phần | Đổi nghĩa của "không có tướng lõi nào" từ *bằng chứng chống* thành *thiếu tín hiệu* — có thể đúng hơn, nhưng là đổi ngữ nghĩa |
| **C** | Giữ nguyên thành phần, **trừ sàn** của từng profile khỏi `total` | Ít xâm lấn nhất, không đổi ngữ nghĩa thành phần nào | Thêm một bước ẩn; sàn phải tính lại mỗi khi trọng số đổi |

**Đề nghị: A.** Lý do: `_evidence()` đã chọn quy ước gốc-0 (`max(0, x−0.5)·2`), nên A làm `total`
**khớp với `evidence`** thay vì thêm quy ước thứ ba. Và mất mát của A nhỏ: `meta_score` chỉ hạ được
điểm khi `sample_n ≥ 200` **và** `top4_rate < 0.55`, còn tín hiệu "comp này tệ" vẫn còn đường khác
để nói (`evidence`, và chuỗi lý do).

## Sửa cái này thì vỡ cái gì

Mọi ngưỡng **tuyệt đối** trên `total` đều được hiệu chuẩn theo thang hiện tại, nên phải hiệu chuẩn
lại:

| Ngưỡng | Giá trị | Ảnh hưởng |
|---|---|---|
| `stability.same_direction_min_score` | 0,60 | **Có.** Đã kiểm: 0,60 vẫn đạt được (điểm cao nhất với board hoàn hảo = 1,0000), nhưng ở 2-1 thì không — đúng ý đồ. Hạ sàn sẽ làm nó càng khó đạt hơn |
| `stability.pivot_flag_below` | 0,30 | **Có.** Hiện gần trùng sàn của fast8/9 (0,16–0,33) → nhiều comp fast bị cờ "nên đổi hướng" chỉ vì sàn thấp |
| `commitment.lock_margin` / `lean_margin` | 0,12 / 0,05 | **Có** — là hiệu số nên ít nhạy hơn, nhưng độ rộng thang đổi thì hiệu số cũng đổi nghĩa |
| `commitment.min_evidence` | 0,25 | **Không** — chạy trên `evidence`, vốn đã re-center đúng |
| `contest` | 0,20 | Chỉ khi `enable_scouting = true` (mặc định tắt) |

Ngoài ra: `tests/test_decision.py`, `tests/test_comp_archetype.py` có assert trên điểm số cụ thể —
sẽ đỏ, và đó là **đúng**: chúng đang khoá lại hành vi sai.

## Cách tiến hành đề nghị

1. Viết **test hồi quy trước**: comp có `evidence > 0` phải xếp trên comp có `evidence = 0` khi mọi
   thứ khác bằng nhau. Test này **đỏ ngay bây giờ** — đó là định nghĩa của bug.
2. Sửa theo phương án A.
3. Hiệu chuẩn lại 3 ngưỡng ở bảng trên, ghi số cũ/số mới vào file này.
4. Chạy lại `scripts/directional_baseline.py` — sàn đổi có thể làm tỉ lệ hoà điểm đổi theo, và đó
   là số cần biết **trước** khi làm directional.

> ⚠️ Không gộp bước này vào cùng commit với directional. Nếu gộp, không còn biết delta đo được đến
> từ việc sửa bug hay từ tính năng mới.

## Related

- [Architecture](architecture.md) — 4 bước gỡ nghịch lý con gà — quả trứng
- [Blind spots](blind-spots.md) §5 · [Baseline](baseline.md)
- `src/decision/comp_selector.py` · `config/scoring_weights.yaml` khối `comp_selector`
