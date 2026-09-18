# Gamer-Facing Esports Analytics — Desktop Dark UI Visual System (EN sources)

Date: 2026-09-18. Language: EN. Iterations: 3.
Method note: most hex values below were extracted **directly from the live production CSS/HTML** of each site (curl + regex on their shipped bundles), not from secondary "brand color" blogs. Source URL given per block.

---

## 1. Background / surface / accent / semantic colors — per tool

### 1.1 Blitz.gg — most complete token system found
Source: `https://blitz.gg/_app/immutable/assets/2.B92iJ5G-.css` (fetched 2026-09-18, HTTP 200)

**Mechanism: surfaces are a single HSL ramp `--shade0` … `--shade10`, with a per-game `--hue` and `--saturation`.** Dark surfaces are NOT neutral gray — they carry the game's hue at 14–38 % saturation.

```
--app-bg:      var(--shade9)
--nav-bg:      var(--shade8)
--card-surface:var(--shade7) | --shade8 | --shade9   (varies by theme)
--border-color:var(--shade5) | var(--shade4-50) | var(--shade6-50)
```

Observed theme rows (raw, as shipped):

| theme (`--hue`) | shade5 | shade6 | shade7 | shade8 | shade9 (app bg) | shade10 |
|---|---|---|---|---|---|---|
| 222deg (default) | `222 9% 21%` | `222 14% 15%` | `222 14% 12%` | `222 19% 11%` | `222 20% 10%` | `222 33% 6%` |
| 220deg (saturated) | `220 22% 21%` | `220 33% 17%` | `220 32% 13%` | `220 32% 11%` | `220 34% 9%` | `220 51% 4%` |
| 256deg | `256 25% 22%` | `256 32% 17%` | `256 32% 13%` | `256 31% 11%` | `256 38% 8%` | `256 57% 5%` |
| 168deg | `168 25% 15%` | `168 32% 13%` | `168 31% 11%` | `168 32% 9%` | `168 38% 7%` | `168 61% 4%` |
| 273deg (`--saturation:36%`) | `273 36% 23%` | `273 36% 20%` | `273 36% 16%` | `273 36% 12%` | `273 36% 10%` | `273 36% 7%` |

Converted to hex (default hue 222 row): shade0 `#ebecf0`, shade1 `#999ca3`, shade2 `#898d94`, shade3 `#60646c`, shade4 `#474a52`, shade5 `#31343a`, shade6 `#21242c`, shade7 `#1a1d23`, shade8 `#171a21`, **shade9 `#14171f` (app bg)**, shade10 `#0a0d14`.
Saturated hue-220 row: shade5 `#2a3241`, shade6 `#1d273a`, shade7 `#171e2c`, shade8 `#131925`, shade9 `#0f141f`, shade10 `#05080f`.

**Tier colors (S→F equivalent), exact:**
```
--tier1:    #f4af25   (gold/amber)
--tier2:    #30d9d3   (bright turquoise)
--tier3:    #9dd5d7   (pale turquoise)
--tier4:    #c0d4d8   (near-neutral pale blue)
--tier5:    #585c65   (gray, desaturated = "bad")
--tierNone: #34363d   (surface gray)
```
Note the tier ramp is **NOT** a red→green rainbow. It is *saturation + lightness decay from one accent hue*: only tier1 is a different hue (gold), tiers 2–5 walk turquoise → gray. Bad tiers literally recede into the background.

**Performance / delta scale** (used for stat deltas, parallel to the tier ramp):
```
--perf-pos3:#30d9d3  --perf-pos2:#7ad6d6  --perf-pos1:#9dd5d7
--perf-neutral:#c0d4d8
--perf-neg1:#d4afb4  --perf-neg2:#dc797d  --perf-neg3:#e44e4e
```
Positive = cyan (not green), negative = red, neutral = pale. 7-step, symmetric diverging.

**Rank tiers — two tokens per tier: a fill and a brighter text variant.**
```
--rank-iron:#817678        --rank-iron-text:#a29294
--rank-bronze:#9f6347      --rank-bronze-text:#b97452
--rank-silver:#80989d      --rank-silver-text:#a2c1c7
--rank-gold:#cd8837        --rank-gold-text:#f1a64e
--rank-platinum:#1c91b6    --rank-platinum-text:#14c0f5
--rank-emerald:#519847     --rank-emerald-text:#56d744
--rank-diamond:#8141eb     --rank-diamond-text:#9556ff
--rank-master:#9d48e0      --rank-master-text:#a952e5
--rank-grandmaster:#d94444 --rank-grandmaster-text:#ef4f4f
--rank-challenger:#f4c874  --rank-challenger-text:#f4c874
--rank-none:var(--shade6)  --rank-none-text:var(--shade3)
```
**This is the single most transferable rule found: tier color as *text* is a lighter/more saturated variant than the same tier as a *fill*.** Challenger is the only tier where fill == text.

**TFT placement (top-4 vs bot-4) colors:**
```
--placement-gold-bg:#ffbf50    --placement-gold-bg-dark:#987740
--placement-silver-bg:#a6acb9  --placement-silver-bg-dark:#43474e
--placement-bronze-bg:#9f7956  --placement-bronze-bg-dark:#594533
--placement-fourth-bg:#5d656b  --placement-none-bg:#5d656b
```
Only placements 1/2/3 get a color; 4th and "none" share the same neutral `#5d656b`.

**TFT unit cost colors (directly relevant to a TFT tool):**
```
--cost1:#485767 (gray-blue)  --cost2:#275e4e (green)  --cost3:#3a4894 (blue)
--cost4:#e50dc2 (magenta)    --cost5:#daaa29 (gold)   --cost7:#43dec2 (teal)
```

**Brand / semantic:**
```
--primary-hsl:345deg 100% 48%   (Blitz red ≈ #f50032)
--primary-hsl-hover:352deg 69% 58%
--ad:#ff5757  --ap:#7e88f7      (attack damage / ability power)
--subscriber-solid:oklch(87% .14 73.52)  (premium gold)
--blue:oklch(.7 .25 231.7)  --green:oklch(.8 .28 142.58)  --red:oklch(.69 .26 35.04)
--yellow:oklch(.88 .21 98.5) --purple:oklch(.68 .28 295.3) --turq:oklch(.84 .19 189.8)
--orange:oklch(.72 .24 45.1) --pink:oklch(.73 .25 322.4)   --lime:oklch(.83 .22 129.6)
```
Blitz defines accent hues in **OKLCH with a fixed lightness band (L 0.68–0.88)** — that is how they keep every accent equally readable on dark.

Radii: `--br-sm:2px/3px`, `--br:3px/5px`, `--br-lg:5px/8px`, `--br-xl:7px/16px`. Spacing: `--padding:1.25rem`, `--inset:.5rem`, `--btn-height:2.25rem`.

---

### 1.2 tactics.tools (TFT)
Source: `https://tactics.tools/_next/static/css/38e68521423f9558.css` + page HTML.

