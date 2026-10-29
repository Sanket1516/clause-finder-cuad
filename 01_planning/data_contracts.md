# Data contracts

All records are pydantic v2 models in `04_src/contract_intel/common/schemas.py`. They are serialised as JSON/JSONL with
UTF-8 encoding and `ensure_ascii=False`. Offsets are always **Python `str` indices** (code points) into the document text,
read with `Path.read_text(encoding="utf-8")`, and are half-open `[start, end)`.

## Global invariants (enforced in code and tests)

| ID | Invariant | Enforced by |
|---|---|---|
| INV-1 | For every `Chunk` and `RetrievedPassage`: `text == documents[doc_id].text[start:end]` | `Chunk` validator at build time; `test_offsets.py` property test over all chunks |
| INV-2 | Text added for indexing (headings, defined terms, context) goes into `index_text` only and is never returned as passage text | `RetrievedPassage` built from `Chunk.start/end`, not from `index_text` |
| INV-3 | Inference functions accept a query *string* plus config, never a `BenchmarkQuery` or gold spans | type signature of `Pipeline.search(query: str)`; test inspects the signature |
| INV-4 | Within one response, passages from the same document do not overlap | NMS step in `ranking/postprocess.py`; test |
| INV-5 | `doc_id` is stable across runs: the NFC-normalised corpus-relative path, e.g. `cuad/<file>.txt` | `data/corpus.py`; manifest |
| INV-6 | Every prediction/metric record carries `experiment_id` and `config_hash` | schemas (required fields) |

## Records

### `Document`
| Field | Type | Notes |
|---|---|---|
| `doc_id` | str | INV-5 |
| `path` | str | local path, relative to the data root |
| `text` | str | full original text, unmodified (BOM and `\n` normalisation as Python text mode yields) |
| `n_chars` | int | `len(text)` |
| `sha256` | str | of the raw file bytes; checked against `SHA256SUMS` |
| `title` | str \| None | derived from the filename, for routing/display only |

### `BenchmarkQuery`
| Field | Type | Notes |
|---|---|---|
| `query_id` | str | `cuad-mini-{index:03d}` — the index is the position in the `mini()` output (benchmark files have no IDs) |
| `query` | str | verbatim |
| `split` | `"train"`\|`"test"` | from `assign_split(query)` |
| `answerable` | bool | always `True` |
| `gold` | list[`GoldSpan`] | scoring only (INV-3) |
| `doc_id` | str | gold document (scoring/diagnosis only) |

### `GoldSpan`
`doc_id: str`, `start: int`, `end: int`, `answer: str` (validated `== doc.text[start:end]`).

### `UnanswerableQuery` (file: `02_data/unanswerable/unanswerable_queries.jsonl`, frozen)
| Field | Type | Notes |
|---|---|---|
| `query_id` | str | `unans-{nn:03d}` |
| `query` | str | `Consider "<title>"; …` form (A-07) |
| `category` | `"absent_clause"`\|`"not_in_corpus"`\|`"out_of_scope"` | A-09 |
| `target_doc_id` | str \| None | the contract the question is about, if indexed. **Diagnosis only; never an inference input** |
| `rationale` | str | why it is unanswerable / what was checked |
| `answerable` | bool | always `False` |
| `split` | — | *not stored* — computed at load time with `assign_split`, so the frozen file can't hold a hand-edited split |

The lock file `02_data/unanswerable/unanswerable_queries.sha256` records the file hash. A regression test fails if the
file changes.

### `Chunk`
| Field | Type | Notes |
|---|---|---|
| `chunk_id` | str | `{doc_id}::{start}-{end}` (deterministic) |
| `doc_id` | str | |
| `start`, `end` | int | offsets into the original text |
| `text` | str | `doc.text[start:end]` (INV-1) |
| `index_text` | str | what is tokenised/embedded. Defaults to `text`; may be enriched (INV-2) |
| `section_path` | list[str] | detected headings, if any (clause-aware chunking) |
| `chunker` | str | name + params hash |

### `RetrievedPassage`
| Field | Type | Notes |
|---|---|---|
| `rank` | int | 1-based, after final ranking |
| `doc_id` | str | |
| `start`, `end` | int | original offsets |
| `text` | str | INV-1 |
| `score` | float | final-stage score (higher = better) |
| `stage_scores` | dict[str, float] | e.g. `{"bm25": 12.3, "dense": 0.61, "rrf": 0.03, "rerank": 4.2}` |
| `chunk_id` | str | provenance |

### `SearchResponse`
| Field | Type | Notes |
|---|---|---|
| `query` | str | |
| `abstained` | bool | |
| `abstention_reason` | str \| None | e.g. `"top score 0.12 < threshold 0.31"`, `"no indexed contract matches the title"` |
| `confidence` | float | the signal the abstention gate thresholds |
| `passages` | list[`RetrievedPassage`] | empty iff `abstained` (end-to-end view) |
| `ranked_candidates` | list[`RetrievedPassage`] | pre-gate list, kept for the ranking-view evaluation and the web app's "show anyway" toggle |
| `experiment_id`, `config_hash` | str | INV-6 |
| `latency_ms` | dict[str, float] | per stage |

### `QueryPrediction` (per-query evaluation row; `06_results/predictions/<experiment_id>/<split>.jsonl`)
`query_id, split, answerable, abstained, confidence, passages[ (doc_id,start,end,score,rank) ] (top max_k), gold_doc_id,
per_k: {k: {precision, recall, n_ret_chars, n_overlap_chars}} (ranking view), e2e_per_k (end-to-end view),
failure_label (see evaluation_protocol §Diagnosis), latency_ms, experiment_id, config_hash`.

### `ExperimentRecord` (one line per iteration in `03_experiments/logs/iterations.jsonl`, append-only)
| Field | Notes |
|---|---|
| `iteration` | 0 = baseline |
| `experiment_id` | `{iteration:02d}-{short_name}-{config_hash[:8]}` |
| `parent_experiment_id` | the accepted config it was compared to |
| `config_path`, `config_hash` | sha256 of the canonicalised resolved config |
| `change` | human-readable diff of config keys |
| `rationale` | why it was tried; which failure category it targets |
| `proposer` | `"human"`, `"rule:<rule_name>"`, `"search:<grid_name>"`, or `"llm:<model>"` |
| `split` | must be `"train"` (guard) |
| `metrics` | primary, guardrails, full P/R@k, abstention rates, latency |
| `delta_vs_parent`, `bootstrap` | paired deltas + resample statistics |
| `decision` | `"accepted"` / `"rejected"` + the rule clause that decided it |
| `failure_summary` | counts per diagnosis label |
| `git_commit`, `timestamp`, `runtime_s`, `env` | reproducibility |

### `TestRunLedgerEntry` (`06_results/test_runs/ledger.jsonl`, append-only)
`run_no, timestamp, experiment_id, config_hash, git_commit, reason, metrics_path`.
