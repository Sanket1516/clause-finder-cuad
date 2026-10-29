"""Original contract text management. Text is read once, exactly as the benchmark's offsets assume:
Python default text mode, UTF-8 (not utf-8-sig, no newline=''), and never modified afterwards."""
from pathlib import Path

from .benchmark import nfc


def read_document(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


class DocumentStore:
    """doc_id -> immutable original text, over a corpus root laid out as <root>/<doc_id>."""

    def __init__(self, corpus_root: Path, doc_ids):
        self.root = Path(corpus_root)
        self._files = self._index_files()
        self._texts: dict[str, str] = {}
        self.missing: list[str] = []
        for d in sorted(set(doc_ids)):
            p = self._files.get(nfc(d))
            if p is None:
                self.missing.append(d)
            else:
                self._texts[d] = read_document(p)

    def _index_files(self) -> dict[str, Path]:
        # NFC-normalise on both sides so an NFD/NFC spelling difference cannot hide a file
        out = {}
        if self.root.exists():
            for p in self.root.rglob("*.txt"):
                out[nfc(p.relative_to(self.root).as_posix())] = p
        return out

    def text(self, doc_id: str) -> str:
        return self._texts[doc_id]

    def __contains__(self, doc_id: str) -> bool:
        return doc_id in self._texts

    def doc_ids(self) -> list[str]:
        return sorted(self._texts)

    def path(self, doc_id: str) -> Path:
        return self._files[nfc(doc_id)]
