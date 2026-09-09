# Implementation Brief — TFT_Agent Track B: HUD Reader + Augment Vision Reader

> **Audience:** an implementing agent with no prior context on this repository.
> **Repo:** `D:\workspace\TFT_Agent` (Python 3.11+, Windows, PyQt6 overlay for Teamfight Tactics Set 18, Vietnamese client, 1920×1080).
> **Read this whole document before writing code.** Every constraint here was verified against the repository or against real extracted video frames. Where a number is unmeasured, it says so explicitly — do not invent one.

---

## 0. House rules for this repository (non-negotiable)

These are conventions the existing code already follows. Violating them will make the change inconsistent with the codebase.

| Rule | Detail |
|---|---|
| **Comments/docstrings in ASCII-folded Vietnamese** | e.g. `# Bo phan loai nay doc ba cai nut`. No diacritics in code comments. |
| **User-facing strings in full Vietnamese** | e.g. `reason="ô 1 còn lượt đổi"` — these reach the overlay, so they keep diacritics. |
| **Never guess a value** | If something cannot be read, return an explicit "unknown/unresolved" state with a `reason` string. Do not fall back to a plausible default silently. This is the single most important rule in this codebase. |
| **Every measured constant carries its evidence** | Thresholds live in a frozen dataclass, each field commented with the measured gap it sits in. See `src/vision/reroll_buttons.py:99-108` for the pattern to copy. |
| **Config files are generated, not hand-edited** | `config/screen_regions*.yaml` is produced by `tools/calibrate.py`. Add coordinates to `SEED_PIXELS` in that tool and re-run it. |
| **Tests are 100% offline** | No network, no `data/frames/` dependency (it is gitignored). Current state: **631/631 passing**. Do not regress this. |
| **Surgical diffs** | Touch only what the task requires. Do not reformat or "improve" adjacent code. |

Run the suite with:
```powershell
.\.venv\Scripts\python -m pytest -q
```

---

## 1. What exists today, and what is missing

The vision layer feeds three independent parameters into one decision call:

```python
Advisor.advise(state: GameState, choices: Sequence[AugmentChoice | str] | None, rerolls: RerollState | None)
```

| Leg | Produces | File | Status |
|---|---|---|---|
| Reroll buttons | `rerolls` | `src/vision/reroll_buttons.py` | **DONE** — 105/105 on hand labels |
| HUD OCR | `state` | `src/vision/hud_reader.py` | **DOES NOT EXIST — build it** |
| Augment vision | `choices` | `src/vision/augment_reader.py` | **DOES NOT EXIST — build it** |

Consequences of the two gaps, all three of which this work closes:
1. `scripts/advise_from_frame.py` requires `--gold`, `--stage`, `--choices` typed by hand.
2. `scripts/run_evaluation.py:88` hard-codes SPEC §12.1 as `{"skipped": "can 200-500 frame gan nhan tay"}`.
3. `docs/augment-reroll/evaluation.md:58` lists `augment_reader` as a blocker for the expert-agreement study.

---

## 2. CRITICAL FINDING — read before designing the HUD reader

**During augment selection, the bottom HUD bar is not rendered by the game.**

Verified directly against extracted region crops:

| Crop | Content |
|---|---|
| `data/frames/s7h-jHMpFmQ/roi/gold/augment_select_021_011005.png` | **blank dark terrain** — no gold digits |
| `data/frames/s7h-jHMpFmQ/roi/stage/augment_select_021_011005.png` | reads `3-2` cleanly |
| `data/frames/s7h-jHMpFmQ/roi/traits/augment_select_021_011005.png` | 6 trait rows, fully legible |

The `gold`, `level`, and `xp` ROIs all sit at `y ≈ 0.817` (pixel y 882–914), inside the bottom bar. That bar is replaced by the full-screen augment overlay.

**Therefore: a single augment-select PNG can never yield gold/level/xp.** Only `stage`, `hp`, and `traits` are on screen.

**Required solution (already decided by the project owner):** build a carry-forward tracker at `src/game_state/state_tracker.py` — a file SPEC §3.3 already names but which does not exist. It keeps the last good gold/level/xp read from earlier planning-phase frames. A single-PNG invocation reports those fields as `never_seen` in a `degraded` list; a video-backed invocation supplies real values.

---

## 3. Decisions already made by the project owner

Do not revisit these. They were chosen deliberately.

