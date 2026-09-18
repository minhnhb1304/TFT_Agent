# ZH Research: Modern Dark Palettes for a TFT Desktop Tool

Scope: colors only. Sources: Chinese design systems + Chinese design writing. All hex values below were extracted from **shipped token files**, not from articles, unless marked otherwise.

---

## 0. Headline finding (the mechanism)

Current bg `#14171f` = **HSL(224, 22%, 10%)**.

Every major Chinese design system ships a dark base with **saturation 0–8%**:

| System | Dark page bg | HSL | Sat |
|---|---|---|---|
| TDesign (Tencent) | `#181818` | (0, 0%, 9%) | **0%** |
| Ant Design v5 | `#000000` / container `#141414` | (0, 0%, 0/8%) | **0%** |
| Arco Design (ByteDance) | `#17171a` | (240, 6%, 10%) | **6%** |
| Semi Design (ByteDance/Douyin) | `#16161a` | (240, 8%, 9%) | **8%** |
| **Current TFT tool** | `#14171f` | (224, **22%**, 10%) | **22%** |

**The bg is ~3x more saturated than any shipped CN dark token.** That is the single measurable reason it reads as "土/网吧风" rather than "高级感". Saturated navy-black is the 2016–2019 esports/gaming-peripheral look; 2024–2026 CN systems converged on near-neutral.

Second mechanism: the amber accent.

| Color | HSL | Role in CN design systems |
|---|---|---|
| Current accent `#f4af25` | (40, 90%, 55%) | — |
| Ant Design `colorWarning` `#faad14` | (40, 96%, 53%) | **warning** |
| Arco `gold-6` `#f7ba1e` | (43, 93%, 54%) | gold preset, **not** a primary |
| TDesign `--td-warning-color` (dark) `#cf6e2d` | (24, 71%, 53%) | **warning** |

`#f4af25` is within ~3° hue and ~2% lightness of Ant Design's **warning token**. Used as the app-wide brand accent, the entire UI sits permanently in the "alert" semantic register — and in a data-dense tool every card reads as a caution flag. No major CN design system uses amber/gold as `colorPrimary`. Sources: [antd seed.ts](https://github.com/ant-design/ant-design/blob/master/components/theme/themes/seed.ts), [arco compiled-colors.less](https://github.com/arco-design/arco-design/blob/main/components/style/theme/color/compiled-colors.less), [tdesign _dark.less](https://github.com/Tencent/tdesign-common/blob/develop/style/web/theme/_dark.less).

Contrast check confirms it: `#f4af25` on `#14171f` = **9.4:1**. That is *higher than white body text needs*. A 9.4:1 accent competes with content instead of directing to it — the "everything glows" effect.

---

## 1. Shipped dark tokens (exact, from source)

### TDesign (Tencent) — `style/web/theme/_dark.less`

Pure-neutral gray ramp, zero hue:

```
gray-14 #181818   -> --td-bg-color-page
gray-13 #242424   -> --td-bg-color-container
gray-12 #2c2c2c   -> --td-bg-color-container-hover / secondarycontainer
gray-11 #393939   -> --td-bg-color-component / border-level-1 (divider)
gray-10 #4b4b4b   -> component-hover / secondarycomponent
gray-9  #5e5e5e   -> --td-component-border (real border)
```

Text: `rgba(255,255,255, 90% / 55% / 35% / 22%)` (primary/secondary/placeholder/disabled).
Brand in dark = `--td-brand-color-8` = **`#4582e6`** (light mode uses `#0052d9`).
Scrollbar `rgba(255,255,255,.10)`, hover `.30`.

### Semi Design (ByteDance) — `semi-theme-default/scss/global.scss`

Slight cool tint (~240°, 5–8%), 5-step elevation:

