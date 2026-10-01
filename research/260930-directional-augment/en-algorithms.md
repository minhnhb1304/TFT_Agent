# Algorithmic soundness: plan-conditioned scoring & the augment circular-dependency problem (EN sources)

Researched 2026-09-30. 5 iterations, English only. Scope: algorithmic formulation only (Q1-Q5 as assigned). No TFT gameplay/tooling/UX content included — covered by sibling agents.

Format: Question -> Finding -> Evidence -> URL. Structured data, not prose essay.

---

## Q1. Standard formulation for "action value depends on future plan, plan depends on action"

### Finding 1a: The formally correct / standard approach is MARGINALIZATION over a belief distribution, not max, not naive one-pass feedback.

This is the exact structure of a **Bayes-Adaptive MDP (BAMDP)**: augment state with a belief `b` (posterior distribution over the hidden latent — here, "which comp/archetype is the true plan"), and define reward/value as the belief-weighted sum over latents:

`R(s,b,a) = Σ_φ b(φ) · R(s,φ,a)`

A policy is "Bayes-optimal" if it maximizes **expected** return in this belief-augmented (s,b) space, solving the Bellman optimality equation under the posterior predictive model. This is the established, named solution to exactly the doc's circularity: belief over plans is a first-class state variable, updated incrementally (Bayesian filtering) as picks/board state accrue, not resolved by a hard classify-then-feedback pass.
EVIDENCE: BAMDP is "a principled framework for sequential decision making under model uncertainty," agent maintains "a posterior distribution over latent parameters," reward defined by the marginalization formula above.
URL: https://www.emergentmind.com/topics/bayes-adaptive-markov-decision-processes-bamdps (also cross-ref: https://arxiv.org/pdf/1205.3109 "Efficient Bayes-Adaptive RL using Sample-Based Search", https://www.jmlr.org/papers/volume22/21-0657/21-0657.pdf "VariBAD: Variational Bayes-Adaptive Deep RL via Meta-Learning")

### Finding 1b: General POMDP framing confirms marginalization (expectation over belief), not maximization, is the textbook decision rule.

In a POMDP, belief state = probability distribution over hidden states (here: hidden "true plan"); optimal policy maximizes **expected discounted cumulative reward** under that belief — i.e., an expectation over hypotheses, not a max over hypotheses. Recent applied work (Tru-POMDP) explicitly maintains "a categorical belief... over goal hypotheses" via hierarchical hypothesis trees for exactly the "hidden intent / hidden goal" case the augment problem resembles.
EVIDENCE: "belief state is introduced as a probability distribution over states... satisfying the Markov property"; "POMDP solution is the optimal policy that maximizes the expected, discounted cumulative reward."
URL: https://www.sciencedirect.com/topics/engineering/partially-observable-markov-decision-process ; https://tru-pomdp.github.io/ ; https://arxiv.org/html/2506.02860v2

### Finding 1c: Max-over-plans is a known, named, and criticized decision rule — it is "maximax," not a neutral formulation.

Scoring an action by its best-case value under whichever plan makes it look best (`max_φ value(action|φ)`) is the classical **maximax criterion** from decision theory under uncertainty (Wald-family decision rules: maximin/maximax/minimax-regret/Laplace/expected-value). It is explicitly the *optimistic* extreme, sibling to Wald's pessimistic **maximin**. Both are named, both have known failure modes.
EVIDENCE: "Maximax means 'maximize the maximum payoff'... focuses on the best possible outcome... ignoring downside risk." Criticized as: "disregard[s] the probabilities and values of other outcomes, and can lead to poor decisions"; "does not ask which outcome is most likely"; "can be inconsistent and irrational... may alter the preference order of alternatives depending on how payoffs are presented."
URL: https://fiveable.me/key-terms/game-theory/maximax-criterion ; https://spicelogic.com/docs/decisiontreeanalyzer/intro/decision-criteria-333 ; (maximin sibling, for contrast) https://en.wikipedia.org/wiki/Wald's_maximin_model