1. **gold/level/xp** → carry-forward tracker (`src/game_state/state_tracker.py`).
2. **Traits** → Gemini reads the traits panel in the **same call** as the augment cards. Resolve the Vietnamese trait names to `apiName` through the existing `traits` namespace of `data/name_index.json` (36/36 traits, **0 ambiguous groups**).
3. **When Gemini is unavailable** (missing key / timeout / quota / malformed response) → **refuse and report**. Do NOT fall back to guessing augment names with RapidOCR. Justification in §7.6.
4. **SPEC §12.1 evaluation** → wire it up in this pass; `run_evaluation.py` must stop printing "skipped".

---

## 4. INTERFACE CORRECTION — `choices` must not be `list[str]`

The original task description asked `AugmentReader` to return `choices: list[str]`. **That shape is wrong for this codebase** and you must not implement it as the primary contract.

**Why:** `research/vision-stack/augments.md` measures **5 pairs** of Set 18 augments that are unrecoverable in Vietnamese — identical display name *and* identical icon:

| Pair (`apiName`) | Vietnamese name | Differs by |
|---|---|---|
| `DA_NestingDollsPlus` / `DA_NestingDollsPlusPlus` | Búp Bê Xây Tổ | tier 2 vs 3 |
| `DA_18_FloraFatalisAugment` / `…Plus` | Thực Vật Hấp Thụ | nothing |
| `DA_18_PrimalAugment_Sivir` / `_Nidalee` | Quái Thú Bên Trong | champion granted |
| `DA_18_PrimalAugmentPlus_Sivir` / `_Nidalee` | Quái Thú Bên Trong+ | champion granted |
| `DA_TonsOfStatsI` / `DA_TonsOfStatsII` | (recoverable in EN only, by letter case) | tier 1 vs 2 |

Confirmed live in the data: `data/name_index.json` → `meta.ambiguous_group_counts` = `{"augments": {"en": 5, "vi": 5}}`.

A `list[str]` with one string per card structurally cannot express "these two candidates, we cannot separate them." Collapsing to one is exactly the guess forbidden in writing at `src/knowledge/name_index.py:19`, `src/knowledge/augment_catalog.py:14`, and `src/decision/augment_advisor.py:14`.

**The correct type already exists** at `src/decision/augment_advisor.py:55-79`:

```python
@dataclass
class AugmentChoice:
    api_names: list[str]        # >1 element = a genuinely ambiguous pair
    confidence: float = 1.0
    display_name: str = ""

    @property
    def ambiguous(self) -> bool:
        return len(self.api_names) > 1
```

`AugmentAdvisor.rank()` and `Advisor.advise()` already accept `AugmentChoice`. So:

- **Primary contract:** `AugmentReading.to_choices() -> list[AugmentChoice]`
- **Convenience only:** `AugmentReading.api_names_flat() -> list[str]`, which **raises `AugmentReadError` if any slot is ambiguous**, so the lossy path can never silently drop a candidate.

> Note for the final report: SPEC §3.5.4 says "4 cặp". The measured data says 5. Propose a one-line SPEC correction; do not silently follow the stale number.

---

## 5. Existing code you MUST reuse (do not reimplement)

| What you need | Use this | Location |
|---|---|---|
| ROI rectangles, ratio-based (0..1), resolution independent | `Region`, `ScreenRegions.load/region/crop`, `crop(image, region)` | `src/capture/regions.py` |
| Binarize a crop before OCR (gray → normalize → Otsu → 6× upscale) | `binarize_for_ocr(crop, scale=6)` | `src/vision/preprocess.py:116` |
| Is the HUD bar actually on screen? | `hud_bar_present(crop) -> bool` | `src/vision/preprocess.py:136` |
| Read RapidOCR output safely across SDK versions | `ocr_texts(result)`, `ocr_join(result)`, `has_digit(result)` | `src/vision/preprocess.py:56,106,111` |
| Vietnamese display name → `apiName` | `NameIndex.resolve(text, namespace, lang) -> list[str]`, `.resolve_stem(...)` | `src/knowledge/name_index.py:103,123` |
| Augment tier from apiName/name (name first, icon only as fallback) | `resolve_tier(api, name, icon)` | `src/knowledge/augment_catalog.py:83` |
| Text normalization (NFD + strip Mn + `đ→d` + lowercase) | `normalize(text)` | `src/knowledge/augment_catalog.py:39` |
| Target state object | `GameState` (all fields have safe defaults), `RE_STAGE` | `src/game_state/models.py:17,74` |
| Read `.env` / API keys | `load_env()`, then `os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")` | `src/utils/env.py` |
| Evaluation harness (already written, unused) | `Prediction(entity, predicted, truth, latency_ms, ambiguous_pair)`, `evaluate(preds)` | `src/eval/recognition.py` |
| **Module style to copy exactly** | frozen dataclasses + `reason` strings + `.load()` classmethod + module-local `*Error(RuntimeError)` | `src/vision/reroll_buttons.py` |

