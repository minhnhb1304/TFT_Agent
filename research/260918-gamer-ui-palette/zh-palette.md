# ZH sources — dark gaming/esports analytics UI palette (desktop)

Searched in 中文 only. 4 iterations. Facts + hex + URLs.

## 1. Dark background / surface scales (exact hex, Chinese design systems)

### TDesign (腾讯, open source) — authoritative, machine-readable
Source: https://raw.githubusercontent.com/Tencent/tdesign-common/main/style/web/theme/_dark.less
(docs: https://tdesign.tencent.com/design/dark , https://tdesign.tencent.com/design/color)

14-step neutral ramp, dark mode (gray-1 lightest → gray-14 darkest):
```
1 #f3f3f3  2 #eeeeee  3 #e7e7e7  4 #dcdcdc  5 #c5c5c5  6 #a6a6a6  7 #8b8b8b
8 #777777  9 #5e5e5e 10 #4b4b4b 11 #383838 12 #2c2c2c 13 #242424 14 #181818
```
Semantic mapping in dark:
- page background = gray-14 `#181818`
- container (card) = gray-13 `#242424`
- container hover = gray-12 `#2c2c2c`; container active = gray-10 `#4b4b4b`; container selected = gray-9 `#5e5e5e`
- secondary container = `#2c2c2c`; its hover `#383838`
- component bg = gray-11 `#383838`; hover `#4b4b4b`; active `#5e5e5e`; disabled `#2c2c2c`
- divider / component stroke = gray-11 `#383838`
- border (stronger) = gray-9 `#5e5e5e`
- scrollbar = `rgba(255,255,255,10%)`
- mask: popup `rgba(0,0,0,40%)`, disabled `rgba(0,0,0,60%)`
- inset hairline on popups = `inset 0 .5px 0 #5e5e5e`
- table shadow color `rgba(0,0,0,55%)`

Text on dark (opacity, NOT solid hex — key convention):
- primary `rgba(255,255,255,90%)`, secondary `55%`, placeholder `35%`, disabled `22%`
- anti/inverse only = `#fff` (small scale)

TDesign brand (blue) dark ramp 1→10:
`#1b2f51 #173463 #143975 #103d88 #0d429a #054bbe #2667d4 #4582e6 #699ef5 #96bbf8`
- default brand in dark = ramp **8** `#4582e6` (light mode uses ramp 6) → i.e. accents get **lighter + less saturated** in dark.
- hover = ramp7 `#2667d4`, active = ramp9 `#699ef5`, focus = ramp2 `#173463`, light-selected = ramp1 `#1b2f51`.
- text-link and text-brand = `#4582e6`.

Status colors in dark (the value actually used as `--td-*-color`):
- warning `#cf6e2d` (ramp5); ramp: `#4f2a1d #582f21 #733c23 #a75d2b #cf6e2d #dc7633 #e8935c #ecbf91 #eed7bf #f3e9dc`
- error `#c64751` (ramp6); ramp: `#472324 #5e2a2d #703439 #83383e #a03f46 #c64751 #de6670 #ec888e #edb1b6 #eeced0`
- success `#059465` (ramp5); ramp: `#193a2a #1a4230 #17533d #0d7a55 #059465 #43af8a #46bf96 #80d2b6 #b4e1d3 #deede8`

Design rationale (TDesign color doc): neutral scale was expanded to **14 levels using CIELab lightness** specifically "为在深色模式下区分界面层级"; color ramps built in **HCT space** with saturation+lightness interpolation so tones are perceptually even; common text colors hit contrast > 4.5 (WCAG 2.0).
Source: https://tdesign.tencent.com/design/color , https://codesign.qq.com/hc/article/design-system-color/

### Ant Design dark (via 优设 write-up)
Source: https://www.uisdc.com/dark-pattern-design
Three-layer framework, exact hex:
- 应用框架/top layer `#1F1F1F`
- 内容组件/middle `#141414`
- 页面容器/base `#000000`
Neutrals expanded to **13 steps** because shadows barely read on dark — layering must be done with lightness, not elevation shadows.
Text opacity: primary 85%, secondary 65%, tertiary 45%, **disabled raised to 30%** (vs light) so it doesn't vanish.
Explicit rule: "避免大面积使用纯 #FFFFFF 文字", esp. tables/lists (reading-heavy). Pure white only for small-scale emphasis.
Brand color in dark derived by **transparency transform** of the base brand, not a separate palette; for hues **225–330°** (deep cool tones) increase transparency further or they become unreadable on dark.

### Material dark, as taught in Chinese design circles
Source: https://www.cnblogs.com/timefiles/articles/16894260.html
- surface `#121212`; elevation = semi-transparent **white overlay** 0%→16% (1dp = 5%, 8dp = 12%, 24dp = 16%)
- primary color in dark = the **200 tone** (desaturated) to hold ≥ 4.5:1 and reduce 光学振动 (optical vibration)
- text opacity 87% / 60% / 38%
- deepest surface vs white text ≈ **15.8:1** so that even disabled text on the *highest* (lightest) surface still clears 4.5:1
- dark error color `#CF6679` = light `#B00020` + 40% white overlay

### 微信 dark (cited as example in ZH guide)
Source: https://pixso.cn/designskills/dark-ui-design-guide/
- dialog background `#1E1E1E`; body text = white @ 80% ≈ `#C1C1C1` → **9.26:1**
- dividers nearly invisible on purpose (minimize lines, use spacing instead)
- 3–4 elevation levels, max 4–5 surface tones
- warning icon saturation is *lowered* in dark vs light

### 京东 (JD) dark mode spec — principles, no hex published
Source: https://jdrdl.jd.com/Design-Darkmode.html
- pure white text produces "文字边缘明显的光晕" (halo at glyph edges) → don't
- avoid high-saturation accents (视觉振动)
- images get a translucent black overlay to cut saturation+brightness
- shadows are weak on dark → express hierarchy with different black levels

## 2. Rarity / quality tier colors (白绿蓝紫橙金)

Canonical hex (WoW lineage, the de-facto standard cited by Chinese sources too):
Source: https://www.color-hex.com/color-palette/38466 , https://warcraft.wiki.gg/wiki/Quality
```
普通/Common     白  #FFFFFF   (poor/劣质 usually #9D9D9D grey)
精良/Uncommon   绿  #1EFF00
稀有/Rare       蓝  #0070DD
史诗/Epic       紫  #A335EE
传说/Legendary  橙  #FF8000
神话/Mythic     粉/彩  (no single standard; 粉色或彩色)
```
Origin per Chinese sources: 《暗黑破坏神》1996 → 《暗黑破坏神2》2000 established it, WoW propagated it; now default grammar in 国内游戏界.
Sources: https://www.thepaper.cn/newsDetail_forward_33444206 , https://www.zhihu.com/question/21922080 , https://cowlevel.net/question/1869989

Caveat: `#1EFF00` and `#FF8000` are very saturated — on a `#181818`-class dark surface they trigger the 视觉振动 problem every ZH dark-mode spec warns about. Expect to desaturate/lighten per Material's "200 tone" rule if used as text.

### TFT / 云顶之弈 cost tiers (直接相关)
1费 白 / 2费 绿 / 3费 蓝 / 4费 紫 / 5费 金(橙) — same 5-step ladder, gold at top instead of orange.
Sources: https://tft.scoregg.com/post/1062437.html , https://gl.ali213.net/html/2019-6/343031.html , https://www.9game.cn/yundingzhiyi/6646781.html
羁绊 tiers use a *different* metal ladder: 青铜 / 白银 / 黄金 / 棱彩 (bronze/silver/gold/prismatic) — no published hex found in ZH sources.

### T0/T1/T2 tier-list colors
**Negative finding.** ZH TFT/金铲铲 tier-list sites (233乐园, TapTap, scoregg, 3DM) use T0/T1/T2 labels heavily but **publish no color spec or hex**. No ZH design write-up on tier-badge coloring found. In practice ZH sites reuse the rarity ladder (T0=橙/金, T1=紫, T2=蓝, T3=绿) — inferred, not sourced.

## 3. Dark readability rules (ZH consensus)

- **Never pure black bg.** Reason given consistently: 黑色太深，无法让用户感知界面的高度和空间感; grey levels are what communicate depth. Use 深灰 (#121212 / #181818 / #1E1E1E class).
  https://pixso.cn/designskills/dark-ui-design-guide/ , https://www.cnblogs.com/timefiles/articles/16894260.html
- **Never pure white text at scale.** Halo/bloom at glyph edges, "到处都是亮点", causes 误操作. Use 90%/85% white or a slightly dimmed white.
  https://jdrdl.jd.com/Design-Darkmode.html , https://www.uisdc.com/dark-pattern-design
- **Contrast**: WCAG AA 4.5:1 body, 3:1 large text; dark specs additionally target **15.8:1** between deepest surface and white text as headroom so upper surfaces still pass.
- **Saturation**: high-saturation colors on dark produce 光学振动/视觉振动 → eye fatigue. Desaturate accents, brighten them instead.
- **Shadows don't work** on dark → use surface lightness steps (3–5 max) for elevation.
- **Dark is the right default** for "需要用户长时间盯着界面" categories — explicitly names 基金/股票/视频直播/设计开发类; esports analytics fits the same profile. Game UI specifically: 玩家长时间交互，冷色暗色系可避免过度视觉刺激和疲劳.
  https://pixso.cn/designskills/dark-ui-design-guide/ , https://zhuanlan.zhihu.com/p/64707077
- **60/30/10** ratio cited as the ZH game-UI color split: 主色 60% / 辅助色 30% / 突出色 10%.
  https://zhuanlan.zhihu.com/p/64707077

## 4. Typography for numeric/data-dense dark UI (ZH)

Source: https://www.uisdc.com/visual-design-font (数据可视化设计指南·字体篇), also https://zhuanlan.zhihu.com/p/649423144 , https://sspai.com/prime/story/monospaced-fonts
- **Numerals: use 等宽/等距 digits (tabular figures)** so columns align on the same vertical — explicitly called out as the thing that makes tables scannable.
- Recommended numeral/Latin face: **D-DIN** (Regular for refined look). Chinese body: **思源黑体 / 苹方** (both commercially usable / system). Avoid thin serif (宋体) on screen; 无衬线 + slightly heavier weight.
- **Numbers render ~4–6px smaller than 中文 at the same font-size** → bump numeral size up so data reads clearly.
- Numeral weight: **Bold** for KPI/data emphasis.
- Table alignment: text + header left/center, **numbers right-aligned**.
- Min body size 16px at 1920×1080.
- On dark: increase font size slightly and loosen letter-spacing/line-height vs light mode (https://pixso.cn/designskills/dark-ui-design-guide/).

## 5. Gaming-tool specific design write-ups (ZH)

- **WeGame 暗色模式实践总结** — https://zhuanlan.zhihu.com/p/368289448 (403 to fetch; snippet only). Key claim from snippet: WeGame hosts many sub-products (LOL助手/CF助手/DNF助手) each with its own **独立主题色**; solution was to first conform each to WeGame's shared color system, then designer review passes. For backgrounds with mixed light/dark art they dropped dual background images in favor of a **dark overlay** on one asset. → pattern worth copying: one neutral system + per-module accent.
- 腾讯光子《英雄联盟手游》界面概念设计 — https://www.gameres.com/892149.html , https://www.uisdc.com/lol-interface-design — Hextech art direction (steampunk + dark fairy tale); concept-level, not a token spec.
- 腾讯游戏学堂《英雄联盟》界面交互设计之道 — https://gwb.tencent.com/community/detail/105108
- CoDesign (腾讯) 大厂网页设计规范·色彩篇 — https://codesign.qq.com/hc/article/design-system-color/

## Gaps / unresolved

1. No ZH source publishes **T0/T1/T2 tier-badge hex**. Must invent or borrow from rarity ladder.
2. No published hex for 云顶之弈 cost tiers or 羁绊 bronze/silver/gold/prismatic — would need to sample the client/assets directly.
3. 玩加赛事 / B站赛事数据 / 掌上英雄联盟 publish no design-system docs; only inspectable by scraping their CSS (not done).
4. WeGame dark-mode article is Zhihu-403'd — full content unverified beyond search snippet.
5. 米哈游 / 网易 dark-gaming-UI design articles: none found in 4 iterations. TDesign is the only ZH source with actual machine-readable dark tokens.

## Sources
- https://raw.githubusercontent.com/Tencent/tdesign-common/main/style/web/theme/_dark.less
- https://tdesign.tencent.com/design/dark
- https://tdesign.tencent.com/design/color
- https://codesign.qq.com/hc/article/design-system-color/
- https://www.uisdc.com/dark-pattern-design
- https://www.cnblogs.com/timefiles/articles/16894260.html
- https://pixso.cn/designskills/dark-ui-design-guide/
- https://jdrdl.jd.com/Design-Darkmode.html
- https://www.uisdc.com/visual-design-font
- https://zhuanlan.zhihu.com/p/64707077
- https://zhuanlan.zhihu.com/p/649423144
- https://sspai.com/prime/story/monospaced-fonts
- https://www.thepaper.cn/newsDetail_forward_33444206
- https://www.zhihu.com/question/21922080
- https://cowlevel.net/question/1869989
- https://www.color-hex.com/color-palette/38466
- https://warcraft.wiki.gg/wiki/Quality
- https://tft.scoregg.com/post/1062437.html
- https://gl.ali213.net/html/2019-6/343031.html
- https://www.9game.cn/yundingzhiyi/6646781.html
- https://zhuanlan.zhihu.com/p/368289448
- https://www.gameres.com/892149.html
- https://www.uisdc.com/lol-interface-design
- https://gwb.tencent.com/community/detail/105108
