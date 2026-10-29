# Final configuration: failure analysis (train)

Experiment `final-547ff2f3` · split **train** (purpose: development) · 140 answerable and 39 unanswerable queries · primary k = 4

## Headline numbers (ranking view, before the abstention gate)

| k | recall | precision |
|---|---|---|
| 1 | 0.2137 | 0.1199 |
| 2 | 0.3366 | 0.1089 |
| 4 | 0.4483 | 0.0752 |
| 8 | 0.5916 | 0.0561 |
| 16 | 0.7187 | 0.0357 |
| 32 | 0.8409 | 0.0240 |
| 64 | 0.9087 | 0.0188 |

## Abstention (decision-level; not character metrics)

Threshold 0.2401, calibrated on train answerable queries.

| | answered | abstained | total |
|---|---|---|---|
| answerable | 133 | 7 (**false abstention**) | 140 |
| unanswerable | 23 (**false answer**) | 16 (correct abstention) | 39 |

False-abstention rate 0.050 · correct-abstention rate 0.410 · false-answer rate 0.590 · AUROC of the confidence signal 0.737

## Failure categories (answerable queries, ranking view)

| label | n | share | meaning |
|---|---|---|---|
| ranked_too_low | 68 | 48.6% | gold text is retrieved, but only at rank > k |
| hit | 56 | 40.0% | recall@k >= 0.99 |
| partial_span | 12 | 8.6% | right place, but the returned text covers only part of the gold span(s) |
| right_doc_wrong_section | 4 | 2.9% | gold never retrieved in the top 64; the top-1 passage is in the right contract |

Flagged `ambiguous_ground_truth` (gold covers >40% of the contract or <15 chars): **0** queries.

## Unanswerable queries by category

| category | n | correctly abstained |
|---|---|---|
| absent_clause | 26 | 12 |
| not_in_corpus | 7 | 3 |
| out_of_scope | 6 | 1 |

## Reviewable examples

Each example shows the question, the gold text (evaluation only) and what the system returned at ranks 1-2. Offsets are `[start, end)` into the original document.

### ranked_too_low (68)

- **cuad-mini-003** · Are there any exceptions to competitive restrictions in this contract?  
  contract `BICYCLETHERAPEUTICSPLC_03_10_2020-EX-10.11-SERVICE AGREEMENT` · gold 33572-34034 (1 span(s)) · first gold overlap at rank 21  
  gold: “save that nothing in this paragraph 13.2 shall prevent you from holding (with the prior written consent of the Company, which shall not be unreasonably delayed or withheld) up to three percent (3%) of the issued equity s...”  
  rank 1 (same contract, 40340-41049, score 11.07): “14.3 While the restrictions set out in paragraph 14.2 above are considered by the parties to be reasonable in all the circumstances, it is agreed that if any on...”  
  rank 2 (same contract, 32706-33277, score 9.50): “(d) information regarding any of the Company's business partners and their services, including names, representatives, proposals, bids, contracts and their cont...”  

