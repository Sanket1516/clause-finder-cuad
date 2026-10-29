# Prompt 05 summary: evidence-driven improvement loop (train only)

## Setup before the first experiment (committed in `a9ee951`, loop code in `42b51a5`)
- `03_experiments/optimization_objective.md`: primary metric = train ranking-view **character recall@4** (n = 140); guardrails G1-G5; accept iff
  ΔR@4 ≥ +0.010 and paired-bootstrap P(gain) ≥ 0.90 and all guardrails pass; inconclusive / rejected otherwise; ties keep the simpler parent.
- `03_experiments/proposals/catalogue.yaml`: 15 candidates, written from the baseline's train failure pattern, ordered by target failure label.
- Command: `python 03_experiments/run_improvement_loop.py` — restartable (state = append-only `experiment_log.jsonl`); re-running it after completion added no lines.

## Result (train; `experiment_summary.md`, `experiment_log.jsonl`, `improvement_history.csv`, `train_comparison.json`)
15 iterations beyond baseline: **3 accepted, 12 rejected, 0 inconclusive.**

| # | change | R@4 | ΔR@4 | P(gain) | decision (reason) |
|---|---|---|---|---|---|
| 0 | baseline | 0.0213 | | | |
| 1 | strip title prefix | 0.0485 | +0.027 | 0.94 | **rejected**: G2 (correct abstention 0.179 → 0.026) |
| 2 | route to contract by title, rank inside it | 0.3086 | +0.287 | 1.00 | **accepted** |
| 3 | soft routing (boost) | 0.2884 | −0.020 | 0.00 | rejected (G2) |
| 4 | English stopwords | 0.2829 | −0.026 | 0.12 | rejected |
| 5 | 300-char chunks | 0.2497 | −0.059 | 0.00 | rejected |
| 6 | 1000-char chunks | 0.3995 | +0.091 | 1.00 | rejected: G1 (precision@4 0.064 → 0.049 < 0.9×) |
| 7 | paragraph-aware chunks (≤800) | 0.4122 | +0.104 | 1.00 | **accepted** |
| 8 | clause/heading-aware chunks | 0.3764 | −0.036 | 0.02 | rejected (G1, G3) |
| 9 | light stemming | 0.4483 | +0.036 | 0.92 | **accepted** |
| 10 | BM25 k1 = 1.0 | 0.4412 | −0.007 | 0.18 | rejected |
| 11 | BM25 b = 0.9 | 0.4391 | −0.009 | 0.09 | rejected |
| 12 | abstention signal = top1 / query idf mass | 0.4483 | 0.000 | — | rejected (no change in primary metric) |
| 13 | abstention signal = margin | 0.4483 | 0.000 | — | rejected (G2) |
| 14 | 100-char overlap | 0.4483 | 0.000 | — | rejected — a **no-op** (overlap only affects fixed chunks; parent uses paragraph chunks) |
| 15 | expand passages ±100 chars | 0.4424 | −0.006 | 0.31 | rejected (G1) |

**Selected (best on train): `final` = title routing + paragraph chunks + light stemming** (`03_experiments/configs/final.yaml`, frozen threshold in `final_resolved.yaml`).
Train, baseline → final: R@1 0.000 → 0.214 · R@4 0.021 → **0.448** · R@16 0.173 → 0.719 · R@64 0.428 → 0.909 · P@4 0.007 → 0.075 · false abstention 4.3% → 5.0% ·
correct abstention 17.9% → 20.5% · AUROC 0.55 → 0.63 · p95 latency 4 ms → 2 ms. These are **train** numbers, optimistic by construction (15 comparisons, one split).
**The held-out test split was not run** (no ledger entry).

## Findings the report must carry (honest)
1. **Abstention regressed where it matters most.** Correct abstention on never-indexed contracts fell from 7/7 (baseline) to **1/7**: routing always lands
   on some contract and the gate has no notion of title-match quality. The aggregate guardrail G2 did not catch it because absent-clause abstentions rose
   (0/26 → 6/26). Overall the final system still gives passages for 31 of 39 unanswerable train queries.
2. **My rule cannot accept abstention-only changes.** Iteration 12 doubled correct abstention (0.205 → 0.410; AUROC 0.633 → 0.737; 3/7 never-indexed recovered)
   but was rejected because the pre-declared primary metric (ranking-view recall) cannot move when only the gate changes. I did not change the rule retroactively.
   Adopting this signal now would be a **post-hoc, train-only** decision and must be labelled as such.
3. Iteration 14 was a no-op and iterations 12-13 only touched the gate, so the number of *retrieval* experiments that could change R@4 is 12, not 15.
4. Title routing assumes the user names the contract (every benchmark query does; document hit@1 is 140/140 on train). That is a property of the benchmark's
   phrasing, not evidence the system finds the right contract for a vague question.
5. Multiple comparisons: 15 candidates were compared on 140 queries; accepted gains should be expected to shrink on test. Stem-light (P(gain) 0.92) is the most borderline acceptance.

## Leakage checks
Loop calls `evaluate(..., purpose="development")` on `train` only (guard test + source-text test); gold is used for scoring only; the frozen unanswerable file is
verified against its lock at load; proposals use train failure counts only. `git`: no test artifacts exist anywhere.
