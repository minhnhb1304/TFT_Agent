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

**Track B — cần máy có game đang chạy**: capture, calibrate ROI, OCR, đọc `OpponentBoard`, và chạy
overlay thật. Bắt đầu bằng `tools/probe_environment.py` (chưa viết). Phần quyết định của overlay
(`overlay_window.apply_capture_protection`) đã có test; phần vẽ chỉ kiểm chứng được khi có màn hình.

## Chạy thử không cần game

```bash
python -m src.decision.augment_advisor          # xếp hạng 3 augment trên tình huống tổng hợp
python scripts/build_augment_features.py --locale-file tests/fixtures/cdragon/en_us.trimmed.json
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

---

## Ghi chú cho người chấm

Mỗi con số trong báo cáo đều có một test dẫn xuất lại từ dữ liệu thật:

```bash
pytest tests/test_augment_catalog.py -v
```

Ví dụ: ladder giải tier augment đạt **254/254** với phân bố 75/28/135/16; **19/254** đường dẫn icon
mâu thuẫn với tên augment (bằng chứng định lượng cho quy tắc "tên là chính, icon là phụ"); **0** va
chạm khi bỏ dấu tiếng Việt.