- **cuad-mini-004** · Does this contract include any right of first refusal, right of first offer, or right of first negotiation?  
  contract `BICYCLETHERAPEUTICSPLC_03_10_2020-EX-10.11-SERVICE AGREEMENT` · gold 6235-6531 (2 span(s)) · first gold overlap at rank 18  
  gold: “On or as soon as practicable following the Effective Date, it is intended that you will be granted an option under the Option Plan to acquire 107,417 ordinary shares in the capital of BTL ("Shares") (representing approxi...”  
  rank 1 (same contract, 52986-53756, score 8.07): “18.10 We reserve the right to amend the documents referred to above from time to time. 19 THIRD PARTY RIGHTS Save in respect of any rights conferred by this Agr...”  
  rank 2 (same contract, 32212-32705, score 7.76): “lists, names, addresses (including email), telephone, facsimile or other contact numbers and contact names, representatives, their needs or desires with respect...”  

- **cuad-mini-005** · How is intellectual property ownership assigned in this contract?  
  contract `BICYCLETHERAPEUTICSPLC_03_10_2020-EX-10.11-SERVICE AGREEMENT` · gold 44840-45359 (1 span(s)) · first gold overlap at rank 7  
  gold: “To the extent that such IPRs do not vest automatically in the Company by operation of law, you hereby assign and agree to assign to the Company all of your right, title and interest in any existing and future IPRs which ...”  
  rank 1 (same contract, 48467-48963, score 10.93): “During the term of your employment and at all times thereafter subject always to your obligations to third parties, you shall furnish such information and prope...”  
  rank 2 (same contract, 42555-43347, score 10.88): “15.1 For the purpose of this paragraph 15 "IPRs" shall mean all trade secrets, Copyrights, trademarks and trade and business names (including goodwill associate...”  

- **cuad-mini-006** · What is the expiration date of this contract?  
  contract `HPILHOLDING_01_07_2015-EX-99.1-COOPERATION AGREEMENT.txt` · gold 5604-5739 (1 span(s)) · first gold overlap at rank 12  
  gold: “The term of this Agreement shall be one (1) year unless terminated earlier in accordance with the terms of this Agreement (the "Term").”  
  rank 1 (same contract, 8049-8739, score 4.97): “7.2. Consents To GINARES's knowledge, no consent, approval, order or authorization of, or registration, qualification, designation, declaration or filing with, ...”  
  rank 2 (same contract, 9481-10164, score 4.95): “Consents To HPIL ET's knowledge, no consent, approval, order or authorization of, or registration, qualification, designation, declaration or filing with, any f...”  

### partial_span (12)

- **cuad-mini-055** · Does this contract include an exclusivity agreement?  
  contract `PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTELLECTUAL PROPERT` · gold 3388-4736 (3 span(s)) · first gold overlap at rank 3  
  gold: “The licenses granted herein are exclusive worldwide licenses to: 1. make, have made, use, lease, sell and import Licensed Products for the legal purposes of researching, developing, manufacturing, assembling, distributin...”  
  rank 1 (same contract, 11679-12406, score 8.43): “2. This License does not include a minimum annual royalty payable by THI to Marv. 3. Fair Market Value" means, with respect to any Licensed Product sold, leased...”  
  rank 2 (same contract, 17699-18490, score 7.26): “material prepared by the Recipient or its Representatives which contain or reflect or are based upon, in whole or in part, information furnished by the Disclosi...”  

- **cuad-mini-057** · What licenses are granted under this contract?  
  contract `PREMIERBIOMEDICALINC_05_14_2020-EX-10.2-INTELLECTUAL PROPERT` · gold 3264-3378 (4 span(s)) · first gold overlap at rank 1  
  gold: “THI is granted the following rights to the Applications in Appendix A and the Licensed Products derived therefrom:”  
  rank 1 (same contract, 2803-3457, score 15.65): “AGREEMENT 1. RECITALS. The Recitals are hereby incorporated herein by this reference, as if fully restated herein. 2. LICENSING. To the extent that terms in the...”  
  rank 2 (same contract, 4750-5453, score 13.95): “Licenses granted herein are solely for products in the form sold by the Licensee and are not to be construed either (i) as consent by the Marv to any act which ...”  

- **cuad-mini-061** · Are there any exceptions to competitive restrictions in this contract?  
  contract `DYNAMEXINC_06_06_1996-EX-10.4-TRANSPORTATION SERVICES AGREEM` · gold 8102-8548 (2 span(s)) · first gold overlap at rank 3  
  gold: “It is understood and agreed that Dynamex, from time to time and upon request, may provide pick-up and/or delivery services for other next-day or multiple day courier service providers, as part of their next-day and multi...”  
  rank 1 (same contract, 37032-37496, score 8.64): “(d) there are no pending or threatened actions or proceedings to which Purolator is a Party, or which is before any court or administrative agency, which might ...”  
  rank 2 (same contract, 35690-36377, score 8.31): “(d) there are no pending or threatened actions or proceedings to Dynamex is a Party, or which is before any court or administrative agency, which might material...”  

- **cuad-mini-070** · Is there a cap on liability under this contract?  
  contract `DYNAMEXINC_06_06_1996-EX-10.4-TRANSPORTATION SERVICES AGREEM` · gold 16459-16927 (2 span(s)) · first gold overlap at rank 3  
  gold: “Such liability shall not exceed the other Party's contractual liability to its customers. The Parties acknowledge that their contract of carriage with their customers provides that liability for loss, damage or delay, in...”  
  rank 1 (same contract, 37032-37496, score 13.06): “(d) there are no pending or threatened actions or proceedings to which Purolator is a Party, or which is before any court or administrative agency, which might ...”  
  rank 2 (same contract, 35690-36377, score 11.77): “(d) there are no pending or threatened actions or proceedings to Dynamex is a Party, or which is before any court or administrative agency, which might material...”  

### right_doc_wrong_section (4)

- **cuad-mini-085** · Does this contract include any revenue or profit-sharing arrangements?  
  contract `KINGPHARMACEUTICALSINC_08_09_2006-EX-10.1-PROMOTION AGREEMEN` · gold 98802-99086 (2 span(s)) · first gold overlap at rank None  
  gold: “In consideration for King's performance of its obligations under this Agreement, Depomed shall pay promotion fees (the "Promotion Fees") to King as follows: following each Agreement Quarter during the Term, Depomed shall...”  
  rank 1 (same contract, 90812-91188, score 11.39): “(b) King will work on behalf of Depomed to provide necessary support for managed markets and trade customer groups with respect to the Product to enable Depomed...”  
  rank 2 (same contract, 89362-90112, score 11.37): “(a) Depomed or its Affiliates shall book all sales of the Product in the Territory and shall be responsible for entering into any contracts and other arrangemen...”  

- **cuad-mini-167** · Can this contract be terminated for convenience, and under what conditions?  
  contract `BONTONSTORESINC_04_20_2018-EX-99.3-AGENCY AGREEMENT.txt` · gold 67047-67461 (1 span(s)) · first gold overlap at rank None  
  gold: “Subject to the Wind-Down Budget and payment of Expenses, Agent shall use the E-Commerce Platform in connection with the GOB Sale to fulfill customer orders made during the GOB Sale Term and otherwise promote the GOB Sale...”  
  rank 1 (same contract, 107633-108277, score 8.82): “15.9 Section Headings. The headings of sections of this Agreement are inserted for convenience only and shall not be considered for the purpose of determining t...”  
  rank 2 (same contract, 17814-18600, score 7.92): “(xviii) the designee under any Lease/Contract Assumption Notice shall be required, if requested by the applicable counterparty, to provide adequate assurance of...”  

- **cuad-mini-168** · Is there an anti-assignment clause in this contract?  
  contract `BONTONSTORESINC_04_20_2018-EX-99.3-AGENCY AGREEMENT.txt` · gold 105765-106250 (1 span(s)) · first gold overlap at rank None  
  gold: “This Agreement shall inure to the benefit of and be binding upon the Parties and their respective successors and assigns, including, but not limited to, any chapter 11 or chapter 7 trustee; provided, however, that this A...”  
  rank 1 (same contract, 98888-99686, score 13.80): “The Approval Order shall provide that (a) the counterparties to the Leases or Contracts identified in any Lease/Contract Assumption Notice shall have twenty-one...”  
  rank 2 (same contract, 135796-136327, score 12.58): “PLEASE TAKE FURTHER NOTICE that objections, if any, to the assumption and assignment of any Lease or Contract must be filed with the Bankruptcy Court and served...”  

- **cuad-mini-173** · Is there a most favored nation clause in this contract?  
  contract `IGENEBIOTECHNOLOGYINC_05_13_2003-EX-1-JOINT VENTURE AGREEMEN` · gold 28071-28291 (1 span(s)) · first gold overlap at rank None  
  gold: “The grant of licenses to any third parties shall be the prerogative of the Board provided that no such license shall be granted at terms more favorable to the third party than were offered to the member(s) of such Party.”  
  rank 1 (same contract, 9667-10046, score 8.51): “(b) Notwithstanding clause (a) above, nothing contained in this Agreement will require or obligate either Party to initiate any litigation to which any governme...”  
  rank 2 (same contract, 61397-61945, score 6.27): “provided, however, that neither Party will be prohibited from using such documents and information in litigation against the other Party. C. The Parties shall c...”  

### false_answer (23 of 39 unanswerable)

- **unans-008** [absent_clause] Consider the Gas Franchise Agreement between the Town of Vinton and Roanoke Gas Company; What warranties does the grantee give under this contract?  
  top passage (score 11.29): “5. NONDISCRIMINATION. Grantee shall not discriminate on the basis of race, religion, color, sex, national origin, age, disability, or any other basis prohibited...”  
- **unans-009** [absent_clause] Consider the Gas Franchise Agreement between the Town of Vinton and Roanoke Gas Company; Is there an indemnification obligation under this contract?  
  top passage (score 6.63): “5. NONDISCRIMINATION. Grantee shall not discriminate on the basis of race, religion, color, sex, national origin, age, disability, or any other basis prohibited...”  
- **unans-013** [absent_clause] Consider the Endorsement Agreement between Holiday RV Superstores, Inc. and Affinity Group, Inc. for Good Sam Branding; Can the company clip or excerpt the endo...  
  top passage (score 12.02): “WHEREAS, AGI, either directly or through subsidiaries, operates the "Good Sam" club for recreational vehicle enthusiasts; and WHEREAS, the Company has determine...”  
- **unans-018** [absent_clause] Consider the Co-Branding and Services Agreement between RSL COM PrimeCall, Inc. and deltathree.com, Inc.; Are there any tax withholding or tax allocation provis...  
  top passage (score 8.34): “Section 9.13 [Third Parties]. Third Parties. There are no intended third party beneficiaries to this Agreement. Section 9.14 [Counterparts]. Counterparts. This ...”  

## Notes

- Ground-truth text above is shown for review only; it was never an input to retrieval.
- A `false_answer` means the gate did not withhold; it does not mean the returned text is a wrong clause.
