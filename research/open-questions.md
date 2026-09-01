# Open Questions

> **Re-graded:** 2026-08-28. Set 18's launch retired some questions and promoted others from
> "hypothetical" to "testable today". Ordered by decision impact.

## Settled 2026-09-01 by running the API with a real key

| Was | Now |
|---|---|
| "Can we self-crawl augment statistics from `tft-match-v1`?" | **No — settled, negatively.** The `augments` field no longer exists on a Set 18 participant, and `"augment"` appears nowhere in the match payload. Measured on `vn2`, 3 ranked Set 18 matches. See [set-data](set-data.md) |
| "Could a third-party stats site supply augment statistics instead?" | **No — settled 2026-09-02, and this is the stronger finding.** tactics.tools exposes four augment fields (`augmentSingles`, `aug1s`, `aug2s`, `aug3s`) and **all four are empty at every rank group**, including `all` at **1,752,735 games**; their `/augments` page returns `{"singles": [], "pairs": [], "trios": []}`. The largest public aggregator has no Set 18 augment data either, so this is **not a limitation of this project**. `augment_row_count()` in `src/knowledge/tactics_tools.py` re-measures it on every crawl |
| "Do datatft.com or tftacademy.com publish measured augment stats?" | **No — both publish human tier lists.** datatft ships its augment tiers **hardcoded in the JS bundle**, credited to named players (Horox, 九九, 云顶精神力); tftacademy shows S/A/B/C buckets with no numbers. Neither carries a sample size, and neither claims to. Usable only as an ordinal prior — see `ExpertTierListProvider` |
| "Does `tft-match-v1` still carry enough for meta comps?" | **Yes.** `units` (with `itemNames`), `traits` (with `style`/`num_units`), `placement`, `level` are intact — enough to measure comps and to back-fill placement for §12.2 |
| "Which regional host serves `vn2` for match-v1?" | **`sea`.** Confirmed by live call, not by inference |
| "Is `gemini-2.5-flash-lite` still available?" | **No.** HTTP 404: *"no longer available to new users… use models/gemini-3.5-flash-lite"*. The project now pins `gemini-3.5-flash-lite` |

> ⚠️ **Sample-size warning for `vn2`.** The apex ladder held **2 challenger** and **160 apex players
> total** on 2026-09-01 — the ranked season is young. Comp statistics crawled now carry small-sample
> uncertainty that must be reported, and a re-crawl closer to the deadline will be strictly better.

## Retired by the 2026-08-26 launch

| Was | Now |
|---|---|
| "When does Set 18 go live / is the data real?" | **Settled.** Live since 2026-08-26; roster, icons and traps all re-measured on `/latest/` — see [set-data](set-data.md) |
| "Capture the PBE client and diff its HUD against Set 17" | **Superseded.** The Unreal HUD is now the *live* HUD. This is ordinary calibration work against the live client, not research |
| "Which branch do we build against?" | **Settled.** `/pbe/` and `/latest/` are currently identical. Use `/latest/`; keep the switch for the 2026-10-09 client |

## Blocking — resolve before writing code

| Question | Why it is unresolved | Who can resolve it |
|---|---|---|
| Does Riot's TFT policy bind a **purely private, never-distributed, single-user** tool? | The registration clause is scoped to products that *"serve players"*, and developer enforcement runs through API-key revocation — which does not exist for an unregistered tool. No source addresses Riot's posture | Riot DevRel ticket. **Still the single most decision-relevant unknown** |
| **Does capture still work on the Unreal build?** | **Promoted.** Two days post-launch, EN searches found *no* reports of capture/overlay breakage — and *no* confirmation of safety. Absence of evidence, on a two-day window | **You, in 10 minutes.** See the test table below |
| Would Riot approve a registered product of this shape? | The policy text reads as a clear no for state-conditioned advice; registration outcomes are case-by-case with no public register to sample | Riot Developer Portal application |
| How does Overwolf obtain real-time TFT `board` / `bench` / `store` / `augments` when Riot's Live Client Data API carries none of it? | Injection, a private arrangement, or an undocumented endpoint — all consistent with the evidence | Unanswerable from public docs |
| Does the Riot/Overwolf **augment contradiction** resolve in favour of Riot's text? | Riot permits augment metadata; Overwolf says it *"can't be displayed"*; Blitz and tactics.tools ship it publicly today | Riot DevRel |
| Does OP.GG's MCP server actually serve **Set 18** data, and does its ToS permit use? | The endpoint proxies OP.GG's live backend, so Set 18 *should* flow — unverified by a live call. Separately, OP.GG's site ToS prohibits automated collection with no MCP carve-out ([prior-art](prior-art.md)) | A 5-minute smoke test; then an email to OP.GG |

## The user must verify these personally

