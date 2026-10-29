# Decision log

Append-only. Format: ID · date · decision · alternatives · rationale · status.

| ID | Date | Decision | Alternatives | Rationale | Status |
|---|---|---|---|---|---|
| D-001 | 2026-10-29 | Use the existing git repo in the assignment folder as the submission repo; git-ignore `*.pdf` and `00_assessment/` | Separate clean repo dir; moving the PDF | Inputs must not be moved; ignoring keeps the brief out of the repo | Provisional (D-OPEN-1) |
| D-002 | 2026-10-29 | Numbered workspace folders; `04_src` is a source root containing package `contract_intel` | Conventional `src/` layout | Requested structure; numbered names aren't importable, so the package sits one level down | Accepted |
| D-003 | 2026-10-29 | Metric = the authors' code semantics (wrong-doc chars in the precision denominator; empty → 0); returned passages made non-overlapping | Set-based metric with right-doc-only denominator | Fidelity to the cited definition; NMS removes the double-count ambiguity | Accepted |
| D-004 | 2026-10-29 | Report two retrieval views (ranking pre-gate, end-to-end post-gate) | Single end-to-end number | Separates retrieval failures from abstention failures | Accepted |
| D-005 | 2026-10-29 | Primary metric = train ranking-view Recall@4; guardrails G1–G5; paired-bootstrap acceptance (Δ ≥ 0.01, P ≥ 0.90) | Recall@64 (paper's headline, unrealistic reading budget); Precision@k primary (rewards tiny chunks); F1@k (hides the trade-off); end-to-end metric (mixes components) | See `evaluation_protocol.md` §5; declared before any result | Accepted |
| D-006 | 2026-10-29 | Abstention τ auto-calibrated on train to FAR ≤ 0.05 for every candidate | Fixed τ; maximise balanced accuracy on train unanswerables | 136 answerables give a stabler estimate than ~28 unanswerables; keeps G2 meaningful across score scales | Accepted |
| D-007 | 2026-10-29 | Baseline = fixed 500-char chunks, no overlap, BM25, no routing/rerank, top-1-score gate | Dense baseline as in the paper | Simplest reasonable, deterministic, explainable; 500 chars matches the paper's chunk size | Accepted |
| D-008 | 2026-10-29 | No LLM by default; any LLM must be local; no hosted model without explicit user authorisation | Hosted Gemini/Claude for rewrite/rerank | Privacy of real contracts; reproducibility; time | Accepted |
| D-009 | 2026-10-29 | Loop proposer = rule-based selection from a pre-registered catalogue keyed on failure labels, plus small grids | LLM proposer; Bayesian optimisation | Explainable; avoids p-hacking via unbounded search; fits the time budget | Accepted |
| D-010 | 2026-10-29 | Minimal CLI + web app built right after the baseline, before the loop | The prompt's original order | The brief's FAQ priority (demo + report first) | Accepted |
| D-011 | 2026-10-29 | One planned test run evaluating baseline + final together; every test evaluation in a ledger | Test run per milestone | The brief asks for test only at final reporting and for the count | Accepted |
| D-012 | 2026-10-29 | Streamlit for the web app, Typer for the CLI, rank_bm25, sentence-transformers (optional) | Gradio, argparse, Elasticsearch, FAISS | See architecture §5 | Accepted (deps installed in Phase 1) |
| D-013 | 2026-10-29 | Unanswerables in the benchmark surface form, three categories, target ≥40 | Free-form questions; 30 exactly | Avoids style leakage; test count ≈12 instead of ≈9 | Accepted |

## Open decisions (need the user)

| ID | Question | Default if no answer |
|---|---|---|
| D-OPEN-1 | Submission repo: this folder's repo (PDF ignored) or a separate clean directory? | This folder, with ignores |
| D-OPEN-2 | Commit planning docs (`01_planning/`) to the repo? They paraphrase requirements but contain no copied text | Commit, after a phrase-level audit |
| D-OPEN-3 | Authorise git commits (required for the unanswerable freeze evidence), and which author email to use (the repo's configured identity) | Ask at Phase 2 |
| D-OPEN-4 | Private (logistics section) vs public (deliverables section) repo | Private + collaborator access |
| D-OPEN-5 | Optional local LLM stretch (Ollama) — attempt at all given the time? | No; mention as future work |

## Failed experiments / deviations
(none yet)

## Additions during implementation (2026-10-29)

| ID | Decision | Rationale / evidence | Status |
|---|---|---|---|
| D-014 | BM25 implemented in-repo (no `rank_bm25`) | transparent, tiny, no dependency | Accepted |
| D-015 | Protocol Amendment 1 (taxonomy, calibration on answerable only, actual counts) committed before any metric | see `evaluation_protocol.md` | Accepted |
| D-016 | Loop run: 15 pre-registered candidates, 3 accepted (route-filter, paragraph-chunks, stem-light); `final` = that sequence | `03_experiments/experiment_summary.md` | Accepted (train evidence only) |
| D-017 | The pre-declared rule cannot accept gate-only changes; `abstain-norm` (CAR 0.205 → 0.410 on train) was rejected by the rule and NOT adopted | integrity of the pre-registered rule; recorded as a limitation | **Open: needs user decision** (a labelled post-hoc abstention stage is possible) |
| D-018 | The final configuration regressed correct abstention on never-indexed contracts (7/7 → 1/7) | `PROMPT_05_SUMMARY.md` finding 1; guardrail G2 was aggregate and missed it | Open |
| D-019 | Demo/UI examples drawn from train / frozen-unanswerable-train only; wording never asserts a clause is absent | legal-safety + leakage hygiene | Accepted |
| D-020 | Streamlit started with `--server.address localhost` in the run guide | default binds all interfaces | Accepted |
