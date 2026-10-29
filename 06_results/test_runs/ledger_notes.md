# Test-run ledger notes

`ledger.jsonl` is append-only and counts evaluations of the held-out test split.

- **Entries 1 and 2 (experiment `test-75f1b203`, written by two runs of the unit-test suite) are NOT real test evaluations.** It was written by a unit test
  (`test_calibration_on_test_is_refused`) running on the synthetic fixture corpus, after the ledger was moved to the start of
  `evaluate()` and before the tests were pointed at a temporary ledger. No benchmark test query was scored, and no held-out
  data was read. The entry is kept, not deleted, for transparency. A conftest fixture now redirects test-suite ledger writes to a temp file.
- Real held-out evaluations are listed from entry 3 onward.
