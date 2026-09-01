# Nhật Ký Phát Triển

> Trạng thái **thực tế** của dự án. Checkbox trong [`SPEC.md §7`](SPEC.md) đã lỗi thời ở vài chỗ —
> file này mới là nguồn đúng.
>
> Cập nhật: **2026-09-02** · 332 test xanh, chạy hoàn toàn offline · 74 file Python

---

## Tổng quan

| | |
|---|---|
| **Track A** — lõi offline, không cần game | ✅ **Xong** |
| **Track B** — cần máy đang chạy TFT | ⛔ **Chưa bắt đầu** — chặn toàn bộ phần còn lại |
| Nút thắt hiện tại | Không có dữ liệu nhận diện. Mọi số ở §12.1–12.4 đều cần Track B |

---

## Nhật ký theo mốc

| Ngày | Commit | Nội dung |
|---|---|---|
| 08-06 → 08-14 | `0efe27e`…`3d2dc8b` | SPEC v1→v2, báo cáo research đa ngôn ngữ |
| 08-29 → 08-31 | `c712ae8` | **Lõi Track A**: knowledge · scoring · advisor · eval harness · 155 test |
| 09-01 | `7f473c1` | Sửa bẫy `setData[0]` |
| 09-01 | `2ed54f4` | Tier 1 + Tier 3 của `claude_feedback.md` |
| 09-01 | `a5a88a6` | Tài liệu hoá cảnh báo dữ liệu giả lập |
| 09-01 | `160fdf8` | Nạp key từ `.env` |
| 09-01 | `96dda89` | Tinh chỉnh đặc trưng bằng Gemini |
| 09-01 | `c3ddd6c` | Crawl đội hình meta thật; augment thì **không lấy được** |
| 09-02 | — | Nguồn tactics.tools + bảng tier do người xếp; **xác nhận augment tắc ở mọi nguồn** |

---

## Đã làm

### Nền tảng dữ liệu

| Hạng mục | Kết quả |
|---|---|
| CDragon client | 6 cái bẫy im lặng thành assert runtime |
| Locale đầy đủ | `fetch_locale.py` → `data/cdragon_cache/` (en_us 23.6 MB + vi_vn 24.2 MB) |
| Bảng đặc trưng augment | 254/254, tầng 1 tất định + tầng 2 LLM (175 dòng tinh chỉnh) |
| Ánh xạ tên → `apiName` | `name_index.json` — 254 augment · 36 trait · 65 champion, VI + EN |
| Đội hình meta | **Đo thật** — 249 trận, 1988 participant, 12 đội hình |
| Đội hình meta (bên thứ ba) | tactics.tools — 456.572 ván, 12 đội hình, cỡ mẫu 819–46.091. Ghi ra **file riêng** |
| Stats unit/trait/item | tactics.tools — 74 unit · 91 trait · 131 item. **Chưa nối vào scoring engine** |
| Bảng tier augment | Khung đã có (`ExpertTierListProvider` + importer). **Repo không kèm dữ liệu** — xem lý do bên dưới |
| Stats augment | ⚠️ **Giả lập** — không nguồn nào còn cấp, xem bên dưới |

### Thuật toán (trọng tâm đồ án)

5 thành phần điểm `w₁..w₅` (SPEC §3.5.4), mỗi cái trả `(score, reason)`. Trọng số nằm ở
`config/scoring_weights.yaml` để ablation tắt/bật được mà không sửa code.

Phụ trợ: comp selector · economy rules · item · position · contest score · LLM refinement
(khoá bằng `assert_order_preserved`, không được đổi thứ hạng).

### Đánh giá (SPEC §12)

Harness đủ 4 phương pháp — logger, P/R/F1, Spearman, Cohen's κ, ablation. **Chạy được nhưng
`n = 0`**: chưa có dataset thật.

### An toàn (SPEC §1.3)

`tests/test_readonly_invariant.py` quét AST toàn bộ `src/`, `scripts/`, `tools/`. Hotkey đi qua
`RegisterHotKey` + Qt native event filter — **không** `WH_KEYBOARD_LL`, không cần admin.

---

## Phát hiện đã đổi kế hoạch

Bốn thứ chỉ lộ ra khi chạy thật, không phải khi đọc tài liệu.

### 1. `setData[0]` không phải Set 18

Locale đầy đủ có **35 khối `setData`** không theo thứ tự; khối đầu là `TFTSet14`, còn khối Set 18
có `name = "Set10"`. Lấy nhầm thì bảng trait thành của Set 14, `trait_affinity` rỗng sạch,
`BoardFit` trung tính cho **mọi** augment — **hỏng hoàn toàn im lặng**.

> Fixture trimmed chỉ giữ một khối, nên bug này xanh hết test cho đến ngày gặp file thật.
> **Bài học**: fixture là tập con có thể giấu cái bẫy nằm ở *hình dạng* dữ liệu.

### 2. Riot đã gỡ trường `augments` — và không nguồn nào khác lấp được

Participant Set 18 của `tft-match-v1` **không còn `augments`**; cả payload không có chuỗi
`"augment"` nào (kiểm tra 3 trận ranked, vn2).

SPEC §3.4.2 gọi `RiotApiProvider` là *"bảo vệ tốt nhất trước hội đồng"* cho stats augment.
**Đường đó đã đóng** — không do rate limit hay công sức. Đã sửa SPEC thay vì để nó treo.

