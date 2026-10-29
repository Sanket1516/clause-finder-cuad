# Experiment summary (train only)

15 iterations beyond the baseline. Primary metric: character recall@4 on 140 train answerable queries (ranking view). Acceptance rule: `03_experiments/optimization_objective.md`. Held-out test: **not evaluated**.

| # | experiment | proposer | R@4 | dR@4 | P(gain) | P@4 | R@1 | correct-abst. | decision |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `baseline` | human | 0.0213 | +0.0000 | nan | 0.0066 | 0.0000 | 0.179 | **baseline** |
| 1 | `strip-title` | rule:catalogue/strip-title | 0.0485 | +0.0272 | 0.939 | 0.0104 | 0.0113 | 0.026 | **rejected** |
| 2 | `route-filter` | rule:catalogue/route-filter | 0.3086 | +0.2873 | 1.000 | 0.0642 | 0.1286 | 0.231 | **accepted** |
| 3 | `route-boost` | rule:catalogue/route-boost | 0.2884 | -0.0202 | 0.000 | 0.0611 | 0.1143 | 0.103 | **rejected** |
| 4 | `stopwords` | rule:catalogue/stopwords | 0.2829 | -0.0257 | 0.118 | 0.0679 | 0.1540 | 0.256 | **rejected** |
| 5 | `chunk-300` | rule:catalogue/chunk-300 | 0.2497 | -0.0589 | 0.000 | 0.0832 | 0.1179 | 0.231 | **rejected** |
| 6 | `chunk-1000` | rule:catalogue/chunk-1000 | 0.3995 | +0.0909 | 1.000 | 0.0489 | 0.1709 | 0.231 | **rejected** |
| 7 | `paragraph-chunks` | rule:catalogue/paragraph-chunks | 0.4122 | +0.1036 | 1.000 | 0.0675 | 0.2044 | 0.231 | **accepted** |
| 8 | `clause-chunks` | rule:catalogue/clause-chunks | 0.3764 | -0.0358 | 0.023 | 0.0605 | 0.1830 | 0.205 | **rejected** |
| 9 | `stem-light` | rule:catalogue/stem-light | 0.4483 | +0.0361 | 0.924 | 0.0752 | 0.2137 | 0.205 | **accepted** |
| 10 | `bm25-k1-low` | rule:catalogue/bm25-k1-low | 0.4412 | -0.0071 | 0.180 | 0.0739 | 0.2411 | 0.205 | **rejected** |
| 11 | `bm25-b-high` | rule:catalogue/bm25-b-high | 0.4391 | -0.0092 | 0.094 | 0.0759 | 0.2066 | 0.205 | **rejected** |
| 12 | `abstain-norm` | rule:catalogue/abstain-norm | 0.4483 | +0.0000 | 0.000 | 0.0752 | 0.2137 | 0.410 | **rejected** |
| 13 | `abstain-margin` | rule:catalogue/abstain-margin | 0.4483 | +0.0000 | 0.000 | 0.0752 | 0.2137 | 0.026 | **rejected** |
| 14 | `overlap-100` | rule:catalogue/overlap-100 | 0.4483 | +0.0000 | 0.000 | 0.0752 | 0.2137 | 0.205 | **rejected** |
| 15 | `expand-100` | rule:catalogue/expand-100 | 0.4424 | -0.0059 | 0.314 | 0.0581 | 0.2252 | 0.205 | **rejected** |

## What each iteration tried

### 1. strip-title - rejected
- hypothesis: Scoring only the clause question (title clause removed) stops party-name tokens from pulling the cover-page chunk to the top, so clause chunks rank higher. Risk: without the title, other contracts compete, so wrong_document may rise.
- why now: most frequent train failure is 'ranked_too_low' (71 of 139 failing queries); entry targets it
- change: `query.strip_title_prefix`: False -> True
- result: R@4 0.0213 (baseline) | this run 0.0485 | delta vs parent +0.0272; runtime 0.422s
- decision: guardrail failed: G2_correct_abstention

