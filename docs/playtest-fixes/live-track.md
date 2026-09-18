# Live Track

Track **L** và mốc **M5** của [playtest fixes](overview.md). Chạy song song với track R theo
[live mode plan](../live-mode/overview.md), với các điều chỉnh do có lõi chung.

## Ánh xạ với live-mode plan

| Live-mode phase | Trong plan này | Thay đổi so với bản gốc |
|---|---|---|
| [Phase 0 — Spike](../live-mode/phase-0-spike.md) | **L0**, song song M0 | Không đổi. Cần máy game |
| [Phase 1 — Capture](../live-mode/phase-1-capture.md) | **L1**, song song M1–M2 | Không đổi. `WindowCaptureSource` trả `Frame` như `VideoFrameSource` |
| [Phase 2 — Session](../live-mode/phase-2-session.md) | **Thay bằng** [core-session.md](core-session.md) (M1) | Thêm `CardReader` protocol, `seek`, `stable_frames`, `AdviceReady.state/cards` |
| [Phase 3 — App shell](../live-mode/phase-3-app.md) | **M5a** | Worker gọi đúng `LiveSession` của replay; panel dùng chung widget với replay |
| [Phase 4 — Validation](../live-mode/phase-4-validation.md) | **M5b** | Thêm check reroll + dòng trạng thái; ghi thêm video để gắn nhãn |

## Dùng chung với replay

| Thành phần | Chỗ | Ghi chú |
|---|---|---|
| `AugmentPanel` + dòng trạng thái + hàng ô lỗi | `src/overlay/widgets/` | Replay nhúng vào cửa sổ, live đặt trên overlay |
| Renderer `AdviceReady → rows` | `src/overlay/widgets/augment_panel.py` | Thuần dữ liệu, test không cần Qt |
| Config `live.*` | `config/settings.yaml` | Một bộ cho cả hai vỏ |

## Việc

| # | Việc | Phụ thuộc | Kiểm chứng |
|---|---|---|---|
| L0 | `tools/probe_environment.py` theo phase 0 | Máy game | Q1–Q7 có câu trả lời |
| L1 | `src/capture/game_window.py`, `screen_capture.py` theo phase 1 | L0 | Test fake backend; probe dùng source mới |
| M5a.1 | `src/live/app.py` + `scripts/run_live.py` dùng `LiveSession` | M1, L1 | `--source video:<record>` chạy được |
| M5a.2 | **Kiểm G5**: `run_live --source video` vs `run_replay --headless` cùng record | M5a.1, M2 | `replay_live_diff = 0` |
| M5a.3 | Hotkey F1–F4, Ctrl+Q theo phase 3 | M5a.1 | Test dispatch |
| M5b.1 | Checklist phase 4 + các dòng dưới | M5a | 1 game Normal |
| M5b.2 | Record màn hình song song khi test live → thêm vào bộ nhãn | M5b.1 | File nhãn mới trong `data/eval/playtest/` |

## Check bổ sung trong trận (M5b)

| Check | Đạt |
|---|---|
| Reroll 1 ô → panel đổi đúng ô | Trong ≤ 3 s sau khi thẻ ổn định |
| Dòng trạng thái ở màn chọn lõi | Tiền/cấp/XP = giá trị ngay trước khi mở màn |
| Không câu lý do nào trùng giữa 3 thẻ | Sau M4 |
| OCR reader latency dưới tải game | p95 ghi vào `summary.json` |

## Nguyên tắc an toàn (không đổi)

- Capture theo cửa sổ, không inject, không `OpenProcess` — `test_readonly_invariant.py` quét
  cả `src/live/`, `src/replay/`.
- Chỉ game Normal, có giới hạn thời gian ([testing protocol](../../research/vanguard/testing-protocol.md)).

## Related

- [Overview](overview.md)
- [Shared core](shared-core.md)
- [Live mode risks](../live-mode/risks.md)
