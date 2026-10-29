"""Selection, split, manifests, unanswerable-set freeze. Data-dependent tests skip if the corpus is not downloaded."""
import copy
import hashlib
import json
import random
from collections import Counter

import pytest
from conftest import RAW, ROOT, jsonl, needs_data

from contract_intel.data.benchmark import load_tests, mini, select_mini_with_ids
from contract_intel.data.splits import assign_split
from contract_intel.data.unanswerable import load_unanswerable

D = ROOT / "02_data"


# ---- pure-logic tests (no data needed) ----
def _fake_tests(n):
    return [{"query": f"q{i}", "snippets": [{"file_path": f"cuad/doc{i % 7}.txt", "span": [0, 1], "answer": "x"}]} for i in range(n)]


def test_mini_returns_everything_when_small():
    t = _fake_tests(10)
    assert mini(t, 194) is t


def test_mini_is_deterministic_and_size_capped():
    t = _fake_tests(500)
    a, b = mini(t), mini(copy.deepcopy(t))
    assert len(a) == 194 and a == b


def test_mini_matches_reference_definition():
    t = _fake_tests(300)

    def ref(tests, n=194):  # transcription of the specified function
        def key(x):
            random.seed(x["snippets"][0]["file_path"])
            return random.random()
        return sorted(tests, key=key)[:n]
    assert mini(t) == ref(t)


def test_assign_split_known_values_and_whitespace_strip():
    q = "Consider the X; What is the governing law for this contract?"
    h = int(hashlib.sha256(q.encode("utf-8")).hexdigest(), 16)
    assert assign_split(q) == ("test" if h % 10 < 3 else "train")
    assert assign_split("  " + q + "\n") == assign_split(q)


def test_assign_split_is_deterministic_and_roughly_30pct():
    qs = [f"query number {i}" for i in range(2000)]
    s = [assign_split(q) for q in qs]
    assert s == [assign_split(q) for q in qs]
    assert 0.25 < s.count("test") / len(s) < 0.35


def test_unanswerable_loader_rejects_missing_fields_dupes_and_bad_category(tmp_path):
    base = {"query_id": "u1", "query": "q", "category": "absent_clause", "target_doc_id": None,
            "rationale": "r", "absence_check": {}, "verification_method": "m"}
    p = tmp_path / "u.jsonl"
    p.write_text(json.dumps({k: v for k, v in base.items() if k != "rationale"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing fields"):
        load_unanswerable(p)
    p.write_text(json.dumps(base) + "\n" + json.dumps(base) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_unanswerable(p)
    p.write_text(json.dumps({**base, "category": "bogus"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bad category"):
        load_unanswerable(p)


def test_lock_mismatch_is_detected(tmp_path):
    p = tmp_path / "u.jsonl"
    p.write_text("{}\n", encoding="utf-8")
    lock = tmp_path / "u.sha256"
    lock.write_text("0" * 64 + "  u.jsonl\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since it was frozen"):
        load_unanswerable(p, lock)


# ---- data-dependent tests ----
@needs_data
def test_selection_is_194_and_repeatable(mini_records):
    assert len(mini_records) == 194
    again = select_mini_with_ids(load_tests(RAW / "benchmarks" / "cuad.json"))
    assert [m["query_id"] for m in again] == [m["query_id"] for m in mini_records]
    assert [m["source_index"] for m in again] == [m["source_index"] for m in mini_records]


@needs_data
def test_selected_queries_keep_original_annotations(mini_records):
    full = load_tests(RAW / "benchmarks" / "cuad.json")
    for m in mini_records:
        assert m["test"] == full[m["source_index"]]  # nothing rewritten


@needs_data
def test_only_referenced_contracts_are_indexed(doc_ids, store):
    on_disk = {p.relative_to(RAW / "corpus").as_posix() for p in (RAW / "corpus").rglob("*.txt")}
    assert on_disk == doc_ids == set(store.doc_ids())
    assert len(doc_ids) == 29


@needs_data
def test_manifests_are_consistent():
    q = jsonl(D / "query_manifest.jsonl")
    g = jsonl(D / "gold_annotations.jsonl")
    ids = [x["query_id"] for x in q]
    assert len(ids) == len(set(ids)), "duplicate query ids"
    assert {x["query_id"] for x in g} == set(ids)
    assert all(set(x) == {"query_id", "query", "split"} for x in q), "query manifest must carry only inference-safe fields"
    assert all(x["split"] == assign_split(x["query"]) for x in q)
    assert sum(1 for x in g if x["answerable"]) == 194
    sm = json.loads((D / "split_manifest.json").read_text(encoding="utf-8"))
    cnt = Counter((x["split"], x["answerable"]) for x in g)
    assert sm["counts"]["train_answerable"] == cnt[("train", True)]
    assert sm["counts"]["test_answerable"] == cnt[("test", True)]
    assert sm["counts"]["train_unanswerable"] == cnt[("train", False)]
    assert sm["counts"]["test_unanswerable"] == cnt[("test", False)]


@needs_data
def test_duplicate_benchmark_queries_share_a_split():
    by = {}
    for x in jsonl(D / "query_manifest.jsonl"):
        by.setdefault(x["query"], set()).add(x["split"])
    assert all(len(v) == 1 for v in by.values())


# ---- frozen-set consistency (works without the corpus) ----
def test_unanswerable_set_is_frozen_and_large_enough():
    rows = load_unanswerable(D / "unanswerable_queries.jsonl", D / "unanswerable_queries.sha256")
    assert len(rows) >= 30
    assert {r["split"] for r in rows} == {"train", "test"}
    assert all(r["split"] == assign_split(r["query"]) for r in rows)
    assert all(r["rationale"] and r["verification_method"] for r in rows)


@needs_data
def test_unanswerable_queries_do_not_collide_with_benchmark_queries():
    q = {x["query"] for x in jsonl(D / "query_manifest.jsonl") if x["query_id"].startswith("cuad-mini")}
    rows = load_unanswerable(D / "unanswerable_queries.jsonl")
    assert not (q & {r["query"] for r in rows})


@needs_data
def test_unanswerable_absence_checks_still_hold():
    import importlib.util
    spec = importlib.util.spec_from_file_location("vu", D / "validate_unanswerable.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.check()["absence_check_failures"] == []
