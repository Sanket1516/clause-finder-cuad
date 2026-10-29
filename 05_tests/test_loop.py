"""Acceptance rule, proposer and the restartable loop (on a small synthetic corpus, train-only)."""
import json
from collections import Counter

import pytest
import yaml
from fixtures import DOC_A, DOC_B, make_config, make_store

from contract_intel.common.config import dump_config
from contract_intel.data.queries import EvalQuery, Gold
from contract_intel.experiments import acceptance as acc
from contract_intel.experiments.loop import run_loop
from contract_intel.experiments.proposer import label_counts, load_catalogue, propose


def H(**kw):
    base = {"R@4": 0.20, "P@4": 0.10, "R@1": 0.10, "CAR": 0.50, "p95_ms": 10.0, "build_s": 1.0}
    base.update(kw)
    return base


# ---- acceptance rule ----
def test_bootstrap_is_deterministic_and_detects_a_real_gain():
    a, b = [0.0] * 50 + [0.5] * 50, [0.2] * 50 + [0.5] * 50
    r1, r2 = acc.paired_bootstrap(a, b), acc.paired_bootstrap(a, b)
    assert r1 == r2 and r1["p_gain"] == 1.0 and r1["ci95"][0] > 0
    assert acc.paired_bootstrap(a, a)["p_gain"] == 0.0
    with pytest.raises(ValueError):
        acc.paired_bootstrap([1.0], [1.0, 2.0])


def test_accept_requires_min_gain_and_confidence():
    parent = [0.0] * 100
    cand = [0.3] * 40 + [0.0] * 60
    d = acc.decide(H(), H(**{"R@4": 0.32}), parent, cand, 4, 39)
    assert d["decision"] == "accepted"


def test_small_gain_is_rejected_and_unconvincing_gain_is_inconclusive():
    assert acc.decide(H(), H(**{"R@4": 0.205}), [0.0] * 10, [0.005] * 10, 4, 39)["decision"] == "rejected"
    noisy_parent = [0.0] * 98 + [1.0, 0.0]
    noisy_cand = [0.0] * 98 + [0.0, 1.0]
    cand_better = [0.0] * 99 + [1.0]
    d = acc.decide(H(), H(**{"R@4": 0.22}), noisy_parent, cand_better, 4, 39)
    assert d["decision"] in ("inconclusive", "rejected") and d["decision"] != "accepted" or d["bootstrap"]["p_gain"] >= 0.9
    assert acc.decide(H(), H(**{"R@4": 0.22}), [0.3, 0.1] * 5, [0.1, 0.3] * 5, 4, 39)["decision"] == "inconclusive"


@pytest.mark.parametrize("override,guard", [
    ({"P@4": 0.05}, "G1_precision"), ({"CAR": 0.40}, "G2_correct_abstention"), ({"R@1": 0.05}, "G3_recall_at_1"),
    ({"p95_ms": 5000.0}, "G4_p95_latency_ms"), ({"build_s": 5000.0}, "G5_build_seconds")])
def test_each_guardrail_vetoes_even_a_big_gain(override, guard):
    d = acc.decide(H(), H(**{"R@4": 0.9, **override}), [0.0] * 20, [0.9] * 20, 4, 39)
    assert d["decision"] == "rejected" and guard in d["reason"] and not d["guardrails"][guard]["pass"]


def test_one_query_of_correct_abstention_may_be_lost_but_not_two():
    one = acc.guardrails(H(CAR=0.50), H(CAR=0.50 - 1 / 39), 4, 39)["G2_correct_abstention"]
    two = acc.guardrails(H(CAR=0.50), H(CAR=0.50 - 2 / 39), 4, 39)["G2_correct_abstention"]
    assert one["pass"] and not two["pass"]


# ---- proposer ----
def test_proposer_follows_the_dominant_failure_label_and_skips_tried(tmp_path):
    cat = [{"id": "a", "targets": ["wrong_document"], "hypothesis": "h", "overrides": {"query": {"strip_title_prefix": True}}},
           {"id": "b", "targets": ["partial_span"], "hypothesis": "h", "overrides": {"chunking": {"size_chars": 300}}}]
    parent = make_config()
    e, cand, why = propose(cat, Counter({"partial_span": 5, "wrong_document": 2}), parent, set(), set(), 0)
    assert e["id"] == "b" and cand.chunking.size_chars == 300 and "partial_span" in why
    e2, _, _ = propose(cat, Counter({"partial_span": 5, "wrong_document": 2}), parent, {"b"}, set(), 1)
    assert e2["id"] == "a"
    assert propose(cat, Counter({"partial_span": 5}), parent, {"a", "b"}, set(), 2) is None


def test_proposer_never_repeats_an_identical_configuration():
    parent = make_config(chunking={"size_chars": 300})
    cat = [{"id": "same", "targets": ["partial_span"], "hypothesis": "h", "overrides": {"chunking": {"size_chars": 300}}}]
    from contract_intel.common.config import config_hash
    assert propose(cat, Counter({"partial_span": 1}), parent, set(), {config_hash(parent)}, 0) is None


def test_the_real_catalogue_is_valid():
    from pathlib import Path
    cat = load_catalogue(Path(__file__).resolve().parents[1] / "03_experiments" / "proposals" / "catalogue.yaml")
    assert len(cat) >= 5 and all({"id", "targets", "hypothesis", "overrides"} <= set(e) for e in cat)


# ---- the loop on a fixture corpus ----
LAW, LAW_E = DOC_A.index("2. GOVERNING LAW"), DOC_A.index("3. ASSIGNMENT")