**`ScreenRegions` API you will call:**
```python
regions = ScreenRegions.load("config/screen_regions.yaml")
box: Region = regions.region("hud", "gold")          # raises RegionError if missing
crop_img: np.ndarray = regions.crop(frame, "hud", "gold")   # BGR view, no copy
```

**Existing calibrated ROIs** in `config/screen_regions*.yaml`:
```yaml
screens:
  hud:
    stage:  {x: 0.4,      y: 0.00463, w: 0.024479, h: 0.026852}   # px 768,5  → 815,34
    gold:   {x: 0.532292, y: 0.816667, w: 0.01875,  h: 0.025926}   # px 1022,882 → 1058,910
    level:  {x: 0.18125,  y: 0.816667, w: 0.034896, h: 0.02963}
    xp:     {x: 0.236979, y: 0.816667, w: 0.033854, h: 0.02963}
    traits: {x: 0.0,      y: 0.238889, w: 0.123958, h: 0.494444}   # px 0,258 → 238,792
    # ... shop, bench, board, opponents
  augment_select:
    reroll_0: {x: 0.260417, y: 0.772222, w: 0.052083, h: 0.048148} # px 500,834 → 600,886
    reroll_1: {x: 0.473958, ...}                                    # px 910,834
    reroll_2: {x: 0.6875,   ...}                                    # px 1320,834
```
There is **no `hp` ROI** (SPEC §3.1 records HP as `*chưa đo*` — never measured) and **no augment card ROI**. You will add both in Task 1.

---

## 6. Deliverables — five new files, four extended

### New
| File | Role |
|---|---|
| `src/vision/ocr_engine.py` | Lazy-singleton RapidOCR + digit reader. SPEC §3.2 already names this file. |
| `src/vision/hud_reader.py` | HUD ROI crops → typed fields with per-field presence + reason |
| `src/game_state/state_tracker.py` | Carry-forward + multi-frame majority vote. SPEC §3.3 already names this file. |
| `src/vision/augment_reader.py` | Gemini Vision → card titles + traits → `AugmentChoice`. SPEC §3.2/§9.3 name this file. |
| `src/vision/frame_reader.py` | Composition point where the three legs meet |

### Extended
| File | Change |
|---|---|
| `tools/calibrate.py` | Add `SEED_PIXELS["hud"]["hp"]` and `SEED_PIXELS["augment_select"]["card_text_0/1/2"]`, `["cards"]` |
| `scripts/advise_from_frame.py` | Auto-invoke all three readers; CLI flags become overrides; add `--from-video/--at` |
| `scripts/run_evaluation.py` | Replace the hard-coded §12.1 `"skipped"` with a real table |
| `config/settings.yaml` + `src/utils/settings.py` | New `vision:` section |

---

## 7. Tasks

### Task 1 — Measure and add the two missing ROIs

**Do not hand-guess coordinates.** Use the same method that produced the reroll-button geometry: run Canny edge detection over the **255 `augment_select` frames across all three VODs** (`data/frames/{s7h-jHMpFmQ,5tshRxYLwv8,vQDqc9eiDpk}/augment_select/*.png`), take column/row histograms of edge pixels, and confirm all three VODs agree. Then render a contact sheet and confirm by eye.

Add to `tools/calibrate.py:SEED_PIXELS` (pixel coordinates on a 1920×1080 reference frame):

- **`hud.hp`** — the player's own HP box, top-right next to their avatar. Approximately `(1785, 265, 1835, 305)`. **This estimate is from visual inspection only — measure it properly before committing.**
- **`augment_select.card_text_0/1/2`** — the title + description band of each card, roughly `y 515..700`. Card centres are `549.5 / 959.5 / 1369.5` with a **410 px pitch**, identical to the reroll buttons (already proven stable across all three VODs). Excluding the card artwork halves the upload size and removes nothing Gemini needs.
- **`augment_select.cards`** — the union band covering all three cards, for a single composite crop.

