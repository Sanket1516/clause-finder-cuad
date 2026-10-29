"""Chunk provenance, offset reconstruction, stable ranking, empty candidates, config validation, abstention,
serialization, inference isolation."""
import inspect
import random
from pathlib import Path

import pytest
from fixtures import DOC_A, make_config, make_store

from contract_intel.abstention.gate import calibrate_threshold, confidence, decide
from contract_intel.chunking import chunk_document
from contract_intel.common.config import ConfigError, config_from_dict, config_hash, load_config
from contract_intel.common.schemas import SearchResponse
from contract_intel.pipeline import Pipeline
from contract_intel.ranking.postprocess import remove_overlaps

SRC = Path(__file__).resolve().parents[1] / "04_src" / "contract_intel"


# ---- chunking / provenance / offsets ----
@pytest.mark.parametrize("strategy", ["fixed", "paragraph", "clause"])
@pytest.mark.parametrize("size", [60, 100, 500])
def test_every_chunk_reconstructs_from_original_offsets(strategy, size):
    cfg = config_from_dict({"name": "t", "chunking": {"strategy": strategy, "size_chars": size}}).chunking
    for text in (DOC_A, "a" * 1000, "word " * 300, "\n\n\n", "", "ARTICLE I\nSection 1.1 Foo bar.\n" * 20):
        chunks = chunk_document("cuad/x.txt", text, cfg)
        for c in chunks:
            assert text[c.start:c.end] == c.text and c.doc_id == "cuad/x.txt" and 0 <= c.start < c.end <= len(text)
            assert len(c.text) <= size or strategy == "fixed"  # packers never exceed the size


def test_fixed_chunks_with_overlap_cover_the_document():
    cfg = config_from_dict({"name": "t", "chunking": {"strategy": "fixed", "size_chars": 100, "overlap_chars": 20}}).chunking
    text = "".join(chr(97 + i % 26) for i in range(350))
    chunks = chunk_document("d", text, cfg)
    assert chunks[0].start == 0 and chunks[-1].end == len(text)
    assert all(b.start == a.start + 80 for a, b in zip(chunks, chunks[1:]))


def test_long_unbroken_text_is_split_not_lost():
    cfg = config_from_dict({"name": "t", "chunking": {"strategy": "paragraph", "size_chars": 100}}).chunking
    text = "Sentence one is here. " * 40
    chunks = chunk_document("d", text, cfg)
    assert len(chunks) > 5 and all(len(c.text) <= 100 for c in chunks)
    assert all(a.end <= b.start for a, b in zip(chunks, chunks[1:])), "packed chunks must not overlap"
    assert "".join(c.text for c in chunks).replace(" ", "") == text.replace(" ", "")  # only whitespace may be dropped


def test_pipeline_chunks_carry_document_ids_and_exact_offsets(tmp_path):
    store = make_store(tmp_path)
    pipe = Pipeline(make_config(), store)
    assert {c.doc_id for c in pipe.chunks} == set(store.doc_ids())
    assert all(store.text(c.doc_id)[c.start:c.end] == c.text for c in pipe.chunks)
    assert [c.chunk_id for c in pipe.chunks] == [f"{c.doc_id}::{c.start}-{c.end}" for c in pipe.chunks]


# ---- retrieval / ranking ----
def test_search_returns_ranked_passages_with_provenance(tmp_path):
    store = make_store(tmp_path)
    r = Pipeline(make_config(), store).search("governing laws State of New York", k=3)
    assert r.decision == "answered" and not r.abstained and 1 <= len(r.passages) <= 3
    assert [p.rank for p in r.passages] == list(range(1, len(r.passages) + 1))
    assert all(r.passages[i].score >= r.passages[i + 1].score for i in range(len(r.passages) - 1))
    top = r.passages[0]
    assert top.doc_id == "cuad/A.txt" and "New York" in top.text
    assert store.text(top.doc_id)[top.start:top.end] == top.text
    assert r.experiment_id.startswith("test-") and len(r.config_hash) == 64


def test_ranking_is_deterministic_and_ties_break_by_position(tmp_path):
    d = tmp_path / "corpus" / "cuad"
    d.mkdir(parents=True)
    (d / "T.txt").write_text(("alpha beta gamma delta " * 5 + "\n\n") * 6, encoding="utf-8")
    from contract_intel.data.corpus import DocumentStore
    store = DocumentStore(tmp_path / "corpus", ["cuad/T.txt"])
    cfg = make_config(chunking={"strategy": "paragraph", "size_chars": 130, "overlap_chars": 0})
    runs = [[(p.start, p.score) for p in Pipeline(cfg, store).search("alpha gamma", 6).ranked_candidates] for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]
    starts = [s for s, _ in runs[0]]
    assert starts == sorted(starts), "equal scores must be ordered by document position"


def test_empty_candidate_set_is_reported_distinctly(tmp_path):
    r = Pipeline(make_config(), make_store(tmp_path)).search("qqqqq zzzzz")
    assert r.decision == "no_candidates" and r.abstained and r.passages == [] and r.ranked_candidates == []
    assert r.confidence == 0.0 and "shares any term" in r.abstention_reason


def test_overlapping_passages_are_removed_keeping_best(tmp_path):
    store = make_store(tmp_path)
    cfg = make_config(chunking={"strategy": "fixed", "size_chars": 100, "overlap_chars": 50})
    r = Pipeline(cfg, store).search("agreement assign consent", k=10)
    by_doc = {}
    for p in r.ranked_candidates:
        for s, e in by_doc.get(p.doc_id, []):
            assert not (p.start < e and s < p.end), "overlap survived"
        by_doc.setdefault(p.doc_id, []).append((p.start, p.end))
    assert remove_overlaps(r.ranked_candidates) == r.ranked_candidates


