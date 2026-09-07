# Detection Surface

What Vanguard demonstrably does, what it is merely *positioned* to do, and what it structurally
cannot do. Verified 2026-09-04.

## What `vgk.sys` hooks

An April 2025 reverse-engineering of Vanguard's syscall dispatch table
([archie-osu](https://archie-osu.github.io/2025/04/11/vanguard-research.html)) shows case
entries for:

| Hooked syscall | Reached by |
|---|---|
| `NtGdiDdDDIOutputDuplGetFrameInfo` | `IDXGIOutputDuplication::GetFrameInfo` — i.e. `dxcam` / Desktop Duplication |
| `NtUserGetWindowDisplayAffinity` | Any display-affinity query |
| `NtGdiBitBlt`, `NtGdiDdDDIPresent` | GDI blit, DXGI present |

**This is not evidence of detection.** The RE author explicitly deferred analysing what the
hook bodies do — block, log, report, or pass through is unknown — and worked against the
VALORANT-context driver, in April 2025, on a driver that has changed since.

But it does change the honest claim. Not *"no evidence Vanguard watches Desktop Duplication"*
but **"Vanguard sits on that syscall and nobody has looked inside."** State it that way.

## What Riot confirmed it captures

Matt "K30" Paoletti, Senior Anti-Cheat Analyst, May 2024, during the LoL/TFT rollout
([PCGamesN](https://www.pcgamesn.com/league-of-legends/riot-vanguard-response), cross-verified
against a second outlet):

> Vanguard *"DOES NOT take a screenshot of your whole computer/multiple monitors"* but *"will
> take a picture of your game client (in fullscreen) and the region your game client occupies
> (in windowed/borderless) **for suspicious activity related to ESP hacks**."*

Read against this project: the overlay runs borderless, inside that region, and the capture is
of composited output — so it **includes the overlay**. The stated purpose of the capture is
finding overlays. This is the most direct risk vector in the assessment, and it comes from
Riot on the record rather than from driver speculation.

**Why it is still acceptable.** The target is ESP: enemy positions, boxes, skeletons. A text
panel ranking three augments is not ESP-shaped, and `enable_scouting: false` keeps it from
becoming opponent-board-shaped. Overlays over the League client are ubiquitous and partly
sanctioned — Discord, Steam, Overwolf, Blitz, op.gg all draw there, and Riot's own FAQ says
overlays should keep working.

> ⚠️ **Do not cite Riot's 2020 statement** that the driver *"does not collect or send any
> information about your computer back to us"*. It is contradicted by their own 2024 screenshot
> admission. Cite the 2024 one.

## Window-style enumeration

`EnumWindows` + `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST` + geometry overlap is a
documented heuristic — for EasyAntiCheat and BattlEye
([secret.club](https://secret.club/2019/02/10/battleye-anticheat.html)), and for Tencent
CrossFire ([52xuejishu](https://www.52xuejishu.com/forum-post/1799.html), ZH).

That is a precise description of this project's overlay. **But every source describes it as a
signal, never a standalone trigger.** BattlEye pairs it with a *title blacklist* and
module-integrity checks on recognised overlay hosts, and its own FAQ says *"No one is banned
for using non-hack programs (like Fraps, overlays, etc.)"*. No documented case anywhere of a
ban attributed solely to window style. The sweep would enumerate Discord and OBS too.

No Vanguard-specific evidence of this sweep exists in any language.

## Passive window handles — structurally unobservable

This one is settled rather than merely unevidenced, and it is the cleanest result in the
assessment.

- `ObRegisterCallbacks` — the mechanism anti-cheat drivers use to intercept handle acquisition —
  supports **only** `PsProcessType`, `PsThreadType`, `ExDesktopObjectType`
  ([Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_operation_registration)).
- An `HWND` is **not an Object Manager handle at all**. It is an index into the separate USER
  handle table maintained by `win32k.sys`
  ([Geoff Chappell](https://www.geoffchappell.com/studies/windows/win32/user32/structs/handleentry.htm)).

So `OpenProcess` is fully observable to a kernel driver, and `FindWindow` / `EnumWindows` /
`GetClientRect` / `ClientToScreen` / `GetWindowThreadProcessId` have **no equivalent kernel
observability path**. This holds by Windows architecture, not by vendor policy — so it holds
for Vanguard regardless of what its hook bodies do.

This is why `SPEC §1.3`'s ban on `OpenProcess` is the correct line to draw, and why window-rect
queries sit safely on the other side of it.

## `python.exe`

No evidence either way that Vanguard flags unsigned or interpreted runtimes absent memory or
input activity. Riot's FAQ never mentions binaries, signatures, or interpreters — only memory.

The one comparative case, [Kyrluckechuck/TFT-Bot](https://github.com/Kyrluckechuck/TFT-Bot),
self-archived 2024-04-20 calling itself *"a liability against any accounts it's run by, even
when only run as source code"* — but it drove `pyautogui` and `keyboard`, and the notice cites
**no actual ban**. Precautionary self-archival by an input-automating bot. It is not evidence
about a passive tool, and should not be cited as if it were.

## Related

- [Overview](overview.md) — bottom line and the six answers
- [Capture design decision](capture-design.md) — what was changed as a result
- [`../vanguard-risk.md`](../vanguard-risk.md) — Riot policy analysis
