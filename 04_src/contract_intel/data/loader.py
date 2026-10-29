"""Locate the prepared corpus and build the DocumentStore (indexes exactly the contracts in document_manifest.jsonl)."""
import json
from pathlib import Path

from .corpus import DocumentStore
from .queries import DATA_DIR


class MissingDataError(RuntimeError):
    pass


def load_store(data_dir: Path = DATA_DIR) -> DocumentStore:
    manifest = Path(data_dir) / "document_manifest.jsonl"
    corpus = Path(data_dir) / "raw" / "corpus"
    if not manifest.exists():
        raise MissingDataError(f"{manifest} not found. Run: python 02_data/prepare_dataset.py")
    ids = [json.loads(l)["doc_id"] for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not corpus.exists():
        raise MissingDataError(f"{corpus} not found. Run: python 02_data/download_data.py")
    store = DocumentStore(corpus, ids)
    if store.missing:
        raise MissingDataError(f"{len(store.missing)} indexed documents are missing, e.g. {store.missing[0]}. "
                               "Run: python 02_data/download_data.py")
    return store
