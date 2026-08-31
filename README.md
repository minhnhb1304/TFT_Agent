# TFT Advisory Agent

Hệ hỗ trợ ra quyết định cho Teamfight Tactics — đọc trạng thái bàn cờ **chỉ bằng thị giác máy tính**,
rồi xếp hạng và giải thích lựa chọn augment tốt nhất.

> **Đồ án tốt nghiệp.** Chạy cục bộ, single-user, **không phát hành**. Xem
> [`SPEC.md` §11](SPEC.md) về phạm vi và đạo đức nghiên cứu.

| Tài liệu | Nội dung |
|---|---|
| [`SPEC.md`](SPEC.md) | Đặc tả v3 — kiến trúc, thuật toán, phương pháp đánh giá |
| [`research/`](research/overview.md) | Báo cáo nghiên cứu, đã re-verify 2026-08-28 trên Set 18 live |

---

## Cài đặt

Yêu cầu **Python 3.11+** (đã kiểm chứng trên **3.14.7**, Windows).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Toàn bộ dependency đã xác nhận có wheel cho cp314 (PyQt6 và OpenCV dùng wheel `abi3`).

> ⚠️ `opencv-python` ghim `<5`. OpenCV 5.0 đã phát hành nhưng đổi API; mọi prior art đều dùng 4.x.

## Chạy test

```bash
pytest -q
```

Test **chạy hoàn toàn offline** — không test nào chạm mạng. Nguyên tắc mock-first: mọi phụ thuộc bên
ngoài đều có fixture trong `tests/fixtures/`.

---

## Trạng thái hiện tại

**Track A — lõi offline** (không cần game, không cần API key):

| Milestone | Trạng thái | Nội dung |
|---|---|---|
| A1 Scaffold + bất biến an toàn | ✅ | `tests/test_readonly_invariant.py` |
| A2 CDragon client | ✅ | `src/knowledge/cdragon_client.py` |
| A3 Augment catalog | ✅ | `src/knowledge/augment_catalog.py` |
| A4 Bảng đặc trưng augment | ✅ | `scripts/build_augment_features.py` → `data/augment_features.json` (254/254) |
| A5 Scoring engine (SPEC §7 Phase 4) | ✅ | `src/decision/scoring/` · `augment_advisor.py` · `widgets/augment_panel.py` |
| Advisor phụ trợ (Phase 5) | ✅ | `comp_selector` · `rules_engine` · `item_advisor` · `position_advisor` · `llm_reasoner` · `advisor` |
| A6 Eval harness (Phase 6) | ✅ | `src/eval/` — logger, correlation, ablation, recognition, expert study |
| Contest score (Phase 7) | ✅ | `contest_analyzer.py` + cờ `enable_scouting` (mặc định **tắt**) |
| A7 Dữ liệu Set 18 thật | ✅ | `scripts/fetch_locale.py` → `data/cdragon_cache/` (en_us + vi_vn đầy đủ, ~24 MB mỗi bản) |
| A8 Bảng ánh xạ tên → `apiName` | ✅ | `scripts/build_name_index.py` → `data/name_index.json` (254 augment · 36 trait · 65 champion, cả VI lẫn EN) |
| A9 Stats augment | ⚠️ giả lập | `data/augment_stats.csv` — Riot đã gỡ trường `augments`, xem cảnh báo bên dưới |
| A10 Hotkey toàn cục | ✅ | `src/utils/hotkeys.py` — `RegisterHotKey` qua Qt, **không** dùng `WH_KEYBOARD_LL` |
| A11 Nạp key từ `.env` | ✅ | `src/utils/env.py` — tự viết, không thêm dependency; biến môi trường thắng file |
| A12 Riot API client | ✅ | `src/knowledge/riot_api.py` — rate limit 2 cửa sổ, lọc `tft_set_number`, 42 test offline |
| A13 Meta comp **đo thật** | ✅ | `scripts/crawl_meta_comps.py` → `data/meta_comps.json` (VN2 hạng cao, kèm `match_id`) |
| A14 Tinh chỉnh đặc trưng bằng LLM | ✅ | `build_augment_features.py --llm` trên `gemini-3.5-flash-lite` |

**Track B — cần máy có game đang chạy**: capture, calibrate ROI, OCR, đọc `OpponentBoard`, và chạy
overlay thật. Bắt đầu bằng `tools/probe_environment.py` (chưa viết). Phần quyết định của overlay
(`overlay_window.apply_capture_protection`) đã có test; phần vẽ chỉ kiểm chứng được khi có màn hình.

---

## ⚠️ Nguồn dữ liệu — đọc trước khi trích số

Hai file thống kê **không cùng độ tin cậy**. Phải phân biệt khi viết báo cáo.

| File | Nguồn | Dùng được cho báo cáo? |
|---|---|---|
| `data/meta_comps.json` | **Đo thật** — `tft-match-v1`, hạng cao VN2, có `match_id` truy ngược | ✅ Có, kèm cỡ mẫu |
| `data/augment_stats.csv` | **GIẢ LẬP** — `source` = `MOCK-NOT-REAL` | ❌ **Tuyệt đối không** |

### Vì sao augment vẫn phải giả lập

