# MetaTFT Tag Audit

Đối chiếu bảng feature lõi (`data/augment_features.json`) với nhãn tag của MetaTFT, để tìm
những dòng feature đáng đọc lại. Đo 2026-10-05 trên `main` @ `8237ae1`.

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

## Số hiện tại

| Phép so | TP | FP | FN | TN | Đồng thuận |
|---|---|---|---|---|---|
| `category` ∈ tag MT | | | | | **230/253 = 90,9%** |
| `category` == tag đầu của MT | | | | | 183/253 = 72,3% |
| `econ_value>0` vs `econ` | 113 | **17** | 8 | 115 | 90,1% |
| `tempo=="scaling"` vs `scaling` | 25 | **49** | 11 | 168 | 76,3% |
| `trait_affinity` ≠ ∅ vs `trait` | 20 | 0 | **18** | 215 | 92,9% |
| `item_grants` ≠ ∅ vs `items` | 57 | 2 | 33 | 161 | 86,2% |
| `category=="combat"` vs `combat` | 63 | 3 | 23 | 164 | 89,7% |

Theo nguồn trích xuất (`category` ∈ tag MT): `deterministic-v1` 71/78, `llm:gemini-3.5-flash-lite` 159/175.

## Ba tín hiệu đáng đọc lại

1. **Lõi cho trang bị bị chấm điểm kinh tế.** 17 FP của `econ_value` phần lớn là lõi cho đồ
   (Big Grab Bag, Band of Thieves II/II+, Buried Treasures III, Lucky Gloves/+, Caretaker's
   Favor, Extra Buckles, Belt Overflow, Cooking Pot, Consuming Flora/+, ...) mang `econ_value`
   tới 3. `econ_fit.py` lấy `econ_value/3` làm cường độ, nên các lõi này đứng ngang lõi kinh tế
   mạnh nhất — nghi là một nguồn của độ suy biến `econ_value = 3` đo ở `5edb568`
   ([baseline.md](baseline.md)).
2. **`tempo="scaling"` quá rộng.** 49 FP / 11 FN; `tempo` cấp cho `tempo_fit.py`.
3. **Lõi thưởng độ sâu tộc hệ chung chung vô hình.** 18 lõi MT gắn `trait` nhưng
   `trait_affinity` rỗng (Verticality I–III, The Trait Tree/+, Branching Out/+, Spreading
   Roots/+, Legion Of Threes, Stand United, Hard Commit, ...). `trait_affinity` cố ý chỉ ghi tộc
   hệ cụ thể, nên scorer không thấy các lõi này — đúng điểm nghẽn tầng feature ở
   [blind-spots.md](blind-spots.md) §2, và chạm trực tiếp đóng góp #3.

## Giới hạn

- Số trên đo trên bảng feature tại `8237ae1`; sửa `augment_features.json` thì chạy lại script,
  đừng sửa tay bảng số. Snapshot tag giữ nguyên để so trước/sau.
- MetaTFT có thể đổi tag bất kỳ lúc nào, không versioned — luôn trích `crawled_at` khi dẫn số.
- Đồng thuận cao không chứng minh feature đúng: hai bên có thể cùng sai cùng kiểu.

## Related

- [overview.md](overview.md) — bản đồ tài liệu directional augment
- [blind-spots.md](blind-spots.md) — điểm nghẽn tầng feature (§2)
- [baseline.md](baseline.md) — số "TRƯỚC" và độ suy biến `econ_value`
- [contribution.md](contribution.md) — đóng góp #3
- `scripts/crawl_metatft_tiers.py` — cùng endpoint, phần tier list
