# Ban Risk and Riot Policy

> **Verified:** 2026-08-28. All eight policy quotes below were re-fetched and confirmed verbatim.
> Two were **truncated** in the previous pass and are now completed — the omissions mattered.

> 📌 **Scope note (SPEC v3, 2026-08-29).** The project is an unpublished single-user thesis artifact,
> so the **developer-policy** half below is no longer a build constraint ([SPEC §11](../SPEC.md)) — it
> is retained as the evidence base should the tool ever be distributed. The **ToS / Vanguard** half
> stays fully binding, enforced by `tests/test_readonly_invariant.py`. Independent axes: dropping the
> policy constraint does **not** relax the read-only architecture.

**Bottom line (as research, not as a build constraint — see the scope note above):** Vanguard is the
wrong thing to fear. Were this tool published, the TFT developer policy — not anti-cheat — would be the
binding limit, and it would prohibit a board-state-aware Augment Advisor while permitting a narrower
static version. The loudest "project killer" circulating in the research (augment win rates are banned)
is **refuted** by Riot's own text.

## Actually safe vs assumed safe

| Element | Status | Evidence |
|---|---|---|
| DXGI desktop duplication (read-only) | **Confirmed outside the documented detection surface** | Vanguard's own taxonomy targets tampering, DMA, pixelbots, bootkits, internal + kernel cheats; a pixelbot is defined as *"a computer vision cheat that injects player input"* ([Vanguard On-Demand, 2026-06-24](https://www.riotgames.com/en/news/vanguard-on-demand)) |
| `WS_EX_LAYERED / TRANSPARENT / NOACTIVATE` overlay | **Confirmed** — never appears on any documented blocking list (which covers vulnerable kernel drivers `rtcore64.sys`, `ene.sys`, `inpoutx64.sys`, `WinRing0`, injection hooks, input-layer software) | same |
| §1.3 forbidden list (no RPM, no DLL injection, no D3D hook, no `SendInput`) | **Correctly calibrated — do not weaken** | Kyrluckechuck/TFT-Bot README states Vanguard makes it *"a liability against any accounts it's run by"* — and that bot automates input ([repo](https://github.com/Kyrluckechuck/TFT-Bot)) |
| Client capture protection (`SetWindowDisplayAffinity` on the game) | **Assumed safe only.** Absence of evidence across 4 languages; no researcher ran a capture test | [ZeroLP/External-Mitigations](https://github.com/ZeroLP/External-Mitigations) is a public blueprint for exactly this counter-move |
| "We touch no Riot API so the policy doesn't apply" | **REFUTED** | *"If your product serves players, you must register it with us regardless of whether or not your product uses official documented APIs."* ([docs/tft](https://developer.riotgames.com/docs/tft)) |
| Zero confirmed bans for read-only advisory overlays | **Confirmed, but it is absence of evidence** | Four independent language searches (Riot Support, dev boards, GitHub, Inven, fmkorea, V2EX, voz.vn) returned an empty set. Every located ban involves input automation, modskin, memory hacks or boosting. |

## Riot's TFT policy, verbatim

Source for all quotes: <https://developer.riotgames.com/docs/tft>, re-fetched 2026-08-28.

> **Correction to the previous pass:** it claimed the page was *"still stamped LAST UPDATED March 11,
> 2025."* The TFT policy page carries **no date stamp of its own**. The adjacent general-policies page
> ([/policies/general](https://developer.riotgames.com/policies/general)) reads **LAST UPDATED
> May 29, 2025**. Do not cite a date for the TFT page itself.

| Prohibited | Quote |
|---|---|
| Real-time prescription | *"Issues arise when the recommendations adjust in real time based on the player's actions in game and give direct prescriptions of what to do."* |
| Overlays | *"Apps and overlays during the game may not include any real-time data that would improve a player's performance immediately by altering player behavior, such as 'go here now' versus altering it upon reflection, learning and coaching the player game over game."* ← **the trailing clause was missing before; it is permissive** |
| Skill tests | *"Products cannot bypass a skill test for the player. Skill tests can include the tracking of diverse information over a short period of time."* |
| Unapproved list | *"Scouting - tracking the champions opponents have on their boards. Products that bypass a skill test for the player. Apps that provide dynamic, real-time information. Apps that dictate player decisions."* |
| Opponent prediction | *"Apps and Overlays during gameplay (including the loading screen) may not track your opponent's champions/plays or predict their next plays."* Elaborated: a lobby's most-played champ/synergy/augment may not be shown during gameplay ← **not previously recorded** |
| Legend stats | *"Products cannot display win rates for Legends and Legend-based Augments. This applies to all websites, applications, and overlays."* |

| Permitted | Quote |
|---|---|
| Augment metadata | *"**For example**, an app can provide metadata on augment statistics as this information is available prior to the game and is not based on in-game activity."* |
| Static recommendations | *"Having a static recommendation for a player pre-game is acceptable, even if that same recommendation is available to you the entire game."* |
| Highlighting choices | *"Products should not remove game decisions, but may highlight decisions that are important and give multiple choices to help players make good decisions."* |
| The one approved overlay category | *"Game overlays that provide static data that is available prior to the game."* (Production key + RSO) |

## The compliant corridor

| Do | Don't |
|---|---|
| Detect *which* three augments are on screen via CV | Rank them, or emit a recommended pick |
| Show each one's pre-game static Place / Top-4 / Win | Weight them by current board, gold, HP or comp |
| Present all three as equal options | Recompute anything from live board state |
| Ship Legend data with win rates stripped | Display Legend or Legend-based Augment win rates |
| Keep it private, single-user, unpublished | Distribute (triggers the registration clause) |

**Corridor widener, newly surfaced:** the completed overlay quote contrasts banned *"go here now"*
prescriptions against *"altering it upon reflection, learning and coaching the player game over game."*
Riot is drawing the line at **immediacy**, not at advice. A post-round or post-game review surface is
materially safer than a live in-round one, and the previous pass's truncated quote hid this.

**REFUTED — "augment win rates are banned, the project is dead":** Riot's live policy blesses augment
metadata, and [tactics.tools/augments](https://tactics.tools/augments) currently renders `Place`, `Top 4`
and `Win` columns publicly. The sources behind the "killer" claim are stale: Overwolf's TFT compliance
page still cites *TFT Patch 13.12 notes* (June 2023), and MetaTFT's help page reflects the July 2023 state
Mortdog called "naive" and Riot reverted at Set 9.5.

**Unresolved contradiction:** Overwolf's GEP page says *"DO NOT include augment data support in your apps…
Displaying this data can result in banning"*
([Overwolf](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/teamfight-tactics/)) —
directly against Riot's own text, and present in Overwolf's *newest* (ow-electron) doc tree today. The
reconciliation nobody drew: Overwolf's compliance doc is Riot's contractual requirement **on Overwolf
partners**, not law binding every third-party app.

## Penalty ceiling and jurisdiction

| Question | Answer | Evidence |
|---|---|---|
| Governing contract | Riot ToS §7.1(11), last modified 2024-12-01 — enumerates *"mods, hacks, cheats, scripts, bots, trainers and automation programs"*, programs that *"intercept, emulate, or redirect"*, and programs that *"collect info… by reading areas of memory"*. **Passive framebuffer capture is not enumerated.** The load-bearing undefined word is *"unauthorized"* | [ToS](https://www.riotgames.com/en/terms-of-service) |
| Ceiling | *"temporary bans, account suspension or termination and deletion, hardware bans"* | same |
| Vietnam entity | **Riot Games Services PTE. LTD.**, 51 Bras Basah Rd, Singapore 189554; SIAC arbitration, Singapore law. Vietnam is unenumerated but falls under Southeast Asia | [ToS (vi)](https://www.riotgames.com/vi/terms-of-service) |
| "VNG publisher terms supersede Riot's" | **REFUTED** — that supersession clause sits under *fan-content* provisions, not the §7.1 User Rules | same |
| Korean identity-linked mass-ban model | Does not transfer — a Korean regulatory artifact with no Vietnamese equivalent | same |

## Cross-language tension left honest

**"Did Vanguard kill the TFT OCR ecosystem in April 2024?"** EN asserted at high confidence that
`jfd02/TFT-OCR-BOT` was archived 2024-04-18, "one week after Vanguard shipped". **REFUTED** — the repo page
reads *"archived by the owner on Apr 9, 2026"*; all three researchers conflated the GitHub API's
`pushed_at` with the archive event, and the README never mentions Vanguard, anti-cheat or bans
([repo](https://github.com/jfd02/TFT-OCR-BOT)). ZH and VN handled this correctly and EN did not.

## Related

- [Research overview](overview.md)
- [Set 18 status & data sources](set-data.md)
- [Vision stack](vision-stack/overview.md) · [Augment pipeline](vision-stack/augments.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
- [Open questions](open-questions.md)
