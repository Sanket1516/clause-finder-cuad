"""Offset validation: every gold snippet must satisfy document[start:end] == answer."""
from collections import Counter

from .benchmark import doc_id_of, nfc
from .corpus import DocumentStore


def validate_snippets(mini_records: list[dict], store: DocumentStore) -> dict:
    """Return a report dict. Issue kinds: missing_document, bad_offsets, text_mismatch,
    overlapping_spans, multi_document_query."""
    issues, n_snip, n_ok = [], 0, 0
    for m in mini_records:
        qid, snippets = m["query_id"], m["test"]["snippets"]
        if len({nfc(s["file_path"]) for s in snippets}) > 1:
            issues.append({"query_id": qid, "kind": "multi_document_query"})
        spans = []
        for j, s in enumerate(snippets):
            n_snip += 1
            did = doc_id_of(s["file_path"])
            start, end = s["span"]
            if did not in store:
                issues.append({"query_id": qid, "snippet": j, "kind": "missing_document", "doc_id": did})
                continue
            text = store.text(did)
            if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text)):
                issues.append({"query_id": qid, "snippet": j, "kind": "bad_offsets", "span": [start, end], "doc_len": len(text)})
                continue
            if text[start:end] != s["answer"]:
                issues.append({"query_id": qid, "snippet": j, "kind": "text_mismatch", "span": [start, end],
                               "expected_head": s["answer"][:80], "found_head": text[start:end][:80]})
                continue
            n_ok += 1
            spans.append((start, end))
        spans.sort()
        for a, b in zip(spans, spans[1:]):
            if a[1] > b[0]:
                issues.append({"query_id": qid, "kind": "overlapping_spans", "spans": [list(a), list(b)]})
    return {
        "n_queries": len(mini_records),
        "n_snippets": n_snip,
        "n_snippets_exact_match": n_ok,
        "all_valid": n_ok == n_snip and not issues,
        "issue_counts": dict(Counter(i["kind"] for i in issues)),
        "issues": issues,
    }


def document_diagnostics(doc_id: str, raw_bytes: bytes, text: str) -> dict:
    """Facts that explain offset behaviour. The canonical text is NOT modified by any of this."""
    return {
        "doc_id": doc_id,
        "n_chars": len(text),
        "n_bytes": len(raw_bytes),
        "has_bom": text.startswith("﻿"),
        "crlf_in_raw_bytes": raw_bytes.count(b"\r\n"),
        "lone_cr_in_raw_bytes": raw_bytes.count(b"\r") - raw_bytes.count(b"\r\n"),
        "non_ascii_chars": sum(1 for c in text if ord(c) > 127),
        "non_bmp_chars": sum(1 for c in text if ord(c) > 0xFFFF),
        "path_nfc_equals_given": nfc(doc_id) == doc_id,
    }
