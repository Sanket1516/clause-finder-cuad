"""Ranking post-processing: overlap removal (INV-4), optional expansion, rank assignment."""
from ..common.schemas import RetrievedPassage


def remove_overlaps(passages: list[RetrievedPassage]) -> list[RetrievedPassage]:
    """Keep the best-ranked passage whenever two passages of the same document overlap. Input must be ranked best-first."""
    kept: list[RetrievedPassage] = []
    by_doc: dict[str, list[tuple[int, int]]] = {}
    for p in passages:
        spans = by_doc.setdefault(p.doc_id, [])
        if any(p.start < e and s < p.end for s, e in spans):
            continue
        spans.append((p.start, p.end))
        kept.append(p)
    return kept


def expand(p: RetrievedPassage, doc_text: str, chars: int) -> RetrievedPassage:
    """Grow a passage by `chars` on each side, clipped to the document. Text is re-sliced from the original document."""
    s, e = max(0, p.start - chars), min(len(doc_text), p.end + chars)
    return p.model_copy(update={"start": s, "end": e, "text": doc_text[s:e]})


def assign_ranks(passages: list[RetrievedPassage]) -> list[RetrievedPassage]:
    return [p.model_copy(update={"rank": i + 1}) for i, p in enumerate(passages)]
