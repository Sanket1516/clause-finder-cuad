# Technical debrief preparation

How to use this: for each question, **open the cited file and read the code before reading the answer** — you must be able to explain it, not recite it. The answers describe only what the code does today. Where something was *not* built or tested, the answer says so; do not claim otherwise.
Numbers are from `06_results/final_comparison.md` and `REPORT.md`.

## A. Design
**1. Walk me through the pipeline.** `Pipeline.search(query, k)` (`04_src/contract_intel/pipeline.py`): `split_title` pulls the "Consider the <title>;" clause; `DocRouter` scores each contract's first 3,000 characters against the title and keeps the top contract (`routing.mode: filter`); the question without its title clause is scored with BM25 against that contract's chunks; overlapping passages are dropped; confidence = top BM25 score / sum of idf of the question's distinct words; if confidence < threshold the response abstains. Config: `03_experiments/configs/final.yaml`.

**2. Why BM25 and not dense or hybrid retrieval?** Simplest thing that gives a measurable baseline, runs on CPU in milliseconds, and every score is explainable (`retrieval/lexical.py`, ~40 lines). **I did not build or test dense, hybrid or reranking**, so I cannot claim they would or would not help. The failure analysis (REPORT s7) suggests where they might: questions whose words do not appear in the clause (cases 1-7). That is a hypothesis.

**3. Why no LLM?** Retrieval problem; a lexical baseline already gives a signal; contracts are confidential (a hosted model needs authorisation and a privacy review); a local model adds latency and a caching burden for reproducibility. Not tested, so no claim about benefit. (REPORT s3.)

**4. Why no LangChain/LlamaIndex?** Offsets are the core requirement; framework splitters can lose them. Small hand-written modules are explainable and easier to change live.

**5. Why routing by title? Is that legitimate?** Every benchmark question begins "Consider the <contract description>;", so the user's question names the contract. Using that text is inference-time input; the gold document is never used (`Pipeline.search` takes only a string; `test_pipeline.py::test_search_takes_only_the_question_text`). Limit: it assumes the user names the contract; a wrong title silently restricts the search to the wrong contract. It was the single biggest gain: recall@4 0.021 -> 0.309 on train (iteration 2).

## B. Chunking and offsets
**6. How do you guarantee exact character offsets?** Text is read once with `Path.read_text(encoding="utf-8")` (default text mode, as the benchmark offsets assume; `data/corpus.py`), never modified. A `Chunk` is `(doc_id, start, end)` with `text = document[start:end]`; `chunk_document` asserts equality when each chunk is built (`chunking/__init__.py`), the evaluator rechecks every returned passage, and the application layer checks again before display. Any enrichment would go into `index_text`, which is never returned. 0 violations in 49 saved metric files; 272/272 gold snippets validated (`data/validate.py`).

**7. How does paragraph-aware chunking work?** Split at blank lines (`\n[ \t]*\n`), greedily pack consecutive paragraphs up to 800 characters, split any longer paragraph at a sentence end (or whitespace) in the last 40% of the window, trim whitespace, drop chunks < 20 characters. Offsets stay on the original text. It beat fixed 500-char chunks (R@4 0.309 -> 0.412) while 1000-char chunks raised recall but were vetoed on precision.

**8. What did the BOM / CRLF / NFD notes in the dataset card mean for you?** None of the 29 files has a BOM, CRLF or a non-NFC path (`06_results/dataset_validation.json`), so those hazards were not triggered. Code handles them (NFC matching in `DocumentStore`, text mode newline translation) and unit tests cover them (`test_offsets.py`).

## C. Metrics
**9. Define character-level precision and recall as you implemented them.** For one query: overlap = characters of returned passages inside gold spans *of the same document*. precision@k = overlap / all returned characters (wrong-document text counts against precision), recall@k = overlap / gold characters (several gold spans pooled). Macro-average over queries. Nothing returned -> precision 0. `evaluation/metrics.py`; checked against hand cases and a port of the authors' formula in `test_metrics.py`.

