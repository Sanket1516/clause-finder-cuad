# Commit map

The history was reworded once (messages only; same order, dates and file contents) before publication. Machine-written run records (`06_results/test_runs/ledger.jsonl`, `03_experiments/**/*run_info.json`, `experiment_log*.jsonl`, `final_freeze.json`, `final_comparison.json`) store the commit hashes that were current when they were written; map them here.

| Recorded (old) | Current | Time | Subject |
|---|---|---|---|
| `b1f3e64` | `389c644` | 21:00 | feat(data): add dataset pipeline, offset validation and frozen unanswerable set |
| `961aa36` | `26e9701` | 21:04 | docs(eval): amend protocol with actual split counts, failure taxonomy and calibration rule |
| `81eebd4` | `2900fd0` | 21:09 | feat(retrieval): add baseline BM25 engine, evaluator and baseline train results |
| `a9ee951` | `184bd1b` | 21:09 | docs(experiments): declare optimization objective and candidate catalogue |
| `42b51a5` | `3f69021` | 21:12 | feat(experiments): add improvement loop with acceptance rule and proposer |
| `33a06e3` | `3320f62` | 21:12 | test(experiments): tighten inconclusive-case assertion |
| `448b0b8` | `d571bba` | 21:14 | feat(experiments): run train-only improvement loop (15 iterations) and select final config |
| `905cc11` | `d0759eb` | 21:22 | feat(app): add CLI and Streamlit web app on a shared service; add demo docs |
| `4c5cd43` | `6bfb5e1` | 21:25 | feat(abstention): add title-match and coverage gate signals; declare round-2 objective |
| `a63a1eb` | `03fe08c` | 21:26 | feat(experiments): add round-2 abstention stage runner |
| `3f0ba4e` | `f1a6f5a` | 21:26 | feat(experiments): run round-2 abstention stage on train; adopt top1_norm gate |
| `20b0ac3` | `eea4282` | 21:47 | fix(eval): record test runs at evaluation start; isolate tests from real ledger |
| `de28438` | `2fdd7f0` | 21:47 | chore(release): freeze baseline and final configurations with checksums |
| `e08abb5` | `9cb9298` | 21:49 | feat(eval): run held-out evaluation for baseline and final; add --restart and final comparison |
| `7662e7f` | `e05da87` | 21:58 | fix(cli): check test-split guard before loading data |
| `2656e76` | `fd57f27` | 21:59 | fix(data): make download idempotent; add guard-order regression test |
| `9859d2b` | `7b68972` | 22:05 | docs: add README and REPORT; refresh demo scenarios |
| `fb9cde9` | `763691b` | 22:10 | docs(release): add audit, submission checklist, known issues, demo script and interview notes |
| `0665d17` | `d62aa63` | 22:13 | fix(security): raise explicit errors instead of asserts; add security audit |
| `a90954f` | `8648eff` | 22:22 | docs: shorten AI-tool disclosure |
| `5050e39` | `48180eb` | 22:22 | docs: remove organisation and recipient names from audit documents |