| Test | Cost | What it settles |
|---|---|---|
| Capture one frame of TFT **on the Unreal build** and assert it is not uniformly black | 10 min | Whether Riot ships `SetWindowDisplayAffinity` on the client. **Nobody has run this on 18.1.** Treat capture as a **runtime precondition**, not an architectural invariant |
| Confirm the Unreal build still offers **borderless windowed** | 5 min | A hard dependency — exclusive fullscreen bypasses the DWM compositor and cannot be overlaid. **No source addresses this post-migration** |
| Record the client's **process name, executable and window class/title** on 18.1 | 5 min | Baseline for detecting what the 2026-10-09 standalone client changes. Cheap now, impossible retroactively |
| Run DXGI desktop duplication with TFT in **fullscreen-exclusive** | 10 min | Untested by every researcher |
| `GET https://127.0.0.1:2999/liveclientdata/allgamedata` during an actual **TFT** match | 5 min | Whether `activePlayer.level` and `championStats.currentHealth` are served for TFT. Do **not** remove level/HP from the vision pipeline until this passes |
| Call `tft_list_meta_decks` against `https://mcp-api.op.gg/mcp` | 5 min | Whether the meta layer has Set 18 data at all |
| Run RapidOCR PP-OCRv6 on a real 1080p **Unreal-rendered** TFT frame with the game running | 30 min | Every latency figure in the corpus is vendor-published or measured on an idle machine. The Unreal build has a higher GPU floor than Hextech |
| Confirm an Overwolf app (MetaTFT/Blitz) still receives live events on 18.1 | 15 min | Whether the GEP route survived the migration. Marketing pages referencing 18.1 are not evidence |

## Primary sources no agent could fetch

| Source | Failure | Consequence |
|---|---|---|
| `support.riotgames.com/hc/en-us/articles/225266848` (Third-Party Applications) | JS-rendered SPA returning a "Poro loading" shell. `web.archive.org` **blocked** to agents | The widely-quoted four "measurable player advantage" categories are **not primary-source confirmed**. **Drop this quote from any risk memo.** It does not change the verdict |
| `support-developer.riotgames.com` TFT article | **HTTP 403** | May contain supplementary policy detail; needs a manual browser check |
| Riot DevRel Vanguard FAQ (article 28021427366163) | HTTP 403 on both URL forms | *"There is absolutely no allow list"* remains second-hand. **Do not reason "MetaTFT does it through channels I could also use."** |
| [dev-relations #1071](https://github.com/RiotGames/developer-relations/issues/1071) comment thread | Could not render; author account deleted, closed *"unsuitable"* | **No public safe-harbour statement for transparent topmost overlays exists** |

## Cross-source tensions left genuinely unsettled

| Topic | The tension |
|---|---|
| Overwolf GEP after 2026-10-09 | GEP keys off LoL game ID **21570** and detects TFT queues via the LoL launcher's `lobby_info`. Both anchors disappear when TFT leaves the League client. Overwolf's docs still mention neither Set 18, Unreal, nor the standalone client. **The sanctioned route may break on the same date as the scraping route** |
| Is Overwolf's TFT GEP formally Riot-authorised or merely tolerated? | No Riot-owned page names Overwolf. Treat as **unproven** |
| Does CommunityDragon's TFT feed survive the standalone client? | It survived 18.1 intact — a good sign. But if TFT data migrates into Unreal-client files a League extractor cannot parse, the project's primary data source dies. The Oct 9 client is the real test |
| Does the Oct 9 client change process name / window class / title? | No Riot statement; standalone PBE reported ~2026-09-09 (secondary sources only). Directly determines whether DXGI window targeting survives |
| Was the policy's opponent-prediction clause always there? | The *"including the loading screen"* opponent-tracking sentence is present today but could not be diffed against a March-2025 snapshot (archive.org blocked). Reads as elaboration, not contradiction |
| Would Riot treat OCR acquisition as "unregistered" or as **anti-cheat evasion**? | Riot's policies are behaviour-based and silent on OCR as an acquisition method for *advisory* tools |
| Has Riot **ever** banned a player for a read-only screen-capture overlay? | Four independent language searches: zero confirmed cases, and zero Riot statements affirming safety. Empirical ban risk is low; policy risk is high; **these are independent axes** |

## Lower-priority unknowns

| Question | Note |
|---|---|
| Does `windows-capture`'s `draw_border` flag suppress the Windows capture indicator, and can it target the TFT window without the `GraphicsCapturePicker` consent UI? | The programmatic per-window path exists (OBS uses it); the Python binding's exposure was not verified |
| Gemini Flash vision accuracy on small anti-aliased HUD text over a busy background | Every benchmark found tests documents, receipts or handwriting. Nearest datapoint: PaddleOCR >90% on TFT card names, judged insufficient by its own author |
| Champion portrait variance from skins, chibi tacticians and star-level borders | Decides whether masked template matching or dHash is viable for unit art at all |
| Does VNG Games layer Vietnam-specific account monitoring on the ĐTCL PC client? | Governing ToS is settled (Riot Games Services PTE. LTD., Singapore law); local enforcement posture is not |
| macOS support dropped in 18.1 | Irrelevant to this Windows-only project, but confirms Riot is willing to break platforms at a set boundary |

## Related

- [Research overview](overview.md) · [Ban risk & Riot policy](vanguard-risk.md)
- [Set 18 status & data sources](set-data.md)
- [Vision stack](vision-stack/overview.md) · [OCR & matching](vision-stack/ocr.md) · [Augment pipeline](vision-stack/augments.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