Apply with the existing mode (which appends to `generated_by` rather than overwriting provenance):
```powershell
.\.venv\Scripts\python tools/calibrate.py --add-screen --screen augment_select --out config/screen_regions.yaml --validate
.\.venv\Scripts\python tools/calibrate.py --add-screen --screen hud --out config/screen_regions.yaml --validate
```
Repeat for `config/screen_regions.s7h-jHMpFmQ.yaml` and `config/screen_regions.5tshRxYLwv8.yaml` (both tracked in git; `config/screen_regions.yaml` is gitignored).

**Privacy constraint (SPEC §9.1):** the card band and the traits panel contain no summoner names; the top bar and the right-hand player list do. Only cropped bands are ever uploaded to Gemini — **never a full frame**.

**Acceptance:** `--validate` reports no blocker collision for the new regions on all three config files.

---

### Task 2 — `src/vision/ocr_engine.py`

RapidOCR construction cost is **unmeasured anywhere in this repo** (`dev_log.md:494`, `research/open-questions.md:50` both list it as an open TODO). `scripts/qualify_vod.py:216` constructs it once per run with no cache. Constructing per frame would blow the latency budget invisibly — hence a singleton.

```python
class OcrError(RuntimeError): ...

@dataclass(frozen=True)
class DigitRead:
    text: str            # raw joined OCR output, kept for provenance
    value: int | None    # None = did not parse or failed validation
    reason: str

def engine() -> Any:
    """Process-wide lazy singleton. Built once, never on the per-frame path."""

def read_digits(crop: np.ndarray, *, scale: int = DEFAULT_OCR_SCALE,
                call: Callable[[Any], Any] | None = None) -> DigitRead: ...
```

- Construct as `from rapidocr import RapidOCR; ocr = RapidOCR()` (no constructor args — matches `scripts/qualify_vod.py:216`).
- Import lazily inside the function so the rest of the system runs without the OCR package installed.
- `call` is the injection seam so tests never construct a real engine.
- Pipe crops through `binarize_for_ocr()` then `ocr_texts()`. **Never** access `result.txts` directly — `src/vision/preprocess.py:16-22` documents that RapidOCR changes its return schema between major versions and direct access fails silently to empty.

> `research/vision-stack/ocr.md:18` suggests per-digit templates would beat full OCR for these small numerals. **Not doing that:** `src/vision/preprocess.py:3-9` already measured RapidOCR at 98–100% on `gold`/`xp`/`stage` after binarization. Record it as a known optimisation, do not implement it.

---

### Task 3 — `src/vision/hud_reader.py`

```python
HudField = Literal["stage", "gold", "level", "xp", "hp"]

@dataclass(frozen=True)
class FieldRead:
    field: HudField
    value: int | str | None
    raw_text: str
    present: bool          # was there anything on screen to read?
    reason: str
    latency_ms: float

@dataclass(frozen=True)
class HudReading:
    fields: tuple[FieldRead, ...]
    def get(self, field: HudField) -> FieldRead: ...
    @property
    def bar_visible(self) -> bool: ...   # the gold/level/xp group is on screen
    def to_dict(self) -> dict: ...

class HudReadError(RuntimeError): ...

class HudReader:
    @classmethod
    def load(cls, regions: str | Path | ScreenRegions = DEFAULT_REGIONS,
             *, call=None) -> "HudReader": ...
    def read(self, frame: np.ndarray) -> HudReading: ...
```

**Per-field pipeline:** `regions.crop(...)` → `hud_bar_present()` gate → `binarize_for_ocr()` → `read_digits()` → validate.

**Validation bounds (SPEC §3.2 "OCR misread → validation rules"):**

| Field | Rule |
|---|---|
| `gold` | integer 0–999 |
| `level` | integer 1–10 |
| `xp` | integer 0–99 |
| `hp` | integer 0–100 |
| `stage` | must match `models.RE_STAGE` = `^\s*(\d+)\s*-\s*(\d+)\s*$` |

A value failing validation becomes `value=None` with a reason. **Never clamp into range** — a clamped value is a guess wearing a valid costume.

**Error policy:**
- `read()` never raises for an unreadable or absent field — it records `present=False` with a reason.
- `HudReadError` is raised only for structurally broken input: empty frame, or a missing ROI. Validate ROIs **in `__init__`** so a misconfigured file fails at construction, not at the first frame. Copy `RerollButtonReader.__init__` (`src/vision/reroll_buttons.py:215-250`) for this.

`hud_bar_present()` on the `gold` crop is what makes an augment-select frame report `bar_visible=False` cleanly instead of OCR-ing terrain (see §2).

---

