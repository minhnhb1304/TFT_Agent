# EN Research: Explanation Design Literature — Directional/Branching Augment Explanations

Scope: explanation-design literature only (contrastive explanation, XRL, uncertainty communication, time-pressured UI, faithfulness). No TFT gameplay/tools/scoring research (covered by sibling agents).
Iterations run: 3 (search+fetch cycles). Language: English only (per assignment).

---

## Q1. Contrastive explanation ("why P rather than Q") — does it prescribe naming the tradeoff for near-tied #1 vs #2?

**Finding:** Yes — canonical theory says explanations are inherently contrastive (fact vs. foil), selective (not full causal chains), and that citing probabilities alone is a weak substitute for citing the causal/structural *difference*. This directly supports replacing "Economy value 2/3" style state-description with a fact/foil difference statement when two options are close.

**Evidence:**
- Fact/foil terminology and core claim: "one does not explain events per se, but... why the puzzling event occurred in the target case but not in some counterfactual contrast case" (Hilton 1990, cited in Miller). Foil selection requires "largely similar history, against which the differences stand out."
- Selectivity: "Explanations are *selected* (in a biased manner) — people rarely, if ever, expect an explanation that consists of an actual and complete cause of an event."
- Probabilities insufficient: "referring to probabilities or statistical relationships in explanation is not as effective as referring to causes. The most likely explanation is not always the *best* explanation for a person." — directly relevant to NOT leaning on the raw numeric margin.
- Lipton's Difference Condition: to explain "P rather than Q" cite "a cause of P and the absence of a corresponding event in the history of not-Q"; contrastive explanations are *easier* to derive than complete explanations because "one only needs to understand what is different between the two cases" — this is an argument FOR branching/contrastive explanation being simpler, not more complex, than two independent state-descriptions.

**Citations:**
- Miller, T. (2017/2019). "Explanation in Artificial Intelligence: Insights from the Social Sciences." arXiv:1706.07269 (published *Artificial Intelligence*, 267, 1–38, 2019 — venue not independently re-verified this session, flagged below).
- Lipton, P. (1990). "Contrastive Explanation." *Royal Institute of Philosophy Supplement*, 27, 247–266.
- URLs: https://arxiv.org/abs/1706.07269 , https://ar5iv.labs.arxiv.org/abs/1706.07269 , https://philpapers.org/rec/LIPCEA

**Not verified:** exact AIJ 2019 volume/page for Miller — only arXiv metadata fetched, not the journal record.

---

## Q2. Conditional/plan-based explanation for a choice whose value depends on future commitment

**Finding:** There is a directly-applicable prior technique — "tradeoff-focused contrastive explanation" for MDP/multi-objective planning — that produces almost exactly the branching format proposed in the design doc: name what you gain, what you'd have to give up, in domain terms, framed as a choice between alternative policies. Separately, XRL work explains actions by their *expected future outcomes* conditional on the policy followed afterward.

**Evidence:**
- Sukkerd, Simmons & Garlan's template for explaining a plan choice against a Pareto-alternative: *"I could [improve these QAs by these amounts], by [carrying out this alternative policy] instead. However, this would [worsen these other QAs by these amounts]"* then *"decided not to do that because [the improvement] is not worth [the deterioration]."* Explanations ground raw numbers in human-interpretable domain concepts (e.g., "non-intrusive at 5 locations, somewhat intrusive at 2"). User study: 3.8× higher correctness and improved confidence vs. plan-visualization-only baseline. This is a template for exactly the "Pick A commits you to X / Pick B commits you to Y" structure, backed by an empirical comprehension/confidence result — strong support for the design doc's proposal, and citable evidence it improves (not just satisfies) user understanding.
- XRL / Expected Future Outcomes: "fixed-horizon temporal difference learning enables contrastive explanations consisting of Expected Future Outcomes (EFOs) for different state-action pairs" — i.e., an action's explanation is stated as "if this path is followed, expect outcome Y," which matches "commits you to a reroll comp at level 6."
- Temporal Policy Decomposition (TPD) explains RL actions "in terms of their Expected Future Outcomes... time-granular insights into the consequences of each decision" — future-oriented rather than past-state-descriptive, same shift the design doc wants (from "HP 100 is comfortable" state-description to "commits you to X").
- Related: RADAR-X pairs contrastive explanations with *revised plan suggestions* in mixed-initiative planning — i.e., explanation is coupled to naming what the user would have to do differently, reinforcing the "suggested comps" attachment in the design doc.

