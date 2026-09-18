# Phase 4 — Live Validation

The only phase that needs real matches. Timeboxed: one Normal game, run-and-exit, per the
[testing protocol](../../research/vanguard/testing-protocol.md).

## Before the match

- [ ] `git pull`; old agent-made `run_live.py` removed
- [ ] `pip install -r requirements.txt` (adds `windows-capture`)
- [ ] Game in **Borderless**; note resolution and Windows display scale
- [ ] `python tools/probe_environment.py` — all checks pass
- [ ] `python scripts/refresh_data.py --check` — no stale tables (or knowingly accepted)
- [ ] Replay smoke: `run_live.py --source frames:...` shows a ranking on screen

## During the match

| Check | Pass |
|---|---|
| Overlay visible over the game, top-right, not covering cards/HUD | Yes at 2-1, 3-2, 4-2 |
| F1 / F2 / F4 / Ctrl+Q work while the game has focus | All respond |
| F2 on: mouse passes through; off: panel clickable | Both |
| Ranking appears within budget after screen opens | p95 < 8 s (Gemini ~3 s + HUD ~1.2 s + slack) |
| Rerolling one card updates the ranking | New ranking after the card changes |
| Leaving the augment screen clears the panel | Within ~1 s |
| Game FPS impact | Note before/after, no stutter |

## Recorded output

`data/live_sessions/<timestamp>/`:

- `events.jsonl` — every emitted event with the latency record from Phase 2
- `frames/` — the frame behind each `AdviceReady` (only with `logging.save_frames: true`)
- `summary.json` — p50/p95 per stage (capture, gate, augment, hud, advise), machine info,
  **capture path = `wgc-native`** (not VOD) so §12.1 numbers are not mixed with lossy sources

## After the match

- [ ] Latency p50/p95 into `docs/next-steps.md` §7.2 (replaces idle-machine numbers)
- [ ] Wrong reads → label those frames, add to eval set (next-steps §7.1 held-out set)
- [ ] ROI misses (hp §7.3, stage §7.4) → fix `config/screen_regions.yaml`, re-run replay tests
- [ ] Note any WGC border / consent behaviour in `research/open-questions.md` (closes line 78)

## Done when

Three augment rounds in one game produce a visible, correct-slot ranking with working hotkeys,
and `summary.json` exists with p95 inside budget.

## Related

- [Overview](overview.md)
- [Risks](risks.md)
