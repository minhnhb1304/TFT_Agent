# Phase 3 — App Shell

`scripts/run_live.py` — the one command the test machine runs. Wires capture, session,
overlay and hotkeys. Fully runnable against a replay source, so it is debugged without a game.

> The test machine already has an agent-made `run_live.py`. Rename or delete it before
> pulling, or git will refuse to overwrite the untracked file.

## CLI

```
python scripts/run_live.py                               # live: WGC on the game window
python scripts/run_live.py --source frames:data/frames/s7h-jHMpFmQ/augment_select --fps 1
python scripts/run_live.py --source video:"downloads/<vod>.mkv" --start 4200
python scripts/run_live.py --no-overlay                  # console only, prints events
```

## Startup order (order matters)

1. `SetProcessDpiAwareness(2)` — **before** `QApplication` (SPEC §3.6), or overlay coordinates
   drift on scaled monitors
2. `load_env()`, `Settings.load()`; print `Advisor.stale_data` if non-empty
3. Preflight (reuse Phase 0 checks): window found, borderless, build, key present. Fail → print
   the fix and exit 1; do not start a half-working overlay
4. `QApplication`, `create_windows()`, place panel at top-right of the **client rect**
5. `check_blockers(panel_rect)` — overlay must not cover any ROI (`assert_roi_disjoint_from_overlay`)
6. `GlobalHotkeyManager.install(app)`; print any binding that failed to register
7. Start `LiveWorker` QThread; `app.exec()`

## `src/live/app.py`

```python
class LiveWorker(QObject):
    event = pyqtSignal(object)          # LiveEvent, plain data
    def run(self): loop: frame = source.grab(); ev = session.step(frame); emit if not Idle; sleep to fps
    @pyqtSlot() def force_refresh(self)  # queued call from main thread
    def stop(self)

class LiveApp:
    def on_event(self, ev)               # main thread: panel.set_ranking / clear / status line
```

## Hotkeys

| Key | Action | Implementation |
|---|---|---|
| F1 | Show/hide overlay | `window.setVisible(not visible)` |
| F2 | Click-through on/off | toggle `WindowTransparentForInput`, re-`show()` (flag change hides the window) |
| F3 | Force refresh | queued `worker.force_refresh` |
| F4 | Detail on/off | panel shows reasons + `stale_data` / degraded lines |
| Ctrl+Q | Quit | `worker.stop()`, `hotkeys.uninstall()`, `app.quit()` |

`WindowStaysOnTopHint` + `Tool` + `WA_ShowWithoutActivating`: the overlay never steals focus
from the game, which is exactly why hotkeys must be global and not `keyPressEvent`.

## Shutdown

Ctrl+Q, console Ctrl+C, and game-window-closed all go through one `shutdown()`:
stop worker → join thread (timeout 15 s, Gemini max) → close capture → unregister hotkeys.

## Tests

- `QT_QPA_PLATFORM=offscreen`: frames replay source → panel `rows()` match expected ranking
- Hotkey callbacks call the right handler (dispatch by id, no OS registration in test)
- Startup aborts with exit 1 when preflight fails (fake window finder)

## Related

- [Overview](overview.md)
- [Phase 4 — Live validation](phase-4-validation.md)
