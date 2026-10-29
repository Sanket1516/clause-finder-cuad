"""Data contracts (see 01_planning/data_contracts.md). Offsets are Python str indices, half-open [start, end)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Decision = Literal["answered", "below_threshold", "no_candidates"]


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)
    chunk_id: str
    doc_id: str
    start: int
    end: int
    text: str  # == document[start:end]  (INV-1)
    index_text: str  # what is tokenised; may differ from text (INV-2) but is never returned to the user
    chunker: str = ""


class RetrievedPassage(BaseModel):
    rank: int
    doc_id: str
    start: int
    end: int
    text: str  # == document[start:end]  (INV-1)
    score: float
    chunk_id: str
    stage_scores: dict[str, float] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """What a user-facing caller receives. `passages` is empty iff the system abstained; `ranked_candidates`
    always keeps the pre-gate ranking (used by the ranking-view evaluation and the UI's 'weak evidence' panel)."""
    query: str
    decision: Decision
    abstained: bool
    abstention_reason: str | None = None
    confidence: float
    threshold: float | None
    passages: list[RetrievedPassage]
    ranked_candidates: list[RetrievedPassage]
    experiment_id: str
    config_hash: str
    latency_ms: dict[str, float] = Field(default_factory=dict)
