"""Build manifests from the downloaded data.

    python 02_data/prepare_dataset.py

Outputs (02_data/):
  query_manifest.jsonl     inference-safe fields only: query_id, query, split  (benchmark + unanswerable)
  gold_annotations.jsonl   evaluation-only: labels, gold spans, source doc, source indices
  document_manifest.jsonl  one row per indexed contract (id, sha256, sizes)
  split_manifest.json      counts per split/answerability, selection hashes
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from contract_intel.data.benchmark import doc_id_of, load_tests, select_mini_with_ids  # noqa: E402
from contract_intel.data.corpus import DocumentStore  # noqa: E402
from contract_intel.data.splits import assign_split  # noqa: E402
from contract_intel.data.unanswerable import load_unanswerable  # noqa: E402

D = ROOT / "02_data"
RAW = D / "raw"


def write_jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main() -> None:
    tests = load_tests(RAW / "benchmarks" / "cuad.json")
    mini = select_mini_with_ids(tests)
    if len(tests) >= 194 and len(mini) != 194:
        raise SystemExit(f"expected 194 selected queries, got {len(mini)}")
    ids = {doc_id_of(s["file_path"]) for m in mini for s in m["test"]["snippets"]}
    store = DocumentStore(RAW / "corpus", ids)
    if store.missing:
        raise SystemExit(f"missing documents (run download_data.py): {store.missing[:3]}")

    qrows, grows = [], []
    for m in mini:
        t = m["test"]
        q = t["query"]
        qrows.append({"query_id": m["query_id"], "query": q, "split": assign_split(q)})
        grows.append({
            "query_id": m["query_id"], "split": assign_split(q), "answerable": True,
            "mini_index": m["mini_index"], "source_index": m["source_index"],
            "doc_id": doc_id_of(t["snippets"][0]["file_path"]),
            "gold": [{"doc_id": doc_id_of(s["file_path"]), "start": s["span"][0], "end": s["span"][1],
                      "answer": s["answer"]} for s in t["snippets"]],
        })

    unans_path = D / "unanswerable_queries.jsonl"
    unans = []
    if unans_path.exists():
        lock = D / "unanswerable_queries.sha256"
        unans = load_unanswerable(unans_path, lock if lock.exists() else None)
        for r in unans:
            qrows.append({"query_id": r["query_id"], "query": r["query"], "split": r["split"]})
            grows.append({"query_id": r["query_id"], "split": r["split"], "answerable": False,
                          "category": r["category"], "doc_id": r["target_doc_id"], "gold": []})

    write_jsonl(D / "query_manifest.jsonl", qrows)
    write_jsonl(D / "gold_annotations.jsonl", grows)

    acq = json.loads((D / "acquisition_record.json").read_text(encoding="utf-8"))
    sha = {d["doc_id"]: d["sha256"] for d in acq["documents"]}
    per_doc = Counter(doc_id_of(m["test"]["snippets"][0]["file_path"]) for m in mini)
    write_jsonl(D / "document_manifest.jsonl", [
        {"doc_id": d, "sha256": sha[d], "n_chars": len(store.text(d)), "n_benchmark_queries": per_doc[d]}
        for d in store.doc_ids()])

    cnt = Counter((g["split"], "answerable" if g["answerable"] else "unanswerable") for g in grows)
    qlist_hash = hashlib.sha256("\n".join(m["test"]["query"] for m in mini).encode("utf-8")).hexdigest()
    dup = {q: c for q, c in Counter(m["test"]["query"] for m in mini).items() if c > 1}
    manifest = {
        "source_revision": acq["revision"],
        "n_source_queries": len(tests),
        "n_selected": len(mini),
        "n_documents_indexed": len(ids),
        "selected_queries_sha256": qlist_hash,
        "counts": {f"{s}_{a}": cnt[(s, a)] for s in ("train", "test") for a in ("answerable", "unanswerable")},
        "answerable_total": sum(1 for g in grows if g["answerable"]),
        "unanswerable_total": sum(1 for g in grows if not g["answerable"]),
        "unanswerable_by_category_and_split": {
            f"{c}/{s}": sum(1 for g in grows if not g["answerable"] and g.get("category") == c and g["split"] == s)
            for c in sorted({g.get("category") for g in grows if not g["answerable"]}) for s in ("train", "test")},
        "duplicate_benchmark_queries": dup,
        "unanswerable_file_sha256": hashlib.sha256(unans_path.read_bytes()).hexdigest() if unans else None,
    }
    (D / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("n_selected", "n_documents_indexed", "counts")}))


if __name__ == "__main__":
    main()
