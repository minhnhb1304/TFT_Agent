# Phase 0 — Spike and Preflight

Answer the unverified questions about WGC **before** writing the capture module. Everything
here runs on the test machine, script-and-exit, in a Normal game.

## Questions to close

| # | Question | Source of doubt | Pass |
|---|---|---|---|
| Q1 | Can `windows-capture` target the TFT window by title without the `GraphicsCapturePicker` consent UI? | [open-questions.md:78](../../research/open-questions.md) | Frames arrive, no dialog |
| Q2 | Does `draw_border=False` suppress the yellow capture border? | same | No border, or border accepted |
| Q3 | Exact window title / class of the game window | assumed `League of Legends (TM) Client` / `RiotWindowClass` | Found via `FindWindow` |
| Q4 | Are frames non-black in Borderless? In Fullscreen? | SPEC §3.0 preflight | Borderless non-black |
| Q5 | Does the WGC frame include window chrome, i.e. must we crop to client rect? | WGC captures the window surface | Offset measured |
| Q6 | Frame rate and CPU cost while the game runs | none measured | ≥5 fps, CPU note recorded |
| Q7 | Does the 2.0.1 API still use `@capture.event on_frame_arrived` + `start_free_threaded()`? | 1.x API knowledge | Confirmed or new API noted |

## Deliverable: `tools/probe_environment.py`

Runs, prints a report, writes `data/live_probe/<timestamp>/` (report JSON + 3 PNG frames), exits.

```
probe_environment.py [--seconds 5] [--title "League of Legends (TM) Client"]
  1. Windows build (>= 19041), DWM on, DPI scale of the game monitor
  2. FindWindow(title/class) -> hwnd; GetClientRect + ClientToScreen -> client rect
  3. Borderless check: client rect == monitor rect, no WS_CAPTION
  4. WGC capture for N seconds: count frames, mean fps, first-frame latency
  5. Save frames; assert not all-black (mean > threshold)
  6. Crop to client rect, resize to 1920x1080, run RerollButtonReader + HUD reader once
  7. GEMINI key present? (utils/env.describe) — never print the key
```

Step 6 is the first real signal that ROIs fit this machine's resolution.

## Rules

- **Run once with the game closed** first (steps 1, 7 only) — testing protocol step 2.
- Read-only: no `OpenProcess` (banned by `tests/test_readonly_invariant.py`); locate the window
  by title/class only. The AST test covers `tools/` automatically.
- Add `windows-capture==2.0.1` to requirements only after Q1 passes.

## Exit criteria

| Outcome | Next |
|---|---|
| Q1, Q4 pass | Phase 1 with WGC backend |
| Q1 fails (consent UI / no frames) | Phase 1 with `mss` backend + mandatory `check_blockers()` for overlay rect |
| Q4 fails in Borderless | Stop; capture is not viable on this machine — revisit dual-PC protocol |

## Related

- [Overview](overview.md)
- [Phase 1 — Capture source](phase-1-capture.md)
