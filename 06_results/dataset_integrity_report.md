# Dataset integrity report

Generated from `06_results/dataset_validation.json`, `02_data/split_manifest.json` and `02_data/acquisition_record.json`.

## Acquisition
- Source: `awinml/legalbench-rag`, revision `2b9c248bc8179ef0908fd6ba01d50b156facd48b`, acquired 2026-10-29 15:24 UTC.
- Downloaded: `benchmarks/cuad.json` (4,042 queries) and 29 contracts. Every file's sha256 matches the mirror's `SHA256SUMS`.

## Selection
- `mini()` (verbatim from the brief) applied to the 4,042 queries gives **194** queries over **29** contracts.
- Re-running the selection gives the same order (test `test_selection_is_194_and_repeatable`). Ordered-query hash: `da52dce78461226fc76df33cd37fb0f267f4a148cbde763623c751b55dccccba`.
- Selected records equal the originals in `cuad.json` (test `test_selected_queries_keep_original_annotations`).
- The corpus folder holds exactly the 29 referenced contracts and nothing else.
- There are no duplicate query strings among the 194.

## Offset validation
| Check | Result |
|---|---|
| Gold snippets | 272 |
| `document[start:end] == answer` | **272 / 272** |
| Missing documents | 0 |
| Invalid offsets | 0 |
| Overlapping gold spans within a query | 0 |
| Queries whose snippets span more than one document | 0 |

Document-level facts (these explain why offsets are stable): none of the 29 files has a BOM, a CRLF or a lone CR,
none contains characters outside the BMP, and all 29 paths are already in NFC form. 13 files contain non-ASCII characters.
So the dataset card's NFD path note and the CRLF/BOM rules are **not triggered in this subset**. They are still handled and unit-tested.

## Splits (prescribed `assign_split`)
| | train | test | total |
|---|---|---|---|
| Answerable benchmark queries | 140 | 54 | 194 |
| Unanswerable queries (frozen) | 39 | 10 | 49 |

Test share: 27.8% of benchmark queries and 20.4% of unanswerables. The unanswerable share is below the "roughly a third"
the split function suggests. With only 49 hash draws this is within sampling noise, and we do not alter the rule. Test
estimates of abstention rest on **10** queries, so they will have wide intervals.

Unanswerable queries by category and split: absent_clause 26 / 7, not_in_corpus 7 / 1, out_of_scope 6 / 2 (train / test).
Multi-snippet answerable queries: 37 train, 15 test (of 140 and 54).

## Unanswerable-set validation
- 49 queries (minimum 30). Schema, categories and unique IDs are enforced by `load_unanswerable`.
- All 49 absence patterns have zero hits in their target document (or in the whole corpus for `not_in_corpus`). Re-run with `validate_unanswerable.py`.
- Verification strength is uneven and should be read as such: **two** target contracts (the Glu Mobile amendment, the Vinton gas franchise) were read in full, and for the remaining ones absence rests on **keyword patterns** plus my judgement of synonyms. A paraphrase that the patterns miss could make a query answerable after all. If that is found, it will be reported as a label defect and the file will not be edited.
- The queries reuse each contract's benchmark title prefix, so they look like benchmark queries. `not_in_corpus` queries use invented party names, checked to be absent from every indexed text.
- The set's sha256 is `5a860dc9a438c57c0a7976606c60c1d70021b0bf909a0ea4f40b8938dbbf2b46`.

## Known limitations
- Splits are per query, so the same contract appears in train and test queries (test measures new questions, not new contracts).
- One contract (Glu amendment) is 1,902 chars; the largest is 173,240 chars; total 1,211,773 chars.
- The paper itself was not read; metric definitions come from the authors' code.
