# Session Handoff

Việc tồn đọng sau phiên 2026-10-05 → 08. Đọc file này trước khi bắt đầu phiên sau. Trạng thái
2026-10-08: **1027 test xanh, 4 commit đã push lên `main` (`253bafc`), duyệt tay xong 254/254**.

## Phiên 2026-10-10: duyệt vòng 2 đang dở (26/47)

Nhãn tay được so lại với MetaTFT và datatft, rồi mở vòng duyệt 2. **Chưa commit gì của phiên này.**

| Việc | Trạng thái |
|---|---|
| Vòng 2a: 32 lõi lệch cả hai nguồn hoặc tự mâu thuẫn | Xong 26; 6 lõi còn lại chuyển sang 2b |
| Vòng 2b: 47 lõi (`data/eval/augment_review_round2.json`) | **26/47**, dừng sau NO SCOUT NO PIVOT. Còn 21: Omega Riftbeast, Pandora's Bench, Pandora's Items I/II/III, Prismatic Destiny (2), Recombobulator, Silver Destiny (3), Weight The Worth, Solo Leveling, The Golden Dragon, The Golden Egg, The Tower, Time Skip, Trait Ladder, U.R.F, Warpath, Young and Wild and Free |
| Làm tiếp | `.venv\Scripts\python scripts\review_augment_features.py` → bộ lọc "Vòng 2: chưa duyệt lại" |
| Sau khi duyệt xong | So lại với hai nguồn, rồi việc code #1 bên dưới (áp nhãn tay vào bảng feature) |

Đổi trong phiên:

