import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02_data" / "raw"
needs_data = pytest.mark.skipif(not (RAW / "benchmarks" / "cuad.json").exists(),
                                reason="run `python 02_data/download_data.py` first")


@pytest.fixture(scope="session")
def mini_records():
    from contract_intel.data.benchmark import load_tests, select_mini_with_ids
    return select_mini_with_ids(load_tests(RAW / "benchmarks" / "cuad.json"))


@pytest.fixture(scope="session")
def doc_ids(mini_records):
    from contract_intel.data.benchmark import doc_id_of
    return {doc_id_of(s["file_path"]) for m in mini_records for s in m["test"]["snippets"]}


@pytest.fixture(scope="session")
def store(doc_ids):
    from contract_intel.data.corpus import DocumentStore
    return DocumentStore(RAW / "corpus", doc_ids)


def jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
