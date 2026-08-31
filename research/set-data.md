# Set 18 Status and Data Sources

> **Verified:** 2026-08-28 against `/latest/`. Supersedes the 2026-08-13 pass, which was written
> while Set 18 was still PBE-only.
>
> **Amended 2026-09-01**: a sixth silent trap (`setData[0]`) surfaced the first time the project
> downloaded the **full** locale rather than a trimmed fixture. Every other measurement below stands.

**Bottom line:** Set 18 **Enchanted Wilds is live** (patch 18.1, launched 2026-08-26). The previous
`blocker` grade is **resolved**. Every measured claim from the PBE pass reproduced exactly on live —
the roster, the icon coverage, and all four silent traps. Two things changed: the `vn_vn` decoy is now
branch-dependent, and this doc's own trait-art URL was string-built and is wrong 2 times in 36.

## Launch confirmed — read these fields, not a calendar

| Field on `/latest/` | Value |
|---|---|
| `mDefaultSet.SetName` | **`TFTSet18`** |
| `mDefaultSet.SetDisplayName` | `Enchanted Wilds` |
| `mDefaultSet.SetAugmentName` | **`Boombox Augment`** (Set 17 was `Hexcore Augments`) |
| `tftchampions-teamplanner.json` | `TFTSet17` (64) + `TFTSet18` (65). `TFTSet16` dropped |

`/pbe/` and `/latest/` are **currently identical** — same `mDefaultSet`, same 64+65 rosters. The
dual-branch strategy has no remaining purpose until the standalone client reaches PBE (reported
~2026-09-09). Keep the branch switch behind config; do not delete it.

> History, for context only: before 2026-08-26 live served `TFTSet17` ("Space Gods") and Set 18
> existed on PBE alone. That is why the `/pbe/` machinery exists. It is no longer a constraint.

**Any code keyed on the string "Hexcore" breaks at 18.1** — `SetAugmentName` is now `Boombox Augment`.
Note the *asset paths* still say `hexcore/` (see [augments](vision-stack/augments.md)); the display
name changed, the directory did not. Do not "fix" one by the other.

## The two breakage events

| Date | Event | Impact |
|---|---|---|
| **2026-08-26** ✅ done | Hextech → **Unreal**, patch 18.1 | Every ROI coordinate, icon template and star-border heuristic from Set 17 is disposable. Minimap deprecated. Min spec: Win10 **19041+**, DX11 FL4.3, SM5. **macOS support dropped** in 18.1. TFT still launches from the existing League/Riot client — no new process yet |
| **2026-10-09** ⏳ pending | **Standalone TFT PC client** | Likely changes process name, executable and window class/title → breaks DXGI window targeting **and** overlay owner-window logic. May break Overwolf GEP, which keys off LoL game ID 21570. PBE reported ~2026-09-09 (secondary sources only) |

Source: [Unreal migration FAQ](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/faq-tft-unreal-migration/),
patch 18.1 notes.

## Data sources — use these exact URLs

