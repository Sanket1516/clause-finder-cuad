# Evaluation protocol

**Status: declared before any experiment has been run.** No metric value has been observed yet. This file is committed
before the baseline runs. Later changes to it must be appended as dated amendments, never silent edits.

## 1. Benchmark selection (deterministic)

1. Download `benchmarks/cuad.json` and `corpus/cuad/` from `awinml/legalbench-rag`. Verify sha256 against the mirror's
   `SHA256SUMS`, then record the revision (commit hash) in `02_data/manifests/data_manifest.json`.
2. `tests = json.loads(Path("benchmarks/cuad.json").read_text(encoding="utf-8"))["tests"]`
3. `cuad_mini = mini(tests, n=194)`, implemented exactly as the authors' function. Sort key: `random.seed(t["snippets"][0]["file_path"]); random.random()`.
   Python 3 string seeding is deterministic across runs and versions. A unit test pins it: n = 194, plus a sha256 of the
   ordered query list stored in the manifest.
4. `query_id = cuad-mini-{i:03d}` by position in `cuad_mini`.
5. Indexed corpus = the set of distinct `snippets[*].file_path` across the 194 queries. Paths are NFC-normalised (A-13).
   No other CUAD file is indexed.
6. **Offset validation (hard gate):** for every snippet, `doc[start:end] == answer`, where
   `doc = Path(p).read_text(encoding="utf-8")`. Any mismatch aborts the pipeline. The result is written to
   `02_data/validation/offset_validation.json`. We also record per query that spans are disjoint and in the same document.

## 2. Splits

- `assign_split(query)`, exactly as given: sha256 of `query.strip()`, `int(hex, 16) % 10 < 3 → "test"`. It applies to
  benchmark *and* unanswerable queries. The split is never stored by hand; it is always recomputed.
- Counts (train/test × answerable/unanswerable) are written to the manifest and copied into the REPORT.
- **Train** is used for all development, tuning, threshold calibration and the improvement loop.
- **Test** is used only for final reporting (§7).
- No sub-splits are planned. If the loop needs one, it is carved out of train (permitted) and documented as an amendment.

## 3. Retrieval metrics (LegalBench-RAG definition, A-02/A-03)

For a query with gold spans G (one document) and the top-k returned passages R_k (non-overlapping per document, INV-4):

- `overlap_k` = Σ over returned passages p in the gold document, Σ over gold spans g, of |p ∩ g|
- `precision@k` = overlap_k / Σ_p |p|. Wrong-document characters count in the denominator. If nothing is returned, precision = 0.
- `recall@k` = overlap_k / Σ_g |g|
- k ∈ {1, 2, 4, 8, 16, 32, 64}. Macro-averaged over queries. Reported separately for train and test, always with n.
- **Ranking view:** computed on `ranked_candidates` (before the abstention gate).
- **End-to-end view:** computed on `passages`. An abstained answerable query scores 0/0.
- Secondary diagnostics (not used for acceptance): document hit@k (any passage from the gold document), MRR of the first
  overlapping passage, and mean returned characters@k.
- Parity test: on hand-built fixtures, our metric equals a direct port of the authors' `QAResult.precision/recall`.

## 4. Abstention metrics

The gate abstains when `confidence < τ`. Abstained means nothing is returned and the response says so.

| Metric | Population | Definition |
|---|---|---|
| False abstention rate (FAR) | answerable benchmark queries | #abstained / #answerable |
| Correct abstention rate (CAR) | unanswerable queries | #abstained / #unanswerable |
| False answering rate (FAnsR) | unanswerable queries | 1 − CAR |
| CAR by category | absent_clause / not_in_corpus / out_of_scope | same, per category |
| AUROC of `confidence` | answerable vs unanswerable | threshold-free separability diagnostic |

**Threshold calibration (train only, automatic, part of every evaluation):** τ = the largest value such that
train FAR ≤ `abstention.target_far` (config; default **0.05**). We then report CAR at that τ. Because τ is fitted on train,
train abstention numbers are optimistic in-sample estimates. The test numbers are the honest ones; the REPORT says so.
The calibrated τ is frozen into the final config before the test run.

## 5. Objective, guardrails and acceptance rule (declared a priori)

**Primary metric: train ranking-view character Recall@4** (macro over train benchmark queries).

Why:
- The product is "show me the clause". A user reads a handful of passages, and k = 4 is a realistic reading budget.
  It is also in the paper's grid and leaves room for multi-snippet answers (≈29% of CUAD queries have several spans).
- Recall measures "did we surface the answering text". Missing the clause is the costly error in legal review.
  Extra text costs reading time, which precision captures as a guardrail.
- We use the ranking view so the primary metric isolates retrieval quality. Abstention gets its own guardrail, so one
  component's failure can't hide behind the other.

**Guardrails** (each candidate is compared with the current accepted *parent*):

