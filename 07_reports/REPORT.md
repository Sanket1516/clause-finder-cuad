# Evaluation report: contract clause search

Numbers come from saved artifacts: `06_results/final_comparison.{md,json}` (generated from `03_experiments/final_eval/*`), `03_experiments/experiment_log*.jsonl`,
`06_results/dataset_validation.json`. "n" is always the number of queries behind a figure. Illustrative examples are marked as such and are not measurements.

## 1. Summary
I built a local clause-search system over 29 CUAD contracts: it returns ranked passages with document IDs and exact character offsets, or abstains when no passage is
strong enough. A lexical baseline (500-character chunks + BM25, whole question as the query) scored **character recall@4 = 0.043** on the 54 held-out test questions. After a
logged, train-only improvement process (15 pre-registered candidates: 3 accepted, 12 rejected, then a post-hoc 5-candidate abstention stage) the frozen final configuration —
routing to the named contract, paragraph-aware chunks, light stemming, a normalised-score gate — scores **recall@4 = 0.448** (recall@1 0.202, @16 0.747, @64 0.925; precision@4 0.085)
on the same test questions, matching its train score (0.448, n = 140). **Abstention is the weak part:** the final system correctly abstains on 3 of 10 held-out unanswerable
questions (baseline 1 of 10) and wrongly withholds 4 of 54 answerable ones. No language model is used. The held-out test split was evaluated once per configuration (see section 4 for the exact count).

## 2. System design
**Pipeline:** question -> (optional) pick the contract named in the question's "Consider the ...;" clause -> BM25 over that contract's chunks -> remove overlapping passages ->
ranked candidates -> confidence = top BM25 score / sum of idf of the question's words -> abstain if below a threshold calibrated on train. Offsets are first-class: chunks are ranges over
the untouched original text, and `text == document[start:end]` is asserted when chunks are built and rechecked before display (0 violations in all 49 saved metric files).

| Decision | Chosen | Alternatives and why not (here) |
|---|---|---|
| Retrieval | BM25 written in-repo (~40 lines, every score explainable) | Dense / hybrid / cross-encoder rerankers: **not built or tested**, so I make no claim about them. Chosen for transparency, CPU-only speed and a 12-hour budget. |
| Chunking | fixed 500 (baseline) -> paragraph-aware <= 800 chars | 300 and 1000 fixed and clause/heading-aware chunks were tried and rejected (section 6). |
| Contract selection | use the named title only to choose the contract, then rank clauses inside it | Scoring the title together with the clause (baseline) lets party names pull cover pages to the top. Soft routing was worse. |
| Abstention | one-parameter threshold on a normalised score | Learned classifier: too few labelled unanswerables (39 train) |
| Improvement loop | pre-registered catalogue + rule keyed on failure type | LLM proposer / Bayesian search: harder to explain, more freedom to over-fit 140 queries |
| Frameworks | none (no LangChain etc.) | every line is explainable in the debrief |

## 3. LLM use
**No LLM is used anywhere** (retrieval, ranking, abstention, query handling or loop proposals). Reasons: the task is retrieval and a lexical baseline already gives a measurable
signal; contracts are confidential, so a hosted model would need explicit authorisation and a privacy review, and a local model would add latency and a reproducibility burden (output caching) the
time budget did not allow. I therefore **cannot say whether an LLM would help**; that comparison was not run. (AI tool use is disclosed in the README.)

## 4. Evaluation setup
- **Benchmark:** LegalBench-RAG CUAD, mirror `awinml/legalbench-rag` revision `2b9c248b…`. The prescribed `mini()` selection gives **194 queries over 29 contracts** (only those contracts are indexed: 1,211,773 characters).
  Offset check: **272/272** gold snippets satisfy `document[start:end] == answer`; no missing documents or overlapping gold spans (`dataset_validation.json`).
