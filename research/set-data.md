# Set 18 Status and Data Sources

**Bottom line:** §8's premise is wrong — Set 18 is **not live until 2026-08-26**. The data layer is
nevertheless workable today on the `/pbe/` branch: a complete 65-champion roster with 100% icon coverage.
Two false blockers reported elsewhere (no Set 18 champion data; 39% icon coverage) are refuted by
measurement. What genuinely cannot be sourced is roll odds, XP costs and pool sizes.

## Set 18 is not live — five independent proofs

| # | Proof | Source |
|---|---|---|
| 1 | Patch 17.9 notes (2026-08-11): *"Our newest set, Enchanted Wilds, will go live at the end of patch 17.9, on August 26th"* | [patch notes](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-17-9/) |
| 2 | Unreal FAQ: *"Starting August 26th with the release of Enchanted Wilds…"* | [FAQ](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/faq-tft-unreal-migration/) |
| 3 | Live `tftsets.json`: `LCTFTModeData.mDefaultSet.SetName = TFTSet17` / `"Space Gods"`. **Re-verified 2026-08-13.** | [live](https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/tftsets.json) |
| 4 | Live `tftchampions-teamplanner.json` has only `TFTSet16` (100) and `TFTSet17` (64) — no Set 18 key | [live](https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions-teamplanner.json) |
| 5 | Set 18 assets 404 on live, 200 on PBE; PBE `mDefaultSet.SetName = TFTSet18` / `"Enchanted Wilds"`, and PBE lists **8** active sets vs live's 7. **Re-verified 2026-08-13.** | [pbe](https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftsets.json) |

The "Set 18 went live 2026-08-12" claim traces to CommunityDragon file mtimes from a routine rebuild for
patch 17.9, plus a **pre-seeded Set 18 stub** (36 traits, 19 non-playable entries) in the aggregate file.

## The augment system is renamed in Set 18

`mDefaultSet.SetAugmentName` reads **`"Boombox Augment"`** on PBE, against `"Hexcore Augments"` on live
Set 17. Any code, prompt or lookup keyed on the string "Hexcore" breaks at 18.1. This directly affects the
spec's highest-priority feature — see [ban risk](vanguard-risk.md) for the separate policy constraint on
that feature.

## Two breakage events, six weeks apart

| Date | Event | Impact |
|---|---|---|
| 2026-08-26 | Hextech → **Unreal** engine swap, patch 18.1 | Every ROI coordinate, icon template and star-border heuristic is disposable. Minimap **deprecated**. *"Preferred Settings will be reset as we migrate from one engine to the other."* Min spec: Win10 19041+, DX11 FL4.3, SM5 |
| 2026-10-09 | **Standalone TFT PC client** — *"our PC client will remain in Hextech until a dedicated client comes out… four patches later on October 9th"* | Likely changes process name, executable and window class/title → breaks dxcam/DXGI window targeting **and** overlay owner-window logic. May also break Overwolf GEP, which keys off LoL game ID 21570 |

Source for both: [Unreal migration FAQ](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/faq-tft-unreal-migration/)

## Data sources — use these exact URLs