| ID | Guardrail | Rule | Why |
|---|---|---|---|
| G1 | Precision@4 (train, ranking view) | new ≥ 0.90 × parent | Stops "wins" that come only from returning longer passages (bigger chunks inflate Recall@k). |
| G2 | CAR at target FAR (train, calibrated) | new ≥ parent − 1 query (≈ one unanswerable) | Retrieval changes alter the score distribution. Abstention must not get meaningfully worse. |
| G3 | Recall@1 (train, ranking view) | new ≥ parent − 0.02 | Protects the top result shown first in the UI. |
| G4 | p95 warm query latency (CPU) | ≤ 2,000 ms | The demo must stay interactive on a laptop CPU. |
| G5 | Index build time | ≤ 15 min | Reviewers must be able to reproduce the results within the time stated in the README. |

**Acceptance rule:** a candidate is **accepted** iff all of the following hold:
1. ΔRecall@4 = new − parent ≥ **+0.010** (absolute);
2. a paired bootstrap over train queries (B = 2,000, seed = 0, resampling query IDs) gives P(Δ > 0) ≥ **0.90**;
3. G1–G5 all pass.

Otherwise it is **rejected**. An accepted candidate becomes the new parent. Equal scores → reject (keep the simpler
parent). The rule is applied by code (`experiments/acceptance.py`) and the decisive clause is logged.

Why: about 136 train queries is small, so per-query recall is noisy and a raw "higher is better" rule would accept noise.
The paired bootstrap uses the same queries for both arms, which removes between-query variance. 0.90 rather than 0.95
balances false accepts against a short loop (≥5 iterations). The test set is the final arbiter, and the REPORT discusses
multiple-comparison risk.

## 6. Diagnosis taxonomy (used by the loop's proposer and by the REPORT's error analysis)

Per answerable train query, in the ranking view at k = 4 (and with candidates up to 64 for the "rank" labels):

| Label | Condition | Typical fix candidates |
|---|---|---|
| `hit` | recall@4 ≥ 0.99 | — |
| `partial_span` | 0 < recall@4 < 0.99 | overlap, larger/merged chunks, neighbour expansion, sentence-boundary chunking |
| `right_doc_wrong_section` | a top-4 passage is in the gold doc but overlap = 0, and gold is overlapped somewhere in the top 64 | reranker, hybrid, heading context, clause-aware chunking |
| `wrong_document` | no top-4 passage is in the gold doc | title routing / document filter, hybrid |
| `not_retrieved` | no overlap anywhere in the top 64 | vocabulary mismatch → dense/hybrid, query expansion |
| `false_abstention` | end-to-end: gate abstained (orthogonal flag) | confidence signal / calibration |

Per unanswerable query: `correct_abstention` or `false_answer` (+ category).

## 7. Test-set usage

- The loop and all tuning code refuse `split="test"` (guard + test).
- Final reporting = **one** planned test run that evaluates the frozen baseline config and the frozen final config
  together. Every test evaluation, planned or accidental, is appended to `06_results/test_runs/ledger.jsonl`.
  The REPORT states the ledger count.

## 8. Runtime and reproducibility

Each evaluation records:
- index build time;
- per-stage query latency (p50/p95, warm, single process);
- total wall time;
- config hash; git commit; dataset manifest hash; Python and package versions (`pip freeze` snapshot);
- OS/CPU; random seeds.

Model downloads are pinned by Hugging Face revision. LLM outputs (if any) are cached by `sha256(model + prompt)`, so
reruns make no model calls. Re-running an evaluation with the same config and commit must reproduce the metrics exactly.
A regression test pins baseline train metrics after the first run.

---

## Amendment 1 (2026-10-29, written and committed BEFORE any retrieval metric was computed)

1. **Actual counts** (Prompt 02): benchmark train 140 / test 54; unanswerable train 39 / test 10. Wherever this document says
   "about 136 train queries" read 140. The acceptance rule, thresholds and guardrails are unchanged.
2. **Diagnosis taxonomy refined** (replaces the table in section 6; evaluated at k = primary_k over the top-64 non-overlapping candidates):
   `hit` (recall@k >= 0.99), `partial_span` (0 < recall@k < 0.99), `ranked_too_low` (recall@k = 0 but a candidate at rank > k overlaps gold),
   `right_doc_wrong_section` (gold never overlapped in top 64; top-1 passage is in the gold document),
   `wrong_document` (gold never overlapped in top 64; top-1 passage is in another document), `no_candidates`, `ingestion_failure`
   (returned text != document[start:end]). Flags: `ambiguous_ground_truth` (gold > 40% of the document or < 15 chars), and in the
   end-to-end view `false_abstention`. Unanswerable: `correct_abstention` / `false_answer`.
   "Incorrect source offsets" is covered by `ingestion_failure`, which is checked for every returned passage of every query.
3. **Abstention calibration uses answerable queries only**: tau = the (floor(target_far*n)+1)-th smallest top-signal value among the
   n answerable TRAIN queries. No unanswerable label is used to fit tau, which keeps the 39 train unanswerables a clean estimate.
4. Candidate pool: `retrieval.candidates` = number of chunks kept before overlap removal; evaluation reads at most 64 passages.