**Citations:**
- Sukkerd, R., Simmons, R., & Garlan, D. (2020). "Tradeoff-Focused Contrastive Explanation for MDP Planning." arXiv:2004.12960 (AAMAS-family venue; exact proceedings not independently confirmed this session).
- van der Waa, J., et al. (2018). "Contrastive Explanations for Reinforcement Learning in terms of Expected Consequences." arXiv:1807.08706. **Not verified**: author list taken from search snippet, not fetched full-text (PDF fetch failed as binary both attempts) — recommend independent author confirmation before citing.
- "Explainable Reinforcement Learning via Temporal Policy Decomposition," arXiv:2501.03902 (2025).
- "RADAR-X: An Interactive Mixed Initiative Planning Interface Pairing Contrastive Explanations and Revised Plan Suggestions," arXiv:2011.09644.
- URLs: https://arxiv.org/pdf/2004.12960 , https://arxiv.org/html/2501.03902v1 , https://arxiv.org/pdf/2011.09644 , https://arxiv.org/pdf/1807.08706

---

## Q3. The honesty problem — hand-set priors, near-tied margin smaller than uncertainty, numeric score display, automation bias

**Finding, three parts:**

**(a) Don't display false-precision numbers; use qualitative bands / evidence, not decimals.** General UX/ML-writing consensus: raw score deltas (0.73 vs 0.71) read as meaningful when they're noise; recommendation is categorical bands ("high/moderate/low confidence") or evidence-based hedging over decimal scores. LLM confidence self-reports are also poorly calibrated (models "overestimate correctness probability by 20–60%" in cited surveys) — an added reason not to expose a precise number from a hand-tuned-prior system as if it were measured.
- **Not independently verified**: these were WebSearch-synthesized summaries (Ultralytics glossary, generic ML-writing blog posts), not fetched primary sources — treat as directional industry consensus, not peer-reviewed citation. Flag for thesis: find a peer-reviewed source on numeric-score false-precision if a hard citation is required.

**(b) Google PAIR (canonical HCI-for-AI guidance) directly addresses the tradeoff of showing uncertainty vs. trust:** "Indicating that a prediction could be wrong may cause the user to trust that particular prediction less. However, in the long term, users may come to use or rely on your product or company more." I.e., honesty about a tie costs short-term confidence but is the recommended tradeoff.
- Citation: Google PAIR, "Explainability + Trust," *People + AI Guidebook*. URL: https://pair.withgoogle.com/chapter/explainability-trust/

**(c) Explanations can increase, not decrease, automation bias/over-reliance — the critical anti-pattern for this design.** Directly on point, and by the same author (Tim Miller) as the contrastive-explanation work in Q1:
- Vered, M., Livni, T., Howe, P. D. L., Miller, T., & Sonenberg, L. (2023). "The Effects of Explanations on Automation Bias." *Artificial Intelligence*, 322, 103952. Finding: explanations "did not reduce automation bias... and sometimes increased it"; "explanations are interpreted as a general signal of competence — rather than being evaluated individually for their content — and just by their presence can increase the trust in and overreliance on the AI." This is the single most important citation for the "does explanation help or hurt" question in the task.
- URL: https://psychologicalsciences.unimelb.edu.au/__data/assets/pdf_file/0019/5252131/2023Vered.pdf (PDF fetch itself 403'd; citation/finding confirmed via ResearchGate + ScienceDirect listing and search snippets — recommend fetching the PDF directly outside this session for exact quotes/numbers).
- Corroborating: a neuroradiology study on GPT-4 free-text rationales found "detailed, fluent explanations were treated as a cue of competence, prompting deference even when recommendations were wrong" — likely arXiv:2404.15187 "Evaluating Physician-AI Interaction for Cancer Management," **not independently fetched/verified this session, flag before citing**.

