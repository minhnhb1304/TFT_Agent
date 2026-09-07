# Capture Design Decision

Why the capture layer is **window-scoped** and why `SetWindowDisplayAffinity` is **off by
default**. Decided 2026-09-04, before `src/capture/` was written.

## The decision

One design choice retires three separate exposures. It cost nothing because the module did not
exist yet — `src/capture/` and `src/vision/` were empty at the time of the assessment.

| Exposure | Old design | Now |
|---|---|---|
| `NtUserGetWindowDisplayAffinity` — hooked in `vgk.sys`; a peer AC uploads the value | Called on both overlay windows, mandatory | Not called (`overlay_capture_protection: false`) |
| `NtGdiDdDDIOutputDuplGetFrameInfo` — hooked in `vgk.sys` | `dxcam` would call it ~5×/sec | Window-scoped capture uses a different path |
| Self-capture feedback loop | Suppressed by the affinity flag | Structurally impossible |

**None of the three is proven to trigger anything.** The argument is not that Vanguard acts on
them. It is that all three disappear together for the price of choosing a different capture API
before writing the module, and no comparable argument exists for keeping them.

## Why the old design existed, and why the reason no longer holds

The original docstring in `overlay_window.py` was right about the problem: without capture
protection, the overlay lands in the frame it is capturing, vision re-reads its own text, and
the advisor feeds on its own output. That failure is silent and very hard to trace.

But the fix was aimed at the symptom. Capturing the **game window** instead of the **desktop**
means another process's topmost overlay is not in the captured content at all — the loop cannot
form, so nothing needs suppressing. The bug class is designed out rather than masked.

## Why the affinity call was worth removing

Three reasons, in ascending order of weight:

1. **It is trivially detectable.** `GetWindowDisplayAffinity` reads the value *"from any
   process"*, with no ACL and no elevation
   ([MSDN](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowdisplayaffinity)).
2. **A peer anti-cheat already collects it.** Activision's TAC enumerates overlapping windows,
   queries `GetWindowTextW`, `GetClassNameA` and `GetWindowDisplayAffinity`, then encrypts and
   uploads the value ([ssno.cc, 2025-01](https://ssno.cc/posts/reversing-tac-1-4-2025/)).
   Collection is blanket, for any window carrying the flag. *Caveat:* TAC is user-mode with no
   kernel component, so this proves the check is industry-real, not that `vgk.sys` performs it.
3. **It is the only call in the stack whose shape resembles evasion.** Riot confirmed it
   photographs the region the client occupies, looking for overlays. A visible advisory panel
   is judged on its **content**, which is benign. A window deliberately hidden from that
   photograph is judged on its **behaviour**, which reads as evasion regardless of intent.

Point 3 is the one that matters for the thesis defence. Choosing visibility is the option
consistent with the honesty standard `SPEC §11.5` already sets — there is nothing here worth
hiding, so hide nothing.

## Counter-argument, stated fairly

The flag is emphatically **not** cheat-exclusive. KeePassXC ships it deliberately
([PR #6030](https://github.com/keepassxreboot/keepassxc/pull/6030)), Signal Desktop ships it in
production, and ZH sources record it as the standard recommendation for banking and
cloud-desktop clients. And the **setter** is ownership-gated — even an Administrator process
cannot set affinity on another process's window
([IOActive](https://www.ioactive.com/signal-windows-desktop-contentprotection-bypass/)), so the
call cannot be spoofed onto this project or forced by anyone else.

Nobody has shown Vanguard checks it. Keeping it would probably have been fine. It was removed
because a free alternative existed, not because the flag was proven dangerous.

## What was implemented

| Change | File |
|---|---|
| `create_windows(..., capture_protection=False)` — default off, `protection` dict empty when disabled | `src/overlay/overlay_window.py` |
| `apply_capture_protection()` kept intact and fully tested — the fallback path for setups where window-scoped capture is unavailable | `src/overlay/overlay_window.py` |
| `capture:` section — `window_scoped`, `overlay_capture_protection`, `assert_roi_disjoint_from_overlay` | `config/settings.yaml` |
| `test_capture_protection_is_off_by_default` — the default is now a verifiable property, not an intention | `tests/test_overlay.py` |

## Still to build

- **Window-scoped capture** in `src/capture/` — Windows Graphics Capture against the
  `League of Legends.exe` window, or DXGI cropped to the game rect with the overlay outside it.
- **ROI disjointness assertion** in `tools/calibrate.py` — the overlay panel must not intersect
  any OCR region. `assert_roi_disjoint_from_overlay: true` is already in settings; the check
  turns a layout convention into a verifiable invariant, and is the second line of defence if
  window-scoped capture ever falls back to desktop capture.

## Related

- [Detection surface](detection-surface.md) — the hook and screenshot evidence behind this
- [Overview](overview.md) — bottom line and the six answers
- [Testing protocol](testing-protocol.md) — how to validate this without risking the machine
