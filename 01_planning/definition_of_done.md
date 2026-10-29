# Definition of done

A box is ticked only with evidence: a file path, a test name or command output. "Should work" doesn't count.

## Data
- [ ] 194 CUAD-mini queries selected with the authors' `mini()`; ordered-query hash in the manifest
- [ ] Indexed documents == documents referenced by those queries (test)
- [ ] 100% of gold snippets pass `doc[start:end] == answer` (validation report)
- [ ] Split counts (train/test) recorded for benchmark and unanswerable queries
- [ ] ≥30 (target ≥40) labelled unanswerable queries with rationale; committed **before** the baseline run; lock-hash test green; untouched afterwards (git log)

## System
- [ ] `Pipeline.search(query: str)` returns ranked passages with `doc_id`, `start`, `end`, `text`, `score`, `rank`
- [ ] INV-1 offset test passes over every chunk of every config used
- [ ] Abstention returns an empty list *and* an explicit message with a reason
- [ ] All pipeline choices come from YAML config; `baseline.yaml` and `final.yaml` committed
- [ ] CLI: `prepare`, `index`, `search`, `evaluate`, `loop` work from a fresh clone
- [ ] Streamlit app runs and shows both an answer case and an abstention case (screenshots in `08_demo/screenshots/`)

## Evaluation and loop
- [ ] Char-level P/R@k for k ∈ {1,2,4,8,16,32,64}, train and test, with n; parity test against the authors' formula
- [ ] FAR, CAR and false-answer rate on train (development) and test (final)
- [ ] Primary metric + guardrails + acceptance rule committed before the baseline (`evaluation_protocol.md`)
- [ ] Single-command loop; ≥5 logged iterations beyond the baseline, each with change, rationale, metrics, proposer, decision
- [ ] Loop never touches test (guard test)
- [ ] Test ledger exists; the REPORT states the number of test runs

## Docs
- [ ] README: Overview, Setup, How to run, Architecture, Reproducing results (with timings), Assumptions, AI tool usage; no results in it
- [ ] REPORT: Summary, System design, LLM use, Evaluation setup, Results (baseline vs final × train/test with n), Iteration history, Error analysis (≥10 failures by cause), Limitations & next steps; train–test gap discussed

## Release
- [ ] `pytest` green (output saved in the audit)
- [ ] Fresh-clone reproduction of the train metrics matches the REPORT
- [ ] No secrets, no PDF, no brief text in the repo (audit greps)
- [ ] Private GitHub repo; collaborator access for the reviewers; link emailed before 08:00 IST 30 Oct
- [ ] No claim of production readiness
