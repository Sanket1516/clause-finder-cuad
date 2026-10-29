# 02_data: dataset acquisition and preparation

Source: LegalBench-RAG mirror `awinml/legalbench-rag`, pinned to revision `2b9c248bc8179ef0908fd6ba01d50b156facd48b`.
Only `benchmarks/cuad.json` and the CUAD contracts referenced by the 194 CUAD-mini queries are downloaded (29 files, 6.5 MB).

## Reproduce

```bash
python 02_data/download_data.py        # downloads + verifies sha256 against the mirror's SHA256SUMS (~1 min)
python 02_data/validate_offsets.py     # document[start:end] == answer for every gold snippet -> 06_results/dataset_validation.json
python 02_data/prepare_dataset.py      # manifests below
python 02_data/validate_unanswerable.py
pytest 05_tests/test_dataset.py 05_tests/test_offsets.py
```

## Files

| File | Committed | Content |
|---|---|---|
| `download_data.py`, `prepare_dataset.py`, `validate_offsets.py`, `validate_unanswerable.py` | yes | scripts |
| `acquisition_record.json` | yes | source URL, pinned revision, acquisition time, per-file sha256 |
| `raw/` | no (git-ignored) | downloaded benchmark + contracts |
| `query_manifest.jsonl` | yes | **inference-safe**: `query_id`, `query`, `split` (benchmark and unanswerable queries) |
| `gold_annotations.jsonl` | yes | **evaluation only**: answerability, gold spans, source document, indices into the full `cuad.json` |
| `document_manifest.jsonl` | yes | indexed contracts: id, sha256, length, number of benchmark queries |
| `split_manifest.json` | yes | counts per split and answerability, selection hash |
| `unanswerable_queries.jsonl` | yes, **frozen** | the unanswerable query set |
| `unanswerable_queries.sha256` | yes | lock hash; a test fails if the set changes |

## Conventions

- `doc_id` = NFC-normalised corpus-relative path, e.g. `cuad/<file>.txt`.
- Offsets are Python `str` indices of `Path.read_text(encoding="utf-8")`, half-open `[start, end)`. Text is never normalised.
- The benchmark files carry no query IDs. `query_id = cuad-mini-NNN` is the position in the `mini()` output;
  `source_index` in `gold_annotations.jsonl` is the position in the full `cuad.json`.
- The split is never stored by hand. It is recomputed from the query text with the prescribed `assign_split`.

## Unanswerable set (frozen)

Categories: `absent_clause` (the target contract has no such text), `not_in_corpus` (the contract and parties are not indexed),
`out_of_scope` (information a contract does not hold). Each row records the rationale, the verification method and the
regex patterns that must have zero hits in the target document (or in the whole corpus for `not_in_corpus`).
The set was committed before any retrieval experiment. If a defect is found later it is reported, not edited.