- **Bỏ luật "`utility` chỉ đi một mình"** (`check_feature`): người duyệt được gắn `utility` làm nhãn phụ cho lõi có cơ chế đặc biệt. [category-multilabel/definition.md](category-multilabel/definition.md)
- **Mã `type` của datatft đã xác nhận** từ mã nguồn trang (`DatabaseView-*.js`): 1 kinh tế, 2 chiến đấu, 3 trang bị, 4 tộc hệ, 5 độc quyền, 6 khác. Việc code #5 hết bị chặn; [offer-rounds/overview.md](offer-rounds/overview.md) vẫn ghi "chưa xác nhận", chưa sửa.
- **Trang duyệt**: bộ lọc "Vòng 2", thẻ báo "CHƯA LƯU ĐƯỢC" khi server từ chối (trước đó thẻ vẫn ghi "Đã lưu").
- **Khuôn ghi chú** người duyệt đang dùng: `<cơ chế> => nên/không nên chọn nếu <điều kiện>` và `đã có <lõi> => ưu tiên <lõi khác>`. Chưa code nào đọc; là nguyên liệu cho luật chuyên gia và directional.
- Phép so tay ↔ MetaTFT ↔ datatft mới chạy bằng script tạm, **chưa vào repo** (việc code #4).

## Làm ngay đầu phiên

| # | Việc | Ghi chú |
|---|---|---|
| 1 | ~~Commit, tách 4 commit~~ **Xong 2026-10-08** (`410af32` · `c719a17` · `616c928` · `253bafc`) | Commit nhãn duyệt tay mới chỉ ở local, chưa push |
| 2 | **Probe client trước 2026-10-09** | Hạn ngoài, ghi ở [next-steps.md](next-steps.md): `tools/probe_environment.py --closed` rồi `--seconds 5` trên máy game. Chưa rõ đã chạy chưa |
| 3 | Chạy lại server duyệt khi cần sửa nhãn | `.venv\Scripts\python scripts\review_augment_features.py` → `http://127.0.0.1:8766/` |

Đề xuất tách commit (thay đổi reroll phải đứng riêng để số trước/sau đọc được):

| Commit | Gồm |
|---|---|
| Schema nhãn | `categories` 1–3 nhãn, `carry_type` AD/AP/both/none, `frontline`, luật Emblem ⇒ `trait`, sửa BoardFit + cờ `legacy_tank_direction`, trang duyệt |
| Offer rounds | Crawler datatft, snapshot, trường `offer_rounds`, đăng ký nguồn, định nghĩa `tempo` |
| Sửa bậc | `resolve_tier` chỉ theo icon, luật `+`/`++` và số La Mã, `data/augment_tier_overrides.json`, 38 lõi đổi bậc |
| Reroll pool | Lọc theo bậc + lượt, cờ `reroll_policy.pool_by_offer_round`, tài liệu số đo |

## Chờ bạn quyết

| Câu hỏi | Bối cảnh |
|---|---|
| Giữ `pool_by_offer_round: true`? | Mục tiêu tăng ở 7/9 ô, **giảm nhẹ ở Kim cương 3-2** (−0,00014). [augment-reroll/offer-round-pool.md](augment-reroll/offer-round-pool.md) |
| `both_match = 0.8` có hợp lý? | Điểm BoardFit của lõi `both` trên board AD/AP. Là lựa chọn thiết kế, chưa chỉnh theo dữ liệu |
| Tách `tempo` thành 3 mức (`immediate / mixed / scaling`)? | Quyết bằng số: đếm lõi có chữ "lai" trong Ghi chú sau khi duyệt xong |
| Ghi mục "board_condition có cấu trúc" vào next-steps? | Trường này chữ tự do, không code nào đọc. Đã đề xuất, chưa được trả lời |
| `reroll` là nhãn riêng hay gộp vào `econ`? | Tạm giữ riêng tới khi làm `econ_type` (next-steps #2) |

## Việc của bạn: duyệt tay

Đã duyệt **254/254** (111 đúng · 140 sai · 3 chưa chắc), lưu ở `data/eval/augment_feature_review.json`.
Xong 2026-10-08; các gạch đầu dòng dưới là danh sách soát lại, việc code #1 đã hết bị chặn.

- **21 lõi "Cần xem lại"** vì đã chấp nhận `immediate` cho lõi chỉ có ở 2-1. Hedge Fund vẫn đang `immediate` trong bảng, chờ sửa thành `scaling`.
- Thêm vài lõi "Cần xem lại" từ đợt đổi schema (nhãn `tank` cũ, nhãn gốc đã đổi).
- 4 lõi Band of Thieves: `item_grants` phải là `CompletedItem`.
- Soát kỹ: nhãn phụ `combat` (máy đếm từ khoá), `frontline` của Forged in Strength / FOURcing / Gilded Steel, `both` (máy chỉ gắn 2 lõi), nhãn chính ★ của nhóm lõi cho ấn.
- Lõi "trả ngay một phần, còn lại scale": ghi **"lai"** vào Ghi chú.

## Việc code còn lại, theo thứ tự

| # | Việc | Chặn bởi |
|---|---|---|
| 1 | Áp nhãn tay vào `data/augment_features.json` dưới `manual-audit:…`, tính độ chính xác theo `extraction_method` | Duyệt xong (hoặc xong một phần) |
| 2 | Đo lại baseline (tỉ lệ hoà top-1…) với cờ `legacy_tank_direction` bật/tắt | — |
| 3 | ~~Chạy lại Monte-Carlo tháng 9~~ **Xong 2026-10-07** ([augment-reroll/ablation-results.md](augment-reroll/ablation-results.md)). Còn [tailoring-beta-sweep.md](augment-reroll/tailoring-beta-sweep.md) vẫn dùng pool cũ N = 132 | — |
| 4 | So `categories` với nhãn tay: Jaccard, P/R/F1 từng nhãn ([category-multilabel/phases.md](category-multilabel/phases.md) P5) | Việc 1 |
| 5 | Xác nhận ý nghĩa 6 mã `type` của datatft, rồi dùng làm nguồn so thứ hai (offer-rounds P6) | Cần ≥2 request nữa tới file JS tải sau |
| 6 | Tách `Anvil` thành 3 loại đe + `Artifact`, `RadiantItem` trong bộ trích và ItemFit | next-steps #6; hiện chỉ có ở trang duyệt |
| 7 | Việc cũ chưa đụng: centering fix `CompSelector`, `econ_type`, directional augment | next-steps #1–#3 |

## Không làm, đã có lý do

- Tách lõi trùng tên theo lượt (offer-rounds P5): 3/5 nhóm có lượt giống hệt nhau.
- Đưa `categories` vào chấm điểm (category-multilabel P6): dễ đếm hai lần; mặc định đóng.
- Hai artifact trên claude.ai ("Duyệt phân loại lõi", "Bảng phân loại lõi") **chưa xoá được**: gõ `/artifacts` rồi bấm `d`.

## Related

- [next-steps.md](next-steps.md): bảng việc tổng, hạn nộp
- [category-multilabel/overview.md](category-multilabel/overview.md): schema nhãn mới
- [offer-rounds/overview.md](offer-rounds/overview.md) · [offer-rounds/tier-mismatch.md](offer-rounds/tier-mismatch.md): lượt chào, bậc
- [directional-augment/feature-audit.md](directional-augment/feature-audit.md): định nghĩa từng trường
