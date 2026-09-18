# Phase 2 — Live Session Core

The loop's brain as a pure state machine: `step(frame) -> LiveEvent`. No Qt, no capture, no
threads. Injected clock, reader and advisor.

## Extract first (no behaviour change)

`scripts/advise_from_frame.py` holds the frame→advice glue inline. Move it into
`src/live/pipeline.py` and make the script call it:

```python
def advise_frame(reader, advisor, image, ref, last_rerolls) -> FrameAdvice
    # screen gate, reroll fallback to last stable state, empty-choices guard, Advisor.advise
```

Fix while extracting (found in survey): the rebuilt `GameState` drops `xp_needed`; the reroll
reader runs twice per frame. Covered by existing `advise_from_frame` behaviour + a new test.

## `src/live/session.py`

```
          screen_present && settled             cards hash changed / F3
 IDLE ─────────────────────────────▶ AUGMENT ───────────────────────────▶ (re-read)
  ▲  every 3 s: HUD-only read           │
  │  → tracker.update                   │ screen absent for > 1 s (grace)
  └─────────────────────────────────────┘ → emit Cleared
```

```python
class LiveSession:
    def __init__(self, reader, advisor, *, clock, hud_every_s=3.0, grace_s=1.0): ...
    def step(self, frame: Frame) -> LiveEvent     # Idle | AdviceReady(bundle) | Cleared | Status(msg)
    def force_refresh(self) -> None               # F3: drop aHash cache, re-read next frame
    def new_game(self) -> None                    # tracker.reset(), clear last rerolls
```

- **Gate before Gemini.** Run `reroll_reader.read` first; only call `FrameReader.read` when the
  screen is present *and* settled.
- **Emit only on change.** Same ranking as last emit → `Idle`. The overlay does not flicker.
- **HUD priming** outside the augment screen uses `hud_reader` + `tracker.update` only.
- **New game** heuristic: stage goes backwards (e.g. `4-2` → `1-x`) or window re-found.
- **Latency record** per read: `{capture_ms, gate_ms, augment_ms, hud_ms, advise_ms}` appended
  to the event, for Phase 4 p50/p95.

## Tests — `tests/test_live_session.py`

Uses real PNGs in `data/frames/*/augment_select/` and a fake Gemini call (same pattern as
`tests/test_frame_reader.py`).

| Case | Expect |
|---|---|
| Non-augment frame | No Gemini call; `Idle` |
| Augment frame, settled | One Gemini call; `AdviceReady` with 3 entries |
| Same frame ×5 | Still one Gemini call (aHash); one `AdviceReady` |
| Augment → blank for 0.5 s → augment | No `Cleared` (grace) |
| Augment → blank for 1.5 s | `Cleared` |
| Button pressed (unsettled) | Uses last stable rerolls, no crash |
| Gemini raises / missing key | `AdviceReady` absent, `Status` carries degraded message |
| `force_refresh()` | Next augment frame calls Gemini again |

## Related

- [Overview](overview.md)
- [Phase 3 — App shell](phase-3-app.md)
