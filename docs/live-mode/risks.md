# Live Mode Risks

Ordered by likelihood × impact. Each has an early signal and a fallback.

| # | Risk | Early signal | Mitigation / fallback |
|---|---|---|---|
| R1 | WGC shows consent picker or no frames for the game window | Phase 0 Q1 | `mss` backend cropped to client rect + mandatory `check_blockers()` so the overlay stays out of every ROI |
| R2 | Resolution ≠ 1080p breaks reroll template thresholds | Phase 0 step 6 fails on this machine | Resize client area to 1920×1080 in the source (planned); if still off, re-measure thresholds on probe frames |
| R3 | Game in Fullscreen → black frames / overlay hidden | Preflight non-black + borderless checks | Refuse to start with a message: switch to Borderless |
| R4 | Worker blocks on Gemini (≤12 s) → overlay looks frozen | Status line stuck | Worker thread only; panel shows "reading cards…" status; Qt thread never waits |
| R5 | HUD OCR (~1.1 s idle) much slower under game load | Phase 4 `hud_ms` p95 | Lower HUD priming cadence; skip HUD on re-reads within one augment screen |
| R6 | Advice on old-patch data | `stale_data` non-empty at startup | Printed at startup and on F4 detail; `refresh_data.py` before the session |
| R7 | Missing / invalid Gemini key → no card names | Preflight key check; `degraded` "Lỗi gọi Gemini" | Preflight warns; panel shows status instead of an empty ranking |
| R8 | Overlay covers cards or HUD ROIs | `check_blockers()` at startup | Move panel; placement is relative to client rect |
| R9 | Anti-cheat exposure while co-running with Vanguard | — | Window-scoped WGC, no injection, no `OpenProcess`, AST read-only test covers new code; Normal games only, timeboxed ([testing protocol](../../research/vanguard/testing-protocol.md)) |
| R10 | Qt widget touched from worker thread → random crashes | Crash only under load | Worker emits plain data via signals; test asserts no widget import in `session.py` |
| R11 | Agent-made `run_live.py` on test machine conflicts with ours | `git pull` refuses | Rename it first (checklist item in Phase 4) |

## Explicitly out of scope for v1

- Comp / economy / item panels (SPEC §3.6 widgets not built yet)
- Opponent scouting (`enable_scouting` stays off)
- `127.0.0.1:2999/liveclientdata` as a HUD replacement — still unverified for TFT
  ([open-questions.md](../../research/open-questions.md)); keep vision for level/HP
- Capture protection (`SetWindowDisplayAffinity`) — stays off ([capture design](../../research/vanguard/capture-design.md))

## Related

- [Overview](overview.md)
- [Phase 0 — Spike](phase-0-spike.md)
