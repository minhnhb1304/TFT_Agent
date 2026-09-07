# Augment Reroll Policy — Plan

Working plan for the sequential augment reroll policy. Superseded by `docs/augment-reroll/*.md`
once implementation lands; kept as the record of what was decided and why.

## Context

`AugmentAdvisor` (`src/decision/augment_advisor.py`) statically ranks the 3 augment cards on
screen. Set 18 gives each slot its own reroll button, so the real decision is a **sequence**:
reroll or pick, and if reroll, which slot. Nothing in the codebase models this — `grep reroll`
finds only the `reroll` *feature category* and the unrelated `SHOP_REFRESH` hotkey.

Goal: a reroll policy that is (a) mathematically derived rather than heuristic, (b) inside the
~30 s / 5 ms latency invariant (SPEC §3.5.3), and (c) additive — `rank()` and the 501 existing
tests must not change.

### Established during planning

**Confirmed empirically** (frame `data/frames/s7h-jHMpFmQ/augment_select/augment_select_023_011007.png`,
stage 3-2): three cards, all **same tier** (gold), **three independent per-slot reroll buttons**
with visually distinct states, and **no numeric reroll counter** anywhere on screen.

**Measured latency** (`.venv`, Python 3.14.7, 50 reps):

| Path | p50 | p95 |
|---|---|---|
| `score_one` × gold tier (N=132) | 1.39 ms | 2.18 ms |
| `score_one` × all 254 | 4.52 ms | 12.24 ms ❌ |
| `rank(3)` (current path) | 0.05 ms | 0.11 ms |

⇒ Scoring **one tier** fits the budget once; all 254 does not. This drives the caching design and
means **no NumPy rewrite is needed**. Pool sizes: tier 1 = 62, tier 2 = 132, tier 3 = 60.

**Confirmed dead end (do not re-litigate):** a live probe of `d3.tft.tools` across all rank groups
and Set 18 patches returns `{"singles": []}` — the HTML column headers are placeholders with no
payload behind them. `dev_log.md` #2 was right. No tactics.tools augment crawl is planned; the
negative result gets recorded in `config/data_sources.yaml` with the probe evidence.

### Assumptions (user-supplied, not publicly verifiable — implemented as named, config-gated, falsifiable)

Research (EN + ZH) could not confirm these from any primary source; wiki/Mobalytics return 403/402.

1. **Burn-on-reveal**: any augment shown (even rerolled away) leaves that player's pool for later
   stages. Stage variants (`X`, `X +`, `X ++`) are distinct; *picking* any variant locks the others.
2. **One reroll per slot**, 3 per stage, no carry-over, no gold cost.
3. All three cards at a stage share one tier (visually confirmed at 3-2 only).

---

## The math

### State and Bellman recursion

Within one augment stage. `L` = best score among slots whose token is spent (safe forever);
`v₍₁₎ ≤ … ≤ v₍ₙ₎` = scores on the `n` slots still holding a token. `F_S` = distribution of
`Score(a | S)` over the tier pool — **not a parametric assumption**: the empirical CDF of scoring
every augment in the tier against the current state.

```
V(L, ∅)            = L
V(L, v₍₁..ₙ₎)      = max( max(L, v₍ₙ₎),                          # PICK
                          E_σ~F_S[ V(max(L,σ), v₍₂..ₙ₎) ] − c )  # REROLL worst
```

The rerolled slot's new value joins `L`; `v₍₁₎` is destroyed. The continuation does not depend on
`v₍₁₎` — **the score of the card you are about to reroll is irrelevant when n ≥ 2.**

### Three results to prove

- **T1 — reroll the worst.** Coupling: rerolling `argmin` retains a set dominating elementwise what
  rerolling any other token slot retains, and `V` is monotone in each argument. Needs slot
  exchangeability.
- **T2 — free rerolls ⇒ exhaust.** If `c = 0` and `n ≥ 2`, REROLL **weakly dominates** PICK: both
  `L` and `v₍ₙ₎` survive, so the post-reroll stop value is ≥ the current one. Early stopping is
  strictly EV-losing. *This is the result that contradicts the naive pro heuristic.*
- **T3 — the single threshold.** With `B = max(L, v₍ₙ₎)`, `R` = floor retained on reroll (`R = B`
  when n ≥ 2; `R = L` when n = 1), and `g(R) = E[max(R,σ)] = R + ∫_R^1 (1−F_S(u))du`:

  ```
  REROLL  ⟺  g(R) − B > c
  ```

  For n ≥ 2 this is `∫_B^1 (1−F_S(u))du > c`, decreasing in `B` ⇒ **single stopping region**, so
  the myopic rule *is* the optimal rule — no threshold schedule needed. `θ*` is the `B` at the flip.

