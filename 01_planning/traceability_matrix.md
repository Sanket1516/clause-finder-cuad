# Requirement traceability matrix

Short labels only (full wording: git-ignored `00_assessment/assessment_requirements.md`). Paths: modules are relative to
`04_src/contract_intel/`, tests to `05_tests/`, configs to `03_experiments/configs/`. **Status: all Planned**; nothing is
implemented yet. P0 = blocking.

| ID | Label | Page | Pri | Module | Config | Automated test | Report artifact | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | Find the answering clause | 1–2 | P0 | `pipeline.py`, `retrieval/*`, `ranking/*` | `retrieval`, `ranking`, `chunking` | `integration/test_pipeline.py` | REPORT §Results | Planned |
| R-02 | Say when no clause exists | 1–2 | P0 | `abstention/gate.py` | `abstention` | `unit/test_gate.py`, `e2e/test_cli.py::abstain` | REPORT §Results (abstention) | Planned |
| R-03 | Evidence-driven improvement | 1, 3 | P0 | `experiments/*` | all | `integration/test_loop.py` | REPORT §Iteration history | Planned |
| R-04 | Deadline 08:00 IST 30 Oct | 1 | P0 | — | — | — | `09_submission/release_audit/audit.md` | Planned |
| R-06 | Private repo + collaborator invite (A-01) | 1, 4 | P0 | — | — | — | audit checklist | Planned |
| R-07 | Assumptions in README | 1 | P1 | — | — | — | README §Assumptions ← `assumptions.md` | Planned |
| R-08 | AI tool usage in README | 1 | P1 | — | — | — | README §AI tool usage | Planned |
| R-09 | Explainable/modifiable code | 1, 5 | P1 | all (small modules) | — | full suite | `08_demo/` rehearsal notes | Planned |
| R-10 | Correct dataset files, verified | 1 | P0 | `data/download.py` | `data.revision` | `unit/test_download.py` (checksum logic) | `02_data/manifests/data_manifest.json` | Planned |
| R-11 | Exactly 194 via `mini()` | 1–2 | P0 | `data/benchmark.py` | `data.mini_n` = 194 | `unit/test_mini.py` (vs reference impl; n; order hash) | manifest; REPORT §Evaluation setup | Planned |
| R-12 | Index only referenced contracts | 2 | P0 | `data/corpus.py` | — | `integration/test_corpus_scope.py` | manifest (doc list) | Planned |
| R-13 | UTF-8 text mode + offset check | 2 | P0 | `data/validate.py` | — | `integration/test_offsets_gold.py` | `02_data/validation/offset_validation.json` | Planned |
| R-14 | Mandated split function | 2, 5 | P0 | `data/splits.py` | — | `unit/test_splits.py` (vs reference impl) | manifest counts | Planned |
| R-15 | Train-only tuning; count test runs | 2 | P0 | `evaluation/evaluator.py` (guard, ledger) | — | `unit/test_test_guard.py` | `06_results/test_runs/ledger.jsonl` → REPORT | Planned |
| R-16 | ≥30 labelled unanswerables | 2 | P0 | `data/unanswerable.py` | — | `unit/test_unanswerable_schema.py` (count, fields, categories) | `02_data/unanswerable/*.jsonl` | Planned |
| R-17 | Same split for unanswerables | 2 | P0 | `data/splits.py` | — | `unit/test_splits.py` | manifest | Planned |
| R-18 | Frozen before the loop | 2 | P0 | lock file | — | `regression/test_unanswerable_frozen.py` (sha256) | git log; REPORT §Evaluation setup | Planned |
| R-19 | Report split counts | 2 | P1 | `data/unanswerable.py` | — | — | REPORT §Evaluation setup | Planned |
| R-20 | Ranked passages with doc + offsets | 2 | P0 | `common/schemas.py`, `ranking/postprocess.py` | `retrieval.candidates`, `evaluation.ks` | `unit/test_offsets.py` (INV-1 over all chunks), `unit/test_nms.py` | CLI/web screenshots | Planned |
| R-21 | Empty result + message | 2 | P0 | `abstention/gate.py`, `interfaces/*` | `abstention.*` | `e2e/test_cli.py` | screenshots | Planned |
| R-22 | Web app | 2 | P0 | `interfaces/webapp.py` | `--config` | `e2e/test_webapp_smoke.py` (Streamlit AppTest) | README §How to run; screenshots | Planned |
| R-23 | CLI | 2 | P0 | `interfaces/cli.py` | `--config` | `e2e/test_cli.py` (Typer CliRunner) | README §How to run | Planned |
| R-24 | >1 approach, metrics decide | 2 | P1 | `chunking/*`, `retrieval/*`, `ranking/*` | candidate configs | `integration/test_loop.py` | iteration log | Planned |
| R-25 | Choices in config | 2 | P1 | `common/config.py` | all YAML | `unit/test_config.py` (extra=forbid, inheritance, hash stability) | README §Architecture | Planned |
| R-26 | Messy-contract handling | 3 | P2 | `chunking/clause.py`, `retrieval/router.py` | `chunking.strategy`, `routing.mode` | `unit/test_clause_chunker.py` | REPORT §Limitations, §Error analysis | Planned |
| R-27 | LLM justification (if used) | 3 | C | — | `llm` (off) | — | REPORT §LLM use | Planned (no LLM) |
| R-28 | No committed keys | 3 | P0 | `.gitignore` | env vars | release-audit secret scan | audit | Planned |
| R-29 | Cached LLM outputs (if used) | 3 | C | `common/llm_cache.py` (only if used) | — | cache-hit test | — | Not applicable unless an LLM is used |
| R-30 | Report + demo exist | 3 | P0 | — | — | e2e tests | REPORT.md; demo | Planned |
| R-31 | Char P/R@k, train & test | 3 | P0 | `evaluation/metrics.py` | `evaluation.ks` | `unit/test_metrics.py` (hand cases + authors'-code parity) | REPORT §Results | Planned |
| R-32 | Abstention both directions | 3 | P0 | `evaluation/metrics.py` | `abstention.target_far` | `unit/test_abstention_metrics.py` | REPORT §Results | Planned |
| R-33 | Baseline recorded | 3 | P0 | `experiments/loop.py` (iter 0) | `baseline.yaml` | `regression/test_baseline_metrics.py` (pinned after first run) | REPORT §Results | Planned |
| R-34 | Objective declared first | 3 | P0 | — | `evaluation.primary_k` | — | `evaluation_protocol.md` (committed pre-baseline) → REPORT | Declared (uncommitted) |
| R-35 | One-command loop | 3 | P0 | `experiments/{loop,proposer,acceptance}.py` | `03_experiments/proposals/catalogue.yaml` | `integration/test_loop.py` (fixture corpus), `unit/test_acceptance.py` | REPORT §Iteration history | Planned |
| R-36 | Log every iteration | 3 | P0 | `experiments/loop.py` | — | `unit/test_iteration_log_schema.py` | `03_experiments/logs/iterations.jsonl` + `.md` | Planned |
| R-37 | ≥5 iterations | 3 | P0 | — | `loop.max_iterations` | count assertion in the release audit | iteration log | Planned |
| R-38 | Loop is train-only; no gold at inference | 4 | P0 | `evaluation/evaluator.py`, `pipeline.py` | — | `unit/test_test_guard.py`, `unit/test_pipeline_signature.py` | REPORT §Evaluation setup | Planned |
| R-39 | Train–test gap discussed | 4 | P1 | — | — | — | REPORT §Results | Planned |
| R-40 | Code for app, CLI, eval, loop | 4 | P0 | `04_src/` | — | suite | audit | Planned |
| R-41 | README sections | 4 | P0 | — | — | audit checklist | README.md | Planned |
| R-42 | REPORT sections | 4–5 | P0 | — | — | audit checklist | REPORT.md | Planned |
| R-43 | Log + baseline/final configs | 4 | P0 | — | `baseline.yaml`, `final.yaml` | audit | `03_experiments/` | Planned |
| R-44 | Unanswerable set in repo | 4 | P0 | — | — | R-16 tests | `02_data/unanswerable/` | Planned |
| R-45 | Tests for core pieces | 4 | P0 | — | — | `pytest` | audit (pytest output) | Planned |
| R-46 | Fresh-clone reproducibility + timings | 4 | P1 | `interfaces/cli.py` | — | fresh-clone dry run | README §Reproducing results | Planned |
| R-47 | No results in README | 4 | P2 | — | — | audit grep | README | Planned |
| R-48 | Readable report, n per figure | 5 | P1 | `evaluation/report_tables.py` | — | — | REPORT | Planned |
| R-49 | ≥10 failures grouped by cause | 5 | P0 | `evaluation/diagnose.py` | — | count assertion | REPORT §Error analysis | Planned |
| R-50 | No brief text in repo | 6 | P0 | `.gitignore` | — | audit grep of distinctive phrases | audit | Planned |
| R-51 | Confidentiality conduct | 5–6 | P0 | — | — | — | — | Ongoing |
| S-1 | LLM rewrite/rerank vs best non-LLM | 4 | O | — | `llm` | — | REPORT §LLM use | Deprioritised |
| S-2 | Hybrid + reranker | 4 | O | `retrieval/hybrid.py`, `ranking/rerank.py` | `retrieval.hybrid`, `ranking.reranker` | `unit/test_rrf.py` | iteration log | Loop candidate |
| S-3 | Clause-aware chunking / xref & definition resolution | 4 | O | `chunking/clause.py` | `chunking.strategy` | `unit/test_clause_chunker.py` | iteration log | Clause chunking = candidate; xref resolution deferred |

R-05 (Python), R-52 (frameworks) and R-53 (priority guidance) are design guidance; they are satisfied by the choices in
`architecture.md` and `implementation_plan.md` and need no tests.