### Task 4 — `src/game_state/state_tracker.py`

Solves §2, and is the home for SPEC §3.2's *"Multi-frame sampling (3–5 frames), majority vote"* rule.

```python
@dataclass
class GameStateTracker:
    window: int = 5
    _history: deque[HudReading] = field(default_factory=lambda: deque(maxlen=5))

    def update(self, reading: HudReading) -> None: ...
    def state(self, *, traits: dict[str, int] | None = None) -> GameState: ...
    @property
    def stale(self) -> tuple[str, ...]: ...       # served from an older frame
    @property
    def never_seen(self) -> tuple[str, ...]: ...  # still at GameState defaults
```

Resolution rules per field:
1. Present in the current frame → **majority vote** over the last `window` readings (kills OCR flicker).
2. Absent now, seen before → last good value, and the field name goes into `stale`.
3. Never seen → the `GameState` default (`gold=0`, `level=1`, `xp=0`, `hp=100`, `stage="1-1"`), and the field name goes into `never_seen`.

Callers surface `stale` and `never_seen` in a `degraded` list. **Nothing pretends a default is a real reading.**

---

### Task 5 — `src/vision/augment_reader.py`

```python
@dataclass(frozen=True)
class CardRead:
    slot: int
    title: str                    # verbatim text Gemini returned
    body: str
    api_names: tuple[str, ...]    # 0 = unresolved, 1 = clean, >1 = genuinely ambiguous
    confidence: float
    reason: str

@dataclass(frozen=True)
class AugmentReading:
    cards: tuple[CardRead, ...]
    traits: dict[str, int]        # KEYS ARE apiName, not display text — see below
    source: str                   # "gemini:<model>" | "cache"
    latency_ms: float
    def resolved(self) -> bool: ...
    def to_choices(self) -> list[AugmentChoice]: ...
    def api_names_flat(self) -> list[str]: ...   # raises if any slot is ambiguous
    def to_dict(self) -> dict: ...

class AugmentReadError(RuntimeError): ...

class AugmentReader:
    @classmethod
    def load(cls, regions=DEFAULT_REGIONS, names: NameIndex | str | Path = ...,
             *, model: str = ..., timeout_s: float = ...,
             call: Callable[[bytes], str] | None = None) -> "AugmentReader": ...
    def read(self, frame: np.ndarray) -> AugmentReading: ...
```

#### 5.1 Gemini client

Follow `src/decision/llm_reasoner.py:130-141` **exactly** — it is the established pattern:

```python
def _default_call(self, image_png: bytes) -> str:
    load_env()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("thieu GEMINI_API_KEY")
    from google import genai            # LAZY import, inside the method
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=self.model,
        contents=[PROMPT, types.Part.from_bytes(data=image_png, mime_type="image/png")],
        config={"response_mime_type": "application/json"},
    )
    return getattr(resp, "text", "") or ""
```

- SDK is **`google-genai>=2.20.0`** (pinned in `requirements.txt`). It is **not** `google-generativeai`, which is EOL.
- Default model: **`gemini-3.5-flash-lite`** (matches `src/utils/settings.py` and `LlmReasoner.model`). SPEC §9.1's code sample shows `gemini-2.5-flash-lite` — that sample is stale; follow the settings value.
- **Hard wall-clock timeout** via `ThreadPoolExecutor(max_workers=1)` + `.result(timeout=timeout_s)` — the same mechanism `LlmReasoner.refine` uses. The SDK is synchronous.
- `call` is the injection seam. Tests pass a plain lambda returning canned JSON — see §9.

#### 5.2 One request, one image

Composite the three `card_text_*` crops **and** the `traits` crop into a single labelled image, then make **one** call. Three separate calls would triple latency and cost for no accuracy gain.

#### 5.3 Response schema — keep it flat

SPEC §9.1 warns: *"Giữ schema **phẳng**… Schema sâu có thể bị từ chối."*

```json
{
  "cards":  [{"slot": 0, "title": "Chỉ Một Con Đường II", "body": "Các Tướng nhận được 2% Sức Mạnh Công Kích..."}],
  "traits": [{"name": "Tàn Phá", "count": 2}]
}
```

If the API rejects even this, fall back to two single-list calls. Parse with the brace-scan + `json.loads` pattern from `llm_reasoner._parse` (`src/decision/llm_reasoner.py:117-124`) — malformed output returns `None`, never crashes.

#### 5.4 Resolving card titles → apiName

Follow the matching rules in SPEC §3.2 / `research/vision-stack/ocr.md:48-56`:

