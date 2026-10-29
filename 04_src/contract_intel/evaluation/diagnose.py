"""Failure taxonomy (01_planning/evaluation_protocol.md section 6, as amended by Amendment 1).

Ranking-view label for an ANSWERABLE query, evaluated at primary_k over the top-64 non-overlapping candidates:
  hit                   recall@k >= 0.99
  partial_span          0 < recall@k < 0.99               (right place, span only partly covered)
  ranked_too_low        recall@k == 0, but a candidate at rank > k overlaps the gold text (found within top 64)
  right_doc_wrong_section  gold never overlapped in the top 64, but the top-1 passage is in the gold document
  wrong_document        gold never overlapped in the top 64, and the top-1 passage is in another document
  no_candidates         the retriever returned nothing at all
  ingestion_failure     a returned passage's text does not equal document[start:end]   (never expected; guards INV-1)
Orthogonal flags: ambiguous_ground_truth (gold covers >40% of the document or < 15 chars: scoring is unreliable),
false_abstention (end-to-end view: the gate withheld the answer).
UNANSWERABLE queries: correct_abstention | false_answer."""
from .metrics import Interval

LABELS_ANSWERABLE = ["hit", "partial_span", "ranked_too_low", "right_doc_wrong_section", "wrong_document",
                     "no_candidates", "ingestion_failure"]


def _overlaps(c: Interval, gold: list[Interval]) -> bool:
    return any(c[0] == g[0] and c[1] < g[2] and g[1] < c[2] for g in gold)


def first_overlap_rank(cands: list[Interval], gold: list[Interval]) -> int | None:
    for i, c in enumerate(cands):
        if _overlaps(c, gold):
            return i + 1
    return None


def diagnose_answerable(cands: list[Interval], gold: list[Interval], recall_at_k: float, k: int, doc_len: int,
                        offsets_ok: bool = True) -> dict:
    found = first_overlap_rank(cands, gold)
    gold_chars = sum(e - s for _, s, e in gold)
    flags = []
    if doc_len and (gold_chars / doc_len > 0.4 or gold_chars < 15):
        flags.append("ambiguous_ground_truth")
    top1_ok = bool(cands) and cands[0][0] == gold[0][0]
    if not offsets_ok:
        label = "ingestion_failure"
    elif not cands:
        label = "no_candidates"
    elif recall_at_k >= 0.99:
        label = "hit"
    elif recall_at_k > 0:
        label = "partial_span"
    elif found is not None:
        label = "ranked_too_low"
    else:
        label = "right_doc_wrong_section" if top1_ok else "wrong_document"
    return {"label": label, "found_rank": found, "top1_doc_correct": top1_ok, "flags": flags}


def diagnose_unanswerable(abstained: bool) -> dict:
    return {"label": "correct_abstention" if abstained else "false_answer", "found_rank": None, "top1_doc_correct": None, "flags": []}
