"""Evaluator, split guard, diagnosis taxonomy and run artifacts, on a deterministic synthetic corpus."""
import json

import pytest
from fixtures import DOC_A, DOC_B, make_config, make_store

from contract_intel.data.queries import EvalQuery, Gold
from contract_intel.evaluation.diagnose import diagnose_answerable, diagnose_unanswerable
from contract_intel.evaluation.evaluator import evaluate, headline, save_run
from contract_intel.evaluation.guard import SplitGuardError, check_split, record_test_run
from contract_intel.pipeline import Pipeline

LAW = DOC_A.index("2. GOVERNING LAW")
LAW_END = DOC_A.index("3. ASSIGNMENT")
WAR = DOC_B.index("2. WARRANTY")


def queries():
    return [
        EvalQuery("q1", "What is the governing law State of New York", "train", True, (Gold("cuad/A.txt", LAW, LAW_END),), "cuad/A.txt"),
        EvalQuery("q2", "warranty goods twelve months", "train", True, (Gold("cuad/B.txt", WAR, len(DOC_B)),), "cuad/B.txt"),
        EvalQuery("q3", "agreement expires December 2030", "train", True, (Gold("cuad/A.txt", DOC_A.index("1. TERM"), LAW),), "cuad/A.txt"),
        EvalQuery("u1", "helicopter submarine quokka", "train", False, (), None, "out_of_scope"),
        EvalQuery("u2", "zzz qqq nothing", "train", False, (), None, "absent_clause"),
    ]


def pipe(tmp_path, **over):
    return Pipeline(make_config(**over), make_store(tmp_path))


# ---- guard ----
def test_development_purpose_can_never_see_test():
    with pytest.raises(SplitGuardError, match="may not be used for development"):
        check_split("test", "development", confirm_test=True)
    with pytest.raises(SplitGuardError, match="explicit confirmation"):
        check_split("test", "final", confirm_test=False)
    check_split("test", "final", confirm_test=True)
    check_split("train", "development")
    with pytest.raises(SplitGuardError):
        check_split("validation", "development")


def test_evaluate_refuses_test_without_final_and_confirmation(tmp_path):
    p = pipe(tmp_path)
    with pytest.raises(SplitGuardError):
        evaluate(p, "test", "development", queries=queries())
    with pytest.raises(SplitGuardError):
        evaluate(p, "test", "final", confirm_test=False, queries=queries())


def test_improvement_loop_module_does_not_request_test():
    # the loop calls evaluate() with purpose='development' only; this guards the source text
    import pathlib
    loop = pathlib.Path(__file__).resolve().parents[1] / "03_experiments" / "run_improvement_loop.py"
    if loop.exists():
        src = loop.read_text(encoding="utf-8")
        assert '"final"' not in src and "confirm_test=True" not in src and "split=\"test\"" not in src


