# Modern Dark Palettes for a TFT Desktop Tool (EN sources)

Scope: palette/color only. All values pulled from shipped CSS / published token packages where possible.
Date: 2026-09-19. Iterations: 9 (search + fetch + evaluate).

---

## 0. Audit of the current palette (why it reads dated)

Converted with the Oklab reference transform (script: `scratchpad/oklch.py`).

| Token | Hex | OKLCH (L%, C, H) |
|---|---|---|
| current surface | `#14171f` | **20.52%, 0.0167, 269** |
| current accent | `#f4af25` | 79.92%, 0.158, 78 |

Two concrete defects vs shipped modern systems:

1. **Chroma 4–6× too high at the surface layer.** Modern base surfaces sit at C ≈ 0.000–0.006. `#14171f` is C = 0.0167 — visibly navy, not "tinted neutral".
   - Vercel `--background-dark-100` `#0a0a0a` → C **0.000** ([geist-colors/background-dark.css](https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/background-dark.css))
   - Linear surface `#0f1011` → C **0.0026** ([designmd.cc/benchmarks/linear](https://designmd.cc/benchmarks/linear))
   - Radix `--slate-1` `#111113` → C **0.0041** ([@radix-ui/colors slate-dark.css](https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/slate-dark.css))
   - Tailwind v4 `zinc-950` `oklch(14.1% 0.005 285.823)` → C **0.005** ([tailwindcss@4/theme.css](https://cdn.jsdelivr.net/npm/tailwindcss@4/theme.css))
2. **Base lightness is one step too high.** L = 20.5% is where modern systems put a *card* (Radix `slate-3` `#212225` = L 20.1%; Tailwind `zinc-900` = L 21%). Modern **bases** sit at L 13.9–17.8%. Result: no room left below for elevation, so depth gets faked with borders/glows.
3. **Hue pairing is the 2016–2019 dashboard cliché.** surface H≈269 (navy) + accent H≈78 (amber) is a near-complementary navy/orange split — the Blitz/Overwolf-era signature.

---

## 1. Current dark product UIs — shipped token values

### 1.1 Vercel Geist — **pure neutral, zero-chroma surfaces**
Source: [`geist-colors` npm package CSS](https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/), mirrors [vercel.com/geist/colors](https://vercel.com/geist/colors).

```
--background-dark-100: #0a0a0a
--background-dark-200: #000
```
Gray dark ramp (HSL lightness, saturation = **0%** at every step):
```
gray-dark-100  hsl(0 0% 10%)   gray-dark-600  hsl(0 0% 53%)
gray-dark-200  hsl(0 0% 12%)   gray-dark-700  hsl(0 0% 56%)
gray-dark-300  hsl(0 0% 16%)   gray-dark-800  hsl(0 0% 49%)
gray-dark-400  hsl(0 0% 18%)   gray-dark-900  hsl(0 0% 63%)
gray-dark-500  hsl(0 0% 27%)   gray-dark-1000 hsl(0 0% 93%)
```
Accent (blue), published in OKLCH:
```
--blue-dark-600:  oklch(64.94% 0.1982 251.81)
--blue-dark-700:  oklch(57.61% 0.2321 258.23)   /* ≈ #0070f3, the interactive blue */
--blue-dark-900:  oklch(71.70% 0.1648 250.79)   /* text-on-dark */
```
Geist also ships an amber ramp in OKLCH — useful reference for "what a *modern* amber looks like":
```
--amber-dark-700: oklch(81.87% 0.1969 76.46)    /* vs current #f4af25 = 79.9% 0.158 78 */
--amber-dark-600: oklch(75.04% 0.1737 74.49)
```
**Verdict: surfaces pure neutral (C=0), single vivid accent, accent carries all chroma.**

### 1.2 Linear — near-neutral with imperceptible blue, iris accent
Source: [designmd.cc/benchmarks/linear](https://designmd.cc/benchmarks/linear)

```
surface primary   #0f1011   (L 17.23%, C 0.0026, H 248)
surface secondary #08090a   (L 13.90%, C 0.0029, H 246)
border primary    #2a2e33
border subtle     #24282c
text primary      #f7f8f8
text secondary    #d0d6e0
text muted        #8a8f98
brand / focus     #5e6ad2   (L 56.74%, C 0.1585, H 275)
accent purple     #8b5cf6
accent red        #eb5757
```
Note: Linear's `#5e6ad2` is essentially Radix `iris-9` `#5b5bd6` (L 54.0%, C 0.184, H 278) — independent confirmation that "indigo/iris ~275°" is the current default product accent.
**Verdict: blue-tinted, but at C 0.003 the tint is sub-perceptual. Accent is functional only (links, focus), never decoration.**

### 1.3 Raycast
Source: [Raycast design-system writeups](https://oh-my-design.kr/design-systems/raycast), [manual.raycast.com/themes](https://manual.raycast.com/themes)
```
Raycast Dark   #151515   (near-neutral)
Raycast Black  #070A0B
brand red      #FF6363
blue accent    ~#55B3FF
```
Theme JSON is a 12-slot schema (background layers, selection, loader, 7 accent tokens); users export via "Copy as JSON".
**Verdict: neutral surfaces, one saturated brand accent.**

### 1.4 Framer
Source: [designmd.cc/benchmarks/framer](https://designmd.cc/benchmarks/framer)
```
bg            #000000
surface       #080808
surface-2     #242424
text          #ffffff / #999999 / #8c8c8c / #666666
accent blue   #0099ff
accent green  #00bb88
```
**Verdict: pure black + pure neutral grays, maximum contrast (20–21:1), two vivid accents used sparingly.**

### 1.5 Warp
Themes are YAML with `name / accent / cursor / background / foreground / details / terminal_colors`; `details: darker` for dark themes. Reference dark bg in the official repo examples: `#0d1117` (L 17.63%, C 0.014, H 258).
Sources: [docs.warp.dev custom-themes](https://docs.warp.dev/terminal/appearance/custom-themes), [warpdotdev/themes](https://github.com/warpdotdev/themes)
**Verdict: user-themed; the ships-by-default direction is a near-neutral ~L 17% base with one accent slot.**

### 1.6 Cursor / Arc / Dia / Superhuman — **not resolved**
No authoritative published token file found in English sources. Cursor inherits VS Code theme JSON (`editor.background` `#181818` for the Cursor-branded community theme). Arc/Dia and Superhuman publish no design tokens. **Do not cite numbers for these.**

### 1.7 Summary table — surface tint across shipped systems

| System | base hex | OKLCH chroma | tint |
|---|---|---|---|
| Vercel Geist | `#0a0a0a` | 0.000 | none |
| Framer | `#000000` / `#080808` | 0.000 | none |
| Radix `gray` | `#111111` | 0.000 | none |
| Linear | `#0f1011` | 0.0026 | blue, sub-perceptual |
| Radix `slate` | `#111113` | 0.0041 | blue, sub-perceptual |
| Tailwind `zinc-950` | `oklch(14.1% .005 285.8)` | 0.005 | violet, sub-perceptual |
| Warp gh-dark | `#0d1117` | 0.014 | blue, perceptible |
| **current (blitz-derived)** | `#14171f` | **0.0167** | **navy, obvious** |
| Tailwind `slate-950` | `oklch(12.9% .042 264.7)` | 0.042 | strong blue (marketing, not app chrome) |

**The modern band is C ≤ 0.006.** "Blue-tinted" in 2026 means 0.003, not 0.017.

---

## 2. Riot / League / TFT client palette

Official Riot front-end CSS documentation mirror: [rcp-fe-lol-documentation — CSS Patterns](https://leonkraim.github.io/rcp-fe-lol-documentation-26.09/css/patterns/)
Full Hextech palette: [league-of-legends-css-styles/demo/colors.html](https://vitorsammarco.github.io/league-of-legends-css-styles/demo/colors.html)

**Backgrounds / greys**
```
HEXTECH BLACK  #010A13   (L 13.85%, C 0.0277, H 240)
BLUE 7         #0A142B
BLUE 6         #0A323C
GREY 4         #1E2328
GREY COOL      #1E282D
GREY 3         #3C3C41
GREY 2         #5B5A56
GREY 1         #A09B8C   (muted text)
GOLD 7         #32281E
```
**Golds**
```
GOLD 1 #F0E6D2   GOLD 4 #C89B3C  (L 71.4%, C 0.123, H 83)  ← primary gold
GOLD 2 #CDBE91   GOLD 5 #785A28
GOLD 3 #C8AA6E   GOLD 6 #463714
```
**Blues / teals**
```
BLUE 1 #CDFAFA   BLUE 4 #0A96AA
BLUE 2 #B2D9DB   BLUE 5 #005A82
BLUE 3 #0AC8B9   (L 74.95%, C 0.131, H 185)  ← hextech teal
```
**Semantic (from Riot FE docs)**
```
success #00B74F   warning #F0B232   error #E84057   info #0AC8B9
border  #3B3B3B   border-light #5B5B5B
text    #FFFFFF   text-muted #A09B8C   text-accent #C89B3C
```

Observations:
- Riot's own base `#010A13` is C 0.0277 — **more** blue-tinted than the current palette. Riot's dark is deliberately "fantasy navy"; copying it reproduces the dated look.
- Riot's gold `#C89B3C` (L 71.4) is *darker and less chromatic* than a modern gold solid (Radix `amber-9` `#FFC53D` = L 85.4, C 0.157). `#C89B3C` on `#010A13` is a ~5:1 pair — legible but muddy on modern displays.
- **Usable-as-is: the teal `#0AC8B9`** (L 74.95, C 0.131) — that lightness/chroma is squarely in the modern accent band and reads contemporary.

**TFT set-specific UI theming: not documented in English sources.** TFT brand identity is described only qualitatively — "vibrant and electrified palette based on core gradient logics, Hextech blue and Chemtech green" ([Long Vu, TFT Brand Identity](https://long.vu/project/tft-id)). No per-set token file exists publicly. Champion-cost tier colors are not published by Riot in any machine-readable form I could find — do not treat community values as canonical.

---

## 3. Modern gaming / esports products

**Weak evidence tier — no published token files exist.** tracker.gg, Faceit, Mobalytics, Overwolf, rivalsmeta.com and rivalstracker.com ship no design-system documentation and no scrapeable token export I could retrieve. Do not cite hex values for these; I found none I can source.

What is documented is the *critique*, and it's consistent:
- The RGB-peripheral aesthetic (Razer/Corsair) bled into web design; esports team sites use neon accents matched to jersey colors — this is now the marker of the genre, not of quality ([muffingroup — esports website design](https://muffingroup.com/blog/esports-website-design/)).
- The advocated correction: *"let dark tones dominate, reserve neon for UI states (active/hover/alerts), use a light neutral for text, avoid multiple neons at full saturation on large blocks."*

**Practical conclusion for a TFT tool: there is no modern gaming product worth deriving a palette from.** The products that read modern in 2026 are the productivity tools (§1). Derive surfaces from Linear/Geist/Radix and borrow only Riot's *teal* or *gold* as the single domain-signalling accent.

---

## 4. Dated vs modern — mechanism-level

| Mechanism | Dated | Modern | Source |
|---|---|---|---|
| **Surface chroma** | Perceptible navy/blue tint (C 0.015–0.045) | Near-neutral, C ≤ 0.006; tint present but sub-perceptual | measured across §1.7 |
| **Base lightness** | Base too light (L ~20%), leaving no elevation headroom | Base L 13.9–17.8%, cards L 20–22%, elevated L 25–27% | [Geist bg-dark `#0a0a0a`](https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/background-dark.css); [Radix slate-dark](https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/slate-dark.css) |
| **Depth mechanism** | Drop shadows + glows on a dark base (shadows are invisible on dark, so glows compensate) | Stepped background luminance: `#09090B` → `#18181B` → `#27272A`; "depth through luminance hierarchy rather than shadows" | [Recursion — UI color trends 2026](https://www.recursion.agency/blog/ui-color-trends-2026) |
| **Pure black / pure white** | `#000000` void + `#FFFFFF` harsh text | `#09090B` base, `#FAFAFA` primary text, `#A1A1AA` secondary, `#71717A` tertiary | same |
| **Accent count** | Multiple saturated accents + gradients competing | One saturated accent at full strength, everything else neutral | [Recursion](https://www.recursion.agency/blog/ui-color-trends-2026); [muz.li mobile 2026](https://muz.li/blog/whats-changing-in-mobile-app-design-ui-patterns-that-matter-in-2026/) |
| **Accent hue pairing** | Complementary navy + amber/orange (Blitz/Overwolf-era dashboard) | Neutral surface + one accent at any hue; no complementary tension with the surface | measured (§0) |
| **Brand color reuse** | Brand hex lifted unchanged from the light-mode brand sheet — high-saturation colors "vibrate aggressively on dark canvases, causing photopic strain and failing contrast audits" | Desaturate brand by 20–30% and *raise* surface luminance for dark mode | [Recursion](https://www.recursion.agency/blog/ui-color-trends-2026) |
| **Neutral family** | Pure `#808080`-family gray "feels dated" | Tinted neutrals — zinc and slate families are the 2026 tech-product standard | [Recursion](https://www.recursion.agency/blog/ui-color-trends-2026) |
| **Color space** | HEX/HSL ramps with uneven perceived lightness between hues | OKLCH ramps — Tailwind v4 moved its entire default palette to OKLCH for perceptual uniformity and P3; Geist publishes a P3 OKLCH block alongside every HSL ramp | [tailwindcss@4/theme.css](https://cdn.jsdelivr.net/npm/tailwindcss@4/theme.css); [geist-colors blue-dark.css](https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/blue-dark.css) |
| **"Gamer neon"** | Multiple neons at full saturation on large blocks, RGB-peripheral aesthetic | Neon reserved for state only (active/hover/alert) | [muffingroup](https://muffingroup.com/blog/esports-website-design/) |

**Note on the apparent contradiction:** one source says "pure gray feels dated, use zinc/slate", while Vercel and Framer ship literally C=0.000 neutrals. Resolution: the dated thing is **mid-gray `#808080` used as a UI color**, not a zero-chroma *ramp*. Both a C=0.000 ramp (Geist) and a C=0.005 ramp (zinc) read modern. What does not read modern is C ≥ 0.015.

---

## 5. Candidate palettes

All five use the same structural rules: base L ≈ 14–18%, three surface steps below L 28%, border from the ramp not from a shadow, **one** accent, OKLCH-uniform tier ramp.

Tier ramps are generated at fixed OKLCH L and C with only hue varying, so no tier "shouts" louder than another — this is the thing a hand-picked hex ramp always gets wrong. All verified in sRGB gamut (script `scratchpad/oklch.py`).

---

### Candidate A — "Geist Void" (from Vercel Geist)
Zero-chroma surfaces, one blue. Reads modern because **all** chroma budget goes to the accent; nothing else competes.

```
bg        #0a0a0a   oklch(14.5%  0     0)       /* --background-dark-100 */
surface1  #131313   oklch(18.5%  0     0)
surface2  #1c1c1c   oklch(22.5%  0     0)
surface3  #252525   oklch(26.5%  0     0)
border    #333333   oklch(32%    0     0)
border-hi #4d4d4d   oklch(42%    0     0)
text      #ededed   oklch(93%    0     0)       /* gray-dark-1000 */
text-2    #a1a1a1   oklch(66%    0     0)
text-3    #707070   oklch(52%    0     0)
accent    #0070f3   oklch(57.61% 0.2321 258.23) /* --blue-dark-700 */
accent-hi #3291ff   oklch(64.94% 0.1982 251.81) /* --blue-dark-600 */
```
Tier ramp (L 0.76 / C 0.14, uniform):
```
T1 #9cb4cd   T2 #5aca94   T3 #40befd   T4 #bf9bfc   T5 #e2a520
```
Risk: zero tint can read "flat / unbranded" on a games tool. Mitigate with accent volume, not surface tint.

---

### Candidate B — "Linear Graphite" (from Linear)
The safest bet. Blue tint at C 0.003 — present in the hand, invisible to the eye. Iris accent.

```
bg        #08090a   oklch(13.90% 0.0029 246)   /* Linear surface-secondary */
surface1  #0f1011   oklch(17.23% 0.0026 248)   /* Linear surface-primary  */
surface2  #17191c   oklch(21%    0.004  248)
surface3  #1f2226   oklch(25%    0.005  248)
border    #24282c   oklch(28%    0.006  248)   /* Linear border-subtle    */
border-hi #2a2e33   oklch(31%    0.007  248)   /* Linear border-primary   */
text      #f7f8f8
text-2    #d0d6e0
text-3    #8a8f98
accent    #5e6ad2   oklch(56.74% 0.1585 275)   /* Linear brand            */
accent-hi #8b5cf6   oklch(60.6%  0.25   293)
```
Tier ramp: same uniform ramp as A (`#9cb4cd #5aca94 #40befd #bf9bfc #e2a520`) — but swap T4 to the accent family so tier-4 and brand agree.

---

### Candidate C — "Slate + Hextech" (Radix slate-dark + Riot teal) — **strongest fit for a TFT tool**
Radix slate is a shipped, contrast-audited 12-step dark scale (C ≈ 0.004). The accent is Riot's own hextech teal `#0AC8B9` — domain-correct, and its L 74.95 / C 0.131 already sits in the modern accent band. Gold demoted to a *secondary* signal so the navy+amber cliché never forms.

Surfaces verbatim from [`@radix-ui/colors` slate-dark](https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/slate-dark.css):
```
bg        #111113   slate-1   (L 17.85%, C 0.0041)
surface1  #18191b   slate-2
surface2  #212225   slate-3
surface3  #272a2d   slate-4
border    #363a3f   slate-6
border-hi #43484e   slate-7
text      #edeef0   slate-12
text-2    #b0b4ba   slate-11
text-3    #696e77   slate-9
accent    #0ac8b9   oklch(74.95% 0.1309 185)   /* Riot BLUE 3 / hextech   */
accent-2  #12a594   radix teal-9  (fill/solid)
accent-hi #0bd8b6   radix teal-11 (text on dark)
gold      #ffc53d   radix amber-9  — status/legendary ONLY, ≤2% of pixels
```
Tier ramp (L 0.78 / C 0.13 uniform, teal-anchored):
```
T1 #acb9c3   T2 #5ad0ac   T3 #41c8f6   T4 #b39dfa   T5 #e3ae28
```
(T4 nudged from `#bda6ff` which clipped sRGB.)

---

### Candidate D — "Zinc / Violet" (Tailwind v4 + Recursion 2026 recommendation)
The literal "2026 standard" per the trend source: zinc neutrals, layered by luminance, `#FAFAFA` text. Violet accent avoids any collision with Riot gold and with in-game team colors.

```
bg        #09090b   oklch(14.08% 0.0044 286)   /* zinc-950 */
surface1  #18181b   oklch(21.03% 0.0059 286)   /* zinc-900 */
surface2  #27272a   oklch(27.39% 0.0055 286)   /* zinc-800 */
surface3  #3f3f46   zinc-700
border    #27272a   zinc-800
border-hi #3f3f46   zinc-700
text      #fafafa   zinc-50
text-2    #a1a1aa   zinc-400
text-3    #71717a   zinc-500
accent    oklch(60.6% 0.25  292.7)   /* violet-500 */
accent-hi oklch(70.2% 0.183 293.5)   /* violet-400, text-on-dark */
```
Tier ramp (Tailwind 400-level, already OKLCH-uniform-ish at L ≈ 0.70–0.83):
```
T1 zinc-400    oklch(70.5% 0.015 286)
T2 emerald-400 oklch(76.5% 0.177 163)
T3 sky-400     ~oklch(74.6% 0.16  232)
T4 violet-400  oklch(70.2% 0.183 294)
T5 amber-400   oklch(82.8% 0.189 84)
```
Note the un-uniformity: amber-400 is 12 L-points brighter than violet-400. If you use Tailwind stock, **re-level tier colors to a common L** or T5 will always dominate.

---

### Candidate E — "Warm Graphite + Modern Gold" (keeps the gold identity, kills the navy)
For the case where the amber accent is non-negotiable. The fix is not the accent — it's removing the blue from the surface and warming it *slightly*, so surface and accent share a hue family instead of opposing it. Directly inverts the §0 defect #3.

```
bg        #0c0a08   oklch(14.5%  0.006 70)
surface1  #141210   oklch(18.5%  0.006 70)
surface2  #1e1b19   oklch(22.5%  0.006 70)
surface3  #272522   oklch(26.5%  0.006 70)
border    #353230   oklch(32%    0.006 70)
border-hi #4f4d4a   oklch(42%    0.006 70)
text      #f5f4f2
text-2    #a8a49e
text-3    #7a7671
accent    #ffc53d   oklch(85.37% 0.1572 84)    /* radix amber-9 — brighter+cleaner than #f4af25 */
accent-2  #ffca16   radix amber-11 (text on dark)
accent-dp #8f6424   radix amber-8  (borders/fills)
```
Tier ramp (L 0.76 / C 0.14 uniform — same as A, warm neutral T1):
```
T1 #b3ada4   T2 #5aca94   T3 #40befd   T4 #bf9bfc   T5 #e2a520
```
Why this reads modern: surface C drops 0.0167 → 0.006; hue moves 269 → 70 so accent and surface are in the same family; accent lightness rises 79.9 → 85.4 giving a cleaner, less muddy gold than both `#f4af25` and Riot's `#C89B3C`.

---

## 6. Recommendation

- **C (Slate + Hextech)** if you want the tool to read as a TFT tool. Teal is Riot-native, shipped-value sourced, and dodges the navy/amber cliché entirely.
- **B (Linear Graphite)** if you want maximum "modern software" signal and don't need the domain cue.
- **E** only if the gold is a brand requirement.
- Avoid A's zero tint if the app has large flat regions; avoid D's stock Tailwind tier ramp without re-levelling.

Cross-cutting rules regardless of choice:
1. Cap surface chroma at **C ≤ 0.006**.
2. Base at **L 14–18%**, three steps to L 27%, borders from the ramp — no shadows, no glows.
3. **One** accent. Gold/teal as status color ≤ 2% of pixels.
4. Tier colors at a **fixed OKLCH L and C**, hue-only variation.
5. Text `#FAFAFA`-class not `#FFFFFF`; base not `#000000` unless following Framer deliberately.

---

## 7. Unresolved

- **Vercel Geist gray-dark OKLCH block not retrieved** — only the HSL lightness steps (saturation 0%). The P3 OKLCH equivalents exist in the package but the gray file returned only the HSL block.
- **Cursor, Arc/Dia, Superhuman** — no published tokens found. Numbers circulating for Cursor are community themes, not shipped defaults.
- **TFT per-set UI theming** — no public token/asset colour manifest found. Community Dragon was not reachable for a colour manifest in this pass; a follow-up should try CDragon raw asset endpoints directly.
- **TFT champion-cost tier colors** — no authoritative Riot source. Every community value I saw was unsourced; the OKLCH-uniform ramps above are a deliberate substitute, not a reproduction.
- **tracker.gg / Faceit / Mobalytics / Overwolf** — zero extractable palettes. Claim "modern gaming products exist worth copying" is **unsupported** by what I could retrieve.
- `gh` CLI unavailable in this environment, so GitHub code-search (Phase 3) was replaced with jsdelivr/raw-CDN fetches of the same packages.

---

## Sources

- https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/background-dark.css
- https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/gray-dark.css
- https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/gray.min.css
- https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/blue-dark.css
- https://cdn.jsdelivr.net/npm/geist-colors@1.0.0/amber-dark.css
- https://vercel.com/geist/colors
- https://github.com/ephraimduncan/geist-colors
- https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/slate-dark.css
- https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/gray-dark.css
- https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/teal-dark.css
- https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/iris-dark.css
- https://cdn.jsdelivr.net/npm/@radix-ui/colors@3.0.0/amber-dark.css
- https://cdn.jsdelivr.net/npm/tailwindcss@4/theme.css
- https://designmd.cc/benchmarks/linear
- https://designmd.cc/benchmarks/framer
- https://www.shadcn.io/design/vercel
- https://manual.raycast.com/themes
- https://oh-my-design.kr/design-systems/raycast
- https://docs.warp.dev/terminal/appearance/custom-themes
- https://github.com/warpdotdev/themes
- https://leonkraim.github.io/rcp-fe-lol-documentation-26.09/css/patterns/
- https://vitorsammarco.github.io/league-of-legends-css-styles/demo/colors.html
- https://www.riotgames.com/en/news/under-hood-league-clients-hextech-ui (404 at time of fetch; indexed via technology.riotgames.com redirect)
- https://nexus.leagueoflegends.com/en-us/2016/12/the-visual-language-of-hextech/
- https://long.vu/project/tft-id
- https://www.recursion.agency/blog/ui-color-trends-2026
- https://muz.li/blog/whats-changing-in-mobile-app-design-ui-patterns-that-matter-in-2026/
- https://muffingroup.com/blog/esports-website-design/
