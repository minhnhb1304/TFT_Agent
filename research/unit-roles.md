# Unit Roles

> **Measured:** 2026-09-18 against `datatft.com/database` (data version **18.2b**, site-reported
> update 2026/09/17). Not yet imported — this is a costed proposal, not a shipped source.

**Bottom line:** the champion `role` field that CDragon leaves empty for 63 of 65 Set 18 units is
published in full by DataTFT, as **12 roles covering all 65 units**. The roles are not editorial
labels: each one is a **mana-generation rule**, so the taxonomy is Riot's own mechanic, not a
tier-list opinion. This unblocks the `role` fallback already written into
`infer_carry_type` (`src/decision/scoring/board_fit.py:58`), and it fixes carry detection in
`CompAggregator`.

## Why this is not the stat-derived role heuristic that was rejected

A role guessed from `range` + `hp` labels every melee unit a tank, which deletes exactly the reroll
comps the advisor most needs: measured on 40 vn2 matches, **5 of 20 detected carries are melee**
(Rengar, Master Yi, Camille, Akali, Nidalee). DataTFT's taxonomy classes all five as
Fighter / Specialist / Marksman — never Tank. A "Tank is never the carry" rule is therefore safe
against this source and unsafe against a stat heuristic.

## The 12 roles

Prefix = damage type. Suffix = mana and targeting behaviour.

| Role suffix | Mechanic |
|---|---|
| Assassin | Attacks grant 10 mana. Takes **15% less damage** from every enemy except its current target |
| Caster | Attacks grant **7** mana. Gains **2 mana regen** |
| Fighter | Attacks grant 10 mana. Gains **5-30% attack speed, scaling with stage** |
| Marksman | Attacks grant 10 mana. No further bonus |
| Specialist | "Specialists generate resources in a unique way" — per-unit special case |
| Tank | Attacks grant only **5** mana, but **gains mana from taking damage**, and is **more likely to be targeted** |

`Hybrid Fighter` exists in the taxonomy with **0 units** in Set 18.

## Set 18 distribution

| Role | n | Units |
|---|---|---|
| Magic Tank | 17 | Leona, Rek'Sai, Rakan, Ornn, Kobuko, Alistar, Elise, Shen, Sejuani, Fiddlesticks, Hecarim, Amumu, Malphite, Lillia, Sentinel, Taric, Maokai |
| Magic Caster | 13 | Karma, Veigar, Pebbles, LeBlanc, Teemo, Gromp, Cassiopeia, Soraka, Ahri, Zyra, Lux, Ivern, Alune |
| Attack Caster | 7 | Varus, Cinderling, Yunara, Kog'Maw, Sivir, Ezreal, Ashe |
| Attack Fighter | 6 | Akali, Camille, Warwick, Rengar, Brambleback, Elder Dragon |
| Attack Tank | 6 | Yorick, Scuttlecrab, Rammus, Vi, Krug, Sett |
| Attack Marksman | 5 | Xayah, Tristana, Mama Beak, Aphelios, Draven |
| Attack Specialist | 3 | Caitlyn, Master Yi, Gnar |
| Magic Assassin / Fighter / Marksman | 2 each | Kha'Zix, Kennen / Diana, Morgana / Azir, Nidalee |
| Magic Specialist / Attack Assassin | 1 each | Kayle / Murkwolf |

## How to obtain it — and the two constraints

- **There is no crawlable REST API.** `api.datatft.com` is POST-only and signs every request
  (timestamp + nonce + device id + a salt baked into the bundle); the unit database itself ships as
  an **AES-ECB encrypted blob** (`assets/data-us-*.js`). Neither was touched.
- **Read the rendered page instead.** Headless Chrome on `/database`, then
  `document.querySelectorAll('.hero-cover-item')` — each card carries name, traits, cost and role as
  plain text. `robots.txt` allows `/database` (it disallows only `/admin`, `/login`, `/tip/edit`).
- **Crawl once per patch, not per run.** Roles change only when Riot reworks a unit.

## Mapping to `apiName` — one trap

All 65 display names resolve against the CDragon Set 18 roster. **Four names are ambiguous, and all
four are PvE monsters**: `Krug`, `Murkwolf`, `Razorbeak`, `Elder Dragon` each exist as a neutral
creep (`TFT_Krug`) *and* as a Set 18 unit (`DA_Krug18`). Disambiguate by cost or hardcode them; a
naive name match silently picks whichever comes first.

## Proposed work

1. `scripts/crawl_unit_roles.py` -> `data/unit_roles.json`, carrying `source` + crawl date like every
   other data file.
2. Feed `Champion.role` so the `infer_carry_type` fallback stops being dead code.
3. `CompAggregator.carries()`: exclude `*Tank` from carry candidates. This removes the tank-as-carry
   failure at its cause, where `item_weight` only removes it by symptom. It does **not** catch a
   frontline holding an emblem (`Brambleback`, Attack Fighter) — keep `item_weight` as well.

## Related

- [Set 18 status and data sources](set-data.md)
- [Open questions](open-questions.md)
- [Prior art](prior-art.md)