def test_test_ledger_is_append_only_and_counts_runs(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    assert record_test_run("e1", "h1", "r", "m.json", ledger) == 1
    assert record_test_run("e2", "h2", "r", "m.json", ledger) == 2
    assert [json.loads(l)["run_no"] for l in ledger.read_text().splitlines()] == [1, 2]


def test_test_run_is_ledgered_when_it_starts_and_never_double_counted(tmp_path):
    p = pipe(tmp_path)
    led = tmp_path / "led.jsonl"
    q = EvalQuery("t1", "governing law New York", "test", True, (Gold("cuad/A.txt", LAW, LAW_END),), "cuad/A.txt")
    res = evaluate(p, "test", "final", True, ledger=led, queries=[q])
    assert len(led.read_text().splitlines()) == 1, "counted at evaluation start, even before anything is saved"
    save_run(res, tmp_path / "out", "cmd")
    assert len(led.read_text().splitlines()) == 1, "saving must not double count"
    evaluate(p, "train", queries=queries())
    assert len(led.read_text().splitlines()) == 1, "train evaluations are never ledgered"


# ---- evaluator ----
def test_evaluation_produces_per_query_evidence_and_aggregates(tmp_path):
    p = pipe(tmp_path, abstention={"threshold": None, "target_far": 0.0})
    res = evaluate(p, "train", queries=queries())
    m, recs = res["metrics"], {r["query_id"]: r for r in res["records"]}
    assert m["n_answerable"] == 3 and m["n_unanswerable"] == 2 and m["split"] == "train" and m["purpose"] == "development"
    assert set(recs) == {"q1", "q2", "q3", "u1", "u2"}
    r = recs["q1"]
    for key in ("passages", "gold_for_evaluation_only", "metrics", "label", "decision", "abstained", "experiment_id", "config_hash", "split"):
        assert key in r
    assert r["metrics"]["ranking"]["2"]["recall"] > 0 and r["passages"][0]["doc_id"] == "cuad/A.txt"
    assert m["retrieval_ranking_view"]["4"]["n"] == 3
    # the calibrated threshold is written to the resolved config, not silently applied
    assert res["resolved_config"].abstention.threshold == m["threshold"] is not None
    assert m["offset_integrity_failures"] == 0 and m["abstention"]["n_unanswerable"] == 2


def test_calibration_on_test_is_refused(tmp_path):
    p = pipe(tmp_path, abstention={"threshold": None})
    with pytest.raises(ValueError, match="calibrate"):
        evaluate(p, "test", "final", True, ledger=tmp_path / "led.jsonl", queries=[EvalQuery("t1", "governing law", "test", True, (Gold("cuad/A.txt", LAW, LAW_END),), "cuad/A.txt")])


def test_end_to_end_view_scores_abstained_answerable_queries_as_zero(tmp_path):
    p = pipe(tmp_path, abstention={"threshold": 1e9})
    res = evaluate(p, "train", queries=queries())
    m = res["metrics"]
    assert m["retrieval_ranking_view"]["4"]["recall"] > 0, "ranking view is independent of the gate"
    assert m["retrieval_end_to_end"]["4"]["recall"] == 0.0 and m["abstention"]["false_abstention_rate"] == 1.0
    assert m["abstention"]["correct_abstention_rate"] == 1.0
    assert all(r["e2e_label"] == "false_abstention" for r in res["records"] if r["answerable"])


def test_false_answer_is_visible_and_not_hidden_by_recall(tmp_path):
    p = pipe(tmp_path, abstention={"threshold": 0.0})
    m = evaluate(p, "train", queries=queries())["metrics"]
    assert m["abstention"]["false_answer_rate"] > 0, "unanswerable queries that match something must count as false answers"
    assert m["e2e_label_counts"].get("false_answer", 0) == m["abstention"]["confusion"]["unanswerable_answered_FP"]


def test_gold_is_kept_out_of_the_prediction_inputs(tmp_path):
    p = pipe(tmp_path)
    seen = []
    original = p.retrieve
    p.retrieve = lambda q: (seen.append(q), original(q))[1]
    evaluate(p, "train", queries=queries())
    assert seen == [q.query for q in queries()] and all(isinstance(s, str) for s in seen)


def test_save_run_writes_artifacts_and_refuses_to_overwrite(tmp_path):
    res = evaluate(pipe(tmp_path), "train", queries=queries())
    paths = save_run(res, tmp_path / "run", "python -m contract_intel evaluate --config t")
    preds = [json.loads(l) for l in open(paths["predictions"], encoding="utf-8")]
    assert len(preds) == 5 and json.load(open(paths["metrics"]))["n_queries"] == 5
    info = json.load(open(paths["run_info"]))
    assert info["command"].startswith("python -m contract_intel") and info["config_hash"] == res["metrics"]["config_hash"]
    with pytest.raises(FileExistsError):
        save_run(res, tmp_path / "run", "again")
    save_run(res, tmp_path / "run", "again", overwrite=True)


def test_headline_is_flat_and_complete(tmp_path):
    h = headline(evaluate(pipe(tmp_path), "train", queries=queries())["metrics"])
    for key in ("R@1", "R@2", "R@4", "P@4", "e2e_R@4", "FAR", "CAR", "false_answer_rate", "AUROC", "p95_ms"):
        assert key in h


# ---- diagnosis taxonomy ----
G = [("d1", 1000, 1200)]


@pytest.mark.parametrize("cands,recall,expected", [
    ([("d1", 1000, 1200)], 1.0, "hit"),
    ([("d1", 1000, 1100)], 0.5, "partial_span"),
    ([("d1", 0, 100), ("d1", 200, 300), ("d1", 400, 500), ("d1", 600, 700), ("d1", 1000, 1100)], 0.0, "ranked_too_low"),
    ([("d1", 0, 100)], 0.0, "right_doc_wrong_section"),
    ([("d2", 0, 100), ("d1", 0, 100)], 0.0, "wrong_document"),
    ([], 0.0, "no_candidates"),
])
def test_diagnosis_labels(cands, recall, expected):
    assert diagnose_answerable(cands, G, recall, 4, 5000)["label"] == expected


def test_diagnosis_flags_and_integrity():
    assert diagnose_answerable([("d1", 0, 5)], [("d1", 0, 10)], 0.0, 4, 5000)["flags"] == ["ambiguous_ground_truth"]
    assert diagnose_answerable([("d1", 0, 5)], [("d1", 0, 4000)], 0.0, 4, 5000)["flags"] == ["ambiguous_ground_truth"]
    assert diagnose_answerable([("d1", 0, 5)], G, 1.0, 4, 5000, offsets_ok=False)["label"] == "ingestion_failure"
    assert diagnose_unanswerable(True)["label"] == "correct_abstention" and diagnose_unanswerable(False)["label"] == "false_answer"
    assert diagnose_answerable([("d1", 0, 100), ("d1", 1050, 1060)], G, 0.0, 1, 5000)["found_rank"] == 2
