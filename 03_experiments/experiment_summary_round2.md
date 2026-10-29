# Round 2 summary: abstention stage (train only, post hoc)

Objective and rule: `03_experiments/optimization_objective.md`, Amendment 1. Retrieval metrics are identical across all rows by construction (guardrail R1).

| # | gate signal | correct abstention | gain (queries) | P(gain) | AUROC | absent_clause (of 26) | not_in_corpus (of 7) | out_of_scope (of 6) | decision |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `round1-final` | 0.205 (8/39) |  | nan | 0.633 | 6 | 1 | 1 | **baseline** |
| 1 | `abstain-norm` | 0.410 (16/39) | 8 | 1.000 | 0.737 | 12 | 3 | 1 | **accepted** |
| 2 | `abstain-coverage` | 0.333 (13/39) | -3 | 0.119 | 0.721 | 11 | 1 | 1 | **rejected** |
| 3 | `abstain-title` | 0.205 (8/39) | -8 | 0.018 | 0.582 | 1 | 7 | 0 | **rejected** |
| 4 | `abstain-norm-title` | 0.410 (16/39) | 0 | 0.000 | 0.796 | 12 | 3 | 1 | **rejected** |
| 5 | `abstain-coverage-title` | 0.385 (15/39) | -1 | 0.287 | 0.776 | 11 | 3 | 1 | **rejected** |

Selected gate: Round-1 selection (routing + paragraph chunks + light stemming) plus round-2 gate: abstain-norm. Saved as `03_experiments/configs/final.yaml` / `final_resolved.yaml`; round-1 selection preserved as `final_round1*.yaml`.
