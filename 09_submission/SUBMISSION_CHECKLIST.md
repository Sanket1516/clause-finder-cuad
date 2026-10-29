# Submission checklist

Tick only what you have verified yourself. "Done by assistant" means evidenced in `FINAL_AUDIT.md`. **Nothing here has been sent, published or shared by the assistant.**
Brief deadline: **08:00 IST, Friday 30 October** (per the brief's logistics section). Recipient per the brief: the address in its logistics section (`datascience.ai@` at the company's domain) — re-read the brief to confirm spelling before sending.

## A. Repository
- [ ] Decide visibility. Brief is inconsistent: logistics = **private + collaborator access**; deliverables = "public". Safer reading: private + collaborators. (You requested public; not yet created.)
- [ ] Create the repo on GitHub (`Sanket1516/contract-intelligence-assistant` or another name that does not reveal the company), **empty**, no README/licence.
- [ ] `git remote add origin <url>` then `git push -u origin main --tags` (assistant will do this once the repo exists and you confirm).
- [ ] If private: add the reviewers as collaborators (GitHub -> Settings -> Collaborators) and confirm they can see it.
- [ ] Open the repo in a private/incognito window to check what a stranger sees.

## B. Content (done by assistant, re-verify quickly)
- [x] `README.md` (10 sections) and `REPORT.md` (8 sections) at the root — `FINAL_AUDIT` R-41/R-42
- [x] Source: `04_src/`; configs: `03_experiments/configs/` (`baseline.yaml`, `final.yaml`, `final_resolved.yaml`, `final_freeze.json`)
- [x] Dataset preparation instructions and scripts: `02_data/`
- [x] Experiment logs: `03_experiments/experiment_log.jsonl`, `experiment_log_round2.jsonl`, summaries
- [x] Frozen unanswerable queries: `02_data/unanswerable_queries.jsonl` (+ sha256 lock; committed once, `b1f3e64`)
- [x] Tests: `05_tests/` (168 pass)
- [x] Final evaluation artifacts: `06_results/final/`, `06_results/final_comparison.*`, `03_experiments/final_eval/`
- [ ] **README section 10: replace the placeholder with your own account of what you reviewed/decided.**
- [ ] Read REPORT.md once (target ~15 minutes); fix anything you cannot defend.

## C. Confidentiality and safety
- [x] Assessment PDF and `00_assessment/` never committed (history scan: 0)
- [x] No secrets in history (pattern scan: 0); none needed
- [x] No copied brief sentences at HEAD (6-phrase scan: 0)
- [ ] **Decide about `01_planning/`**: it paraphrases the brief's requirements (page-numbered). Consider removing it, or at least `traceability_matrix.md`, before going public (KNOWN_ISSUES #3).
- [ ] Decide about the author email shown in commits (KNOWN_ISSUES #4).
- [ ] `git ls-files | grep -iE "pdf|00_assessment|\.env"` returns nothing (run it yourself).

## D. Verification you can repeat
- [x] Fresh clone + new venv: install, download, tests (168), baseline, both loops, test-metric reproduction, CLI exit codes, web health — all passed (Windows).
- [ ] Run the web app once and look at it: `streamlit run 04_src/web_app.py --server.address localhost`
- [ ] Run `08_demo/demo_script.md` end to end (~5 min) and time it.
- [ ] Rehearse `08_demo/interview_preparation.md`; practise one live change (suggestions are in the last section of that file).

## E. Submission
- [ ] Email the repository link to the recipient in the brief, before the deadline, from the account you used for the application.
- [ ] Save a screenshot/confirmation of the sent email and of the collaborator list.
- [ ] Do not discuss the assignment with other candidates (brief s12).
