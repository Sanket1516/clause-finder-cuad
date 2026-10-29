# Demo scenarios

Illustrations of behaviour, **not benchmark results**. Outcomes were observed on 2026-10-29 with the frozen `final` configuration
(`final-0a25f701`, abstention signal `top1_norm`, threshold 0.2401). Every question comes from the **train** split or the train portion
of the frozen unanswerable set; none comes from the held-out test split. Measured metrics are in `REPORT.md`.
Reproduce with `python 04_src/cli.py search "<question>"` or the web app's example buttons.

| # | Scenario | Question (abridged) | Expected | Observed |
|---|---|---|---|---|
| A | Answerable | Loop Industries marketing agreement: *What is the governing law for this contract?* | governing-law passage with offsets | **answered**, confidence 0.571. Rank 1 = chars 32237-32994, a governing-law paragraph of an *assignment* attached to the agreement; the main agreement's "Choice of Law" paragraph (24700-25489) is rank 2. A reader must check which instrument applies. |
| B | Answerable | Cano Petroleum sponsorship: *Is there an anti-assignment clause?* | the assignment clause | **answered**, confidence 0.391. Rank 1 = chars 7063-7821, starts "18. Assignment. This Agreement may not be assigned by either party without the prior written consent...". |
| C | Unanswerable: clause absent | Glu Mobile amendment: *What is the governing law?* (the amendment has none) | abstain | **abstained** (`below_threshold`, 0.159 < 0.2401). The message says this does not prove the clause is absent; the weak candidates sit behind "Show weak passages". |
| D | Unanswerable: contract not indexed | Invented "Aurora Streaming / Northwind Studios" licence: *Does it allow sublicensing?* | abstain | **answered (false answer)**, confidence 0.585. Routing sent the question to an unrelated indexed contract. Known weakness. |
| E | Unanswerable: out of scope | Cano sponsorship: *What is the current market price of the sponsor's shares?* | abstain | **answered (false answer)**, confidence 0.384 (a recital). |
| F | Unanswerable: clause absent, other wording | Glu amendment: *Does the contract allow sublicensing to a third-party platform?* | abstain | **answered (false answer)**, confidence 0.273, just above the threshold; the passage is the amendment's opening paragraph. |
| G | Invented contract + generic clause | Meridian Sports / Ironbridge League: *What is the governing law?* (frozen `unans-038`) | abstain | **answered (false answer)**, confidence 0.697 — higher than scenario A. A real governing-law paragraph from an unrelated contract (Vitaminshoppe, chars 58392-58720) matches the generic question strongly. |
| H | Malformed input | empty question, `-k 0`, `-k 65` | clear message, no traceback | CLI exit code 2; the web app shows a warning. |
| I | Missing data | `CONTRACT_INTEL_DATA_DIR` pointing nowhere | clear message | CLI exit code 3 with the setup commands; the web app shows "Could not start the search engine". |

## What this shows
- A and B work as intended; C works. D-G do not: on the 39 train unanswerables the final configuration abstains on 16 and answers 23
  (REPORT section 5), and scenario G shows the gate can be *more* confident about an invented contract than about a real one.
- Because the gate is unreliable, every interface labels results as candidate passages and never states that a clause is absent.
