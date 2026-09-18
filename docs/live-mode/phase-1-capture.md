# Phase 1 — Capture Source

A `FrameSource` over the live game window, so every vision module written against VODs runs
unchanged (`src/capture/frame_source.py` docstring promised exactly this).

## Files

| File | Content | Tested how |
|---|---|---|
| `src/capture/game_window.py` | Find window, client rect, borderless check | Pure crop math unit-tested; Win32 calls thin |
| `src/capture/screen_capture.py` | `WindowCaptureSource` (WGC), `DesktopCropSource` (mss, fallback) | Fake backend injected |
| `config/settings.yaml` `capture:` | `backend: wgc \| mss`, `window_title`, `window_class`, `fps: 5` | Settings test |
| `tests/test_screen_capture.py` | Contract + crop + resize tests | Headless |

## `game_window.py`

```python
@dataclass(frozen=True)
class ClientRect:            # screen coordinates of the client area
    left: int; top: int; width: int; height: int

def find_game_window(title: str, cls: str) -> int | None     # FindWindowW, no OpenProcess
def client_rect(hwnd: int) -> ClientRect                      # GetClientRect + ClientToScreen
def is_borderless(hwnd: int, monitor: ClientRect) -> bool
def crop_offset(window_rect, client: ClientRect) -> tuple[int, int]   # pure, tested
```

## `screen_capture.py`

```python
class WindowCaptureSource:        # satisfies FrameSource
    def __init__(self, title, *, backend=None, target_size=(1920, 1080), clock=time.time): ...
    size -> target_size
    grab(at=None) -> Frame | None  # latest frame: BGRA -> BGR, crop client, resize; None if none yet
    frames(start=0.0, end=None)    # yields grab() at settings fps until end (wall clock)
    close()
```

- WGC is callback-driven: `on_frame_arrived` stores **only the latest** buffer under a lock;
  `grab()` copies it. No queue → no backlog when the reader is slow.
- `Frame.ref = format_ref("live", t)` with wall-clock `t` (the protocol docstring's rule).
- `on_closed` (game exited) sets a flag; `grab()` returns `None` and the worker reports
  "game window closed".
- Backend is injected (`backend=FakeBackend(frames)`) so tests never touch Win32.

## Tests

- `isinstance(WindowCaptureSource(..., backend=fake), FrameSource)`
- Crop removes chrome offset measured in Phase 0 (Q5); output is exactly 1920×1080 BGR uint8
- 2560×1440 and 1600×900 inputs resize correctly; non-16:9 client raises a clear error
- `grab()` before first frame → `None`; after close → `None`
- Read-only invariant test still green (new files scanned automatically)

## Done when

`python tools/probe_environment.py` uses `WindowCaptureSource` instead of raw WGC calls and
produces the same frames as Phase 0.

## Related

- [Overview](overview.md)
- [Phase 0 — Spike](phase-0-spike.md)
- [Phase 2 — Live session core](phase-2-session.md)
