# MetaTFT Tag Audit

Đối chiếu bảng feature lõi (`data/augment_features.json`) với nhãn tag của MetaTFT, để tìm
những dòng feature đáng đọc lại. Đo 2026-10-05.

> **MetaTFT KHÔNG phải ground truth.** Nhãn do một người (META Spencer) gán tay, không có tài
> liệu định nghĩa. Bất đồng là **tín hiệu audit** — quyết định từng ca phải dựa trên mô tả lõi
> (cdragon, `data/cdragon_cache`) và cơ chế game, không dựa trên việc MetaTFT nói gì.

## Nguồn và tái lập

| Bước | Lệnh / file |
|---|---|
| API | `GET https://api-hc.metatft.com/tft-stat-api/augments_tiers?tft_set=TFTSet18`, trường `content.content.tags` |
| Snapshot | `data/augment_tags.metatft.json` — chỉ giữ apiName có trong catalog, `meta` ghi `crawled_at`, `metatft_updated_at`, `labeled_by` |
| Crawl lại | `python scripts/crawl_metatft_tags.py --overwrite` (hoặc `--from-file <payload.json>` để không gọi API) |
| So | `python scripts/compare_metatft_tags.py [--list-fp]` |
| Logic + test | `src/eval/metatft_tags.py` · `tests/test_metatft_tags.py` |

Snapshot hiện tại: payload lấy 2026-10-05T07:12Z, MetaTFT cập nhật 2026-10-05T05:15Z. Khớp
253/254 apiName trực tiếp; thiếu `DA_BuildABud`.

## Hai bộ nhãn không cùng từ vựng

| Bên | Dạng nhãn |
|---|---|
| Ta | `category` đơn nhãn ∈ {econ, combat, item, trait, utility, reroll} + `tempo` + `econ_value` 0–3 + `trait_affinity` |
| MetaTFT | 1–3 tag ∈ {combat, items, econ, trait, scaling, misc} (122 lõi 1 tag, 106 lõi 2 tag, 25 lõi 3 tag) |

Ánh xạ gần đúng: `item→items`, `utility→misc`, `reroll→econ`, còn lại giữ tên.

## Số trước / sau audit

Trước = `main` @ `8237ae1`. Sau = `wf/augment-integrated` (gộp 4 nhánh + audit tổng hợp).

| Phép so | Trước TP/FP/FN/TN | Trước | Sau TP/FP/FN/TN | Sau |
|---|---|---|---|---|
| `category` ∈ tag MT | | 230/253 = 90,9% | | 244/253 = 96,4% |
| `category` == tag đầu MT | | 183/253 = 72,3% | | 195/253 = 77,1% |
| `econ_value>0` vs `econ` | 113/**17**/8/115 | 90,1% | 113/8/8/124 | 93,7% |
| `tempo=="scaling"` vs `scaling` | 25/**49**/11/168 | 76,3% | 35/26/1/191 | 89,3% |
| `trait_affinity` ≠ ∅ vs `trait` | 20/0/**18**/215 | 92,9% | 20/0/18/215 | 92,9% |
| `trait_affinity` ∪ `trait_count_reward` vs `trait` | 20/0/18/215 | 92,9% | 26/2/12/213 | 94,5% |
| `item_grants` ≠ ∅ vs `items` | 57/2/33/161 | 86,2% | không đổi | 86,2% |

> ⚠️ **Số "sau" không phải bằng chứng độc lập.** Dòng được audit chủ yếu được CHỌN vì bất đồng
> với MetaTFT, nên đồng thuận tăng một phần là do chọn mẫu. Bằng chứng ngược chiều: 8 dòng tempo
> và 1 dòng econ (Nesting Dolls) do bước tổng hợp sửa (áp định nghĩa cho mọi biến thể) đi **ngược** MetaTFT
> — `tempo` FP tăng 18 → 26. Định nghĩa từng trường: [feature-audit.md](feature-audit.md).

## Tín hiệu và kết luận

1. **Lõi cho trang bị bị chấm điểm kinh tế** — đã sửa (`econ_value` chỉ tính vàng/XP/reroll/
   tướng). Nhưng **giả thuyết "đây là nguồn suy biến ở `5edb568`" bị bác**: chấm lại 147
   scenario bằng scorer hiện tại, chỉ đổi bảng feature, hoà top-1 tuyệt đối là 16/147 trước và
   16/147 sau riêng nhánh econ. Nhóm `econ_value=3` co 75 → 56 nhưng tỉ lệ hoà không giảm.
2. **`tempo="scaling"` quá rộng** — đã sửa theo định nghĩa *đo bằng vòng đấu*. Hệ quả phụ: hoà
   tuyệt đối 16 → 20/147 (Baron's Lair = Hold The Line, Wisp Rebate++ = Champ Delivery++ sau khi
   trùng vector feature). 147 scenario chỉ có **30 bộ lựa chọn khác nhau** — đếm theo bộ: 3 → 4.
3. **Lõi thưởng độ sâu tộc hệ chung chung** — 6/18 nay có `trait_count_reward`
   ([trait-count-reward.md](trait-count-reward.md)); 12 lõi còn lại chỉ cho emblem/tướng.

## Giới hạn

- Chạy lại `scripts/compare_metatft_tags.py` sau mỗi lần sửa `augment_features.json`; đừng sửa
  tay bảng số. Snapshot tag giữ nguyên để so trước/sau.
- MetaTFT có thể đổi tag bất kỳ lúc nào, không versioned — luôn trích `crawled_at` khi dẫn số.
- Đồng thuận cao không chứng minh feature đúng: hai bên có thể cùng sai cùng kiểu, và dòng
  đồng thuận (TN/TP) chưa từng được audit.
- `econ` của MT không có định nghĩa và gồm cả tướng được tặng; ánh xạ `reroll→econ` là xấp xỉ.

## Related

- [overview.md](overview.md) — bản đồ tài liệu directional augment
- [feature-audit.md](feature-audit.md) — định nghĩa trường và nhãn `manual-audit`
- [blind-spots.md](blind-spots.md) — điểm nghẽn tầng feature (§2)
- [baseline.md](baseline.md) — số "TRƯỚC" và độ suy biến `econ_value`
- [contribution.md](contribution.md) — đóng góp #3
- `scripts/crawl_metatft_tiers.py` — cùng endpoint, phần tier list
