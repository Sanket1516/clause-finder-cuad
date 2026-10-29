"""Metrics. Pure functions, independently testable.

CHARACTER-LEVEL RETRIEVAL METRICS (LegalBench-RAG definition, as implemented in the authors' run_benchmark.py)
  Ground truth G : the query's gold spans (document, [start,end)); all in one document, pairwise disjoint.
  Prediction  R_k: the top-k returned passages (document, [start,end)).
  overlap        : characters of R_k that lie inside a gold span of the SAME document.
  precision@k    = overlap / (total characters returned, in ANY document)   -> wrong-document text counts against precision
  recall@k       = overlap / (total gold characters)                        -> multiple gold spans are pooled, not averaged
  Zero denominators: nothing returned -> precision 0 (authors' convention); no gold characters -> recall 0 (never occurs here).
  Overlapping/repeated predictions: the authors' code sums lengths and would double-count them. We take the UNION of
  returned characters per document first (dedupe=True), which is identical to the authors' value when passages do not
  overlap (the pipeline guarantees that) and cannot be inflated by overlap otherwise.
  Aggregation: unweighted mean over queries (macro). The paper additionally averages four sources with equal weight; we have one.

ABSTENTION METRICS are decision-level and are NOT character-level metrics (see abstention_metrics)."""
from collections import defaultdict

Interval = tuple[str, int, int]  # (doc_id, start, end)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _by_doc(items: list[Interval], dedupe: bool) -> dict[str, list[tuple[int, int]]]:
    d: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for doc, s, e in items:
        if e > s:
            d[doc].append((s, e))
    return {k: (_merge(v) if dedupe else sorted(v)) for k, v in d.items()}


def char_precision_recall(returned: list[Interval], gold: list[Interval], dedupe: bool = True) -> dict:
    ret, gld = _by_doc(returned, dedupe), _by_doc(gold, True)
    n_ret = sum(e - s for v in ret.values() for s, e in v)
    n_gold = sum(e - s for v in gld.values() for s, e in v)
    overlap = 0
    for doc, rs in ret.items():
        for rs_, re_ in rs:
            for gs, ge in gld.get(doc, []):
                lo, hi = max(rs_, gs), min(re_, ge)
                if hi > lo:
                    overlap += hi - lo
    return {
        "precision": overlap / n_ret if n_ret else 0.0,
        "recall": overlap / n_gold if n_gold else 0.0,
        "n_returned_chars": n_ret, "n_gold_chars": n_gold, "n_overlap_chars": overlap,
    }


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def aggregate_retrieval(per_query: list[dict], ks: list[int], view: str) -> dict:
    """per_query rows carry `metrics[view][str(k)] = {precision, recall, ...}`; macro-average over the rows given."""
    out = {}
    for k in ks:
        rows = [r["metrics"][view][str(k)] for r in per_query]
        out[str(k)] = {"precision": mean([r["precision"] for r in rows]), "recall": mean([r["recall"] for r in rows]), "n": len(rows)}
    return out


def abstention_metrics(rows: list[dict]) -> dict:
    """rows: {answerable: bool, abstained: bool}. 'Positive' for the answer-decision is 'system answers'."""
    tp = sum(1 for r in rows if r["answerable"] and not r["abstained"])   # answered an answerable query
    fn = sum(1 for r in rows if r["answerable"] and r["abstained"])       # FALSE ABSTENTION
    fp = sum(1 for r in rows if not r["answerable"] and not r["abstained"])  # FALSE ANSWER
    tn = sum(1 for r in rows if not r["answerable"] and r["abstained"])   # CORRECT ABSTENTION
    n_ans, n_un = tp + fn, fp + tn

    def div(a, b):
        return a / b if b else float("nan")

    ans_p, ans_r = div(tp, tp + fp), div(tp, tp + fn)
    abs_p, abs_r = div(tn, tn + fn), div(tn, tn + fp)

    def f1(p, r):
        return 2 * p * r / (p + r) if p == p and r == r and (p + r) > 0 else float("nan")

    return {
        "confusion": {"answerable_answered_TP": tp, "answerable_abstained_FN": fn,
                      "unanswerable_answered_FP": fp, "unanswerable_abstained_TN": tn},
        "n_answerable": n_ans, "n_unanswerable": n_un,
        "false_abstention_rate": div(fn, n_ans),       # answerable queries wrongly given nothing / answerable queries
        "correct_abstention_rate": div(tn, n_un),      # unanswerable queries correctly given nothing / unanswerable queries
        "false_answer_rate": div(fp, n_un),            # unanswerable queries that still got passages / unanswerable queries
        "answer_decision": {"precision": ans_p, "recall": ans_r, "f1": f1(ans_p, ans_r)},
        "abstain_decision": {"precision": abs_p, "recall": abs_r, "f1": f1(abs_p, abs_r)},
    }


def auroc(pos: list[float], neg: list[float]) -> float:
    """P(score_pos > score_neg) + 0.5 P(tie): how well the confidence signal separates answerable (pos) from unanswerable (neg)."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))