Nhưng `units` / `traits` / `placement` còn nguyên → **đội hình meta đo thật được**. Đó là lý do
`meta_comps.json` là thật còn `augment_stats.csv` vẫn giả.

**Kiểm chứng ngoài (09-02).** tactics.tools có sẵn bốn trường augment và **cả bốn đều rỗng** ở mọi
rank group, kể cả nhóm `all` với 1.752.735 ván. datatft nhúng bảng tier **hardcode trong bundle JS**
do ba người chơi xếp; tftacademy chỉ có S/A/B/C, không con số nào. Nghĩa là câu trả lời cho hội đồng
đổi từ *"chúng tôi không crawl được"* thành *"trang thống kê công khai lớn nhất cũng không có"* —
mạnh hơn hẳn. `augment_row_count()` đo lại điều này sau mỗi lần crawl.

### 3. `gemini-2.5-flash-lite` đã bị gỡ

API trả 404 kèm chỉ dẫn dùng `gemini-3.5-flash-lite`. Trước đó handler chỉ in tên kiểu lỗi nên
nuốt mất câu này — giờ in cả nội dung.

### 4. LLM phá dữ liệu đúng nếu không chặn

```
trait_affinity: ['DA_Riftbeast18'] -> []
item_grants:    ['AnyComponent'] -> ['component','component',...]
```

Hai trường đó chứa apiName suy từ dữ liệu có cấu trúc; LLM không thể biết chuỗi đó là gì.
**Nguyên tắc rút ra**: LLM chỉ được dùng cho phần *phán đoán đọc từ văn bản*; phần *định danh*
luôn lấy từ dữ liệu có cấu trúc.

---

## Dự kiến triển khai

### Chặn mọi thứ — Track B, Phase 0 (§7)

Phải chạy trên máy đang mở TFT thật. Chưa làm được cái nào.

| # | Việc | Chi phí | Quyết định điều gì |
|---|---|---|---|
| 1 | `tools/probe_environment.py` — build Windows, process/window class, borderless | 30' viết + 10' chạy | Mốc so sánh cho client 2026-10-09. **Không ghi bây giờ thì mất vĩnh viễn** |
| 2 | Chụp 1 frame → assert không đen | 10' | Riot có bật capture protection không. Chưa ai chạy trên 18.1 |
| 3 | Benchmark RapidOCR khi game đang chạy | 30' | Mọi số latency hiện có đều đo trên máy rảnh |
| 4 | `GET 127.0.0.1:2999/liveclientdata` trong trận | 5' | Có bỏ được level/HP khỏi pipeline vision không |

### Phase 1–3 — Vision (sau Phase 0)

`preflight.py` → `screen_capture.py` → `tools/calibrate.py` → `session_detector.py` →
`augment_reader.py` (Gemini Vision primary) → champion/item/trait recognition.

> Recognizer trả `apiName` + confidence và **không chấm điểm**. Cầu nối OCR → `apiName` đã có sẵn
> (`name_index.py`), scoring engine không phải đổi một dòng.

### Phase 6 — Kết quả (cần dataset)

Gán nhãn 200–500 frame → chạy `run_evaluation.py` → viết chương kết quả. Harness sẵn sàng, chỉ
thiếu dữ liệu. **Tier 5**: nhờ 3–5 người chơi rank khá đánh giá ~50 scenario lấy Cohen's κ.

### Deadline bên ngoài — 2026-10-09

Client TFT standalone. Khả năng đổi process name / window class → vỡ window targeting và overlay
owner-window. PBE báo cáo ~09-09. **Đây là lý do việc #1 ở trên phải làm sớm.**

---

## Nợ kỹ thuật đã biết

| Vấn đề | Ảnh hưởng |
|---|---|
| `augment_stats.csv` giả lập | Không trích được vào báo cáo. Đã loại trừ ba nguồn ngoài (09-02) — chỉ còn chờ Riot trả lại trường |
| `data/augment_tiers.json` chưa có dữ liệu | Khung chạy được nhưng rỗng: phải đọc bảng tier bằng mắt rồi nạp tay. Cố tình — cùng nguyên tắc với `comp_database.py`, không nhét bảng tier từ bìa vào repo |
| `tactics_tools_stats.json` chưa có ai đọc | Số unit/trait/item đã đo được nhưng chưa nối vào `item_advisor` / `board_fit`. Nối vào là thêm một đường ảnh hưởng chưa đo được trong ablation |
| Cỡ mẫu vn2 nhỏ (2 challenger / 160 apex) | Số đội hình mang bất định. Crawl lại gần deadline sẽ tốt hơn |
| Riot Personal Key hết hạn 24h | Mỗi lần crawl phải lấy key mới |
| `roll_odds.py` chưa có importer nào | Đã gắn nhãn `Unverified Data (Set 18.1)` nhưng chưa nối vào `rules_engine` |
| `styles.py` không ai import | `augment_panel` hardcode lại cùng giá trị — theme bị nhân đôi |
| `data/item_recipes.json` chưa sinh | Sinh được từ locale đầy đủ, chưa cần tới |
| Checkbox SPEC §7 lỗi thời | Nhiều mục Phase 1–3 đã xong nhưng chưa tick |

---

## Liên quan

[`SPEC.md`](SPEC.md) — đặc tả v3 · [`README.md`](README.md) — cài đặt & cảnh báo dữ liệu ·
[`research/`](research/overview.md) — báo cáo nghiên cứu · [`claude_feedback.md`](claude_feedback.md) — quyết định Tier 1–5
