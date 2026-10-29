# Contract Clause Search

A small retrieval system that, given a natural-language question about a contract, returns the passages most likely to answer it
— each with its source document and exact character offsets — or says that no passage was found strong enough. It is built and
measured on the CUAD portion of the LegalBench-RAG benchmark. Measured results and analysis are in [REPORT.md](REPORT.md), not here.

## 1. Overview
Lawyers and business teams routinely ask questions such as "Is there an anti-assignment clause?" or "What is the governing law?" and
answer them by reading contracts. This project finds the clause instead. It is a **retrieval aid, not a legal advisor**: it returns
candidate passages and never concludes that a clause does not exist. No language model is used; all processing is local.

## 2. Features
- **Ranked evidence with provenance:** every passage carries `doc_id`, `start`/`end` character offsets into the original contract text,
  a score and a rank. `document[start:end] == passage text` is checked when chunks are built and again before anything is displayed.
- **Abstention:** when no passage clears a configured evidence threshold the system returns nothing and says so, distinguishing "no candidate
  shares a term with the question" from "candidates exist but are too weak".
- **CLI** (`search`, `evaluate`, `configs`) with JSON output and meaningful exit codes; **Streamlit web app** over the same engine.
- **Evaluation:** character-level precision/recall at k = 1, 2, 4, 8, 16, 32, 64; abstention metrics in both directions; per-query evidence;
  failure taxonomy; a guard that keeps the held-out test split away from development.
- **Self-improvement loop:** one command evaluates the current configuration on train, diagnoses failures, proposes a configuration change from a
  pre-registered catalogue, accepts or rejects it by a declared rule and logs every iteration.
- **Configuration-driven:** chunking, tokenisation, BM25 parameters, routing, candidate counts, abstention signal and threshold are all in YAML.

## 3. Architecture
```
question text ──► [title routing: choose the named contract] ──► BM25 over chunks ──► overlap removal ──► ranked candidates
                                                                                          │
                                  confidence signal (top BM25 score / question idf mass) ─┴─► abstention gate ──► SearchResponse
                                                                                                                   │
                                                                                          CLI  ·  Streamlit app  ·  evaluator
```
| Package `04_src/contract_intel/` | Responsibility |
|---|---|
| `data/` | download-independent loading, the prescribed `mini()` selection and `assign_split`, immutable contract text, offset validation, frozen unanswerable set |
| `chunking/` | fixed, paragraph-aware and clause-aware chunkers; all return spans over the **original** text |
| `retrieval/` | BM25 written out in full (`lexical.py`); contract router (`router.py`) |
| `ranking/` | overlap removal, ranks |
| `abstention/` | confidence signals, the three-outcome gate, threshold calibration |
| `pipeline.py` | composes the above; `search(query: str, k)` is the only inference entry point and receives nothing but the question |
| `application/` | the service both interfaces call (config resolution, input validation, error handling) |
| `interfaces/` | `cli.py` (Typer) and `webapp.py` (Streamlit) |
| `evaluation/` | metrics, evaluator, failure taxonomy, split guard + test-run ledger |
| `experiments/` | acceptance rule, proposer, improvement loop, abstention stage |

Configuration lives in `03_experiments/configs/` (`baseline.yaml`, `final.yaml`, `final_resolved.yaml`; `extends:` inheritance, strict validation).
Data lives in `02_data/`; planning documents in `01_planning/`; results in `06_results/`.

## 4. Requirements and setup
- Python 3.10+ (developed and verified on **3.11.9, Windows 11**; Linux/macOS and Python 3.10 are *not verified*).
- Network access once, to download the dataset (6.5 MB) and Python packages. No GPU, no API keys, no external services at run time.
- Disk: ~10 MB data, ~7 MB repository.
```bash
git clone <repo-url> contract-search && cd contract-search
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash: source .venv/Scripts/activate);  Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,web]"       # pydantic, pyyaml, numpy, typer, huggingface_hub, pytest, streamlit
```
Optional environment variables: `CONTRACT_INTEL_DATA_DIR`, `CONTRACT_INTEL_CONFIG_DIR` (default: the repository layout).

## 5. Dataset preparation
The data is the public LegalBench-RAG mirror `awinml/legalbench-rag` at a pinned revision. Only `benchmarks/cuad.json` and the 29 contracts
referenced by the 194 benchmark queries are downloaded.
```bash
python 02_data/download_data.py       # fetch + verify sha256 against the mirror's SHA256SUMS
python 02_data/prepare_dataset.py     # select the 194 queries, assign splits, write manifests
python 02_data/validate_offsets.py    # document[start:end] == answer for every gold snippet (writes 06_results/dataset_validation.json)
python 02_data/validate_unanswerable.py
```
Details, file formats and the frozen unanswerable set: [02_data/README.md](../02_data/README.md). The assessment document is not part of this repository.