1. `NameIndex.resolve(title, namespace="augments", lang="vi")`.
2. Empty result → retry with `NameIndex.resolve_stem(...)` (tier suffix `I`/`II`/`III`/`+`/`++` dropped), lower the confidence, and say so in `reason`.
3. Still empty → `api_names=()` with a reason. **Do not fuzzy-match.**
4. `len(hits) > 1` → keep **all** of them in `api_names`; this becomes an ambiguous `AugmentChoice`.

> **Do NOT copy prior-art fuzzy thresholds.** `research/vision-stack/ocr.md:42-46` measured that `SequenceMatcher >= 0.85` is *actively harmful* here: `chuyen doi nang luong i` vs `…ii` scores **0.979**, and `van cuoc hoang kim+` vs `…++` scores **0.974**. Tier is exactly what must be distinguished.

Tier resolution uses `augment_catalog.resolve_tier()` — **name first, icon path only as fallback**. Reversing that order mis-assigns tier for 19/254 augments.

#### 5.5 Resolving traits → apiName

`NameIndex.resolve(name, namespace="traits", lang="vi")`. Traits have **0 ambiguous groups**, so expect exactly one hit; if more ever appear, record it rather than pick one.

**Emit `apiName` keys, not Vietnamese display text.** This avoids a live bug: `src/decision/scoring/board_fit.py:46-54`'s `trait_key()` strips everything that is not `[a-z]`, so `"Hỏa Ngục"` would collapse to `"hangc"` and never match. `apiName` keys survive that function intact.

#### 5.6 Caching — required, not an optimisation

Gate re-recognition on a perceptual hash (aHash) of the `cards` crop. This is the explicit recommendation at `research/vision-stack/ocr.md:55`: *"gate re-recognition on a perceptual-hash change."*

Two payoffs:
- The three cards are static for the whole ~30 s selection window, so a live loop costs **one** Gemini call per augment screen instead of one per frame.
- It cuts the §12.1 evaluation run from 255 calls to roughly 50 — the frames were extracted 5 per event (`--per-event 5`), so most are duplicates of the same three cards.

#### 5.7 When Gemini is unavailable

Return an `AugmentReading` with empty `api_names` and a `reason` naming the cause (missing key / timeout / quota / malformed JSON). `AugmentReadError` is raised only when a caller demands a value that does not exist — i.e. from `.api_names_flat()` or `.to_choices()`.

> **Deliberate deviation from SPEC §9.3.** That section lists RapidOCR as the fallback for augment names. **Do not implement it.** `docs/vod_pipeline_sop.md:150` measured that **82%** of Set 18 augment names contain at least one stacked-diacritic character absent from the PP-OCRv6 charset (33/35 missing), producing wrong output *even on clean 96 px images* — this is a charset limitation, not an image-quality one. A fallback that is wrong 82% of the time is worse than refusing. Add a one-line SPEC annotation recording this measurement.

---

### Task 6 — `src/vision/frame_reader.py`

```python
@dataclass(frozen=True)
class FrameReading:
    state: GameState
    choices: list[AugmentChoice]
    rerolls: RerollState | None
    degraded: list[str]
    latency_ms: dict[str, float]

class FrameReader:
    @classmethod
    def load(cls, regions=DEFAULT_REGIONS, **kw) -> "FrameReader": ...
    def read(self, frame: np.ndarray, *, tracker: GameStateTracker | None = None) -> FrameReading: ...
```

Mirrors `src/decision/advisor.py`: the single place the vision modules meet, each leg wrapped so one failing degrades only itself. `degraded` carries the tracker's `stale` / `never_seen` entries plus any unresolved card.

---

### Task 7 — Wire `scripts/advise_from_frame.py`

Target behaviour:
```bash
python scripts/advise_from_frame.py --frame <frame.png>
```
runs with **no manual state arguments**.

- `--frame` — single PNG. `stage`/`hp`/`traits`/`choices`/`rerolls` are read for real; `gold`/`level`/`xp` appear in `degraded` as `never_seen`.
- `--from-video <path> --at <t>` — **new mode.** Walks backwards over earlier frames to prime the `GameStateTracker`, so gold/level/xp become real values. This is the mode that demonstrates the complete loop.
- `--gold/--level/--stage/--traits/--choices` are retained as **overrides**. The script must print which values came from pixels and which from flags.
- Keep the existing guards: refuse when the frame is not the augment-select screen; refuse when any reroll slot reads `pressed` or `unknown`.

