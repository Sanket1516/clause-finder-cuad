# Baseline failure analysis (train)

Experiment `baseline-921dcc6f` · split **train** (purpose: development) · 140 answerable and 39 unanswerable queries · primary k = 4

## Headline numbers (ranking view, before the abstention gate)

| k | recall | precision |
|---|---|---|
| 1 | 0.0000 | 0.0000 |
| 2 | 0.0006 | 0.0003 |
| 4 | 0.0213 | 0.0066 |
| 8 | 0.0944 | 0.0106 |
| 16 | 0.1731 | 0.0123 |
| 32 | 0.3025 | 0.0107 |
| 64 | 0.4282 | 0.0072 |

## Abstention (decision-level; not character metrics)

Threshold 28.3653, calibrated on train answerable queries.

| | answered | abstained | total |
|---|---|---|---|
| answerable | 134 | 6 (**false abstention**) | 140 |
| unanswerable | 32 (**false answer**) | 7 (correct abstention) | 39 |

False-abstention rate 0.043 · correct-abstention rate 0.179 · false-answer rate 0.821 · AUROC of the confidence signal 0.546

## Failure categories (answerable queries, ranking view)

| label | n | share | meaning |
|---|---|---|---|
| ranked_too_low | 71 | 50.7% | gold text is retrieved, but only at rank > k |
| right_doc_wrong_section | 59 | 42.1% | gold never retrieved in the top 64; the top-1 passage is in the right contract |
| partial_span | 9 | 6.4% | right place, but the returned text covers only part of the gold span(s) |
| hit | 1 | 0.7% | recall@k >= 0.99 |

Flagged `ambiguous_ground_truth` (gold covers >40% of the contract or <15 chars): **0** queries.

## Unanswerable queries by category

| category | n | correctly abstained |
|---|---|---|
| absent_clause | 26 | 0 |
| not_in_corpus | 7 | 7 |
| out_of_scope | 6 | 0 |

## Reviewable examples

Each example shows the question, the gold text (evaluation only) and what the system returned at ranks 1-2. Offsets are `[start, end)` into the original document.

### ranked_too_low (71)

- **cuad-mini-002** · What is the governing law for this contract?  
  contract `BICYCLETHERAPEUTICSPLC_03_10_2020-EX-10.11-SERVICE AGREEMENT` · gold 53956-54252 (1 span(s)) · first gold overlap at rank 53  
  gold: “This Agreement shall be governed by and interpreted in accordance with the laws of England and Wales and the parties to this Agreement submit to the exclusive jurisdiction of the Courts of England and Wales in relation t...”  
  rank 1 (same contract, 0-500, score 41.90): “Exhibit 10.11 DATED 26 September 2019 BicycleTX Ltd and Nigel Crockett ___________________________________________________ SERVICE AGREEMENT ___________________...”  
  rank 2 (same contract, 56500-57000, score 29.18): “any other way, including but not limited to by way of a merger. 19 THIS AGREEMENT has been executed and delivered as a deed by or on behalf of the parties on th...”  

- **cuad-mini-006** · What is the expiration date of this contract?  
  contract `HPILHOLDING_01_07_2015-EX-99.1-COOPERATION AGREEMENT.txt` · gold 5604-5739 (1 span(s)) · first gold overlap at rank 7  
  gold: “The term of this Agreement shall be one (1) year unless terminated earlier in accordance with the terms of this Agreement (the "Term").”  
  rank 1 (same contract, 3500-4000, score 53.16): “T THIS COOPERATION AGREEMENT ("Agreement") is signed this 5th day of January, 2015 (the "Closing Date"), by and between HPIL ENERGYTECH Inc., a Nevada (USA) cor...”  
  rank 2 (same contract, 0-500, score 49.96): “COOPERATION AGREEMENT made by and between HPIL ENERGYTECH Inc. and GINARES GROUP AG January 5, 2015 Table of Contents 1. Term......................................”  

