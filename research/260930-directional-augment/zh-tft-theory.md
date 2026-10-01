# ZH-community check: directional augment value (2-1/3-2 board-not-committed claim)

Scope: Chinese-language (简体/繁體) high-elo TFT (云顶之弈) theory only. 3 search-fetch iterations (+1 extra verification round). Retrieval limitation flagged up front: 知乎专栏 (zhihu columns) returned HTTP 403 on every WebFetch attempt (5 tries), NGA (`nga.178.com`) is not indexed by the search tool used (`site:` operator returned zero relevant hits), one Bilibili 专栏 (`cv14705010`) returned empty/paywalled content, one Sohu article was fetched but explicitly lacked the theory content sought, and `web.archive.org` is blocked in this environment entirely. These are exactly the platforms most likely to carry deep theorycrafting (知乎专栏, NGA楼中楼讨论, B站长文). What follows is therefore built from what actually loaded: Gamersky (游民星空) guides, Sohu articles, search-engine snippets from Zhihu/Hupu/17173/QQ pages I could not directly fetch, and one 17173 article fetched in full. Confidence is capped accordingly — see verdicts.

---

## Claim 1: 先符文后阵容 (augment-first, comp-decided-later) is ZH high-elo consensus at 2-1/3-2

**Verdict: PARTLY (weak/mixed evidence, no source states this as a named consensus theory)**

Evidence:
- **Against/complicating** — Gamersky S6 guide (2021, older season): *"因此根据阵容选择合适的海克斯强化是新版本的唯一玩法"* ("selecting the right augment based on your comp is the only playstyle of the new version") — states the opposite direction (comp→augment fit), but this is S6-era (双城之战 pre-set) design philosophy, not S18-current. https://www.gamersky.com/handbook/202111/1435383.shtml
- **Partial support** — a search-engine-surfaced fragment (source page not independently re-confirmed by direct fetch, treat as lower-confidence): *"羁绊和职业类的海克斯的缺点是需要确定阵容，因为会固定阵容的搭配，但是职业羁绊类的海克斯是最强的过渡，最适合连胜"* ("trait/class augments' downside is they require locking in a comp because they fix your lineup, but they're the strongest early transition tool, best for winstreaking") — frames comp-locking as an explicit **downside** of certain augments, implying non-locking augments are preferred while comp is undecided. This is the closest thing found to the claim's spirit, but it argues a tradeoff, not a named "augment-first" doctrine, and I could not open the primary page to confirm exact wording/author.
- **Adjacent, no augment link** — Gamersky 搜卡技巧 piece: *"前两轮千万不要考虑什么阵容，以抓对子凑二星为主，第三轮再根据手牌决定发展方向"* ("don't think about comp at all in the first two rounds; grab pairs for 2-star; decide direction in round 3 based on your hand") — confirms comp is genuinely undecided early, but attributes the decision trigger to **手牌 (hand/cards)**, not augments. https://www.gamersky.com/handbook/201908/1214300_2.shtml (via search snippet)
- **Notable silence** — a dedicated Gamersky 过渡期 (transition-stage) guide (S5-era, 11.12 patch, 2021) explicitly frames early comps as **打工体系** (temporary "laboring" comp) and states the route is decided at the "2-2武器库/石头人" checkpoint and final comp locked at the **D牌阶段** — and **does not mention augments/海克斯 at all** in this decision framework. https://www.gamersky.com/handbook/202106/1399649_2.shtml — could reflect the source's age (augments were less central pre-S6) rather than current theory.
- No source found that explicitly compares 2-1 vs 3-2 vs 4-2 as different degrees of commitment, as the claim asks.

**Conclusion:** I could not confirm "先符文后阵容" as a stated ZH consensus doctrine. What's confirmed is a real, recognized *tradeoff* — trait/class-locking augments trade flexibility for early power — but the accessible sources frame decision-timing around hand/cards and equipment-pool checkpoints, not augments as the primary determinant. Given the 403 wall on 知乎专栏 (where this kind of systematized theory is most likely to live), this verdict should be treated as inconclusive rather than a real refutation.

---

## Claim 2: economy augments split into opposite-direction families (刷新/重随 → D牌三星 vs 经验 → 冲人口找双星高费), with 纯金币 as neutral third family

**Verdict: REFUTED (as stated) — accessible ZH sources rank economy augments by power tier, not by directional family**

