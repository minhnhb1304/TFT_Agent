# EN: High-Elo TFT Augment-Selection Theory — Claim Verification

Scope: domain-truth check only, per doc claims. English sources only. 4 search-fetch iterations.

---

## Claim 1

> "At 2-1 and 3-2 the board is placeholder; strong players pick the augment first and let it decide the comp, rather than picking the augment that fits the current board."

**Verdict: PARTLY (leans REFUTED on the specific mechanism claimed)**

- Consensus framework is **board/context-first**, not augment-first. MadeByKeo's 2-1 evaluation checklist: "Upgraded unit — Do you have a 2-star unit? Item slam — Do you have an item that works on that unit? Augment synergy — Will the augment benefit that unit?" — board state gates augment value, not the reverse. [TFT Flex Play Guide, MadeByKeo, tftsense.gg, Set 18 patch 18.3](https://tftsense.gg/study-hall/tft-flexible-play/)
- Same author's general augment guide: 2-1 priority = "Strong board → Item augment (default). Weak board → Econ augment (safe choice). Unclear → Direction augment." Board state is the input; augment choice is the output. [TFT Augment Guide, tftsense.gg, Set 18 patch 18.3](https://tftsense.gg/study-hall/tft-augments-guide/)
- The actual dominant 2-1 principle found is **"stay flexible," not "let augment decide comp"**: "First augments should usually keep your options open, unless a comp-specific augment is so powerful that it justifies committing to a direction before you have any information." [Evaluating Augments, tft.ninja](https://tft.ninja/guides/augments/evaluating)
- Design-intent evidence points the same way: Mortdog (game director) says Riot deliberately reduced "direction-locking augments at 2-1 (like old crown/crest spam)" so players don't get hard-forced into a comp by an augment roll. This is from Set 16, an older set, but signals a standing design philosophy against augment-forces-comp at 2-1. [Mortdog Set 16 Deep-Dive, spoonfedbytes.com](https://www.spoonfedbytes.com/mortdogs-set-16-deep-dive-design-goals-carries-meta-philosophy-in-lore-legends/)
- Counter-signal (weaker source, older set — Set 14 "Enchanted Wilds", not a named pro): "elite players take the augment that locks their comp direction and refuse the ones that pull them off line," justified by contested-ness ("a clean force into a strong vertical trait hits far above its rate" early in a fresh set). Note this same article also says "the winner keeps the most lines open through stage two" — internally in tension, read as: stay generally flexible, but force a *specific trait* if you have a confident contest-read. [TFT Enchanted Wilds Best Comps, ggclan.com, Set 14](https://ggclan.com/news/tft-enchanted-wilds-best-comps-ladder-guide)
- 2-1 → 3-2/4-2 shift is real and matches the doc's spirit, just phrased as flexibility→commitment rather than augment-leads-comp: "At 4-2, your augment should usually solve the biggest issue stopping your final board... You can always commit harder at your second and third augments once the board tells you what it wants to be." [Evaluating Augments, tft.ninja](https://tft.ninja/guides/augments/evaluating); progression also stated by MadeByKeo: 2-1 = "educated guess," 3-2/4-2 = "much clearer picture" of comp/contest/items/gold/HP. [TFT Augment Guide, tftsense.gg](https://tftsense.gg/study-hall/tft-augments-guide/)

**Net read for the project:** the doc's underlying instinct (2-1 augment carries directional/optionality value beyond board-fit) is directionally right, but "augment leads comp, board is placeholder" overstates it. Real framework: board context still gates augment choice at 2-1, but the choice itself should be evaluated by how many future comps it keeps open, not by best current-board stat fit. Recommend the project phrase this as "keep-options-open vs current-fit," not "augment-first vs board-first."

---

## Claim 2

> "Economy augments split into reroll-economy (forces stop-and-roll-down at 5/6/7 for 3★ 1-3 cost) vs XP-economy (forces fast 8/9 for 2★ 4-5 cost), directionally opposed. Is flat-gold economy a third, neutral family?"

**Verdict: CONFIRMED**

- Reroll-economy augments mechanically exclude XP spending and reward reroll spam: "Wise Spending: You can no longer buy XP. Every time you spend gold to reroll your Shop, gain 2 XP." Same family: "Patience is a Virtue: gain 4 rerolls now, +1 free reroll each round if you did not buy a champion previous round." Both push toward staying low-level and rolling down for 3★ cheap units. [Augments Set 18 TFT Info, tactics.tools](https://tactics.tools/info/augments) / cross-checked [TFT Augments Guide, bamboogaming.net](https://www.bamboogaming.net/tft/augments)
- XP-economy augments do the opposite — cheap/free levels to reach 8/9 fast: "Epoch: gain 4 XP and 2 free rerolls now and at the start of every stage." "Upward Mobility: reduces XP purchase cost by 1, grants 2 HP and 1 free reroll on level-up." [same sources as above]
- Direct statement of the opposition: "If you are doing a certain strategy such as reroll, you should take a reroll augment, while XP augments push you toward a leveling-focused strategy. This creates a clear strategic fork." [search-aggregated from mobafire.com/bamboogaming.net/tftforge.gg TFT augments guides — cross-source consensus, no single canonical URL beyond the pages above]
- **Flat-gold IS a distinct, direction-neutral third family**, matching a "standard leveling" archetype sitting between reroll (intentionally under-level) and fast-level (intentionally over-level): "Standard Leveling: Flexible strategy focused around a healthy economy while still keeping up in levels" vs. "Reroll comps want to be under-leveled to hit 3-star units" vs. "Fast 8/9 strategies save up lots of gold to level up faster." [When and How to Level in TFT (Three Fundamental Strategies), mobalytics.gg](https://mobalytics.gg/tft/guides/leveling-guide) — note: direct fetch of this URL 403'd; content taken from search-result snippet, treat as lower-confidence citation, corroborate before quoting verbatim in the final report.
- Economy augments generally are time-sensitive regardless of family: "The same gold augment is fantastic at Stage 2 and nearly dead at Stage 4, because interest compounds over time." [aggregated from bamboogaming.net/tftsense.gg economy commentary]

**Net read:** doc's claim 2 is accurate. Reroll vs XP economy are mechanically and strategically opposed (can't do both — reroll augments literally block XP purchases in some cases). Flat-gold/standard leveling is the documented third, neutral/flexible family. Good to cite as-is.

---

## Claim 3

> Is there established English terminology: "anchor augment", "comp-defining augment", "forcing augment", "flex augment", "augment flexibility", "high-commitment augment", "openness"?

**Verdict: PARTLY — real vocabulary exists but not the exact list assumed**

Confirmed as actual community/coaching terminology:
- **"Direction augment"** — one of a canonical 4-type taxonomy (econ / item / combat / direction) used by tftsense.gg (MadeByKeo). [TFT Augment Guide, tftsense.gg, Set 18](https://tftsense.gg/study-hall/tft-augments-guide/)
- **"Comp-defining augment"** — attested: "If your board has no clear direction, trait, emblem, or comp-defining augments become more valuable." (aggregated search snippet, multiple guide sites; recommend re-verifying exact source page before quoting in final synthesis)
- **"Flex vs Forced"** — a named, dedicated dichotomy with its own guide page. Forcing = "decide on a specific team composition before or very early in the game... commit to building it regardless of what happens." Flexing = "stay open and adapt your comp based on what the game gives you," with pivots possible "through Stage 3 or even Stage 4." [Flex vs Forced, tft.ninja](https://tft.ninja/guides/team-comps/flex-vs-forced)
- **"Flexible play"** as a named strategy category — tftsense.gg has a dedicated "TFT Flex Play Guide." [tftsense.gg](https://tftsense.gg/study-hall/tft-flexible-play/)
- **"Keep your options open" / "options open"** — the standard phrase for the 2-1 optionality principle (see Claim 1/4 evidence), used verbatim by tft.ninja.
- **"Comp-specific" vs "generic" augment** — used by tft.ninja as the operative binary instead of "high-commitment": "unless a comp-specific augment is so powerful that it justifies committing... lean toward generic, flexible, or economy augments."
- **"Committing" / "commitment"** as a verb/noun is used generically, not as a fixed compound term "high-commitment augment."

NOT found in any source across this search: **"anchor augment"**, **"optionality"** (as exact term), **"high-commitment augment"** (as exact compound). These appear to be the project doc's own coinages, not attested community vocabulary.

**Recommendation for the project report:** use "direction augment" / "comp-defining augment" / "flex vs forced" / "keep options open" / "comp-specific vs generic augment" — these are the real terms found in current (Set 18) coaching content. Avoid "anchor augment" and "optionality" as if they were established jargon; if used, flag them explicitly as project-internal terminology, not community-standard.

---

## Claim 4

> "The value of an early augment is how many viable meta comps it opens, not how much stat it adds to the current board." Does high-elo theory support this optionality notion at 2-1? Counter-argument?

**Verdict: CONFIRMED, with a documented (weaker-sourced) counter-argument**

- Directly and explicitly confirmed, near-identical phrasing to the doc's claim: "When two options are close, you should take the one that keeps you flexible — a slightly weaker pick that works with three different comps is usually better than a slightly stronger pick that only works if a specific carry shows up." [Evaluating Augments, tft.ninja](https://tft.ninja/guides/augments/evaluating)
- Same source gives the exception threshold (i.e., when raw power should override optionality): "unless a comp-specific augment is so powerful that it justifies committing to a direction before you have any information."
- Vertical emblem augments are valued specifically for opening otherwise-unreachable comps, not raw stats — same optionality logic applied to a specific augment type: "A vertical emblem augment beats raw stats because it opens a comp you could not reach otherwise." [ggclan.com, Set 14 — older set, principle plausibly set-independent since emblems recur every set](https://ggclan.com/news/tft-enchanted-wilds-best-comps-ladder-guide)

**Counter-argument found (contested-ness > optionality):**
- Same ggclan (Set 14, non-named-pro source, lower authority): forcing early is profitable specifically *because* the lobby hasn't read contest yet — "Forcing works best in the opening days [of a patch/set]... when half the lobby has not learned the breakpoints, a clean force into a strong vertical trait hits far above its rate." This argues commitment can beat optionality when you have a confident contest read, i.e., optionality value is conditional on the meta being unsolved/uncontested, and decays as the lobby (or patch) matures.
- Caveat found in the same space: "Do Not Force a Comp in Week One" is cited as a counter-counter-heuristic elsewhere in the search results (aggregated snippet, source unclear) — i.e., forcing-on-contest-read itself has dissenting takes; treat the whole "force early because uncontested" line as a real but second-tier, disputed position, not consensus.

**Net read:** the doc's optionality claim for 2-1 is well supported by an authoritative, current-looking source (tft.ninja) in near-verbatim language. The counter-argument exists (contested-ness/meta-read can justify early forcing) but comes from a lower-authority, older-set source and is itself internally contested — treat as a real nuance to flag, not a refutation.

---

## Set/Patch Currency Notes

| Source | Set/Patch | Relevance to Set 18 target |
|---|---|---|
| tftsense.gg (MadeByKeo) | Set 18, patch 18.3 | Directly current |
| tft.ninja (Evaluating Augments, Flex vs Forced) | Undated in content, pages updated Mar/Jun 2026 | Very likely Set 18-era (dates postdate Set 18 launch 2026-08-26 per project brief... note: page "updated" dates predate that launch date oddly — flag for the project to re-verify page currency manually, may reflect Set 17 with rolling updates) |
| Mortdog Set 16 deep-dive | Set 16 (older) | Design-philosophy claim only (reduce 2-1 direction-locks) — treat as historical precedent, not current mechanic |
| ggclan.com (Enchanted Wilds) | Set 14 (older) | Principle (contest-read forcing, emblem optionality) plausibly set-independent, but not verified against Set 18 augment pool |
| mobalytics.gg leveling guide | Set/patch unspecified, fetch blocked (403) | Snippet-only, re-verify before quoting |

## Unresolved / Flag for lead-researcher

1. Could not confirm tft.ninja's exact set coverage — page has no explicit "Set 18" label despite being the most current-feeling source. Worth a follow-up fetch/search to pin down.
2. mobalytics.gg leveling guide blocked by 403 on WebFetch — evidence for the "flat gold = neutral third family" sub-claim rests on search snippets only, not a verified page read. Recommend re-fetch via another tool/agent before final synthesis treats it as fully confirmed.
3. Did not find a named high-elo pro (Frodan, Dishsoap, k3soju, Robinsongz, Milk, Setsuko) directly on record for any of the 4 claims — all confirming sources are guide-site authors (MadeByKeo/tftsense, tft.ninja, unnamed ggclan author), not competitive players. If the project needs pro-attributed quotes specifically, this is a gap — consider a targeted follow-up search for Frodan/Dishsoap YouTube/Twitch VOD transcripts or tweets on 2-1 augment philosophy.
4. "Anchor augment" and "optionality" as exact terms were not found anywhere — confirmed absent, not just unconfirmed.