**(d) Alternative framing that sidesteps the honesty problem: Evaluative AI.** Instead of a single ranked recommendation + confidence, show evidence for and against each option and let the user judge — avoids the "persuasive," overstated-confidence framing entirely.
- Miller, T. (2023). "Explainable AI is Dead, Long Live Explainable AI! Hypothesis-driven Decision Support using Evaluative AI." *FAccT '23* (ACM Conference on Fairness, Accountability, and Transparency), Chicago. Argues recommendation-driven XAI (rank + single justification) can be "counter-productive to better human decision making"; proposes showing evidence for/against options "irrelevant of the judged likelihood," contrasted with approaches that only explain why non-recommended options are "incorrect" in a "persuasive" way.
- URL: https://arxiv.org/abs/2302.12389

---

## Q4. Time-pressured explanation (seconds, not minutes) — what gets read?

**Finding:** Converging guidance across clinical/RTS/HCI literature: under severe time pressure, lead with the recommendation + the single reason it fired + the action choices; push all supporting detail behind progressive disclosure. Time pressure measurably increases reliance on the top-line recommendation, so the top line must carry the honesty burden (ties to Q3c).

**Evidence:**
- "For time-sensitive situations, clinicians do not need every detail at every moment but need the right detail at the right time; a strong CDS UI leads with the recommendation, the reason it fired, and the action options, with additional evidence... revealed progressively." — exactly the terse-header / expandable-detail structure implied by the 30-second constraint.
- "Alert content — the reason for activation and potential medical consequences — should be kept concise, with additional details accessible through related data links."
- Swaroop, Buçinca, Gajos & Doshi-Velez (2024), "Accuracy-Time Tradeoffs in AI-Assisted Decision Making under Time Pressure," *IUI '24* (29th ACM Conference on Intelligent User Interfaces, Greenville SC): under time pressure, participants shown the AI recommendation upfront became "much quicker... while keeping similar accuracy," i.e., people lean on the top-line recommendation and don't deeply process supporting explanation under time pressure — reinforces that the reason line must be trustworthy/terse since it may be all that's read, not a nice-to-have caveat buried lower.
- Mastrianni et al. (2025), "To Recommend or Not to Recommend: Designing and Evaluating AI-Enabled Decision Support for Time-Critical Medical Events," arXiv:2505.11996 (trauma resuscitation CDS) — directly studies recommendation framing under time-critical conditions; **full-text PDF fetch failed (binary/encoding) both attempts — only metadata/citation confirmed, content not independently verified this session.**

**Citations:**
- Swaroop, S., Buçinca, Z., Gajos, K.Z., & Doshi-Velez, F. (2024). "Accuracy-Time Tradeoffs in AI-Assisted Decision Making under Time Pressure." IUI '24. https://arxiv.org/pdf/2306.07458
- Mastrianni, A., Kim, M.S., Sullivan, T.M., Sippel, G.J., Burd, R.S., Gajos, K.Z., & Sarcevic, A. (2025). "To Recommend or Not to Recommend..." arXiv:2505.11996.
- Progressive-disclosure/selective-transparency in clinical CDS: ScienceDirect article "Operationalizing selective transparency using progressive disclosure..." — **URL captured from search snippet only, not fetched; title/authors not independently confirmed.**

---

## Q5. Anti-pattern: post-hoc LLM rationalization of a numeric score (faithfulness vs. plausibility)

**Finding:** Yes, well-documented and directly warns against exactly the tool's optional "LLM rewrites the reason wording after ranking" step. Core risk: the rewritten explanation can be a plausible-sounding story that doesn't reflect the actual computation (the hand-set prior weights), and can even fabricate supporting "facts" to justify a conclusion reached by other means.

**Evidence:**
- "Plausibility refers to human satisfaction with an explanation, while faithfulness requires that the explanation accurately reflects the model's internal reasoning process... Post-hoc explanations can be optimized for human plausibility, potentially obscuring the model's true, and possibly flawed, decision-making process."
- "Unfaithfulness occurs when models arrive at the correct answer despite invalid reasoning text... model answers can be predicted through linear probes before explanation generation, and models can be induced to change their answers and fabricate supporting facts to justify new conclusions." — this is the precise failure mode to flag: an LLM rewrite step could rationalize a ranking with reasons that sound causal but were never part of the score computation.
- "LLMs often prioritize plausibility over faithfulness due to their training objectives" — i.e., this isn't an edge case, it's an expected tendency of the rewriting step.

