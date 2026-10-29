"""Document routing from the contract title the user names in the question ("Consider the <title>; ...").
Inference-time inputs only: the question text and the corpus. Gold annotations are never visible here."""
import re

from ..common.config import Bm25Config
from ..common.schemas import Chunk
from .lexical import BM25Index

_PREFIX = re.compile(r"^\s*Consider\s+(?P<title>[^;]{3,400});\s*(?P<rest>.*)$", re.S)


def split_title(query: str) -> tuple[str | None, str]:
    """('<title>', '<question without the title clause>') or (None, query) when the question names no contract."""
    m = _PREFIX.match(query)
    if not m:
        return None, query
    return m.group("title").strip(), m.group("rest").strip()


class DocRouter:
    """Scores each contract's opening text (parties, title, recitals) against the title the user named."""

    def __init__(self, store, head_chars: int, bm25: Bm25Config):
        heads = [Chunk(chunk_id=f"{d}::head", doc_id=d, start=0, end=min(head_chars, len(store.text(d))),
                       text=store.text(d)[:head_chars], index_text=store.text(d)[:head_chars], chunker="head")
                 for d in store.doc_ids()]
        self.index = BM25Index(heads, bm25)
        self.heads = heads

    def route(self, title: str, top_docs: int) -> list[tuple[str, float]]:
        ranked, _ = self.index.top(title, top_docs)
        return [(self.heads[i].doc_id, s) for i, s in ranked]