Evidence:
- Full-text fetch of a dedicated economy-augment article (17173, 2026-02-28, author 兔顶之弈): confirms the article **does not systematically distinguish augment families by mechanical type** (reroll/refresh vs XP vs pure gold). It ranks individual augments hierarchically (S-tier/mid/low) by overall strength and by which existing strategy they slot into (e.g. 物尽其用 enabling 连胜经济/winstreak economy; 新纪元 enabling early interest stacking; 存心失利 pairing gold+refreshes). It "briefly hints" at directional push (front-loaded-gold augments → early interest; refresh-focused augments → D-card support) but explicitly does **not** map augment types to comp archetypes the way the claim states. https://news.17173.com/content/02282026/153155590.shtml
- Search snippet (generic strength claim, no family split): *"经济类的强化符文是最强的，但越到后期越需要补一个战力类强化"* ("economy augments are the strongest [class] but you need to add a power-augment later or you'll cap out") — again power-tier framing, not the two-opposed-families framing.
- Search snippet noted a **细水长流型 vs 收菜型** (slow-drip vs harvest) two-way split — but the search tool itself flagged this is about **羁绊 (trait synergies)**, not augments, and I found no source extending it to augments.
- No source found treating 纯金币 (pure-gold, no reroll/no XP) augments as an explicit third, direction-neutral family.

**Conclusion:** The opposition claimed (reroll-economy forces low-cost 3-star / XP-economy forces high-cost double-up) is a real structural fact about *what the mechanics do*, but I found no ZH source that names or theorizes it as two opposed "families" the way the claim frames it. ZH guides I could reach discuss economy augments individually by tier/strength, not by this directional taxonomy.

---

## Claim 3: ZH vocabulary — genuine community terms found (with gloss + source)

Confirmed via search/fetch (real usage, not invented):

| Term | Gloss | Example source |
|---|---|---|
| 打工体系 / 打工阵容 | Temporary early-game "laboring" comp used only to survive/winstreak before the real comp is decided | Gamersky transition guide, S5/11.12: "过渡期阵容...仅是前期血量积累工具，并非最终成型" — https://www.gamersky.com/handbook/202106/1399649_2.shtml |
| 定路线 | "Decide the route" — the checkpoint where a player commits to a general direction (not full comp) so item-building can proceed | Same source: *"大致路线上我们一般要在2-2武器库或最晚石头人后就要决定了，不定路线就没法合装备"* |
| 成型阵容 | "Formed/settled comp" — the point comp is actually locked | Same source: *"确定成型阵容的时机就是D牌...的时候了"* |
| D牌 / D牌流 | Rerolling down (staying low-level) to dig for 2-star/3-star copies of cheap units | Search snippet, zhihu p/491707962 era guide: "最佳D牌阶段是3-1阶段" |
| 容错率 | "Error-tolerance rate" — how much margin for mistakes a comp/economy/health total gives you | Search snippet: *"容错率分为阵容、血量和金币三个方面...刺客阵容的容错率很低"* (assassin comps have low error-tolerance) |
| 保血冲人口 | Preserve HP while pushing levels — the XP-economy playstyle named directly in claim 2's language and independently found in guides | Search snippet: *"尽量维持和运营一样的人口...千万不要卖大血"* |
| 撞车 / 撞卡 | "Collision" — contention when multiple players want the same champion/pool, worsened by 专属强化 (champion-locked augments) | QQ syzs article snippet: *"当多个玩家选择同一个英雄的专属强化符文时，会出现撞车现象，这会大大增加双方将该英雄升到3星的难度"* — https://syzs.qq.com/blog/news/20230126A001I700 |
| 抢卡 | "Fighting over cards" — contesting the same pool as opponents | Search snippet, gamersky 搜卡技巧: "需要观察对手的阵容特点，判断是否有人和自己抢牌" |
| 卡池 | Shared card pool (finite copies per cost) | Multiple sources, standard term |

**Terms from the assignment I could NOT verify with a citation** (searched directly, no confirmed source found): 定体系/定阵容 as a fixed idiom (I only found the functionally-equivalent 定路线/成型阵容), 转型 (used generically for "pivot" in TFT context broadly but not pinned to a specific augment-theory source), 强制体系 (not found as a set phrase — the closest is the "缺点是需要确定阵容" framing above, which describes the concept without this exact label), 上限/下限 (ceiling/floor — a very common general ZH gaming term, but I did not find it applied specifically to augment theory in what loaded), 开局符文 (not found as a set phrase — sources say 海克斯/强化符文 generically, sometimes "第一个海克斯"), 上人口流 (I could not find this exact 4-character compound; sources use 冲人口/升人口/上人口 as verbs, not as a named "-流" style/archetype the way D牌流 is named), 卡级 (not found — closest is 卡人口, holding at a level).

Per the instruction not to invent vocabulary: the report above only asserts terms that appeared in fetched/search-snippet text; everything else is marked unconfirmed rather than presented as genuine.

