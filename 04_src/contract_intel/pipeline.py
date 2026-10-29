"""The retrieval pipeline. `search(query: str)` is the ONLY inference entry point: it receives the question text and
nothing else, so benchmark annotations cannot reach it (INV-3).

  question -> [title routing] -> BM25 over chunks -> [expand] -> overlap removal -> ranked candidates
           -> confidence signal -> abstention gate -> SearchResponse
"""
import time

from .abstention.gate import confidence, decide
from .chunking import chunk_document
from .common.config import PipelineConfig, config_hash
from .common.logging import get_logger, timed
from .common.schemas import Chunk, RetrievedPassage, SearchResponse
from .data.corpus import DocumentStore
from .ranking.postprocess import assign_ranks, expand, remove_overlaps
from .retrieval.lexical import BM25Index
from .retrieval.router import DocRouter, split_title

log = get_logger()


class Pipeline:
    def __init__(self, cfg: PipelineConfig, store: DocumentStore):
        t0 = time.perf_counter()
        self.cfg = cfg
        self.store = store
        self.config_hash = config_hash(cfg)
        self.experiment_id = f"{cfg.name}-{self.config_hash[:8]}"
        self.chunks: list[Chunk] = []
        for d in store.doc_ids():  # sorted -> deterministic chunk order (doc, start)
            self.chunks.extend(chunk_document(d, store.text(d), cfg.chunking))
        if not self.chunks:
            raise ValueError("no chunks were produced; is the corpus empty?")
        self.index = BM25Index(self.chunks, cfg.retrieval.bm25)
        self.router = (DocRouter(store, cfg.routing.head_chars, cfg.retrieval.bm25)
                       if cfg.routing.mode != "none" else None)
        self.build_seconds = round(time.perf_counter() - t0, 3)
        log.info("built %s: %d docs, %d chunks in %.2fs", self.experiment_id, len(store.doc_ids()), len(self.chunks), self.build_seconds)

    # -- retrieval without the abstention gate (used by the evaluator and by search) --
    def retrieve(self, query: str) -> tuple[list[RetrievedPassage], float, dict[str, float]]:
        lat: dict[str, float] = {}
        cfg = self.cfg
        title, rest = split_title(query)
        scored_text = rest if (cfg.query.strip_title_prefix and title is not None and rest) else query
        routed: set[str] | None = None
        title_match = 1.0  # neutral when the question names no contract
        with timed(lat, "route_ms"):
            if self.router is not None and title is not None:
                hits, title_match = self.router.route(title, cfg.routing.top_docs)
                routed = {d for d, _ in hits} or None
        with timed(lat, "retrieve_ms"):
            ranked, mass = self.index.top(scored_text, len(self.chunks) if routed else cfg.retrieval.candidates)
            if routed is not None:
                if cfg.routing.mode == "filter":
                    ranked = [(i, s) for i, s in ranked if self.chunks[i].doc_id in routed]
                else:  # boost
                    ranked = [(i, s * (1 + cfg.routing.boost) if self.chunks[i].doc_id in routed else s) for i, s in ranked]
                    ranked.sort(key=lambda t: (-t[1], t[0]))
            ranked = ranked[: cfg.retrieval.candidates]
        with timed(lat, "rank_ms"):
            cands = []
            for i, s in ranked:
                c = self.chunks[i]
                p = RetrievedPassage(rank=0, doc_id=c.doc_id, start=c.start, end=c.end, text=c.text, score=s,
                                     chunk_id=c.chunk_id, stage_scores={"bm25": s})
                if cfg.ranking.expand_chars:
                    p = expand(p, self.store.text(c.doc_id), cfg.ranking.expand_chars)
                cands.append(p)
            if cfg.ranking.remove_overlaps:
                cands = remove_overlaps(cands)
            cands = assign_ranks(cands)
        cov = self.index.coverage(scored_text, ranked[0][0]) if ranked else 0.0
        conf = confidence(cfg.abstention.signal, cands, mass, cov, title_match)
        return cands, conf, lat

    def search(self, query: str, k: int = 5) -> SearchResponse:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if k < 1:
            raise ValueError("k must be >= 1")
        cands, conf, lat = self.retrieve(query)
        decision, reason = decide(conf, len(cands), self.cfg.abstention.threshold)
        answered = decision == "answered"
        return SearchResponse(
            query=query, decision=decision, abstained=not answered, abstention_reason=reason, confidence=conf,
            threshold=self.cfg.abstention.threshold, passages=cands[:k] if answered else [],
            ranked_candidates=cands, experiment_id=self.experiment_id, config_hash=self.config_hash, latency_ms=lat)
