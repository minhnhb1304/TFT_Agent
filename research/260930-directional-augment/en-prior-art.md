# Directional Augment Evaluation — Prior Art & Data Availability (EN sources)

Scope: existing tools/datasets/repos only. No gameplay theory, no ML literature, no explainability. 4 search-fetch iterations (min 2 / max 4 allowed).

Methodology note: `gh` CLI is **not installed** in this environment (confirmed failure in both Bash and PowerShell — `gh: command not found` / not recognized). GitHub research below was done via WebSearch (`site:github.com` + targeted terms) and direct `github.com`/`api.github.com` WebFetch instead of `gh search`. Flagging this as a deviation from the standard protocol — a caller with working `gh` may find more.

---

## Q1: Do existing tools condition augment recommendations on comp/archetype (vs. flat tier list)?

| Site | Verified mechanism | Evidence |
|---|---|---|
| **MetaTFT** (metatft.com) | Comp guide pages list "BIS" (best-in-slot) augments **per specific comp** (e.g. Aphelios Flex: Sword Overflow, Swordsmith, Carve a Path, Bronze 4 Life; Juggernaut Flex: Baron's Lair, Plot Armor, Hold The Line), each with a stated priority order like "Item > Trait > Econ > Combat." This reads as a **curated priority heuristic per comp archetype**, not a raw stat table — the "priority" framing (Item > Trait > Econ) is an authored rule, not an obviously computed ranking. **Could not confirm computed-vs-curated directly**: metatft.com/comps and metatft.com/comps/aphelios-flex are JS-rendered SPAs — WebFetch returned only the page `<title>`, no body content, on repeated attempts. [metatft.com/comps](https://www.metatft.com/comps), [metatft.com/augments](https://www.metatft.com/augments) — both effectively opaque to WebFetch. |
| **tactics.tools** (tactics.tools/augments) | Global augment stats only (Games/Place/Top4/Win columns) — **no per-comp filter visible** in page structure. Confirms the project's already-established finding: the augment data table itself is **empty** for the current patch. [tactics.tools/augments](https://tactics.tools/augments) |
| **TFT Academy** (tftacademy.com/tierlist/comps) | **Confirmed NOT conditioned.** Comps and Augments are separate top-level tier lists (`/tierlist/comps` vs `/tierlist/augments`), no per-comp augment section found. Explicitly **human-authored**: page text reads "Our experts have decided that no comp meets the criteria of being ranked S Tier this patch" — editorial judgment, not computed. [tftacademy.com/tierlist/comps](https://tftacademy.com/tierlist/comps) |
| **Mobalytics** (mobalytics.gg/tft/tier-list/augments) | **Could not verify** — WebFetch returned HTTP 403. |
| **Blitz.gg** | WebSearch snippet only (no direct fetch succeeded — see below): in-game overlay shows augment tier/placement/winrate "for different comps" as part of comp guide pages, and a per-team-guide "recommended augments" list. Sounds structurally similar to MetaTFT's per-comp curated list, **not confirmed as computed conditional statistics**. Blitz's own "How Blitz.GG uses Machine Learning to analyze TFT Compositions" Medium article (which could explain methodology) returned HTTP 403 / socket closed on both fetch attempts — **inaccessible**. [blitz.gg/tft/comps](https://blitz.gg/tft/comps), article (blocked): [medium.com/blitz-press/...](https://medium.com/blitz-press/how-blitz-gg-uses-machine-learning-to-analyze-tft-compositions-eefc8527ba6d) |
| **LoLChess.gg** | WebSearch snippet only: "detailed information about augments and the strongest team compositions" — too vague to confirm conditioning mechanism. Not fetched directly. |
| **tactics.tools, OP.GG, Tacter** | OP.GG and Tacter **not directly checked** — ran out of iteration budget (4 iterations used across all 4 questions per scope). Gap, not a negative finding. |

**Answer: Partial yes, but likely human-curated, not computed-conditional.** The clearest pattern across MetaTFT/Blitz/TFT Academy is a **human-authored "BIS augments for this comp" list** attached to each comp guide page — i.e., editors/data analysts hand-pick augment priorities per archetype. None of the fetchable sources show a *computed* conditional statistic (e.g., "Augment X has Y placement specifically within Fast-9 comps, n=1200 games") on a commercial site. The one place that concept appears is an open-source hobby repo (HexCall, see Q3/Q4) — not a commercial/mainstream tool.

---

## Q2: Does public augment × comp conditional data exist?

| Source | Finding |
|---|---|
| **tactics.tools** | Augment stats table **empty** at current patch — corroborates the project's established finding (Set 18, Riot `tft-match-v1` augments field gone). [tactics.tools/augments](https://tactics.tools/augments) |
| **MetaTFT API** (third-party-documented wrapper) | Explicitly documented as **NOT exposing augment data at all**: "The API covers comp-level builds, traits, unit items, and placement trends. Augment-specific stats are not included in any current endpoint." Comp-level (`get_comps`, `get_comp_details`, `get_unit_items`) works; augments are absent entirely, not just unconditioned. [parse.bot MetaTFT API listing](https://parse.bot/marketplace/5194af2c-7ceb-40ce-8b3f-b6f70748fa6e/metatft-com-api) |
| **tft-augment-stats.vercel.app** | Global-only augment placement/winrate (Master+, NA/EUW/VN, refreshed every 30 min per site copy) — but data is **stale**: page content corresponds to **Patch 16.4**, no Set 18 mention, no per-comp breakdown. Likely an abandoned/pre-Set-18 snapshot. [tft-augment-stats.vercel.app](https://tft-augment-stats.vercel.app/) |
| **teamfight.lol Data Explorer** | Has separate filter categories for Champions/Items/Traits/Comps and a separate Augments database — **could not confirm** whether the Explorer BETA supports a joint augment×comp query (fetch returned only nav labels, not functional detail). Flagged as unresolved — worth a follow-up direct visit/interaction rather than WebFetch. [teamfight.lol/stats/explorer](https://teamfight.lol/stats/explorer) |

**Answer: No verified remaining public source of conditioned (augment × comp) statistics.** Even *unconditioned* global augment stats are shaky right now — MetaTFT's API explicitly excludes augments, tactics.tools' table is empty, and the one site with global numbers (tft-augment-stats.vercel.app) is on stale pre-Set-18 data. This strengthens the project's premise: the underlying data for an archetype-conditioned score **cannot currently be sourced from any public site or API** for Set 18. The one exception (HexCall, below) claims to compute this from raw match data, but its data pipeline's actual freshness/legitimacy for Set 18 is unverified and directly contradicts the already-established fact that Riot's API dropped the augments field — see flag in Q3.

---

## Q3: Open-source prior art (augment recommenders/advisors)

All 5 repos found are **very recent** (created Aug–Sept 2026) and **have 0–3 stars** — this is an active but immature niche; multiple hobbyists are independently building near-identical TFT advisory tools right now, none with traction or established credibility.

| Repo | Scoring model | Archetype-conditioned? | Stars / last push / lang |
|---|---|---|---|
| **[buinguyenbaokhanh/hexcall](https://github.com/buinguyenbaokhanh/hexcall)** | Bidirectional augment↔comp lookup. Claims real match data via empirical Bayes shrinkage: `projected_placement = comp.avg_placement + Σ shrink(lift(augment, comp), n)`, sample-size weighted. Pre-game only (manual augment entry, does not read live game state). | **Yes** — explicitly augment×comp conditional, this is the whole premise. **⚠ Contradiction flag**: claims to derive this from "real match data," but the project's established context says Riot's `tft-match-v1` dropped the `augments` field for Set 18. Could not verify actual data source/currency — repo has no visible docs on where match data comes from (own scraper? cached pre-removal data? unclear). Treat this repo's data legitimacy as **unverified, likely stale or aspirational**. | 0 stars / pushed 2026-09-29 / JS |
| **[Craggles2304/climb-ai](https://github.com/Craggles2304/climb-ai) (PR #12, "Augment Decision Lab")** | Scores 3 offered augments against stage/HP/gold/level/board-strength/carry-direction/traits/items across 6 axes: immediate power, scaling, flexibility, economy/tempo, synergy, commitment risk. Explicitly board-state conditioned (imports saved "Board Lab" state to derive board strength/carry/traits/items). Confidence-weighted — "missing board/item evidence lowers model confidence instead of being fabricated." **Explicitly practice/post-game-review only, not live adaptive shotcalling.** | **Yes, closely** — this is conceptually the closest hit to the project's proposed design (per-axis bonuses conditioned on board state, e.g. econ axis). Worth flagging to the design-doc author as directly comparable prior art, even though scope differs (practice mode vs. live advisory) and it's a 0-star, 3-week-old repo. | 0 stars / pushed 2026-09-29 / TS |
| **[Mattbusel/tft-synapse](https://github.com/Mattbusel/tft-synapse)** | Rust overlay reading Riot **Live Client API** (not match-v1). Rule-based heuristics + human-readable YAML meta files, plus "ranks augments with a bandit model that learns from your placements" — i.e. personalized/adaptive via bandit feedback, not comp-archetype conditioning from population stats. Also has board/economy/item/opponent advisors. Active releases (v0.6.0, cross-platform builds). | Partial/different axis — conditions on *your own outcome history* (bandit), not on comp archetype directly. Not the same mechanism as the proposed feature. | stars not captured (WebSearch only, no repo API fetch) / active per release v0.6.0 / Rust |
| **[arslanberke/tft-helper](https://github.com/arslanberke/tft-helper)** | Two fused "System-1" probabilistic engines (Laya, Jev) combined via `EnsembleEngine` (weighted mean of per-option distributions + agreement signal). Takes typed questions (`Choice`/`Score`/`Noul`) against a `state` object → board-state conditioned. Augment data source **undocumented** in README. Direction: **Comp→Augment only** (no inverse). | Yes (board-state conditioned), but data source opacity makes it unclear if it's grounded in real stats or heuristic scoring. | 0 stars / pushed 2026-09-24 / Python+JS |
| **[Uranium2/tft_augments_helper](https://github.com/Uranium2/tft_augments_helper)** | Pure **flat stats lookup**: daily-scraped pick/win rate/avg placement by rank tier, shown via OCR overlay during gameplay. No board-state or comp conditioning at all. | No — explicitly flat, by design. | 3 stars / Python |

**Answer: The archetype-conditioning idea is not novel in concept** — at least two very fresh hobby repos (HexCall, climb-ai) are independently building close variants of it right now. But **none are mature, validated, or widely adopted** (all 0-3 stars, all <1 month old as of 2026-09-30). No repo has a credibly-sourced, verified augment×comp dataset for the current set — HexCall's data claim is unverified/possibly contradicted by the known Riot API gap.

---

## Q4: Does any tool expose augment → comps-it-opens (inverse direction)?

**Yes — one hit, open-source only, not commercial.**

- **HexCall** ([buinguyenbaokhanh/hexcall](https://github.com/buinguyenbaokhanh/hexcall)) explicitly does this: "Augment→Comp: Enter your augments, receive ranked comps with projected placements" alongside the reverse "Comp→Augment: Browse meta comps and see which augments strengthen them." This is **exactly** the "directional potential" inverse-mapping idea in the design doc. Caveat: 0 stars, 6-week-old repo, data-source legitimacy unverified (see Q3 flag), and it does not read live game state (manual augment entry, pre-game planning tool only — not a live-advisory use case like this project's).
- **tftrecommender.com** "Max Synergies" mode (Simulated Annealing) is adjacent but different: it optimizes a comp given owned emblems/a Trainer Golem, not a general augment→comps mapping. Not a true hit for this question.
- No commercial site (MetaTFT, tactics.tools, TFT Academy, Blitz.gg, LoLChess.gg) was found or confirmed to expose this inverse direction — all found mechanisms go comp→augment (or are flat/global), never augment→comp.

**Answer: Not present in any commercial tool found. One very immature open-source repo (HexCall) does exactly this, but its credibility and data currency are unverified/questionable.**

---

## What could not be verified (explicit)

- **MetaTFT** comp pages (`/comps`, `/comps/aphelios-flex`, `/augments`) — JS-rendered SPA, WebFetch only returns `<title>`, no body. Computed-vs-curated mechanism for "BIS augments per comp" **unconfirmed**.
- **Mobalytics** augment tier list — HTTP 403, blocked.
- **Blitz.gg** ML methodology Medium article — HTTP 403 / socket closed, blocked on 2 attempts.
- **teamfight.lol** Data Explorer — filter/query capabilities for joint augment×comp queries not confirmed from static fetch; would need interactive/JS-rendered check.
- **OP.GG, Tacter, LoLChess.gg (deep)** — not directly fetched; only surfaced in WebSearch snippets. Gap due to iteration budget, not a negative finding.
- **gh CLI unavailable** in this environment (both Bash/POSIX and PowerShell) — GitHub research done via WebSearch + direct repo/API WebFetch instead of `gh search`. A wider `gh search code`/`gh search repos` sweep might surface more repos than the 5 found here.
- **HexCall's actual data pipeline** — repo claims empirical Bayes shrinkage over "real match data" for augment×comp lift, but given Riot dropped the `augments` field from `tft-match-v1` for Set 18 (per this project's already-established finding), it's unclear whether HexCall's numbers are current, stale/pre-removal, synthetic, or aspirational (code not read directly, only README-level summary via WebFetch).

---

## Bottom line for the design doc

1. **Feasibility of the proposed feature's premise is weak on public data**: no verified public source currently publishes augment×comp conditional stats for Set 18, and even flat/global augment stats are degraded (tactics.tools empty, MetaTFT API excludes augments entirely, one stale vercel snapshot). If the archetype-conditioning bonus is meant to be *data-derived*, there is currently no dataset to derive it from — it would have to be heuristic/rule-based (as the design doc's "bonus for X when board can Y" framing already suggests) rather than statistically fit.
2. **Conceptual novelty is limited but execution novelty is open**: two 0-star, <1-month-old hobby repos (climb-ai's Augment Decision Lab, HexCall) are attempting close variants of board/archetype-conditioned augment scoring right now. Commercial tools (MetaTFT, TFT Academy, Blitz.gg) show per-comp "BIS augment" lists that read as human-curated, not computed-conditional. Nobody has shipped a credible, data-grounded, live, archetype-conditioned augment advisor.
3. **The inverse "augment → comps it opens" idea** exists in exactly one place found (HexCall), unverified/immature.

---

## Sources

- [MetaTFT comps](https://www.metatft.com/comps)
- [MetaTFT augments](https://www.metatft.com/augments)
- [MetaTFT pro comps](https://www.metatft.com/pro-comps)
- [tactics.tools/augments](https://tactics.tools/augments)
- [tftacademy.com/tierlist/comps](https://tftacademy.com/tierlist/comps)
- [mobalytics.gg/tft/tier-list/augments](https://mobalytics.gg/tft/tier-list/augments) (blocked, 403)
- [blitz.gg/tft/comps](https://blitz.gg/tft/comps)
- [Blitz ML Medium article](https://medium.com/blitz-press/how-blitz-gg-uses-machine-learning-to-analyze-tft-compositions-eefc8527ba6d) (blocked)
- [tft-augment-stats.vercel.app](https://tft-augment-stats.vercel.app/)
- [MetaTFT API (parse.bot listing)](https://parse.bot/marketplace/5194af2c-7ceb-40ce-8b3f-b6f70748fa6e/metatft-com-api)
- [teamfight.lol/stats/explorer](https://teamfight.lol/stats/explorer)
- [github.com/buinguyenbaokhanh/hexcall](https://github.com/buinguyenbaokhanh/hexcall)
- [github.com/Craggles2304/climb-ai PR #12](https://github.com/Craggles2304/climb-ai/pull/12)
- [github.com/Mattbusel/tft-synapse](https://github.com/Mattbusel/tft-synapse)
- [github.com/arslanberke/tft-helper](https://github.com/arslanberke/tft-helper)
- [github.com/Uranium2/tft_augments_helper](https://github.com/Uranium2/tft_augments_helper)
- [tftrecommender.com/en/guide](https://www.tftrecommender.com/en/guide)

## Unresolved questions

1. Is MetaTFT/Blitz's per-comp "BIS augment" list computed from stats or hand-curated by editors? (JS-SPA blocked direct verification)
2. Does teamfight.lol's Data Explorer BETA actually support a joint augment×comp query?
3. Is HexCall's claimed "real match data" for augment×comp lift genuine/current, or stale/synthetic given the known Set 18 API gap?
4. What do OP.GG and Tacter show for augments — not checked (iteration budget).