Đo trực tiếp bằng key thật ngày **2026-09-01**: participant của `tft-match-v1` ở Set 18
**không còn trường `augments`**, và cả payload trận đấu không chứa chuỗi `"augment"` nào. Riot đã
gỡ nó. Đây không phải giới hạn rate limit hay công sức — **đường đó đã đóng**.

Còn lại `units`, `traits`, `placement`, `level` thì nguyên vẹn, nên **đội hình meta đo thật được** —
và `crawl_meta_comps.py` làm đúng việc đó.

Thiếu `augment_stats.csv` thì w₁ trả 0.5 cho cả 254 augment, tức **30% ngân sách điểm thành hằng số**
và dòng ablation *"chỉ w₁"* — dòng quan trọng nhất của đồ án (SPEC §12.4) — suy biến thành sắp xếp
alphabet. Nên file giả lập vẫn cần, nhưng nó **tự khai báo là giả** ở đúng chỗ người dùng nhìn thấy:

```
Vị trí trung bình 3.94 (n=553, nguồn: MOCK-NOT-REAL)
```

Chi tiết: [`research/set-data.md`](research/set-data.md) · [`research/open-questions.md`](research/open-questions.md)

---

## Chạy thử không cần game

```bash
# Một lần: kéo dữ liệu Set 18 thật về cache (~50 MB, cần mạng)
python scripts/fetch_locale.py

# Sinh lại các bảng dữ liệu (đều deterministic, chạy lại ra file y hệt)
python scripts/build_augment_features.py --locale en_us --offline
python scripts/build_name_index.py
python scripts/build_mock_stats.py --overwrite      # augment: vẫn phải giả lập

# Cần key (đặt trong .env — xem .env.example)
python scripts/build_augment_features.py --locale en_us --offline --llm --diff
python scripts/crawl_meta_comps.py --dry-run        # xem ngân sách request trước
python scripts/crawl_meta_comps.py --matches 250 --overwrite

# Chạy
python -m src.decision.augment_advisor                        # xếp hạng 3 augment + lý do
python scripts/run_evaluation.py --scenarios data/scenarios   # 4 phương pháp đánh giá §12
```

---

## Bất biến kiến trúc (SPEC §1.3)

Dự án này **thuần read-only**. Không đọc memory, không inject, không hook render, không gửi input.

Đây không phải lời hứa suông — nó được **thi hành bằng test**:

```bash
pytest tests/test_readonly_invariant.py -v
```

Test quét AST của toàn bộ `src/`, `scripts/`, `tools/`. Nhắc tên `SendInput` trong comment thì không
sao; thực sự import hay gọi nó thì build đỏ ngay.

**Hotkey là chỗ dễ vi phạm nhất** — nên nó có banlist riêng (`tests/test_hotkeys.py`).
Thư viện `keyboard` cài `SetWindowsHookEx(WH_KEYBOARD_LL)`: một hook cấp thấp nhìn thấy **mọi phím
của mọi ứng dụng** trên máy, và thường đòi quyền admin. `RegisterHotKey` không cần cả hai — nó đăng
ký tổ hợp với hệ điều hành, và OS post `WM_HOTKEY` vào message queue của process này. Vẫn chạy khi
game đang focus, vì chặn ở tầng OS chứ không phải tầng cửa sổ.

> `QShortcut` **không** dùng được ở đây: nó chỉ bắn khi cửa sổ được focus, mà overlay đặt
> `WA_ShowWithoutActivating` + `WindowTransparentForInput` nên không bao giờ focus.

---

## Ghi chú cho người chấm

Mỗi con số trong báo cáo đều có một test dẫn xuất lại từ dữ liệu thật:

```bash
pytest tests/test_augment_catalog.py -v
```

Ví dụ: ladder giải tier augment đạt **254/254** với phân bố 75/28/135/16; **19/254** đường dẫn icon
mâu thuẫn với tên augment (bằng chứng định lượng cho quy tắc "tên là chính, icon là phụ"); **0** va
chạm khi bỏ dấu tiếng Việt.

Bảng ánh xạ tên tái lập cùng những con số đó trên **locale đầy đủ**, không phải fixture:

```bash
pytest tests/test_name_index.py -v
```

Tiếng Việt mất **5** cặp augment không phân biệt được, tiếng Anh mất **4** — chênh lệch đúng một cặp,
do `Tons of Stats!` / `TONS of Stats!` chỉ khác nhau ở chữ hoa và bản dịch tiếng Việt gộp cả hai.
Đây là **giới hạn dữ liệu**, được báo cáo chứ không giấu: gặp cặp mập mờ thì hiển thị cả hai kèm nhãn.

### Một cái bẫy đã đo được, chưa từng ghi trong research

Trên bản locale **đầy đủ**, `setData[0]` là **`TFTSet14`**, không phải Set 18. File thật mang 35 khối
`setData` không theo thứ tự nào, và khối của Set 18 có `name` là `"Set10"`. Lấy nhầm khối thì bảng
ánh xạ trait thành của Set 14, `trait_affinity` rỗng sạch, và `BoardFit` trung tính cho **mọi**
augment — hỏng hoàn toàn im lặng.

Bẫy này **không lộ ra ở fixture trimmed** (fixture chỉ giữ đúng một khối), nên nó xanh hết test cho
đến ngày chạy trên dữ liệu thật. Đã khoá bằng `cdragon_client.select_set_data()` + test.