```
--semi-color-bg-0  rgb(22,22,26)   #16161a   page
--semi-color-bg-1  rgb(35,36,41)   #232429   container / nav
--semi-color-bg-2  rgb(53,54,60)   #35363c
--semi-color-bg-3  rgb(67,68,74)   #43444a
--semi-color-bg-4  rgb(79,81,89)   #4f5159
--semi-color-border      rgba(white, .08)
--semi-color-fill-0/1/2  rgba(white, .12 / .16 / .20)
--semi-color-text-0..3   grey-9 @ 1 / .8 / .6 / .35
--semi-color-overlay-bg  rgba(22,22,26,.6)
--semi-shadow-elevated   inset 0 0 0 1px rgba(255,255,255,.1), 0 4px 14px rgba(0,0,0,.25)
```

Semi's dark grey ramp is the light ramp **exactly reversed** (`grey-0` dark = `#1C1F23` = light `grey-9`). Primary dark = `blue-5` = **`#54A9FF`** (light `blue-5` = `#0064FA`).

Semi also ships an explicit **AI accent** set (`--semi-color-ai-general`, `--semi-color-ai-purple`) — violet/purple is the current CN "modern/AI" signal color.

### Arco Design (ByteDance) — `theme/color/compiled-colors.less`

Notable: Arco's **light** grays are blue-tinted (`#f7f8fa`, `#4e5969`, `#1d2129`), but the **dark** grays are stripped to near-pure neutral. Deliberate de-tinting on mode switch:

```
gray-1  rgb(23,23,26)   #17171a
gray-2  rgb(46,46,48)   #2e2e30
gray-3  rgb(72,72,73)   #484849
gray-4  rgb(95,95,96)   #5f5f60
gray-5  rgb(120,120,122)#78787a
gray-6  #929293  gray-7 #ababac  gray-8 #c5c5c5  gray-9 #dfdfdf  gray-10 #f6f6f6
```

Dark accent ramps (level 5 is the usable accent):

```
dark-blue-5   #4699fa    dark-cyan-5  #30c9c9
dark-green-5  #1db440    dark-green-6 #27c346
dark-orange-5 #ff8b1f    dark-gold-5  #f7c034
dark-red-5    #f54e4e    dark-red-6   #f76965
```

### Ant Design v5 — `theme/themes/dark/colors.ts`

Algorithmic, from `colorBgBase = #000`:

```
colorBgLayout     = lighten(bgBase, 0)   -> #000000
colorBgContainer  = lighten(bgBase, 8)   -> #141414
colorBgElevated   = lighten(bgBase, 12)  -> #1f1f1f
colorBgSpotlight  = lighten(bgBase, 26)
colorBorderSecondary = lighten(bgBase, 19)
colorBorder       = lighten(bgBase, 26)  -> ~#424242
colorText  85% / Secondary 65% / Tertiary 45% / Quaternary 25% (white alpha)
colorFill  18% / 12% / 8% / 4% (white alpha)
```

