# Live Mode

Plan for running the advisor against a live TFT game on the **same machine**. Scope of v1:
**augment-select screen only** — ranking + reroll advice on a click-through overlay, driven by
global hotkeys. Comp/economy panels come after v1. Drafted 2026-09-15.

## Why this is needed

Today the only path from pixels to advice is `scripts/advise_from_frame.py` on a saved frame or
VOD. Three pieces are missing for live play:

| Missing | Exists and will be reused |
|---|---|
| Screen capture (`FrameSource` over the game window) | `FrameSource` protocol, `VideoFrameSource` |
| Live loop: capture → gate → read → advise → overlay | `FrameReader`, `GameStateTracker`, `Advisor` |
| App shell: overlay windows + hotkeys wired together | `create_windows`, `AugmentPanel`, `GlobalHotkeyManager` |

## Architecture

```
 Qt main thread                                 Worker QThread
 ─────────────────────────────                  ──────────────────────────────────────────
 LiveApp                                         LiveWorker (loop, ~5 Hz)
  ├─ passthrough window + AugmentPanel  ◀─signal─  frame = source.grab()
  ├─ GlobalHotkeyManager (F1-F4, Ctrl+Q) ─slot──▶  event = session.step(frame)   (pure)
  └─ preflight report (console)                     └─ LiveSession: gate → FrameReader → Advisor
                                                 source: WindowCaptureSource | Frames/Video replay
```

- **Qt widgets are touched only on the main thread.** The worker emits plain data
  (`AdviceBundle`, status string); the app renders it.
- **`LiveSession` has no Qt and no capture** — it takes a frame and returns an event. That is
  what makes the loop testable headless against `data/frames/*/augment_select/*.png`.
- **Replay source** (`--source frames:<dir>` / `--source video:<file>`) runs the *whole* app
  without the game. Most debugging happens here, not in a match.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Capture API | `windows-capture` 2.0.1 (WGC, window-scoped) | Already decided in [research/overview.md](../../research/overview.md); overlay can't enter the frame; avoids the DXGI syscall `vgk.sys` hooks. abi3 wheel installs on Python 3.14 (checked) |
| Fallback | `mss` cropped to client rect | Installed; only if the Phase 0 spike fails. Requires ROI/overlay disjointness check |
| Frame size | Resize client area to 1920×1080 before reading | Reroll thresholds were measured only at 1080p; ROIs are fractions but templates are not |
| Screen gate | `RerollButtonReader` `screen_present` + `settled` | Local, cheap. `FrameReader.read` does not gate and would call Gemini on every frame |
| Loop cadence | 5 Hz grab; full read only on augment screen | SPEC §3.1 ~5 FPS; aHash cache makes repeated identical cards free |
| HUD priming | HUD-only read every ~3 s outside augment screen | Augment screen hides gold/level; tracker must already hold them |
| Overlay | `passthrough` window from `create_windows`, top-right of client rect | Click-through by default; F2 flips to interactive |

## Phases

| # | Phase | Output | Needs game? | Effort |
|---|---|---|---|---|
| 0 | [Spike + preflight](phase-0-spike.md) | `tools/probe_environment.py`, go/no-go on WGC | **Yes** (minutes) | 0.5 d |
| 1 | [Capture source](phase-1-capture.md) | `src/capture/game_window.py`, `screen_capture.py` | No (fake backend) | 1 d |
| 2 | [Live session core](phase-2-session.md) | `src/live/session.py` + extracted glue | No | 1.5 d |
| 3 | [App shell](phase-3-app.md) | `src/live/app.py`, `scripts/run_live.py` | No (replay) | 1.5 d |
| 4 | [Live validation](phase-4-validation.md) | checklist run, latency p50/p95, ROI fixes | **Yes** | 1 d |

Phases 1 and 2 are independent and can run in parallel after Phase 0.

## Related

- [Risks](risks.md)
- [Capture design decision](../../research/vanguard/capture-design.md)
- [Testing protocol](../../research/vanguard/testing-protocol.md) — Normal games, timeboxed sessions
- [Next steps §7](../next-steps.md) — latency and ROI items this plan closes
