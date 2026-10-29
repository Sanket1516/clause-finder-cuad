"""Document chunkers. Every chunker returns spans over the ORIGINAL text; `text` is always `document[start:end]`.
Nothing is normalised, so offsets can never drift (INV-1)."""
import re
from typing import Iterator

from ..common.config import ChunkingConfig
from ..common.schemas import Chunk


class ChunkIntegrityError(AssertionError):
    pass


_PARA = re.compile(r"\n[ \t]*\n")
# Section-heading shapes common in contracts: "ARTICLE IV", "Section 4.2", "4.2 Title", "(a) ..." is NOT a boundary.
_CLAUSE = re.compile(r"(?m)^[ \t]*(?:(?:ARTICLE|Article|SECTION|Section|EXHIBIT|Exhibit|SCHEDULE|Schedule)\b[ \t]*[\w.\-]*"
                     r"|\d{1,2}(?:\.\d{1,2}){0,3}[.)]?[ \t]+[A-Z\"])")
_SENT_END = re.compile(r"[.;:]\s")


def _trim(text: str, s: int, e: int) -> tuple[int, int]:
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    return s, e


def _split_long(text: str, s: int, e: int, size: int) -> Iterator[tuple[int, int]]:
    """Cut [s,e) into pieces <= size, preferring a sentence end, then whitespace, in the last 40% of the window."""
    while e - s > size:
        hard = s + size
        lo = s + int(size * 0.6)
        cut = None
        for m in _SENT_END.finditer(text, lo, hard):
            cut = m.end()
        if cut is None:
            ws = text.rfind(" ", lo, hard)
            cut = ws + 1 if ws != -1 else hard
        yield s, cut
        s = cut
    yield s, e


def _fixed(text: str, size: int, overlap: int) -> Iterator[tuple[int, int]]:
    step = size - overlap
    for i in range(0, len(text), step):
        yield i, min(i + size, len(text))
        if i + size >= len(text):
            break


def _packed(text: str, boundary: re.Pattern, size: int) -> Iterator[tuple[int, int]]:
    starts = sorted({0} | {m.end() if boundary is _PARA else m.start() for m in boundary.finditer(text)})
    blocks = [(a, b) for a, b in zip(starts, starts[1:] + [len(text)])]
    cur_s = cur_e = None
    for bs, be in blocks:
        if cur_s is not None and be - cur_s <= size:
            cur_e = be
            continue
        if cur_s is not None:
            yield cur_s, cur_e
            cur_s = cur_e = None
        if be - bs > size:
            pieces = list(_split_long(text, bs, be, size))
            for ps, pe in pieces[:-1]:
                yield ps, pe
            cur_s, cur_e = pieces[-1]
        else:
            cur_s, cur_e = bs, be
    if cur_s is not None:
        yield cur_s, cur_e


def chunk_document(doc_id: str, text: str, cfg: ChunkingConfig) -> list[Chunk]:
    if cfg.strategy == "fixed":
        spans = _fixed(text, cfg.size_chars, cfg.overlap_chars)
    elif cfg.strategy == "paragraph":
        spans = _packed(text, _PARA, cfg.size_chars)
    else:
        spans = _packed(text, _CLAUSE, cfg.size_chars)
    tag = f"{cfg.strategy}:{cfg.size_chars}:{cfg.overlap_chars}"
    out = []
    for s, e in spans:
        if cfg.strategy != "fixed":
            s, e = _trim(text, s, e)
        if e - s < cfg.min_chars or not text[s:e].strip():
            continue
        c = Chunk(chunk_id=f"{doc_id}::{s}-{e}", doc_id=doc_id, start=s, end=e, text=text[s:e], index_text=text[s:e], chunker=tag)
        if text[c.start:c.end] != c.text:  # INV-1, enforced at build time
            raise ChunkIntegrityError(c.chunk_id)
        out.append(c)
    return out
