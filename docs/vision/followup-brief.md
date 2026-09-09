# Follow-up Brief — TFT_Agent Track B: three corrections after verification

> **Audience:** an implementing agent with no prior context on this repository or on the conversation that produced this document.
> **Repo:** `D:\workspace\TFT_Agent` (Python 3.11+, Windows, PyQt6 overlay for Teamfight Tactics Set 18, Vietnamese client, 1920×1080).
> **Predecessor:** `docs/vision/implementation-brief.md` — the work order that built the HUD reader and the augment vision reader. That work is **done and merged**; the suite is at **708/708 passing**. This document handles what end-to-end verification found afterwards.
> Every number below was measured on this machine. Where a figure is still unmeasured, it says so — do not invent one.

---

## 0. House rules (non-negotiable)

| Rule | Detail |
|---|---|
| **Comments/docstrings in ASCII-folded Vietnamese** | e.g. `# Doc timeout tu Settings`. No diacritics in code comments. |
| **User-facing strings in full Vietnamese** | e.g. `reason="ô 1 còn lượt đổi"` — these reach the overlay. |
| **Never guess a value** | Unreadable → an explicit unresolved state with a `reason` string. Never a silent plausible default. |
| **Every measured constant carries its evidence** | See `src/vision/reroll_buttons.py:99-108` (`ButtonThresholds`) for the pattern: each field commented with the measured gap it sits in. |
| **Config is generated, not hand-edited** | `config/screen_regions*.yaml` comes from `tools/calibrate.py`. (`config/settings.yaml` is hand-edited and is fine to edit.) |
| **Tests 100% offline** | No network, no `data/frames/` dependency (gitignored). Baseline **708/708**. Do not regress. |
| **Surgical diffs** | Touch only what the task requires. |

```powershell
.\.venv\Scripts\python -m pytest -q
```

---

## 1. What verification found

A crash was already fixed before this brief was written: `scripts/advise_from_frame.py` called
`vs.frame(at=…)`, but `VideoFrameSource` (`src/capture/video_source.py:168`) only has `.grab(at)`. That
made `--from-video` mode raise `AttributeError` on every invocation. Both call sites now use `.grab()`.
**No action needed — listed so you do not re-introduce it.** No test caught it because the suite is
offline and never touches `VideoFrameSource`.

Three items remain, and they are this brief's scope.

### Measurements taken

Three runs of `scripts/advise_from_frame.py --frame … --timeout 60 --json`, idle machine:

| Stage | Placeholder currently in code/docs | Measured |
|---|---|---|
| Gemini vision (cards + traits) | 6.0 s timeout | **3.10 / 3.14 / 3.16 s** |
| HUD read, 5 crops | "Ngân sách 300 ms p95" | **1.05 / 1.13 / 1.20 s** |
| Reroll buttons | — | 11–14 ms |

Current §12.1 output from `scripts/run_evaluation.py`:

```
Thuc the                   P       R      F1      n    p50 ms    p95 ms
gold                   0.000   0.000   0.000      0       0.0       0.0
hp                     0.903   0.800   0.848     35     176.1     212.8
level                  0.000   0.000   0.000      0       0.0       0.0
stage                  0.967   0.829   0.892     35     202.9     241.1
xp                     0.000   0.000   0.000      0       0.0       0.0
```

`gold`/`level`/`xp` at n=0 is **correct** — the bottom HUD bar is not rendered during augment selection.
There is no `augment` row at all; Task 3 fixes that.

---

## 2. Task 1 — Wire the `vision:` settings, then set the timeout to 12.0 s

### 2.1 The problem is not the number, it is that the number is unreachable

`config/settings.yaml` currently contains:

```yaml
vision:
  # Nhan dien the augment va toc/he bang Gemini Vision (SPEC 9.1).
  gemini_model: gemini-3.5-flash-lite
  gemini_timeout_s: 6.0
  enable_gemini_vision: true
  vote_window: 5
```

and `src/utils/settings.py:113-127` defines accessors `Settings.gemini_model`,
`.gemini_timeout_s`, `.enable_gemini_vision`, `.vote_window`.

**Nothing reads any of them.** The whole `vision:` block is dead config. The two production call sites
take the module constant instead:

- `scripts/evaluate_recognition.py:62` — `AugmentReader.load(regs)`, no `timeout_s` argument at all.
- `scripts/advise_from_frame.py:79` — `--timeout` argparse default is `DEFAULT_TIMEOUT_S`, imported
  from `src/vision/augment_reader.py`, never from `Settings`.
