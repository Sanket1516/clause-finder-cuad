"""Offset validation: every gold snippet must satisfy document[start:end] == answer, and failure modes are detected."""
import unicodedata

import pytest
from conftest import needs_data

from contract_intel.data.corpus import DocumentStore
from contract_intel.data.validate import validate_snippets


def _store(tmp_path, text):
    d = tmp_path / "corpus" / "cuad"
    d.mkdir(parents=True)
    (d / "a.txt").write_bytes(text.encode("utf-8"))
    return DocumentStore(tmp_path / "corpus", ["cuad/a.txt"])


def _rec(span, answer, path="cuad/a.txt", qid="q0"):
    return {"query_id": qid, "test": {"query": "q", "snippets": [{"file_path": path, "span": span, "answer": answer}]}}


def test_valid_snippet(tmp_path):
    s = _store(tmp_path, "Hello governing law world")
    rep = validate_snippets([_rec([6, 19], "governing law")], s)
    assert rep["all_valid"] and rep["n_snippets_exact_match"] == 1


def test_text_mismatch_detected(tmp_path):
    s = _store(tmp_path, "Hello governing law world")
    rep = validate_snippets([_rec([5, 18], "governing law")], s)
    assert rep["issue_counts"] == {"text_mismatch": 1} and not rep["all_valid"]


@pytest.mark.parametrize("span", [[-1, 3], [5, 5], [7, 3], [0, 999]])
def test_invalid_offsets_detected(tmp_path, span):
    s = _store(tmp_path, "Hello governing law world")
    assert validate_snippets([_rec(span, "x")], s)["issue_counts"] == {"bad_offsets": 1}


def test_missing_document_detected(tmp_path):
    s = _store(tmp_path, "abc")
    rep = validate_snippets([_rec([0, 1], "a", path="cuad/nope.txt")], s)
    assert rep["issue_counts"] == {"missing_document": 1}


def test_missing_document_reported_by_store(tmp_path):
    (tmp_path / "corpus" / "cuad").mkdir(parents=True)
    s = DocumentStore(tmp_path / "corpus", ["cuad/ghost.txt"])
    assert s.missing == ["cuad/ghost.txt"]


def test_overlapping_gold_spans_flagged(tmp_path):
    s = _store(tmp_path, "abcdefghij")
    rec = {"query_id": "q", "test": {"query": "q", "snippets": [
        {"file_path": "cuad/a.txt", "span": [0, 6], "answer": "abcdef"},
        {"file_path": "cuad/a.txt", "span": [4, 9], "answer": "efghi"}]}}
    assert validate_snippets([rec], s)["issue_counts"] == {"overlapping_spans": 1}


def test_crlf_is_normalised_like_default_text_mode(tmp_path):
    # Default text mode turns CRLF into LF; the benchmark offsets assume exactly that.
    s = _store(tmp_path, "line1\r\nline2")
    assert s.text("cuad/a.txt") == "line1\nline2"
    assert validate_snippets([_rec([6, 11], "line2")], s)["all_valid"]


def test_bom_is_preserved_not_stripped(tmp_path):
    s = _store(tmp_path, "﻿Title")
    assert s.text("cuad/a.txt").startswith("﻿")
    assert validate_snippets([_rec([1, 6], "Title")], s)["all_valid"]


def test_nfd_and_nfc_paths_resolve_to_the_same_file(tmp_path):
    name = "café.txt"  # NFC on disk
    d = tmp_path / "corpus" / "cuad"
    d.mkdir(parents=True)
    (d / name).write_text("hello", encoding="utf-8")
    nfd_id = unicodedata.normalize("NFD", "cuad/" + name)
    s = DocumentStore(tmp_path / "corpus", [nfd_id])
    assert not s.missing and s.text(nfd_id) == "hello"


@needs_data
def test_all_194_queries_gold_spans_match_exactly(mini_records, store):
    rep = validate_snippets(mini_records, store)
    assert rep["issues"] == []
    assert rep["n_snippets"] == rep["n_snippets_exact_match"] == 272
    assert store.missing == []
