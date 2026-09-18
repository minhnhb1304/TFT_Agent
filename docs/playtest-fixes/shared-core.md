# Shared Core

Quyết định 2026-09-17: **phát triển song song replay (`run_replay.py`) và live mode**.
Để hai mode không lệch nhau, mọi logic nằm trong **một lõi dùng chung**; mỗi mode chỉ là
một vỏ mỏng khác nhau ở nguồn khung hình và giao diện.

## Kiến trúc

```
 Vỏ replay (run_replay.py)              Vỏ live (scripts/run_live.py)
  video player, nút mốc, tua              overlay click-through, hotkey F1–F4
  VideoFrameSource (seek được)            WindowCaptureSource (WGC)
            │                                        │
            └──────────── frame, t ──────────────────┘
                              ▼
                 LiveSession.step(frame, t) -> LiveEvent        (src/live/session.py)
                   ├─ gate: RerollButtonReader (screen_present, settled)
                   ├─ HUD priming ngoài màn chọn lõi → GameStateTracker
                   ├─ AugmentScreenTracker: theo dõi từng ô, reroll, khung ổn định
                   ├─ CardReader (protocol): OcrCardReader | GeminiCardReader
                   └─ Advisor.advise(tracker.state(traits), choices, rerolls)
```

## Quy tắc

| Quy tắc | Vì sao |
|---|---|
| `src/live/` **không import Qt** | Test headless; dùng chung cho cả hai vỏ |
| Vỏ **không** tự dựng `GameState`, không tự đọc thẻ | Lỗi #3 hiện tại chính là do replay tự dựng state |
| `CardReader` là protocol, chọn bằng config | Replay đang dùng OCR, live plan dùng Gemini — so được trên cùng record |
| Replay chạy **cùng `step()` như live**, tuần tự theo thời gian | Hành vi trên record = hành vi trong trận |
| Tua/nhảy mốc trong replay → `session.seek(t)`: reset theo dõi màn, **giữ** tracker nếu tua tới | Không đọc lại HUD từ đầu mỗi lần tua |
| Mốc tự động = kết quả của `LiveSession` chạy nhanh trên video, không phải scanner riêng | Một nguồn sự thật cho "đang ở màn chọn lõi" |

## Ánh xạ sang các hạng mục

| Hạng mục | Phần nằm trong lõi chung |
|---|---|
| [A. Reroll rescan](augment-reroll-rescan.md) | `AugmentScreenTracker`, `OcrCardReader` (bước 3–9) |
| [B. Game state](game-state-value.md) | HUD priming, `tracker.state(traits)`, `bundle.economy` trong `LiveEvent` |
| [C. Commentary](augment-commentary.md) | Trong `Advisor`/scorer — vỏ chỉ hiển thị |
| [D. Expert knowledge](expert-knowledge.md) | `ExpertRuleScorer` trong `Advisor`; công cụ gắn nhãn là vỏ replay |
| [Live mode phase 2](../live-mode/phase-2-session.md) | Chính là lõi này — bổ sung `CardReader` protocol và `seek(t)` |

## Thứ tự làm

Xem roadmap M0–M6 trong [overview.md](overview.md#roadmap). Chi tiết lõi:
[core-session.md](core-session.md); vỏ replay: [replay-shell.md](replay-shell.md); vỏ live:
[live-track.md](live-track.md).

## Related

- [Overview](overview.md)
- [Live mode overview](../live-mode/overview.md)
- [Live mode phase 2](../live-mode/phase-2-session.md)
