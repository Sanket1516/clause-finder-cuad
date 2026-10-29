# Implementation plan

Time budget: planning finished ≈ 21:15 IST Thu 29 Oct; the hard deadline is **08:00 IST Fri 30 Oct**. Times below are
targets, with ~1.5 h of buffer kept at the end.

## Ordering and the one deviation

Requested order: data → baseline → evaluation → improvement → CLI/web → report/release.

**Deviation:** a *minimal* CLI and web app move ahead of the improvement loop, to straight after the first baseline
evaluation.
1. The brief says submissions without a working demo are not reviewed, and its FAQ says to prioritise demo + report,
   then the loop.
2. The interfaces only call `Pipeline.search()`, so they don't depend on the loop. Every later config improves them for free.

Evaluation code is built *with* the baseline rather than after it: the baseline is defined by its measured train metrics.

## Phases

| # | Phase (prompt) | Target | Deliverables | Exit check |
|---|---|---|---|---|
| 0 | Discovery + architecture (P00–P01) | done 21:15 | `01_planning/*` | this summary |
| 1 | **Data preparation** | 22:00 | `pyproject.toml`, `data/*`, download script, `02_data/manifests/data_manifest.json`, `02_data/validation/offset_validation.json`, unit tests for `mini`, `assign_split`, offsets | 194 queries; 100% offsets match; split counts recorded; doc set == referenced set |
| 2 | **Unanswerable set + freeze** | 23:00 | ≥40 queries in JSONL with rationale + manual absence checks; lock hash; `evaluation_protocol.md` | **git commit** of set + protocol *before any metric is computed*; split counts recorded |
| 3 | **Baseline + evaluation** | 00:30 | schemas, config loader, fixed chunker, BM25, NMS, gate + calibration, metrics (with parity test), evaluator + test guard + ledger, diagnosis; `baseline.yaml`; iteration 0 logged | train metrics for baseline; offset invariant test over all chunks green |
| 4 | **Minimal demo** | 01:30 | Typer CLI (`prepare/index/search/evaluate`); Streamlit app showing ranked passages + offsets + abstention message | manual smoke + CLI e2e test; screenshot |
| 5 | **Improvement loop** | 03:30 | acceptance rule, catalogue, proposer, `loop` command; ≥5 iterations logged (expect several rejections) | `iterations.jsonl` ≥6 lines (baseline + 5); `final.yaml` |
| 6 | **Final test run + analysis** | 05:00 | one ledger-recorded test run of baseline + final; error analysis (≥10 failures by cause); charts | ledger count = 1 (or justified) |
| 7 | **REPORT + README** | 06:15 | `REPORT.md` (8 sections), `README.md` (7 sections) | section checklists |
| 8 | **Release audit + submission** | 06:30 | secret scan, brief-text scan, fresh-clone reproduction, `pytest`, GitHub private repo + collaborator invite | `09_submission/release_audit/audit.md` |
| — | Buffer | 06:30–08:00 | — | — |

## Loop candidate catalogue (pre-registered; finalised in Phase 5 *before* running)

Each candidate targets a failure label. The order within a label is fixed in advance.

| Target label | Candidates |
|---|---|
| `wrong_document` | title routing `boost` → `filter`; |
| `partial_span` | overlap 0 → 25%; chunk size grid {300, 800, 1200}; sentence-snapped chunks; neighbour expansion |
| `right_doc_wrong_section` | clause-aware chunking; heading context in `index_text`; cross-encoder rerank of top-50 |
| `not_retrieved` | hybrid BM25 + dense (RRF); stopword/stemming tokenizer variants; query template stripping |
| abstention (G2) | confidence = margin / routing-aware combined signal |

## Scope cuts if behind schedule (in this order)

1. Drop the dense/hybrid candidates (stay lexical + rerank).
2. Drop the cross-encoder.
3. Web app: keep it minimal (no highlighting).
4. Never cut: offset validation, unanswerable freeze-before-loop, test guard, ≥5 logged iterations, REPORT, demo.
