# Tier Mismatch

38 lõi mà vị trí trong ba danh sách `hexs18` của datatft khác bậc cũ của ta (62/132/60).
**Đã giải quyết 2026-10-06 theo phán quyết của người dùng** (người chơi thật): cả 38 lõi đổi
bậc, bậc mới là 70/115/69, còn **0 lõi** lệch với datatft. Mọi số liệu theo bậc đo trước ngày
này dùng bậc sai.

## Phán quyết

| Nhóm | Số lõi | Luật | Thực hiện |
|---|---|---|---|
| A. Biến thể `+` / `++` | 20 | Cùng một lõi với bản gốc, chỉ chào ở lượt muộn hơn → **cùng bậc** với bản gốc. Hậu tố không nói gì về bậc | Luật trong code, `tier_source = variant-of-base` |
| B. Tên có số La Mã | 11 | Số La Mã là **thứ hạng trong họ** (II cao hơn I), không phải bậc tuyệt đối: `I` có thể đã là gold, khi đó `II` là prismatic | Luật trong code, `tier_source = roman-order` khi phải sửa |
| C. Icon CDragon sai | 7 | datatft đúng, icon CDragon sai. Không luật nào suy ra được | File dữ liệu `data/augment_tier_overrides.json`, `tier_source = user-override` |

## Cách giải bậc hiện tại

`src/knowledge/augment_catalog.py`. Tên **không còn** cho bậc tuyệt đối.

| Bước | Ở đâu | Làm gì | Số lõi mang nguồn này |
|---|---|---|---|
| 1 | `resolve_tier` | `missing-tN.tex` | 38 |
| 2 | `resolve_tier` | số La Mã cuối đường dẫn icon (`_ii.tex`, `-ii.tex`) | 149 |
| 3 | `resolve_tier` | chữ số cuối đường dẫn icon | 26 |
| 4 | `_apply_family_rules` (B) | trong một họ La Mã, bậc phải tăng ngặt; vi phạm thì nâng bản số cao lên (bậc bản thấp + 1), không vượt 3 | 1 |
| 5 | `_apply_family_rules` (A) | biến thể lấy bậc của bản gốc (`DA_XPlus` → `DA_X`, kể cả `DA_BandOfThievesIIPlus`, `DA_18_PrimalAugmentPlus_Sivir`) | 33 |
| 6 | `_apply_tier_overrides` (C) | ghi đè theo file; tên lạ trong file thì **dừng ngay** | 7 |

Chỉ riêng ba bước icon đã cho 68/118/68 và khớp datatft ở 30/31 lõi nhóm A + B. Bước 4 sửa
đúng một lõi: `DA_TonsOfStatsII` dùng chung icon `_ii` với bản I (bậc 2) → 3. Bước 5 không đổi
bậc nào trên dữ liệu hiện tại (icon của 33 biến thể đã trùng bản gốc); nó là rào cho set sau.

Luật không áp được thì **không đoán**, ghi vào `AugmentCatalog.tier_rule_gaps`. Hiện có 7 biến
thể không có bản gốc trong catalog, giữ bậc icon (đều trùng datatft): `NestingDollsPlus`,
`NestingDollsPlusPlus`, `18_WispRebatePlus`, `18_WispRebatePlusPlus`, `InvestedPlus`,
`InvestedPlusPlus`, `MoneyHungryPlus`.

## Danh sách đã đổi

Ký hiệu `cũ → mới`, `DA_` lược bỏ. Tổng 38: 1→2 ×4, 2→1 ×7, 2→3 ×18, 3→1 ×5, 3→2 ×4.

| Nhóm | Đổi | Lõi |
|---|---|---|
| A | 2 → 1 | `18_BranchingOutPlus`, `18_ResidualMagicPlus`, `18_WispRebatePlus`, `ChampDeliveryPlus`, `CognitiveTaxPlus`, `SilverDestinyPlus` |
| A | 3 → 1 | `18_ResidualMagicPlusPlus`, `18_WispRebatePlusPlus`, `ChampDeliveryPlusPlus`, `SilverDestinyPlusPlus` |
| A | 2 → 3 | `BandOfThievesIIPlus`, `GoldenGamblePlus`, `InvestedPlus`, `LuckyGlovesPlus`, `NestingAnvilsPlus`, `NestingDollsPlus`, `PrismaticDestinyPlus`, `TheTraitTreePlus` |
| A | 3 → 2 | `BoosterPackPlusPlus`, `HeroicGrabBagPlusPlus` |
| B | 1 → 2 | `BronzeForLifeI`, `InvestmentStrategyI`, `JeweledLotus_I`, `TonsOfStatsI` |
| B | 2 → 3 | `18_LuxAugmentII`, `BandOfThievesII`, `BronzeForLifeII`, `InvestmentStrategy`, `JeweledLotus_II`, `WorththeWaitII`, `TonsOfStatsII` (`roman-order`) |
| C | 2 → 1 | `PandorasBench` |
| C | 2 → 3 | `DeadlierBlades`, `DeadlierCaps`, `Flexible` |
| C | 3 → 1 | `ForgeAFriend` |
| C | 3 → 2 | `ConstructACompanion`, `WovenMagic` |

## Rào chống lệch lại

| Test (`tests/test_augment_catalog.py`) | Khoá điều gì |
|---|---|
| `test_tiers_agree_with_datatft_lists` | Bậc của ta = `list_index + 1` cho cả 254 lõi. Test chỉ **so sánh**; không code nào đọc `list_index` làm bậc |
| `test_plus_variants_share_the_base_tier` | Luật A trên 33 biến thể |
| `test_roman_numeral_is_rank_within_family_not_absolute` | Luật B: mọi họ tăng ngặt |
| `test_user_overrides_fix_group_c`, `test_overrides_are_optional_and_checked` | File override; thiếu file vẫn chạy, tên lạ thì lỗi |

Đỏ lên nghĩa là CDragon hoặc datatft đổi dữ liệu: xem lại bằng kinh nghiệm chơi, **đừng** ép cho khớp.

## Đã sinh lại

| Thứ | Kết quả |
|---|---|
| `data/augment_features.json` (`--migrate`) | 38 dòng đổi, chỉ trường `tier`; 81 dòng manual-audit và `offer_rounds` giữ nguyên |
| `data/augment_stats.csv` (mock, neo theo bậc) | 38 dòng đổi |
| Pool reroll theo (bậc, lượt) | Đo lại: [../augment-reroll/offer-round-pool.md](../augment-reroll/offer-round-pool.md) |
| [../augment-reroll/ablation-results.md](../augment-reroll/ablation-results.md) | Chạy lại 2026-10-07 với bậc đã sửa + pool theo lượt |

## Related

- [overview.md](overview.md): vấn đề, số đo, kết luận tóm tắt
- [source.md](source.md): cấu trúc `hexs18`, trường `img` và `list_index`
- [phases.md](phases.md): P4 dùng bậc đã sửa
