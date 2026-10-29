# Five-minute demo script

Setup before the call (about 2 minutes, not part of the five): repo cloned, virtualenv active, `python 02_data/download_data.py && python 02_data/prepare_dataset.py` done, one terminal open at the repo root and `streamlit run 04_src/web_app.py --server.address localhost` already running in a browser tab.
All demo questions come from the **train** split or the train part of the frozen unanswerable set. Say out loud which statements are *examples* and which are *measurements*.

| Time | Step | What to do / say | Source of truth |
|---|---|---|---|
| 0:00-0:45 | **1. Problem and architecture** | "Find the clause that answers a contract question, with exact offsets, or say nothing was found. 29 CUAD contracts, 194 benchmark questions, plus 49 questions I wrote that the contracts cannot answer. No LLM; local BM25." Show the diagram in `README.md` s3 in one sentence: *route to the named contract -> BM25 over paragraph chunks -> remove overlaps -> confidence gate*. | `README.md`, `04_src/contract_intel/pipeline.py` |
| 0:45-1:45 | **2. A question with evidence** | Web app: click **Anti-assignment (answerable)** -> Search. Point out: passage text, `characters 7063-7821` (half-open range), score, "Show surrounding text". Then in the terminal: `python 04_src/cli.py search "<same question>" -k 1 --json` and show `start`/`end`/`doc_id`; say `document[start:end] == text` is asserted. | Expected: top passage starts "18. Assignment. This Agreement may not be assigned…" (observed in `demo_scenarios.md` B) |
| 1:45-2:30 | **3. Abstention** | Click **Clause absent from the contract (abstains)** -> "No sufficient evidence found". Read the message: "this does not prove that the contract has no such clause". Open the weak-passage expander: "not sufficient evidence". Terminal: same question, show exit code 10 (`echo $?`). | `demo_scenarios.md` C (confidence 0.159 < 0.2401) |
| 2:30-3:30 | **4. Measured results (not examples)** | Open `06_results/final_comparison.md`. Say: held-out test, 54 answerable queries: baseline recall@4 0.043 -> final 0.448; recall@64 0.356 -> 0.925. Abstention on 10 test unanswerables: 1/10 -> 3/10 correct; 4/54 answerable wrongly withheld. Train recall@4 0.448 as well. Be explicit: test was run once per configuration, and 10 unanswerables cannot support firm claims. | `06_results/final_comparison.md`, `REPORT.md` s5 |
| 3:30-4:30 | **5. Improvement log: one accepted, one rejected** | Open `03_experiments/experiment_summary.md`. **Accepted:** iteration 2 "route to the named contract": R@4 0.021 -> 0.309, P(gain) 1.00, all guardrails passed. **Rejected:** iteration 6 "1000-char chunks": R@4 rose to 0.400 but precision@4 fell 0.064 -> 0.049 (below 0.9x), so the guardrail vetoed it; rejected rather than "best recall". Mention iteration 14 was a no-op and round 2 was post hoc. | `experiment_log.jsonl` lines 3 and 7 |
| 4:30-5:00 | **6. One known failure and the fix** | Show scenario G: invented "Meridian Sports / Ironbridge League" governing-law question is **answered** with confidence 0.697 (an unrelated contract's governing-law paragraph). Say: the gate scores clause similarity but not whether the *named* contract exists. Fix I would try (untested): a calibrated score of how well the named contract matched, plus more negative examples; the simple title-match variants I tried did not help alone (REPORT s6). | `demo_scenarios.md` G; `REPORT.md` s8 |

## Commands (verified to run)
```bash
python 04_src/cli.py search "Consider the Sponsorship Agreement between R. C. Boyd Enterprises, LLC and Cano Petroleum, Inc. for 'Honey Hole'; Is there an anti-assignment clause in this contract?" -k 3
python 04_src/cli.py search "Consider the Amendment No. 3 to Wireless Content License Agreement between Fox Mobile Entertainment, Inc. and Glu Mobile Inc.; What is the governing law for this contract?" --show-weak ; echo "exit=$?"
python 04_src/cli.py search "Consider the Sports Rights Agreement between Meridian Sports Network and Ironbridge League Ltd.; What is the governing law for this contract?"
```
## If something fails live
- Web app does not load: use the CLI only (all of steps 2-3 work there).
- Data missing: `python 02_data/download_data.py && python 02_data/prepare_dataset.py` (about 15 s).
- Do not run the test-split evaluation live (it appends to the ledger).