- `src/vision/frame_reader.py:82-109` — `FrameReader.load()` takes `timeout_s: float = DEFAULT_TIMEOUT_S`
  and does not import `src.utils.settings` at all.

So `src/vision/augment_reader.py:38`'s `DEFAULT_TIMEOUT_S = 6.0` always wins. **Editing only the YAML
would be a silent no-op.** Wire it first, then change the value.

### 2.2 Changes

1. **`src/vision/frame_reader.py`** — `FrameReader.load()` gains `settings: Settings | None = None`.
   When supplied, source `model`, `timeout_s` and `vote_window` from it. Explicit keyword arguments must
   still win, so existing tests can keep injecting values directly:

   ```python
   @classmethod
   def load(cls, regions=DEFAULT_REGIONS, *, settings: Settings | None = None,
            model: str | None = None, timeout_s: float | None = None,
            vote_window: int | None = None, **kw):
       s = settings or Settings.load()
       model = model if model is not None else s.gemini_model
       timeout_s = timeout_s if timeout_s is not None else s.gemini_timeout_s
       vote_window = vote_window if vote_window is not None else s.vote_window
       ...
   ```

2. **Both scripts** call `Settings.load()` and pass it through. `--timeout` / `--model` become genuine
   overrides: argparse default `None`, meaning "take it from settings".

3. **Wire `enable_gemini_vision`** in `AugmentReader.read()`. When false, return the unresolved
   `AugmentReading` that the refusal path already builds, with reason
   `"Gemini Vision đã tắt trong cấu hình"`. No new behaviour — it reuses
   `self._unresolved_reading(...)` (see `src/vision/augment_reader.py:468-478` for the timeout path
   doing exactly this) — and it gives labelling runs and CI an offline switch.

4. **Set 12.0 in all three places so they cannot drift:**
   `config/settings.yaml: vision.gemini_timeout_s`, `src/utils/settings.py: DEFAULTS["vision"]`, and
   `src/vision/augment_reader.py: DEFAULT_TIMEOUT_S`.

   Comment the constant with its evidence, in `ButtonThresholds` style:

   ```python
   # Do duoc 3 lan tren may ranh: 3,10 / 3,14 / 3,16 s. 12,0 = ~4x p50, con
   # chua ~18 s trong dong ho ~30 s cua man chon augment. Nguong 6,0 cu da
   # timeout that o che do --from-video. CHUA do khi game dang chay (SPEC 12.1).
   DEFAULT_TIMEOUT_S = 12.0
   ```

### 2.3 Acceptance

New test: write a settings file under `tmp_path` with `vision.gemini_timeout_s: 0.5`, load it, and
assert `FrameReader.load(settings=…)` hands `0.5` to the `AugmentReader` it constructs. This locks the
wiring so the config cannot silently go dead again.

---

## 3. Task 2 — Correct documentation that measurement contradicts

Text only, no behaviour change.

| Location | Currently says | Change to |
|---|---|---|
| `docs/vision/hud-reader.md:45` | `- **Độ trễ**: Ngân sách 300 ms p95 cho 5 crop HUD khi game đang chạy (SPEC §12.1).` | Measured **1,05–1,20 s** for 5 crops on an idle machine — roughly **3,7×** over the original budget. Keep the SPEC §12.1 note that the real figure must be taken with the game running. |
| `docs/vision/augment-reader.md:41-43` | `…giảm từ 255 lượt gọi xuống còn ~50 lượt trong chu kỳ đánh giá.` | Wrong — see §4.1 below. Replace with: of 255 frames, **169** show all three cards and hold **129** distinct aHash states; the cache is a **single last-value, exact-match** cache (`max_hash_diff=0`, in-process only), so it helps a live loop on a static screen and helps a batch run very little. |
| `docs/vision/augment-reader.md:47` | `…quá hạn ngạch, timeout 6.0s…` | 12.0 s, with the measured 3.1 s p50 that justifies it. |
| `scripts/advise_from_frame.py:7` | `--at 11005` | `--at 4205`. `augment_select_021_011005.png` encodes **HH:MM:SS** (01:10:05), and `data/frames/s7h-jHMpFmQ/manifest.json` confirms `"t": 4205.0`. The predecessor brief misread the filename suffix as seconds and the error was copied into the docstring. |
| `scripts/run_evaluation.py:157` | Prints a caveat about ambiguous augment pairs | That script never evaluates augment today. Print the line only in the mode that actually produces the augment row (Task 3d). |