---

### Task 8 — Benchmark, then set the budgets

Every latency figure in this repo was measured on an idle machine, and **there is no figure at all for Gemini Vision** (SPEC §9.1: *"Chưa đo cho crop nhỏ. Tự benchmark trước khi cam kết ngân sách/frame"*). Ship these as placeholders, then replace them with measurements:

| Stage | Placeholder | Note |
|---|---|---|
| RapidOCR singleton construction | once at startup | must never be on the frame path |
| HUD read (5 crops) | budget 300 ms p95 | measure **with the game running**, per SPEC §12.1 |
| Gemini vision, cache hit | ~0 ms | aHash compare only |
| Gemini vision, cache miss | hard timeout **6.0 s** | of a ~30 s window; refuse rather than block |
| Scoring + reroll policy | ~3 ms p95 | already measured |

Add to `config/settings.yaml` and `src/utils/settings.py:DEFAULTS`:

```yaml
vision:
  gemini_model: gemini-3.5-flash-lite
  gemini_timeout_s: 6.0
  enable_gemini_vision: true
  vote_window: 5
```

Deliberately **separate** from `features.llm_hard_timeout_s: 2.0`, which governs optional explanation refinement that is allowed to vanish entirely. Recognition is on the path and needs its own number.

> **Spec tension — state it, do not hide it.** `src/decision/llm_reasoner.py:3-5` declares: *"LLM khong bao gio nam tren duong quyet dinh co han gio."* That invariant governs **reasoning**. SPEC §9.3 is explicit that the recognizer returns `apiName` + confidence and **never scores** — so ranking stays deterministic, closed-form and LLM-free. Recognition unavoidably precedes scoring. The hard timeout, the aHash cache, and the refuse-don't-guess path are what keep the boundary honest. Document this reasoning in the module docstring.

---

### Task 9 — SPEC §12.1 evaluation

`src/eval/recognition.py` is already written and unused. It expects `Prediction(entity, predicted, truth, latency_ms, ambiguous_pair)` where `entity` is one of `augment`, `champion`, `item`, `gold`, `level`, `hp`, `stage`.

1. **`data/eval/frame_labels.json`** — hand labels per frame for `stage/gold/level/xp/hp/augment/traits`. Follow the exact conventions of the existing `data/eval/reroll_button_labels.json`: repo-relative path keys, a `_meta` block declaring the state alphabet and counts, and labels written **before** looking at any model output.
2. **`scripts/evaluate_recognition.py`** — runs every reader over a frames directory, emits `Prediction` records, calls `evaluate()`, prints the table. Set `ambiguous_pair=True` whenever `AugmentChoice.ambiguous` is true.
3. **`scripts/run_evaluation.py`** — delete the hard-coded `"skipped"` at line 88 and the message at line 106; print the real table when the labels file exists, and keep the honest "chua co frame gan nhan" message when it does not.

**Two limits must be printed with the table, not buried:**
1. These 255 frames are the **development set** (`data/frames/*/manifest.json` records `role: development`) — the same frames used to tune thresholds. SPEC §12.1's headline number requires the self-recorded footage described in `research/vanguard/testing-protocol.md` step 3.
2. The 5 ambiguous Vietnamese pairs get their own row. That is a **data limitation, not a model error** — `recognition.py` already separates them.

---

## 8. Testing

All offline, no network, no `data/frames/` dependency. Current baseline is **631/631 passing** — do not regress it.

| File | Must cover |
|---|---|
| `tests/test_ocr_engine.py` | injected `call`; digit parsing; empty crop raises; singleton constructed only once |
| `tests/test_hud_reader.py` | synthetic HUD crops; **every validation bound** (gold 1000 rejected, level 11 rejected, malformed stage rejected); `bar_visible=False` on a terrain crop; missing ROI raises at construction, not at first read |
| `tests/test_state_tracker.py` | carry-forward; majority vote over a flickering field; `stale` vs `never_seen`; window eviction |
| `tests/test_augment_reader.py` | injected `call` returning canned JSON; ambiguous title → 2 `api_names`; unresolvable title → empty + reason, never a guess; `api_names_flat()` raises on ambiguity; timeout → refuse; malformed JSON → refuse not crash; aHash cache → second `read()` makes **zero** calls; traits resolve to `apiName` |
| `tests/test_frame_reader.py` | composition; one failing leg degrades only itself; `degraded` contents |
| schema test | `data/eval/frame_labels.json` alphabet/count invariants |