- `:root { color-scheme: dark }`; body: `background: var(--primary-1)`, `color: hsla(0,0%,100%,.87)` — **Material-style 87 % white, not #fff**.
- Palette is **Radix Colors**, aliased: `--primary-*` = blue, `--secondary-*` = violet, `--tertiary-*` = teal, each 1→12.
- Dark surfaces: `--primary-1:#0f1720` (app bg), `--primary-2:#0f1b2d`, `--primary-3:#10243e`, `--primary-4:#102a4c`, `--primary-5:#0f3058`, `--primary-6:#0d3868`, `--primary-7:#0a4481`, `--primary-8:#0954a5`.
- Accent / link: `--primary-9:#0091ff`, `--primary-11:#52a9ff` (the actual text-accent used).
- Text ramp: `--white1:#eaf6ff`, `--white2:rgba(234,246,255,.7)`, `--white3:rgba(234,246,255,.45)`.
- Semantic: green `--green-11:#4cc38a`, red `--red-11:#ff6369`, amber `--amber-11:#f1a10d`, yellow `--yellow-11:#f0c000`, teal `--tertiary-11:#0ac5b3`. Medal-ish: `--gold-11:#bfa888`, `--bronze-11:#cba393`.
- Themes are body classes: `body.midnight`, `body.light`; `#app-bg` is a full-bleed background **image** (`s15_midnight2.jpg`) behind translucent cards.
- Interactive accent pattern seen inline: `background-color:rgba(82,169,255,0.08); border:1px solid #52a9ff; color:#52a9ff`.
- Card border: `border:3px solid #202022`, card fill `background-color:#202022`.
- Scrim fills: `#00000050`, `#00000055`, `#11111155`, `#33333377`, `#44444488`.

---

### 1.3 op.gg — largest named token scale
Source: `https://c-lol-web.op.gg/app-router/releases/production-267-1-27f8c8dc/_next/static/css/*.css`

Full 100→900 ramps (all shipped as literal hex):

| ramp | 100 | 300 | 500 | 700 | 900 |
|---|---|---|---|---|---|
| main (brand blue) | `#ECF2FF` | `#B3CDFF` | **`#5383E8`** | `#2F5EC0` | `#28344E` |
| gray | `#F7F7F9` | `#C3CBD1` | `#758592` | `#44515C` | `#202D37` |
| darkpurple | `#CFCFE1` | `#9E9EB1` | `#676678` | `#424254` | **`#1C1C1F`** (+850 `#282830`, 800 `#31313C`) |
| red | `#FFF1F3` | `#FFBAC3` | **`#E84057`** | `#B61337` | `#59343B` |
| green | `#E6F7DB` | `#A8E082` | `#00AE0A` | `#1B7D25` | `#304A1D` |
| blue | `#DDF9FF` | `#52D5F3` | `#0093FF` | `#095BB3` | `#183955` |
| yellow | `#FFF9DB` | `#FFD424` | `#EB9C00` | `#AC6306` | `#4A340E` |
| orange | `#FFF1E6` | `#FCB77A` | `#FF8200` | `#C55900` | `#703100` |
| purple | `#F3EEFF` | `#C0A5FF` | `#7D59EA` | `#5836B2` | `#332353` |
| teal | `#E5FAF3` | `#89DFC4` | `#00BBA3` | `#008889` | `#1D4346` |
| pink | `#FFE4F4` | `#FF9BD2` | `#E537A2` | `#B920B7` | `#5F225E` |
| bronze | `#F6EDE3` | `#D7B792` | `#907659` | `#6B5D4D` | `#3A3734` |

**Dark-mode mechanism:** the `--opggkit-color-*` aliases **invert the scale index** in dark mode — `--opggkit-color-gray-100` = `#f5f7f9` (light) but `#202d37` (dark); `-900` flips the other way. One component stylesheet, two themes, zero per-component dark overrides.

LoL-client-skinned tokens (for the "classic" rune/panel look): `--classic-panel-gray-200:#1c1c1f`, `--classic-panel-gray-0:#31313c`, `--classic-rune-gray-0:#f3e7b8`, `-100:#e5d298`, `-200:#b99a50`, `-250:#8e6a23`, `-500:#6d5a2d`, `-900:#30230f`.

