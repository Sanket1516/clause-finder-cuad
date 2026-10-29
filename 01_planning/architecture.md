# Architecture

Design goal: the **simplest robust system that can be measured objectively**. It is a single Python package run as one
process: local files in, local files out, no services, no paid APIs, no agent frameworks. Every pipeline choice lives
in a YAML config, so the improvement loop can change it.

## 1. Data flow

```
 HF mirror ──download──▶ 02_data/raw/{benchmarks/cuad.json, corpus/cuad/*.txt, SHA256SUMS}
                                │
                    prepare (select mini → validate offsets → assign splits → manifests)
                                │
        ┌───────────────────────┼─────────────────────────────┐
        ▼                       ▼                             ▼
  DocumentStore         BenchmarkQueries (194)        UnanswerableQueries (frozen, ≥30)
  (original text,       train/test + gold spans       train/test computed at load
   doc_id, sha256)      [scoring only]                [category for diagnosis only]
        │
   Chunker (config) ── Chunk{doc_id,start,end,text,index_text}
        │
   Index build: BM25 index │ (optional) dense embeddings ── cached on disk by (config_hash, corpus_hash)
        │
 query:str ─▶ QueryProcessor ─▶ [Router: title → candidate docs] ─▶ Retriever(s) ─▶ Fusion ─▶ [Reranker]
                                                                                        │
                                              Postprocess: NMS (no overlap), optional trim/expand, top-k
                                                                                        │
                                                         AbstentionGate(confidence, τ) ─▶ SearchResponse
                                                                                        │
                               ┌────────────────────────────────────────────────────────┤
                               ▼                                ▼                       ▼
                             CLI                         Streamlit web app        Evaluator (train | test-guarded)
                                                                                        │
                                                          metrics, diagnosis, predictions, ledger
                                                                                        │
                                                           Improvement loop (train only): propose → evaluate →
                                                           accept/reject → log → next
```

## 2. Package layout (`04_src/contract_intel/`)

Numbered top-level folders are not importable names, so `04_src` is a *source root* (`pyproject.toml`:
`package-dir = {"" = "04_src"}`; pytest `pythonpath = ["04_src"]`, `testpaths = ["05_tests"]`).

