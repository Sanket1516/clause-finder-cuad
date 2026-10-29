# Prompt 04 summary: evaluation and failure analysis

## Where things are (adapted to the existing package layout)
| Requested | Actual |
|---|---|
| `04_src/evaluation/` | `04_src/contract_intel/evaluation/` (`metrics.py`, `evaluator.py`, `diagnose.py`, `guard.py`) |
| `04_src/analysis/` | `04_src/contract_intel/analysis/failure_report.py` |
| `05_tests/test_metrics.py`, `test_evaluation.py` | as requested |
| baseline outputs | `06_results/baseline_train_metrics.json`, `baseline_predictions.jsonl`, `baseline_failure_analysis.md` (originals kept in `03_experiments/baseline/`; copies never overwrite) |

## Metric definitions (documented in `metrics.py`)
- Ground truth: the query's gold spans in one document, disjoint. Prediction: top-k returned passages `(document, [start,end))`.
- precision@k = overlapping characters / **all** returned characters (wrong-document text counts against precision);
  recall@k = overlapping characters / all gold characters; multiple gold spans are pooled. Macro-average over queries.
- Nothing returned -> precision 0 (authors' convention). Zero gold characters -> recall 0 (never occurs).
- Overlapping or repeated predictions: unioned per document first, so overlap cannot inflate scores. Identical to the authors' formula when
  passages don't overlap (tested against a port of their code). **This union step is my assumption, not part of the published definition.**
- Not claimed as official: the paper's multi-source equal weighting (one source here); k grid 1,2,4,8,16,32,64 taken from the authors' code.
- Hand-calculated tests cover perfect, partial, over-long, wrong-document, multi-span, empty, inverted-interval, overlapping and repeated cases.

## Abstention evaluated separately (decision-level, never mixed into character metrics)
Confusion matrix with explicit denominators: answerable answered / **false abstention** / **false answer** / correct abstention; precision, recall, F1
of both the "answer" and "abstain" decisions; false-abstention, correct-abstention and false-answer rates; AUROC of the confidence signal;
per-category counts. Two retrieval views are saved: *ranking* (before the gate) and *end-to-end* (abstained answerable queries score 0).

## Per-query evidence
`*_predictions.jsonl`: query ID, split, query, answerability and category, decision, confidence, threshold, top-64 passages with offsets and
scores, gold (key named `gold_for_evaluation_only`), per-k metrics in both views, failure label, first-overlap rank, flags, latency, experiment and config IDs.

## Failure taxonomy
hit · partial_span · ranked_too_low · right_doc_wrong_section · wrong_document · no_candidates · ingestion_failure (offset mismatch) ·
ambiguous_ground_truth (flag) · false_abstention · false_answer · correct_abstention. (Protocol Amendment 1, committed before any metric.)
**Baseline, train, 140 answerable:** ranked_too_low 71 · right_doc_wrong_section 59 · partial_span 9 · hit 1. Reviewable examples with gold text and
the returned passages: `06_results/baseline_failure_analysis.md`. Zero queries were flagged ambiguous; zero ingestion failures.

## Split protection
`evaluate()` takes an explicit split and purpose. `development` can only ever see `train`; `test` needs `purpose="final"` **and** `--confirm-test`
and writes an append-only ledger (`06_results/test_runs/ledger.jsonl`). Queries whose own split label differs from the requested split are rejected.
**The test split has not been evaluated** (no ledger exists).

## Verification
Metric, evaluator, guard and taxonomy tests pass (part of the 161-test suite). I also hand-checked three baseline queries (gold span vs returned
offsets vs recorded per-query overlap) before trusting the baseline numbers.