| Purpose | URL | Note |
|---|---|---|
| Champion roster (**authoritative**) | `raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions-teamplanner.json` | 65 champions, tiers `{1:14, 2:13, 3:14, 4:14, 5:10}`, traits, `squareIconPath` |
| Active sets / default set | `…/latest/…/v1/tftsets.json` | Root key `LCTFTModeData`; read `.mDefaultSet.SetName` |
| Localized text (Vietnamese) | `raw.communitydragon.org/latest/cdragon/tft/vi_vn.json` | ~24 MB. Assert `Last-Modified` |
| Trait + augment art | Read the `icon` field **verbatim**, swap `.tex`→`.png`, prefix `raw.communitydragon.org/latest/game/` | **36/36 traits HTTP 200.** See the trait-art trap below |
| Champion art | Read `squareIconPath` verbatim, strip `/lol-game-data/assets`, lowercase, prefix `…/latest/plugins/rcp-be-lol-game-data/global/default` | **65/65 HTTP 200**, 5,855–10,356 bytes |
| Meta decks / augments / items | `https://mcp-api.op.gg/mcp` (MIT) | See [prior-art](prior-art.md) — ToS conflict, needs a smoke test |
| Match history | `tft-match-v1` via [developer.riotgames.com/apis](https://developer.riotgames.com/apis) | **`tft-match-v5` does not exist** |
| Data Dragon | — | **Demote.** No Set 18 keys |
| Live TFT board state | — | **Does not exist.** Live Client Data API is Summoner's-Rift-only ([#373](https://github.com/RiotGames/developer-relations/issues/373), open since 2020) |

## Six traps that fail silently

| Trap | Symptom | Rule |
|---|---|---|
| **Trait art built from the display name** | This doc previously documented `trait_icon_18_<en_name>.png`. String-building the filename from the EN display name resolves **34/36**; two traits 404. Reading `icon` verbatim resolves **36/36** | Never string-build. This trap was *in this file* |
| `vn_vn.json` vs `vi_vn.json` | **Now branch-dependent**: `vn_vn` is **404 on `/latest/`** but still **HTTP 200 on `/pbe/`**, frozen at 2023-05-03. A PBE-configured loader still fails silently | Use `vi_vn.json`. Assert `Last-Modified` at load regardless of branch |
| Aggregate `cdragon/tft/{lang}.json` `sets['18']` | **Still a stub on live** — `number=18`, `mutator=TFTSet18`, but `name=Set10`, 19 PvE monsters, nonsense costs (8, 11) | Read the roster from `tftchampions-teamplanner.json`, never the aggregate |
| Set 18 reuses **Set 10** asset names | Confirmed live: the stub is literally `name=Set10`; `SetAugmentContainer` is `EOG_AugmentProp_Set10.png` | Key on `mutator` / `number`, **never** `name`. Add a regression assert |
| Inconsistent identifiers | `character_id` no longer starts `TFT18_` — **65/65** start with `DA` in three shapes (`DA_18_Xayah` ×48, `DA_Krug18`, `DA_Gromp18_AP`); casing differs *within* one path (dir `TFT18_Murkwolf` vs file `TFT18_MurkWolf_Square`) | Read paths verbatim, strip, lowercase. Never construct |
| **`setData[0]` is not the set you want** — measured 2026-09-01 on the full `en_us.json` | The real locale carries **35** `setData` blocks in no meaningful order. Index 0 is **`TFTSet14`**; Set 18 sits at index 1 — and *its* `name` is `"Set10"`, so filtering by name fails too. Reading `setData[0]` yields a Set 14 trait map with **no error**: `trait_affinity` comes back empty for all 254 augments and `BoardFit` goes neutral across the board | Select by **`mutator == "TFTSet18"`**. Never by position, never by `name` |

> ⚠️ The `setData[0]` trap is invisible to a trimmed fixture. `tests/fixtures/cdragon/*.trimmed.json`
> keep exactly one `setData` block, so code indexing `[0]` stays green through the whole test suite
> and only breaks the first time it meets the real file. Locked by
> `cdragon_client.select_set_data()` and `tests/test_cdragon_client.py`.
>
> **General lesson**: a fixture that is a strict subset can hide a trap that lives in the *shape* of
> the full data, not its values. Trimming is not free.

## The four-namespace join

`trait_id` → EN display → icon filename → VI display, with **no string rule connecting them**:

| trait_id | EN | icon file | VI |
|---|---|---|---|
| `DA_18_Slayer` | Ravager | `trait_icon_18_ravager.tex` | Tàn Phá |
| `DA_18_Battlemage` | Monolith | `trait_icon_18_monolith.tex` | Cự Thạch |

Build an explicit four-column table keyed on `apiName`. Both verified HTTP 200 on live.

## What still cannot be sourced

| Missing | Evidence (re-checked on live 2026-08-28) |
|---|---|
| Roll odds, XP costs, pool/bag sizes | `ShopOdds` / `TierOdds` / `ChampionTierOdds` / `LevelXP` = **0 hits** in the live Set 18 payload. Launch did **not** publish them |
| Augment / Wisp icon templates | 345 `DA_*` share one sprite; 48/254 `isAugment` carry `missing-t*` placeholders — see [augments](vision-stack/augments.md) |
| Meaningful augment win rates | Stats sites are days into cold start after 2026-08-26 |

**Consequence unchanged:** do not ship hardcoded odds. Gate the Economy Advisor behind verified 18.1
numbers or label it "unverified".

## Related

- [Research overview](overview.md)
- [Ban risk & Riot policy](vanguard-risk.md)
- [Vision stack](vision-stack/overview.md) · [Augment pipeline](vision-stack/augments.md)
- [Prior art, overlay UI & LLM layer](prior-art.md)
- [Open questions](open-questions.md)
