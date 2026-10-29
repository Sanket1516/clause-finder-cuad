# Demo scenarios

Illustrations of behaviour, **not benchmark results**. Outcomes below were observed on 2026-10-29 with the `final` configuration
(`final-df9f97a9`, abstention threshold 4.597). All questions come from the **train** split or the frozen unanswerable set (train
portion); none come from the held-out test split. Reproduce with the commands in `run_demo.md`. Measured metrics live in the report.

| # | Scenario | Question (abridged) | Expected behaviour | Observed |
|---|---|---|---|---|
| A | Answerable, clause present | Loop Industries marketing agreement: *What is the governing law for this contract?* | passages from that contract, ranked, with offsets | **answered**, confidence 9.71. Top passage chars 32237-32994 (an *assignment* sub-agreement's governing-law paragraph); rank 2 (24700-25489) is the main agreement's "Choice of Law" paragraph. Both are Delaware law, but a reader must check which instrument applies, which is why the UI says "candidates". |
| B | Answerable, clause present | Cano Petroleum sponsorship: *Is there an anti-assignment clause?* | the assignment clause | **answered**, confidence 9.48. Top passage chars 7063-7821 begins "18. Assignment. This Agreement may not be assigned by either party without the prior written consent...". |
| C | Unanswerable: clause absent | Glu Mobile amendment: *What is the governing law?* (the amendment has none) | abstain | **abstained** (`below_threshold`, confidence 2.70 < 4.597). Message says this does not prove the clause is absent. "Show weakest passages" lists what was found, labelled as insufficient. |
| D | Unanswerable: contract not indexed | Invented "Aurora Streaming / Northwind Studios" licence: *Does it allow sublicensing?* | abstain | **answered (false answer)**, confidence 19.94: title routing sent the question to an unrelated indexed contract. **Known weakness**, see below. |
| E | Unanswerable: outside a contract's scope | Cano sponsorship: *What is the current market price of the sponsor's shares?* | abstain | **answered (false answer)**, confidence 9.90 (a recital passage). Same weakness. |
| F | Unanswerable: clause absent, other wording | Glu amendment: *Does the contract allow sublicensing to a third-party platform?* | abstain | **answered (false answer)**, confidence 10.48 (the amendment's opening paragraph). The passage shares generic licence vocabulary ("License Agreement", "Licensee") with the question; no sublicensing text exists. The cause was not investigated further. |
| G | Malformed input | empty question / `-k 0` / `-k 65` | clear message, no traceback | CLI exit code 2; web shows a warning. |
| H | Missing data | `CONTRACT_INTEL_DATA_DIR` pointing nowhere | clear message | CLI exit code 3 with the setup commands; web shows "Could not start the search engine". |

## What the table shows about the system
- Scenarios A-C work as intended. D-F do not: on the 39 train unanswerable queries the final configuration abstains on only 8 (20.5%);
  it recovers **1 of 7** never-indexed contracts, whereas the baseline recovered 7 of 7 (by accident: the party names of invented
  contracts did not match anything). The fix is a gate that uses how well the *named contract* matched, not only the clause score.
  This is a recorded limitation, not a solved problem.
- Because the gate can fail, every interface labels results as candidate passages and never states that a clause is absent.