**Conventions to follow** (all from `tests/test_reroll_buttons.py`):
- `cv2 = pytest.importorskip("cv2")` at module level.
- Build `ScreenRegions` in memory with `Region.from_pixels(*px, 1920, 1080)` — do not do YAML I/O in logic tests.
- Generate synthetic images programmatically; use `np.random.default_rng(seed)` for reproducible terrain.
- `@pytest.mark.parametrize` over both tracked `config/screen_regions.*.yaml` files to assert the new ROIs exist.

**Mocking pattern — important:** for Gemini, inject a plain callable via the constructor (`AugmentReader(call=lambda img: '{"cards": [...]}')`). This is the pattern used by `LlmReasoner(call=...)` in `tests/test_decision.py`. Do **not** use `unittest.mock.patch`, and do **not** use the `FakeSession`/`FakeResponse` classes from `tests/test_tftacademy.py` — those are reserved for `requests`-based HTTP clients.

---

## 9. Verification

```powershell
# 1. full suite, still fully offline
.\.venv\Scripts\python -m pytest -q

# 2. ROI geometry lands where it should
.\.venv\Scripts\python tools/calibrate.py --validate --screen augment_select --out config/screen_regions.s7h-jHMpFmQ.yaml
.\.venv\Scripts\python tools/calibrate.py --validate --screen hud            --out config/screen_regions.s7h-jHMpFmQ.yaml

# 3. HUD reader against hand labels
.\.venv\Scripts\python scripts/evaluate_recognition.py --frames-dir data/frames/s7h-jHMpFmQ/augment_select --labels data/eval/frame_labels.json --entities stage,hp

# 4. THE TARGET: single command, no manual state args
.\.venv\Scripts\python scripts/advise_from_frame.py --frame data/frames/5tshRxYLwv8/augment_select/augment_select_041_020047.png

# 5. complete loop, tracker primed from the VOD
.\.venv\Scripts\python scripts/advise_from_frame.py --from-video "downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv" --at 11005

# 6. refuse-don't-guess still holds with no API key
$env:GEMINI_API_KEY=""; .\.venv\Scripts\python scripts/advise_from_frame.py --frame <augment frame>

# 7. §12.1 prints a table instead of "skipped"
.\.venv\Scripts\python scripts/run_evaluation.py
```

**Expected results:**
- (4) prints `stage`/`hp`/`traits`/`choices`/`rerolls` read from pixels, with `gold`/`level` listed in `degraded`.
- (5) prints **no** `degraded` entry for `gold`/`level`.
- (6) refuses with an actionable message and a non-zero exit code.
- (7) prints P/R/F1 + p50/p95 per entity, with the ambiguous-pair row reported separately.

A useful ground-truth check for step 4: frame `augment_select_041_020047.png` in the `5tshRxYLwv8` VOD currently reads `rerolls = (True, False, False)`.

---

## 10. Documentation to update on completion

- `docs/vision/overview.md` — the three-leg status table; all three now built
- `docs/vision/hud-reader.md` and `docs/vision/augment-reader.md` — new files, same shape as the existing `docs/vision/reroll-buttons.md` (measured numbers, thresholds with their gaps, stated limits)
- `docs/next-steps.md` §3 — "bước 3" moves from *một phần* to complete
- `SPEC.md` — two one-line corrections: §3.5.4 "4 cặp" → 5 (data says 5); §9.3's RapidOCR fallback annotated with the 82% measurement

**Documentation conventions for this project** — one heading per file; **max 100 lines per file** (split longer content into sibling files); kebab-case filenames, no numbers; always end with a `## Related` section of relative links; prefer tables and code blocks over prose paragraphs. `docs/vision/reroll-buttons.md` is a worked example of all five.

> This brief itself is exempt from the 100-line rule: it is a one-off work order, not reference documentation. Delete it once the work lands.

---

## 11. What this work must NOT claim

State these limits explicitly in the docs rather than letting a reader assume otherwise:

- **No latency claim** until Task 8 is run with the game actually running. Placeholders must be labelled as placeholders.
- **No SPEC §12.1 headline number** from the development set — the table gets printed and captioned as development-set only.
- **No accuracy claim for Gemini Vision** until it is measured against `data/eval/frame_labels.json`.
- **Traits depend on the network** in this design. Offline trait-icon template matching (SPEC §9.2's stated approach) stays a Phase 2 item: it needs 36 trait icons fetched from CommunityDragon, and `data/cdragon_cache/` currently holds only JSON locale files, no images.
