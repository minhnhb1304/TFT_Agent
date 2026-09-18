# Core Session

Mốc **M1** (phần lõi) của [playtest fixes](overview.md). Hiện thực [shared-core.md](shared-core.md)
và thay thế thiết kế `LiveSession` trong [live mode phase 2](../live-mode/phase-2-session.md).

## Cấu trúc module

| File | Nội dung | Nguồn |
|---|---|---|
| `src/live/__init__.py` | Export công khai | Mới |
| `src/live/events.py` | `LiveEvent`: `Idle`, `ScreenOpened`, `AdviceReady`, `Cleared`, `Status` | Mới |
| `src/live/card_reader.py` | `CardReader` protocol, `OcrCardReader`, `GeminiCardReader` | Tách từ `run_replay.py`, bọc `AugmentReader` |
| `src/live/screen_tracker.py` | `AugmentScreenTracker`: từng ô, hash, ổn định, reroll | Mới (M2 làm đầy đủ) |
| `src/live/session.py` | `LiveSession`: máy trạng thái, HUD priming, gọi `Advisor` | Mới |
| `src/live/pipeline.py` | Glue frame→advice tách từ `scripts/advise_from_frame.py` | Theo live-mode phase 2 |

## Interface

```python
class CardReader(Protocol):
    name: str
    def read_slot(self, frame: np.ndarray, slot: int) -> CardRead: ...   # CardRead đã có
    def read_traits(self, frame: np.ndarray) -> dict[str, int]: ...

@dataclass(frozen=True)
class AdviceReady:
    t: float; stage: str
    bundle: AdviceBundle                 # gồm ranking, reroll, economy, comp
    state: GameState                     # đúng state đã dùng — vỏ chỉ hiển thị
    cards: tuple[CardRead, ...]          # cả ô không đọc được, kèm reason
    stale_fields: tuple[str, ...]
    latency_ms: dict[str, float]

class LiveSession:
    def __init__(self, card_reader, hud_reader, reroll_reader, advisor, tracker,
                 *, hud_every_s=3.0, grace_s=30.0, stable_frames=3): ...
    def step(self, frame: Frame) -> LiveEvent
    def seek(self, t: float) -> None      # replay: tua lùi → new_game(); tua tới → giữ tracker
    def force_refresh(self) -> None       # F3 / nút quét lại: đọc lại cả 3 ô
    def new_game(self) -> None
```

## Máy trạng thái

```
 IDLE ── gate: screen_present ──▶ OPENING ── đủ stable_frames ──▶ AUGMENT
  ▲  HUD mỗi hud_every_s             (chưa đọc thẻ)                │ ô i đổi / nút i bấm
  │  → tracker.update                                              ▼
  └──── vắng màn > grace_s → Cleared ◀──────────────────────── RE-READ ô i → AdviceReady
```

- Gate **trước** mọi OCR/Gemini: khung ngoài màn chỉ tốn đọc nút + HUD định kỳ.
- `grace_s` lớn vì người chơi **ẩn màn chọn lõi ~10 s để xem bàn cờ** rồi mở lại (đo trên
  record 2026-09-16, cả 2 game). Mở lại KHÔNG phải màn mới: giữ nguyên offer và lượt reroll.
- `AdviceReady` chỉ phát khi (cards, rerolls, state) đổi — overlay không nháy.
- `Frame.t` là đồng hồ duy nhất (video = vị trí file, live = wall clock) → replay tái lập 100%.

## Việc

| # | Việc | Kiểm chứng |
|---|---|---|
| 1 | Tách `DynamicCardRecognizer` → `OcrCardReader` **giữ nguyên hành vi** (1 dòng, cutoff 0.45) | Test so khớp output cũ trên khung `data/frames` |
| 2 | `GeminiCardReader` bọc `AugmentReader` hiện có | `tests/test_frame_reader.py` vẫn xanh |
| 3 | `events.py`, `session.py` với tracker đơn giản (đọc 3 ô khi mở màn) | `tests/test_live_session.py` (bảng dưới) |
| 4 | Tách `pipeline.py` từ `advise_from_frame.py`; sửa mất `xp_needed`, bỏ đọc nút 2 lần | Script cho output như cũ |
| 5 | Config `live.card_reader: ocr \| gemini`, `live.hud_every_s`, `live.stable_frames` | Settings test |
| 6 | AST test: `src/live/` không import `PyQt*` | Test mới |

## Test — `tests/test_live_session.py`

| Tình huống | Kỳ vọng |
|---|---|
| Khung ngoài màn | Không gọi `CardReader`; `Idle` |
| Mở màn, khung đang hiện | Chưa đọc cho tới `stable_frames` |
| Cùng khung ×5 | 1 lần đọc, 1 `AdviceReady` |
| Vắng 0.5 s rồi lại có | Không `Cleared` |
| Vắng 1.5 s | `Cleared` |
| HUD đọc trước khi mở màn | `AdviceReady.state.gold` = giá trị đó, không phải 0 |
| Ô không khớp tên | Có trong `cards` với reason; ranking đánh dấu thiếu |
| `seek` lùi | `new_game()` được gọi |

## Related

- [Shared core](shared-core.md)
- [Replay shell](replay-shell.md)
- [Augment reroll rescan](augment-reroll-rescan.md)
