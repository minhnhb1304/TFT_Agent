# OCR Engine and Matching Rules

The text-recognition half of the [vision stack](overview.md). The headline result: the language risk the
spec worried about is not real, and the risk nobody named is.

## OCR engine

| Engine | Status | Decision |
|---|---|---|
| EasyOCR (§4, §6) | Latest **1.7.2, 2024-09-24** — 23 months stale, `requires_python: None`, hard deps on `torch`/`torchvision` ([PyPI](https://pypi.org/pypi/easyocr/json)) | **Replace.** (Correction to one researcher: torch *is* available for 3.14, so it is heavy, not uninstallable) |
| RapidOCR | Latest **3.9.2, 2026-07-21**, `>=3.8,<4`, no torch, no paddlepaddle ([PyPI](https://pypi.org/pypi/rapidocr/json)) | **Adopt** — pinned to **PP-OCRv6**. Its language list includes `vi`; the PP-OCRv5 "latin" list does **not** ([model list](https://rapidai.github.io/RapidOCRDocs/main/model_list/)) |
| Legacy `rapidocr-onnxruntime` | Stale 2025-01, capped `<3.13` | Do not install |

For small fixed-position numerals (gold, level, stage), full OCR is likely the wrong tool — a per-digit
template or tiny classifier is both faster and more accurate. Keep OCR for names and augment text.

## Vietnamese diacritics — measured and REFUTED

All researchers ranked this the top risk. Tested directly against the real vocabulary in
[`vi_vn.json`](https://raw.communitydragon.org/pbe/cdragon/tft/vi_vn.json): strip every diacritic
(NFD + Mn removal, plus `đ→d`) from both sides and measure collisions.

| Vocabulary | Carry diacritics | Collisions after **total** diacritic loss | Pairs ≥0.85 |
|---|---|---|---|
| Champions (82) | 11 | **0** | 0 |
| Traits (66) | 58 | **0** | 0 |
| Augments (410 unique) | — | **0** | 2 genuinely distinct |

The Vietnamese TFT vocabulary stays uniquely resolvable under complete diacritic loss. It only bites if
you compare raw OCR output against **un-normalised** names. This downgrades §9.2's language risk and makes
a cheap CPU OCR engine sufficient.

## Matching rules — do NOT copy the prior-art thresholds

`jfd02`'s `arena_functions.py` uses `SequenceMatcher.ratio() >= 0.7` (champions, line 66) and `>= 0.85`
(items, line 128). Two researchers recommended lifting these wholesale. **Applied to augments this is
actively harmful:** of 67 augment pairs at ≥0.85, **65 (97%) are the same augment at a different tier** —
`chuyen doi nang luong i` vs `…ii` at 0.979, `van cuoc hoang kim+` vs `…++` at 0.974. 118 of 410 augments
carry a tier suffix, forming 53 tier families. Tier is exactly what the Augment Advisor must distinguish.

| Rule | Detail |
|---|---|
| Normalise both sides | NFD + Mn removal + `đ→d`, lowercase, before any comparison |
| Split the tier token first | Strip trailing `I` / `II` / `III` / `+` / `++`, fuzzy-match the **stem** only |
| Resolve tier by lookup, not by border colour | CDragon icon paths encode it: 499 contain `_ii.`, 275 `_iii.`, 144 `_i.` (e.g. `augments/hexcore/crown_bruiser_iii.tex`); a smaller set names it in words (37 gold, 12 silver, 5 prismatic, 4 bronze) |
| Constrain the charset | Restrict OCR to characters appearing in this set's names — cheap, high-yield |
| Fuse, don't trust | OCR + HSV histogram match, arbitrated by edit distance; gate re-recognition on a perceptual-hash change |

## Latency

Every figure in the corpus is vendor-published, measured on Apple Silicon, or measured on an idle Xeon.
None measures the case that matters: OCR on a 1080p frame **while the game is contending for the same
CPU/GPU**. Measure it before committing to a per-frame budget — see [open questions](../open-questions.md).

## Related

- [Vision stack overview](overview.md)
- [Research overview](../overview.md)
- [Set 18 status & data sources](../set-data.md)
- [Prior art, overlay UI & LLM layer](../prior-art.md)
- [Open questions](../open-questions.md)