Canonical framing: **McCall sequential search with recall** / Ferguson Ch. 2 house-selling
recursion (<https://www.math.ucla.edu/~tom/Stopping/sr2.pdf>). **Not** the secretary problem
(no-recall, unknown F) and **not** Cayley–Moser (explicitly no-recall). Record that correction.

### Tailoring: `F_S` is a *weighted* empirical CDF, not uniform

Uniform draws over the tier pool violate TFT's trait-tailoring mechanic. The bias has a known
sign: tailoring favours augments matching active board traits, which are exactly the
BoardFit-high ones ⇒ uniform **understates** `E[max]` ⇒ the agent becomes artificially fearful of
rerolling. Fix with one parameter:

```
w_j ∝ 1 + β · 1{ trait_affinity(j) ∩ active_traits(S) ≠ ∅ }
```

`F_S` becomes the `w`-weighted empirical CDF. Costs nothing — weighted suffix sums replace counts,
same O(N) build / O(log N) query. `β = 0` recovers uniform, so it is a clean ablation arm.
Doc note: tailoring is partly *player-controlled* (benching units shrinks the tailored pool —
Dishsoap); the advisor models the passive effect only and must not recommend board manipulation.

### Reroll cost `c` — static matrix, derivation lives in the docs

`c` ships as an **O(1) lookup on (tier, stage)** from `config/scoring_weights.yaml`. No runtime
combinatorics, no `γ` parameter: γ is not independently observable in Set 18 (Riot uses lobby-wide
joint tier tables), and per-decision binomials over N=132 in pure Python is budget risk for a
number that barely moves.

The combinatorial argument stays in `docs/augment-reroll/depletion-cost.md` as the **justification
for the matrix's shape**, not as code. It explains the three regimes:

| Regime | Why | Matrix |
|---|---|---|
| Prismatic (N=60), stage 2-1 | small pool, few S-tier per archetype; burning a good-but-not-best card costs a real future draw | `c > 0` ⇒ early stop can be optimal |
| Gold (N=132) / Silver (N=62) | burning ~1 % of pool | `c ≈ 0` ⇒ exhaust rerolls |
| Any tier, stage 4-2 | no future stage exists | `c ≡ 0` ⇒ always exhaust |

One sharpening the doc must include, because it strengthens the argument: burning a **bad** card
*helps* the future pool. The cost is incurred only in the middle case — the revealed card is good
but not better than `B`, so it is burned unpicked. That is exactly the "second S-tier Prismatic you
can't take" scenario. The matrix values are **user-supplied priors, not measurements**; label them
as such and expose them to ablation.

### Edge cases where T1/T2 fail

Optimal under {exchangeable slots, i.i.d. draws, free rerolls, risk-neutral, exact scores}. Each
failure is an assumption violation:

1. **Non-exchangeable slots** — a Set 14-style themed slot with a different reroll budget breaks T1.
2. **Tailoring** — handled above by the weighted CDF; the residual is the player-controlled part.
3. **Optimizer's curse** — `Base` (w1, 30 % of score) is currently neutral for all 254 because
   `augment_stats.csv` is `MOCK-NOT-REAL`. Under score noise, taking a max over *more* draws
   amplifies selection bias ⇒ the noisy-optimal policy rerolls **less** than the noise-free one.
   Document the shrinkage term; do not silently ship one.
4. **Cross-stage augments** — `Augmented Power` (next augment one tier higher) and `Reroll Transfer`
   (each unused reroll → 3 shop rerolls + 3 gold) break within-stage separability. The latter makes
   unused rerolls genuinely valuable.
5. **Ambiguous recognition** — 5 indistinguishable pairs (`research/vision-stack/augments.md`).
6. **HP double-counting** — `TempoFit` already maps HP → augment value (`low_hp=35`, `high_hp=70`);
   adding HP to `θ*` counts it twice. The sign is also contested: at low HP with a losing board the
   placement payoff is convex ⇒ risk-*seeking*, the opposite of "risk-averse when HP ≤ 30". Keep HP
   in `TempoFit`; expose one `risk_lambda` defaulting to 0 (risk-neutral) as an ablation arm.

---

## Implementation

### New files

| File | Contents |
|---|---|
| `src/decision/reroll_policy.py` | `RerollState`, `PoolDistribution`, `RerollAdvice`, `RerollPolicy` |
| `src/eval/reroll_ablation.py` | Monte-Carlo counterfactual + analytic ceiling |
| `config/data_sources.yaml` | Sources registry, incl. recorded negative results |
| `tests/test_reroll_policy.py`, `tests/test_reroll_ablation.py` | Tests |
| `docs/augment-reroll/*.md` | Written analysis |

### Data contract

```python
@dataclass(frozen=True)
class RerollState:
    """Which slots still hold a token. Explicit input — the screen shows no counter."""
    available: tuple[bool, bool, bool] = (True, True, True)
    burned: tuple[str, ...] = ()          # api_names already revealed this game

@dataclass(frozen=True)
class PoolDistribution:
    """Tailoring-weighted empirical CDF of Score(a|S) over one tier. Built ONCE per window."""
    tier: int
    scores: tuple[float, ...]             # sorted ascending
    weights: tuple[float, ...]            # tailoring weights, normalized
    api_names: tuple[str, ...]
    source: str                           # provenance
    sample_n: int
    is_evidence: bool                     # annotation only — never gates the action
    def expected_max(self, floor: float) -> float      # g(floor), O(log N) weighted suffix sums
    def tail_integral(self, floor: float) -> float     # ∫_floor^1 (1−F)

@dataclass(frozen=True)
class RerollAdvice:
    action: Literal["PICK", "REROLL"]     # ALWAYS populated
    target_slot: int
    fallback_slot: int
    expected_gain: float
    reason: str
    threshold: float
    depletion_cost: float
    pool_source: str
    pool_n: int
    evidence: Literal["measured", "ordinal", "uncalibrated"] = "uncalibrated"
```

### Evidence annotation never suppresses the action

The reroll decision compares `B` against `F_S`, and **both come from the same score function**, so
the comparison is invariant to any monotone recalibration of `Score`. It stays valid with `Base`
neutral across all 254. Therefore:

- `advise_reroll` **always** returns a concrete `PICK`/`REROLL` action.
- `evidence` downgrades the *claim strength in the reason string* and the overlay styling, never
  the action. `"uncalibrated"` ⇒ the reason says the ordering is model-relative, not placement-backed.
- What genuinely cannot be claimed is that the threshold maps to placement — say that, don't refuse.

### Additive API on `AugmentAdvisor`

Do **not** touch `rank()` or `score_one()` (covered by `tests/test_scoring.py`, `tests/test_decision.py`):

```python
def pool_distribution(self, tier, state, exclude=()) -> PoolDistribution
def advise_reroll(self, ranking, state, rerolls, pool=None) -> RerollAdvice
```

### Latency architecture

Build `PoolDistribution` **once** on augment-window detection (1.39 ms p50 / 2.18 ms p95 for the
largest tier), cache sorted scores + weighted suffix sums, then every decision is O(log N) —
microseconds. State is frozen for the ~30 s window.

- **Never** score all 254 (12.24 ms p95). Filter to the current tier first.
- **No NumPy re-implementation.** It would duplicate all five scorers and risk drift from
  `score_one`. Defer; if measurement *under load* (SPEC §12.1) demands it, add it gated on a
  parity test asserting equality with `score_one` across every augment × a matrix of states.

### Ambiguous pairs

`Ranking` can hold >3 entries (both halves scored); slot identity is `ScoredAugment.choice_index`.
Represent an ambiguous slot as an interval `[min, max]` and **act only when the decision is
invariant across it**; otherwise emit `PICK` with the existing `KHÔNG PHÂN BIỆT ĐƯỢC` flag.
Preserves the invariant at `augment_advisor.py:14-17` that ambiguous pairs are never guessed.

### Config

Add `reroll_policy:` to `config/scoring_weights.yaml` **and** add `"reroll_policy"` to
`ScoringConfig.TOP_LEVEL_TUNING` at `src/decision/scoring/types.py:78` — otherwise it is dead
config, the exact bug that file's comment documents for `comp_selector`.

```yaml
reroll_policy:
  risk_lambda: 0.0            # 0 = risk-neutral; HP already lives in tempo_fit
  tailoring_beta: 1.0         # trait-match draw weight; 0 = uniform (ablation arm)
  burn_on_reveal: true        # ASSUMPTION — docs/augment-reroll/mechanics-assumptions.md
  cost_matrix:                # user-supplied priors, NOT measurements
    prismatic: {stage_2: 0.08, stage_3: 0.04, stage_4: 0.00}
    gold:      {stage_2: 0.01, stage_3: 0.01, stage_4: 0.00}
    silver:    {stage_2: 0.01, stage_3: 0.01, stage_4: 0.00}
```

### `config/data_sources.yaml`

URL/endpoint registry to refresh each patch, with `last_verified`, `patch`, `status` per entry so
staleness is visible. Seeded with ddragon `tft-augments.json`, CDragon, and the **recorded negative
results** — `d3.tft.tools` → `{"singles": []}` with probe date — plus empty slots for sources the
user supplies.

---

## Evaluation

**Monte-Carlo counterfactual leads — it needs no pro labels and runs today at unlimited n.**
`src/eval/reroll_ablation.py`: sample a state, draw 3 cards from the tailoring-weighted pool, run
`π_sequential` vs `π_first_look` (argmax of initial 3) vs `π_random` vs `π_oracle`. Report
`Δ E[S]` with bootstrap CI using the existing seeding conventions. Cross-check against the
closed-form ceiling `Δ ≤ E[max of 6 draws] − E[max of 3 draws]` on the empirical CDF. Label output
unambiguously: *policy-vs-policy under the model's own score function — not evidence about
placement.* Run the `tailoring_beta ∈ {0, 1}` arm to quantify the under-rerolling bias directly.

**Expert agreement is written but cannot run — a boundary, not a footnote.** Blocked on Track B:
`player_pick`, `final_placement`, and the `augment_reader` recognition layer do not exist
(`dev_log.md` #9). Build the code path, mark it blocked, claim no result.

- **Brennan–Prediger S stays primary**, including for the 3-card pick space — Cohen's κ inflates the
  sample space on disjoint label sets (0.577 vs the correct 0.40, `src/eval/expert_study.py:12-29`).
  For the binary REROLL/PICK space, S with k=2 gives `p_e = 0.5`; still S, still not κ. Report both
  label spaces with their `k`. Note SPEC §12.3 still says κ and is stale.
- Reuse `expert_study.chance_corrected_agreement` and
  `correlation.permutation_p_value(groups=game_id)` for block permutation.
- 18 windows across **6 independent games**; ≤4 decisions each (~72 points, still 6 clusters).
  Report `n_windows` *and* `n_games`. Both VODs are `role: development` ⇒ not admissible as §12.1
  evaluation data. Reuse the existing `CHUA KET LUAN DUOC` pattern rather than issuing a verdict.

---

## Files to modify

| File | Change |
|---|---|
| `src/decision/augment_advisor.py` | +2 methods; `rank()`/`score_one()` untouched |
| `src/decision/scoring/types.py:78` | add `"reroll_policy"` to `TOP_LEVEL_TUNING` |
| `config/scoring_weights.yaml` | `reroll_policy:` block |
| `src/decision/advisor.py` | wire `advise_reroll` into `AdviceBundle` inside `_safe()` |
| `src/overlay/widgets/augment_panel.py` | render the advice line (respect `MAX_REASONS=3`) |
| `SPEC.md` | new §3.5.5 Reroll Policy; note §12.3 κ→S staleness |

Reuse rather than rebuild: `FeatureTable.get`, `ScoringConfig.tune/with_ablation/only`,
`AugmentStats.is_evidence`, `eval/correlation.permutation_p_value`,
`eval/expert_study.chance_corrected_agreement`, `eval/ablation.kendall_tau`, `ScenarioLogger`
(needs a `reroll_trace` field → schema 2 → 3).

## Docs layout

Per `rules/documentation.md` (≤100 lines/file, one heading, kebab-case, `## Related`):
`docs/augment-reroll/` → `overview.md`, `formalization.md`, `dominance-theorem.md`,
`depletion-cost.md`, `tailoring.md`, `heuristic-analysis.md`, `architecture.md`, `evaluation.md`,
`mechanics-assumptions.md`.

---

## Verification

1. `./.venv/Scripts/python.exe -m pytest -q` — all 501 existing tests pass (proves additivity).
2. New tests in `tests/test_reroll_policy.py`:
   - `c=0, n≥2` ⇒ always REROLL (T2), for every incumbent score including 1.0
   - `target_slot` is always the argmin among token-holders (T1)
   - `n=1` flips at exactly `g(L)`; cards just above/below give opposite actions
   - stage 4-2 ⇒ `depletion_cost == 0` for every tier
   - prismatic 2-1 with a strong incumbent ⇒ PICK; same state in gold ⇒ REROLL (regime split)
   - **`evidence="uncalibrated"` still returns a concrete action** (regression test for the
     paralysis bug), and the reason string states the limitation
   - `tailoring_beta > 0` raises `expected_max` vs `beta=0` when the pool has trait matches, and
     the two agree exactly when it has none
   - ambiguous slot straddling the threshold ⇒ PICK + ambiguity flag
   - `expected_max` matches a brute-force weighted mean to 1e-9
   - determinism: same inputs ⇒ identical advice
3. Latency gate: `pool_distribution` build p95 < 5 ms, each `advise_reroll` p95 < 0.5 ms, same
   harness as above. Re-measure under load per SPEC §12.1.
4. `python -m src.decision.augment_advisor --json` CLI unchanged.
5. `src/eval/reroll_ablation.py` at n=10 000: `Δ E[S]` sits below the analytic ceiling, and the
   `beta=0` arm shows measurably less rerolling than `beta=1`.

## Related

- [SPEC.md](../SPEC.md) — §3.5.3 latency invariant, §3.5.4 scoring engine, §12 evaluation
- [dev_log.md](../dev_log.md) — #2 augment stats unobtainable, #9 VOD pipeline status
- [vod_pipeline_sop.md](vod_pipeline_sop.md) — frame extraction procedure