Also add a short **"Đo được"** section to `docs/vision/augment-reader.md` with the three Gemini timings —
that file currently records no measured latency at all.

Keep the project documentation conventions: one heading per file, **max 100 lines per file**,
kebab-case names, always a `## Related` section of relative links, tables over prose.
`docs/vision/reroll-buttons.md` is the worked example.

---

## 4. Task 3 — Augment labels, and make the §12.1 table show the row

### 4.1 Finding that shapes the labelling

**Cards change within a single augment event.** In `5tshRxYLwv8`, event `(3979.4, 3985.4)`:

| Frame | Slot 2 card title | Slot 2 button state |
|---|---|---|
| `augment_select_021_010620.png` | Cộng Mệt Nghỉ! | `pressed` |
| `augment_select_022_010621.png` | Xúc Xắc Ma Pháp | `disabled` |
| `augment_select_025_010624.png` | Xúc Xắc Ma Pháp | `disabled` |

The player rerolled slot 2 mid-event. Two consequences:

1. **Labels must be per frame**, never per event.
2. The aHash cache is behaving **correctly** — content genuinely changed. Of 255 extracted frames, 169
   show all three cards, holding **129** distinct aHash states. The predecessor brief's "255 → ~50
   calls" claim was wrong; Task 2 corrects the doc that repeated it.

### 4.2 Why there is no `augment` row today

Two independent causes, both need fixing:

- `data/eval/frame_labels.json` holds 35 `stage` and 35 `hp` labels but only **one** non-null `augment`
  entry (`5tshRxYLwv8/…_041_020047.png`).
- `scripts/run_evaluation.py:88-134` hard-codes the five HUD entities and never constructs an
  `AugmentReader`, so it would print no augment row even with complete labels. That also means it
  currently costs **zero** Gemini calls — a property to preserve deliberately, not by accident.

### 4.3 Label schema (already established — follow it exactly)

```json
"data/frames/5tshRxYLwv8/augment_select/augment_select_041_020047.png": {
  "stage": "4-2", "hp": 69, "gold": null, "level": null, "xp": null,
  "augment": ["DA_BoosterPack2", "DA_ClockworkAccelerator", "DA_MaliciousMonetization"],
  "traits": null
}
```

`augment` is a **flat list of exactly 3 apiName strings in slot order**. `traits`, when non-null, is
`dict[str, int]` keyed by apiName. Keys are repo-relative paths. `gold`/`level`/`xp` are `null` on
augment-select frames because the bottom HUD bar is not rendered there.

### 4.4 Labelling method and its honest provenance

Transcribe each card title from the frame, then **validate every transcription against the closed
254-name Set 18 catalog** via `NameIndex.resolve(title, namespace="augments", lang="vi")`
(`src/knowledge/name_index.py:103`). A title that fails to resolve is a transcription error — flag it for
review, never guess. That catalog constraint is what makes these labels far stronger than free-form
model output.

This is **not** an independent human label, and the record must say so. `_meta` gains:

```json
"labeled_by": "chép tay có hỗ trợ + đối chiếu danh mục 254 lõi Set 18, <ngày>",
"augment_label_method": "Đọc tiêu đề thẻ trên khung hình, giải qua NameIndex.resolve(...,'augments','vi'). Tiêu đề không giải được thì đánh dấu để người soát, không đoán.",
"augment_caveat": "Đây KHÔNG phải nhãn người độc lập. Con số augment đo mức ĐỒNG THUẬN giữa Gemini Vision và một bản chép tay đã đối chiếu danh mục."
```

The same caveat goes into the §12.1 caption and into `docs/vision/augment-reader.md`.

### 4.5 Scope: ~60 frames, ~20 per VOD

Stratified to **include** the awkward cases rather than avoid them:

- reroll-transition frames where a card changes mid-event (the §4.1 example is one)
- faded/desaturated confirm frames, where contrast drops
- cursor-occluded titles
- non-augment frames already in the set, which keep `augment: null` — the recognizer must refuse there

Each new frame also gets `stage` and `hp` labels, lifting those entities above n=35. `traits` stays
`null` — see §4.7.

