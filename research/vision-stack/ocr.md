# OCR Engine and Matching Rules

> **Verified:** 2026-08-28 against `/latest/` (Set 18 live). PyPI facts re-checked the same day.

The text-recognition half of the [vision stack](overview.md). Headline result unchanged: the language
risk the spec worried about is **not** the real one. But the risk that *is* real has moved — it is not
diacritics and it is not fuzzy thresholds, it is **name collisions**, covered in
[augments.md](augments.md).

## OCR engine

| Engine | Status (2026-08-28) | Decision |
|---|---|---|
| EasyOCR (§4, §6) | Latest **1.7.2, 2024-09-24** — 23 months stale, `requires_python: None`, hard deps on `torch`/`torchvision` ([PyPI](https://pypi.org/pypi/easyocr/json)) | **Replace.** (torch *is* available for 3.14, so it is heavy, not uninstallable) |
| RapidOCR | Latest **3.9.2, 2026-07-21**, `>=3.8,<4`, no torch, no paddlepaddle ([PyPI](https://pypi.org/pypi/rapidocr/json)) | **Adopt** — pinned to **PP-OCRv6**. Its language list includes `vi`; the PP-OCRv5 "latin" list does **not** ([model list](https://rapidai.github.io/RapidOCRDocs/main/model_list/)) |
| Legacy `rapidocr-onnxruntime` | Stale 2025-01, capped `<3.13` | Do not install |

For small fixed-position numerals (gold, level, stage), full OCR is likely the wrong tool — a per-digit
template or tiny classifier is both faster and more accurate. Keep OCR for names and augment text.

## Vietnamese diacritics — measured and REFUTED (re-confirmed on live)

Tested against the real live vocabulary in
[`vi_vn.json`](https://raw.communitydragon.org/latest/cdragon/tft/vi_vn.json): strip every diacritic
(NFD + Mn removal, plus `đ→d`) from both sides and measure collisions.

| Vocabulary (Set 18, live) | Unique | Carry diacritics | Collisions after **total** diacritic loss |
|---|---|---|---|
| Traits | 36 | 35 | **0** |
| Augment names | 249 | 246 | **0** |

The Vietnamese TFT vocabulary stays uniquely resolvable under complete diacritic loss. It only bites if
you compare raw OCR output against **un-normalised** names. A cheap CPU OCR engine remains sufficient.

> ⚠️ **But the language risk is not zero.** Diacritics are refuted; **name collisions are not.** 254
> Set 18 augments collapse to **249** unique Vietnamese names vs **250** in English — Vietnamese is
> marginally *worse*. Four of those pairs are unrecoverable by any method. See
> [augments.md](augments.md). Do not quote "Vietnamese risk refuted" without that qualifier.

## Matching rules — do NOT copy the prior-art thresholds

`jfd02`'s `arena_functions.py` uses `SequenceMatcher.ratio() >= 0.7` (champions, line 66) and `>= 0.85`
(items, line 128). Two researchers recommended lifting these wholesale. **Applied to augments this is
actively harmful:** the overwhelming majority of high-scoring pairs are the same augment at a different
tier — `chuyen doi nang luong i` vs `…ii` at 0.979, `van cuoc hoang kim+` vs `…++` at 0.974. Tier is
exactly what the augment feature must distinguish.

| Rule | Detail |
|---|---|
| Normalise both sides | NFD + Mn removal + `đ→d`, lowercase, before any comparison |
| Split the tier token first | Strip trailing `I` / `II` / `III` / `+` / `++`, fuzzy-match the **stem** only |
| Resolve tier from `apiName`/`name` | **Not** from the icon path — art is reused across tiers and 19/254 paths contradict the name. Full ladder: [augments.md](augments.md) |
| Case-sensitive tiebreak | Lowercasing is mandatory to *find* candidates, but destroys `Tons of Stats!` vs `TONS of Stats!`. Re-compare case-sensitively when >1 candidate survives |
| Constrain the charset | Restrict OCR to characters appearing in this set's names — cheap, high-yield |
| Fuse, don't trust | OCR + HSV histogram match, arbitrated by edit distance; gate re-recognition on a perceptual-hash change |
| Accept ambiguity | Some pairs cannot be separated. Show both, labelled — never guess |

## Latency

Every figure in the corpus is vendor-published, measured on Apple Silicon, or measured on an idle Xeon.
None measures the case that matters: OCR on a 1080p frame **while the game is contending for the same
CPU/GPU** — now an Unreal-rendered game with a higher floor than the Hextech build. Measure it before
committing to a per-frame budget — see [open questions](../open-questions.md).

## Related

- [Augment pipeline](augments.md) — tier ladder, unrecoverable pairs
- [Vision stack overview](overview.md)
- [Research overview](../overview.md) · [Set 18 status & data sources](../set-data.md)
- [Prior art, overlay UI & LLM layer](../prior-art.md) · [Open questions](../open-questions.md)
