# TFT Advisory Agent Research

## Verdict — proceed, but change the architecture and the feature contract

The technical design survives scrutiny better than the spec itself assumes. Riot's June 2026 Vanguard
On-Demand post defines the computer-vision cheat class as "a computer vision cheat that **injects player
input**" ([riotgames.com](https://www.riotgames.com/en/news/vanguard-on-demand)) — injection is the
defining trait, so read-only DXGI capture plus a `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`
window matches no documented detection surface. **§1.3's forbidden list is correctly calibrated and must
not change.**

The blocker is **policy, not anti-cheat**. Riot's TFT developer policy
([developer.riotgames.com/docs/tft](https://developer.riotgames.com/docs/tft)) names all three priority
features from §9 decision #4 as unapproved use cases, and binds the project regardless of API use: *"If
your product serves players, you must register it with us regardless of whether or not your product uses
official documented APIs."* A narrow legal corridor does exist and is precisely describable — **static
pre-game metadata, surfaced against the three offered choices, never ranked, never prescribed, never
recomputed from live board state.** Redesign into that corridor now rather than retrofitting later.

Three further findings block day one: the §6 `requirements.txt` **does not install**, the §9.1 LLM stack
is **end-of-life**, and **Set 18 is not live until 2026-08-26** — §8 assumes otherwise.

## Risk by sub-topic

| Sub-topic | Risk | Bottom line |
|---|---|---|
| [Ban risk & Riot policy](vanguard-risk.md) | **high** | Vanguard is low risk; the TFT developer policy prohibits the Augment Advisor *as specified*. A permitted narrower version exists. |
| [Set 18 & data sources](set-data.md) | **blocker** | Set 18 is not live until 2026-08-26. Data is fetchable today on the `/pbe/` branch, but four CommunityDragon traps cause silent empty loads. |
| [Vision stack](vision-stack/overview.md) | **high** | Two dependency pins are unsatisfiable/dead. The top-ranked risk (Vietnamese diacritics) is measured and refuted; the real risk is augment tier collisions. |
| [Prior art & LLM layer](prior-art.md) | **high** | Every open-source TFT overlay is dead. OP.GG ships an MIT-licensed MCP server that replaces the entire scraping layer. |
| [Open questions](open-questions.md) | — | Four primary sources are unfetchable by any agent; two 10-minute tests would settle hard dependencies. |

## Spec changes required

| SPEC section | Now known to be wrong / stale | Change to |
|---|---|---|
| §6 `dxcam>=0.4.0` | **REFUTED — hard install failure.** `0.4.0` exists only as `0.4.0.dev1`, which PEP 440 sorts *below* `0.4.0`. Latest real release is `0.3.0` ([PyPI](https://pypi.org/pypi/dxcam/json)) | `dxcam>=0.3.0` |
| §6 / §9.1 `google-generativeai>=0.8.0` | **REFUTED.** `0.8.6`, `Development Status :: 7 - Inactive`; support ended permanently 2025-11-30 ([PyPI](https://pypi.org/pypi/google-generativeai/json)) | `google-genai` (live at `2.18.0`) |
| §9.1 `gemini-1.5-flash` | **REFUTED.** Shut down 2025-09-29; `gemini-2.0-flash` also shut down ([changelog](https://ai.google.dev/gemini-api/docs/changelog), [models](https://ai.google.dev/gemini-api/docs/models)) | `gemini-2.5-flash-lite` or `gemini-3.5-flash-lite` |
| §9.1 "free tier: 15 RPM, 1M tokens/day" | **REFUTED.** Google no longer publishes free-tier RPM/TPM/RPD at all; the docs now say only *"View your active rate limits in AI Studio"* ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)) | Delete the quota figure. Build backpressure + a hard cap + a deterministic local fallback. |
| §4 / §6 `easyocr` | Last release 2024-09-24, drags in `torch`+`torchvision` ([PyPI](https://pypi.org/pypi/easyocr/json)) | `rapidocr>=3.9.2` pinned to a **PP-OCRv6** recognition model (only v6 lists `vi`) |
| §8 "Set 18 đã xuất hiện trên PBE… Chỉ focus vào Set 18" | Set 18 launches **2026-08-26**; live `mDefaultSet` is `TFTSet17` | Point all URLs at `/pbe/` until launch; build machinery against Set 17; gate cutover on `mDefaultSet` flipping |
| §8 Data Sources → Data Dragon | No Set 18 keys; newest version `16.16.1` while TFT is on patch 17.x | Demote to fallback or drop |
| §8 Data Sources → MetaTFT/lolchess/TFTactics scraping | Superseded | OP.GG MCP, MIT licensed, `https://mcp-api.op.gg/mcp` ([README](https://raw.githubusercontent.com/opgginc/opgg-mcp/main/README.md)) |
| §9 decision #4 priority order | Augment Advisor as specified is a named prohibition | **Comp Selector → Economy → Augment (static stats only, unranked)** |
| §9 decision #5 "Overwolf — khảo sát thêm" | Its GEP already returns `board` (grid position + star level + items), `bench`, `store`, `augments` | Resolve the decision: spike it for one day before writing board-reading CV |
| §3.6 Overlay | `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` is absent — the overlay composites into its own capture | Add it (`0x11`), gate on Win10 2004+ ([MS Learn](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)) |
| §3.1 Capture | `dxcam` is *desktop*-scoped | Evaluate `windows-capture` 2.0.1 (WGC, **window**-scoped, non-hooking) ([PyPI](https://pypi.org/pypi/windows-capture/json)) |
| §1.3 "Riot Official API" listed as safe live source | No live TFT state API exists — Live Client Data API is Summoner's-Rift-only, request open since 2020 ([issue #373](https://github.com/RiotGames/developer-relations/issues/373)) | Mark as post-game aggregation only |

**Not a change:** §8's `tft-match-v1` is correct. `tft-match-v5` does not exist; that claim was a
researcher error about the spec, not a spec error.

## Related

- [Ban risk & Riot policy](vanguard-risk.md)
- [Set 18 status & data sources](set-data.md)
- [Vision stack](vision-stack/overview.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
- [Open questions](open-questions.md)
