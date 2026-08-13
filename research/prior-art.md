# Prior Art, Overlay UI and the LLM Layer

**Bottom line:** every open-source TFT overlay is dead or archived — budget for building capture, OCR,
state model and overlay from scratch. But two §8/§10 assumptions are refuted: the planned scraping layer
is replaced by an official MIT-licensed API, and the §9.1 LLM stack is end-of-life.

## Existing projects

| Project | Stars | Status | Lesson |
|---|---|---|---|
| [jfd02/TFT-OCR-BOT](https://github.com/jfd02/TFT-OCR-BOT) | 341 | Archived **2026-04-09** (last push 2024-04-18) | The only usable code reference. README: *"16:9 resolution borderless windowed is required… (Use 1920x1080 for best results)"*, *"League & client must be in English"*, *"Make sure you don't have any overlays on"*. **Not** killed by Vanguard — the two-year gap between last push and archival refutes that story |
| [Kyrluckechuck/TFT-Bot](https://github.com/Kyrluckechuck/TFT-Bot) | 44 | Archived 2024-04-20 | The one genuine primary-source Vanguard warning: *"a liability against any accounts it's run by"*. It automates input (global keyboard listening, draft pathing, auto-purchase). Different risk class — cited as support for §1.3, not against screen capture |
| [TeamFightTacticsBots/Alune](https://github.com/TeamFightTacticsBots/Alune) | 105 | Active | Migrated to Android emulator + ADB. The "deliberately to escape Vanguard" motive is **researcher inference** — the README never mentions Vanguard. Hypothesis, not finding |
| Just2good/TFT-Overlay | 630 | Dead since 2021 | Per-set data churn is the documented killer |
| Antize/TFT-Overlay-Outdated | ~50 | Dead — maintainer **renamed the repo** to say "Outdated" | Same |
| [MetaTFT](https://www.overwolf.com/app/metatft.com-metatft) | 8.02M downloads | Live | The market answer is "consume Overwolf's event feed", not screen capture. Advertises *"live augment stats, comp recommendations, win chance estimates, lobby scouting"* — which contradicts Overwolf's own compliance doc |
| [Questie.ai](https://questie.ai/gaming-ai/teamfight-tactics) | commercial, $19.99/mo | Live | Direct competitor doing VLM screen-reading: *"analyzing your screen in real time… No API integration required"*. Two risk choices worth copying: **deliver by voice** (no overlay window, no self-capture) and time advice to natural pauses. Makes no ToS or ban-safety claim anywhere |

**Never verified from an Overwolf primary source:** that Overwolf works by DirectX hooking. The getting-started
page only says apps *"run on top of the Overwolf Desktop App"*. It is corroborated only indirectly, by
[dev-relations #1071](https://github.com/RiotGames/developer-relations/issues/1071)'s author framing his
alternatives as a transparent window vs *"injecting a Riot-approved .dll"*. Do not assert the mechanism.

## Overlay UI

| Item | Guidance |
|---|---|
| Exclusive fullscreen | **Cannot be overlaid** — it bypasses the DWM compositor that honours z-order. Independently asserted across 3 languages and corroborated by `jfd02`'s borderless-windowed requirement. Detect display mode at startup and refuse to run with a clear message rather than rendering nothing |
| Two windows, from the start | `WS_EX_TRANSPARENT` is all-or-nothing — one window cannot mix a click-through background with clickable widgets. Retrofitting this is painful |
| Skip the ctypes layer | PyQt6 exposes everything natively: `FramelessWindowHint \| WindowStaysOnTopHint \| Tool \| WindowTransparentForInput`, plus `WA_TranslucentBackground` and `WA_ShowWithoutActivating`. No `SetWindowLong` needed |
| DPI | `SetProcessDpiAwareness(2)` **before** `QApplication` construction. Drop the Qt5-era `AA_EnableHighDpiScaling` |
| Positioning | `GetClientRect` + `ClientToScreen`, not `GetWindowRect`. Re-sync on a timer |
| Self-capture | Add `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` — see [vision stack](vision-stack/overview.md) |
| Trigger | Not a continuous 10 FPS loop. TFT is turn-based with a ~30 s planning phase; working prior art polls at 200 ms behind a dual-aHash gate, or fires once on a hotkey. Hotkeys inside the game window need `WH_KEYBOARD_LL` and therefore admin rights |

## Meta data sources — §8 scraping plan is superseded

| Source | Verdict |
|---|---|
| **OP.GG MCP** — `https://mcp-api.op.gg/mcp`, Streamable HTTP, **MIT** ([README](https://raw.githubusercontent.com/opgginc/opgg-mcp/main/README.md)) | **Adopt.** Six TFT tools confirmed: `tft_get_champion_item_build`, `tft_get_play_style`, `tft_list_augments`, `tft_list_champions_for_item`, `tft_list_item_combinations`, `tft_list_meta_decks`. Feeds Comp Selector + Item Advisor + Economy directly. **Caveat:** the README documents no API key, **no rate limits and no ToS grant** — email OP.GG before depending on it |
| MetaTFT / lolchess / TFTactics scraping (§8) | **Drop as primary.** Only MetaTFT's ToS was ever retrieved and it has no scraping clause; permissive `robots.txt` is not a licence |
| Fallback if OP.GG declines | A **centralised** server-side Playwright crawl on a 4-hourly cron into your own DB — never scraping from each user's machine |
| CommunityDragon `vi_vn.json` | **Keep.** 28 locales, all refreshed on one daily pipeline (identical timestamps). Use as a constrained OCR lexicon and cross-join to `en_us.json` by ID |

## LLM layer — §9.1 must be rewritten

| §9.1 as written | Reality |
|---|---|
| `import google.generativeai as genai` | `Development Status :: 7 - Inactive`; publisher states *"All support for this repository ended permanently on November 30, 2025"* ([PyPI](https://pypi.org/pypi/google-generativeai/json)). → `google-genai` |
| `GenerativeModel('gemini-1.5-flash')` | Shut down 2025-09-29. `gemini-2.0-flash` and `-lite` also marked **(Shut down)** ([models](https://ai.google.dev/gemini-api/docs/models)). → `gemini-2.5-flash-lite` ($0.10/$0.40 per 1M) or `gemini-3.5-flash-lite` |
| "Chi phí ~$0 — free tier: 15 RPM, 1M tokens/day" | No free-tier RPM/TPM/RPD table exists any more; docs say only *"View your active rate limits in AI Studio"* ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)). Free tier is marked *"Used to improve our products: Yes"* for every Flash model |
| Screenshot upload on free tier | Human review is permitted — though all researchers omitted the mitigating clause *"disconnecting this data from your Google Account, API key, and Cloud project before reviewers see or annotate it"* ([terms](https://ai.google.dev/gemini-api/terms)). The real exposure is **in-frame**: eight summoner names are pixels, not metadata. **Crop to the augment/shop ROI before upload**, and use the paid tier |
| Structured JSON output | Supported and Pydantic-native, but *"Very large or deeply nested schemas may be rejected"* ([docs](https://ai.google.dev/gemini-api/docs/structured-output)). Keep the response a **flat** list of `{name, verdict_enum, one_line_reason}` |
| Latency budget "~2-3s" (§9.3 Approach A) | Unresolved. The two benchmarks found measure different things — ~450 ms TTFT text-only vs ~7,500 ms full-page document OCR at n=1. Neither measures a small cropped game-UI crop, which is far cheaper. Measure it yourself against a pinned model ID |

**Architectural consequence:** the LLM must never sit on the critical path of a timed decision. Render a
deterministic answer immediately from a rules+stats engine (interest breakpoints, level EV, trait fitting
are closed-form arithmetic) and let any LLM response arrive as an optional refinement behind a hard
timeout. Route through an OpenAI-compatible abstraction so the reasoning layer stays vendor-swappable.

## §8 assumption to correct

Building template assets against **PBE Set 18** means rebuilding them at live launch and again at mid-set.
No researcher connected this to their own survivorship evidence, yet per-set churn is what killed every
overlay above. Build the asset pipeline to **regenerate automatically** from CommunityDragon rather than
hand-curating, and defer final template capture until 2026-08-26.

## Related

- [Research overview](overview.md)
- [Ban risk & Riot policy](vanguard-risk.md)
- [Set 18 status & data sources](set-data.md)
- [Vision stack](vision-stack/overview.md)
- [Open questions](open-questions.md)
