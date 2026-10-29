# Prompt 01 summary: requirements traceability and architecture

## Outputs
| File | Content |
|---|---|
| `01_planning/traceability_matrix.md` | Every mandatory requirement → page, module, config, test, report artifact, status |
| `01_planning/architecture.md` | Single-process package; module responsibilities; data flow; config strategy; alternatives; resources |
| `01_planning/data_contracts.md` | Document, BenchmarkQuery, UnanswerableQuery, Chunk, RetrievedPassage, SearchResponse, QueryPrediction, ExperimentRecord, TestRunLedgerEntry; invariants INV-1…INV-6 |
| `01_planning/evaluation_protocol.md` | Selection, splits, metric definitions (authors' semantics), abstention metrics + calibration, **primary metric / guardrails / acceptance rule**, diagnosis taxonomy, test-set policy, reproducibility |
| `01_planning/{implementation_plan, assumptions, risk_register, decision_log, definition_of_done}.md` | Updated |

## Key design points
- Offsets are first-class. Chunks are ranges over immutable original text; enrichment goes to `index_text` only;
  INV-1 is tested over every chunk.
- Primary metric = **train Recall@4** (ranking view). Guardrails: Precision@4 ≥ 0.9× parent, CAR at FAR ≤ 5% (≤ 1-query
  drop), Recall@1 (≤ 0.02 drop), p95 latency ≤ 2 s, build ≤ 15 min. Acceptance: Δ ≥ +0.01 and paired-bootstrap
  P(Δ > 0) ≥ 0.90. All of this was declared before any result.
- Baseline: 500-char fixed chunks, BM25, top-1-score gate calibrated on train.
- Loop: rule-based proposer over a pre-registered catalogue keyed on failure labels.
- One planned test run (baseline + final together), recorded in a ledger.
- Plan deviation: a minimal demo comes right after the baseline, per the brief's priority guidance.

## Acceptance criteria check
- Every mandatory requirement has a planned implementation and verification: yes, see the traceability matrix
  (R-04/R-06/R-51 are verified manually).
- Source offsets are preserved by design: INV-1/INV-2.
- Train/test are separated: guard + ledger + split recomputed from text.
- The improvement loop is reproducible: config hashes, pinned seeds, append-only logs.

## Unresolved decisions (need the user)
D-OPEN-1 … D-OPEN-5 in `decision_log.md`: repo location, committing the planning docs, **authorising git commits** (needed
before the loop for the unanswerable freeze), private vs public, optional local LLM.

## Not verified yet
- Corpus size, document count and split counts (Phase 1).
- Feasibility of dense/rerank latency on this CPU.
