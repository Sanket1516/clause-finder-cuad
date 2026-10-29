"""Validate document[start:end] == answer for every gold snippet of the 194 CUAD-mini queries.
    python 02_data/validate_offsets.py        -> 06_results/dataset_validation.json ; exit 1 on any failure
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from contract_intel.data.benchmark import doc_id_of, load_tests, select_mini_with_ids  # noqa: E402
from contract_intel.data.corpus import DocumentStore  # noqa: E402
from contract_intel.data.validate import document_diagnostics, validate_snippets  # noqa: E402

RAW = ROOT / "02_data" / "raw"


def run() -> dict:
    mini = select_mini_with_ids(load_tests(RAW / "benchmarks" / "cuad.json"))
    ids = {doc_id_of(s["file_path"]) for m in mini for s in m["test"]["snippets"]}
    store = DocumentStore(RAW / "corpus", ids)
    rep = validate_snippets(mini, store)
    rep["n_documents_referenced"] = len(ids)
    rep["missing_documents"] = store.missing
    rep["documents"] = [document_diagnostics(d, store.path(d).read_bytes(), store.text(d)) for d in store.doc_ids()]
    # the corpus folder must contain exactly the referenced contracts (nothing extra gets indexed)
    on_disk = {p.relative_to(RAW / "corpus").as_posix() for p in (RAW / "corpus").rglob("*.txt")}
    rep["extra_files_on_disk"] = sorted(on_disk - ids)
    rep["all_valid"] = rep["all_valid"] and not store.missing
    return rep


if __name__ == "__main__":
    rep = run()
    out = ROOT / "06_results" / "dataset_validation.json"
    out.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"snippets {rep['n_snippets_exact_match']}/{rep['n_snippets']} exact; issues={rep['issue_counts']}; "
          f"docs={rep['n_documents_referenced']}; all_valid={rep['all_valid']}")
    sys.exit(0 if rep["all_valid"] else 1)