- **cuad-mini-010** · Is there a cap on liability under this contract?  
  contract `HPILHOLDING_01_07_2015-EX-99.1-COOPERATION AGREEMENT.txt` · gold 11380-11583 (2 span(s)) · first gold overlap at rank 9  
  gold: “GINARES agrees that the sole and exclusive remedy for money damages related to this Agreement and the transactions contemplated hereby shall be the rights to indemnification set forth in this Section 9.”  
  rank 1 (same contract, 3500-4000, score 53.63): “T THIS COOPERATION AGREEMENT ("Agreement") is signed this 5th day of January, 2015 (the "Closing Date"), by and between HPIL ENERGYTECH Inc., a Nevada (USA) cor...”  
  rank 2 (same contract, 0-500, score 49.77): “COOPERATION AGREEMENT made by and between HPIL ENERGYTECH Inc. and GINARES GROUP AG January 5, 2015 Table of Contents 1. Term......................................”  

### right_doc_wrong_section (59)

- **cuad-mini-000** · What is the expiration date of this contract?  
  contract `GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content ` · gold 598-989 (1 span(s)) · first gold overlap at rank None  
  gold: “The rights granted hereunder shall be effective as of the Effective Date and shall expire on December 31, 2006 (the "Term"); provided, however, that with respect to each Property, including Robots, Kingdom of Heaven, Mr....”  
  rank 1 (same contract, 0-500, score 65.89): “AMENDMENT NO. 3 Dated as of February 19, 2007 Reference is hereby made to that certain fully executed Wireless Content License Agreement Number 12965 dated as o...”  
  rank 2 (same contract, 1500-1902, score 50.06): “e to all of the terms and conditions hereof. Glu Mobile Inc. ("Licensee") Fox Mobile Entertainment, Inc. ("Fox") By: /s/ Albert A. Pimentel By: /s/ Jamie Samson...”  

- **cuad-mini-003** · Are there any exceptions to competitive restrictions in this contract?  
  contract `BICYCLETHERAPEUTICSPLC_03_10_2020-EX-10.11-SERVICE AGREEMENT` · gold 33572-34034 (1 span(s)) · first gold overlap at rank None  
  gold: “save that nothing in this paragraph 13.2 shall prevent you from holding (with the prior written consent of the Company, which shall not be unreasonably delayed or withheld) up to three percent (3%) of the issued equity s...”  
  rank 1 (same contract, 0-500, score 39.95): “Exhibit 10.11 DATED 26 September 2019 BicycleTX Ltd and Nigel Crockett ___________________________________________________ SERVICE AGREEMENT ___________________...”  
  rank 2 (same contract, 56500-57000, score 30.31): “any other way, including but not limited to by way of a merger. 19 THIS AGREEMENT has been executed and delivered as a deed by or on behalf of the parties on th...”  