# ---- abstention ----
def test_three_distinct_abstention_outcomes():
    from contract_intel.common.schemas import RetrievedPassage
    assert decide(0.0, 0, 1.0)[0] == "no_candidates"
    d, reason = decide(0.5, 3, 1.0)
    assert d == "below_threshold" and "does not prove" in reason
    assert decide(1.5, 3, 1.0) == ("answered", None)
    assert decide(1.0, 3, 1.0)[0] == "answered"  # boundary: conf == threshold is answered
    with pytest.raises(ValueError, match="calibrate"):
        decide(1.0, 3, None)
    p = [RetrievedPassage(rank=1, doc_id="d", start=0, end=1, text="x", score=4.0, chunk_id="c"),
         RetrievedPassage(rank=2, doc_id="d", start=1, end=2, text="y", score=1.0, chunk_id="c2")]
    assert confidence("top1_score", p, 8.0) == 4.0 and confidence("top1_norm", p, 8.0) == 0.5
    assert confidence("margin_norm", p, 8.0) == 3.0 / 8.0 and confidence("top1_score", [], 1.0) == 0.0


def test_abstaining_response_keeps_no_passages_but_keeps_candidates(tmp_path):
    cfg = make_config(abstention={"threshold": 1e9})
    r = Pipeline(cfg, make_store(tmp_path)).search("governing law New York")
    assert r.decision == "below_threshold" and r.abstained and r.passages == [] and len(r.ranked_candidates) > 0
    assert r.threshold == 1e9


def test_calibration_hits_target_false_abstention_rate():
    conf = [float(i) for i in range(100)]
    tau = calibrate_threshold(conf, 0.05)
    assert sum(c < tau for c in conf) / 100 <= 0.05 and tau == 5.0
    assert calibrate_threshold(conf, 0.0) == 0.0
    with pytest.raises(ValueError):
        calibrate_threshold([], 0.05)


# ---- configuration ----
@pytest.mark.parametrize("bad", [
    {"chunking": {"size_chars": 100, "overlap_chars": 100}},
    {"chunking": {"strategy": "magic"}},
    {"retrieval": {"candidates": 0}},
    {"retrieval": {"bm25": {"b": 1.5}}},
    {"evaluation": {"ks": [1, 2], "primary_k": 4}},
    {"unknown_key": 1},
    {"chunking": {"size_chars": 500, "typo_field": 1}},
])
def test_invalid_configuration_is_rejected(bad):
    with pytest.raises(ConfigError):
        config_from_dict({"name": "bad", **bad})


def test_config_extends_and_hash_ignores_labels(tmp_path):
    (tmp_path / "base.yaml").write_text("name: base\nchunking: {size_chars: 300}\nretrieval: {candidates: 50}\n", encoding="utf-8")
    (tmp_path / "child.yaml").write_text("extends: base.yaml\nname: child\nchunking: {size_chars: 400}\n", encoding="utf-8")
    c = load_config(tmp_path / "child.yaml")
    assert c.chunking.size_chars == 400 and c.retrieval.candidates == 50
    assert config_hash(c) == config_hash(config_from_dict({**c.model_dump(mode="json"), "name": "other", "description": "x"}))
    assert config_hash(c) != config_hash(load_config(tmp_path / "base.yaml"))


def test_missing_and_malformed_config_files(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")
    (tmp_path / "bad.yaml").write_text("name: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(tmp_path / "bad.yaml")
    (tmp_path / "loop.yaml").write_text("extends: loop.yaml\nname: x\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="circular"):
        load_config(tmp_path / "loop.yaml")


def test_pipeline_rejects_bad_queries(tmp_path):
    pipe = Pipeline(make_config(), make_store(tmp_path))
    for bad in ("", "   ", None):
        with pytest.raises(ValueError):
            pipe.search(bad)
    with pytest.raises(ValueError):
        pipe.search("law", k=0)


# ---- serialization ----
def test_search_response_round_trips_through_json(tmp_path):
    r = Pipeline(make_config(), make_store(tmp_path)).search("warranty goods twelve months", 2)
    back = SearchResponse.model_validate_json(r.model_dump_json())
    assert back == r and back.passages[0].doc_id == r.passages[0].doc_id


# ---- inference isolation ----
def test_search_takes_only_the_question_text():
    params = list(inspect.signature(Pipeline.search).parameters)
    assert params == ["self", "query", "k"]
    assert list(inspect.signature(Pipeline.retrieve).parameters) == ["self", "query"]


def test_inference_modules_never_reference_gold_annotations():
    forbidden = ("gold", "snippets", "EvalQuery", "gold_annotations", "queries import", "split_manifest")
    for rel in ("pipeline.py", "retrieval/lexical.py", "retrieval/router.py", "ranking/postprocess.py",
                "abstention/gate.py", "chunking/__init__.py", "application/service.py"):
        src = (SRC / rel).read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in src.replace("queries import ROOT", ""), f"{rel} mentions {word!r}"


def test_results_do_not_depend_on_anything_but_the_query(tmp_path):
    pipe = Pipeline(make_config(), make_store(tmp_path))
    q = "assign this agreement written consent"
    a = [(p.doc_id, p.start, p.end, p.score) for p in pipe.search(q).passages]
    random.seed(123)
    b = [(p.doc_id, p.start, p.end, p.score) for p in pipe.search(q).passages]
    assert a == b