**Why this matters for the doc's proposal:** the doc's "directional potential" (score an augment by the best plan it could commit you to) is structurally maximax. Maximax is well-documented as biased toward options that have *one* great-but-improbable outcome and ignores the probability/likelihood of actually reaching that plan. It is NOT the standard formulation in sequential decision-making literature — expectation-under-belief (BAMDP/POMDP) is.

### Finding 1d: Fixed-point / EM-style alternation is a real, named alternative — but solves a different problem (parameter estimation from data), and doesn't map cleanly onto a single real-time draft decision.

EM alternation ("chicken-and-egg... you need the group labels to find the averages, but you need the averages to find the group labels... solved through EM": E-step / M-step, iterate to convergence) is the standard tool when two *unknown quantities* mutually determine each other **across a dataset with many observations**. It is not naturally a per-decision, single-shot planning tool — it's an offline/batch estimation procedure. Relevant analogy: could be used offline to jointly learn "archetype cluster assignments" and "archetype-conditioned augment values" from historical game logs, but does NOT resolve the online, single-augment-offer circularity the doc describes. That online problem is a belief/POMDP problem (1a/1b), not an EM problem.
EVIDENCE: "The EM algorithm solves this through an iterative two-step process... stopping when parameters barely change between iterations."; "EM algorithm is useful in sequential decision problems where it is difficult to directly optimize the incomplete data likelihood due to hidden data."
URL: https://medium.com/data-science/solving-a-chicken-and-egg-problem-expectation-maximization-em-c717547c3be2 ; https://sciencedirect.com/topics/social-sciences/expectation-maximization-algorithm

### Finding 1e: Naive one-pass "comp selector output fed back into augment scorer" is architecturally the failure mode literature warns about — order-dependent, no feedback loop closure, no uncertainty representation.

