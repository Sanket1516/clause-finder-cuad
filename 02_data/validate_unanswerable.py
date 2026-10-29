"""Re-verify the frozen unanswerable set: schema, count, lock hash, split counts, and that every
absence pattern still has zero hits in its target document (or in the whole corpus for not_in_corpus).
Run: python 02_data/validate_unanswerable.py   (exit 1 on failure). Never edits the frozen file."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04_src"))

from contract_intel.data.corpus import DocumentStore  # noqa: E402
from contract_intel.data.unanswerable import load_unanswerable  # noqa: E402

D = ROOT / "02_data"


def check(min_n: int = 30) -> dict:
    rows = load_unanswerable(D / "unanswerable_queries.jsonl", D / "unanswerable_queries.sha256")
    all_docs = [json.loads(l)["doc_id"] for l in (D / "document_manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    store = DocumentStore(D / "raw" / "corpus", all_docs)
    failures = []
    for r in rows:
        ac = r["absence_check"]
        docs = [r["target_doc_id"]] if ac["scope"] == "target_doc" else store.doc_ids()
        for d in docs:
            for p in ac["patterns"]:
                n = len(re.findall(p, store.text(d), re.I))
                if n != ac["expected_hits"]:
                    failures.append({"query_id": r["query_id"], "doc_id": d, "pattern": p, "hits": n})
    return {
        "n": len(rows), "meets_minimum": len(rows) >= min_n,
        "by_split": dict(Counter(r["split"] for r in rows)),
        "by_category_split": {f"{k[0]}/{k[1]}": v for k, v in sorted(Counter((r["category"], r["split"]) for r in rows).items())},
        "absence_check_failures": failures,
    }


if __name__ == "__main__":
    rep = check()
    print(json.dumps(rep, indent=2))
    sys.exit(0 if rep["meets_minimum"] and not rep["absence_check_failures"] else 1)