**10. What is your own assumption there?** I union overlapping returned characters per document before counting, so overlap cannot inflate scores; identical to the authors' formula when passages do not overlap (the pipeline guarantees that). Also "ranking view" vs "end-to-end view" reporting (abstained answerable queries score 0 in the latter).

**11. Why is precision so low (0.08 at k = 4)?** Gold spans are short (about 300 characters at the median) and returned paragraphs are up to 800, so even a perfect hit has precision < 0.5; most top-4 passages are not the answer. Both are measured, not an error. It is why precision@4 is a guardrail: bigger chunks win recall by returning more text.

## D. Abstention
**12. How does abstention work and how is the threshold chosen?** Three outcomes in `abstention/gate.py`: `no_candidates`, `below_threshold` (confidence < threshold), `answered`. Threshold = the (floor(0.05 x n)+1)-th smallest confidence among the **answerable train** queries, so about 5% of answerable train queries are refused (7/140). Unanswerable labels never fit it; they only score it. Frozen as 0.2401 in `final_resolved.yaml`.

**13. Does it work?** Not well. Train: correct abstention 16/39, test 3/10 (Wilson 95% [0.11, 0.60]); false abstention 7/140 train, 4/54 test. AUROC 0.74 train / 0.68 test. `unans-038` is answered with confidence 0.697 (higher than a real query). 4 of the 7 train false abstentions were retrieval hits just under the threshold.

**14. Why did the baseline abstain correctly on all 7 missing contracts then?** Accident: its scored text included the invented party names, which matched nothing, so top scores were low. Routing removed that accident; the loop's guardrail missed it because it measured abstention in aggregate. Be ready to say this plainly.