**Citations:**
- Agarwal, C., Tanneru, S.H., & Lakkaraju, H. (2024). "Faithfulness vs. Plausibility: On the (Un)Reliability of Explanations from Large Language Models." arXiv:2402.04614.
- Lyu, Q., Apidianaki, M., & Callison-Burch, C. (2024). "Towards Faithful Model Explanation in NLP: A Survey." *Computational Linguistics*, 50(2), MIT Press. https://direct.mit.edu/coli/article/50/2/657/119158
- Related, not deeply verified this session (title/snippet only): "Chain-of-Thought Reasoning In The Wild Is Not Always Faithful," arXiv:2503.08679 — same family of finding (stated reasoning ≠ actual driver of the answer), useful as a second independent source if the thesis wants two citations for this claim.
- URLs: https://www.semanticscholar.org/paper/Faithfulness-vs.-Plausibility:-On-the-of-from-Large-Agarwal-Tanneru/3868e87a24f671f8789b9ef2f788506126d4fd8c , https://arxiv.org/html/2311.07466v4 (related: measuring faithfulness/self-consistency)

**Practical implication for the design doc:** if an LLM rewrite step runs after the ranking is computed from hand-set priors, the rewritten branching explanation ("Pick A commits you to reroll at 6...") is a plausibility artifact, not a faithful account of the prior weights, unless the rewrite is constrained to only rephrase pre-computed, code-generated facts (which comps/levels/margins) rather than generate new causal claims. This is the literature-backed argument for template-filling over free generation in the rewrite step.

---

## Cross-cutting synthesis (for the design doc verdict)

1. **The branching design is theoretically sound** — it's the textbook contrastive-explanation form (Q1) applied with an existing, empirically-validated template from planning XAI (Q2, Sukkerd et al.'s tradeoff template maps almost 1:1 onto "Pick A / Pick B").
2. **But contrastive explanation is not a free pass on honesty** — Vered et al. 2023 (Q3c) is the load-bearing warning: adding *any* explanation, including a well-formed contrastive one, can increase unwarranted trust just by being present and fluent-sounding, independent of whether it's correct. A tie dressed up in a confident-sounding branching narrative is the worst case, not the best.
3. **Under the 30-second constraint (Q4), the top-line reason carries almost all the weight** — so whatever the tool prints first must itself encode the honesty signal (e.g., visibly flag "near-tied" / "low-confidence gap") rather than relying on a hedge buried in expandable detail nobody opens in time.
4. **The LLM-rewrite anti-pattern (Q5) is a real, literature-documented risk specifically for this architecture** (score from fixed priors → LLM restates as prose) — recommend constraining the rewrite to a fill-in-the-template operation over pre-computed facts, not open generation, and treating this as a testable faithfulness requirement, not a style nicety.

---

## Unresolved / needs independent verification

- Miller (2017) AIJ 2019 exact volume/page — only arXiv preprint metadata confirmed.
- van der Waa et al. 2018 (arXiv:1807.08706) author list — taken from search snippet only; PDF fetch failed both attempts (binary encoding issue in this session's fetch tool). Verify before citing.
- Sukkerd, Simmons & Garlan (2020) exact publication venue (AAMAS workshop vs. main track) — not confirmed beyond arXiv.
- Neuroradiology GPT-4 "fluency as competence cue" study — likely arXiv:2404.15187 but not fetched/confirmed; don't cite without checking.
- "False precision in numeric confidence scores" — only generic/blog-level sources found; no peer-reviewed primary source located in 3 iterations. If the thesis needs a hard academic citation for "don't show decimal confidence," a 4th iteration targeting HCI venues (CHI, IUI) specifically on confidence-score display would be needed.
- Progressive-disclosure/selective-transparency clinical CDS ScienceDirect article — title/authors from snippet only, not fetched.
- Several PDF fetches failed outright (binary/stream decoding errors in WebFetch this session) for: 1706.07269 (Miller full text), 1807.08706, 2004.12960 (direct PDF; ar5iv HTML mirror succeeded instead), 2306.07458 (direct PDF; ar5iv HTML mirror succeeded instead), 2505.11996, 2302.12389 (direct PDF only — HTML mirror not tried, citation confirmed via search only, content not independently verified). Where an ar5iv HTML mirror worked, content was extracted successfully; where it wasn't tried, treat quotes as search-snippet-level confidence only.
