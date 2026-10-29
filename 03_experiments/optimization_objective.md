# Optimization objective (declared before the first experiment)

Status: **frozen**. This restates `01_planning/evaluation_protocol.md` section 5 (declared before any result existed) and adds the
inconclusive rule, the complexity rule and the catalogue policy. The only information used to order the catalogue is the
**baseline's train failure pattern**; no candidate had been run when this file was committed. Changes to this file after the first
experiment must be appended as dated amendments and may not be applied to experiments already run.

## Primary metric

**Character-level Recall@4 on train answerable queries (n = 140), ranking view, macro-averaged.**
Why: the product shows a person a few passages, and the costly legal error is missing the clause. k = 4 is a realistic reading
budget in the paper's k grid, and leaves room for multi-span answers. The ranking view keeps retrieval quality separate from the
abstention gate, so one component cannot hide the other's failure.

## Guardrails (each compared with the current accepted parent)

| ID | Guardrail | Maximum acceptable regression | Why |
|---|---|---|---|
| G1 | Precision@4 (train, ranking view) | new >= 0.90 x parent | stops "wins" that only come from returning longer text |
| G2 | Correct-abstention rate on the 39 train unanswerables, at the calibrated threshold | new >= parent - 1/39 (one query) | retrieval changes shift the score scale; abstention must not meaningfully degrade |
| G3 | Recall@1 (train, ranking view) | new >= parent - 0.02 | protects the first result a user sees |
| G4 | p95 warm per-query latency on this CPU | <= 2,000 ms | demo must stay interactive |
| G5 | Index build time | <= 900 s | reviewers must be able to reproduce results quickly |

## How abstention quality enters
Every candidate gets its own threshold, calibrated on the **answerable train queries only** so that at most 5% are refused
(target false-abstention rate, fixed for all candidates). Abstention quality is therefore measured by what that fixed false-abstention
budget buys: correct abstention on unanswerables (G2) and AUROC (reported, not gating). The unanswerable labels are never used to
fit a threshold, only to score it.

## Decision rule (applied by code in `contract_intel/experiments/acceptance.py`)

1. If any guardrail fails -> **rejected** (reason names the guardrail).
2. Else let delta = candidate R@4 - parent R@4 and p_gain = P(delta > 0) from a paired bootstrap over the 140 train queries
   (B = 2000, seed 0).
3. delta >= +0.010 **and** p_gain >= 0.90 -> **accepted** (becomes the new parent).
4. delta >= +0.010 but p_gain < 0.90 -> **inconclusive** (promising, not proven; parent unchanged, entry kept, not retried).
5. Otherwise (delta < +0.010) -> **rejected**. A tie keeps the simpler parent.

## Runtime and complexity
A candidate never earns an exception for being sophisticated: it must clear the same bar. Added components (dense model, reranker)
must additionally respect G4 and G5. Among changes that all pass, the loop adopts them one at a time in catalogue order, so the final
configuration is the sequence of accepted changes, each justified by its own train evidence.

## Catalogue policy (anti-p-hacking)
Candidates come from `03_experiments/proposals/catalogue.yaml`, written and committed before the first run. The proposer selects the
next untried entry whose `targets` match the most frequent failure label of the current parent on **train**. Entries are never added
after seeing results unless recorded as a dated amendment in the catalogue before they run. Because ~16 comparisons are made,
the report will treat accepted gains as optimistic and compare against the held-out test result once.

## Leakage rules enforced in code
- The loop evaluates with `purpose="development"` on `split="train"`; the evaluator raises for anything else.
- The pipeline receives only the question text; gold spans are used for scoring and display only.
- The frozen unanswerable file is verified against its sha256 lock at load time.
- Proposals use failure-label counts computed from train predictions only.
