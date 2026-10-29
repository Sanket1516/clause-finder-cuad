"""Shared application layer + web request handling: answerable/unanswerable, malformed input, missing data, offsets."""
from pathlib import Path

import pytest
from fixtures import DOC_A, make_app_env

from contract_intel.application import (ApplicationError, ConfigNotCalibrated, InvalidQuery, SearchService, list_configs,
                                        resolve_config_path)
from contract_intel.common.config import ConfigError
from contract_intel.interfaces.webapp import DISCLAIMER, run_search

ROOT = Path(__file__).resolve().parents[1]
Q_LAW = "Consider the Marketing Agreement between Alpha Corp and Beta LLC; What is the governing law?"


@pytest.fixture
def env(tmp_path, monkeypatch):
    return make_app_env(tmp_path, monkeypatch)


def test_answerable_question_returns_traceable_passages(env):
    svc = SearchService("final")
    r = svc.search(Q_LAW, 3)
    assert not r.abstained and 1 <= len(r.passages) <= 3
    top = r.passages[0]
    assert top.doc_id == "cuad/A.txt" and "New York" in top.text and (top.start, top.end) == (DOC_A.index(top.text), DOC_A.index(top.text) + len(top.text))
    for p in r.passages + r.ranked_candidates:
        assert svc.store.text(p.doc_id)[p.start:p.end] == p.text


def test_abstention_returns_no_passages_and_an_honest_reason(env):
    r = SearchService("strict").search(Q_LAW)
    assert r.abstained and r.passages == [] and r.decision == "below_threshold"
    assert "does not prove" in r.abstention_reason and len(r.ranked_candidates) > 0


def test_question_sharing_no_terms_with_the_corpus_abstains_as_no_candidates(env):
    r = SearchService("final").search("qqqq zzzz wwww")
    assert r.decision == "no_candidates" and r.passages == []


@pytest.mark.parametrize("bad", ["", "   ", "\n\t", None, 123])
def test_empty_and_malformed_questions_are_rejected(env, bad):
    with pytest.raises(InvalidQuery):
        SearchService("final").search(bad)


@pytest.mark.parametrize("k", [0, -1, 65, 2.5, "3", True, None])
def test_invalid_result_counts_are_rejected(env, k):
    with pytest.raises(InvalidQuery):
        SearchService("final").search(Q_LAW, k)


def test_overlong_question_is_rejected(env):
    with pytest.raises(InvalidQuery, match="too long"):
        SearchService("final").search("law " * 1000)


def test_whitespace_in_questions_is_normalised(env):
    svc = SearchService("final")
    assert svc.search("  governing   law\n New York ").query == "governing law New York"


def test_unknown_and_uncalibrated_configurations(env):
    with pytest.raises(ConfigError, match="unknown configuration"):
        SearchService("nope")
    with pytest.raises(ConfigNotCalibrated, match="calibrated"):
        SearchService("uncalibrated")
    assert list_configs() == ["final", "strict", "uncalibrated"]
    assert resolve_config_path("final").name == "final.yaml"


def test_missing_documents_or_index_give_a_clear_error(tmp_path, monkeypatch):
    make_app_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CONTRACT_INTEL_DATA_DIR", str(tmp_path / "does-not-exist"))
    with pytest.raises(ApplicationError, match="not found"):
        SearchService("final")
    # manifest present, one indexed document deleted
    make_app_env(tmp_path / "second", monkeypatch)
    (tmp_path / "second" / "data" / "raw" / "corpus" / "cuad" / "B.txt").unlink()
    with pytest.raises(ApplicationError, match="missing"):
        SearchService("final")


# ---- web request handling (view model) ----
def test_web_view_for_answerable_question(env):
    v = run_search(SearchService("final"), Q_LAW, 3)
    assert v.status == "answered" and v.passages and v.weak == []
    p = v.passages[0]
    assert {"rank", "document", "doc_id", "start", "end", "score", "text", "before", "after"} <= set(p)
    assert (p["before"] + p["text"] + p["after"]) in DOC_A or p["doc_id"] != "cuad/A.txt"


def test_web_view_for_abstention_is_explicit_and_not_a_proof_of_absence(env):
    v = run_search(SearchService("strict"), Q_LAW, 3)
    assert v.status == "abstained" and v.passages == [] and "does not prove" in v.detail
    assert v.weak, "weak candidates are available but kept apart from the answer"


@pytest.mark.parametrize("q,k", [("", 3), ("   ", 3), (Q_LAW, 0), (Q_LAW, 500)])
def test_web_view_reports_invalid_input_without_a_traceback(env, q, k):
    v = run_search(SearchService("final"), q, k)
    assert v.status == "invalid" and v.message and "Traceback" not in v.message


def test_web_view_turns_unexpected_errors_into_messages(env, monkeypatch):
    svc = SearchService("final")
    monkeypatch.setattr(svc, "search", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    v = run_search(svc, Q_LAW, 3)
    assert v.status == "error" and "not answered" in v.message and v.detail == "boom"


# ---- full Streamlit script, headless ----
def _app():
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    st.cache_resource.clear()
    return AppTest.from_file(str(ROOT / "04_src" / "web_app.py"), default_timeout=60).run()


def test_streamlit_app_answers_and_abstains(env, monkeypatch):
    at = _app()
    assert not at.exception
    at.text_area[0].set_value(Q_LAW)
    at.button[-1].click().run()
    assert not at.exception and at.success and "cleared the evidence threshold" in at.success[0].value
    at.sidebar.selectbox[0].set_value("strict")
    at.button[-1].click().run()
    assert at.warning and "No sufficient evidence" in at.warning[0].value
    assert any("not proof" in i.value or "does not prove" in i.value for i in at.info)


def test_streamlit_app_handles_empty_question(env):
    at = _app()
    at.button[-1].click().run()
    assert not at.exception and at.warning and "enter a question" in at.warning[0].value


def test_streamlit_app_reports_missing_data(tmp_path, monkeypatch):
    make_app_env(tmp_path, monkeypatch)
    monkeypatch.setenv("CONTRACT_INTEL_DATA_DIR", str(tmp_path / "gone"))
    at = _app()
    at.text_area[0].set_value(Q_LAW)
    at.button[-1].click().run()
    assert at.error and "Could not start" in at.error[0].value


def test_disclaimer_says_results_are_not_legal_conclusions():
    assert "not legal conclusions" in DISCLAIMER
