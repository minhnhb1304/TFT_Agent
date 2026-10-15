# Session Handoff

Việc tồn đọng sau phiên 2026-10-05 → 13. Đọc file này trước khi bắt đầu phiên sau. Trạng thái
2026-10-15: **1034 test xanh, mọi commit đã push lên `main` (`b2b7544`), nhãn tay đã vào bảng**.

## Phiên 2026-10-13: probe client mới

Client TFT standalone: cửa sổ `'TFT  '`, lớp `UnrealWindow`, borderless 1920×1080. Đã push (`e55dee6`).

| Mục | Kết quả (`data/live_probe/20261013_*`) |
|---|---|
| WGC | Chạy, không hộp thoại, không viền vàng, **49,9 fps**, khung đầu 0,37 s |
| HUD, ván Normal (22:29) | Đúng cả 7 trường: 2-6 · vàng 31 · cấp 4 · XP 6/10 · máu 71 · chuỗi −5 |
| Màn chọn lõi (23:21, 23:32) | Nút đổi lõi `active` ×3 đúng. Stage, máu rỗng: ván **người đấu máy**, bố cục khác (lõi ở 1-5, 2-5) |
| Độ trễ HUD | ~1,1 s máy rảnh. `hud_read_s` ở 23:21 và 23:32 là số cache, **không trích**. 12 s ở 22:29 gồm nạp OCR |
| Màn chọn lõi ván Normal (2026-10-15 16:58, `b2b7544`) | Lõi 4-2: stage `4-2` đúng, nút đổi lõi `disabled / active / active` đúng với ảnh. Thanh HUD ẩn nên vàng, cấp, máu rỗng. Độ trễ ~2 s |
| HUD ván Normal (2026-10-15 16:52, 16:56) | Độ trễ **15–26 s**, CPU 97% trong ảnh. 16:52 mất stage, 16:56 mất máu |
| Còn thiếu | Độ trễ HUD khi game chạy chưa đạt: lần 2–4 (OCR đã nạp) vẫn 15–26 s. Màn chọn lõi ẩn thanh HUD: cần giữ vàng, cấp, máu từ khung trước. Máy test chưa có khoá Gemini |

Chưa sửa: [live-mode/phase-0-spike.md](live-mode/phase-0-spike.md), [live-mode/probe-runbook.md](live-mode/probe-runbook.md) còn ghi tên
cửa sổ cũ. Cô kiểm tra tiến độ lần 1 (dòng 1 kế hoạch): trang tóm tắt chưa soạn, chờ chọn dạng.

## Phiên 2026-10-10 → 12: duyệt vòng 2 xong, nhãn tay đã vào bảng

Vòng 2 xong **47/47** (2026-10-12); bản nhãn tay được chốt: 155 sai · 94 đúng · 5 chưa chắc, 27 lõi
có `utility`. Đã commit và push (`37a7445`, `4446f40`).

| Việc | Kết quả |
|---|---|
| Áp nhãn tay (việc code #1) | `python scripts/apply_manual_review.py --write`: **122 dòng đổi**, bảng có 161 dòng `manual-audit`. 5 lõi "chưa chắc" giữ dòng máy |
| Không áp | 44 lõi người duyệt sửa `item_grants` (trường định danh, dùng cả key chỉ có ở trang duyệt). Chờ việc code #6. Crafted Crafting vì thế giữ nhãn `item` |
| Độ khớp bảng cũ với nhãn tay | `categories` 64,9% (deterministic) · 78,8% (llm); `econ_value` 84,2% · 88,5%; `tempo` 84,2% · 92,0%. Script in đủ bảng |
| So với nguồn ngoài | MetaTFT: Jaccard 0,884, trùng khít 192/253, nhãn chính ∈ tag 242/253. datatft: Jaccard 0,818, trùng khít 171/252 |
| Chấm lại 147 scenario (việc code #2) | Hoà tuyệt đối top-1 **20 → 14/147** (4 → 3 bộ lựa chọn); cách < 0,01: 40 → 34. Top-1 đổi 9/147. `legacy_tank_direction` bật/tắt không đổi số nào |
| Nhóm `econ_value = 3` | **56 → 72 lõi** (128 lõi có `econ_value > 0`): nhãn tay làm đỉnh chiều kinh tế đông hơn |
| Đổi theo nhãn tay | `data/augment_stats.csv` sinh lại; Comeback Story `immediate → scaling`, bỏ khỏi mốc `immediate` trong test |

Số chấm lại và phép so tay ↔ MetaTFT ↔ datatft chạy bằng script tạm, **chưa vào repo** (việc code #4).
Omega Riftbeast có nhãn `econ` nhưng `econ_value = 0` (người duyệt giữ).

Đổi trong phiên:

- **Bỏ luật "`utility` chỉ đi một mình"** (`check_feature`): người duyệt được gắn `utility` làm nhãn phụ cho lõi có cơ chế đặc biệt. [category-multilabel/definition.md](category-multilabel/definition.md)
- **Mã `type` của datatft đã xác nhận** từ mã nguồn trang (`DatabaseView-*.js`): 1 kinh tế, 2 chiến đấu, 3 trang bị, 4 tộc hệ, 5 độc quyền, 6 khác. Việc code #5 hết bị chặn; [offer-rounds/overview.md](offer-rounds/overview.md) vẫn ghi "chưa xác nhận", chưa sửa.
- **Trang duyệt**: bộ lọc "Vòng 2", thẻ báo "CHƯA LƯU ĐƯỢC" khi server từ chối (trước đó thẻ vẫn ghi "Đã lưu").
- **Khuôn ghi chú** người duyệt đang dùng: `<cơ chế> => nên/không nên chọn nếu <điều kiện>` và `đã có <lõi> => ưu tiên <lõi khác>`. Chưa code nào đọc; là nguyên liệu cho luật chuyên gia và directional.
- Phép so tay ↔ MetaTFT ↔ datatft mới chạy bằng script tạm, **chưa vào repo** (việc code #4).

## Làm ngay đầu phiên

| # | Việc | Ghi chú |
|---|---|---|
| 1 | ~~Commit, tách 4 commit~~ **Xong 2026-10-08** (`410af32` · `c719a17` · `616c928` · `253bafc`) | Commit nhãn duyệt tay đã push (`37a7445`, `4446f40`) |
| 2 | ~~Probe màn chọn lõi ván Normal~~ **Xong 2026-10-15** ở lõi 4-2 (cùng bố cục với 2-1, 3-2), xem mục trên | Còn lại: độ trễ HUD khi game chạy |
| 3 | Chạy lại server duyệt khi cần sửa nhãn | `.venv\Scripts\python scripts\review_augment_features.py` → `http://127.0.0.1:8766/` |

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
| 1 | ~~Áp nhãn tay vào `data/augment_features.json`~~ **Xong 2026-10-12** (`scripts/apply_manual_review.py`) | — |
| 2 | ~~Đo lại baseline~~ **Xong 2026-10-12** bằng script tạm; đưa phép chấm lại vào `directional_baseline.py` nếu cần dẫn số trong báo cáo | — |
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
