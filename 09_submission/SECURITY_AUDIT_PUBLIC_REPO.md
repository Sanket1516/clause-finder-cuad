# Security audit of the public repository (2026-10-29)

Scope: anonymous clone of `github.com/Sanket1516/JIO-STAR` (18 commits, 360 files) plus the code and dependencies.

| Check | Result |
|---|---|
| Secrets in all history (HF/OpenAI/GitHub/AWS/Slack tokens, private keys, `password=`-style strings) | none |
| Assessment PDF, `00_assessment/`, `.env`, key files in any commit | none |
| GitHub Actions / workflows | none present |
| Dependencies (`pip-audit`, 80 packages incl. transitive, in a fresh venv) | **none vulnerable in the project's dependencies**; only `pip 24.0` and `setuptools 65.5.0` (venv bootstrap tools) have advisories: upgrade with `python -m pip install -U pip setuptools` |
| Static scan (`bandit`, 2,271 lines) | 0 high, 0 medium, 12 low: `subprocess` calls to `git` with argument lists (no shell), `random` in the mandated `mini()` (not security), and 3 `assert`s |
| `assert` used as a real check | **fixed**: the cuad.json checksum check and two data-preparation checks now raise explicitly (asserts are stripped under `python -O`) |
| Injection / unsafe deserialisation | none: `yaml.safe_load` only, no pickle/eval/exec/`shell=True`; the web UI never renders user text as HTML |
| Input abuse | query <= 2,000 chars, `k` in 1-64, strict config schema; the web app only offers configs from a fixed directory listing |
| Network | only the pinned Hugging Face download (revision + sha256 verified); no contract text leaves the machine at run time |
| Data in the repo | public CUAD (CC BY 4.0) excerpts only; no private contracts |

## Not vulnerabilities, but exposure to know about
1. Repository name `JIO-STAR` and `09_submission/*.md` name the company and the submission address. Consider renaming the repo.
2. All 18 commits expose the author email `sanketmali0909@gmail.com`.
3. `01_planning/` paraphrases the assignment's requirements with page numbers; the brief is confidential. Consider deleting that folder (history keeps it unless rewritten).
4. A public solution to a hiring assignment can be copied by other candidates; the brief says work must be independently completed.
5. Dependencies are lower-bounded, not locked; add a lock file if exact reproducibility of installs matters.
6. The Streamlit app has no authentication: run it on `localhost` only (as documented) and never deploy it with confidential contracts.
7. Optional GitHub settings: enable secret scanning push protection and Dependabot alerts.