### 2. route-filter - accepted
- hypothesis: Use the title only to choose the contract (BM25 over each contract's opening 3000 chars), then rank clause chunks inside that contract only. Separates 'which contract' from 'which clause', which the baseline conflates.
- why now: most frequent train failure is 'ranked_too_low' (71 of 139 failing queries); entry targets it
- change: `query.strip_title_prefix`: False -> True, `routing.mode`: none -> filter
- result: R@4 0.0213 (baseline) | this run 0.3086 | delta vs parent +0.2873; runtime 0.597s
- decision: R@4 +0.2873 >= 0.01 and P(gain)=1.000 >= 0.9; all guardrails pass

### 3. route-boost - rejected
- hypothesis: Soft routing (multiply scores of the routed contract's chunks by 3) is more robust than a hard filter when the title match is wrong.
- why now: most frequent train failure is 'ranked_too_low' (69 of 116 failing queries); entry targets it
- change: `routing.boost`: 1.0 -> 2.0, `routing.mode`: filter -> boost
- result: R@4 0.0213 (baseline) | this run 0.2884 | delta vs parent -0.0202; runtime 0.667s
- decision: guardrail failed: G2_correct_abstention

### 4. stopwords - rejected
- hypothesis: Dropping English function words reduces matches on 'this/the/under/any', which appear in every clause.
- why now: most frequent train failure is 'ranked_too_low' (69 of 116 failing queries); entry targets it
- change: `retrieval.bm25.tokenizer.stopwords`: none -> english
- result: R@4 0.0213 (baseline) | this run 0.2829 | delta vs parent -0.0257; runtime 0.36s
- decision: R@4 change -0.0257 is below the minimum gain 0.01

### 5. chunk-300 - rejected
- hypothesis: Gold spans have a median near 300 chars; 300-char chunks raise precision and make ranking more selective.
- why now: most frequent train failure is 'ranked_too_low' (69 of 116 failing queries); entry targets it
- change: `chunking.size_chars`: 500 -> 300
- result: R@4 0.0213 (baseline) | this run 0.2497 | delta vs parent -0.0589; runtime 0.746s
- decision: R@4 change -0.0589 is below the minimum gain 0.01

### 6. chunk-1000 - rejected
- hypothesis: Longer chunks cover multi-sentence clauses fully (fewer partial spans), at some cost in precision.
- why now: most frequent train failure is 'ranked_too_low' (69 of 116 failing queries); entry targets it
- change: `chunking.size_chars`: 500 -> 1000
- result: R@4 0.0213 (baseline) | this run 0.3995 | delta vs parent +0.0909; runtime 0.536s
- decision: guardrail failed: G1_precision

### 7. paragraph-chunks - accepted
- hypothesis: Chunks that respect paragraph boundaries keep a clause together instead of cutting it mid-sentence at a fixed offset.
- why now: most frequent train failure is 'ranked_too_low' (69 of 116 failing queries); entry targets it
- change: `chunking.size_chars`: 500 -> 800, `chunking.strategy`: fixed -> paragraph
- result: R@4 0.0213 (baseline) | this run 0.4122 | delta vs parent +0.1036; runtime 0.527s
- decision: R@4 +0.1036 >= 0.01 and P(gain)=1.000 >= 0.9; all guardrails pass

### 8. clause-chunks - rejected
- hypothesis: Splitting at section headings/numbering aligns chunks with legal clauses, which is how annotators mark answers.
- why now: most frequent train failure is 'ranked_too_low' (70 of 90 failing queries); entry targets it
- change: `chunking.strategy`: paragraph -> clause
- result: R@4 0.0213 (baseline) | this run 0.3764 | delta vs parent -0.0358; runtime 0.51s
- decision: guardrail failed: G1_precision, G3_recall_at_1

### 9. stem-light - accepted
- hypothesis: Light stemming matches 'assign/assignment/assigned', 'terminate/termination'.
- why now: most frequent train failure is 'ranked_too_low' (70 of 90 failing queries); entry targets it
- change: `retrieval.bm25.tokenizer.stem`: none -> light
- result: R@4 0.0213 (baseline) | this run 0.4483 | delta vs parent +0.0361; runtime 0.54s
- decision: R@4 +0.0361 >= 0.01 and P(gain)=0.924 >= 0.9; all guardrails pass

### 10. bm25-k1-low - rejected
- hypothesis: Lower k1 (1.0) reduces the reward for repeated terms, which favours long boilerplate chunks.
- why now: most frequent train failure is 'ranked_too_low' (68 of 84 failing queries); entry targets it
- change: `retrieval.bm25.k1`: 1.5 -> 1.0
- result: R@4 0.0213 (baseline) | this run 0.4412 | delta vs parent -0.0071; runtime 0.535s
- decision: R@4 change -0.0071 is below the minimum gain 0.01

### 11. bm25-b-high - rejected
- hypothesis: Higher length normalisation (b = 0.9) penalises long chunks that match by sheer length.
- why now: most frequent train failure is 'ranked_too_low' (68 of 84 failing queries); entry targets it
- change: `retrieval.bm25.b`: 0.75 -> 0.9
- result: R@4 0.0213 (baseline) | this run 0.4391 | delta vs parent -0.0092; runtime 0.712s
- decision: R@4 change -0.0092 is below the minimum gain 0.01

### 12. abstain-norm - rejected
- hypothesis: A score normalised by the query's idf mass is comparable across questions of different length, improving separation.
- why now: most frequent train failure is 'ranked_too_low' (68 of 84 failing queries); entry targets it
- change: `abstention.signal`: top1_score -> top1_norm
- result: R@4 0.0213 (baseline) | this run 0.4483 | delta vs parent +0.0000; runtime 0.559s
- decision: R@4 change +0.0000 is below the minimum gain 0.01

### 13. abstain-margin - rejected
- hypothesis: The margin between the first and second passage is a better confidence signal than the raw top score.
- why now: most frequent train failure is 'ranked_too_low' (68 of 84 failing queries); entry targets it
- change: `abstention.signal`: top1_score -> margin_norm
- result: R@4 0.0213 (baseline) | this run 0.4483 | delta vs parent +0.0000; runtime 0.556s
- decision: guardrail failed: G2_correct_abstention

### 14. overlap-100 - rejected
- hypothesis: 100-char overlap prevents a clause from being split exactly at a window boundary.
- why now: most frequent train failure is 'partial_span' (12 of 84 failing queries); entry targets it
- change: `chunking.overlap_chars`: 0 -> 100
- result: R@4 0.0213 (baseline) | this run 0.4483 | delta vs parent +0.0000; runtime 0.585s
- decision: R@4 change +0.0000 is below the minimum gain 0.01

### 15. expand-100 - rejected
- hypothesis: Growing each returned passage by 100 chars on both sides captures spans that straddle chunk edges.
- why now: most frequent train failure is 'partial_span' (12 of 84 failing queries); entry targets it
- change: `ranking.expand_chars`: 0 -> 100
- result: R@4 0.0213 (baseline) | this run 0.4424 | delta vs parent -0.0059; runtime 0.631s
- decision: guardrail failed: G1_precision

## Selected configuration (best on train)

`09-stem-light-89f3c1af` (iteration 9); accepted sequence: route-filter, paragraph-chunks, stem-light. Saved as `03_experiments/configs/final.yaml` (+ `final_resolved.yaml` with the frozen abstention threshold).
