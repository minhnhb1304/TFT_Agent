# Augment Recognition Pipeline

> **Verified:** 2026-08-28 against `/latest/`, n = **254** Set 18 augments (`apiName` prefix `DA_`,
> `isAugment: true`). Every number below is reproducible from `cdragon/tft/en_us.json`.

This page covers the **recognition** limit on the augment feature.

> 📌 **Scope note (SPEC v3).** The separate *policy* limit ("show, never rank") no longer constrains
> the build ([SPEC §11](../../SPEC.md)). The recognition limit below is **unaffected** — it is a
> property of Riot's data, not of Riot's policy.

## Template matching is not available

| Fact | Count |
|---|---|
| `DA_*` items sharing the single sprite `assets/ux/tft/hud/zaps/wands/set18_mechanicicon.tex` | **345** |
| `isAugment` entries carrying `missing-t1/t2/t3.tex` placeholders | **48 / 254** (19%) |

No per-augment art exists to match against — hence Gemini Vision as **primary** here (spec §9.3).
Champions and traits are unaffected (65/65 and 36/36 icon coverage).

## Tier resolution — the previous rule was inverted

Earlier guidance said *"resolve tier by icon-path lookup."* That half is wrong: **augment icon art is
reused across tiers**, so **19/254** paths contradict the augment's own `apiName` and `name`:

| apiName | display name (authoritative) | icon path (misleading) |
|---|---|---|
| `DA_BronzeForLifeII` | Bronze For Life **II** | `bronzeforlife_iii.tex` |
| `DA_GoldenGamblePlus` | Golden Gamble**+** | `goldengamble_iii.tex` |
| `DA_CognitiveTaxPlus` | Cognitive Tax**+** | `cognitivetax_i.tex` |

> **Rule: `apiName` / `name` is authoritative. The icon path is a fallback, used only when the name
> carries no tier token.** Never let the icon override an explicit name suffix.

### The separator bug

The tier suffix uses **both** separators: `_` on 127 paths and `-` on 49. Matching only `_ii.` — as
previously documented — **silently misses 49/254 = 19%** of Set 18 augments. Match on
`[-_](i{1,3})\.tex$`, never `_ii.`.

### Resolution ladder — reaches 254/254

Apply in order, first match wins. **The authoritative signal is checked first**, so the 19 conflicts
above resolve correctly by construction:

| # | Signal | Resolves |
|---|---|---|
| 1 | `apiName` / `name` tier token — roman `I`/`II`/`III`, or `+` / `Plus` / `PlusPlus` | 75 |
| 2 | `missing-t(\d)\.tex$` — the placeholder filename encodes tier | 28 |
| 3 | `[-_](i{1,3})\.tex$` on the icon path — **note both separators** | 135 |
| 4 | `(\d)\.tex$` — trailing digit on the icon path | 16 |

Total **254/254**, zero unresolved. Note the irony in step 2: the `missing-t*` placeholders that make
template matching impossible are among the *most reliable* tier signals available.

> **Step order is load-bearing.** Putting the icon checks first resolves the same 254 augments but
> assigns **19 of them the wrong tier**.
>
> `_Gold`/`_Silver` suffixes are **not** tier signals: `DA_GlassCannon_Gold` is named "Glass Cannon
> **II**". Treating Gold as tier 3 inflates the count to 21. Locked by `tests/test_augment_catalog.py`.

## Hard ceiling — pairs that cannot be told apart

Five pairs share an identical **normalised name** and an identical **icon**. Corrected 2026-08-29 — an
earlier draft claimed "three of four differ only by tier"; the regression tests refuted it.

| Pair (`apiName`) | EN / VI name | Shared icon | Differs by | Recoverable |
|---|---|---|---|---|
| `DA_NestingDollsPlus` / `…PlusPlus` | Nesting Dolls / Búp Bê Xây Tổ | `missing-t3` | **tier** 2 vs 3 | ❌ |
| `DA_18_FloraFatalisAugment` / `…Plus` | Consuming Flora / Thực Vật Hấp Thụ | `missing-t2` | nothing — both tier 2 | ❌ |
| `DA_18_PrimalAugment_Sivir` / `_Nidalee` | Beast Within / Quái Thú Bên Trong | `missing-t2` | champion granted | ❌ |
| `DA_18_PrimalAugmentPlus_*` | Beast Within+ / …+ | `missing-t2` | champion granted | ❌ |
| `DA_TonsOfStatsI` / `II` | `Tons of Stats!` vs `TONS of Stats!` | `tons-of-stats-ii` | **tier** 1 vs 2 | ✅ EN only |

English loses **4 pairs, only one a tier distinction**; Vietnamese loses **5**, two of them tier. Real
either way — but mostly *champion/variant* ambiguity, not the tier catastrophe first implied.

### Handling rules

`ocr.md` mandates *"lowercase before any comparison"* — but capitalisation is the **only** thing
separating `Tons of Stats!` from `TONS of Stats!` in English, so lowercasing destroys it.

> **Exception:** match case-insensitively to find candidates; if >1 survives, re-compare
> **case-sensitively** before giving up.

Resolve to one augment → score it. Resolve to a pair → **surface both as ranked entries sharing one
recognition, both labelled; never guess.** Only the on-screen *description text* separates them.

## Language note

Vietnamese is **slightly worse**: it loses 5 pairs vs English's 4 (VI collapses `Tons of Stats!` /
`TONS of Stats!`). A **name-collision** risk, not a diacritics risk — diacritics are measured and
refuted in [ocr.md](ocr.md).

## Related

- [OCR engine & matching rules](ocr.md) · [Vision stack overview](overview.md) · [Set 18 & data sources](../set-data.md)
- [Ban risk & Riot policy](../vanguard-risk.md) — the policy limit on this same feature · [Open questions](../open-questions.md)
