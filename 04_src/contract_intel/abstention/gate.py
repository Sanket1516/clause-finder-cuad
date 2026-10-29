"""Abstention gate. Three distinct outcomes:
  no_candidates   - the retriever returned nothing (no query term occurs in any chunk)
  below_threshold - candidates exist but the confidence signal is below the threshold
  answered        - confidence >= threshold
An abstention means "no passage cleared the configured evidence threshold". It is NOT a claim that the clause does not exist."""
import math

from ..common.config import AbstentionConfig
from ..common.schemas import Decision, RetrievedPassage


def confidence(signal: str, ranked: list[RetrievedPassage], query_mass: float) -> float:
    if not ranked:
        return 0.0
    top1 = ranked[0].score
    if signal == "top1_score":
        return top1
    if signal == "top1_norm":
        return top1 / query_mass if query_mass > 0 else 0.0
    if signal == "margin_norm":
        second = ranked[1].score if len(ranked) > 1 else 0.0
        return (top1 - second) / query_mass if query_mass > 0 else 0.0
    raise ValueError(f"unknown abstention signal: {signal}")


def decide(conf: float, n_candidates: int, threshold: float | None) -> tuple[Decision, str | None]:
    if n_candidates == 0:
        return "no_candidates", "No indexed passage shares any term with the question."
    if threshold is None:
        raise ValueError("abstention threshold is not set; calibrate it on train data first")
    if conf < threshold:
        return "below_threshold", (f"Best passage scored {conf:.3f}, below the configured evidence threshold "
                                   f"{threshold:.3f}. This does not prove that no such clause exists.")
    return "answered", None


def calibrate_threshold(answerable_confidences: list[float], target_far: float) -> float:
    """Largest threshold whose false-abstention rate on the given ANSWERABLE queries is <= target_far.
    Abstain iff conf < threshold, so threshold = the (m+1)-th smallest confidence with m = floor(target_far * n)."""
    if not answerable_confidences:
        raise ValueError("cannot calibrate without answerable queries")
    c = sorted(answerable_confidences)
    m = math.floor(target_far * len(c) + 1e-9)
    return float(c[min(m, len(c) - 1)])
