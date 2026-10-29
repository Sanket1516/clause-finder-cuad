# Prompt 03 summary: baseline retrieval engine

## Implemented (`04_src/contract_intel/`)
| Responsibility | Module |
|---|---|
| Contract text, immutable, read in default text mode UTF-8 | `data/corpus.py`, `data/loader.py` |
| Chunks with document ID + original offsets; fixed / paragraph / clause chunkers | `chunking/__init__.py`, `common/schemas.py` |
| Lexical retrieval: BM25 written out in the repo (Lucene-style idf), deterministic ties | `retrieval/lexical.py` |
| Optional title routing | `retrieval/router.py` (off in the baseline) |
| Ranking: overlap removal, rank assignment | `ranking/postprocess.py` |
| Abstention with three distinct outcomes | `abstention/gate.py` |
| Serialisation with provenance | `common/schemas.py` (`SearchResponse`) |
| Configuration (YAML, `extends`, strict validation, hash) | `common/config.py` |
| Logging/timing | `common/logging.py` |
| Composition; `search(query: str)` is the only inference entry point | `pipeline.py` |

**Offsets.** Every chunk is a range over the untouched document, `text == document[start:end]` is asserted when the chunk is built,
and every returned passage is re-checked at evaluation time and again by the application layer. All 2,437 baseline chunks reproduce exactly.

**Why BM25 is in-repo instead of `rank_bm25`:** ~40 lines, no dependency, every term of a score is explainable in the debrief.

**Abstention states:** `no_candidates` (no query term occurs anywhere) · `below_threshold` (candidates exist, none clear the threshold) ·
`answered`. The wording never claims a clause is absent. Baseline threshold: calibrated on train **answerable** queries only so that at most 5%
are refused (28.37); unanswerable labels are not used for fitting.

**Inference isolation.** `Pipeline.search(query, k)` takes text only; a test inspects its signature and scans the inference modules for any
reference to gold/annotation structures.

## Baseline run (train only) — `03_experiments/baseline/`, `06_results/baseline_*`
Command: `python -m contract_intel evaluate --config baseline --split train --out-dir 03_experiments/baseline`
(also in `train_run_info.json`, with Python/platform/commit/timings). 140 answerable + 39 unanswerable train queries; wall time 0.8 s.

| k | recall | precision |
|---|---|---|
| 1 | 0.0000 | 0.0000 |
| 4 | 0.0213 | 0.0066 |
| 16 | 0.1731 | 0.0123 |
| 64 | 0.4282 | 0.0072 |

Abstention at threshold 28.37: false abstention 6/140 (4.3%); correct abstention 7/39 (17.9%).

## Tests
`test_pipeline.py` (provenance, offset reconstruction for all chunkers, stable ranking, empty candidates, invalid config, abstention,
serialisation, inference isolation). Full suite at this stage: 99 passed; no failures to report.

## Notes
- The baseline run's recorded commit (`961aa36`) predates the commit that added the engine code; the code was unchanged between the run and that commit.
- The baseline is deliberately naive: the whole question is the query. Its failure (the top passage is almost always a contract's cover
  page) is analysed in `baseline_failure_analysis.md` and motivated the loop's first candidates.