**15. How do you decide a question is "unanswerable"?** Not by retrieval failure. Three categories (clause absent from an indexed contract / contract not in the corpus / outside a contract's scope), each with a rationale and regex patterns that must have zero hits in the target contract (whole corpus for invented ones; `02_data/validate_unanswerable.py`). Weakness: two contracts were read in full; the rest rely on keywords.

## E. Data, splits, leakage
**16. How is the benchmark selected and split?** `mini()` and `assign_split()` are used exactly as specified (`data/benchmark.py`, `data/splits.py`): 194 queries over 29 contracts; split = SHA-256 of the stripped query, mod 10 < 3 = test; 140 train / 54 test (unanswerables 39 / 10). The split is recomputed from the text, never stored by hand. Tests compare against reference transcriptions.

**17. How do you prevent tuning on test?** `evaluation/guard.py`: purpose `development` can only see `train`; test needs `purpose="final"` and `--confirm-test`; every test evaluation is appended to `06_results/test_runs/ledger.jsonl`; the loop only accepts train queries; the CLI checks the guard before loading data. Honest count: 4 test evaluations started, 2 recorded; 2 earlier aborted at the save step with results never seen; the ledger also has 2 unit-test artifacts (REPORT s5, `ledger_notes.md`).

**18. Could the same contract in train and test inflate test results?** Yes: the split is per query (mandated), so test queries use contracts that also appear in train queries (test queries cover 21 contracts; train queries cover all 29). Test measures new questions about known contracts. It is in the limitations.

## F. The improvement loop
**19. Explain the loop and the acceptance rule.** `experiments/loop.py`: evaluate the parent on train, count failure types (`evaluation/diagnose.py`), take the first untried catalogue entry targeting the most common type (`experiments/proposer.py`, `03_experiments/proposals/catalogue.yaml`), evaluate on the same queries, then `experiments/acceptance.py`: accept iff recall@4 gain >= 0.010 **and** a paired bootstrap over the 140 queries (B = 2000, seed 0) gives P(gain) >= 0.90 **and** guardrails hold (precision@4 >= 0.9x, correct abstention not down by more than 1/39, R@1 not down by > 0.02, p95 <= 2 s, build <= 900 s). Append-only log; restartable; re-running from scratch in a clean clone reproduced every decision.

**20. Name an accepted and a rejected experiment and why.** Accepted: iteration 2, route to the named contract (R@4 0.021 -> 0.309, P(gain) 1.00). Rejected: iteration 6, 1000-char chunks (R@4 0.400 but precision@4 0.064 -> 0.049 < 0.9x). Also: iteration 1 (drop the title) rejected because correct abstention collapsed; iteration 14 was a no-op.

**21. What are the weaknesses of your loop?** Catalogue was hand-written (after seeing the baseline's failure pattern but before any candidate ran); 20 comparisons on 140 queries (optimistic selection — stemming P(gain) = 0.92 is borderline); the round-1 rule could not accept gate-only changes, so round 2 was designed after seeing one result (post hoc, disclosed); the rule's thresholds (0.010, 0.90) are judgement, not derived.

## G. Engineering
**22. How is it configured and validated?** Pydantic models with `extra="forbid"`, YAML `extends:` inheritance, a canonical hash that ignores name/description (`common/config.py`). Invalid values (overlap >= size, unknown keys, an out-of-range `b`, `primary_k` not in `ks`) raise `ConfigError`; tests in `test_pipeline.py`.

**23. What is your testing strategy?** 168 tests: data/split/offset tests against reference implementations; chunk offset reconstruction for every chunker; ranking stability and tie order; empty candidate sets; abstention boundaries; metric hand-calculations; evaluator + guard + ledger; loop restartability; CLI exit codes; web view-model and a headless Streamlit run; a source scan proving inference modules never mention gold structures. A fresh clone found a real bug (guard ran after data loading), now a regression test.

**24. What are the runtime and memory trade-offs?** All CPU. 1,941 chunks; index build 0.07-0.29 s; p95 query latency 6-8 ms; everything in memory (1.2 M characters of text). Scoring touches only the posting lists of the query's terms, which is fine for a few thousand chunks; at thousands of contracts I would move to a proper search index (untested).

**25. How would you reproduce your numbers from nothing?** README s8: clone, venv, `pip install -e ".[dev,web]"`, download (13 s), prepare, `pytest`, `evaluate`, loops with `--restart`. I did this in a clean clone; baseline metrics, both logs (ignoring timings), the final configs and the saved test metrics matched exactly.

## H. Limitations and what you would do next
**26. What fails and why?** REPORT s7: vocabulary mismatch (expiration date vs "term … one year"; exclusivity vs "exclusive"; revenue sharing vs "royalty"), defined terms, labels loosely tied to questions, wrong-sense matches, multi-span answers only partly covered. Recall@4 = 0.45, recall@64 = 0.91.

**27. Before legal users rely on it?** A far better abstention mechanism; evaluation on their own contracts; human review of every answer; handling of PDFs, tables, amendments, definitions and cross-references (none implemented); access control, audit logs and a privacy review.

**28. What is unproven?** Whether dense/hybrid/LLM approaches help; any statistical claim beyond the bootstrap/Wilson intervals; behaviour on contracts outside these 29; Linux/macOS/Python 3.10.

## Possible live changes (rehearse one)
| Request | Where | Check |
|---|---|---|
| Change chunk size / overlap | `chunking.size_chars` in a copy of `final.yaml`, then `evaluate --config <copy> --split train` | R@4 and P@4 move |
| Add stopwords / change `k1`, `b` | `retrieval.bm25.*` | same |
| Add a `--min-confidence` CLI option | `interfaces/cli.py` -> pass to `SearchService`/`decide` | `05_tests/test_cli.py` |
| Add a gate signal | `abstention/gate.py::confidence`, allow it in `common/config.py` Literal | `test_abstention_stage.py` |
| Query expansion for "expiration date" | `pipeline.py::retrieve` (before `index.top`) | `test_pipeline.py`, then train eval |
| Reciprocal-rank fusion of two retrievers | new `retrieval/hybrid.py` using `BM25Index` twice (e.g. two tokenizers) | unit test + train eval |
| Show confidence in the web app | `interfaces/webapp.py` | `test_application.py` |
Always run `pytest` after a change and evaluate on **train** only. Never run `--split test` in the debrief.