def train_queries():
    qs = []
    for i, (q, d, s, e) in enumerate([
        ("Consider the Marketing Agreement between Alpha Corp and Beta LLC; What is the governing law?", "A", LAW, LAW_E),
        ("Consider the Marketing Agreement between Alpha Corp and Beta LLC; Is there an assignment clause?", "A", DOC_A.index("3. ASSIGNMENT"), len(DOC_A)),
        ("Consider the Supply Agreement between Gamma Inc and Delta Ltd; What warranty applies?", "B", DOC_B.index("2. WARRANTY"), len(DOC_B)),
        ("Consider the Marketing Agreement between Alpha Corp and Beta LLC; When does it expire?", "A", DOC_A.index("1. TERM"), LAW)]):
        qs.append(EvalQuery(f"q{i}", q, "train", True, (Gold(f"cuad/{d}.txt", s, e),), f"cuad/{d}.txt"))
    qs.append(EvalQuery("u0", "Consider the Film Deal between Foo and Bar; Who owns the sequel rights?", "train", False, (), None, "not_in_corpus"))
    qs.append(EvalQuery("u1", "Consider the Supply Agreement between Gamma Inc and Delta Ltd; Is there arbitration?", "train", False, (), None, "absent_clause"))
    return qs


def _setup(tmp_path):
    root = tmp_path / "repo"
    (root / "03_experiments").mkdir(parents=True)
    base = make_config(name="baseline", abstention={"threshold": None, "target_far": 0.0})
    dump_config(base, root / "03_experiments" / "base.yaml")
    cat = {"entries": [
        {"id": "strip-title", "targets": ["right_doc_wrong_section", "ranked_too_low", "wrong_document", "partial_span", "no_candidates"],
         "hypothesis": "strip the title", "overrides": {"query": {"strip_title_prefix": True}}},
        {"id": "stop", "targets": ["right_doc_wrong_section", "ranked_too_low", "wrong_document", "partial_span", "no_candidates"],
         "hypothesis": "drop stopwords", "overrides": {"retrieval": {"bm25": {"tokenizer": {"stopwords": "english"}}}}},
        {"id": "chunk-200", "targets": ["right_doc_wrong_section", "ranked_too_low", "wrong_document", "partial_span", "no_candidates"],
         "hypothesis": "bigger chunks", "overrides": {"chunking": {"size_chars": 200}}}]}
    (root / "03_experiments" / "cat.yaml").write_text(yaml.safe_dump(cat), encoding="utf-8")
    return root


def test_loop_logs_every_iteration_is_restartable_and_train_only(tmp_path):
    root, store = _setup(tmp_path), make_store(tmp_path)
    args = dict(root=root, baseline_config=root / "03_experiments" / "base.yaml", catalogue_path=root / "03_experiments" / "cat.yaml",
                command="pytest", store=store, queries=train_queries())
    run_loop(max_iterations=2, **args)
    log = [json.loads(l) for l in (root / "03_experiments" / "experiment_log.jsonl").read_text().splitlines()]
    assert [e["iteration"] for e in log] == [0, 1, 2] and log[0]["decision"] == "baseline"
    assert all(e["split"] == "train" and e["purpose"] == "development" for e in log)
    for e in log[1:]:
        assert e["decision"] in ("accepted", "rejected", "inconclusive") and e["decision_reason"] and e["proposer"].startswith("rule:")
        assert e["hypothesis"] and e["diff"] and e["guardrails"] and e["bootstrap"]["B"] == 2000
    # restart: continues with the remaining catalogue entry, keeps the earlier log lines untouched
    before = (root / "03_experiments" / "experiment_log.jsonl").read_text()
    out = run_loop(max_iterations=10, **args)
    after = (root / "03_experiments" / "experiment_log.jsonl").read_text()
    assert after.startswith(before) and len(after.splitlines()) == 4 and out["n_iterations_beyond_baseline"] == 3
    again = run_loop(max_iterations=10, **args)  # nothing left -> no new lines
    assert (root / "03_experiments" / "experiment_log.jsonl").read_text() == after and again["n_iterations_beyond_baseline"] == 3
    assert (root / "03_experiments" / "configs" / "final.yaml").exists() and (root / "06_results" / "improvement_history.csv").exists()
    assert json.loads((root / "06_results" / "train_comparison.json").read_text())["split"] == "train"
    # accepted parent chain is consistent
    parent = log[0]["experiment_id"]
    for e in json.loads(json.dumps([json.loads(l) for l in after.splitlines()]))[1:]:
        assert e["parent_experiment_id"] == parent
        if e["decision"] == "accepted":
            parent = e["experiment_id"]


def test_loop_rejects_non_train_queries(tmp_path):
    root, store = _setup(tmp_path), make_store(tmp_path)
    bad = train_queries() + [EvalQuery("t0", "q", "test", True, (Gold("cuad/A.txt", 0, 5),), "cuad/A.txt")]
    with pytest.raises(ValueError, match="only accepts train"):
        run_loop(root, root / "03_experiments" / "base.yaml", root / "03_experiments" / "cat.yaml", 1, "x", store=store, queries=bad)


def test_label_counts_ignore_hits_and_unanswerables():
    recs = [{"answerable": True, "label": "hit"}, {"answerable": True, "label": "partial_span"},
            {"answerable": False, "label": "false_answer"}, {"answerable": True, "label": "partial_span"}]
    assert label_counts(recs) == Counter({"partial_span": 2})
