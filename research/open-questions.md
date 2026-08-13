# Open Questions

What four adversarial cross-checks could **not** resolve. Ordered by decision impact.

## Blocking — resolve before writing code

| Question | Why it is unresolved | Who can resolve it |
|---|---|---|
| Does Riot's TFT policy bind a **purely private, never-distributed, single-user** tool? | The registration clause is scoped to products that *"serve players"*, and developer enforcement runs through API-key revocation — which does not exist for an unregistered tool. No source in any of four languages addresses Riot's posture | Riot DevRel ticket. **This is the single most decision-relevant unknown** |
| Would Riot approve a registered product of this shape? | The policy text reads as a clear no for state-conditioned advice, but registration outcomes are case-by-case and there is no public register of TFT overlay approvals or denials to sample | Riot Developer Portal application |
| How does Overwolf obtain real-time TFT `board` / `bench` / `store` / `augments` when Riot's Live Client Data API carries none of it? | Injection, a private arrangement, or an undocumented endpoint — all three are consistent with the evidence | Unanswerable from public docs |
| Does the Riot/Overwolf **augment contradiction** resolve in favour of Riot's text? | Riot permits augment metadata; Overwolf says it *"can't be displayed… by any means"*; Blitz and tactics.tools ship it publicly today. All three cannot be right | Riot DevRel |

## The user must verify these personally

| Test | Cost | What it settles |
|---|---|---|
| Capture one frame of TFT and assert it is not uniformly black | 10 min | Whether Riot has shipped `SetWindowDisplayAffinity` on the client. No researcher ran this. Treat capture as a **runtime precondition**, not an architectural invariant — build the self-check into startup and fail loudly |
| Run TFT in **fullscreen-exclusive** and retry DXGI desktop duplication | 10 min | A hard dependency. Untested by every researcher |
| `GET https://127.0.0.1:2999/liveclientdata/allgamedata` during an actual **TFT** match | 5 min | Whether `activePlayer.level` and `championStats.currentHealth` are served for TFT. Riot documents this for League only; the sole evidence is one 2024 bot's code. Do **not** remove level/HP from the vision pipeline until this passes |
| Capture the **PBE** client and diff its HUD against Set 17 | 1 hr | Whether any Set 17 pixel geometry survives the Unreal swap. PBE is already the Unreal build — this is the only place the post-migration HUD exists before 2026-08-26, and nobody has done it |
| Open `support.riotgames.com` policy pages in a **real browser** | 5 min | See below |
| Run RapidOCR PP-OCRv6 on a real 1080p TFT frame **with the game running** | 30 min | Every latency figure in the corpus is vendor-published, measured on Apple Silicon, or measured on an idle Xeon. None measures the contended case |

## Primary sources no agent could fetch

| Source | Failure | Consequence |
|---|---|---|
| `support.riotgames.com/hc/en-us/articles/225266848` (Third-Party Applications) | JS-rendered SPA returning a ~10 KB "Poro loading" shell to every fetcher, via 4 independent attempts. `web.archive.org` unreachable | The widely-quoted four "measurable player advantage" categories — including *"drawing conclusions for you"* — are **not primary-source confirmed** and are **not** on `developer.riotgames.com/policies/general` where one researcher placed them. **Drop this quote from any risk memo.** It does not change the verdict, because the TFT developer policy prohibits the same behaviour verifiably |
| Riot DevRel Vanguard FAQ (article 28021427366163) | HTTP 403 on both URL forms | *"There is absolutely no allow list"* remains second-hand — and is in tension with Overwolf's undocumented TFT data capability. **Do not reason "MetaTFT does it through channels I could also use."** |
| `legal.kr.riotgames.com` | JS SPA; archive.org blocked | The Korean identity-linked permanent-ban model is unverified — and moot, since Vietnam is governed by Riot Games Services PTE. LTD. under Singapore law |
| [dev-relations #1071](https://github.com/RiotGames/developer-relations/issues/1071) comment thread | Could not render | Issue metadata confirmed: opened 2025-05-06, author account deleted, closed *"unsuitable"*. **No public safe-harbour statement for transparent topmost overlays exists.** A private ticket is the only channel that can produce one, and nobody has confirmed anyone ever got an answer |

## Cross-language tensions left genuinely unsettled

| Topic | The tension |
|---|---|
| Overwolf GEP after 2026-10-09 | GEP keys off LoL game ID **21570** and detects TFT queues via the LoL launcher's `lobby_info`. Both anchors disappear when TFT leaves the League client. Overwolf's TFT docs mention neither Set 18, Unreal, nor the standalone client. **The sanctioned route may break on the same date as the scraping route** |
| Is Overwolf's TFT GEP formally Riot-authorised or merely tolerated? | Two of three reports asserted "Riot-authorized"; no Riot-owned page names Overwolf. Treat as **unproven** |
| Does CommunityDragon's TFT feed have a hard expiry? | Suggestive already: Set 18 gameplay data is largely absent from the League-extracted `map22` (109 refs vs Set 17's 10,169) and the `rcp-be-lol-game-data` plugin path carries zero Set 18 champions on live. If TFT data migrates into Unreal-client files a League extractor cannot parse, the project's primary data source dies |
| Does the Oct 9 client change process name / window class / title? | No Riot statement; the client is not yet on PBE. Directly determines whether dxcam/DXGI window targeting survives |
| Vietnamese client coverage at 18.1 | Trait strings are present and correct on PBE — a good sign — but champion display names and augment text were not exhaustively verified, and the `vi_vn`/`vn_vn` decoy suggests locale handling deserves direct testing |
| Would Riot treat OCR acquisition as "unregistered" or as **anti-cheat evasion**? | Riot's policies are uniformly behaviour-based and completely silent on OCR as an acquisition method for *advisory* tools, as opposed to for pixelbots |
| Has Riot **ever** banned a player for a read-only screen-capture overlay in any title? | Four independent language searches: zero confirmed cases, and zero Riot statements affirming such tools are safe. Convergent — but still absence of evidence. Empirical ban risk is low; policy risk is high; **these are independent axes** |

## Lower-priority unknowns

| Question | Note |
|---|---|
| Does `windows-capture`'s `draw_border` flag actually suppress the Windows capture indicator, and can it target the TFT window without the `GraphicsCapturePicker` consent UI? | Microsoft's docs describe both as standard; the programmatic per-window path exists (OBS uses it) but the Python binding's exposure was not verified |
| Gemini Flash vision accuracy on small anti-aliased HUD text over a busy background, **in any language** | Every benchmark found across four languages tests documents, receipts or handwriting. Nearest datapoint: PaddleOCR at >90% on TFT card names, which its own author judged insufficient without a second recogniser fused in |
| Champion portrait variance from skins, chibi tacticians and star-level borders | Unresolved everywhere. Decides whether masked template matching or dHash is viable for unit art at all |
| Does VNG Games layer Vietnam-specific account monitoring on the ĐTCL PC client? | Garena-era VED demonstrably did. Governing ToS is settled; local operational enforcement posture is not |
| ToS text (as distinct from `robots.txt`) for lolchess.gg, tactics.tools, TFTacademy | Matters much less if the OP.GG MCP path is adopted |
| OP.GG MCP rate limits, API-key requirement, commercial-use grant | The README states none of it, and GitHub's API returned 403, so repo activity is unverified |

## Related

- [Research overview](overview.md)
- [Ban risk & Riot policy](vanguard-risk.md)
- [Set 18 status & data sources](set-data.md)
- [Vision stack](vision-stack/overview.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