The published spec states the three frame levels as **`#000000` (page) / `#141414` (content component) / `#1F1F1F` (app frame)**, and that neutrals were extended to 13 steps for dark ([优设 / Ant Design dark spec](https://www.uisdc.com/dark-pattern-design)).

---

## 2. The accent rule in dark mode (Q4) — measured, not quoted

Computed from the light→dark token pairs above:

| System | Light accent | Dark accent | ΔL | ΔS |
|---|---|---|---|---|
| TDesign brand | `#0052d9` (217,100,43) | `#4582e6` (217,76,59) | **+16** | **−24** |
| Semi primary | `#0064fa` (216,100,49) | `#54a9ff` (210,100,66) | **+17** | 0 |
| Arco blue | `#3491fa` (212,95,59) | `#4699fa` (212,95,63) | +4 | −0 |
| Arco gold | `#f7ba1e` (43,93,54) | `#f7c034` (43,92,59) | +5 | −1 |

**Rule that actually holds across all four:** the dark accent lands at **HSL L ≈ 59–66%**, hue unchanged (±6°). How it gets there differs:
- If the light accent was already bright (L ≥ 54), only nudge +4~5 and leave saturation alone (Arco).
- If the light accent was deep (L ≤ 49), raise **+16~17 L** and either cut saturation ~24 pts (TDesign) or keep it (Semi).

Stated principle in CN design writing: 去饱和 (desaturate) so accent-vs-text contrast stays ≥ 4.5:1 at every elevation, per WCAG AA; and keep tones in the **50–200 band** of the palette rather than the 500+ band ([优设 dark mode adaptation](https://www.uisdc.com/dark-mode-adaptation), [人人都是产品经理 — Google dark mode](https://www.woshipm.com/pd/3318213.html)). TDesign's own writeup frames it as "降低饱和度与明度，通过透明度调节" rather than inverting, justified by 侧抑制 / 视觉适应 / 残像 ([站酷 — TDesign 暗黑模式适配探索](https://www.zcool.com.cn/article/ZMTMxNTc4OA==.html)).

Ant Design's stated transform is **透明度转换法, not 反色** — and specifically: for cool hues in **225°–325°**, raise the alpha value to avoid unreadable text on dark ([优设](https://www.uisdc.com/dark-pattern-design)).

**Target contrast for the accent: 4.5–7:1 on bg.** Not 9+. TDesign's `#4582e6` = 4.73:1, Arco `#4699fa` = 6.1:1, Semi `#54a9ff` = 7.3:1. Current `#f4af25` at 9.4:1 is out of band on the high side.

---

## 3. "土/过时" vs modern — mechanism table

| Dated mechanism | Why | Modern replacement |
|---|---|---|
| Saturated navy-black bg (S ≥ 15%) | Reads as 2016-era esports skin; tints every neutral on top of it, so grays look muddy | Near-neutral base, **S ≤ 8%** (TDesign 0%, Arco 6%, Semi 8%) |
| Gold/amber as **primary** accent | Occupies the `warning` hue slot in every CN system; whole UI reads as alert | Reserve amber for warning/one tier; primary = blue/cyan/violet at L≈60–66 |
| Accent contrast 9–11:1 | Over-signalling, "everything glows"; accent stops guiding the eye | Accent 4.5–7:1 on bg; let white text at 85% carry the contrast |
| Glow/outer-shadow on accent | 网吧风 shorthand | Elevation by **lighter surface**, not glow. Semi: `inset 0 0 0 1px rgba(255,255,255,.1), 0 4px 14px rgba(0,0,0,.25)` |
| Low-contrast gray-blue text | 高饱和/高明度 palettes lack 品质感 and 色彩间缺乏联系 → 低廉、粗糙 ([人人都是产品经理](https://www.woshipm.com/ucd/1729140.html), [设计达人](https://www.shejidaren.com/gaojigan-peise.html)) | Fixed alpha ladder: 90/55/35/22 (TDesign) or 85/65/45/25 (AntD) |
| Many accent hues at once | No hierarchy | One accent + semantic set; 大部分界面为深灰，少量强调色凸显功能 ([Material CN summary](https://zhuanlan.zhihu.com/p/73096322)) |
| Uneven ramps built in HSL | HSL L is "名不副实" — hue drift and uneven steps | Build in **OKLCH**: fix H and C, derive the whole ramp from L; e.g. `oklch(0.62 0.19 259)` → `.95 / .62 / .37` ([标点符](https://www.biaodianfu.com/oklch/), [知乎](https://zhuanlan.zhihu.com/p/560489954)). HCT exists but 换算复杂, 效果提升有限 |

Also standard in CN writing: never pure black as the *only* surface — Google's `#121212` baseline, elevation via 4%–12% white overlay ([优设 9图](https://www.uisdc.com/group/647088.html), [知乎 Material dark](https://zhuanlan.zhihu.com/p/73096322)).

---

## 4. Candidate palettes (validated)

All contrast ratios computed against each palette's own `bg`. Tier ramp is shared and taken from Arco's dark accent ramps so it's system-sourced rather than invented.

**Shared tier scale (S→D):**

| Tier | Hex | Source | CR vs `#16161a` |
|---|---|---|---|
| S | `#f54e4e` | Arco `dark-red-5` | 5.23 |
| A | `#ff8b1f` | Arco `dark-orange-5` | 7.70 |
| B | `#f7c034` | Arco `dark-gold-5` | 10.78 |
| C | `#27c346` | Arco `dark-green-6` | 7.72 |
| D | `#929293` | Arco dark `gray-6` | 5.80 |

> Note this is where the amber belongs: `#f7c034` as **tier B**, not as the app accent.

---

### Candidate A — 腾讯 TDesign 纯中性 (safest, most "企业级高级感")

| Token | Hex | CR vs bg |
|---|---|---|
| bg | `#181818` | 1.00 |
| surface1 | `#242424` | 1.14 |
| surface2 | `#2c2c2c` | 1.27 |
| surface3 | `#393939` | 1.54 |
| border | `#5e5e5e` | 2.74 |
| divider | `#393939` | — |
| accent | `#4582e6` | **4.73** |
| text 1/2/3/4 | white @ 90/55/35/22% | 17.8 (primary) |

Why modern: zero-saturation neutrals are the strongest single differentiator from the current look. Every value is a shipped Tencent token — nothing invented. Risk: `#4582e6` at 4.73:1 is the low end; on `surface1` it drops to 4.13:1, so don't put accent *text* on raised cards, only accent fills/borders.

---

### Candidate B — 字节 Semi 冷中性 (recommended)

| Token | Hex | CR vs bg |
|---|---|---|
| bg | `#16161a` | 1.00 |
| surface1 | `#232429` | 1.17 |
| surface2 | `#35363c` | 1.50 |
| surface3 | `#43444a` | 1.86 |
| border | `#4f5159` | 2.28 |
| border-subtle | `rgba(255,255,255,.08)` | — |
| accent | `#54a9ff` | **7.30** (6.27 on surface1) |
| text 0/1/2/3 | `#f9f9f9` @ 100/80/60/35% | 18.0 |

Why modern: retains a *whisper* of cool tint (240°, 8%) so it doesn't read as flat charcoal, but is 1/3 the saturation of the current bg. Surface steps are larger than TDesign's (lum .008 → .018 → .037 → .058), which reads better on a data-dense table UI where you need card-vs-row separation without borders. This is the Feishu/Douyin-family look, which is what CN audiences currently parse as 现代.

---

### Candidate C — Arco 近中性 + 青 (most differentiated from every other TFT tool)

| Token | Hex | CR vs bg |
|---|---|---|
| bg | `#17171a` | 1.00 |
| surface1 | `#2e2e30` | 1.32 |
| surface2 | `#484849` | 1.96 |
| surface3 | `#5f5f60` | 2.80 |
| border | `#78787a` | 4.06 |
| accent | `#30c9c9` (Arco `dark-cyan-5`) | **8.79** (6.66 on surface1) |

Why modern: cyan is the one accent hue not colonised by either the esports-gold cliché or the generic SaaS blue. Widest surface separation of the four (lum .009 → .028 → .065 → .115) — good if the tool has deep nesting. Caveat: 8.79:1 accent is bright; use it sparingly (links, selected state) or dial to `dark-cyan-4 #1fa6aa` (~5.9:1) for large fills.

---

### Candidate D — Ant Design 深黑 + 紫 (AI/2026 register)

| Token | Hex | CR vs bg |
|---|---|---|
| bg | `#000000` | 1.00 |
| surface1 | `#141414` | 1.14 |
| surface2 | `#1f1f1f` | 1.27 |
| surface3 | `#2b2b2b` | 1.48 |
| border | `#424242` | 2.09 |
| accent | `#9f7aea` violet | **6.45** (5.65 on surface1) |
| text | white @ 85/65/45/25% | 21.0 |

Why modern: violet/purple is the explicit "AI scene" accent ByteDance shipped in Semi (`--semi-color-ai-general`, `--semi-color-ai-purple`) — it's the current CN signal for "smart tool", which is what a TFT analyser is. Pure-black base also wins on OLED. Caveats: surface steps are the *smallest* of the four (lum 0 → .007 → .014 → .024), so a dense table will look flat without explicit borders; and pure black + high-contrast text is the combination CN articles flag for 残像/视觉疲劳 — if the tool is used in long sessions prefer A or B.

---

## 5. Recommendation

**Candidate B (Semi 冷中性) + the shared tier ramp**, with these three changes from the current design:

1. `bg #14171f` → `#16161a`. Saturation 22% → 8%. This alone kills most of the "土".
2. `accent #f4af25` → `#54a9ff`. Frees amber to mean what it means everywhere else in CN systems.
3. Move `#f7c034` (Arco `dark-gold-5`, the closest system-sanctioned relative of the current amber) to **tier B only**. Nothing is lost — the gold survives, demoted to a semantic role.

If the brand is contractually amber: keep it, but apply the measured dark rule — drop it to L≈59 and cut saturation, i.e. `#f7c034` → target ~5–6:1, and use it **only** on ≤5% of pixels (selected row, primary button), with a neutral-gray UI around it. Do not also glow it.

---

## Unresolved

- Could not extract live token values from **飞书/Lark**, **HoYoLAB**, **网易大神**, **小米澎湃 OS**, or **鸿蒙**. Lark/Feishu ships no public design-token repo (CN writing only tells you to F12 the web app); HoYoLAB and 网易大神 are SPAs whose HTML carries no hex. Harmony's dark guidance is documented as a *mechanism* (dark resource dir + 分层参数) with no published hex table. All four gaming/OS references in the brief are therefore **unsourced** in this report rather than guessed.
- No Chinese source found that explicitly names "蓝黑+金 = 过时" as a stated critique. The claim in §0 is **derived** from token evidence (the hue occupies the warning slot; bg saturation is 3x the norm), not quoted from a designer. Treat as inference, strong but mine.
- OKLCH is well-covered in CN writing as *theory*; found no CN design system that actually **ships** OKLCH tokens. All four systems above still ship hex/RGB.
- Whether `#4582e6` (TDesign) or `#54a9ff` (Semi) is the better accent depends on how much accent *text* the UI has — untested against the actual TFT layout.

---

## Sources

- https://github.com/Tencent/tdesign-common/blob/develop/style/web/theme/_dark.less
- https://github.com/DouyinFE/semi-design/blob/main/packages/semi-theme-default/scss/global.scss
- https://github.com/DouyinFE/semi-design/blob/main/packages/semi-theme-default/scss/_palette.scss
- https://github.com/arco-design/arco-design/blob/main/components/style/theme/color/compiled-colors.less
- https://github.com/ant-design/ant-design/blob/master/components/theme/themes/dark/colors.ts
- https://github.com/ant-design/ant-design/blob/master/components/theme/themes/seed.ts
- https://www.uisdc.com/dark-pattern-design — 顶级大厂如何做好暗黑模式设计？Ant Design 规范
- https://www.uisdc.com/dark-mode-adaptation — 如何适配深色模式
- https://www.uisdc.com/group/647088.html — 7组暗色UI配色方案
- https://www.zcool.com.cn/article/ZMTMxNTc4OA== — TDesign暗黑模式适配探索
- https://www.woshipm.com/pd/3318213.html — Google 是如何设计深色模式的
- https://www.woshipm.com/ucd/1729140.html — 色彩变量：饱和度 & 亮度
- https://www.shejidaren.com/gaojigan-peise.html — 配色指南：高级感
- https://zhuanlan.zhihu.com/p/73096322 — Material Design 暗色主题规范
- https://www.biaodianfu.com/oklch/ — OKLCH 色彩模型完全指南
- https://zhuanlan.zhihu.com/p/560489954 — OKLCH 是搭建色彩系统的最佳选择
- https://tdesign.tencent.com/design/dark — TDesign 暗色模式