- **cuad-mini-004** · Does this contract include any right of first refusal, right of first offer, or right of first negotiation?  
  contract `BICYCLETHERAPEUTICSPLC_03_10_2020-EX-10.11-SERVICE AGREEMENT` · gold 6235-6531 (2 span(s)) · first gold overlap at rank None  
  gold: “On or as soon as practicable following the Effective Date, it is intended that you will be granted an option under the Option Plan to acquire 107,417 ordinary shares in the capital of BTL ("Shares") (representing approxi...”  
  rank 1 (same contract, 0-500, score 40.07): “Exhibit 10.11 DATED 26 September 2019 BicycleTX Ltd and Nigel Crockett ___________________________________________________ SERVICE AGREEMENT ___________________...”  
  rank 2 (same contract, 56500-57000, score 30.36): “any other way, including but not limited to by way of a merger. 19 THIS AGREEMENT has been executed and delivered as a deed by or on behalf of the parties on th...”  

### partial_span (9)

- **cuad-mini-055** · Does this contract include an exclusivity agreement?  
  contract `PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTELLECTUAL PROPERT` · gold 3388-4736 (3 span(s)) · first gold overlap at rank 4  
  gold: “The licenses granted herein are exclusive worldwide licenses to: 1. make, have made, use, lease, sell and import Licensed Products for the legal purposes of researching, developing, manufacturing, assembling, distributin...”  
  rank 1 (same contract, 0-500, score 48.16): “Exhibit 10.2 INTELLECTUAL PROPERTY AGREEMENT This Intellectual Property Agreement (this "Agreement") is entered into on May 12, 2020 ("Effective Date"), concern...”  
  rank 2 (same contract, 14000-14500, score 46.78): “an hourly rate to Mohammed Zulfiquar and his designees. (b). Premier may partner with other organizations as needed to effectuate the development of technology ...”  

- **cuad-mini-064** · Is there a clause preventing the solicitation of customers in this contract?  
  contract `DYNAMEXINC_06_06_1996-EX-10.4-TRANSPORTATION SERVICES AGREEM` · gold 7291-7515 (2 span(s)) · first gold overlap at rank 4  
  gold: “Except for the joint marketing efforts referred to in Section 3.1 (v) above, Purolator agrees not to directly or indirectly solicit next day or multiple day freight from existing sameday customers of Dynamex.”  
  rank 1 (same contract, 0-500, score 61.94): “1 EXHIBIT 10.4 MARKETING AND TRANSPORTATION SERVICES AGREEMENT THIS AGREEMENT made in duplicate this 20 day of November, 1995. B E T W E E N: PUROLATOR COURIER ...”  
  rank 2 (same contract, 48500-49000, score 45.76): “e written by their proper officers duly authorized on that behalf. PARCELWAY COURIER SYSTEMS CANADA LTD. Per: (ILLEGIBLE) 11/20/95 c/s -------------------------...”  

- **cuad-mini-073** · Does this contract include any revenue or profit-sharing arrangements?  
  contract `RgcResourcesInc_20151216_8-K_EX-10.3_9372751_EX-10.3_Franchi` · gold 1896-2484 (1 span(s)) · first gold overlap at rank 3  
  gold: “Grantor's Franchise Fee shall be a percentage share of the base year total annual Franchise Fee, which shall be determined on a pro rata basis according to its percentage share of the total dollar value of Grantee's gas ...”  
  rank 1 (same contract, 0-500, score 44.02): “Exhibit 10.3 GAS FRANCHISE AGREEMENT THIS AGREEMENT ("Agreement"), made and entered into this 17th day of November, 2015, by and between the TOWN OF VINTON, VIR...”  
  rank 2 (same contract, 4000-4500, score 34.23): “s (or any other address the party to be notified may have designated to the sender by like notice): Grantor: Grantee: Town of Vinton Roanoke Gas Company Attenti...”  

### false_answer (32 of 39 unanswerable)

- **unans-002** [absent_clause] Consider the Amendment No. 3 to Wireless Content License Agreement between Fox Mobile Entertainment, Inc. and Glu Mobile Inc.; Who owns the intellectual propert...  
  top passage (score 64.45): “AMENDMENT NO. 3 Dated as of February 19, 2007 Reference is hereby made to that certain fully executed Wireless Content License Agreement Number 12965 dated as o...”  
- **unans-005** [absent_clause] Consider the Amendment No. 3 to Wireless Content License Agreement between Fox Mobile Entertainment, Inc. and Glu Mobile Inc.; What is the governing law for thi...  
  top passage (score 66.57): “AMENDMENT NO. 3 Dated as of February 19, 2007 Reference is hereby made to that certain fully executed Wireless Content License Agreement Number 12965 dated as o...”  
- **unans-006** [absent_clause] Consider the Amendment No. 3 to Wireless Content License Agreement between Fox Mobile Entertainment, Inc. and Glu Mobile Inc.; What indemnification obligations ...  
  top passage (score 64.45): “AMENDMENT NO. 3 Dated as of February 19, 2007 Reference is hereby made to that certain fully executed Wireless Content License Agreement Number 12965 dated as o...”  
- **unans-007** [absent_clause] Consider the Amendment No. 3 to Wireless Content License Agreement between Fox Mobile Entertainment, Inc. and Glu Mobile Inc.; Is there a confidentiality obliga...  
  top passage (score 65.70): “AMENDMENT NO. 3 Dated as of February 19, 2007 Reference is hereby made to that certain fully executed Wireless Content License Agreement Number 12965 dated as o...”  

## Notes

- Ground-truth text above is shown for review only; it was never an input to retrieval.
- A `false_answer` means the gate did not withhold; it does not mean the returned text is a wrong clause.
