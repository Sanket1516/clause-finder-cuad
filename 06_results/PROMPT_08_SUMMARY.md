# Prompt 08 summary: README and REPORT

Created `07_reports/README.md` and `07_reports/REPORT.md`; identical copies at the repository root (`README.md` with relative links adjusted, `REPORT.md`).

**README (10 required sections, no results):** every command in sections 4-8 was executed in a fresh clone with a new virtualenv (see `09_submission/FINAL_AUDIT.md`), with measured timings.
Marked *not verified*: Python 3.10, Linux/macOS. Section 10 discloses that Claude Code (Claude Opus 5.5 / Sonnet 5.5) wrote the code and documents from the candidate's prompts and contains a
**placeholder the candidate must complete** (what they personally reviewed and decided).

**REPORT (8 required sections):** every figure traces to `06_results/final_comparison.json`, the iteration logs or the prediction files; counts and denominators are explicit; uncertainty values are bootstrap /
Wilson intervals computed from the saved predictions (stated as such). Error analysis has 18 cases (10+ required) from the **train** split, each with a `query_id`. Claims I checked while writing and corrected:
offset violations (0 in 49 metric files), per-contract concentration (24% / 31% for the three largest contracts), the false-abstention breakdown (4 of 7 were retrieval hits), the maximum train/test cutoff difference (0.046).

**Not claimed:** no statement about dense/hybrid retrieval, rerankers or LLMs beyond "not tested"; no significance tests beyond the bootstrap intervals; no cost or speed-up numbers beyond measured latencies.
