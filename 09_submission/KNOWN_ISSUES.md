# Known issues and disclosed limitations

Ordered by how much they matter for the submission. None of them changes a reported number.

## Needs a human decision or action
1. **Repository visibility.** The brief's logistics section says *private with collaborator access*; its deliverables section says *public*. I flagged this and did not resolve it. The user asked for a **public** repo on the `Sanket1516` account. I could not create it
   (no `gh` CLI/token on this machine; I declined to pull a stored credential from the credential manager). If the reviewers expect private + collaborator access, a public repo may not satisfy the logistics instruction; the safe option is private + collaborator invite, which can be switched to public later.
2. **README section 10 contains a placeholder** the candidate must complete (what they personally reviewed and decided). The brief requires the candidate to explain and modify every part of the code in the debrief; the code was written by an AI assistant, so rehearsal with `08_demo/interview_preparation.md` is essential.
3. **Confidentiality of the brief's contents.** The PDF and `00_assessment/` were never committed and no sentence was copied (phrase scan). `01_planning/traceability_matrix.md`, the only file with page-numbered requirement references, was deleted before publication, but it still exists in the commits that added it. The remaining planning documents describe the design, not the brief.
4. **Author identity in history.** Commits are authored as `Sanket1516 <personal Gmail address>`. A public repo exposes that address. Rewriting history is not done here; if undesired, use GitHub's no-reply address for future commits and accept that old commits keep it (or recreate the repository from a squashed tree).

## Results the reader should not over-trust
5. **Abstention is weak:** test correct abstention 3/10, train 16/39 (REPORT s5); the gate can be more confident about an invented contract than a real one (`unans-038`). With 10 test unanswerables, no firm conclusion.
6. **Round 2 was post hoc** (declared after one candidate result was seen on train); accepted gains likely over-state the true gain (20 candidates, 140 queries).
7. **Test evaluations:** 4 started (2 recorded; 2 earlier aborted at the save step, results never seen). The ledger also holds 2 unit-test artifacts, annotated. Details: `PROMPT_07_SUMMARY.md`, `06_results/test_runs/ledger_notes.md`.
8. **Unanswerable labels** rest on keyword absence checks (two contracts read in full). A paraphrased answer could exist; if found it should be reported, not edited.
9. **Train and test share contracts:** results measure new questions about known contracts, not new contracts.

## Engineering
10. Verified only on **Windows 11 / Python 3.11.9**. Python 3.10 (declared minimum) and Linux/macOS are not verified.
11. The web app was exercised headlessly and via a health check, **never viewed in a browser** — check the layout before the demo.
12. `experiment_log*.jsonl` `config_path` strings were edited after the first commit (file-name change); decisions/metrics unchanged (verified by a from-scratch rerun). `final_freeze.json` records commit `20b0ac3a`, the commit *before* the freeze commit `2fdd7f0` (it was written from an uncommitted working tree).
13. Prediction files are duplicated across `03_experiments/iterations`, `final_eval` and `06_results/final` (~2 MB each); harmless (repo ~7 MB).
14. Several planning documents under `01_planning/` describe a plan that differs from what was built (dense/hybrid/reranker, `rank_bm25`, clause-type resolution); they carry a status note.
15. Not implemented: dense/hybrid retrieval, reranking, LLM use, cross-reference and definition resolution, multi-document answers, authentication/audit logging.
16. `iteration 14` (overlap) was a no-op in context; `iterations 12-13` only touch the gate. They remain in the log.
17. Commit `e05da87` has a message describing fixes that arrived in `fd57f27`; history was not rewritten.
