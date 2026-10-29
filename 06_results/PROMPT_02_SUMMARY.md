# Prompt 02 summary: reproducible data preparation and integrity

## Done (all verified by running it)
- `02_data/download_data.py` fetched `benchmarks/cuad.json` and the 29 contracts referenced by the 194 mini queries from
  `awinml/legalbench-rag`, pinned to revision `2b9c248b…`. Every sha256 matched the mirror's `SHA256SUMS`. Record: `02_data/acquisition_record.json`.
- `mini()` (verbatim) gives **194** queries over **29** contracts, in a repeatable order. Selected records equal the originals.
- Offsets: **272 / 272** gold snippets satisfy `document[start:end] == answer` (`06_results/dataset_validation.json`). No missing documents, bad
  offsets or overlapping gold spans. None of the 29 files has a BOM, CRLF, or a non-NFC path, so those dataset-card hazards are not
  triggered here (they are still handled and unit-tested).
- Prescribed `assign_split`: benchmark **train 140 / test 54**.
- **49 unanswerable queries** (33 absent_clause / 8 not_in_corpus / 8 out_of_scope), split with the same function: **train 39 / test 10**.
  By category (train/test): absent_clause 26/7, not_in_corpus 7/1, out_of_scope 6/2.
- Frozen with a sha256 lock (`02_data/unanswerable_queries.sha256`) and committed in `b1f3e64`, before any retrieval code or metric existed.
- Manifests: `query_manifest.jsonl` (inference-safe fields only), `gold_annotations.jsonl` (evaluation only), `document_manifest.jsonl`,
  `split_manifest.json`. `06_results/dataset_integrity_report.md` has the details.

## Tests
`05_tests/test_dataset.py`, `05_tests/test_offsets.py`: selection determinism (against a reference transcription), split determinism, missing
documents, invalid/overlapping offsets, CRLF/BOM/NFD handling, duplicate IDs, manifest consistency, frozen-set lock. Ran with the rest of the suite: all pass.

## Caveats (honest)
- Unanswerable labels are verified by **keyword patterns** (zero hits in the target contract, or in the whole corpus for invented contracts).
  Only two contracts were read in full. A paraphrase the patterns miss could make a query answerable after all; if found, it will be reported, not edited.
- Test has only **10** unanswerables, so test abstention numbers will have wide uncertainty. The test share (20%) is below the "roughly a third" the
  rule suggests; the rule was not altered.
- The unanswerable queries reuse the benchmark's `Consider the <title>;` form, deliberately, so style cannot give them away.
- The paper PDF was not read; metric details come from the authors' code and the dataset card.
