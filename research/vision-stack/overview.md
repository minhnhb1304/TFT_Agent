# Vision Stack

> **Verified:** 2026-08-28. All PyPI pins re-checked the same day and unchanged from the previous pass
> except `google-genai`, now **2.20.0**.

**Bottom line:** two §6 pins block installation on day one. The risk every researcher ranked highest —
Vietnamese diacritics — is **refuted by direct measurement** (see [OCR & matching](ocr.md)); the real
matching risks are augment **tier resolution** and **name collisions**, both measured in
[augments.md](augments.md). And the hardest CV work (board grid + star levels) may not need to be
written at all.

## Install blockers — fix before anything else

| §6 line | Failure | Fix |
|---|---|---|
| `dxcam>=0.4.0` | **Unsatisfiable.** PyPI releases are `0.0.5, 0.1.0.dev1, 0.1.0.dev2, 0.1.0, 0.2.0.dev1, 0.2.0, 0.3.0.dev1, 0.3.0, 0.4.0.dev1` — PEP 440 sorts `0.4.0.dev1` **below** `0.4.0`, so nothing satisfies the pin. Latest real release is **0.3.0**, `requires_python >=3.10` | `dxcam>=0.3.0` |
| `google-generativeai>=0.8.0` | `0.8.6`, `Development Status :: 7 - Inactive`, EOL 2025-11-30; §9.1's `gemini-1.5-flash` shut down 2025-09-29 | `google-genai` (live at **`2.20.0`**, 2026-08-25) + a current Flash model ID |

## Capture backend

| Option | Verdict | Reasoning |
|---|---|---|
| `dxcam` 0.3.0 (DXGI) | **Keep as default** | Genuinely revived: 0.0.5 (2022-09-04) → 0.1.0 (2026-03-08) → **0.3.0 (2026-03-12)**, wheels CPython 3.10–3.14, nothing yanked. README: *"Fast Python Screen Capture for Windows - Updated 2026"*, *"Support DXGI / Windows Graphics Capture dual backend"*. The widespread "dxcam is dead, use BetterCam" advice is stale ([PyPI](https://pypi.org/pypi/dxcam/json)) |
| `dxcam` WinRT backend | **Free fallback tier** | CHANGELOG 0.2.0 adds *"WinRT backend support"*; 0.3.0 adds *"proper handling of the DXGI mode switch (exclusively ↔ normal)"*. Exposed via `backend=`, so ship both behind one interface and auto-detect black frames |
| `windows-capture` 2.0.1 (WGC) | **Evaluate — highest-leverage change available** | Uploaded 2026-08-08, Python 3.9+, exposes `window_name` and a `draw_border` flag ([PyPI](https://pypi.org/pypi/windows-capture/json)). Captures a **window**, not the desktop — which dissolves the self-capture problem entirely. Non-hooking; the API OBS migrated to ([MS Learn](https://learn.microsoft.com/en-us/windows/uwp/audio-video-camera/screen-capture)) |
| `mss` | **Keep wired and tested** | At the spec's 10 FPS target, capture throughput is not the bottleneck — OCR is. Choose on robustness (HDR, hybrid GPU, adapter switching), not FPS |
| RapidShot | **Do not adopt** | 2 stars, vendor-self-reported 13.6% vs 79.7% CPU, no third-party measurement |

**Known issue, over-graded elsewhere:** [dxcam #139](https://github.com/ra1nty/DXcam/issues/139) —
`AttributeError: module 'comtypes' has no attribute 'IUnknown'`. Real and open, but the reporter states
reinstalling `comtypes` also fixes it, on Win11 + CPython 3.14.2 under conda. Pin `comtypes`, test import
in a clean venv; not a blocker.

## The overlay poisons its own capture — §3.6 is missing one line

`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` where `WDA_EXCLUDEFROMCAPTURE = 0x00000011`:
*"The window is displayed only on a monitor. Everywhere else, the window does not appear at all."*
([MS Learn](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity))

| Constraint | Consequence for PyQt6 |
|---|---|
| HWND must be **top-level** and owned by the calling process | Apply to the top-level overlay window, not a child widget |
| Requires DWM compositing | Fails silently on a non-composited desktop |
| Pre-Win10 2004 it degrades to `WDA_MONITOR` | Paints a **blank rectangle over the ROIs you are reading** — worse than doing nothing. Check the OS build at startup |

This is exactly why `jfd02/TFT-OCR-BOT`'s README demands *"Make sure you don't have any overlays on
(Blitz, Mobalytics, etc.)"* — it has no such exclusion.

## Board reading may not need to be written

All three vision researchers concluded board grid position and star levels are unsolved original R&D.
**REFUTED at the platform layer:** Overwolf's TFT GEP (game ID 21570, PBE 215701) documents `board` —
*"Exact position of each chess piece on the grid, including their current level and the items they
possess"* — plus `bench` (star levels + items), `store`, `augments`, `me` (gold/level/XP/health)
([Overwolf](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/teamfight-tactics/)).
That is a superset of the vision pipeline's targets. §9 decision #5 already flagged this as "khảo sát
thêm" — resolve it with a one-day spike before writing CV code. Cost is real: it requires the Overwolf
client runtime and a JS/Electron stack, and it does **not** cure the policy problem.

## Reusable prior art — and what not to reuse

| Reuse | Don't reuse |
|---|---|
| `ocr.py` preprocessing: 3× upscale → `COLOR_BGR2GRAY` → `THRESH_BINARY_INV + THRESH_OTSU` → PSM 7 + char whitelist | The 28-entry `BOARD_LOC` pixel table (2024, Set 11 era) — lift the *method* (fractions of the client rect), re-measure the values |
| The `(0,255,18)` health-colour slot-occupancy probe (`np.all(... axis=-1)` + `np.convolve`) | `requirements.txt` — it contains **PyDirectInput**, the synthetic-input library whose absence is this project's entire §1.3 compliance claim |
| Hard constraint to inherit: **1920×1080 borderless windowed, primary monitor** | Level/HP from `127.0.0.1:2999` — documented for League only; untested for TFT. Keep the OCR path |

## Related

- [OCR engine & matching rules](ocr.md)
- [Augment pipeline](augments.md) — tier ladder, unrecoverable pairs
- [Research overview](../overview.md)
- [Ban risk & Riot policy](../vanguard-risk.md)
- [Set 18 status & data sources](../set-data.md)
- [Prior art, overlay UI & LLM layer](../prior-art.md)
- [Open questions](../open-questions.md)
