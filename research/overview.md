# TFT Advisory Agent Research

> **Verified:** 2026-08-28 against `/latest/`. The 2026-08-13 pass was written while Set 18 was
> PBE-only; its central blocker has since **resolved by calendar**. Everything else was re-measured.

## Verdict — proceed, but change the architecture and the feature contract

The technical design survives scrutiny better than the spec itself assumes. Riot's June 2026 Vanguard
On-Demand post defines the computer-vision cheat class as "a computer vision cheat that **injects player
input**" ([riotgames.com](https://www.riotgames.com/en/news/vanguard-on-demand)) — injection is the
defining trait, so read-only DXGI capture plus a `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`
window matches no documented detection surface. **§1.3's forbidden list is correctly calibrated and must
not change.**

The blocker is **policy, not anti-cheat** — and this conclusion is unchanged after re-verifying all
eight policy quotes verbatim. Riot's TFT developer policy
([developer.riotgames.com/docs/tft](https://developer.riotgames.com/docs/tft)) names the priority
features from §9 decision #4 as unapproved use cases, and binds the project regardless of API use: *"If
your product serves players, you must register it with us regardless of whether or not your product uses
official documented APIs."* A narrow legal corridor exists — **static pre-game metadata, surfaced
against the three offered choices, never ranked, never prescribed, never recomputed from live board
state.** Newly surfaced: the policy draws its line at **immediacy**, contrasting banned *"go here now"*
against permitted *"learning and coaching the player game over game"* — a post-round surface is safer
than a live in-round one.

**Set 18 is now live** (patch 18.1, 2026-08-26). The former day-one blocker is gone. Two day-one
blockers remain from the original pass: the §6 `requirements.txt` **does not install**, and the §9.1
LLM stack is **end-of-life**.

## Risk by sub-topic

| Sub-topic | Risk | Bottom line |
|---|---|---|
| [Ban risk & Riot policy](vanguard-risk.md) | **high** | Vanguard is low risk; the TFT developer policy prohibits the Augment Advisor *as specified*. A permitted narrower version exists. All quotes re-verified |
| [Set 18 & data sources](set-data.md) | **resolved** (was blocker) | Set 18 live since 2026-08-26. All URLs move `/pbe/` → `/latest/`. Five silent traps confirmed on live — one of them was in our own docs |
| [Vision stack](vision-stack/overview.md) | **high** | Two dependency pins are unsatisfiable/dead. Vietnamese diacritics measured and refuted |
| [Augment pipeline](vision-stack/augments.md) | **high** | **New.** Tier resolution rule was inverted; 4 augment pairs are unrecoverable by any recognition method |
| [Prior art & LLM layer](prior-art.md) | **high** | Every open-source TFT overlay is dead. OP.GG MCP replaces the scraping layer, but its ToS contradicts its own MCP server |
| [Open questions](open-questions.md) | — | Post-Unreal capture behaviour is now testable today and remains untested |

## Spec changes required

| SPEC section | Now known to be wrong / stale | Change to |
|---|---|---|
| §6 `dxcam>=0.4.0` | **REFUTED — hard install failure.** `0.4.0` exists only as `0.4.0.dev1`, which PEP 440 sorts *below* `0.4.0`. Latest real release is `0.3.0` ([PyPI](https://pypi.org/pypi/dxcam/json)) | `dxcam>=0.3.0` |
| §6 / §9.1 `google-generativeai>=0.8.0` | **REFUTED.** `0.8.6`, `Development Status :: 7 - Inactive`; support ended permanently 2025-11-30 ([PyPI](https://pypi.org/pypi/google-generativeai/json)) | `google-genai` (live at **`2.20.0`**) |
| §9.1 `gemini-1.5-flash` | **REFUTED.** Shut down 2025-09-29; `gemini-2.0-flash` also shut down ([models](https://ai.google.dev/gemini-api/docs/models)) | A current Flash model ID — verify at implementation time |
| §9.1 "free tier: 15 RPM, 1M tokens/day" | **REFUTED.** Google no longer publishes free-tier RPM/TPM/RPD ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)) | Delete the quota figure. Build backpressure + a hard cap + a deterministic local fallback |
| §4 / §6 `easyocr` | Last release 2024-09-24, drags in `torch`+`torchvision` ([PyPI](https://pypi.org/pypi/easyocr/json)) | `rapidocr>=3.9.2` pinned to a **PP-OCRv6** recognition model (only v6 lists `vi`) |
| §8 / §9 #6 "Set 18 chưa live — build trên Set 17, data `/pbe/`" | **STALE.** Live `mDefaultSet.SetName` = `TFTSet18` since 2026-08-26 | Point all URLs at `/latest/`. Keep the branch switch in config for the 2026-10-09 client |
| §3.2 "tier tra bằng lookup [icon path]" | **INVERTED.** Icon art is reused across tiers; 19/254 paths contradict the augment's own name | Resolve tier from `apiName`/`name`; icon path is fallback. Ladder in [augments.md](vision-stack/augments.md) |
| §8 trait art URL `trait_icon_18_<en_name>.png` | **REFUTED — string-built.** Resolves 34/36; two traits 404 | Read the `icon` field verbatim, `.tex`→`.png`, under `/latest/game/` — **36/36** |
| §9.2 "rủi ro tiếng Việt đã bác bỏ" | **Overclaimed.** Diacritics refuted (0 collisions), but 4 augment pairs share name *and* icon; VI is marginally worse than EN | Qualify: diacritics refuted, **name collisions are not** |
| §8 Data Sources → Data Dragon | No Set 18 keys | Demote to fallback or drop |
| §8 MetaTFT/lolchess/TFTactics scraping | Superseded | OP.GG MCP, MIT, `https://mcp-api.op.gg/mcp` — but see its ToS conflict in [prior-art](prior-art.md) |
| §9 decision #4 priority order | Augment Advisor as specified is a named prohibition | **Comp Selector → Economy → Augment (static stats only, unranked)** |
| §9 decision #5 "Overwolf — khảo sát thêm" | Its GEP already returns `board`, `bench`, `store`, `augments` | Spike it for one day before writing board-reading CV |
| §3.6 Overlay | `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` is absent — the overlay composites into its own capture | Add it (`0x11`), gate on Win10 2004+ ([MS Learn](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)) |
| §3.1 Capture | `dxcam` is *desktop*-scoped | Evaluate `windows-capture` 2.0.1 (WGC, **window**-scoped, non-hooking) |
| §1.3 "Riot Official API" listed as safe live source | No live TFT state API exists ([issue #373](https://github.com/RiotGames/developer-relations/issues/373)) | Mark as post-game aggregation only |

**Not a change:** §8's `tft-match-v1` is correct. `tft-match-v5` does not exist.

## Related

- [Ban risk & Riot policy](vanguard-risk.md)
- [Set 18 status & data sources](set-data.md)
- [Vision stack](vision-stack/overview.md) · [OCR & matching](vision-stack/ocr.md) · [Augment pipeline](vision-stack/augments.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
- [Open questions](open-questions.md)
