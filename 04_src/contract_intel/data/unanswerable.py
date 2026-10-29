"""Frozen unanswerable query set: loading, schema check, lock-hash check. Split is computed, never stored."""
import hashlib
import json
from pathlib import Path

from .splits import assign_split

CATEGORIES = {"absent_clause", "not_in_corpus", "out_of_scope"}
REQUIRED = {"query_id", "query", "category", "target_doc_id", "rationale", "absence_check", "verification_method"}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_unanswerable(path: Path, lock_path: Path | None = None) -> list[dict]:
    path = Path(path)
    if lock_path is not None:
        expect = Path(lock_path).read_text(encoding="utf-8").split()[0]
        if sha256_of(path) != expect:
            raise ValueError("unanswerable_queries.jsonl changed since it was frozen (sha256 lock mismatch)")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        missing = REQUIRED - r.keys()
        if missing:
            raise ValueError(f"{r.get('query_id')}: missing fields {sorted(missing)}")
        if r["category"] not in CATEGORIES:
            raise ValueError(f"{r['query_id']}: bad category {r['category']}")
        r["answerable"] = False
        r["split"] = assign_split(r["query"])
        rows.append(r)
    ids = [r["query_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate unanswerable query_id")
    return rows