- **Split:** the prescribed `assign_split` (SHA-256 of the stripped query, mod 10 < 3 = test): benchmark **train 140 / test 54**.
- **Unanswerable set:** 49 queries written before any retrieval code existed, committed once (`b1f3e64`) and never edited (sha256 lock, regression test). Same split function: **train 39 / test 10**.
  Categories (train/test): clause absent from an indexed contract 26/7, contract not in the corpus 7/1, outside a contract's scope 6/2. Absence was checked by keyword patterns with zero hits in the target
  contract (whole corpus for invented contracts); only two contracts were read in full, so a paraphrased answer could have been missed.
- **Retrieval metrics** (authors' definition): precision@k = overlapping characters / all returned characters (wrong-document text counts against precision), recall@k = overlapping / gold characters, macro-averaged
  over answerable queries, k in {1, 2, 4, 8, 16, 32, 64}. Returned passages are made non-overlapping; nothing returned scores 0. *Ranking view* = before the abstention gate (used for all retrieval tables); *end-to-end view* =
  abstained answerable queries score 0 (final: R@4 0.420 train, 0.430 test).
- **Abstention metrics** (decision level, separate from the character metrics): false abstention = answerable queries given nothing; correct abstention and false answer = unanswerable queries given nothing / given passages.
  The threshold is calibrated on the answerable **train** queries so that at most 5% are refused; unanswerable labels never fit a threshold, only score it.
- **Test usage:** see the count in the next section.

## 5. Results
**Test-split evaluations.** The ledger (`06_results/test_runs/`) holds 4 lines: 2 are unit-test artifacts (explained in `ledger_notes.md`) and 2 are the real evaluations (baseline, final), one per configuration.
Before them, two earlier attempts computed test metrics in memory and then crashed at the save step; they were never printed, saved or looked at and nothing was changed because of them.
So **4 test-split evaluations were started, 2 recorded; none was used for any decision.** A fresh-clone check re-ran them in a throwaway clone to confirm exact reproduction.

**Character-level retrieval, answerable queries (ranking view)**
| k | train baseline R / P | train final R / P | test baseline R / P | test final R / P |
|---|---|---|---|---|
| 1 | 0.000 / 0.000 | 0.214 / 0.120 | 0.000 / 0.000 | 0.202 / 0.096 |
| 2 | 0.001 / 0.000 | 0.337 / 0.109 | 0.000 / 0.000 | 0.346 / 0.101 |
| 4 | 0.021 / 0.007 | **0.448** / 0.075 | 0.043 / 0.004 | **0.448** / 0.085 |
| 8 | 0.094 / 0.011 | 0.592 / 0.056 | 0.079 / 0.008 | 0.583 / 0.055 |
| 16 | 0.173 / 0.012 | 0.719 / 0.036 | 0.184 / 0.013 | 0.747 / 0.038 |
| 32 | 0.303 / 0.011 | 0.841 / 0.024 | 0.244 / 0.010 | 0.887 / 0.026 |
| 64 | 0.428 / 0.007 | 0.909 / 0.019 | 0.356 / 0.007 | 0.925 / 0.016 |
| n | 140 | 140 | 54 | 54 |

Uncertainty (percentile bootstrap over queries, B = 2000, seed 0; computed from the saved predictions): final R@4 train [0.370, 0.528], test [0.320, 0.574]; paired final-minus-baseline R@4 on test +0.406 [0.282, 0.529].

**Abstention**
| | train baseline | train final | test baseline | test final |
|---|---|---|---|---|
| false abstentions / answerable | 6/140 | 7/140 | 4/54 | 4/54 |
| correct abstentions / unanswerable | 7/39 | 16/39 | 1/10 | 3/10 |
| false answers / unanswerable | 32/39 | 23/39 | 9/10 | 7/10 |
| AUROC of the confidence signal | 0.546 | 0.737 | 0.562 | 0.683 |
| threshold (fitted on train) | 28.365 | 0.2401 | 28.365 | 0.2401 |

Final correct abstention by category — train: clause absent 12/26, not in corpus 3/7, out of scope 1/6; test: 2/7, 1/1, 0/2. Wilson 95% intervals for correct abstention: final train [0.27, 0.57], final test [0.11, 0.60].
The baseline's train score on contracts not in the corpus (7/7) was an accident of its design (invented party names matched nothing); it does not mean the baseline "understood" absence.

**Runtime and guardrails (this CPU, warm):** query p95 latency single-digit milliseconds for both configurations (final: 6.1 ms train, 7.9 ms test), index build 0.07-0.29 s, 1,941 chunks (final) vs 2,437 (baseline). The p95 <= 2 s and build <= 900 s guardrails are met by a wide margin.

**Train/test gap.** Recall@4 is identical (0.4483 vs 0.4484), and the other retrieval cutoffs differ by at most 0.05 (recall@32: 0.841 train vs 0.887 test), within the intervals above — I see **no evidence of over-fitting in the retrieval metric**, but also
little power to detect it: the test interval is about ±0.13 wide and 15 candidates were compared on the same train queries. Two reasons not to over-read this: train and test queries concern the *same contracts* (train queries cover all 29, test queries 21 of them), so this measures new questions, not new
contracts, and the three largest contracts account for 24% of train and 31% of test queries. Abstention shows the expected optimism: correct abstention 0.41 on train vs 0.30 on test (3/10), because the gate was selected on those same 39 train
unanswerables (post hoc, section 6) — and false abstention rose from the 5% calibration target to 7.4% (4/54). With 10 test unanswerables the abstention figures cannot support firm conclusions.

## 6. Iteration history
**Objective (declared before experiments, `03_experiments/optimization_objective.md`):** primary metric = train recall@4 (ranking view, n = 140): a reader sees a handful of passages and missing the clause is the costly error. Guardrails (each vs the
current best): precision@4 >= 0.9x, correct abstention not down by more than 1 of 39, recall@1 not down by more than 0.02, p95 latency <= 2 s, build <= 900 s. **Accept** iff recall@4 rises by >= 0.010 *and* a paired bootstrap over the 140 queries says P(gain) >= 0.90 *and* all guardrails pass;
**inconclusive** if the gain is there but P < 0.90; otherwise **reject**. **Loop:** `run_improvement_loop.py` evaluates the parent on train, counts failure types, picks the first untried entry of a pre-registered catalogue targeting the most common type, evaluates it on the same queries, applies the rule and appends to
`experiment_log.jsonl`; it is restartable and deterministic (re-running from scratch in a fresh clone reproduced every decision). Proposer: rules (not an LLM or a search).

| # | Change | R@4 | dR@4 | P(gain) | Decision and reason |
|---|---|---|---|---|---|
| 0 | baseline | 0.021 | | | |
| 1 | drop the title clause from the scored text | 0.049 | +0.027 | 0.94 | **rejected**: correct abstention fell 0.179 -> 0.026 (G2) |
| 2 | route to the named contract, rank only inside it | 0.309 | +0.287 | 1.00 | **accepted** |
| 3 | soft routing (score boost) | 0.288 | -0.020 | 0.00 | rejected (G2) |
| 4 | English stopwords | 0.283 | -0.026 | 0.12 | rejected |
| 5 | 300-char chunks | 0.250 | -0.059 | 0.00 | rejected |
| 6 | 1000-char chunks | 0.400 | +0.091 | 1.00 | **rejected**: precision@4 0.064 -> 0.049 (G1), though recall rose |
| 7 | paragraph-aware chunks (<= 800) | 0.412 | +0.104 | 1.00 | **accepted** |
| 8 | clause/heading-aware chunks | 0.376 | -0.036 | 0.02 | rejected (G1, G3) |
| 9 | light stemming | 0.448 | +0.036 | 0.92 | **accepted** (the most borderline acceptance) |
| 10 | BM25 k1 = 1.0 | 0.441 | -0.007 | 0.18 | rejected |
| 11 | BM25 b = 0.9 | 0.439 | -0.009 | 0.09 | rejected |
| 12 | gate on normalised score | 0.448 | 0.000 | | rejected: cannot raise retrieval recall, though correct abstention doubled (0.205 -> 0.410) |
| 13 | gate on score margin | 0.448 | 0.000 | | rejected (G2) |
| 14 | 100-char chunk overlap | 0.448 | 0.000 | | rejected — a **no-op**: overlap applies only to fixed chunks and the parent already used paragraph chunks |
| 15 | expand each passage by 100 chars | 0.442 | -0.006 | 0.31 | rejected (G1) |

Of the 15 iterations only 12 could change recall@4 (12-14 touch the gate or are no-ops).

**Round 2 — abstention stage (post hoc).** Iteration 12 showed the round-1 rule cannot accept gate-only changes. I therefore declared a second objective *after seeing* that one result (so it is not blind): maximise train correct abstention
(39 unanswerables) at <= 5% false abstention, retrieval metrics required identical, accept iff +2 queries and P(gain) >= 0.90 with no category losing more than 1. Results (`experiment_summary_round2.md`): normalised score **accepted** (8/39 -> 16/39, +8, P = 1.00);
query-word coverage rejected (-3, category guardrail); title-match alone rejected (-8); normalised score x title match rejected (+0, higher AUROC 0.80 but no gain); coverage x title rejected (-1). The accepted gate is the only reason the final abstains on 16/39 instead of 8/39.

## 7. Error analysis
All cases are **final configuration, train split** (so no tuning signal comes from test), traceable by `query_id` in `03_experiments/final_eval/final/train_predictions.jsonl` (gold spans are in `gold_for_evaluation_only`; text via `02_data/raw`).
Distribution of the 140 train answerable queries: hit 56, ranked too low 68, partial span 12, right contract but never found in the top 64 four (`06_results/final_failure_analysis_train.md`). Diagnoses are my reading of the text, not experiments.

| # | Cause | Query (id, question) | What happened | Diagnosis |
|---|---|---|---|---|
| 1 | Vocabulary mismatch: concept named differently | cuad-mini-006, *expiration date* | gold (5604-5739) "The term of this Agreement shall be one (1) year…" appears at rank 12; rank 1 is a "Consents" paragraph | the question's words ("expiration", "date") do not occur in a term clause |
| 2 | same | cuad-mini-013, *expiration date* | gold = "employment … shall continue … until terminated" at rank 8; rank 1 = "Annual Bonus" | same; the clause says "continue until terminated" |
| 3 | same | cuad-mini-020, *expiration date* | gold = "term … one (1) year … ending on December 31, 2008" at rank 9; rank 1 = "18. Assignment" | same. Expiration-date is the largest question type (19 train queries, mean R@4 0.37) |
| 4 | same | cuad-mini-035, *exclusivity agreement* | gold "grants … an exclusive, non-transferable license" at rank 12 | "exclusivity" and "exclusive" are different tokens; light stemming does not conflate them (hypothesis) |
| 5 | same | cuad-mini-056, *revenue or profit-sharing* | gold (11296-11663) "Royalty payments … 5% of the Fair Market Value"; rank 1 is the **adjacent** paragraph (11679-12406) | question says "revenue/profit-sharing", clause says "royalty"; the right neighbourhood is found, the right paragraph is not |
| 6 | same | cuad-mini-101, *uncapped liability* | gold "NO PARTY SHALL BE LIABLE FOR CONSEQUENTIAL … DAMAGES" at rank 9; rank 1 = "Dedication" | the question asks about the *absence* of a cap; lexical overlap with a limitation clause is weak |
| 7 | Defined term, not a keyword | cuad-mini-050, *volume restrictions* | gold = definition `"Maximum Quantity" means [***] pounds…` at rank 18 | the restriction lives in a definition near the top of the contract; no shared words |
| 8 | Ground truth only loosely tied to the question | cuad-mini-068, *services after termination* | gold is a post-termination "shall not enter into an agreement with any other…" restriction; rank 5 | the gold text does not read as "services to be provided after termination"; CUAD's category and the templated question differ (hypothesis) |
| 9 | same | cuad-mini-019, *covenant not to sue* | gold is an employment-termination-on-reconstruction clause; rank 5 | same |
| 10 | Wrong sense of a shared word | cuad-mini-168, *anti-assignment* | gold "inure to the benefit of … successors and assigns" never in top 64; rank 1 concerns the "Approval Order" and the assumption of leases/contracts | "assignment" matches a different kind of assignment clause (hypothesis) |
| 11 | Generic section never matched | cuad-mini-167, *terminate for convenience* | gold (wind-down terms) never in top 64; rank 1 = "Section Headings" boilerplate | "convenience" matches the headings clause ("inserted for convenience only") |
| 12 | Right contract, key words differ | cuad-mini-085, *revenue/profit-sharing* | gold "Depomed shall pay promotion fees" never in top 64; rank 1 is about support for managed markets | "fees" vs "revenue" |
| 13 | Partial coverage of a multi-span answer | cuad-mini-057, *licenses granted* | 4 gold spans (2,159 chars); top results cover R@4 = 0.67 | one answer is spread over several paragraphs; short top-k cannot cover all |
| 14 | same | cuad-mini-161, *audit rights* | 2 spans; R@4 = 0.56 | same |
| 15 | False abstention | 7 answerable train queries withheld (cuad-mini-047, 053, 073, 123, 130, 133, 183) | 3 were also retrieval misses (047, 073, 130; e.g. 073 at confidence 0.073); **4 were hits** (053, 123, 133, 183) withheld at confidence 0.19-0.24, just under the 0.2401 threshold | the gate trades hits for abstentions at the 5% budget; the score distributions of answerable and unanswerable queries overlap heavily |
| 16 | False answer: invented contract, generic clause | unans-038 (conf 0.697) | answered with a real governing-law paragraph of an unrelated contract (Vitaminshoppe, 58392-58720) | the gate cannot tell that the named contract does not exist; a generic clause matches strongly anywhere |
| 17 | False answer: out of scope | unans-047 *credit rating of the joint venture* (conf 0.644) | answered with a joint-venture paragraph | word overlap ("joint venture") without the asked-for fact |
| 18 | False answer: absent clause | unans-001 (conf 0.273, threshold 0.2401) | amendment's opening paragraph returned for *sublicensing* | just above threshold |

By question type the score is very uneven (mean R@4 on train): governing law 0.94 (n = 17), anti-assignment 0.54 (10), expiration date 0.37 (19), cap on liability 0.41 (10), and 0.00 for non-compete, non-solicitation, most-favoured-nation, covenant-not-to-sue,
revenue sharing, volume restrictions and post-termination services. Lexical matching works where the clause uses the question's words and fails where it does not.

## 8. Limitations and next steps
- **Retrieval misses:** recall@4 = 0.45 means more than half of the gold text is not in the top 4; recall@64 = 0.91. Fixes I would test (none was run): dense or hybrid retrieval with a reranker; clause-type-specific query expansion ("expiration date" -> "term of this Agreement … years");
  neighbour expansion for near-misses (case 5). These are hypotheses, not results.
- **Abstention is not reliable.** On test it correctly abstains on 3 of 10 unanswerable questions, and on train 16 of 39. The scenario `unans-038` shows the gate can be *more* confident about an invented contract than about a real one. Ideas: a calibrated score of how well the named contract matched
  (the simple title-match variants I tried did not help alone, section 6), a learned gate with more labelled negatives, or a clarifying question to the user. Until then an empty result must not be read as "no such clause", and a non-empty result must not be read as "this clause exists".
- **Benchmark limits:** 54 and 10 test queries give wide intervals; split by query, not contract; CUAD labels are sometimes loosely tied to the question (cases 8-9); unanswerable labels rely on keyword checks; all contracts are English SEC exhibits as plain text.
- **Selection effects:** 20 candidates were compared on the same train queries; round 2 was designed after seeing one result; accepted gains (especially stemming, P = 0.92) probably over-state the true gain. Test is the honest figure, from one frozen run.
- **Title routing** relies on the user naming the contract in the benchmark's phrasing; a vague question would not benefit and a wrong title silently restricts the search to the wrong contract.
- **Document formats:** PDFs/scans, tables, amendments that modify other documents, definitions and cross-references ("as defined in Section 4.2") are not handled; the system does not resolve definitions or follow references.
- **Before legal users could rely on it:** an evaluation on their own contracts and question types, a far better abstention mechanism, human review of every answer, access control and audit logging, a privacy review (all processing is local and no model is used, which helps), versioned document ingestion and a plan for contracts longer and messier than these.