Win/loss convention: win = `--color-main-500 #5383E8` family, loss = `--color-red-500 #E84057` family. (op.gg's signature: **blue = win, red = loss**, not green/red.)

---

### 1.4 lolchess.gg
Source: page HTML + `https://cdn.dak.gg/tft-web/1789716306/_next/static/css/aafd26828dafb164.css`

No named token layer — Tailwind arbitrary hexes. Dominant shipped values by frequency:
- Surfaces: `#161618` (deepest), `#202020`, `#212227`, `#27282e`, `#2d2f37`, `#323232`, `#363944`, `#4c4f5d`.
- Text: `#ffffff`, `#cfd1d7` (primary body), **`#a5a8b4` (muted — highest-frequency color on the page, 32 uses)**, `#666a7a` (disabled), `#848999`.
- Accents: `#fbdb51` (gold — their signature), `#ca9372` (bronze), `#49e049` / `#adff2f` (green), `#11b288` (teal), `#5e73ba` (blue), `#e9e59e` (pale gold), `#ff4655` (Valorant red, cross-brand).
- Font: `Pretendard, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif` (loaded from cdnjs `pretendard/1.3.9`).

---

### 1.5 teamfight.lol — cleanest semantic naming found (TFT augments DB)
Source: `https://teamfight.lol/database/augments` inline critical CSS

```
/* elevation, not "gray-N" */
--Elevation-0: #121018   (app bg)
--Elevation-1: #181620
--Elevation-2: #1e1c28
--Elevation-3: #262332
--Gradient-Elevation-Subtle: linear-gradient(265deg, var(--Elevation-1) 0%, var(--Elevation-0) 100%)
--Gradient-Elevation-Strong: linear-gradient(180deg, var(--Elevation-2) 0%, var(--Elevation-0) 100%)
--Glass-Tint: hsla(0,0%,100%,.04)

/* text as white-alpha, never as gray hexes */
--Text-Primary:    #fff
--Text-Secondary:  hsla(0,0%,100%,.8)
--Text-Tertiary:   hsla(0,0%,100%,.6)
--Text-Quaternary: hsla(0,0%,100%,.4)
--Text-Disabled:   hsla(0,0%,100%,.3)

/* borders as white-alpha too */
--Border-Subtle:  hsla(0,0%,100%,.04)
--Border-Default: hsla(0,0%,100%,.08)
--Border-Medium:  hsla(0,0%,100%,.12)
--Border-Strong:  hsla(0,0%,100%,.16)

/* interactive states = white overlay, hue-free */
--Interactive-Hover:    hsla(0,0%,100%,.08)
--Interactive-Active:   hsla(0,0%,100%,.12)
--Interactive-Disabled: hsla(0,0%,100%,.05)

/* brand */
--Brand-Orange:#f15d3b (hover #e54d2b, active #d63d1b)
--Brand-Yellow:#fcb34a
--Brand-Purple:#8b7fff
--Gradient-Brand-Orange: linear-gradient(243.96deg,#f1bd00 -25.57%,#f15d3b 160.76%)

/* semantic — each is a TRIPLE: solid + 12% bg + 30-40% border */
--Success:#4ade80  --Success-BG:rgba(74,222,128,.12)  --Success-Border:rgba(74,222,128,.3)
--Warning:#fbbf24  --Warning-BG:rgba(251,191,36,.12)  --Warning-Border:rgba(251,191,36,.4)
--Danger: #ef4444  --Danger-BG: rgba(239,68,68,.12)   --Danger-Border: rgba(239,68,68,.3)
--Info:   #3b82f6  --Info-BG:   rgba(59,130,246,.12)  --Info-Border:   rgba(59,130,246,.3)

/* trait tiers */
--Trait-Bronze:#cd7f32  --Trait-Silver:silver  --Trait-Gold:gold  --Trait-Chromatic:linear-gradient(...)

--Overlay-Light:rgba(0,0,0,.3) --Overlay-Medium:rgba(0,0,0,.55) --Overlay-Dark:rgba(0,0,0,.7) --Scrim:rgba(0,0,0,.4)
--Radius-XS .3rem / SM .6rem / MD .8rem / LG 1.2rem / XL 1.6rem / 2XL 2.4rem / Full 9999px
--Shadow-Elevation-0: none
```

---

### 1.6 tftforge.gg — the "League client" skin
Source: `https://tftforge.gg/en/augments/`

Dominant shipped hexes: `#0d1526` and `#10192d` (272 uses each — app bg + card), `#0b1120`, `#121a2d`, `#141b2b`, `#1c2436`, `#31405c` (border), accents `#d5b36a` (239 uses) and `#f4d89b` (121), plus **`#c89b3c`** — Riot's League-client gold. Text `#f8fafc` / `#94a3b8` (Tailwind slate-50/400).
Augment rarity badges here are rendered as **pill + border + uppercase micro-label**, not colored text: `rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.24em]` with `text-slate-200`.

### 1.7 Tracker.gg, Mobalytics, Overwolf — NOT verified
- `tracker.gg`, `app.mobalytics.gg`, `mobalytics.gg/lol`, `brandfetch.com/*`: all return **HTTP 403** (Cloudflare) to both curl and WebFetch. **No first-party hex obtained.** Do not cite secondary "brand color" aggregator blogs for these — they sample the logo, not the UI.
- `overwolf.com` (marketing site, HTTP 200) ships `#131313` as its most frequent dark value, with accents `#b5df30` (lime), `#5de3e2` / `#41c4c3` (cyan), `#fe3737` (red). This is the *marketing* site, not app chrome.
- Overwolf's official developer guidance is **prose only, no palette**: "choose fonts that offer a clear, easy-to-read experience, especially for dense data"; "ensure all UI components … follow a unified visual language"; "avoid semi-transparent widgets or overlays that reduce clarity and game performance." ([Product Guidelines](https://dev.overwolf.com/ow-native/guides/product-guidelines/overview/), [In-game and Overlay Windows](https://dev.overwolf.com/ow-electron/guides/product-guidelines/app-screen-behavior/in-game-overlays/))

---

## 2. How tiers and rarity are color-coded — the actual rules

**Rule A — a tier/rarity color is a *triple*, not a single value.** Two independent confirmations:
- tactics.tools rarity (`:root{--common:#bbb;--uncommon:#14cc73;--rare:#54c3ff;--epic:#de0ebd;--legendary:#ffc430}`) ships each hue at three alphas:
  - text / icon: full opacity (`--rare:#54c3ff`)
  - **border: `e0` alpha** — `.border-[#54c3ffe0]`, `#14cc73e0`, `#de0ebde0`, `#ffc430e0`, `#bbbbbbe0`
  - **badge fill: `22` alpha (≈13 %)** — `.bg-[#6ECCFF22]`, `#37D48822`, `#DC38C322`, `#F1C55522`, `#BBBBBB22`; a `33` variant (20 %) for hover/selected
  - a second brighter set `--*-2` / `--*-3` exists for use *on* the tinted fill (`--rare-2:#6eccff`, `--rare-3:#87d5ff`)
- teamfight.lol does the same with named tokens: `--Success` / `--Success-BG (12%)` / `--Success-Border (30%)`.

**Rule B — tier as text is brighter than tier as fill.** Blitz ships `--rank-X` and `--rank-X-text` as two different hexes for all 10 ranks (e.g. platinum fill `#1c91b6` vs text `#14c0f5`; gold fill `#cd8837` vs text `#f1a64e`). The text variant is consistently higher chroma AND higher lightness.

**Rule C — bad tiers desaturate into the background rather than turning red.** Blitz `--tier5:#585c65` / `--tierNone:#34363d` sit at 2.7:1 and ~1.5:1 against `#14171f`; they are *deliberately* below AA. Only good tiers get to be legible accents. Same at op.gg (`--color-gray-600 #57646F` for muted rows).

**Rule D — placement/medal colors are only assigned to the top 3.** Blitz: gold `#ffbf50`, silver `#a6acb9`, bronze `#9f7956`, each with a `-dark` fill companion (`#987740` / `#43474e` / `#594533` — roughly the same hue at ~40 % lightness, used as the badge background behind the bright text). 4th+ all collapse to `#5d656b`.

**TFT augment rarity (silver / gold / prismatic) — partially resolved:**
- No site exposes a named `--augment-silver/gold/prismatic` token. The nearest first-party-ish values found:
  - teamfight.lol `--Trait-Bronze:#cd7f32; --Trait-Silver:silver; --Trait-Gold:gold; --Trait-Chromatic:linear-gradient(...)` — i.e. they fall back to **CSS named colors** `silver` (`#C0C0C0`) and `gold` (`#FFD700`), and express the top rarity as a **gradient**, not a flat color.
  - Blitz placement metals (`#a6acb9` silver / `#ffbf50` gold / `#9f7956` bronze) are the closest tuned-for-dark versions of the same three metals.
  - tftforge.gg renders `silver` / `gold` / `prismatic` as **uppercase, letter-spaced pill labels with a border**, using slate text — the word carries the meaning, not the hue.
  - tactics.tools ships a 3-stop rainbow gradient inline (`#23e7e3 → #8bf629 → …`) which is the idiom used for "prismatic"-class things generally.
- **Conclusion: prismatic is consistently a gradient/iridescent treatment, silver and gold are flat metals.** Exact Riot in-client hexes were not recoverable from any public source in this pass — see open questions.

**Tier badge geometry observed:** small pill, `border-radius: 9999px` or 3–8px, 1px border at ~30 % of the tier hue, 11–12px uppercase bold text with `letter-spacing: 0.24em`, on a 12–13 % tint of the same hue.

---

## 3. Typography

| Tool | Body | Display / headings | Mono |
|---|---|---|---|
| tactics.tools | `Roboto, Helvetica, Arial, sans-serif` | `Montserrat` (also `Merienda, Montserrat, Roboto` for one decorative use) | `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace` |
| op.gg | `Roboto` (self-hosted, with `Roboto Fallback` metric-matched), `Pretendard` for KR, `Cairo` for AR, `Apple SD Gothic Neo` fallback | same family, weight-differentiated | `ui-monospace, SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace` |
| lolchess.gg | `Pretendard, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif` | same | `ui-monospace, …` |
| teamfight.lol | `--Font-Family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, Helvetica Neue, Arial, Noto Sans` | same | `--Font-Mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace` |
| tftforge.gg | Tailwind default sans | `font-black` (800/900) for headings | — |

Key observations:
- **Nobody uses a "gamer" display font for data.** Roboto / Pretendard / Inter / system-ui. Decorative faces appear only in logos and one-off headers (tactics.tools' `Merienda`).
- **Every single one declares a mono stack**, but as a *token*, not as the numeric default. No site was observed setting `font-variant-numeric: tabular-nums` globally — op.gg only ships Tailwind's `--tw-numeric-*` plumbing, unconfigured on the homepage.
- teamfight.lol's shipped type scale (rem-based, 10px root): `2XS 1rem / XS 1.2 / SM 1.3 / MD 1.4 / LG 1.6 / XL 1.8 / 2XL 2.4 / 3XL 3.0 / 4XL 3.6 / 5XL 4.8` → i.e. **10/12/13/14/16/18/24/30/36/48 px**. Weights: Light 200, Regular 400, Medium 500, Semibold 600, Bold 700, Black 800.
- tactics.tools sets `html{font-size:16px;line-height:16px}` then overrides per component — a deliberate 1:1 base so `rem` maps to px.
- Practical guidance for numeric columns (not from these sites, from typography sources): use `font-variant-numeric: tabular-nums` (OpenType `tnum`) rather than switching families; ~96 % browser support, but **only ~16 % of web fonts actually ship tabular figures** — Inter, IBM Plex Sans, Source Sans Pro, Noto Sans and Lato do. ([DEV: Tabular Numbers in CSS](https://dev.to/alanwest/tabular-numbers-in-css-font-variant-numeric-vs-monospace-hacks-25cn), [MDN font-variant-numeric](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-variant-numeric))

---

## 4. Contrast & accessibility on dark gaming UI

**Never pure black.** Pure `#000` + light text produces *halation* — characters visually bloom/bleed, worse for astigmatic and low-vision users. Recommended floor is `#121212` or the `#0e0e0e`–`#1a1a1a` band; dark navy `#0F172A`–`#1E293B` also cited. Every tool measured here sits in that band: Blitz `#14171f`, tactics.tools `#0f1720`, teamfight.lol `#121018`, op.gg `#1c1c1f`, lolchess `#161618`. ([Smashing: Inclusive Dark Mode](https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/), [ColorContrast dark mode guide](https://www.colorcontrast.org/blog/dark-mode-contrast-accessibility-guide/))

**Never pure white text either.** `#FFFFFF` on `#121212` = 18.7:1, which *overshoots* and drives halation. Use `#E5E7EB` / `#D1D5DB` (13–15:1) for body, `#9CA3AF` (~7.4:1) for secondary. tactics.tools independently implements this as `hsla(0,0%,100%,.87)`; teamfight.lol as `--Text-Secondary: hsla(0,0%,100%,.8)`.

**Target above the legal minimum.** WCAG AA = 4.5:1 normal / 3:1 large; the dark-mode recommendation is **≥7:1 for body** because halation makes perceived readability lag the computed ratio. ([ColorContrast](https://www.colorcontrast.org/blog/dark-mode-contrast-accessibility-guide/), [DubBot](https://dubbot.com/dubblog/2023/dark-mode-a11y.html))

**Light-mode brand colors collapse on dark — you must ship a lighter variant.** Measured examples: `#3B82F6` 4.6:1 on white → **2.3:1** on `#121212`; `#2E7D32` 5.4:1 → 2.8:1; `#D97706` 4.2:1 → 2.0:1. Fix = lift lightness: `#2563EB` → `#60A5FA` (8.2:1). This is exactly what Blitz encodes by pinning every accent to OKLCH L 0.68–0.88, and what op.gg encodes by flipping the 100↔900 index in dark mode.

**Avoid highly saturated / neon accents** — they strain the eye on dark and worsen bloom. ([Smashing](https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/)) Note the observed tools mostly obey this: Blitz's tier ramp is turquoise→gray, not neon; tactics.tools' brightest accent is `#52a9ff`, not `#00f0ff`.

**Elevation is done with lightness, not shadow.** teamfight.lol ships `--Shadow-Elevation-0: none` and expresses depth as `#121018 → #181620 → #1e1c28 → #262332` (4 steps, ~2–3 % L each) plus `--Glass-Tint: hsla(0,0%,100%,.04)`. Blitz uses shade9 → shade8 → shade7. Shadows are near-useless on a dark ground.

**Verified contrast of the palettes collected** (computed, WCAG 2.x, against each tool's own app background):

| foreground | on `#0f1720` (tt) | on `#14171f` (Blitz) | on `#121018` (teamfight) | on `#1c1c1f` (op.gg) |
|---|---|---|---|---|
| `#ffffff` | 18.05 | 17.92 | 18.87 | 17.00 |
| `#e5e7eb` | 14.58 | 14.47 | 15.24 | 13.73 |
| `#c0d4d8` tier4 | 11.73 | 11.65 | 12.26 | 11.05 |
| `#ffc430` legendary | 11.33 | 11.25 | 11.85 | 10.68 |
| `#30d9d3` tier2 | 10.30 | 10.23 | 10.77 | 9.71 |
| `#f4af25` tier1 | 9.46 | 9.39 | 9.89 | 8.91 |
| `#bbbbbb` common | 9.40 | 9.33 | 9.83 | 8.86 |
| `#54c3ff` rare | 9.13 | 9.07 | 9.55 | 8.60 |
| `#14cc73` uncommon | 8.52 | 8.46 | 8.91 | 8.03 |
| `#4cc38a` green-11 | 8.15 | 8.09 | 8.52 | 7.67 |
| `#a5a8b4` lolchess muted | 7.61 | 7.56 | 7.96 | 7.17 |
| `#00bba3` op.gg teal | 7.42 | 7.37 | 7.76 | 6.99 |
| `#52a9ff` tt accent | 7.29 | 7.23 | 7.62 | 6.86 |
| `#9ca3af` | 7.11 | 7.06 | 7.43 | 6.70 |
| `#c89b3c` LoL gold | 7.05 | 7.00 | 7.38 | 6.65 |
| `#ff6369` red-11 | 6.22 | 6.18 | 6.51 | 5.86 |
| `#5383e8` op.gg brand blue | **4.97** | 4.93 | 5.19 | **4.68** |
| `#e84057` op.gg loss red | **4.56** | 4.52 | 4.76 | **4.29** ❌ |
| `#de0ebd` epic magenta | **4.21** | 4.18 | 4.41 | **3.97** ❌ |
| `#585c65` tier5 | **2.69** | 2.67 | 2.82 | **2.54** ❌ |

Takeaways: gold/cyan/pale accents clear AAA easily; **magenta "epic" and the brand blues/reds sit at 4–5:1 — AA-only, and op.gg's own loss red fails AA on its own background.** In practice these are used on *tinted chips* or as large/bold text, not as 12px body copy. `tier5` is intentionally sub-AA.

---

## Directly transferable rules for a desktop dark TFT tool

1. App bg in the `#0f141f`–`#1c1c1f` band, hue-tinted (H≈220°, S 14–36 %), never `#000`.
2. Four surface steps by lightness only (~2–3 % L apart); shadow `none`.
3. Text as white-alpha: 100 / 80 / 60 / 40 / 30 %. Borders as white-alpha: 4 / 8 / 12 / 16 %.
4. Every semantic or tier color ships as a triple: solid text, 30–40 % border, 12–13 % fill.
5. Tier as text = lighter+more chromatic than tier as fill (two tokens per tier).
6. Bad tiers desaturate toward the surface; only good tiers earn chroma.
7. Pin all accents to one OKLCH lightness band (L 0.68–0.88) so they measure ≥7:1 on the app bg.
8. Sans-serif system/Roboto/Inter for all data; mono only as a token; `tabular-nums` for numeric columns.
9. Prismatic/top-rarity = gradient, not a flat hex. Silver/gold = flat metals tuned for dark (`#a6acb9` / `#ffbf50`), not `silver`/`gold` named colors.
10. Rarity/tier badge = pill, 1px hue border, 11–12px uppercase bold, `letter-spacing ≈ 0.24em`.

---

## Unresolved questions

- **Tracker.gg and Mobalytics palettes are unverified** — both hard-block automated fetch (403). Needs a real browser session or a screenshot-and-sample pass.
- **Exact Riot in-client hexes for TFT augment silver/gold/prismatic** were not found in any public CSS or datamined source in this pass. Community sites either use CSS named `silver`/`gold` or their own tuned metals. Community Dragon asset inspection would be the next step.
- **No site was observed actually enabling `tabular-nums`** despite all shipping a mono token — unclear whether they rely on Roboto/Pretendard's default figures (both are tabular-capable) or simply tolerate jitter.
- Blitz's `--cost6` is absent from the bundle fetched (`--cost1..5` and `--cost7` present) — either dead code or defined elsewhere.
- Whether Blitz's per-game `--hue` switching is considered a win by users, or just brand theming, is not documented anywhere public.

## Sources

- https://blitz.gg/_app/immutable/assets/2.B92iJ5G-.css
- https://tactics.tools/ and https://tactics.tools/_next/static/css/38e68521423f9558.css
- https://tactics.tools/augments
- https://www.op.gg/ and https://c-lol-web.op.gg/app-router/releases/production-267-1-27f8c8dc/_next/static/css/{07d5c60628842272,316e2ed5e1bd648f,af57afacd56902b1,e77a762cc18413e3}.css
- https://lolchess.gg/ and https://cdn.dak.gg/tft-web/1789716306/_next/static/css/aafd26828dafb164.css
- https://teamfight.lol/database/augments
- https://tftforge.gg/en/augments/
- https://www.overwolf.com/
- https://dev.overwolf.com/ow-native/guides/product-guidelines/overview/
- https://dev.overwolf.com/ow-electron/guides/product-guidelines/app-screen-behavior/in-game-overlays/
- https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/
- https://www.colorcontrast.org/blog/dark-mode-contrast-accessibility-guide/
- https://dubbot.com/dubblog/2023/dark-mode-a11y.html
- https://www.accessibilitychecker.org/blog/dark-mode-accessibility/
- https://dev.to/alanwest/tabular-numbers-in-css-font-variant-numeric-vs-monospace-hacks-25cn
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-variant-numeric
- https://www.brandcolorcode.com/league-of-legends-lol (secondary — LoL brand gold #C89B3C / navy #0A1428 / silver #A0A7B4)

---

# Blitz layout grammar

All values verbatim from Blitz.gg's shipped SvelteKit CSS, fetched 2026-09-18. Path prefix for every file: `https://blitz.gg/_app/immutable/assets/`. Pages sampled: `/tft/comps`, `/tft/set18/tierlist/augments`, `/tft/set18/tierlist/champions`, `/tft/set18/stats/augments`, `/tft/set18/stats/items`, `/lol/champions/jinx/build`.

## B1. Row / card anatomy

| Thing | Value | Selector to file |
|---|---|---|
| Tier-list gap between tier rows | `gap: .75rem` | `.tier-list-rows` / `TierListGrid.BRUxcMPC.css` |
| Tier row grid | `grid-template-columns: clamp(5.5rem,12cqi,8rem) 1fr; gap:.5rem; min-height:6.25rem; overflow:clip` | `.tier-list-row` / same |
| ...at <=750px container | `grid-template-columns: 4.25rem 1fr; min-height:4.75rem` | `@container tier-list-new` / same |
| ...at <=450px | `grid-template-columns: 1fr; gap:.25rem` | same |
| Tier item grid inside a row | `repeat(auto-fill, minmax(8rem,1fr)); gap:.5rem; padding:.75rem`; augments page overrides to `minmax(10rem,1fr)` | `.tier-row-items` / same; `.tft-augments-tierlist .tier-row-items` / `160.bJTyUeTL.css` |
| Tier item (one augment/unit cell) | `border-radius: var(--br-lg); padding:.5rem; outline-offset:2px; outline-color:#0000` | `.tier-list-item` / same |
| Entity row inner layout (augment) | `display:flex; align-items:center; gap:.25rem` | `.tft-tier-card` / `160.bJTyUeTL.css` |
| Entity row inner layout (champion) | `display:flex; align-items:center; gap:.5rem` | `.tft-tier-card` / `159.C7Q_9GeT.css` |
| Icon size, champion in tier card | `--size: 2.75rem` (44px) | `.tft-tier-card .unit` / `159.C7Q_9GeT.css` |
| Icon size, unit in comp roster | `--size: 3rem`, then `2.5rem` at <=900px, `2.25rem` at <=800px | `.comp-units .unit` / `CompExandable.DjMag4Pi.css` |
| Icon size, overlapped units | `--size: 2rem`, `margin-inline-start:-.5rem`, first child `z-index:2` | `.comp-units.overlap` / same |
| Icon size, item icon | `--size: 2rem` default; `2.25rem` in item detail header | `.item-icon` / `items.lYdbAqCy.css`; `166.Deq53OKl.css` |
| Icon size, trait icon | `--size: 2rem`, inner glyph at `60%` centered | `.trait-icon` / `Trait.C98Su6fN.css` |
| Icon border treatment | `border: 2px solid var(--shade9)` plus `box-shadow: 0 0 0 1px var(--rarity-color)`, `border-radius: var(--br)` | `.image img` / `Unit.CkB-B7Ns.css` |
| Icon rarity plate | container `background: var(--rarity-color)`; `.rarity1..5/7` map to `--cost1..5` | `.image` / same |
| Text block next to icon | `display:grid; min-width:0` plus name `text-overflow:ellipsis; white-space:nowrap; overflow:hidden` | `.tier-item-info` / `.tier-item-name` / `159`,`160` |
| Unit caption name | `width:6ch; font-size:.7rem; color:var(--shade1); text-align:center; text-overflow:ellipsis` | `.name` / `Unit.CkB-B7Ns.css` |
| Comp row (summary) | `padding:1rem; gap:.5rem; display:grid; border-radius: var(--br-xl)` on top corners only; `overflow:clip`; `scroll-margin-block-start:.5rem` | `.comp-summary` / `CompExandable.DjMag4Pi.css` |
| Comp row expanded panel | `background: var(--shade9); border-top:1px solid var(--shade3-15); border-radius: 0 0 var(--br-xl) var(--br-xl); padding:.5rem` | `.comp-details` / same |
| Table row height | `height: var(--row-height)` (set per-table, inline) | `.cell` / `BodyCell.BfgQq-eT.css` |
| Table cell padding | `padding: 0 .75rem`; first/last cell get `var(--padding)` = 1.25rem in cardless mode | `.cell` / same |
| Table header height | `height: 2.25rem; padding-block-start:.25rem; padding-inline:.875rem` | `th` / `Table.BgFJjrGY.css` |
| **Divider treatment** | `border-bottom: 1px solid var(--shade3-15)` on `tbody tr:not(:last-child)` and on `thead tr` | `Table.BgFJjrGY.css` |
| **Zebra striping** | `tbody tr{background:var(--shade8)}`, `:nth-child(odd){background:var(--shade7)}`, `:hover{background:var(--shade6-75)}` | `Table.BgFJjrGY.css` |
| Card ring instead of border | `box-shadow: inset 0 0 0 1px var(--shade3-15)` (tier rows); `0 0 0 1px var(--shade3-15)` (comp header) | `.tier-row-items`; `header` / `CompExandable` |
| Radii tokens | `--br-sm 2px/3px`, `--br 3px/5px`, `--br-lg 5px/8px`, `--br-xl 7px/16px` (two theme variants) | `2.B92iJ5G-.css` |
| Section label with rule-line | label `color:var(--shade1)`, then `&:after{content:""; background:var(--shade5); flex:1; height:1px}` | `.comp-roster-label` / `CompRoster.CtGUEga1.css` |

All breakpoints are **container queries** (`@container (inline-size<=N)`), not media queries. Named containers observed: `tier-list-new`, `comp-container`, `unit-card`, `table-container`, `content-column`, `toolbar-container`, `stats-container`, `web-footer`.

## B2. Metric presentation

| Fact | Value | Selector to file |
|---|---|---|
| **Tabular figures ARE used** | `font-variant-numeric: tabular-nums` on every table body cell | `.cell` / `BodyCell.BfgQq-eT.css` |
| Numeric cells right-aligned | `.cell.stat{ text-align:right; justify-content:flex-end }` | same |
| Stat column min width | `.cell.has-stat-scale{ min-width:5rem; padding-block:.5rem }` | same |
| Cell default text color | `color: var(--shade1)` - numbers are **dimmer than the entity name**, not brighter | same |
| Comp-row stat value | `text-align:center; width:4.5ch` - **fixed character width**, so `4.52` and `58.1%` occupy identical boxes | `.comp-stats-value` / `CompExandable.DjMag4Pi.css` |
| Comp-row stat label | `color: var(--shade2)` (one step dimmer than the value) | `.comp-stats-label` / same |
| Comp-row stat cluster | `.comp-stats-item{text-align:center; display:grid}` (label stacked over value); `.comp-stats{gap:.5rem}` to `1rem` at >=950px; container `gap:2rem` to `1rem` at <=950px | same |
| LoL stat strip | `.stat{flex:1; place-content:center; display:grid; &:not(:last-child){border-right:1px solid var(--shade6)}}`; `.stat-label{text-align:center; color:var(--shade1)}`; `.stat-value{text-align:center; display:block}` | `.champion-stats` / build-page CSS |
| **Stat magnitude bar** (the distinctive bit) | `.stat-scale` is a row of dot-segments under the number: `span{width:6px; height:2px; background:var(--shade4)}`, `span.filled{background:var(--stat-dot-color)}`, `gap:2px`, `position:absolute; bottom:.25rem`, `pointer-events:none` | `.stat-scale` / `BodyCell.BfgQq-eT.css` |
| Inline stat pill (rune win rate) | `background:var(--shade6-50); color:var(--shade1); border-radius:var(--br-lg); padding:.5rem .75rem; gap:1rem` with `.value{color:var(--shade0)}` | `.rune-stats` / build-page CSS |

**Hero metric, partially answered.** Table bodies are client-hydrated (SSR HTML ships no rows; the page loads one `entry/app.*.js` with runtime-split chunks), so literal column order is not statically recoverable. What the CSS does prove about hierarchy:

1. The entity **name** is the brightest element (`--shade0` or `--tier-color`); numbers sit at `--shade1`; labels at `--shade2`. Blitz does **not** make the metric the visually loudest thing.
2. The metric is distinguished by **fixed-width right-alignment + tabular figures + a sub-baseline dot bar** - position and rhythm, not size or color.
3. Only one stat per row gets `.has-stat-scale` / `--stat-dot-color`; that is the de-facto hero metric slot.
4. No `font-size` is declared on `.cell` or `.comp-stats-value` - numbers inherit the row's type class (`type-subtitle--semi` .875rem/500 or `type-callout--semi` .8125rem/500 in observed markup). **The hero metric is not larger than the entity name.**

## B3. Tier / rank pills and tier labels

| Thing | Value | Selector to file |
|---|---|---|
| Tier label cell (S/A/B rail) | `padding: 1.5rem .75rem; display:grid; place-items:center; align-content:start; color:var(--shade9)` - **dark text on the tier color** | `.tier-label` / `TierListGrid.BRUxcMPC.css` |
| Tier label fill | `&:before{ background: radial-gradient(circle at top center, var(--shade0-50), transparent 10rem), var(--tier-color); border-radius:var(--br-xl); opacity:.5; inset:0 }` | same |
| Tier icon inside label | `width: clamp(3rem,7cqi,4rem)`, then `2.75rem` at <=750, `2.25rem` at <=450; `filter: drop-shadow(0 .25rem .5rem #00000047)` | `.tier-icon` / same |
| **Tier row body tint** | `background: color-mix(in hsl, var(--tier-color) 8%, transparent)` | `.tier-row-items` / same |
| Tier item hover | `background: color-mix(in hsl, var(--tier-color) 10%, transparent)`; `outline: 2px solid color-mix(in hsl, var(--tier-color) 20%, transparent)`; `outline-offset:2px` | `.tier-list-item:hover` / same |
| Tier applied to comp name | `.comp-name{ color: var(--tier-color); -webkit-text-stroke:3px var(--shade9); paint-order: stroke fill }` - tier color on **text**, with a dark stroke for legibility | `CompExandable.DjMag4Pi.css` |
| Tier to color binding | `.tier-1{--tier-color:var(--tier1)} .tier-2{--tier-color:var(--tier2)}` etc. | `CompsList.CYqluAoZ.css` |
| Generic uppercase micro-pill | `.type-overline{ font-size:.6875rem; font-weight:600; text-transform:uppercase; letter-spacing:.015rem }` | `2.B92iJ5G-.css` |
| Smallest uppercase label | `.type-mini{ font-size:.6em; font-weight:625; text-transform:uppercase; letter-spacing:.015rem }` | same |
| Tag / meta pill | `background: var(--shade2-15); color: var(--shade0-75); border-radius: var(--br); padding:.125rem .25rem; width:fit-content` | `.leveling-method` / `CompExandable.DjMag4Pi.css` |
| Accent pill ("NEW") | `color: var(--game-color); background: color-mix(in hsl, var(--game-color), transparent 85%); border-radius:var(--br); padding:.125rem .25rem; line-height:1.5` | `.new-badge` / `PageTabs.B3foxWn-.css` |
| Chip-button (filter) | `background: var(--shade5); color: var(--shade1); border-radius: var(--br); padding:.125rem .5rem; font-size:.875rem`; hover `--shade4`/`--shade0`; **active** `background: color-mix(in hsl, var(--green) 15%, transparent); color: var(--green)` | `.game-events button` / `Panel.DqUKKU0D.css` |

**Confirms the fill-vs-text pairing from the color pass.** Tier color is used at four distinct strengths of the same token: (a) 8-10% `color-mix` background, (b) 20% outline, (c) 50%-opacity solid on the tier rail with *dark* (`--shade9`) text on top, (d) full-strength text color on the comp name with a 3px dark text-stroke. Never a flat saturated block behind light text.

Blitz uses **no letter-spaced uppercase pill for tier itself** - tier is an icon in a colored rail plus a tinted row body. Uppercase letter-spacing (`.015rem`) is reserved for group labels and badges.

## B4. Spacing scale and type scale

**Distinct spacing values observed** (rem unless noted). A 0.125rem-based ramp, not a strict 4/8px grid:

`2px`, `3px`, `6px` | `.125` | `.25` | `.375` | `.5` | `.625` | `.75` | `1` | `1.25` | `1.5` | `2` | `2.25` | `2.5` | `3` | `4` | `6.25` | `12`

Most-used: **`.25` / `.5` / `.75` / `1`** - these four cover nearly every gap and padding in list and table components. `1.25rem` is the page gutter (`--padding`); `1.5rem` and above appear only in tier rails, empty states and footers.

Layout tokens (`2.B92iJ5G-.css`): `--padding:1.25rem`, `--inset:.5rem`, `--btn-height:2.25rem`, `--sp-container:66rem`, `--sp-container-gap:1rem`, `--sp-right-rail-ads:300px`, `--transition:.15s ease-out`.

Content column (`ContentColumn.huT-Pg3S.css`): `--padd:1rem` to `.5rem` at <1100px; `max-width: calc(var(--sp-container) + 2*var(--padd))`; `.content-column{ gap:1.25rem }` to `.75rem` at <=750px.

**Type scale**, all in `2.B92iJ5G-.css`. Font is **Inter variable**, forced globally: `*{ font-family: Inter !important }`, self-hosted at `https://blitz-cdn-plain.blitz.gg/blitz/ui/fonts/Inter-VariableFont_slnt,wght.woff2`. Odd weights (525/575/625/650) are variable-axis values, not static cuts.

| class | size | weight | used for (usage count on `/tft/set18/stats/augments`) |
|---|---|---|---|
| `.type-page-header` | 1.375rem (22px) | 650 | page H1 (x1) |
| `.type-page-subheader` | 1.25rem (20px) | 650 | section H2 |
| `.type-title` / `--semi` / `--bold` | 1rem (16px) | 400 / 500 / 600 | entity names, primary row text (x19) |
| `.type-subtitle` / `--semi` / `--bold` | .875rem (14px) | 400 / 500 / 600 | secondary row text, table cells (x7) |
| `.type-form--button`, `.type-form--tab` | .875rem (14px) | 575 | buttons, tabs (x9) |
| `.type-callout` / `--semi` / `--bold` | .8125rem (13px) | 400 / 500 / 600 | dense stats, metadata (x17) |
| `.type-caption` / `--semi` / `--bold` | .75rem (12px) | 400 / 500 / 600 | captions, tooltips (x4) |
| `.type-overline` | .6875rem (11px) | 600, uppercase, `ls .015rem` | group labels (x3) |
| `.type-mini` | .6em (relative) | 625, uppercase, `ls .015rem` | badges over icons |

Only **7 absolute sizes: 11 / 12 / 13 / 14 / 16 / 20 / 22px**. Nothing above 22px anywhere in the data UI. Ad-hoc component sizes are rare and small: `.7rem` (unit caption), `.75rem` (tooltip).

Unit cards use **container-relative type** instead of rem: `.unit-name{font-size:7cqi; font-weight:575}`, `.unit-cost` / `.unit-trait` / `.unit-ability` at `5cqi`, `.unit-info{gap:2cqi; padding:5cqi}` (`Unit.CkB-B7Ns.css`) - the whole card scales as one unit at any width.

## B5. Marking a recommended / best / selected option

No component named `recommended` or `best` exists in the TFT bundles. The emphasis vocabulary is **six reusable patterns**, all `color-mix` tints of a contextual accent, plus outlines:

| Pattern | Exact CSS | Selector to file |
|---|---|---|
| **Accent tint + accent text** (the "this one" marker) | `background: color-mix(in hsl, var(--game-color) 15%, transparent); color: var(--game-color);` hover to `25%` | `.highlight` / `2.B92iJ5G-.css` |
| **Tier-tinted card + outline on hover/focus** | bg `color-mix(in hsl, var(--tier-color) 10%, transparent)`; `outline: 2px solid color-mix(in hsl, var(--tier-color) 20%, transparent)`; `outline-offset:2px` | `.tier-list-item:hover/:focus-visible` / `TierListGrid.BRUxcMPC.css` |
| **Expanded/open row = outline, not fill** | `.comp-container:has(.open){ outline: 2px solid var(--shade4); outline-offset: 2px }` | `CompsList.CYqluAoZ.css` |
| **Attention flash** (jump-to-target) | `@keyframes destination-highlight{ 0%,to{outline:2px solid #0000; outline-offset:.25rem; box-shadow:0 0 #0000} 15%,60%{outline:2px solid var(--primary); outline-offset:.25rem; box-shadow:0 0 .75rem var(--primary-50)} }` - `2.4s ease-out`, once | `.destination-highlight` / `2.B92iJ5G-.css` |
| **Success / confirmed action** | `color: var(--lime); background: color-mix(in hsl, var(--lime) 15%, transparent)` | `.comp-action.copied` / `CompExandable.DjMag4Pi.css` |
| **Premium / paid item** | `color: var(--subscriber-solid); background: color-mix(in hsl, var(--subscriber-solid), transparent 75%); box-shadow: inset 0 0 0 1px color-mix(...)` | `.premium-account-btn` / `2.B92iJ5G-.css` |
| Current tab | 3px x 1.5rem bar, bottom-centred: `&.current:after{ content:""; background: var(--game-color, var(--primary)); width:1.5rem; height:3px; border-radius: var(--br-sm) var(--br-sm) 0 0; position:absolute; bottom:0; left:50%; transform:translate(-50%) }` plus `view-transition-name: page-tab-indicator` | `.page-tab` / `PageTabs.B3foxWn-.css` |
| Active chip | `background: color-mix(in hsl, var(--green) 15%, transparent); color: var(--green)` | `.game-events button.active` / `Panel.DqUKKU0D.css` |

**Rule: emphasis is never a left bar, star, or heavier border.** It is always `accent at 10-25% tint` plus `accent-colored text`, or a `2px` outline at `outline-offset: 2px`. Selection outlines sit *outside* the box so they never shift layout. The recurring tint constant is **15%** (`.highlight`, `.copied`, active chip, `.status.error`, `.games button`).

## B6. Empty / no-data / low-confidence states

| State | Exact CSS | Selector to file |
|---|---|---|
| Generic empty state | `display:flex; flex-direction:column; justify-content:center; align-items:center; gap:.75rem; padding:1.5rem`; description `color:var(--shade2); text-align:center; max-width:50ch` | `EmptyState._usNcRcw.css` |
| Inline table empty | `text-align:center; color: var(--shade1); padding: 2rem` | `.empty` / `166.Deq53OKl.css` |
| Disabled / unavailable | `opacity: .38; pointer-events: none` - the **same `.38`** for disabled tabs, toolbars and buttons | `.page-tab.disabled`, `ul.disabled` / `PageTabs`; `.toolbar-container.disabled` / `FiltersToolbar`; `.button.disabled` / `Button.Bcesx4uc.css` |
| Disabled form control | `opacity: .6; cursor: not-allowed` (inputs use .6, not .38) | `.select-trigger:disabled` / `Select.BhG6RhlE.css` |
| Status / error strip | `text-align:center; background: var(--shade6); border-radius: var(--br); padding:.25rem; margin-block-start:.5rem`; `&.error{ color: var(--red); background: color-mix(in hsl, var(--red) 15%, transparent); padding:.25rem .5rem }` | `.status` / build-page CSS |
| Loading | branded SVG stroke animation: `stroke: var(--c); stroke-width:4px`, `stroke-dasharray`/`stroke-dashoffset` keyframes over `var(--blitz-loading-loop)`, `cubic-bezier(.25,1,.5,1)`, infinite; container `flex column; gap:1rem`; label `font-weight:700` | `Loading.BYKjE5Zt.css` |
| Search placeholder | absolutely positioned at `left:2.75rem; top:50%; translate:0 -50%; white-space:nowrap` (sits behind a typed value) | `.search-placeholder` / `search-results.oy5008nX.css` |
| **Low-confidence / magnitude signal** | the `.stat-scale` dot strip: unfilled `background: var(--shade4)`, filled `background: var(--stat-dot-color)`, `6px x 2px`, `gap:2px`, `bottom:.25rem` | `BodyCell.BfgQq-eT.css` |

**No dedicated "low sample size" class exists.** The `.stat-scale` dot strip is the only quantitative-confidence affordance in the CSS - an always-present N-segment bar where fewer filled dots means a weaker/lower stat. Blitz does not gray out, asterisk, or italicize untrusted numbers; it renders them at normal weight with fewer dots lit.

## B7. Other mechanisms worth copying

| Mechanism | Value | Source |
|---|---|---|
| Scrollbar styling | `scrollbar-width: thin; scrollbar-color: var(--shade6) transparent`; hover to `var(--shade5)`; `scrollbar-gutter: stable` | `.main-content` / `MainContent.CRcBQoJ5.css` |
| Overflow containers hide scrollbars | `scrollbar-width: none` on `.table-container` and `PageTabs ul` | `Table`, `PageTabs` |
| Text over art | `-webkit-text-stroke: 2-4px var(--shade9/--shade10); paint-order: stroke fill` | `.unit-name`, `.unit-trait`, `.comp-name` |
| Decorative art behind a row | `opacity:.2` to `.3` on hover; `width:50%; max-width:24rem`; `mask-image: radial-gradient(80% 50% at 80%, oklch(0% 0 0), #0000)`; `pointer-events:none` | `.carry-bg` / `CompExandable.DjMag4Pi.css` |
| Floating panel / overlay | `background: var(--shade10-75); backdrop-filter: blur(2rem); border:1px solid var(--shade4-15); border-radius: var(--br-xl); box-shadow: 0 0 50px var(--shade10), 0 0 30px 10px var(--shade10-75); padding:.75rem; width:22rem` | `.panel-content` / `Panel.DqUKKU0D.css` |
| Dropdown menu surface | `background: var(--shade9,#151515); border: 1px solid var(--shade6,#2e2e2e); max-height:20rem; z-index:20; overscroll-behavior:contain` | `.select-menu` / `Select.BhG6RhlE.css` |
| Button | `height: var(--btn-height)` (2.25rem; small 2rem, large 3rem); `background: var(--shade6); color: var(--shade1); border-radius: var(--br-lg); padding-inline:.75rem; gap:.25rem`; icon-only to `padding-inline:.5rem`; focus/hover `outline: 2px solid var(--shade0-25); outline-offset:2px`; primary `linear-gradient(155deg, lch(59% 93.6 19.17), oklch(65% .29 24.77))` | `Button.Bcesx4uc.css` |
| Sortable header | `th.sortable{cursor:pointer}`; `th.active{color:var(--shade0)}` and only then is the caret shown (`.caret{display:none}` to `display:block`); `thead.asc .caret{rotate:.5turn}` | `Table.BgFJjrGY.css` |
| Tab strip on a card | inactive `color:var(--shade2)`, border `1px solid transparent`, no bottom border, `translate: 0 1px`; active `color:var(--shade0); background:var(--shade7); border-color:var(--shade4-15)` | `.tab-button` / `CompExandable.DjMag4Pi.css` |
| Alpha token family | every shade has `-15 / -25 / -50 / -75` variants built from `hsla(var(--shadeN-hsl) / a)` | `2.B92iJ5G-.css` |
| Seasonal theming | `body.theme-halloween{ --hue:273deg; --saturation:36% }` re-tints the entire shade ramp from two variables | `2.B92iJ5G-.css` |

## Corrections to the color section above

- **"No site was observed enabling `tabular-nums`" is now WRONG.** Blitz sets `font-variant-numeric: tabular-nums` on every table body cell (`.cell` / `BodyCell.BfgQq-eT.css`).
- Blitz's body font is **Inter**, not a system stack - forced with `*{font-family:Inter!important}`, self-hosted as a variable font from `blitz-cdn-plain.blitz.gg`.

## Still unresolved (layout)

- **Which literal column is the hero metric** (avg placement vs top-4% vs pick%): table bodies are client-hydrated, SSR HTML has no rows, and the page ships one entry bundle with runtime-split chunks. Needs a headless-browser run against `/tft/set18/stats/augments`.
- `--row-height` and `--stat-dot-color` are consumed by `BodyCell` but **set inline by the Svelte component**, so their literal values are not in any CSS file. Same for how many segments `.stat-scale` renders and what threshold fills each.
- No TFT "recommended comp" badge exists in the CSS; whether one is composed at runtime from `.highlight` is unverified.
- `--game-color` is referenced by `PageTabs` and `.highlight` but never defined in the fetched bundles - it is set per game route at a higher level.
- `/tft/augments`, `/tft/items`, `/tft/champions` return 404; the live paths are set-scoped (`/tft/set18/...`).

## Sources (layout pass)

- https://blitz.gg/tft/comps
- https://blitz.gg/tft/set18/tierlist/augments
- https://blitz.gg/tft/set18/tierlist/champions
- https://blitz.gg/tft/set18/stats/augments
- https://blitz.gg/tft/set18/stats/items
- https://blitz.gg/lol/champions/jinx/build
- https://blitz.gg/_app/immutable/assets/{2.B92iJ5G-,TierListGrid.BRUxcMPC,Table.BgFJjrGY,BodyCell.BfgQq-eT,CompExandable.DjMag4Pi,CompsList.CYqluAoZ,CompRoster.CtGUEga1,CompsPage.D_RHFbO7,Unit.CkB-B7Ns,Trait.C98Su6fN,items.lYdbAqCy,Augment.ClOOQXMZ,AugmentImage.CUOiVkUx,EmptyState._usNcRcw,Panel.DqUKKU0D,PageTabs.B3foxWn-,Button.Bcesx4uc,Select.BhG6RhlE,Loading.BYKjE5Zt,MainContent.CRcBQoJ5,ContentColumn.huT-Pg3S,FiltersToolbar.DyY8nAhm,search-results.oy5008nX,159.C7Q_9GeT,160.bJTyUeTL,166.Deq53OKl,168.CjgyUsUj}.css
- https://blitz-cdn-plain.blitz.gg/blitz/ui/fonts/Inter-VariableFont_slnt,wght.woff2