| Module | Responsibility | Key objects |
|---|---|---|
| `common/config.py` | Load YAML, resolve `extends:` inheritance, validate with pydantic, canonical hash | `PipelineConfig`, `load_config()`, `config_hash()` |
| `common/schemas.py` | Data contracts (see `data_contracts.md`) | `Document`, `Chunk`, `RetrievedPassage`, `SearchResponse`, … |
| `common/logging.py` | Structured logging (stdlib `logging`, JSON lines for runs) | `get_logger()` |
| `common/paths.py` | All filesystem locations in one place | `Paths` |
| `data/download.py` | Fetch only the needed files from HF (pinned revision), verify sha256 | `download()` |
| `data/benchmark.py` | Load `cuad.json`, `mini()` selection, query IDs | `select_mini()` |
| `data/splits.py` | `assign_split()` exactly as specified | `assign_split()` |
| `data/corpus.py` | **Original text management**: read with UTF-8 default text mode, NFC path matching, immutable text | `DocumentStore` |
| `data/validate.py` | Offset gate + dataset report | `validate_offsets()` |
| `data/unanswerable.py` | Load the frozen set, check the lock hash, compute splits | `load_unanswerable()` |
| `chunking/` | `fixed.py` (char window + overlap), `sentence.py` (boundary-snapped windows), `clause.py` (heading/numbering-aware sections, max-length split). All emit offset-exact `Chunk`s | `Chunker` protocol, `make_chunker(cfg)` |
| `retrieval/lexical.py` | BM25 over `index_text`; tokenizer config (lowercase, alnum, optional stopwords/stemming) | `BM25Retriever` |
| `retrieval/dense.py` | *(optional)* sentence-transformers bi-encoder, normalised embeddings, cosine; disk cache | `DenseRetriever` |
| `retrieval/hybrid.py` | Reciprocal-rank fusion (or weighted, normalised) of lexical + dense | `HybridRetriever` |
| `retrieval/router.py` | Document routing from the query's `Consider "<title>"` clause (fuzzy title match against doc titles); none / soft boost / hard filter | `TitleRouter` |
| `ranking/rerank.py` | *(optional)* cross-encoder rerank of the top-N | `CrossEncoderReranker` |
| `ranking/postprocess.py` | NMS (no same-doc overlap, INV-4), optional neighbour expansion/trim, cut to k | `postprocess()` |
| `abstention/gate.py` | Confidence signal (top-1 score, margin, routing-confidence combo) + threshold; `calibrate(τ)` on train | `AbstentionGate` |
| `pipeline.py` | Composes the above from config; `search(query: str, k) -> SearchResponse` (INV-3) | `Pipeline` |
| `evaluation/metrics.py` | Char-level P/R@k (authors' definition), abstention rates, AUROC, bootstrap | pure functions |
| `evaluation/evaluator.py` | Runs a pipeline over a split, writes predictions/metrics; test guard + ledger | `evaluate()` |
| `evaluation/diagnose.py` | Failure labels (protocol §6), failure summary, example extraction for the REPORT | `diagnose()` |
| `experiments/acceptance.py` | The a-priori acceptance rule | `decide()` |
| `experiments/proposer.py` | Picks the next candidate from a pre-registered catalogue, keyed by the dominant failure label; rule-based + small grids; optional LLM proposer plug-in | `propose()` |
| `experiments/loop.py` | Single-command loop: evaluate parent → diagnose → propose → evaluate → decide → log → repeat | `run_loop()` |
| `interfaces/cli.py` | Typer CLI: `download, prepare, index, search, evaluate, loop, report-test` | `app` |
| `interfaces/webapp.py` | Streamlit UI: question box, k slider, config picker, ranked passages with doc/offsets/score + highlighted context, clear "no relevant clause found" state with reason | — |

## 3. Configuration strategy

- Location: `03_experiments/configs/`. `baseline.yaml` is complete; other configs `extends: baseline.yaml` and override
  keys. The loop writes each candidate's *resolved* config to `03_experiments/configs/generated/<experiment_id>.yaml`.
  `final.yaml` is copied from the last accepted candidate.
- The schema is validated by pydantic with `extra="forbid"`, so a misspelt key fails loudly.
- `config_hash` = sha256 of the canonical JSON of the resolved config, excluding the `name`/`description` fields.
  It identifies index caches and experiment IDs.
- Precedence: CLI flags (only `--config`, `--k`, `--split`) > config file > code defaults. Code defaults exist only for
  presentation, never for pipeline behaviour.

```yaml
# sketch of baseline.yaml (values are the baseline's, not tuned)
name: baseline
chunking:   {strategy: fixed, size_chars: 500, overlap_chars: 0}
retrieval:  {method: bm25, candidates: 64,
             bm25: {k1: 1.5, b: 0.75, tokenizer: {lowercase: true, pattern: "\\w+", stopwords: none, stem: false}},
             dense: null, hybrid: null}
routing:    {mode: none}                 # none | boost | filter
ranking:    {reranker: none, rerank_top_n: 50, nms: true, expand_chars: 0}
abstention: {signal: top1_score, target_far: 0.05, threshold: null}   # null → calibrate on train
evaluation: {ks: [1, 2, 4, 8, 16, 32, 64], primary_k: 4, bootstrap: {B: 2000, seed: 0}}
```

## 4. Key design decisions (summary; details in `decision_log.md`)

1. **Offsets are first-class.** Chunks are offset ranges over immutable original text, and enrichment touches `index_text`
   only. This makes INV-1 testable on every chunk.
2. **Lexical baseline (BM25)** as the simplest reasonable pipeline, matching what LegalBench-RAG-style queries reward.
   CUAD queries share contract vocabulary ("non-compete", "governing law").
3. **Title routing** is a first-class, configurable stage. Every query names its contract, and the paper reports that
   wrong-document retrieval dominates. Out-of-corpus titles are also a strong abstention signal.
4. **Abstention as a calibrated gate** with its own metrics, separate from ranking quality.
5. **Pre-registered candidate catalogue** for the loop: proposals are rules keyed on failure labels, plus small grids.
   An LLM proposer is an optional plug-in, off by default.

## 5. Alternatives considered

| Area | Chosen | Alternatives | Why chosen |
|---|---|---|---|
| Orchestration | Plain Python package | LangChain / LlamaIndex | Fewer hidden behaviours; offsets are easy to lose inside framework splitters; must explain every line in the debrief |
| Lexical | `rank_bm25` (BM25Okapi) with our tokenizer | own BM25; Elasticsearch/OpenSearch; bm25s | Tiny, readable, no server; corpus is small (dozens of contracts). Own implementation is the fallback if we need field control |
| Dense | `sentence-transformers` + small open model (e.g. `BAAI/bge-small-en-v1.5`), numpy cosine | FAISS, Chroma, hosted embeddings | ≤ ~10k chunks fit in memory; brute-force cosine is exact and fast; no contract data leaves the machine |
| Reranker | Local cross-encoder (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`; `BAAI/bge-reranker-base` if latency allows) | Cohere/hosted rerankers, LLM rerank | Privacy, no keys, reproducible; CPU-feasible on top-N |
| Chunking | Fixed → sentence-snapped → clause-aware (all offset-exact) | Semantic chunking via embeddings; LLM-contextualised chunks | Explainable, deterministic, cheap; contextual prefixes possible via `index_text` later |
| Abstention | Threshold on calibrated confidence + routing signal | Classifier on features; LLM judge | Few labelled unanswerables (~28 train) → a 1-parameter gate overfits least |
| UI | Streamlit | Gradio, FastAPI + HTML | Fastest single-file UI; brief explicitly allows it |
| CLI | Typer (already installed) | argparse, click | Concise, typed, auto-help |
| Storage | JSON/JSONL + `.npy` caches | SQLite, vector DB | Diffable, reviewable artifacts; small scale |

## 6. Resource constraints

- CPU only (16 logical cores, no CUDA). Dense models must be small; the cross-encoder runs on ≤50 candidates per query.
- Expected scale (to confirm in Prompt 02): tens of contracts, median ~37k chars each → a few thousand 500-char chunks.
  BM25 indexing takes seconds; small-model embedding of all chunks takes a few minutes on CPU (cached).
- **Time:** about 11 h to the deadline at the time of writing. This drives the scope cuts in `implementation_plan.md`.

## 7. Failure risks

See `risk_register.md`. The top three are the deadline, abstention signal quality with few calibration examples, and
unanswerables that are accidentally answerable.
