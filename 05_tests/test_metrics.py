"""Metric correctness against hand-calculated examples, edge cases and a port of the authors' reference formula."""
import math

import pytest

from contract_intel.evaluation.metrics import (abstention_metrics, auroc, char_precision_recall, mean)

A, B = "cuad/A.txt", "cuad/B.txt"


def pr(returned, gold, **kw):
    return char_precision_recall(returned, gold, **kw)


def test_perfect_retrieval():
    r = pr([(A, 100, 200)], [(A, 100, 200)])
    assert r["precision"] == 1.0 and r["recall"] == 1.0


def test_returned_passage_contains_gold_and_more():
    # gold 100 chars, returned 400 chars containing it -> P = 100/400, R = 1
    r = pr([(A, 0, 400)], [(A, 150, 250)])
    assert r["precision"] == 0.25 and r["recall"] == 1.0 and r["n_overlap_chars"] == 100


def test_partial_cover():
    r = pr([(A, 0, 50)], [(A, 0, 100)])
    assert r["precision"] == 1.0 and r["recall"] == 0.5


def test_wrong_document_characters_count_against_precision_only():
    r = pr([(A, 0, 50), (B, 0, 50)], [(A, 0, 100)])
    assert r["precision"] == 0.5 and r["recall"] == 0.5


def test_same_offsets_in_wrong_document_score_zero():
    r = pr([(B, 0, 100)], [(A, 0, 100)])
    assert r["precision"] == 0.0 and r["recall"] == 0.0


def test_multiple_gold_spans_are_pooled():
    gold = [(A, 0, 100), (A, 500, 800)]  # 400 gold chars
    r = pr([(A, 0, 100), (A, 500, 600)], gold)
    assert r["recall"] == 200 / 400 and r["precision"] == 1.0 and r["n_gold_chars"] == 400


def test_nothing_returned_scores_zero_not_nan():
    r = pr([], [(A, 0, 100)])
    assert r["precision"] == 0.0 and r["recall"] == 0.0 and r["n_returned_chars"] == 0


def test_no_gold_characters_gives_zero_recall_without_dividing_by_zero():
    assert pr([(A, 0, 10)], [])["recall"] == 0.0


def test_empty_and_inverted_intervals_are_ignored():
    r = pr([(A, 10, 10), (A, 30, 20), (A, 0, 100)], [(A, 0, 100)])
    assert r["precision"] == 1.0 and r["n_returned_chars"] == 100


def test_repeated_and_overlapping_predictions_cannot_inflate_scores():
    r = pr([(A, 0, 100), (A, 0, 100), (A, 50, 150)], [(A, 0, 100)])
    assert r["n_returned_chars"] == 150 and r["recall"] == 1.0 and r["precision"] == 100 / 150
    naive = pr([(A, 0, 100), (A, 0, 100), (A, 50, 150)], [(A, 0, 100)], dedupe=False)
    assert naive["n_returned_chars"] == 300  # the authors' raw formula double counts; we avoid that


def _authors_formula(returned, gold):
    """Direct port of QAResult.precision/recall from the authors' run_benchmark.py (assumes non-overlapping returns)."""
    tot = rel = 0
    for d, s, e in returned:
        tot += e - s
        for gd, gs, ge in gold:
            if d == gd and min(e, ge) > max(s, gs):
                rel += min(e, ge) - max(s, gs)
    p = rel / tot if tot else 0
    tg = sum(e - s for _, s, e in gold)
    rr = 0
    for gd, gs, ge in gold:
        for d, s, e in returned:
            if d == gd and min(e, ge) > max(s, gs):
                rr += min(e, ge) - max(s, gs)
    return p, (rr / tg if tg else 0)


@pytest.mark.parametrize("returned,gold", [
    ([(A, 0, 500), (A, 500, 1000), (B, 0, 500)], [(A, 400, 700), (A, 900, 1100)]),
    ([(A, 10, 20)], [(A, 0, 100)]),
    ([(B, 0, 5)], [(A, 0, 5)]),
    ([(A, 0, 300), (A, 300, 600), (A, 600, 900)], [(A, 250, 350), (A, 590, 610)]),
])
def test_matches_authors_reference_formula_on_non_overlapping_returns(returned, gold):
    ours = pr(returned, gold)
    p, r = _authors_formula(returned, gold)
    assert math.isclose(ours["precision"], p) and math.isclose(ours["recall"], r)


def test_recall_is_monotone_in_k_for_a_fixed_ranking():
    ranking = [(A, 0, 100), (B, 0, 100), (A, 200, 300), (A, 400, 500)]
    gold = [(A, 200, 300), (A, 400, 450)]
    recalls = [pr(ranking[:k], gold)["recall"] for k in (1, 2, 3, 4)]
    assert recalls == sorted(recalls) and recalls[-1] == 150 / 150


def test_mean_handles_empty():
    assert mean([1, 2, 3]) == 2 and math.isnan(mean([]))


# ---- abstention ----
def rows(spec):
    return [{"answerable": a, "abstained": b} for a, b, n in spec for _ in range(n)]


def test_abstention_metrics_hand_counts():
    # 10 answerable: 8 answered, 2 wrongly abstained. 5 unanswerable: 3 correctly abstained, 2 falsely answered.
    m = abstention_metrics(rows([(True, False, 8), (True, True, 2), (False, True, 3), (False, False, 2)]))
    assert m["confusion"] == {"answerable_answered_TP": 8, "answerable_abstained_FN": 2,
                              "unanswerable_answered_FP": 2, "unanswerable_abstained_TN": 3}
    assert m["false_abstention_rate"] == 0.2 and m["correct_abstention_rate"] == 0.6 and m["false_answer_rate"] == 0.4
    assert m["answer_decision"]["precision"] == 8 / 10 and m["answer_decision"]["recall"] == 8 / 10
    assert math.isclose(m["answer_decision"]["f1"], 0.8)
    assert m["abstain_decision"]["precision"] == 3 / 5 and m["abstain_decision"]["recall"] == 3 / 5


def test_abstention_metrics_empty_denominators_are_nan_not_errors():
    m = abstention_metrics(rows([(True, False, 4)]))
    assert m["false_abstention_rate"] == 0.0 and math.isnan(m["correct_abstention_rate"]) and m["n_unanswerable"] == 0


def test_auroc_cases():
    assert auroc([3, 4], [1, 2]) == 1.0 and auroc([1, 2], [3, 4]) == 0.0 and auroc([1], [1]) == 0.5
    assert math.isnan(auroc([], [1]))
