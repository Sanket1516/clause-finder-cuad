"""Transparent BM25 (Lucene-style non-negative idf) over chunk `index_text`.
Written out in full rather than imported, so every number in a score can be explained in the debrief.

score(q, c) = sum over DISTINCT query terms t present in c of
              idf(t) * tf(t,c) * (k1 + 1) / (tf(t,c) + k1 * (1 - b + b * len(c) / avg_len))
idf(t) = ln(1 + (N - n_t + 0.5) / (n_t + 0.5))
Ties are broken by chunk order (document id, then start offset), so ranking is fully deterministic."""
import math
import re
from collections import Counter, defaultdict

import numpy as np

from ..common.config import Bm25Config, TokenizerConfig
from ..common.schemas import Chunk

_TOKEN = re.compile(r"[A-Za-z0-9]+")
STOPWORDS_ENGLISH = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were will with "
    "under any there which shall such".split())


def _light_stem(t: str) -> str:
    for suf in ("ies", "es", "s", "ing", "ed"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)] + ("y" if suf == "ies" else "")
    return t


def tokenize(text: str, cfg: TokenizerConfig) -> list[str]:
    toks = _TOKEN.findall(text.lower() if cfg.lowercase else text)
    toks = [t for t in toks if len(t) >= cfg.min_token_len]
    if cfg.stopwords == "english":
        toks = [t for t in toks if t.lower() not in STOPWORDS_ENGLISH]
    if cfg.stem == "light":
        toks = [_light_stem(t) for t in toks]
    return toks


class BM25Index:
    def __init__(self, chunks: list[Chunk], cfg: Bm25Config):
        self.cfg = cfg
        self.chunks = chunks
        self.n = len(chunks)
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        lens = np.zeros(self.n)
        for i, c in enumerate(chunks):
            tf = Counter(tokenize(c.index_text, cfg.tokenizer))
            lens[i] = sum(tf.values())
            for t, f in tf.items():
                self.postings[t].append((i, f))
        self.lens = lens
        self.avg_len = float(lens.mean()) if self.n else 0.0
        self.idf = {t: math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def query_terms(self, query: str) -> list[str]:
        return sorted(set(tokenize(query, self.cfg.tokenizer)))

    def scores(self, query: str) -> tuple[np.ndarray, float]:
        """Return (score per chunk, query_mass) where query_mass = sum of idf over distinct query terms found in the index."""
        k1, b = self.cfg.k1, self.cfg.b
        s = np.zeros(self.n)
        mass = 0.0
        norm = k1 * (1 - b + b * self.lens / (self.avg_len or 1.0))
        for t in self.query_terms(query):
            post = self.postings.get(t)
            if not post:
                continue
            idf = self.idf[t]
            mass += idf
            idx = np.fromiter((i for i, _ in post), dtype=np.int64, count=len(post))
            tf = np.fromiter((f for _, f in post), dtype=np.float64, count=len(post))
            s[idx] += idf * tf * (k1 + 1) / (tf + norm[idx])
        return s, mass

    def coverage(self, query: str, chunk_index: int) -> float:
        """Share of the query's distinctive words (idf-weighted, only words present in the corpus) found in chunk `chunk_index`."""
        terms = [t for t in self.query_terms(query) if t in self.idf]
        total = sum(self.idf[t] for t in terms)
        if total <= 0:
            return 0.0
        have = set(tokenize(self.chunks[chunk_index].index_text, self.cfg.tokenizer))
        return sum(self.idf[t] for t in terms if t in have) / total

    def top(self, query: str, n: int) -> tuple[list[tuple[int, float]], float]:
        """Top-n (chunk_index, score) with score > 0, ordered by (-score, chunk_index). Chunks arrive pre-sorted by (doc, start)."""
        s, mass = self.scores(query)
        order = np.lexsort((np.arange(self.n), -s))
        out = [(int(i), float(s[i])) for i in order[:n] if s[i] > 0]
        return out, mass
