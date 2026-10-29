# Final audit

Audit date: 2026-10-29 (IST evening). Repository HEAD at audit start: `9859d2b`. Auditor: the same AI assistant that built the project, so this is **self-review, not independent review**;
where a check needs a human or an external action it is marked NOT VERIFIED. The assessment document is not in this repository; requirement IDs (R-xx) come from a private, git-ignored catalogue
and are described in words here. Status: PASS = executed or inspected with evidence; PARTIAL; FAIL; NOT VERIFIED.

## 1. Requirement checklist
| ID | Requirement | Evidence / verification | Result | Status | Action |
|---|---|---|---|---|---|
| R-01/R-20 | Ranked passages with document + character offsets | `pytest 05_tests/test_pipeline.py test_application.py` ; CLI `search --json` | offsets reproduce text (test + runtime check on every display); 0 offset violations in 49 metric files | PASS | — |
| R-02/R-21 | Say so when nothing is relevant | CLI exit code 10, web warning state; `test_cli.py`, `test_application.py` | works; but the gate is weak (REPORT s5, s8) | PASS (behaviour) / quality limited | disclosed |
| R-03 | Measured, evidence-driven improvement | `experiment_log*.jsonl`, REPORT s6 | 15 + 5 logged iterations | PASS | — |
| R-04 | Deadline 08:00 IST Fri 30 Oct | not yet submitted | — | NOT VERIFIED | user submits before the deadline |
| R-05 | Python | Python 3.11.9 | — | PASS | — |
| R-06 | Repo link to the recipient named in the brief; **private + collaborator access** per logistics section, but the deliverables section says "public" | not done; user asked for a public repo on `Sanket1516`; repo did not exist at audit time | **Inconsistency in the brief, flagged**; I could not create the repo (no credentials) | NOT VERIFIED | user decides visibility; see SUBMISSION_CHECKLIST |
| R-07 | Assumptions documented | README s9, `01_planning/assumptions.md` | present | PASS | — |
| R-08 | AI tool usage noted in README | README s10 | stated; **contains a placeholder the candidate must complete** | PARTIAL | candidate edits README s10 |
| R-09 | Candidate can explain/modify all code | `08_demo/interview_preparation.md` | cannot be verified by me | NOT VERIFIED | candidate rehearses; see KNOWN_ISSUES |
| R-10 | Correct dataset, verified | `python 02_data/download_data.py` (fresh clone) | sha256 verified vs mirror; revision pinned | PASS | — |
| R-11 | Exactly 194 queries via `mini()` | `test_dataset.py`; manifest | 194 over 29 contracts; ordered-query hash recorded | PASS | — |
| R-12 | Index only referenced contracts | `test_only_referenced_contracts_are_indexed` | corpus folder == 29 referenced files | PASS | — |
| R-13 | UTF-8 default text mode; `doc[start:end] == answer` | `python 02_data/validate_offsets.py` | 272/272 exact | PASS | — |
| R-14/R-17 | Prescribed split, also for unanswerables | `test_assign_split_*`; manifests | benchmark 140/54; unanswerable 39/10 | PASS | — |
| R-15 | Tune on train only; count test runs | `evaluation/guard.py`, ledger, `test_evaluation.py`, `test_cli.py` | guard enforced; **4 test evaluations started, 2 recorded, 2 earlier aborted/unseen** (PROMPT_07_SUMMARY s4) | PASS (with disclosure) | — |
| R-16/R-44 | >= 30 labelled unanswerables in repo | `validate_unanswerable.py`, `test_unanswerable_*` | 49 | PASS | — |
| R-18 | Committed before the loop, never edited | `git log -- 02_data/unanswerable_queries.jsonl`; sha256 lock test | one commit `b1f3e64` (21:00); first experiment commit `448b0b8` (21:14) | PASS | — |
| R-19 | Report unanswerable counts per split | REPORT s4 | 39 / 10 | PASS | — |
| R-22 | Web app | `test_application.py` (headless Streamlit), real server health 200 | works; **layout never inspected in a browser** | PASS (functional) | look at it before the demo |
| R-23 | CLI | `test_cli.py`; exit codes checked in fresh clone | works | PASS | — |
| R-24/R-25 | >1 approach tried; config-driven | iteration log; `common/config.py` strict schema | chunkers, tokenisers, routing, gates tried; no hard-coded pipeline choices | PASS | — |
| R-26 | Consider messy-contract issues (cross-references, definitions, formatting, missing contracts) | REPORT s7-s8 | discussed with failure cases; **not implemented** (no cross-reference/definition resolution) | PASS (discussed) / feature absent | disclosed |
| R-27/R-29 | LLM justification / caching | REPORT s3 | no LLM used | NOT APPLICABLE | — |
| R-28 | No keys committed | secret-pattern scan of full history | 0 matches; no key is needed | PASS | — |
| R-30 | Report and demo exist | REPORT.md; CLI + web | present | PASS | — |
| R-31 | Char P/R at several k, train and test | `evaluation/metrics.py`, `test_metrics.py` (hand cases + port of authors' formula) | k = 1..64 reported with n | PASS | — |
| R-32 | Abstention in both directions | metrics + REPORT s5 | reported with denominators | PASS | — |
| R-33 | Baseline recorded | `03_experiments/baseline/`, iteration 0 | train and test metrics saved | PASS | — |
| R-34 | Objective declared before iterating | `03_experiments/optimization_objective.md` commit `a9ee951` precedes `448b0b8` | **round 2 was declared after seeing one result (post hoc), disclosed** | PASS (with disclosure) | — |
| R-35 | One-command loop | `python 03_experiments/run_improvement_loop.py` (fresh clone, `--restart`) | 13 s; reproduced all decisions | PASS | — |
| R-36/R-37 | Every iteration logged; >= 5 | `experiment_log.jsonl` (16 lines), `experiment_log_round2.jsonl` (6) | hypothesis, proposer, metrics, decision per line | PASS | — |
| R-38 | Loop train-only; no gold at inference | `test_inference_modules_never_reference_gold_annotations`, signature test, guard tests | enforced in code and tests | PASS | — |
| R-39 | Train-test gap discussed | REPORT s5 | discussed | PASS | — |
| R-40/R-41/R-42/R-43 | Code, README sections, REPORT sections, logs + baseline/final configs | files present at root and in subfolders | README 10 sections, REPORT 8 sections | PASS | — |
| R-45 | Tests | `pytest` | **168 passed, 0 failed, 0 skipped** (main env, ~6 s; fresh clone same) | PASS | — |
| R-46 | Fresh clone -> reported numbers | fresh clone + new venv (Windows) | install 237 s; download 13 s; tests, baseline, both loops, test reproduction all identical | PASS (Windows only) | Linux/macOS NOT VERIFIED |
| R-47 | No results in README | read README | none (only file pointers) | PASS | — |
| R-48 | Report readable in ~15 min, n per figure | REPORT 3.4k words, tables | length estimate only | NOT VERIFIED | candidate reads it once |
| R-49 | >= 10 failures by cause | REPORT s7 | 18 cases with query IDs | PASS | — |
| R-50 | Brief not copied into the repo | phrase scan of HEAD (6 distinctive sentences: 0 hits); PDF and `00_assessment/` never committed | no copied text. **But** `01_planning/` paraphrases the brief's requirements (page-numbered traceability matrix) | PASS (copy) / RISK (paraphrase) | see KNOWN_ISSUES #3 |
| R-51 | Confidentiality conduct | — | cannot be verified | NOT VERIFIED | — |

## 2. Automated test run
`pytest` (main environment): **168 passed, 0 failed, 0 skipped** (~6 s). By area: dataset/splits 15 · offsets 13 · pipeline/config/chunking/ranking/abstention/serialization/isolation 33 · metrics 19 ·
evaluation/guard/diagnosis 19 · improvement loop/acceptance/proposer 15 · abstention stage 7 · application/web 30 · CLI 17. Regression tests: frozen unanswerable lock, baseline reproduction (fresh clone), guard order.
Fresh-clone run **before** data download (first attempt): 158 passed, 8 skipped (data-dependent), **1 failed** — real defect found, fixed, regression test added (below). After fix, with data: 168 passed.

## 3. Defects found by the audit and what was done
| # | Defect | Found by | Fix | Effect on results |
|---|---|---|---|---|
| 1 | `evaluate --split test` without flags gave exit 3 (missing data) instead of exit 2 when data was absent: the guard ran after data loading | fresh-clone test run | guard moved first; `test_test_split_guard_runs_before_any_data_is_touched` | none |
| 2 | Re-running the download rewrote `acquisition_record.json` (new timestamp) | fresh clone `git status` | idempotent write; true timestamp restored | none |
| 3 | Unit tests wrote 2 entries to the real test ledger | ledger inspection | autouse fixture redirects test writes; entries annotated, not deleted (`ledger_notes.md`) | none (not real test runs) |
| 4 | Test-run counting happened only at save time, so two aborted attempts were not counted | review of the first test attempt | count at evaluation start; disclosed | none |
| 5 | A commit message (`7662e7f`) claimed fixes it did not contain; the follow-up commit `2656e76` completed them | self-review | follow-up commit states this; history not rewritten | none |
| 6 | `experiment_log*.jsonl` `config_path` values were edited after commit (`resolved_config.yaml` -> `train_resolved_config.yaml`) when output files were renamed | self-review | path rename only; metrics/decisions unchanged, verified by the from-scratch rerun | none |

None of the fixes touched retrieval, chunking, metrics or the gate, so **the frozen configuration and the test results are unaffected, and the test evaluation does not need repeating**. Proof: in the fresh clone (at a later commit) the saved test metrics reproduced exactly.

## 4. Security and confidentiality
| Check | Result |
|---|---|
| PDF / `00_assessment/` in any commit | 0 |
| Secret patterns (HF/OpenAI/GitHub tokens, AWS keys, private keys, passwords) in any commit | 0; the system needs no keys |
| Copied brief text at HEAD (6 distinctive sentences) | 0 hits |
| Machine-specific paths in tracked files | none: all tracked files were searched for user-directory paths, `AppData` and the account name; the one hit (an email in `decision_log.md`) is removed in the audit commit |
| Personal email | removed from `decision_log.md`; **still present as commit author metadata** (unavoidable without rewriting history; see KNOWN_ISSUES #4) |
| Unsafe constructs | none: no pickle/eval/exec/`shell=True`; `yaml.safe_load` only; the only `subprocess` calls are `git rev-parse`/`git status` with argument lists |
| External transfers | only the pinned dataset download from Hugging Face; no contract text is sent anywhere at run time |
| Resource use / malformed input | query length capped (2,000 chars), `k` bounded to 1-64, empty/None/non-string rejected, config schema `extra="forbid"`; tested |
| Web exposure | documented command binds `localhost`; Streamlit's default would bind all interfaces |
| Contract material in the repo | the full corpus is **not** committed (git-ignored, re-downloaded). The repo does contain the gold answer excerpts (`02_data/gold_annotations.jsonl`, 272 snippets) and short excerpts in the failure-analysis files, all from the public CUAD SEC filings (CC BY 4.0); prediction files hold offsets and scores only, no passage text |
| Visibility inconsistency in the brief | **flagged** (private in logistics, public in deliverables); no repository was created or published by me |

## 5. Experiment-history audit
Baseline exists (iteration 0, train and test). 15 iterations in round 1 (3 accepted, 12 rejected) and 5 in round 2 (1 accepted, 4 rejected), each with hypothesis, proposer, diff, guardrail values, bootstrap and decision. Unanswerable set committed once and unchanged
(sha256 `5a860dc9…`). Final configuration selected from train metrics only (no test artifact existed until after `final-frozen`). Every number in the REPORT was matched against saved artifacts while writing; corrections made during that check are listed in `PROMPT_08_SUMMARY.md`.
**Unsupported or weak claims to keep out of the debrief:** (a) any claim that dense/hybrid/LLM approaches do or do not help — never tested; (b) "the gate works" — it abstains on 3/10 held-out unanswerables; (c) causal explanations in REPORT s7 are marked as diagnoses/hypotheses, not experiments;
(d) the 7/7 baseline abstention on missing contracts was accidental.

## 6. Verdict
See `09_submission/SUBMISSION_CHECKLIST.md` and `PROMPT_09_SUMMARY.md`: **READY WITH DISCLOSED LIMITATIONS**, conditional on the human-only items (visibility choice and repo creation, collaborator access, README s10 completion, email by the deadline, personal rehearsal).
