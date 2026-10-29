"""New gate signals, router title-match, config cross-check, and the round-2 decision rule."""
import pytest
from fixtures import make_config, make_store

from contract_intel.abstention.gate import confidence
from contract_intel.common.config import ConfigError, config_from_dict
from contract_intel.common.schemas import RetrievedPassage
from contract_intel.experiments.abstention_stage import decide_stage
from contract_intel.pipeline import Pipeline


def P(score):
    return RetrievedPassage(rank=1, doc_id="d", start=0, end=1, text="x", score=score, chunk_id="c")


def test_signal_arithmetic():
    r = [P(4.0), P(1.0)]
    assert confidence("coverage", r, 8.0, coverage=0.25) == 0.25
    assert confidence("title_match", r, 8.0, title_match=0.5) == 0.5
    assert confidence("top1_norm_x_title", r, 8.0, title_match=0.5) == 0.25
    assert confidence("coverage_x_title", r, 8.0, coverage=0.5, title_match=0.5) == 0.25
    assert confidence("title_match", [], 8.0, title_match=0.9) == 0.0, "no candidates -> zero confidence whatever the title says"


def test_title_signals_require_routing():
    with pytest.raises(ConfigError, match="needs routing"):
        config_from_dict({"name": "x", "abstention": {"signal": "title_match"}})
    config_from_dict({"name": "x", "routing": {"mode": "filter"}, "abstention": {"signal": "title_match"}})


def test_title_match_is_high_for_an_indexed_contract_and_low_for_an_unknown_one(tmp_path):
    cfg = make_config(routing={"mode": "filter"}, query={"strip_title_prefix": True}, abstention={"signal": "title_match", "threshold": 0.0})
    pipe = Pipeline(cfg, make_store(tmp_path))
    known = pipe.search("Consider the Marketing Agreement between Alpha Corp and Beta LLC; governing law New York")
    unknown = pipe.search("Consider the Film Deal between Zulu Pictures and Quux Media; governing law New York")
    assert known.confidence > 0.7 and unknown.confidence < known.confidence
    assert unknown.confidence < 0.4


def test_coverage_signal_is_a_fraction(tmp_path):
    pipe = Pipeline(make_config(abstention={"signal": "coverage", "threshold": 0.0}), make_store(tmp_path))
    r = pipe.search("governing laws State of New York")
    assert 0.0 < r.confidence <= 1.0


def _h(**kw):
    base = {"n_unanswerable": 39, "FAR": 0.05, "R@4": 0.4, "P@4": 0.07, "R@1": 0.2}
    base.update(kw)
    return base


def _res(abstained_by_cat):
    recs, i = [], 0
    for cat, flags in abstained_by_cat.items():
        for f in flags:
            recs.append({"query_id": f"u{i:03d}", "answerable": False, "category": cat, "abstained": bool(f)})
            i += 1
    return {"records": recs}


def test_stage_accepts_a_clear_gain_and_rejects_small_or_harmful_ones():
    parent = _res({"a": [0] * 20, "b": [0] * 10})
    better = _res({"a": [1] * 6 + [0] * 14, "b": [1] * 3 + [0] * 7})
    v = decide_stage(_h(), _h(), parent, better, 0.05)
    assert v["decision"] == "accepted" and v["gain_queries"] == 9
    one_more = _res({"a": [1] + [0] * 19, "b": [0] * 10})
    assert decide_stage(_h(), _h(), parent, one_more, 0.05)["decision"] == "rejected"
    # big overall gain but one category loses 2 -> guardrail R2 vetoes
    p2 = _res({"a": [1, 1] + [0] * 18, "b": [0] * 10})
    c2 = _res({"a": [0] * 20, "b": [1] * 10})
    assert decide_stage(_h(), _h(), p2, c2, 0.05)["decision"] == "rejected"
    assert "R2" in decide_stage(_h(), _h(), p2, c2, 0.05)["reason"]


def test_stage_rejects_when_false_abstention_budget_is_exceeded():
    parent = _res({"a": [0] * 20})
    cand = _res({"a": [1] * 10 + [0] * 10})
    assert decide_stage(_h(), _h(FAR=0.2), parent, cand, 0.05)["decision"] == "rejected"


def test_stage_aborts_if_retrieval_changed():
    parent = _res({"a": [0] * 5})
    with pytest.raises(RuntimeError, match="changed retrieval"):
        decide_stage(_h(), _h(**{"R@4": 0.5}), parent, parent, 0.05)