No single source names "naive one-pass feedback" as a pattern (expected — it's an anti-pattern, not a technique), but by elimination against 1a-1c: a one-pass forward feed (comp selector -> augment scorer, no return path, no belief update) is neither marginalization nor iteration-to-fixed-point; it's a single E-step with no M-step, or equivalently a POMDP policy conditioned on a **point estimate** instead of the belief distribution — known in POMDP literature as "MLE-state / most-likely-state heuristic," a documented approximation that discards uncertainty and is inferior to full belief-space planning for exactly the reason the doc's problem exists: early augments, by construction, have high uncertainty over which plan is correct.

**CANNOT FULLY VERIFY:** no single source explicitly benchmarks "one-pass MLE feedback vs BAMDP" in a game-AI context — this is a synthesis from decision-theory fundamentals (1a-1c), not a directly-cited claim. Flagging per instructions.

---

## Q2. Card-draft AI (closest analogue) — archetype conditioning

### Finding 2a: 17Lands / human draft theory explicitly teaches maintaining a soft, evolving commitment — not a hard classify-then-lock architecture. Card evaluation is archetype-conditioned but the archetype itself is a gradually-firming belief, not a discrete early decision.

"Staying open": approach early picks "in a vacuum, regardless of what you've already drafted"; **speculative picks**: take an off-color bomb "just in case you decide to switch into that color later"; **signal reading**: infer what's open from what wheels back, i.e., update belief from environment feedback (a form of Bayesian filtering by proxy); typical human heuristic: "by around pick five or six... you should know your two colors" — i.e., commitment is a *gradual convergence*, not a one-shot resolution of a chicken-and-egg problem.
EVIDENCE: quotes as above.
URL: https://blog.cardsphere.com/how-to-stay-open-in-draft/ ; https://blog.cardsphere.com/a-step-by-step-guide-to-reading-signals/ ; https://magic.wizards.com/en/news/feature/signals-booster-draft-2015-01-19

### Finding 2b: 17Lands itself explicitly warns that a single global card-quality number (GIH WR) is misleading without archetype context, and recommends conditioning on color-pair/archetype — but frames this as a *late-draft* shift in weighting, not an early hard commitment.

"Strong late-game bombs... inflate metrics in decks built specifically to support them, not in isolation." Recommends "win rates of a card in different colour combinations." Explicit temporal rule: "GIH WR is a way better indicator early in a draft... the later in a draft, the more you should focus on your game plan" — i.e., weight shifts continuously from Base-quality-dominant to plan-fit-dominant as information accrues, which is itself evidence against a discrete "comp selector fires once, feeds back" architecture.
EVIDENCE: as quoted.
URL: https://blog.17lands.com/posts/using-win-rate-data/

### Finding 2c: Published draft-bot architectures avoid the circular-dependency architecture entirely — they use continuous, implicit pool representations, not an explicit archetype-classifier-feeds-back-into-scorer design.

- **BayesBot** (academic MTG draft bot, "AI solutions for drafting in Magic: the Gathering"): scores pick `i` by `argmax_i Σ_j log(n_{i→j}/n_i·n_j)` — synergy with **already-drafted cards** via co-occurrence statistics. No explicit archetype variable at all; "archetype fit" emerges implicitly from pairwise card-co-occurrence likelihoods. No circularity because there's no discrete archetype node in the graph.
- **NNetBot** (deep learning draft bot): pack + current collection + actual pick pre-processed into vectors, output element-wise multiplied by pack vector; per-draft accuracy 48.67% vs BayesBot 43.36%, human-tuned Draftsim 44.54% — i.e., the *implicit, no-explicit-archetype* neural approach outperforms both bespoke archetype heuristics and Bayesian co-occurrence.
- **DraftFM** (foundation model, 149M human picks / 29 sets, 1.6M params): represents accumulated pool as **one continuous d-dimensional embedding** via cross-attention over card+count embeddings ("Four learned queries summarize this unordered collection through four-head cross-attention... pool is compressed to one d-dimensional vector"). Explicitly: "archetype membership [is] an implicit consequence of the cards selected, not a separate conditioning variable that could circularly influence card value assessment." This is the closest published answer to the doc's exact circularity question, and the answer is: **don't build a discrete archetype-selector node that feeds back — make plan-commitment a continuous, always-updating embedding that both is influenced by and influences scoring in the same forward pass, with no separate "selector" stage.**
EVIDENCE: quotes/equations as above.
URL: https://arxiv.org/pdf/2009.00655 (BayesBot/NNetBot, "AI solutions for drafting in Magic: the Gathering", Henry N. Ward) ; https://arxiv.org/html/2608.19568v1 (DraftFM)

### Finding 2d: MOBA draft AI (LoL/Dota) treats team composition value as a combinatorial/team-level scoring problem, evaluated by **win-probability given the (partial) team**, not archetype-then-feedback.

"The Art of Drafting: A Team-Oriented Hero Recommendation" (RecSys'18): models drafting as **"a combinatorial game of hero combinations,"** recommending heroes that maximize win probability of the *eventual full team* given the current partial pick state — i.e., value is conditioned on the whole trajectory distribution, scored directly, not funneled through a separate discrete "archetype classifier." Historical accuracy progression on pure pick-based win prediction: DotA2CP (2013) 63%, Conley & Perry logistic regression 69.8%/KNN 70%, Kalyanaraman (2014, added hero roles) 74.1%, more recent team-feature extraction methods 84%.
EVIDENCE: as above.
URL: https://arxiv.org/pdf/1806.10130 / https://web.cs.ucla.edu/~yzsun/papers/2018_recsys_drafting.pdf ; (accuracy lineage) https://www.researchgate.net/publication/364461875_Draft-Analysis_of_the_Ancients_Predicting_Draft_Picks_in_DotA_2_using_Machine_Learning

**CANNOT VERIFY:** Could not find a Hearthstone Arena academic paper or OpenAI Five draft-phase paper that explicitly discusses archetype-probability-distribution vs hard-commitment (Hearthstone Arena tools found — HearthArena, Arenasmith, HDT Arena Helper — are industry heuristic scorers using synergy/curve adjustments, not published architectures with belief-state formalism). Flagging per instructions.
URL (industry tools, not peer-reviewed architecture): https://hsreplay.net/arenasmith/ ; https://github.com/dokson/HdtArenaHelper

---

## Q3. Option value / value of flexibility — is there a rigorous "keeps N plans open" score?

### Finding 3a: Real Options Theory is the rigorous, named framework for valuing flexibility/deferred-commitment in sequential decisions under uncertainty — but it prices flexibility as one term in an expected-value calculation, not as a free-standing "count reachable plans" heuristic.

"Real Options Analysis... takes into account the effect of flexibility... recognizing the presence of flexibility in present and future decisions." Strategic choices (defer, expand, contract, switch, abandon) are "treated as options analogous to financial call/put options." Critically: "real options are most valuable when uncertainty is high; management has significant flexibility to change course... and is willing to exercise the options" — flexibility's value is *conditional on uncertainty resolving usefully*, not an unconditional bonus for having more branches.
EVIDENCE: as quoted.
URL: https://en.wikipedia.org/wiki/Real_options_valuation ; https://thedecisionlab.com/reference-guide/economics/real-options-analysis ; https://faculty.wharton.upenn.edu/wp-content/uploads/2012/05/AMR-Real-Options.pdf ("What Is Not a Real Option: Considering Boundaries for the Application of Real Options to Business Strategy")

### Finding 3b: The RL/AI analogue of "value of keeping options open" is "empowerment" — and it is explicitly, repeatedly criticized as a bad proxy for exactly the failure mode the doc risks: rewarding generically-good-for-everything actions over actually-good actions.

Empowerment = an intrinsic-motivation objective that scores actions/states by the agent's future influence/reachable-state diversity (information-theoretic channel capacity between actions and future states). Documented criticisms directly applicable to a "reward augments that keep N plans open" heuristic:
- "Having more options does not always translate directly into greater capability" (explicit example: one strong job offer beats several weak ones).
- The "implicit assumption is that the agent's influence... is tied to how many states they will have access to" — flagged as "overly simplistic."
- A proxy based on "variance of the user's states at end of rollouts... feels like an engineering solution," "doesn't scale when the environment becomes complex."
- Fix proposed in the literature (Turner/Hadfield-Menell/Tadepalli, attainable-utility preservation): use option value **over goals/utility**, not over raw states — "quietly handles the objection that most state distinctions do not matter." This is the direct academic answer to "don't just count reachable plans, weight them by whether they're actually good plans."
EVIDENCE: as quoted.
URL: https://arxiv.org/html/2511.04177v1 ("When Empowerment Disempowers") ; https://kiciman.org/wp-content/uploads/2021/02/NeurIPS-2020-ave-assistance-via-empowerment-Paper.pdf (AvE: Assistance via Empowerment, NeurIPS 2020) ; https://arxiv.org/pdf/1806.01186 (Turner et al., "Penalizing side effects using stepwise relative reachability")

**Synthesis for the doc:** if a "directional potential / flexibility bonus" term is added, the literature says: (i) it must be priced as expected value under the belief over plans (3a: real options are priced via expectation, discounted by probability of exercise), not a raw count of reachable archetypes; (ii) raw option-counting is a criticized, known-flawed proxy (3b) that rewards generic/uncommitted augments over actually strong ones — exactly the risk of "reward augments that keep options open" as a heuristic bolted onto the linear model.

---

## Q4. Tie-breaking / massive tie-mass in a hand-weighted linear score

### Finding 4a: Directly on-point paper found: massive tie-mass in ranking scores is a named, studied phenomenon with a specific diagnosis and remedy discussion.

"Tie Handling Is Part of the Evaluation Protocol: An Order-Invariance Audit for Tie-Heavy Recommender Scores" — diagnoses causes of tie-mass as: (1) **feature saturation** — "recommender systems exhaust discriminative information early, many items receive identical scores"; (2) **coarse/quantized features** — "discrete or low-precision scoring mechanisms create artificial score clustering"; (3) **insufficient signal** — "rankings based on sparse data or weak predictive features cannot differentiate among similar candidates." This maps precisely onto the project's own measurement (74-94% same-tier tie rate, groups up to 26): a linear-additive score with a small number of coarse component terms (Base/BoardFit/EconFit/ItemFit/TempoFit) is a textbook feature-saturation setup once inputs run out of resolution.
Remedy per this paper: **tie-handling should be explicit, documented, and evaluated as part of the protocol** — arbitrary deterministic tie-break (e.g., alphabetical by id) is not condemned outright, but must be disclosed and its effect on evaluation metrics audited ("order-invariance audit"), because different tie-break methods "can produce substantially different evaluation outcomes."
EVIDENCE: as quoted.
URL: https://arxiv.org/pdf/2609.26977

### Finding 4b: Standard ML/recsys diagnosis of tie-mass is "cold start / insufficient discriminative features," and the accepted remedy direction is adding a more informative conditioning signal — supporting (not proving) the doc's instinct that a plan-conditioned term is a legitimate fix, provided it genuinely adds discriminative signal rather than a redundant one.

"Cold start... occurs when an algorithm can't draw inferences for users/items that it doesn't have sufficient data on... new items... lack behavioral features and hence are ranked as irrelevant." The general pattern across sources: tie-mass = symptom of a low-rank / low-dimensional scoring function relative to the number of candidates; adding a genuinely independent, higher-resolution feature (e.g., plan-fit, if it is NOT strongly correlated with the existing 5 terms) mechanically breaks ties by increasing effective rank of the score function. **Caveat not found in any single source but is a direct corollary of the feature-saturation diagnosis (4a):** if the new plan-conditioned term correlates highly with existing terms (e.g., ItemFit/BoardFit already implicitly encode "which comp you're leaning toward"), it will not break ties — the literature's diagnosis is about *discriminative* power, not *additional* terms per se.
EVIDENCE: as quoted.
URL: https://arxiv.org/pdf/1805.09023 (cold-start) ; https://arxiv.org/pdf/2609.26977 (tie-handling paper, cross-ref)

**CANNOT VERIFY:** No source specifically addresses "danger of arbitrary deterministic tie-break in *ranked advice/decision-support* systems" (as opposed to recsys eval metrics) — closest available is the order-invariance-audit paper (4a), which treats it as a measurement/evaluation-protocol concern, not a user-facing-advice-harm concern. Flagging per instructions — this is an inference/extrapolation, not a directly cited finding.

---

## Q5. Is "myopic/linear-additive -> lookahead/planning" a real, citable academic transition?

### Finding 5a: Yes — well-established, named terminology exists. Use these terms, not invented ones.

Core vocabulary, directly cited:
- **"One-step greedy" / "1-step greedy policy improvement"** — standard term for scoring/acting based on immediate value only. "Policy Iteration (PI) and Value Iteration (VI) are both based on a one-step greedy approach for policy improvement."
- **"h-lookahead policy" / "h-greedy policy" / "κ-greedy policy"** — formal multi-step generalization: "An h-lookahead policy with respect to a value function returns the optimal first action in an h-horizon MDP."
- **"Myopic"** is the standard adjective, used interchangeably with "greedy" / "one-step": "Myopic algorithms (also referred to as greedy) decide sampling points based on a one-step lookahead utility function, oblivious to how this design will affect the future steps." Directly paired with "**non-myopic**" as the named opposite (used extensively in Bayesian Optimization literature too — "Why Non-myopic Bayesian Optimization is Promising").
- Known trade-off, explicitly citable for a Limitations chapter: "increasing the lookahead horizon results in improved sample complexity, with the cost of additional computations"; but "a larger rolling horizon implies an increased dependence on a possibly erroneous model which might cause adverse effects compared to myopic algorithms where errors accumulate only from a one-step lookahead" — i.e., the literature explicitly documents that lookahead is not a free win, it trades bias/error-accumulation-from-model-error against myopia's bias/error-accumulation-from-short-horizon. Good citable nuance for a Future Work section (don't oversell lookahead as strictly better).
EVIDENCE/URL:
- "Beyond the One-Step Greedy Approach in Reinforcement Learning" (Efroni et al.) — https://arxiv.org/pdf/1802.03654 / https://ar5iv.labs.arxiv.org/html/1802.03654
- "Online Planning with Lookahead Policies" (Efroni et al.) — https://arxiv.org/pdf/1909.04236
- "Planning and Learning with Adaptive Lookahead" — https://arxiv.org/pdf/2201.12403
- "Why Non-myopic Bayesian Optimization is Promising" — https://arxiv.org/pdf/1911.01004 / https://proceedings.mlr.press/v108/yue20b/yue20b.pdf
- "Tight Regret Bounds for Model-Based RL with Greedy Policies" — https://arxiv.org/pdf/1905.11527
- MIT lecture notes (Bertsekas), rollout / approximate policy iteration, standard reference for this exact myopic-vs-lookahead terminology in a pedagogical/thesis-citable form — https://web.mit.edu/dimitrib/www/RLTopics_Lecture3.pdf

### Finding 5b: The Efroni et al. line of work explicitly frames its own contribution the same way the doc wants to frame its thesis contribution — "the common 1-step greedy approach is a specific choice, which is not necessarily the most appropriate one" — and cites AlphaGo's multi-step lookahead (MCTS) as the empirical motivating precedent. This is a directly reusable framing/citation for a Limitations & Future Work chapter arguing linear-additive local optimization -> lookahead/planning.
EVIDENCE: as quoted.
URL: https://arxiv.org/pdf/1802.03654

---

## Cross-cutting synthesis (for the algorithmic-soundness verdict)

1. The doc's "chicken-and-egg paradox" is real but not novel — it is the standard structure of sequential decision-making under a hidden/latent plan variable, and has a standard name and standard solution family: **POMDP / BAMDP, belief over hypotheses, value = expectation over belief**, not max, not naive one-pass feedback (Q1).
2. The doc's proposed "max over plans" (directional potential) is a named, critiqued decision rule (**maximax**) — optimistic-bias-prone and not the field's default; default is expectation/marginalization (Q1c vs Q1a-b).
3. The closest and best-documented real-world analogue (competitive MTG draft AI) has already converged on an answer to this exact circularity: **don't build a discrete "comp-selector -> feed back" pipeline; represent commitment as a continuous, always-live embedding/belief that updates every pick and is read by the scorer in the same pass** (Q2c, DraftFM). This is the single most actionable, most directly transferable finding for the doc's architecture question.
4. A raw "rewards keeping options open" bonus is a known-flawed proxy (empowerment criticism) unless weighted by plan quality/probability, not just plan count (Q3).
5. The project's own measured tie-mass (74-94%) is textbook feature-saturation (Q4a) — adding a discriminative (not redundant) plan-fit term is a defensible remedy per the literature, but the doc should show the new term is not collinear with existing terms.
6. "Myopic/greedy -> lookahead/planning" is legitimate, well-precedented academic terminology for a thesis Limitations chapter, with citable nuance that lookahead trades one error source for another rather than being strictly superior (Q5).

## Unresolved / could not verify
- No peer-reviewed Hearthstone Arena or OpenAI-Five-draft-phase paper found addressing archetype-belief vs hard-commitment (Q2, only industry heuristic tools found).
- No source directly benchmarks "naive one-pass feedback" against belief-based planning in a game-AI-specific setting (Q1e) — conclusion there is synthesized from decision-theory fundamentals, not a single citable head-to-head study.
- No source directly addresses "danger of arbitrary deterministic tie-break" in a decision-*advice* (vs. eval-metric) context (Q4) — closest is an evaluation-protocol paper, applied here by extrapolation.
