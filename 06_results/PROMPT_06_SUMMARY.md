# Prompt 06 summary: CLI and web demonstration

## Built (filenames adapted to the package layout)
| Requested | Actual |
|---|---|
| `04_src/cli.py` | `04_src/cli.py` (entry) → `04_src/contract_intel/interfaces/cli.py` (also `python -m contract_intel`) |
| `04_src/web_app.py` | `04_src/web_app.py` (entry) → `04_src/contract_intel/interfaces/webapp.py` |
| `04_src/application/` | `04_src/contract_intel/application/service.py` — the only thing both interfaces call; no retrieval logic in either UI |
| tests | `05_tests/test_cli.py`, `05_tests/test_application.py` |
| demo docs | `08_demo/demo_scenarios.md`, `08_demo/run_demo.md` |

**CLI:** `search` (question, `--config`, `-k`, `--json`, `--save`, `--show-weak`), `evaluate`, `configs`. Exit codes: 0 passages · 10 abstained · 2 invalid input ·
3 missing data / unknown or uncalibrated config · 4 unexpected error. Errors are one-line messages, never tracebacks.

**Web app (Streamlit):** question box, example buttons, search button, configuration selector, number of passages; results show document, `[start, end)` character range,
score, the passage text and optional surrounding text; an explicit "No sufficient evidence found" state; a "How to read the results" panel; a standing disclaimer.

**Legal-safety behaviour:** passages are labelled *candidates, not legal conclusions*. Abstention text states it is not proof the clause is absent. Weak passages found under
the threshold are available only behind a separate, labelled expander / `--show-weak`. No document name, date or offset is generated; each displayed offset is re-checked
against the original text before display. Nothing is sent to any external service (no LLM is used).

**Engineering:** both interfaces use the shared config system and `SearchService`; locations come from the repo layout or `CONTRACT_INTEL_DATA_DIR` / `CONTRACT_INTEL_CONFIG_DIR`
(no machine-specific paths); dependencies are in `pyproject.toml` (`web` extra) and `08_demo/run_demo.md`.

## Verification (actual outcomes)
- `pytest`: **161 passed at the time (168 after later regression tests)** (~8 s), 0 failed, 0 skipped on this machine. Covers: CLI output, JSON and offset reproduction, exit codes, empty/malformed/overlong input, bad `k`,
  unknown and uncalibrated config, missing data and missing documents, answerable and abstaining questions, web view-model for all four states, a headless run of the whole
  Streamlit script (answer, abstain, empty input, missing data), and test-split protection from the CLI.
- The real Streamlit server was started and answered HTTP 200 on `/_stcore/health`; then stopped. I did **not** inspect it visually in a browser, so layout is unreviewed.
- Demo scenarios were executed for real and their observed outcomes recorded (`demo_scenarios.md`).

## Open issue the demo exposes (not fixed here)
Of the unanswerable scenarios, only the "clause absent from the contract" case abstains (re-checked against the frozen final; see demo_scenarios.md). "Contract not indexed" and "outside the contract's scope" return passages
(false answers). This is the abstention weakness measured in Prompts 05 and 07. At the time of this prompt the round-1 selection abstained on 8/39 train unanswerables (1/7 never-indexed); after the round-2 gate the frozen final abstains on 16/39 (3/7 never-indexed). The interfaces word results
conservatively to limit the harm, but the underlying gate needs work before anyone relies on "no result".
