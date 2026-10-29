"""Benchmark loading and the prescribed LegalBench-RAG-mini selection."""
import json
import random
import unicodedata
from pathlib import Path


def mini(tests, n=194):
    """Authors' selection function, verbatim (sorted() is stable, seeding is per-string deterministic)."""
    if len(tests) <= n:
        return tests

    def key(t):
        random.seed(t["snippets"][0]["file_path"])
        return random.random()

    return sorted(tests, key=key)[:n]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def doc_id_of(file_path: str) -> str:
    """Stable document id: NFC-normalised corpus-relative path (dataset card: one path is NFD)."""
    return nfc(file_path)


def load_tests(cuad_json: Path) -> list[dict]:
    raw = Path(cuad_json).read_text(encoding="utf-8")
    return json.loads(raw)["tests"]


def select_mini_with_ids(tests: list[dict], n: int = 194) -> list[dict]:
    """Run mini() and attach identifiers. The files carry no query IDs, so we record
    (a) position in the mini ordering and (b) the index in the full cuad.json."""
    original_index = {id(t): i for i, t in enumerate(tests)}
    chosen = mini(tests, n)
    out = []
    for pos, t in enumerate(chosen):
        out.append(
            {
                "query_id": f"cuad-mini-{pos:03d}",
                "mini_index": pos,
                "source_index": original_index[id(t)],
                "test": t,
            }
        )
    return out
