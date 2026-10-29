"""Evaluation queries: inference-safe fields (query text) and gold annotations are joined here for SCORING ONLY.
`Pipeline.search` never sees an EvalQuery."""
import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "02_data"


@dataclass(frozen=True)
class Gold:
    doc_id: str
    start: int
    end: int


@dataclass(frozen=True)
class EvalQuery:
    query_id: str
    query: str
    split: str
    answerable: bool
    gold: tuple[Gold, ...] = field(default_factory=tuple)
    doc_id: str | None = None
    category: str | None = None


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_queries(split: str, data_dir: Path = DATA_DIR) -> list[EvalQuery]:
    if split not in ("train", "test"):
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")
    q = {r["query_id"]: r for r in _jsonl(data_dir / "query_manifest.jsonl")}
    out = []
    for g in _jsonl(data_dir / "gold_annotations.jsonl"):
        if g["split"] != split:
            continue
        out.append(EvalQuery(
            query_id=g["query_id"], query=q[g["query_id"]]["query"], split=split, answerable=g["answerable"],
            gold=tuple(Gold(s["doc_id"], s["start"], s["end"]) for s in g["gold"]), doc_id=g.get("doc_id"),
            category=g.get("category")))
    return out