## 6. Running the application
```bash
python 04_src/cli.py configs
python 04_src/cli.py search "Consider the Sponsorship Agreement between R. C. Boyd Enterprises, LLC and Cano Petroleum, Inc. for 'Honey Hole'; Is there an anti-assignment clause in this contract?" -k 3
python 04_src/cli.py search "<question>" --config final --json --save result.json
python 04_src/cli.py search "<question>" --show-weak       # when abstaining, also list the (insufficient) best passages
streamlit run 04_src/web_app.py --server.address localhost  # then open http://localhost:8501
```
CLI exit codes: `0` passages returned · `10` abstained (not an error) · `2` invalid input · `3` missing data / unknown or uncalibrated configuration · `4` unexpected error.
Questions work best when they name the contract in the benchmark's form: `Consider the <contract description>; <question>`. Demo scenarios: [08_demo/](../08_demo/).

## 7. Evaluation and experimentation
```bash
python -m contract_intel evaluate --config baseline --split train                       # needs: pip install -e .  (or PYTHONPATH=04_src)
python 03_experiments/run_improvement_loop.py              # round 1: train-only loop (restartable; add --restart to re-run from scratch)
python 03_experiments/run_abstention_stage.py              # round 2: abstention-gate stage (train only; run after round 1; --restart to redo)
pytest                                                     # 168 tests
python -m contract_intel evaluate --config final --split test --final --confirm-test   # held-out test: final reporting ONLY
```
The test split is refused unless both `--final` and `--confirm-test` are given, and every test evaluation is appended to
`06_results/test_runs/ledger.jsonl`. Do not use it for tuning. `--restart` archives the previous log under `03_experiments/previous_runs/` (git-ignored).

## 8. Reproducing results
Measured on the verification machine (Windows 11, 16 logical CPUs, no GPU); download/install times depend on the network.
| Step | Command | Time |
|---|---|---|
| Create venv + install | `python -m venv .venv`; `pip install -e ".[dev,web]"` | 30 s + 237 s |
| Download + verify data | `python 02_data/download_data.py` | 13 s |
| Manifests + validation | `prepare_dataset.py`, `validate_offsets.py`, `validate_unanswerable.py` | ~2 s |
| Tests | `pytest` | 6-13 s |
| Baseline train metrics | `python -m contract_intel evaluate --config baseline --split train` | ~1 s |
| Round 1 loop (15 iterations) | `python 03_experiments/run_improvement_loop.py --restart` | 13 s |
| Round 2 stage (5 candidates) | `python 03_experiments/run_abstention_stage.py --restart` | 6 s |
| Test metrics (baseline, final) | `evaluate ... --split test --final --confirm-test --out-dir <dir>` | ~2 s each |

In a clean clone these reproduced the saved results exactly: baseline train metrics; the experiment logs (same decisions, config hashes and metrics, ignoring timing
fields); `final.yaml`/`final_resolved.yaml` byte-for-byte; and the saved test metrics. Compare with `03_experiments/final_eval/*/`, `03_experiments/experiment_log*.jsonl` and
`06_results/final_comparison.md`. The reported numbers are in [REPORT.md](REPORT.md). (Re-running test evaluations in a clone appends to that clone's own ledger.)

## 9. Assumptions and limitations
Assumptions made where the brief was unclear (full list: `01_planning/assumptions.md`):
- **Metric:** precision = overlapping characters / all returned characters (wrong-document text counts against precision); recall = overlapping / gold characters; macro-average over queries; nothing returned scores 0.
  Returned passages are made non-overlapping so overlap cannot inflate scores (my addition; identical to the published formula when passages do not overlap).
- Retrieval metrics are reported in two views: **ranking** (before the abstention gate) and **end-to-end** (an abstained answerable query scores 0).
- The contract named at the start of each question ("Consider the ...;") is legitimate input; the gold document is never used at inference time.
- "Unanswerable" is established by documented keyword checks on the target contract (two contracts were read in full), not by absence from the benchmark.
- Split is per query, so train and test queries can concern the same contract.
- The repository visibility is the submitter's choice; the brief is inconsistent (private in one place, public in another).
- Test evaluation numbers are single runs; small samples (54 answerable, 10 unanswerable test queries).

Limitations: see REPORT section 8 (abstention is weak, lexical retrieval misses paraphrased clauses, title routing assumes the user names the contract, single document format, no authentication or audit logging).

## 10. AI-tool usage
I used an AI coding assistant (Claude Code) to help write and test the code and to draft the documentation, working from my own prompts and design choices. I reviewed the results, ran the experiments and can explain and modify every part. No language model is used by the system itself.
