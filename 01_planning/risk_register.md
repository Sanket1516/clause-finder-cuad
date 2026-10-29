> **Status note (added at release audit):** written *before* implementation as the plan. Where the built system differs (e.g. no dense/hybrid/reranker, no `rank_bm25`, two-round improvement process, `final_resolved.yaml`), the outcome is recorded in `decision_log.md`, `REPORT.md` and `09_submission/FINAL_AUDIT.md`. Checkboxes and statuses below are **not** updated.

# Risk register

L = likelihood, I = impact (H/M/L).

| ID | Risk | L | I | Mitigation | Owner/trigger |
|---|---|---|---|---|---|
| RK-01 | **Deadline** (~11 h total): unfinished report or demo → submission not reviewed | H | H | Phase plan with targets; demo moved before the loop; scope-cut list; REPORT skeleton generated from metrics files | Re-plan if any phase is >30 min late |
| RK-02 | Unanswerable query is actually answered by its contract (label noise) | M | H | Manual keyword search + read sections per query; rationale recorded; prefer clause types that are clearly absent; once frozen, defects are reported, not edited | Found later → report it |
| RK-03 | Unanswerables stylistically distinguishable from benchmark → inflated abstention | M | H | Same `Consider "<title>"; …` template and CUAD-style phrasing (A-07) | Inspect AUROC per category |
| RK-04 | Unanswerable set edited after the loop starts (breaks the rule) | L | H | Commit before the baseline; sha256 lock + regression test | Test fails on change |
| RK-05 | Test-set leakage (tuning on test, accidental runs) | M | H | Loop refuses `test`; test evaluation needs `--confirm-test`; append-only ledger | Ledger count >1 → explain |
| RK-06 | Gold spans leak into inference (e.g. router uses gold `file_path`) | L | H | `search(query: str)` signature; router only uses query text + corpus titles; signature test | Code review |
| RK-07 | Offset drift (CRLF, BOM, NFD path, enrichment text) | M | H | Read exactly as specified; hard validation gate; INV-1 property test over all chunks | Gate aborts |
| RK-08 | Metric mismatch vs paper (double-counting overlaps, wrong-doc denominator) | M | M | Parity test vs a port of the authors' code; NMS guarantees no overlap | Test |
| RK-09 | Train overfitting by the loop (≈136 queries, many candidates) | M | M | Paired bootstrap acceptance; pre-registered catalogue; report train–test gap honestly | Big gap → discuss |
| RK-10 | Abstention threshold calibrated on ~28 train unanswerables → unstable on test | H | M | 1-parameter gate; FAR-targeted calibration on 136 answerables (more stable); report CIs and the test gap | — |
| RK-11 | Few test unanswerables (~12) → wide CIs | H | M | Report counts and Wilson intervals; make ≥40 in total | — |
| RK-12 | CPU-only latency for dense/rerank | M | M | Small models, top-N limits, caching; G4 guardrail | Drop per scope cuts |
| RK-13 | Dependency install/model download failure on Windows | M | M | Pin versions; lexical path needs only pure-Python deps; models optional | Fallback to lexical |
| RK-14 | Confidential brief text committed | L | H | `.gitignore` for PDF and `00_assessment/`; paraphrase-only planning docs; release-audit grep for distinctive phrases | Audit |
| RK-15 | Secrets committed | L | H | No keys needed by default; `.env` ignored; secret scan | Audit |
| RK-16 | Public vs private repo ambiguity | M | M | Private repo + collaborator access (A-01) | User confirms |
| RK-17 | Live change in the debrief fails because the code is too clever | M | M | Small modules, configs, docstrings, tests; rehearse one change | — |
| RK-18 | Commit history required, but commits need user approval | M | H | Ask the user explicitly before Phase 2 to authorise commits (at least the unanswerable freeze) | Phase 2 start |
| RK-19 | HF mirror changes | L | M | Pin dataset revision; sha256 verification; manifest | Download step |