| Purpose | URL | Note |
|---|---|---|
| Champion roster (**authoritative**) | `raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions-teamplanner.json` | 65 champions, tiers `{1:14, 2:13, 3:14, 4:14, 5:10}`, traits, `squareIconPath` |
| Active sets / default set | `…/pbe/…/v1/tftsets.json` | Root key is `LCTFTModeData`; read `.mDefaultSet.SetName` |
| Localized text (Vietnamese) | `raw.communitydragon.org/pbe/cdragon/tft/vi_vn.json` | 27.5 MB, Last-Modified 2026-08-12 |
| Trait art | `raw.communitydragon.org/pbe/game/assets/ux/traiticons/trait_icon_18_<en_name>.png` | filename follows the **English** display name |
| Meta decks / augments / items | `https://mcp-api.op.gg/mcp` (MIT) | `tft_list_meta_decks`, `tft_list_augments`, `tft_get_champion_item_build`, `tft_list_item_combinations` |
| Match history | `tft-match-v1` via [developer.riotgames.com/apis](https://developer.riotgames.com/apis) | Full TFT surface: `spectator-tft-v5`, `tft-league-v1`, `tft-match-v1`, `tft-status-v1`, `tft-summoner-v1`. **`tft-match-v5` does not exist** — §8's `tft-match-v1` is already correct |
| Data Dragon | — | **Demote.** No Set 18 keys; newest version `16.16.1` vs TFT patch 17.x, so TFT patch numbers cannot build DDragon URLs |
| Live TFT board state | — | **Does not exist.** Live Client Data API (`127.0.0.1:2999`) is Summoner's-Rift-only; the TFT request has been open since 2020-09-24 with no Riot reply ([#373](https://github.com/RiotGames/developer-relations/issues/373)) |

## Four traps that fail silently

| Trap | Symptom | Rule |
|---|---|---|
| `vn_vn.json` exists alongside `vi_vn.json` | Both return **HTTP 200**. `vn_vn.json` is frozen at **2023-05-03** — no Set 18 content, no error | Use `vi_vn.json`. Assert on `Last-Modified` at load. Highest-probability silent failure for a Vietnamese-client project |
| Aggregate `cdragon/tft/{lang}.json` `sets['18']` | A pre-seed **stub** — 19 PvE monsters/dummies, not the roster. Produced two false "no data" blockers | Read the roster from `tftchampions-teamplanner.json` |
| Set 18 reuses **Set 10** asset names | Confirmed in the live PBE payload: `SetAugmentContainer = ".../EOG_AugmentProp_Set10.png"`, plus `TFTSet10Revival*` keys. A pipeline bucketing by `name` files Set 18 under Set 10 | Key on `mutator` / `number`, never `name`. Add a regression assert |
| Display strings are internally inconsistent | Set 18's `TranslatedShortDisplayName` is `"@TextIconKey@ Set18"` (no space) where Set 17 uses `"Set 17"` (with space). `character_id` no longer starts `TFT18_` — **65/65** start with `DA` in three shapes (`DA_18_Xayah`, `DA_Krug18`, `DA_Gromp18_AP`), and casing differs *within* one path: dir `TFT18_Murkwolf` vs file `TFT18_MurkWolf_Square` | Never construct URLs or labels by string-building. Read `squareIconPath` verbatim, strip `/lol-game-data/assets`, lowercase |

**Measured, not assumed:** probing the JSON's own `squareIconPath` on PBE for all 65 champions gives
**65/65 HTTP 200**, 5,855–10,356 bytes. The "39% coverage" figure came from a *guessed* `/hud/{n}_square.png`
path on the *live* branch.

## The four-namespace join

`trait_id` → EN display → icon filename → VI display, with **no string rule connecting them**:

| trait_id | EN | icon file | VI |
|---|---|---|---|
| `DA_18_Slayer` | Ravager | `trait_icon_18_ravager.png` | Tàn Phá |
| `DA_18_Battlemage` | Monolith | `trait_icon_18_monolith.png` | Cự Thạch |

Build an explicit four-column table. Both icon URLs verified HTTP 200.

## What cannot be sourced today

| Missing | Evidence |
|---|---|
| Set 18 roll odds, XP costs, pool/bag sizes | Scanned PBE `map22.bin.json` (72.6 MB): `Set17` appears 10,169 times, `Set18` 109. `ShopOdds`/`TierOdds`/`ChampionTierOdds`/`LevelXP` = **0 hits**. The only bag-size constant is `Common_TierBagSizes_For_CharacterWizard` = 29/22/18/11/10, a dev-tool default that contradicts the circulating community table (29/22/16/12/10) |
| Augment / Wisp icon templates | **345** `DA_*` items share one sprite (`set18_mechanicicon.tex`); of 254 `isAugment` entries, 48 (19%) carry `missing-t1/t2/t3.tex` placeholders |
| Meaningful augment win rates at launch | Stats sites will have days-to-weeks of cold start after 2026-08-26 |

**Consequence:** do not ship hardcoded odds. Gate the Economy Advisor behind verified 18.1 numbers or
label it "unverified". Recognition of augments and Wisps is OCR/multimodal-only — which promotes §9.3
Approach A (Gemini Vision) from fallback to primary mechanism for augments.

## Related

- [Research overview](overview.md)
- [Ban risk & Riot policy](vanguard-risk.md)
- [Vision stack](vision-stack/overview.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
- [Open questions](open-questions.md)