---

## Claim 4: augment value = optionality (how many viable comps it opens) vs current-board fit; counter-argument (早定体系 better due to 抢卡/撞体系)

**Verdict: PARTLY / UNCONFIRMED — optionality framing itself not found in accessible sources; the counter-argument's underlying mechanic is confirmed as real**

Evidence:
- Direct fetch of a Sohu S13 augment-tier article explicitly checked for this framing and found **none**: *"该文章... 不theorize是否augment strength来自打开多个可行阵容而非当前板面契合度"* — the article was pragmatic tier-list style, not theory. https://m.sohu.com/a/828915123_122004016
- The **counter-argument's premise is independently confirmed real**: 撞车/撞卡 (pool contention over champion-locked augments/cards) is a named, recognized mechanic — see 撞车 entry above (QQ syzs). This is consistent with an "early commitment has value because it claims scarce pool share before opponents" argument, but no source in what I retrieved explicitly makes that argument *in opposition to* an optionality theory of augment value.
- The closest analog to the tension in claim 4 is the trait/class-augment tradeoff snippet already cited under Claim 1 (locks comp = downside, but strongest for winstreak = upside) — this is a power-vs-flexibility tradeoff, not explicitly an optionality-of-future-comps argument.

**Conclusion:** Neither the optionality framing nor a clean rebuttal of it surfaced in accessible ZH sources. What's confirmed is that (a) comp-locking is recognized as a real cost of some augments, and (b) pool contention (撞车/抢卡) is a real, named factor that would favor early commitment when the scarce resource is a specific champion. Whether high-elo ZH theory actually weighs these into an explicit "optionality vs board-fit" framework is not established by what I could retrieve — most likely because that level of theorycrafting lives on 知乎专栏/NGA, both of which were inaccessible this session.

---

## Set/season notes

Sources found span S5 (2021, 11.12/9.16 patches) through S13 (2024) and one 2026-dated 17173 article (undated season number, but 2026-02-28 puts it plausibly in S17/pre-S18 window) — none explicitly S18. Where a source is S5/S6-era, I flagged it inline; those describe *pre*-modern-augment-design philosophy (augments were newer, less centrally theorized then) and should not be read as current-meta claims. No source found discusses whether the directional-augment principle is set-independent — this question is open.

---

## Sources

- https://www.gamersky.com/handbook/202111/1435383.shtml — Gamersky, S6 (2021) 海克斯强化玩法介绍
- https://www.gamersky.com/handbook/202106/1399649_2.shtml — Gamersky, S5/11.12 (2021) 过渡期玩法思路
- https://www.gamersky.com/handbook/201908/1214300_2.shtml — Gamersky, 2019, 搜卡技巧 (via search snippet)
- https://news.17173.com/content/02282026/153155590.shtml — 17173, 2026-02-28, 经济强化 article (author 兔顶之弈) — full fetch
- https://m.sohu.com/a/828915123_122004016 — Sohu, S13 (2024-11-21) 海克斯阵容攻略, author 游戏草率菌 — full fetch
- https://syzs.qq.com/blog/news/20230126A001I700 — QQ syzs, 2023, 专属强化/撞车 article (via search snippet)
- https://voice.hupu.com/bbs/624027933 — Hupu, designer/patch info (fetched, no relevant theory content found)
- https://teamfighttactics.fandom.com/zh/wiki/强化符文 — ZH fandom wiki (fetch failed, HTTP 402)
- https://www.bilibili.com/read/cv14705010/ — Bilibili 专栏 (fetch returned empty content)
- Zhihu columns (multiple: p/123369120, p/453339826, p/491707962, p/539650197, etc.) — all WebFetch attempts returned HTTP 403; only search-engine snippets available, cited above as "search snippet" with reduced confidence
- `site:nga.178.com` search — zero relevant results returned by search tool
- `web.archive.org` — blocked in this environment, could not use as 403 workaround

## Unresolved questions

1. Does 知乎专栏/NGA (inaccessible this session) contain an explicit "先符文后阵容" doctrine or its rebuttal? Unknown — needs a session with working zhihu/NGA access or an authenticated fetch tool.
2. Is there a named ZH term for "augment optionality" (claim 4) at all, or is this purely an EN-community framing with no ZH analog?
3. Does ZH theory actually distinguish 2-1 vs 3-2 vs 4-2 augment-decision behavior, or is this a distinction the EN design doc introduced that ZH community doesn't make?
4. Are 上人口流 and 卡级 real named archetypes/terms that exist in ZH TFT discourse but simply didn't surface in my searches, or are they not real established terms?