**Tooling to add:** `--card-sheet <out.png>` on `scripts/evaluate_recognition.py`, rendering the three
`card_text_*` crops per frame as a labelled contact sheet. This is how the labels are produced and how a
human spot-checks them. It mirrors the existing `--sheet` flag on `scripts/read_reroll_buttons.py`.
Commit it so the labelling stays reproducible rather than living in a scratch script.

### 4.6 Make `run_evaluation.py` emit the row

Add an opt-in `--with-augment` flag. **Default off**, so the ordinary run stays free of API calls; when
on, construct an `AugmentReader` and add `augment` predictions. Print the ambiguous-pair caveat only in
that mode.

`scripts/evaluate_recognition.py` needs no change to its augment path — it already builds **one
`Prediction` per card per frame** with `ambiguous_pair=len(card.api_names) > 1`. One scoring convention
there must be **documented, not altered** (around line 124):

```python
pred_c = t_card if t_card in card.api_names else card.api_names[0]
```

It credits a hit when the truth apiName is among the returned candidates. That is the correct reading of
SPEC §3.5.4 — surfacing both members of an unrecoverable pair is right behaviour, not an error — but it
does inflate the headline number relative to a strict single-answer metric. Say so where the number is
reported, and read it alongside the separate ambiguous-pair row.

### 4.7 Two latent bugs found in passing

- **`--entities traits` is a silent no-op.** `scripts/evaluate_recognition.py` accepts `traits` into
  `eval_entities` and constructs an `AugmentReader` for it, then builds **no `Prediction` at all** — the
  loop handles only `stage/hp/gold/level/xp` and `augment`. Fix by rejecting `traits` with an explicit
  "chưa hỗ trợ" message. Labelling the traits panel (6–8 traits with counts per frame) is a much larger
  job than three card titles and is **out of scope** here.
- **`tests/test_frame_reader.py:286`** asserts `len(frame_entries) == meta["frames"]`, so `_meta.frames`
  (currently `35`) must be bumped in the same commit as the new labels or the suite breaks. While there,
  add an assertion that a non-null `augment` has exactly 3 entries — today only `list[str]` is checked.

---

## 5. Verification

```powershell
# 1. suite still green and still offline
.\.venv\Scripts\python -m pytest -q

# 2. the timeout is genuinely wired: set vision.gemini_timeout_s to 0.5 in
#    config/settings.yaml, then confirm the refusal message quotes 0.5s, not 6.0s
.\.venv\Scripts\python scripts/advise_from_frame.py --frame data/frames/5tshRxYLwv8/augment_select/augment_select_041_020047.png

# 3. video mode reaches Gemini inside the new budget (this is the run that timed out at 6.0 s)
.\.venv\Scripts\python scripts/advise_from_frame.py --from-video "downloads/midfeed_tpc_final [s7h-jHMpFmQ].mkv" --at 4205

# 4. contact sheet for spot-checking labels by eye
.\.venv\Scripts\python scripts/evaluate_recognition.py --frames-dir data/frames/s7h-jHMpFmQ/augment_select --card-sheet cards.png

# 5. the augment row appears, with its caveat
.\.venv\Scripts\python scripts/run_evaluation.py --with-augment

# 6. the default run still makes zero Gemini calls
.\.venv\Scripts\python scripts/run_evaluation.py
```

**Expected:**
- (2) the refusal reason quotes the timeout taken from the YAML — this is the proof the wiring works.
- (3) completes with `gold`/`level`/`xp` reported as `stale` (carried forward by `GameStateTracker`),
  **not** `never_seen`, and no timeout.
- (5) prints an `augment` row with real support, plus a separate ambiguous-pair row.
- (6) finishes with no network access.

---

## 6. What this work must still not claim

- **The augment F1 measures agreement, not accuracy** — against a catalog-validated transcription, not
  an independent human label. State it in `_meta`, in the §12.1 caption, and in the reader's doc.
- **All latency figures remain idle-machine.** SPEC §12.1 wants them measured with the game running. The
  HUD figure is already 3.7× its original budget and will worsen under load.
- **Still a development-set number.** These are the same frames used to tune thresholds
  (`data/frames/*/manifest.json` records `role: development`). The thesis headline needs the
  self-recorded footage from `research/vanguard/testing-protocol.md` step 3.
- **Traits recognition stays unmeasured.** After this work the `traits` entity refuses loudly instead of
  silently returning nothing — that is the whole of the improvement there.
